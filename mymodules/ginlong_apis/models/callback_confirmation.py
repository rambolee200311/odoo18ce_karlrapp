"""为 Ginlong 出站回传提供一次性通用重复确认向导。"""

import json
import uuid

from odoo import _, fields, models
from odoo.exceptions import AccessError, UserError


class GinlongCallbackConfirmation(models.TransientModel):
    """确认 API02/04/06/08 的重复或结果未知回传；不保存业务 Payload。"""

    _name = "ginlong.api.callback.confirmation"
    _description = "Ginlong Callback Confirmation"

    api_code = fields.Selection(
        [(code, code) for code in ("API02", "API04", "API06", "API08")],
        required=True, readonly=True,
    )
    source_record = fields.Reference(
        selection=[
            ("world.depot.inbound.order", "入库单"),
            ("world.depot.outbound.order", "出库单"),
        ],
        required=True, readonly=True,
    )
    event_summary = fields.Text(string="本次回传对象", readonly=True)
    history_summary = fields.Text(string="历史回传结果", readonly=True)
    event_snapshots = fields.Text(required=True, readonly=True)
    confirmation_token = fields.Char(required=True, default=lambda self: uuid.uuid4().hex, readonly=True)
    scope = fields.Selection(
        [("unsuccessful", "仅回传未成功项"), ("all", "回传全部"), ("cancel", "取消")],
        required=True, default="unsuccessful",
    )
    multi_event = fields.Boolean(readonly=True)
    has_unknown = fields.Boolean(readonly=True)
    confirm_unknown = fields.Boolean(string="我确认结果未知的请求可能已被锦浪处理，仍要重试")
    consumed = fields.Boolean(default=False, readonly=True)

    def _source_order(self):
        """解析并校验向导所引用的入库或出库订单。"""
        self.ensure_one()
        order = self.source_record.exists() if self.source_record else False
        if not order:
            raise UserError(_("回传来源单据已不存在，请重新打开业务单据操作。"))
        if self.create_uid != self.env.user and not self.env.user.has_group("base.group_system"):
            raise AccessError(_("只能处理由当前用户创建的回传确认。"))
        return order

    def action_confirm(self):
        """重新读取当前业务数据，消费一次性确认并执行符合范围的事件。"""
        self.ensure_one()
        if self.consumed:
            return self._notification(_("该确认已使用，本次没有重复发送。"), success=False)
        order = self._source_order()
        self.write({"consumed": True})

        if self.scope == "cancel":
            from .ginlong_callbacks import _callback_chatter
            _callback_chatter(order, self.api_code, "取消回传", self.scope, self._snapshot_labels())
            return self._notification(_("已取消，本次没有发送 HTTP 请求。"), success=False)

        from .. import idempotency
        from .ginlong_callbacks import (
            _callback_candidates,
            _callback_confirmation_action,
            _process_confirmable_callbacks,
        )

        try:
            order.env.flush_all()
            candidates = _callback_candidates(order, self.api_code)
            candidates = [candidate for candidate in candidates if not candidate.get("error")]
            saved = json.loads(self.event_snapshots or "[]")
            snapshot_by_key = {item["stable_key"]: item for item in saved}
            current_candidates = []
            current_states = []
            # API04 只处理打开确认时列出的 Picking；新完成的批次留给下一次按钮操作。
            for candidate in candidates:
                current = idempotency.inspect_callback_event(
                    order.env, self.api_code, candidate["payload"], candidate["context"],
                    candidate["source"], invoked_at=idempotency.callback_now(),
                )
                old = snapshot_by_key.get(current["stable_key"])
                if not old:
                    continue
                current_candidates.append(candidate)
                current_states.append(current)

            if not current_candidates:
                return self._notification(_("确认中的回传对象已变化或不存在，请重新打开业务单据操作。"), success=False)

            # 如果确认期间相同 Payload 已由另一用户成功发送，重新弹出当前状态确认，
            # 不沿用旧令牌，也不把先前确认扩展到新的成功事件。
            stale_success = False
            for candidate, current in zip(current_candidates, current_states):
                old = snapshot_by_key[current["stable_key"]]
                if current["state"] in {"succeeded", "unknown"} and (
                    current["fingerprint"] != old["fingerprint"]
                    or current.get("generation", 0) != old.get("generation", 0)
                ):
                    stale_success = True
            if stale_success:
                return _callback_confirmation_action(
                    order, self.api_code, current_candidates, current_states,
                )

            return _process_confirmable_callbacks(
                order,
                self.api_code,
                order.env["res.config.settings"].get_ginlong_callback_endpoint(self.api_code)["url"],
                current_candidates,
                idempotency.callback_now(),
                selection="all" if not self.multi_event else self.scope,
                snapshots=saved,
                confirmation_token=self.confirmation_token,
                include_unknown=self.confirm_unknown,
                user_id=self.env.user.id,
            )
        except Exception as exc:
            return self._notification(str(exc), success=False)

    def action_cancel(self):
        """消费并取消本次确认，只写来源 Chatter，不发送 HTTP。"""
        self.ensure_one()
        if self.consumed:
            return self._notification(_("该确认已使用，本次没有发送。"), success=False)
        order = self._source_order()
        self.write({"consumed": True})
        from .ginlong_callbacks import _callback_chatter
        _callback_chatter(order, self.api_code, "取消回传", self.scope, self._snapshot_labels())
        return self._notification(_("已取消，本次没有发送 HTTP 请求。"), success=False)

    def _snapshot_labels(self):
        """安全提取本次向导摘要中的业务对象名称。"""
        self.ensure_one()
        try:
            return [item.get("label", "") for item in json.loads(self.event_snapshots or "[]")]
        except (TypeError, ValueError):
            return [self.source_record.display_name if self.source_record else ""]

    @staticmethod
    def _notification(message, success):
        """关闭确认弹窗并显示发送结果。"""
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Ginlong 回传确认"),
                "message": message,
                "type": "success" if success else "warning",
                "sticky": True,
                "next": {"type": "ir.actions.act_window_close"},
            },
        }
