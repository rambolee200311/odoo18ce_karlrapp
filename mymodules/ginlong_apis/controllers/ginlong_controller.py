import json
import logging

from odoo import http
from odoo.http import request
from odoo.addons.worlddepot.controllers.api_logs import api_logger
from odoo.addons.worlddepot.controllers.validator_token import validate_token

from .. import services

_logger = logging.getLogger(__name__)


class GinlongSimulationController(http.Controller):
    """Local simulation endpoints; not Ginlong's confirmed production routes."""

    def _dispatch(self, handler):
        try:
            payload = json.loads(request.httprequest.data or b"{}")
            if not isinstance(payload, dict):
                return {"success": False, "error": "Request body must be a JSON object"}
            api_user = getattr(request, "api_user", False)
            return handler(request.env, api_user, payload)
        except (TypeError, ValueError) as error:
            return {"success": False, "error": "Invalid JSON request: %s" % error}
        except Exception as error:
            _logger.info("Ginlong local simulation request rejected: %s", error)
            return {"success": False, "error": str(error)}

    @http.route('/ginlong/sim/api01', type='json', auth='none', methods=['POST'], csrf=False)
    @validate_token
    @api_logger
    def api01(self, **params):
        return self._dispatch(services.api01)

    @http.route('/ginlong/sim/api03', type='json', auth='none', methods=['POST'], csrf=False)
    @validate_token
    @api_logger
    def api03(self, **params):
        # API03 remains the local A-003 Solis -> Odoo development assumption.
        return self._dispatch(services.api03)

    @http.route('/ginlong/sim/api05', type='json', auth='none', methods=['POST'], csrf=False)
    @validate_token
    @api_logger
    def api05(self, **params):
        return self._dispatch(services.api05)

    @http.route('/ginlong/sim/api07', type='json', auth='none', methods=['POST'], csrf=False)
    @validate_token
    @api_logger
    def api07(self, **params):
        return self._dispatch(services.api07)
