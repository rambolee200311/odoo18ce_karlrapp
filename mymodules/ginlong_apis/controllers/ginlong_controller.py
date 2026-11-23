"""提供 Ginlong 入库、出库、盘点、产品和库存查询 HTTP 入口。"""

import json
import logging
from functools import wraps

from odoo import fields, http
from odoo.exceptions import UserError
from odoo.service.model import PG_CONCURRENCY_EXCEPTIONS_TO_RETRY
from odoo.http import request
from odoo.addons.worlddepot.controllers.api_logs import api_logger
from odoo.addons.worlddepot.controllers.validator_token import validate_token

from .. import services
from ..errors import GinlongAPIError, make_error
from ..idempotency import execute as execute_idempotent
from ..rate_limiter import rate_limit
from ..validators.required_validator import RequiredFieldError
from ..validators.type_validator import FieldTypeValidationError
from ..validators.payload_validator import validate_payload

_logger = logging.getLogger(__name__)


def _protocol_error_response(error, status=200, retry_after=None):
    """生成仅含 Ginlong 错误协议字段的响应，并登记内部错误信息。"""
    request.ginlong_api_error_log = error.to_log_values()
    response = GinlongSimulationController._json_response({
        "returnStatus": "N",
        "exceptionInfo": error.exception_info,
        "operationTime": fields.Datetime.to_string(fields.Datetime.now()),
    }, status=status)
    if retry_after:
        response.headers["Retry-After"] = retry_after
    return response


def _configured_error_for_exception(error):
    """将校验、格式、业务和系统异常映射到配置目录中的稳定错误码。"""
    if isinstance(error, GinlongAPIError):
        return error
    if isinstance(error, RequiredFieldError):
        related_types = getattr(error, "related_type_issues", ())
        related_type_details = "; Type errors: " + "; ".join(related_types) if related_types else ""
        return make_error(
            "REQ01",
            details="; ".join(error.issues),
            related_type_details=related_type_details,
        )
    if isinstance(error, FieldTypeValidationError):
        return make_error("TYP01", details="; ".join(error.issues))
    if isinstance(error, (TypeError, ValueError)):
        return make_error("REQ02", details=str(error))
    if isinstance(error, UserError):
        # Odoo UserError/ValidationError 属于业务可见异常；Error 组件会清理凭据并限制协议长度。
        return make_error("BUS01", message=str(error), details=str(error))
    return make_error("SYS01", details="%s: %s" % (type(error).__name__, error))


