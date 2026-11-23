"""使用 Odoo ORM 持久化窗口计数，为多 Worker 入站 API 提供共享限流。"""

import json
import logging
import math
from datetime import timedelta
from functools import wraps

from odoo import SUPERUSER_ID, api, fields, http
from odoo.http import request
from odoo.service.model import PG_CONCURRENCY_EXCEPTIONS_TO_RETRY

from .errors import GinlongAPIError, make_error


_logger = logging.getLogger(__name__)
_MAX_RETRIES = 16


def _reserve(api_user_id, api_code, window_start, limit, registry):
    """原子预留指定调用方在固定 UTC 秒窗口内的一个请求名额。

    参数：
        api_user_id: 已认证的 WorldDepot API 用户 ID。
        api_code: 独立限流的 Ginlong API 编号。
        window_start: 固定一秒窗口的起始时间。
        limit: 该 API 的可配置阈值。
        registry: 当前 Odoo Registry，用于打开独立事务。

    返回：
        成功占用名额时返回 True，达到阈值时返回 False。
    """
    domain = [
        ("api_user_id", "=", api_user_id),
        ("api_code", "=", api_code),
        ("window_start", "=", window_start),
    ]
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            with registry.cursor() as cr:
                env = api.Environment(cr, SUPERUSER_ID, {})
                counter_model = env["ginlong.api.rate.counter"]
                counter = counter_model.search(domain, limit=1)
                if counter and counter.request_count >= limit:
                    return False
                if counter:
                    counter.request_count += 1
                else:
                    counter_model.create({
                        "api_user_id": api_user_id,
                        "api_code": api_code,
                        "window_start": window_start,
                        "request_count": 1,
                    })
                cr.commit()
                return True
        except Exception as error:
            _logger.warning(
                "Ginlong limiter ORM concurrency retry api=%s attempt=%s error=%s",
                api_code, attempt, type(error).__name__,
            )
    _logger.error("Ginlong limiter exhausted ORM retries api=%s", api_code)
    raise make_error("RATE02", details="counter reservation retries exhausted")


def rate_limit(api_code):
    """为指定入站接口套用认证用户独立的 UTC 固定一秒限额。

    参数：
        api_code: 需要应用限流的 Ginlong API 编号。

    返回：
        包装后的 Odoo Controller 方法；超限时返回 429 和 Retry-After。
    """
    def decorator(function):
        """包装目标路由，使每次通过认证的请求先占用共享限流名额。"""
        @wraps(function)
        def wrapper(*args, **kwargs):
            """检查当前请求的限流结果，超限时生成 429 响应。"""
            api_user = getattr(request, "api_user", False)
            if not api_user:
                return function(*args, **kwargs)

            reserved = getattr(request, "_ginlong_rate_results", None)
            if reserved is None:
                reserved = {}
                request._ginlong_rate_results = reserved
            if api_code in reserved:
                allowed, window_start, limit = reserved[api_code]
            else:
                try:
                    limit = request.env["res.config.settings"].sudo().get_ginlong_api_rate_limit(api_code)
                    now = fields.Datetime.now()
                    window_start = now.replace(microsecond=0)
                    allowed = _reserve(api_user.id, api_code, window_start, limit, request.registry)
                except PG_CONCURRENCY_EXCEPTIONS_TO_RETRY:
                    raise
                except GinlongAPIError:
                    raise
                except Exception as error:
                    raise make_error(
                        "RATE02",
                        details="%s: %s" % (type(error).__name__, error),
                    ) from error
                if allowed:
                    # 请求内标记仅避免 Odoo 重试同一 HTTP 事务时重复扣次；跨 Worker 的共享计数始终保存在 ORM 模型中。
                    reserved[api_code] = (allowed, window_start, limit)

            if allowed:
                return function(*args, **kwargs)

            now = fields.Datetime.now()
            remaining = max(1, math.ceil(1 - (now - window_start).total_seconds()))
            response = http.Response(
                json.dumps({"success": False, "code": 429, "error": "Rate limit exceeded"}),
                status=429,
                headers={"Retry-After": str(remaining)},
                mimetype="application/json",
            )
            return response

        return wrapper
    return decorator
