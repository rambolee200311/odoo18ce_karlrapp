import json
import logging

from odoo import http
from odoo.exceptions import UserError
from odoo.service.model import PG_CONCURRENCY_EXCEPTIONS_TO_RETRY
from odoo.http import request
from odoo.addons.worlddepot.controllers.api_logs import api_logger
from odoo.addons.worlddepot.controllers.validator_token import validate_token

from .. import services
from ..idempotency import execute as execute_idempotent
from ..rate_limiter import rate_limit

_logger = logging.getLogger(__name__)


class GinlongSimulationController(http.Controller):
    """Local simulation endpoints; not Ginlong's confirmed production routes."""

    @staticmethod
    def _json_response(body, status=200):
        return http.Response(
            json.dumps(body, ensure_ascii=False),
            status=status,
            mimetype="application/json",
        )

    def _dispatch(self, api_code, handler):
        try:
            payload = json.loads(request.httprequest.data or b"{}")
            if not isinstance(payload, dict):
                return self._json_response({"success": False, "error": "Request body must be a JSON object"})
            api_user = getattr(request, "api_user", False)
            if not api_user:
                return self._json_response({"success": False, "error": "Authenticated API user is not configured"})
            result = execute_idempotent(
                request.env,
                api_code,
                payload,
                lambda: handler(request.env, api_user, payload),
            )
            return self._json_response(result)
        except PG_CONCURRENCY_EXCEPTIONS_TO_RETRY:
            # Let the Odoo HTTP request transaction retry serialization and
            # deadlock errors; converting them to JSON here would bypass it.
            raise
        except (TypeError, ValueError) as error:
            return self._json_response({"success": False, "error": "Invalid JSON request: %s" % error})
        except UserError as error:
            return self._json_response({"success": False, "error": str(error)})
        except Exception as error:
            _logger.info("Ginlong local simulation request rejected: %s", error)
            return self._json_response({"success": False, "error": str(error)})

    @http.route('/ginlong/sim/api01', type='http', auth='none', methods=['POST'], csrf=False)
    @validate_token
    @api_logger
    @rate_limit("API01")
    def api01(self, **params):
        return self._dispatch("API01", services.api01)

    @http.route('/ginlong/sim/api03', type='http', auth='none', methods=['POST'], csrf=False)
    @validate_token
    @api_logger
    @rate_limit("API03")
    def api03(self, **params):
        # API03 remains the local A-003 Solis -> Odoo development assumption.
        return self._dispatch("API03", services.api03)

    @http.route('/ginlong/sim/api05', type='http', auth='none', methods=['POST'], csrf=False)
    @validate_token
    @api_logger
    @rate_limit("API05")
    def api05(self, **params):
        return self._dispatch("API05", services.api05)

    @http.route('/ginlong/sim/api07', type='http', auth='none', methods=['POST'], csrf=False)
    @validate_token
    @api_logger
    @rate_limit("API07")
    def api07(self, **params):
        return self._dispatch("API07", services.api07)
