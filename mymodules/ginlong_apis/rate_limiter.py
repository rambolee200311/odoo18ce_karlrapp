import json
import logging
import math
from datetime import timedelta
from functools import wraps

from odoo import SUPERUSER_ID, api, fields, http
from odoo.exceptions import UserError
from odoo.http import request


_logger = logging.getLogger(__name__)
_MAX_RETRIES = 16


def _reserve(api_user_id, api_code, window_start, limit, registry):
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
    raise UserError("Ginlong API rate limiter is temporarily unavailable; retry the request.")


def rate_limit(api_code):
    """Apply one authenticated API user's fixed UTC one-second quota."""
    def decorator(function):
        @wraps(function)
        def wrapper(*args, **kwargs):
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
                limit = request.env["res.config.settings"].sudo().get_ginlong_api_rate_limit(api_code)
                now = fields.Datetime.now()
                window_start = now.replace(microsecond=0)
                allowed = _reserve(api_user.id, api_code, window_start, limit, request.registry)
                if allowed:
                    # The marker only prevents the Odoo HTTP transaction retry
                    # from consuming this external request twice. Shared quota
                    # state always lives in the PostgreSQL ORM model.
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
