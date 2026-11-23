"""按契约顺序协调独立的必填字段与字段类型校验器。"""

from .required_validator import RequiredFieldError, validate_required
from .type_validator import FieldTypeValidationError, validate_field_types


def validate_payload(api_code, payload, direction="request"):
    """先检查全部必填字段，再检查类型，并保留两类错误诊断。

    参数：
        api_code: Ginlong API 编号。
        payload: 请求或响应对象；不会被修改。
        direction: request 检查 O 列，response 检查 V 列。

    返回：
        两项校验均通过时返回 None。

    异常：
        RequiredFieldError: 有必填问题时优先抛出，并附带同时发现的类型错误路径。
        FieldTypeValidationError: 必填校验通过但存在类型问题时抛出。
    """
    required_error = None
    try:
        validate_required(api_code, payload, direction=direction)
    except RequiredFieldError as error:
        required_error = error

    type_error = None
    try:
        validate_field_types(api_code, payload, direction=direction)
    except FieldTypeValidationError as error:
        type_error = error

    # 按既定顺序优先报告必填问题；类型检查仍在 ORM 前完成，便于日志保留完整诊断。
    if required_error:
        required_error.related_type_issues = type_error.issues if type_error else ()
        if type_error:
            # 回传 Wizard 和 API 日志也读取异常文本；同时保留类型诊断，但不改变必填错误优先级。
            required_error.args = (
                "%s; Type errors: %s" % (
                    str(required_error), "; ".join(type_error.issues),
                ),
            )
        raise required_error
    if type_error:
        raise type_error
