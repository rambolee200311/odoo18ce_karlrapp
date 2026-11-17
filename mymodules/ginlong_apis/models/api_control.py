import logging

from odoo import api, fields, models
from odoo.exceptions import ValidationError


_logger = logging.getLogger(__name__)


class GinlongAPIIdempotency(models.Model):
    _name = "ginlong.api.idempotency"
    _description = "Ginlong API Idempotency Result"
    _order = "id desc"

    api_code = fields.Char(required=True, index=True)
    business_key = fields.Char(required=True, index=True, size=512)
    request_fingerprint = fields.Char(required=True, size=64, index=True)
    response_json = fields.Text(required=True)

    _sql_constraints = [
        (
            "uniq_request",
            "unique(api_code, business_key, request_fingerprint)",
            "This Ginlong API request has already been processed.",
        ),
    ]


class GinlongAPIRateCounter(models.Model):
    _name = "ginlong.api.rate.counter"
    _description = "Ginlong API Rate Counter"
    _order = "window_start desc, id desc"

    api_user_id = fields.Many2one("world.depot.api.user", required=True, index=True, ondelete="cascade")
    api_code = fields.Char(required=True, index=True)
    window_start = fields.Datetime(required=True, index=True)
    request_count = fields.Integer(required=True, default=0)

    _sql_constraints = [
        (
            "uniq_rate_window",
            "unique(api_user_id, api_code, window_start)",
            "The Ginlong API rate window already exists.",
        ),
    ]


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    ginlong_api01_rate_limit = fields.Integer(
        string="Ginlong API01 requests per second", default=10,
        config_parameter="ginlong_apis.api01_rate_limit",
    )
    ginlong_api03_rate_limit = fields.Integer(
        string="Ginlong API03 requests per second", default=10,
        config_parameter="ginlong_apis.api03_rate_limit",
    )
    ginlong_api05_rate_limit = fields.Integer(
        string="Ginlong API05 requests per second", default=10,
        config_parameter="ginlong_apis.api05_rate_limit",
    )
    ginlong_api07_rate_limit = fields.Integer(
        string="Ginlong API07 requests per second", default=100,
        config_parameter="ginlong_apis.api07_rate_limit",
    )

    @api.constrains(
        "ginlong_api01_rate_limit", "ginlong_api03_rate_limit",
        "ginlong_api05_rate_limit", "ginlong_api07_rate_limit",
    )
    def _check_ginlong_rate_limits(self):
        for settings in self:
            if any(value < 1 for value in (
                settings.ginlong_api01_rate_limit,
                settings.ginlong_api03_rate_limit,
                settings.ginlong_api05_rate_limit,
                settings.ginlong_api07_rate_limit,
            )):
                raise ValidationError("Ginlong API rate limits must be positive integers.")

    @api.model
    def get_ginlong_api_rate_limit(self, api_code):
        defaults = {"API01": 10, "API03": 10, "API05": 10, "API07": 100}
        if api_code not in defaults:
            raise ValueError("Unknown Ginlong API code: %s" % api_code)
        key = "ginlong_apis.%s_rate_limit" % api_code.lower()
        value = self.env["ir.config_parameter"].sudo().get_param(key, str(defaults[api_code]))
        try:
            return max(1, int(value))
        except (TypeError, ValueError):
            _logger.error("Invalid Ginlong rate limit configuration for %s; using default", api_code)
            return defaults[api_code]