def ginlong_error_response(api_code, strict_success=False):
    """统一规范 Ginlong 路由错误响应，覆盖认证、限流和业务入口。

    参数：
        api_code: 当前路由对应的 Ginlong API 编号。
        strict_success: 是否将成功响应也裁剪为 V3.2 三字段结构。

    返回：
        使用三字段错误结构的路由包装器；限流响应保留 Retry-After。
    """
    def decorator(function):
        @wraps(function)
        def wrapper(*args, **kwargs):
            """捕获内部失败并清理对外响应，只保留协议字段。"""
            request.ginlong_api_code = api_code
            request.ginlong_api_error_log = None
            try:
                response = function(*args, **kwargs)
            except PG_CONCURRENCY_EXCEPTIONS_TO_RETRY:
                raise
            except GinlongAPIError as error:
                status = 503 if error.error_code == "RATE02" else 200
                return _protocol_error_response(error, status=status)
            except UserError as error:
                # 装饰器或认证前置流程抛出的业务异常也走同一错误目录，不误报为系统故障。
                configured_error = _configured_error_for_exception(error)
                _logger.info(
                    "Ginlong %s request rejected by business rule (%s)",
                    api_code, configured_error.error_code,
                )
                return _protocol_error_response(configured_error, status=200)
            except Exception as error:
                _logger.exception("Ginlong %s request failed", api_code)
                return _protocol_error_response(
                    make_error("SYS01", details="%s: %s" % (type(error).__name__, error)),
                    status=500,
                )

            status = getattr(response, "status_code", 200)
            retry_after = getattr(response, "headers", {}).get("Retry-After")
            if isinstance(response, http.Response):
                try:
                    internal_body = json.loads(response.get_data(as_text=True) or "{}")
                except (TypeError, ValueError):
                    internal_body = {}
            elif isinstance(response, dict):
                internal_body = response
            else:
                return response
            if not isinstance(internal_body, dict):
                internal_body = {}

            failed = (
                status >= 400
                or internal_body.get("returnStatus") == "N"
                or internal_body.get("success") is False
                or "error" in internal_body
            )
            if failed:
                logged = getattr(request, "ginlong_api_error_log", None)
                error_code = logged.get("code") if isinstance(logged, dict) else None
                if not error_code:
                    if status in (401, 403):
                        error_code = "AUTH01"
                    elif status == 429:
                        error_code = "RATE01"
                    elif status >= 500:
                        error_code = "SYS01"
                    elif status == 400:
                        error_code = "REQ02"
                    else:
                        error_code = "BUS01"
                    detail = internal_body.get("error") or internal_body.get("exceptionInfo") or "HTTP %s" % status
                    return _protocol_error_response(
                        make_error(error_code, details=detail), status=status, retry_after=retry_after,
                    )

                operation_time = internal_body.get("operationTime") or fields.Datetime.to_string(fields.Datetime.now())
                response_body = {
                    "returnStatus": "N",
                    "exceptionInfo": logged.get("exception_info") or "%s: %s" % (
                        error_code, logged.get("message", "")
                    ),
                    "operationTime": operation_time,
                }
                strict_response = http.Response(
                    json.dumps(response_body, ensure_ascii=False), status=status, mimetype="application/json",
                )
                if retry_after:
                    strict_response.headers["Retry-After"] = retry_after
                return strict_response

            if strict_success:
                response_body = {
                    "returnStatus": internal_body.get("returnStatus", "Y"),
                    "exceptionInfo": internal_body.get("exceptionInfo") or "OK",
                    "operationTime": internal_body.get("operationTime") or fields.Datetime.to_string(fields.Datetime.now()),
                }
                return http.Response(
                    json.dumps(response_body, ensure_ascii=False), status=status, mimetype="application/json",
                )
            return response

        return wrapper
    return decorator


def strict_api07_response(function):
    """兼容旧测试入口；生产路由使用统一的 Ginlong 错误包装器。"""
    return ginlong_error_response("API07", strict_success=True)(function)


