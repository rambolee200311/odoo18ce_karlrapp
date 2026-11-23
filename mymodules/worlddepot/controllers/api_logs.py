import logging
import json
from functools import wraps
from datetime import datetime
from odoo.http import request
from odoo import http, models, fields, api, _
from odoo.service.model import PG_CONCURRENCY_EXCEPTIONS_TO_RETRY

_logger = logging.getLogger(__name__)

_AUTH_ENDPOINTS = {
    '/world_depot/api/auth/token',
    '/world_depot/api/auth/getToken',
}
_REDACTED = '[REDACTED]'


def _request_data_for_log(request_path, request_data):
    """Mask api_secret only on the existing token-issuing endpoints."""
    if request_path not in _AUTH_ENDPOINTS or not request_data:
        return request_data
    try:
        payload = json.loads(request_data)
    except (TypeError, ValueError):
        # The authentication endpoint only accepts JSON credentials. If it is
        # malformed, do not persist or print the unparseable raw body.
        return '[authentication request omitted]'
    if not isinstance(payload, dict):
        return '[authentication request omitted]'
    if 'api_secret' in payload:
        payload['api_secret'] = _REDACTED
    return json.dumps(payload, ensure_ascii=False)


def _response_data_for_log(request_path, response):
    """Mask access_token in the two known token endpoint response shapes."""
    if request_path not in _AUTH_ENDPOINTS or not isinstance(response, dict):
        return response
    # Copy through JSON so the returned response object remains unchanged.
    try:
        payload = json.loads(json.dumps(response, ensure_ascii=False))
    except (TypeError, ValueError):
        return {'data': '[authentication response omitted]'}
    if 'access_token' in payload:
        payload['access_token'] = _REDACTED
    data = payload.get('data')
    if isinstance(data, dict) and 'access_token' in data:
        data['access_token'] = _REDACTED
    return payload


def _is_ginlong_api_path(request_path):
    """识别需要采用 Ginlong 三字段错误契约的入站路由。"""
    return request_path.startswith(('/api/ginlong/', '/ginlong/sim/'))


def _ginlong_system_error_values(error):
    """用 Ginlong 通用 Error 配置生成安全兜底错误，失败时使用固定安全响应。"""
    details = "%s: %s" % (type(error).__name__, error)
    try:
        # 延迟导入避免 WorldDepot 在加载时依赖 Ginlong 模块。
        from odoo.addons.ginlong_apis.errors import make_error

        configured_error = make_error("SYS01", details=details)
        return configured_error.to_log_values()
    except Exception:
        # Error 配置本身不可用时，仍禁止把原始异常内容透传给外部调用方。
        return {
            "code": "SYS01",
            "message": "系统处理失败",
            "details": details,
            "exception_info": "SYS01: 系统处理失败",
        }


class APILog(models.Model):
    _name = 'world.depot.api.log'
    _description = 'API Log'
    _order = 'request_time desc'

    project_id = fields.Many2one("project.project", string="Project", index=True)
    request_source = fields.Char(string='Request Source', help='IP address of the request source')
    request_time = fields.Datetime(string='Request Time', help='Time when the request was received')
    request_path = fields.Char(string='Request Path', help='API endpoint path')
    request_data = fields.Text(string='Request Data', help='Payload of the API request')
    response_data = fields.Text(string='Response Data', help='Payload of the API response')
    exception_details = fields.Text(string='Exception Details', help='Details of any exception that occurred')
    status = fields.Selection(
        [('success', 'Success'), ('error', 'Error')],
        string='Status',
        help='Indicates whether the API call was successful or not'
    )
    code = fields.Char(string='Code', help='API endpoint code')
    success = fields.Boolean(string='Success', help='Indicates whether the API call was successful or not')
    msg = fields.Char(string='Message', help='API endpoint message')
    data = fields.Text(string='Data', help='API endpoint data')

''''
def api_logger(func):
    """Decorator to log API requests, responses, and exceptions using independent transactions."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        # Capture request details at the start
        request_data = request.httprequest.data.decode('utf-8') if request.httprequest.data else ''
        request_source = request.httprequest.remote_addr
        request_time = fields.Datetime.now()
        request_path = request.httprequest.path

        # Execute the endpoint function
        try:
            response = func(*args, **kwargs)
            status = 'success'
            response_str = json.dumps(response) if response else ''
        except Exception as e:
            if isinstance(e, PG_CONCURRENCY_EXCEPTIONS_TO_RETRY):
                # Preserve Odoo's built-in HTTP transaction retry. Rolling back
                # or translating here would hide a serialization/deadlock from
                # the dispatcher before it can rerun the request.
                raise
            # Rollback main transaction before handling error
            request.env.cr.rollback()
            status = 'error'
            response_str = ''
            exception_details = str(e)
            response = {
                'error': 'An unexpected error occurred. Please contact support.',
                'details': exception_details
            }
        finally:
            # Always log using a separate transaction
            try:
                # Create log record using a new cursor/environment
                with api.Environment.manage():
                    with request.registry.cursor() as cr:
                        env = api.Environment(cr, request.env.uid, request.env.context)
                        log_vals = {
                            'request_source': request_source,
                            'request_time': request_time,
                            'request_path': request_path,
                            'request_data': request_data,
                            'status': status,
                        }

                        if status == 'success':
                            log_vals['response_data'] = response_str
                        else:
                            log_vals['exception_details'] = exception_details

                        env['world.depot.api.log'].sudo().create(log_vals)
                        cr.commit()
            except Exception as log_exc:
                # If logging fails, fallback to server logs
                _logger.error("API LOG FAILED: %s - %s", request_path, str(log_exc))
                _logger.debug("Request details: %s", {
                    'source': request_source,
                    'path': request_path,
                    'data': request_data
                })

        return response

    return wrapper

'''


