"""提供 Ginlong API 共用、由配置驱动的错误码和消息模板。"""

import json
import re
from collections import defaultdict
from functools import lru_cache
from pathlib import Path

from odoo.exceptions import UserError


_SECRET_ASSIGNMENT = re.compile(
    r"(?i)\b(api[_-]?secret|api[_-]?key|access[_-]?token|token|password|authorization)\b\s*[:=]\s*[^\s,;]+"
)
_BEARER_CREDENTIAL = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/-]+=*")
_CONTROL_CHARACTERS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def _sanitize_error_text(value, collapse_lines=False):
    """清理错误文本中的控制字符和凭据，避免响应或日志暴露敏感值。"""
    text = str(value if value is not None else "")
    text = _SECRET_ASSIGNMENT.sub(lambda match: "%s=[已隐藏]" % match.group(1), text)
    text = _BEARER_CREDENTIAL.sub("Bearer [已隐藏]", text)
    text = _CONTROL_CHARACTERS.sub(" ", text)
    if collapse_lines:
        text = re.sub(r"\s+", " ", text)
    return text.strip()


def _required_error_summary(details):
    """把必填校验明细压缩为短字段路径列表，避免协议长度截断字段名。"""
    issues = [item.strip() for item in str(details or "").split(";") if item.strip()]
    missing = []
    empty = []
    other = []
    for issue in issues:
        if issue.endswith(" is missing"):
            missing.append(issue[:-len(" is missing")])
        elif issue.endswith(" is empty"):
            empty.append(issue[:-len(" is empty")])
        else:
            other.append(issue)

    groups = []
    if missing:
        groups.append("缺失字段: " + ", ".join(missing))
    if empty:
        groups.append("空值字段: " + ", ".join(empty))
    if other:
        groups.append("字段错误: " + "; ".join(other))
    return "; ".join(groups) or ("必填字段错误: " + str(details))


def _type_error_summary(details):
    """从完整类型诊断提取字段路径，给协议响应生成紧凑字段清单。"""
    issues = [item.strip() for item in str(details or "").split(";") if item.strip()]
    field_names = [issue.split(None, 1)[0] for issue in issues]
    return "类型错误字段: " + ", ".join(field_names) if field_names else ""


@lru_cache(maxsize=1)
def get_error_catalog():
    """读取静态错误目录，供所有 Ginlong API 共用。"""
    path = Path(__file__).resolve().parent / "data" / "error_codes.json"
    with path.open(encoding="utf-8") as catalog_file:
        return json.load(catalog_file)


class GinlongAPIError(UserError):
    """携带稳定错误码、对外消息及内部诊断信息的 Ginlong 错误。"""

    def __init__(self, error_code, **context):
        """按统一目录生成消息，并保留日志所需诊断信息。

        参数：
            error_code: `error_codes.json` 中定义的稳定错误码。
            context: 消息模板可引用的安全上下文值。
        """
        definition = get_error_catalog().get("errors", {}).get(error_code)
        if not definition:
            raise ValueError("Unknown Ginlong API error code: %s" % error_code)
        self.error_code = error_code
        if error_code == "REQ01":
            # 报文响应优先列出紧凑字段路径，完整校验明细仍保存在 API 日志诊断列。
            supplied_details = _sanitize_error_text(context.get("details"), collapse_lines=True)
            context["details"] = supplied_details
            context["summary"] = (
                _required_error_summary(supplied_details)
                if supplied_details else definition.get("fallback_message", "必填字段校验失败")
            )
        elif error_code == "TYP01":
            # 类型错误响应列出全部字段路径；完整原因仍保存在诊断日志中。
            supplied_details = _sanitize_error_text(context.get("details"), collapse_lines=True)
            context["details"] = supplied_details
            context["summary"] = (
                _type_error_summary(supplied_details)
                if supplied_details else definition.get("fallback_message", "字段类型校验失败")
            )
        if error_code == "BUS01":
            # BUS01 使用 Odoo 的业务异常文本作为安全消息；空消息保留目录配置的通用兜底。
            supplied_message = _sanitize_error_text(context.get("message"), collapse_lines=True)
            context["message"] = supplied_message or definition.get(
                "fallback_message", "业务处理失败",
            )
        template_values = defaultdict(str, context)
        self.public_message = _sanitize_error_text(
            definition["message"].format_map(template_values), collapse_lines=True,
        )
        self.diagnostic_message = _sanitize_error_text(
            definition.get("diagnostic", "").format_map(template_values),
        )
        self.exception_info = self._format_exception_info()
        super().__init__(self.exception_info)

    def _format_exception_info(self):
        """生成符合 Ginlong V3.2 长度限制的 `ErrorCode: ErrorMsg` 字符串。"""
        max_length = int(get_error_catalog().get("exception_info_max_length", 40))
        prefix = "%s: " % self.error_code
        message_budget = max(0, max_length - len(prefix))
        if self.error_code in {"REQ01", "TYP01"}:
            labels = (
                ("缺失字段: ", "空值字段: ", "类型错误字段: ")
                if self.error_code == "REQ01"
                else ("类型错误字段: ",)
            )
            for label in labels:
                if not self.public_message.startswith(label):
                    continue
                # 只在完整字段名边界上截取；剩余字段用省略号表示，完整清单仍保留在日志诊断中。
                first_group, separator, remaining_groups = self.public_message.partition("; ")
                names = [name.strip() for name in first_group[len(label):].split(", ") if name.strip()]
                names_budget = max(0, message_budget - len(label))
                selected = []
                omitted = bool(separator)
                for index, name in enumerate(names):
                    candidate = ", ".join(selected + [name])
                    more_names = index < len(names) - 1
                    reserve = len(", ...") if more_names or omitted else 0
                    if len(candidate) + reserve > names_budget:
                        omitted = True
                        break
                    selected.append(name)
                if len(selected) < len(names):
                    omitted = True
                compact_names = ", ".join(selected)
                if omitted:
                    compact_names = (compact_names + ", " if compact_names else "") + "..."
                return prefix + label + compact_names
        if len(self.public_message) <= message_budget:
            return prefix + self.public_message

        # 先保留错误类型及其后的完整字段/属性名，再用省略号提示消息还有内容。
        # BUS01 的动态产品码、SN 等值只保留到完整逗号分隔项边界；详细值仍在日志中。
        issue_label, separator, remainder = self.public_message.partition(": ")
        if separator:
            head = issue_label + ": "
            remaining_budget = max(0, message_budget - len(head))
            if len(head) >= message_budget:
                return prefix + self.public_message[:max(0, message_budget - 3)] + "..."
            selected = []
            for item in remainder.split(", "):
                candidate = ", ".join(selected + [item])
                suffix = ", ..." if len(candidate) < len(remainder) else ""
                if len(candidate) + len(suffix) > remaining_budget:
                    break
                selected.append(item)
            shortened = ", ".join(selected)
            if len(shortened) < len(remainder):
                shortened = (shortened + ", " if shortened else "") + "..."
            return prefix + head + shortened
        return prefix + self.public_message[:max(0, message_budget - 3)] + "..."

    def to_log_values(self):
        """返回 API 日志字段；错误码、消息和诊断分别保存。"""
        return {
            "code": self.error_code,
            "message": self.public_message,
            "details": self.diagnostic_message,
            "exception_info": self.exception_info,
        }


def make_error(error_code, **context):
    """按配置目录构造可由 Odoo 控制器捕获的统一错误。"""
    return GinlongAPIError(error_code, **context)
