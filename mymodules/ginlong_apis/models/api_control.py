"""定义幂等、限流记录及 Ginlong 管理设置。"""

import logging

from odoo import api, fields, models
from odoo.exceptions import ValidationError


_logger = logging.getLogger(__name__)


class GinlongAPIIdempotency(models.Model):
    """保存 Ginlong 请求及回传事件的幂等状态和可复用结果。"""

    _name = "ginlong.api.idempotency"
    _description = "Ginlong API Idempotency Result"
    _order = "id desc"

    api_code = fields.Char(required=True, index=True)
    direction = fields.Selection(
        [("inbound", "Inbound"), ("outbound", "Outbound")],
        required=True, default="inbound", index=True,
    )
    action = fields.Char(index=True)
    business_key = fields.Char(required=True, index=True, size=512)
    event_key = fields.Char(index=True, size=512)
    # stable_event_key 跨不同确认令牌保持不变，供同一业务事件的所有 Worker 共用协调行。
    stable_event_key = fields.Char(index=True, size=64)
    coordination_key = fields.Char(index=True, size=64)
    parent_event_id = fields.Many2one(
        "ginlong.api.idempotency", string="原回传事件", index=True, ondelete="set null",
    )
    # 每个稳定业务事件的每个执行代次只能生成一个发送尝试，跨用户/标签页共用此唯一槽位。
    execution_slot = fields.Char(index=True, size=64, readonly=True)
    confirmation_token = fields.Char(index=True, size=64)
    confirmed_by_id = fields.Many2one("res.users", string="重复回传确认人", readonly=True)
    confirmed_at = fields.Datetime(string="重复回传确认时间", readonly=True)
    legacy_api_log_id = fields.Many2one(
        "world.depot.api.log", string="历史成功日志", readonly=True, ondelete="set null",
    )
    execution_generation = fields.Integer(default=0, readonly=True)
    active_execution = fields.Boolean(default=False, readonly=True)
    last_started_at = fields.Datetime(readonly=True)
    last_completed_at = fields.Datetime(readonly=True)
    last_outcome_state = fields.Selection(
        [("succeeded", "Succeeded"), ("failed", "Failed"), ("unknown", "Unknown")],
        readonly=True,
    )
    request_fingerprint = fields.Char(required=True, size=64, index=True)
    state = fields.Selection(
        [("processing", "Processing"), ("succeeded", "Succeeded"),
         ("failed", "Failed"), ("unknown", "Unknown")],
        required=True, default="succeeded", index=True,
    )
    attempt_count = fields.Integer(required=True, default=1)
    # 回放缓存只供 sudo 的幂等服务读取；避免管理员通过视图/RPC 读取潜在敏感响应内容。
    response_json = fields.Text(required=True, groups="base.group_no_one")

    _sql_constraints = [
        (
            "uniq_request",
            "unique(api_code, business_key, event_key, request_fingerprint)",
            "This Ginlong API request has already been processed.",
        ),
        (
            "uniq_outbound_coordination",
            "unique(api_code, coordination_key)",
            "This Ginlong business event is already coordinated.",
        ),
        (
            "uniq_outbound_execution_slot",
            "unique(execution_slot)",
            "This Ginlong business event generation already has an execution attempt.",
        ),
        (
            "uniq_confirmation_token",
            "unique(api_code, confirmation_token)",
            "This Ginlong confirmation token has already been consumed.",
        ),
    ]


class GinlongAPIRateCounter(models.Model):
    """在数据库中共享每个 API 用户、接口及固定时间窗口的计数。"""

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
    """在 Odoo 设置页维护入站阈值和五个回传 Endpoint。"""

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
    ginlong_api09_rate_limit = fields.Integer(
        string="Ginlong API09 requests per second", default=10,
        config_parameter="ginlong_apis.api09_rate_limit",
    )
    ginlong_api02_callback_url = fields.Char(string="API02 回传 URL（含 objectid）", config_parameter="ginlong_apis.api02_callback_url")
    ginlong_api04_callback_url = fields.Char(string="API04 回传 URL（含 objectid）", config_parameter="ginlong_apis.api04_callback_url")
    ginlong_api06_callback_url = fields.Char(string="API06 回传 URL（含 objectid）", config_parameter="ginlong_apis.api06_callback_url")
    ginlong_api08_callback_url = fields.Char(string="API08 回传 URL（含 objectid）", config_parameter="ginlong_apis.api08_callback_url")
    ginlong_api10_callback_url = fields.Char(string="API10 回传 URL（含 objectid）", config_parameter="ginlong_apis.api10_callback_url")

    @api.constrains(
        "ginlong_api01_rate_limit", "ginlong_api03_rate_limit",
        "ginlong_api05_rate_limit", "ginlong_api07_rate_limit", "ginlong_api09_rate_limit",
    )
    def _check_ginlong_rate_limits(self):
        """拒绝非正的限流值，避免配置后意外封锁接口或失去限流。"""
        for settings in self:
            if any(value < 1 for value in (
                settings.ginlong_api01_rate_limit,
                settings.ginlong_api03_rate_limit,
                settings.ginlong_api05_rate_limit,
                settings.ginlong_api07_rate_limit,
                settings.ginlong_api09_rate_limit,
            )):
                raise ValidationError("Ginlong API rate limits must be positive integers.")

    @api.model
    def get_ginlong_api_rate_limit(self, api_code):
        """读取一个 Ginlong 入站 API 的限流阈值并处理无效配置。

        参数：
            api_code: API01、API03、API05、API07 或 API09。

        返回：
            大于等于 1 的请求/秒整数；配置损坏时使用该接口默认值。
        """
        defaults = {"API01": 10, "API03": 10, "API05": 10, "API07": 100, "API09": 10}
        if api_code not in defaults:
            raise ValueError("Unknown Ginlong API code: %s" % api_code)
        key = "ginlong_apis.%s_rate_limit" % api_code.lower()
        value = self.env["ir.config_parameter"].sudo().get_param(key, str(defaults[api_code]))
        try:
            return max(1, int(value))
        except (TypeError, ValueError):
            _logger.error("Invalid Ginlong rate limit configuration for %s; using default", api_code)
            return defaults[api_code]

    @api.model
    def get_ginlong_callback_endpoint(self, api_code):
        """读取指定人工回传 API 的管理员配置 URL。

        参数：
            api_code: API02、API04、API06、API08 或 API10。

        返回：
            包含去除首尾空格后 URL 的字典；未配置时 URL 为空字符串。
        """
        if api_code not in {"API02", "API04", "API06", "API08", "API10"}:
            raise ValueError("Unknown Ginlong callback API code: %s" % api_code)
        params = self.env["ir.config_parameter"].sudo()
        prefix = "ginlong_apis.%s_callback_" % api_code.lower()
        return {
            "url": params.get_param(prefix + "url", "").strip(),
        }