def api_logger(func):
    """Decorator to log API requests, responses, and exceptions using independent transactions."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        # Capture request details at the start
        request_data = request.httprequest.data.decode('utf-8') if request.httprequest.data else ''
        request_source = request.httprequest.remote_addr
        request_time = fields.Datetime.now()
        request_path = request.httprequest.path
        request_data = _request_data_for_log(request_path, request_data)
        response = None
        response_str = ""
        response_for_log = None
        exception_details = None
        status = "success"
        log_success = True
        log_code = "200"
        log_msg = ""
        log_data = ""

        # Execute the endpoint function
        try:
            response = func(*args, **kwargs)
            if isinstance(response, http.Response):
                response_status = response.status_code
                response_str = response.get_data(as_text=True) or ""
                response_for_log = None
                if response_status >= 400:
                    log_success = False
                    status = "error"
                    log_code = str(response_status)
                    log_msg = "HTTP %s" % response_status
                    log_data = response_str
            else:
                response_for_log = _response_data_for_log(request_path, response)
                response_str = json.dumps(response_for_log, ensure_ascii=False) if response_for_log else ''

            if isinstance(response_for_log, dict):
                if "success" in response_for_log:
                    log_success = bool(response_for_log.get("success"))
                    status = "success" if log_success else "error"
                elif "error" in response_for_log:
                    log_success = False
                    status = "error"

                log_code = response_for_log.get("code") or ("200" if log_success else "ERROR")
                log_msg = response_for_log.get("msg") or response_for_log.get("error") or ""
                if "data" in response_for_log:
                    log_data = json.dumps(response_for_log.get("data"), ensure_ascii=False)

            # 集成控制器可附加内部错误元数据；日志记录完整诊断，但不改写已生成的对外响应。
            internal_error = getattr(request, "ginlong_api_error_log", None)
            if isinstance(internal_error, dict) and internal_error.get("code"):
                log_success = False
                status = "error"
                log_code = internal_error["code"]
                log_msg = internal_error.get("message") or ""
                exception_details = internal_error.get("details") or log_msg

        except Exception as e:
            if isinstance(e, PG_CONCURRENCY_EXCEPTIONS_TO_RETRY):
                # Preserve Odoo's built-in HTTP transaction retry. Rolling back
                # or translating here would hide a serialization/deadlock from
                # the dispatcher before it can rerun the request.
                raise
            # Rollback main transaction before handling error
            request.env.cr.rollback()
            status = 'error'
            response_str = ''
            exception_details = str(e)
            log_success = False
            log_data = ""
            if _is_ginlong_api_path(request_path):
                error_values = _ginlong_system_error_values(e)
                exception_details = error_values.get("details") or str(e)
                log_code = error_values["code"]
                log_msg = error_values["message"]
                response = http.Response(
                    json.dumps({
                        "returnStatus": "N",
                        "exceptionInfo": error_values["exception_info"],
                        "operationTime": fields.Datetime.to_string(fields.Datetime.now()),
                    }, ensure_ascii=False),
                    status=500,
                    mimetype="application/json",
                )
                response_str = response.get_data(as_text=True)
            else:
                response = {
                    'success': False,
                    'error': 'An unexpected error occurred. Please contact support.',
                    'details': exception_details,
                    "code": "SERVER_ERROR",
                }
                response_str = json.dumps(response, ensure_ascii=False)
                log_code = "SERVER_ERROR"
                log_msg = exception_details
        # Always log using a separate transaction
        try:
            # Create a new database connection and environment for logging
            db_name = request.env.cr.dbname
            registry = request.registry
            with registry.cursor() as cr:
                # Create a new environment with the new cursor
                env = api.Environment(cr, request.env.uid, request.env.context)

                api_user = getattr(request, "api_user", False)
                project = api_user.project if api_user and api_user.project else False
                log_vals = {
                    'request_source': request_source,
                    'request_time': request_time,
                    'request_path': request_path,
                    'request_data': request_data,
                    'response_data': response_str,
                    'exception_details': exception_details,
                    'status': status,
                    'project_id': project.id if project else False,
                    "success": log_success,
                    "code": log_code,
                    "msg": log_msg,
                    "data": log_data,
                }

                # if status == 'success':
                #     log_vals['response_data'] = response_str
                # else:
                #     log_vals['exception_details'] = exception_details

                env['world.depot.api.log'].sudo().create(log_vals)
                cr.commit()
        except Exception as log_exc:
            # If logging fails, fallback to server logs
            _logger.error("API LOG FAILED: %s - %s", request_path, str(log_exc))
            _logger.debug("Request details: %s", {
                'source': request_source,
                'path': request_path,
                'data': request_data
            })

        return response

    return wrapper