class GinlongSimulationController(http.Controller):
    """接收 Ginlong 入站请求并复用现有认证、日志、限流和业务服务。"""

    @staticmethod
    def _json_response(body, status=200):
        """将结果编码为 JSON HTTP 响应。

        参数：
            body: 要返回的 JSON 兼容对象。
            status: HTTP 状态码，默认 200。

        返回：
            Odoo HTTP Response。
        """
        return http.Response(
            json.dumps(body, ensure_ascii=False),
            status=status,
            mimetype="application/json",
        )

    @staticmethod
    def _success_body(api_code, result):
        """构造并验证符合 Ginlong V3.2 的成功响应。

        参数：
            api_code: Ginlong API 编号。
            result: 业务服务返回结果。

        返回：
            API07 仅包含协议字段；其他接口保留现有本地结果字段并补齐协议字段。
        """
        # API07 只回传 V3.2 定义的响应字段；产品 ID 和内部处理结果不进入对外报文。
        body = {} if api_code == "API07" else dict(result)
        body.update({
            "returnStatus": "Y",
            "exceptionInfo": "OK",
            "operationTime": fields.Datetime.to_string(fields.Datetime.now()),
        })
        validate_payload(api_code, body, direction="response")
        return body

    @staticmethod
    def _failure_body(api_code, message, payload=None):
        """构造 V3.2 三字段错误体，不将内部异常或查询条件混入响应。"""
        error = message if isinstance(message, GinlongAPIError) else _configured_error_for_exception(
            message if isinstance(message, Exception) else UserError(str(message))
        )
        return {
            "returnStatus": "N",
            "exceptionInfo": error.exception_info,
            "operationTime": fields.Datetime.to_string(fields.Datetime.now()),
        }

    def _dispatch(self, api_code, handler, error_status=200):
        """解析并分派一个有幂等保护的 Ginlong 入站请求。

        参数：
            api_code: Ginlong API 编号。
            handler: 对应的 ORM 业务处理函数。
            error_status: 业务错误映射的 HTTP 状态码。

        返回：
            表示业务结果或错误的 JSON HTTP Response。
        """
        # 清空本次请求的内部错误日志元数据，避免后续装饰器误用旧诊断信息。
        request.ginlong_api_error_log = None
        try:
            payload = json.loads(request.httprequest.data or b"{}")
            if not isinstance(payload, dict):
                raise ValueError("Request body must be a JSON object")
            # 非保税 API01 Add 的 snList 不属于业务数据；只在校验副本中移除，
            # 原始 payload 仍传给服务及共享日志，确保日志能还原实际收到的请求。
            validation_payload = payload
            raw_action = payload.get("action")
            is_api01_add = (
                api_code == "API01"
                and isinstance(raw_action, str)
                and raw_action.strip().casefold() in {"add", "create"}
            )
            if is_api01_add and not services.api01_uses_bonded_forecast_sn(payload):
                validation_payload = {key: value for key, value in payload.items() if key != "snList"}
            # 先校验适用的 O 列字段及嵌套行，再做 Action 规范化、幂等查询或业务 ORM 操作。
            validate_payload(api_code, validation_payload, direction="request")
            request_path = getattr(request.httprequest, "path", "")
            payload = services.normalize_inbound_action(
                api_code, payload, strict=request_path.startswith("/api/ginlong/"),
            )
            api_user = getattr(request, "api_user", False)
            if not api_user:
                raise make_error("AUTH01", details="Authenticated API user is not configured")
            if api_code == "API07":
                # Add 先核对 owner + productCode，再进入通用幂等重放，确保重复新增返回业务失败。
                services.ensure_api07_add_is_new(request.env, api_user, payload)
            if api_code == "API07":
                # 幂等器需要内部的 success=True 判断并保存真实业务结果；
                # 先执行幂等，再裁剪为 Ginlong 三字段响应，避免错误地回滚成功 Add。
                result = execute_idempotent(
                    request.env,
                    api_code,
                    payload,
                    lambda: handler(request.env, api_user, payload),
                )
                result = self._success_body(api_code, result)
            else:
                result = execute_idempotent(
                    request.env,
                    api_code,
                    payload,
                    lambda: self._success_body(api_code, handler(request.env, api_user, payload)),
                )
            return self._json_response(result)
        except PG_CONCURRENCY_EXCEPTIONS_TO_RETRY:
            # 并发序列化或死锁异常交回 Odoo 请求事务处理，转换成 JSON 会绕过其重试机制。
            raise
        except (RequiredFieldError, FieldTypeValidationError) as error:
            return _protocol_error_response(_configured_error_for_exception(error), status=error_status)
        except GinlongAPIError as error:
            return _protocol_error_response(error, status=error_status)
        except (TypeError, ValueError) as error:
            return _protocol_error_response(_configured_error_for_exception(error), status=error_status)
        except UserError as error:
            return _protocol_error_response(_configured_error_for_exception(error), status=error_status)
        except Exception as error:
            _logger.exception("Ginlong %s business processing failed", api_code)
            return _protocol_error_response(_configured_error_for_exception(error), status=error_status)

    @http.route(['/ginlong/sim/api01', '/api/ginlong/TPL_Pending_Receipt_Note'], type='http', auth='none', methods=['POST'], csrf=False)
    @api_logger
    @ginlong_error_response("API01", strict_success=True)
    @validate_token
    @rate_limit("API01")
    def api01(self, **params):
        """接收入库指令，并映射到现有入库 Order，不执行实物收货。

        参数：
            params: Odoo 路由参数；业务 JSON 从当前 HTTP request body 读取。

        返回：
            仅含 returnStatus、exceptionInfo、operationTime 的 Ginlong JSON HTTP Response。
        """
        return self._dispatch("API01", services.api01)

    @http.route(['/ginlong/sim/api03', '/api/ginlong/TPL_Pending_Delivery_Note'], type='http', auth='none', methods=['POST'], csrf=False)
    @api_logger
    @ginlong_error_response("API03")
    @validate_token
    @rate_limit("API03")
    def api03(self, **params):
        """接收出库指令，并按 owner 与 productCode 校验产品变体。

        参数：
            params: Odoo 路由参数；业务 JSON 从当前 HTTP request body 读取。

        返回：
            API03 业务结果对应的 JSON HTTP Response。
        """
        return self._dispatch("API03", services.api03, error_status=400)

    @http.route(['/ginlong/sim/api05', '/api/ginlong/TPL_Stocktake_Order'], type='http', auth='none', methods=['POST'], csrf=False)
    @api_logger
    @ginlong_error_response("API05")
    @validate_token
    @rate_limit("API05")
    def api05(self, **params):
        """接收客户盘点指令并写入现有 WorldDepot 盘点订单。

        参数：
            params: Odoo 路由参数；业务 JSON 从当前 HTTP request body 读取。

        返回：
            API05 业务结果对应的 JSON HTTP Response。
        """
        return self._dispatch("API05", services.api05)

    @http.route(['/ginlong/sim/api07', '/api/ginlong/TPL_Product_Master'], type='http', auth='none', methods=['POST'], csrf=False)
    @api_logger
    @ginlong_error_response("API07", strict_success=True)
    @validate_token
    @rate_limit("API07")
    def api07(self, **params):
        """接收产品档案并更新原生产品模板及货主变体。

        参数：
            params: Odoo 路由参数；业务 JSON 从当前 HTTP request body 读取。

        返回：
            API07 业务结果对应的 JSON HTTP Response。
        """
        return self._dispatch("API07", services.api07)

    @http.route('/api/ginlong/TPL_Stock_Query', type='http', auth='none', methods=['POST'], csrf=False)
    @api_logger
    @ginlong_error_response("API09")
    @validate_token
    def api09(self, **params):
        """只读查询指定货主和仓库的实际物理库存，不更改库存记录。

        参数：
            params: Odoo 路由参数；owner 和 warehouse 从 JSON 请求体读取。

        返回：
            API09 库存结果、请求错误或服务器错误对应的 JSON HTTP Response。
        """
        payload = None
        try:
            payload = json.loads(request.httprequest.data or b"{}")
            if not isinstance(payload, dict):
                raise ValueError("Request body must be a JSON object")
            validate_payload("API09", payload, direction="request")
            result = services.api09(request.env, payload)
            validate_payload("API09", result, direction="response")
            return self._json_response(result)
        except PG_CONCURRENCY_EXCEPTIONS_TO_RETRY:
            raise
        except (RequiredFieldError, FieldTypeValidationError, GinlongAPIError) as error:
            return _protocol_error_response(_configured_error_for_exception(error), status=400)
        except (TypeError, ValueError) as error:
            return _protocol_error_response(_configured_error_for_exception(error), status=400)
        except UserError as error:
            return _protocol_error_response(_configured_error_for_exception(error), status=400)
        except Exception as error:
            _logger.exception("Ginlong API09 inventory query failed")
            return _protocol_error_response(_configured_error_for_exception(error), status=500)
