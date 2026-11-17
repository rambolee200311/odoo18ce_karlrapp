import logging
import json
from functools import wraps
from datetime import datetime
from odoo.http import request
from odoo import models, fields, api, _

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

        except Exception as e:
            # Rollback main transaction before handling error
            request.env.cr.rollback()
            status = 'error'
            response_str = ''
            exception_details = str(e)
            response = {
                'success': False,
                'error': 'An unexpected error occurred. Please contact support.',
                'details': exception_details,
                "code": "SERVER_ERROR",
            }
            response_str = json.dumps(response, ensure_ascii=False)
            log_success = False
            log_code = "SERVER_ERROR"
            log_msg = exception_details
            log_data = ""
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
