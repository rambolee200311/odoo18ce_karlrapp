import json
import logging

from odoo import fields, http
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
    """Ginlong inbound routes plus the former local simulation aliases."""

    @staticmethod
    def _json_response(body, status=200):
        return http.Response(
            json.dumps(body, ensure_ascii=False),
            status=status,
            mimetype="application/json",
        )

    def _dispatch(self, api_code, handler, error_status=200):
        try:
            payload = json.loads(request.httprequest.data or b"{}")
            if not isinstance(payload, dict):
                return self._json_response(
                    {"success": False, "error": "Request body must be a JSON object"}, status=error_status,
                )
            request_path = getattr(request.httprequest, "path", "")
            payload = services.normalize_inbound_action(
                api_code, payload, strict=request_path.startswith("/api/ginlong/"),
            )
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
            return self._json_response(
                {"success": False, "error": "Invalid JSON request: %s" % error}, status=error_status,
            )
        except UserError as error:
            return self._json_response({"success": False, "error": str(error)}, status=error_status)
        except Exception as error:
            _logger.info("Ginlong local simulation request rejected: %s", error)
            return self._json_response({"success": False, "error": str(error)}, status=error_status)

    @http.route(['/ginlong/sim/api01', '/api/ginlong/TPL_Pending_Receipt_Note'], type='http', auth='none', methods=['POST'], csrf=False)
    @validate_token
    @api_logger
    @rate_limit("API01")
    def api01(self, **params):
        return self._dispatch("API01", services.api01)

    @http.route(['/ginlong/sim/api03', '/api/ginlong/TPL_Pending_Delivery_Note'], type='http', auth='none', methods=['POST'], csrf=False)
    @validate_token
    @api_logger
    @rate_limit("API03")
    def api03(self, **params):
        # Ginlong pushes the outbound order into Odoo.
        return self._dispatch("API03", services.api03, error_status=400)

    @http.route(['/ginlong/sim/api05', '/api/ginlong/TPL_Stocktake_Order'], type='http', auth='none', methods=['POST'], csrf=False)
    @validate_token
    @api_logger
    @rate_limit("API05")
    def api05(self, **params):
        return self._dispatch("API05", services.api05)

    @http.route(['/ginlong/sim/api07', '/api/ginlong/TPL_Product_Master'], type='http', auth='none', methods=['POST'], csrf=False)
    @validate_token
    @api_logger
    @rate_limit("API07")
    def api07(self, **params):
        return self._dispatch("API07", services.api07)

    @http.route('/api/ginlong/TPL_Stock_Query', type='http', auth='none', methods=['POST'], csrf=False)
    @validate_token
    @api_logger
    def api09(self, **params):
        try:
            payload = json.loads(request.httprequest.data or b"{}")
            if not isinstance(payload, dict):
                raise ValueError("Request body must be a JSON object")
            result = services.api09(request.env, payload)
            return self._json_response(result)
        except (TypeError, ValueError, UserError) as error:
            return self._json_response({"error": str(error)}, status=400)
        except PG_CONCURRENCY_EXCEPTIONS_TO_RETRY:
            raise
        except Exception as error:
            _logger.exception("Ginlong API09 inventory query failed")
            return self._json_response(
                {"error": "Inventory query failed", "operationTime": fields.Datetime.to_string(fields.Datetime.now())},
                status=500,
            )
