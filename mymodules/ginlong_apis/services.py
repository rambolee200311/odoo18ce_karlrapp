"""将 Ginlong API 报文映射到现有 WorldDepot 订单、产品及 Odoo 库存数据。

接口动作先按已提供的契约规范化，再进入幂等指纹计算；本模块只承担映射，
不把订单接收当成仓库实际执行，也不在盘点指令处理中修改库存。
"""

import json
import math
from decimal import Decimal, InvalidOperation

from odoo import Command, fields
from odoo.exceptions import ValidationError
from odoo.tools.float_utils import float_compare, float_round

from .errors import make_error
from .idempotency import has_successful_once_for_business_key
from .product_identity import ginlong_internal_code
from .validators.payload_validator import validate_payload


_INBOUND_ACTIONS = {
    "API01": {"add": ("CREATE", "Add"), "del": ("DELETE", "Del")},
    "API03": {"add": ("CREATE", "Add"), "del": ("DELETE", "Del"), "edit": ("UPDATE", "Edit")},
    "API05": {"add": ("CREATE", "Add"), "del": ("DELETE", "Del"), "edit": ("UPDATE", "Edit")},
    "API07": {"add": ("CREATE", "Add"), "edit": ("UPDATE", "Edit")},
}
_LOCAL_ACTIONS = {
    **_INBOUND_ACTIONS,
    # API01 的本地兼容路由仍保留先前批准的 Edit；Ginlong 正式路由只接受资料列出的 Add/Del。
    "API01": {
        **_INBOUND_ACTIONS["API01"],
        "edit": ("UPDATE", "Edit"),
    },
}
_LEGACY_ACTIONS = {
    "create": "add",
    "delete": "del",
    "update": "edit",
}
_API01_FORECAST_BUSINESS_TYPE = "保税_海外收货入库"


def api01_uses_bonded_forecast_sn(payload):
    """判断 API01 报文是否适用保税入库的 SN 预报规则。

    参数：
        payload: API01 请求对象。

    返回：
        businessType 精确等于已确认保税入库值时返回 True。
    """
    return payload.get("businessType") == _API01_FORECAST_BUSINESS_TYPE


def normalize_inbound_action(api_code, payload, strict=True):
    """校验并规范化入站 Action，保证相同语义使用稳定的幂等指纹。

    参数：
        api_code: 入站接口编号。
        payload: 原始 JSON 对象。
        strict: True 时按 Ginlong 正式路由动作表校验；False 时兼容本地旧别名。

    返回：
        含规范 Action 拼写的 payload 副本，不修改调用方对象。
    """
    actions_by_api = _INBOUND_ACTIONS if strict else _LOCAL_ACTIONS
    if api_code not in actions_by_api:
        raise ValidationError("Unsupported Ginlong inbound API: %s" % api_code)
    raw_action = payload.get("action")
    if not isinstance(raw_action, str):
        raise ValidationError("%s action must be a string" % api_code)
    action_key = raw_action.strip().casefold()
    action_entry = actions_by_api[api_code].get(action_key)
    if not action_entry and not strict:
        action_key = _LEGACY_ACTIONS.get(action_key, action_key)
        action_entry = actions_by_api[api_code].get(action_key)
    if not action_entry:
        allowed = ", ".join(action[1] for action in actions_by_api[api_code].values())
        raise ValidationError("%s action must be one of: %s" % (api_code, allowed))
    normalized = dict(payload)
    normalized["action"] = action_entry[1]
    return normalized


def _inbound_action(api_code, payload):
    """返回兼容本地路由的内部动作和对外动作名称。"""
    normalized = normalize_inbound_action(api_code, payload, strict=False)
    external_action = normalized["action"]
    internal_action = next(
        value[0] for value in _LOCAL_ACTIONS[api_code].values()
        if value[1] == external_action
    )
    return internal_action, external_action


def _number(value, field_name):
    """将已通过 DECIMAL 校验的数值或数字字符串映射为 Odoo Float。"""
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise ValidationError("%s must be a decimal number or numeric string" % field_name)
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValidationError("%s must be a decimal number or numeric string" % field_name)
    if not math.isfinite(number):
        raise ValidationError("%s must be finite" % field_name)
    return number


def _decimal_quantity(value, field_name):
    """以十进制精度读取数量，避免汇总比较时引入二进制浮点误差。"""
    _number(value, field_name)
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise ValidationError("%s must be a decimal number" % field_name)


def _short_sn_locator(value, max_length):
    """为 40 字符协议错误响应生成可定位的短编码，完整值仍写入日志。"""
    text = str(value or "-")
    if len(text) <= max_length:
        return text
    return "…" + text[-(max_length - 1):]


def _validate_sn_consistency(
    api_code, details, sn_list, products_by_code, sn_required_fields,
    allow_missing_non_serial_allocations=False,
):
    """校验订单明细与 SN 清单的产品、数量和重复编号关系。

    参数：
        api_code: 当前入站接口编号（API01 或 API05）。
        details: 当前请求的产品明细。
        sn_list: 请求中的 SN 清单；None 表示未提供，空列表表示已提供但无记录。
        products_by_code: 按当前货主和 productCode 解析出的 Odoo 产品变体。
        sn_required_fields: 当一条 SN 记录已出现时，为执行一致性检查必须提供的字段。
        allow_missing_non_serial_allocations: True 时允许非 SN 管理产品在完全没有分托行时只保留总量；
            仅 API01 保税入库预报使用，API05 保持既有规则。

    返回：
        按 productCode 分组的有效 SN 原始记录，不修改任何输入对象。

    异常：
        GinlongAPIError: SN 缺失、字段不全、产品不匹配、数量不符或同产品重复 SN。

    说明：
        SN 管理产品的重复仅在本次请求内按 (productCode, productSN) 判断，托盘不属于身份键。
        非 SN 原材料使用 productSN=productCode 表达托盘物料汇总行；同一编码可跨托盘重复，
        数量按产品汇总与 details.quantity 对账。API01/API05 不执行跨单据查重。
    """
    details_by_code = {}
    issues = []
    for index, detail in enumerate(details or []):
        product_code = detail.get("productCode")
        if not product_code:
            # 通用 Required Validator 会先拦住该情况；保留服务入口防御以覆盖非 HTTP 调用。
            issues.append((
                "明细产品缺失: details.productCode",
                "API%s details[%s].productCode is missing" % (api_code, index),
            ))
            continue
        product = products_by_code.get(product_code)
        if not product:
            continue
        details_by_code.setdefault(product_code, {
            "quantity": Decimal("0"),
            "tracking": product.tracking,
        })["quantity"] += _decimal_quantity(
            detail.get("quantity"), "API%s details[%s].quantity" % (api_code, index),
        )

    sn_by_code = {}
    seen_serials = set()
    for index, serial in enumerate(sn_list or []):
        if not isinstance(serial, dict):
            issues.append((
                "SN记录格式错误: snList",
                "API%s snList[%s] must be an object" % (api_code, index),
            ))
            continue
        missing_fields = []
        for field_name in sn_required_fields:
            value = serial.get(field_name)
            if value is None or (isinstance(value, str) and not value.strip()):
                missing_fields.append(field_name)
        if missing_fields:
            for field_name in missing_fields:
                issues.append((
                    "SN字段缺失: snList.%s" % field_name,
                    "API%s snList[%s].%s is required for SN consistency; productCode=%s, productSN=%s"
                    % (api_code, index, field_name, serial.get("productCode"), serial.get("productSN")),
                ))
            continue

        product_code = serial["productCode"]
        if product_code not in details_by_code:
            issues.append((
                "SN产品不匹配: snList.productCode=%s" % product_code,
                "API%s snList[%s].productCode=%s is absent from details" % (
                    api_code, index, product_code,
                ),
            ))
            continue

        serial_number = serial["productSN"]
        serial_managed = details_by_code[product_code]["tracking"] == "serial"
        if serial_managed:
            # 真正的 SN 以 (productCode, productSN) 标识；托盘不同也不能重复。
            duplicate_key = (product_code, serial_number)
            if duplicate_key in seen_serials:
                issues.append((
                    "SN重复: snList.productSN=%s" % serial_number,
                    "API%s duplicate productSN=%s for productCode=%s" % (
                        api_code, serial_number, product_code,
                    ),
                ))
            else:
                seen_serials.add(duplicate_key)
        elif serial_number != product_code:
            # 原材料的 productSN 是产品编码标识，不是单件序列号，允许按托盘拆分数量。
            issues.append((
                "非SN行productSN须等于productCode",
                "API%s non-serial material productSN=%s must equal productCode=%s; palletCode=%s"
                % (api_code, serial_number, product_code, serial.get("palletCode") or "-"),
            ))
            continue

        try:
            serial_quantity = _decimal_quantity(
                serial["quantity"], "API%s snList[%s].quantity" % (api_code, index),
            )
        except ValidationError as error:
            issues.append((
                "SN数量格式错误: snList.quantity",
                str(error),
            ))
            continue
        if serial_managed and serial_quantity != Decimal("1"):
            # 一条 productSN 代表一件实物；总量相等不能替代逐条校验。
            # 协议 exceptionInfo 最多 40 字符，响应显示产品码和托盘码尾部，完整值留给 API 日志。
            public_locator = "SN数量≠1 P=%s T=%s" % (
                _short_sn_locator(product_code, 12),
                _short_sn_locator(serial.get("palletCode"), 9),
            )
            issues.append((
                public_locator,
                "API%s snList[%s].quantity=%s; each SN row must equal 1; "
                "productCode=%s, productSN=%s, palletCode=%s"
                % (
                    api_code, index, serial_quantity, product_code, serial_number,
                    serial.get("palletCode") or "-",
                ),
            ))
        serial_by_product = sn_by_code.setdefault(product_code, {
            "quantity": Decimal("0"),
            "records": [],
        })
        serial_by_product["quantity"] += serial_quantity
        serial_by_product["records"].append(serial)

    if sn_list is None:
        for product_code, product_data in details_by_code.items():
            if product_data["quantity"] != 0:
                if product_data["tracking"] == "serial":
                    issues.append((
                        "SN清单缺失: productCode=%s" % product_code,
                        "API%s serial-tracked productCode=%s requires snList" % (
                            api_code, product_code,
                        ),
                    ))
                elif not allow_missing_non_serial_allocations:
                    issues.append((
                        "原材料托盘明细缺失: productCode=%s" % product_code,
                        "API%s non-serial productCode=%s requires pallet allocations in snList" % (
                            api_code, product_code,
                        ),
                    ))
    else:
        for product_code, product_data in details_by_code.items():
            serial_data = sn_by_code.get(product_code)
            serial_quantity = serial_data["quantity"] if serial_data else Decimal("0")
            has_serial_rows = bool(serial_data and serial_data["records"])
            if not has_serial_rows and product_data["quantity"] != 0:
                if product_data["tracking"] == "serial":
                    issues.append((
                        "SN记录缺失: productCode=%s" % product_code,
                        "API%s serial-tracked productCode=%s quantity=%s has no SN rows"
                        % (api_code, product_code, product_data["quantity"]),
                    ))
                elif not allow_missing_non_serial_allocations:
                    issues.append((
                        "原材料托盘明细缺失: productCode=%s" % product_code,
                        "API%s non-serial productCode=%s quantity=%s has no pallet allocation rows"
                        % (api_code, product_code, product_data["quantity"]),
                    ))
            if (
                (has_serial_rows or not allow_missing_non_serial_allocations)
                and serial_quantity != product_data["quantity"]
            ):
                # 所有产品都按 productCode 汇总核对，原材料的每行 quantity 是对应托盘实物数。
                issues.append((
                    "SN数量不一致: quantity, productCode=%s" % product_code,
                    "API%s productCode=%s details.quantity=%s but snList.quantity sum=%s"
                    % (api_code, product_code, product_data["quantity"], serial_quantity),
                ))

    if issues:
        # 对外给出首个明确错误；完整错误集合写入现有 API 日志诊断字段。
        raise make_error(
            "BUS01",
            message=issues[0][0],
            details="; ".join(issue[1] for issue in issues),
        )

    grouped_records = {}
    for product_code, serial_data in sn_by_code.items():
        grouped_records[product_code] = serial_data["records"]
    return grouped_records


def _project(api_user):
    """取得认证 API 用户所属 WMS 项目，未配置时中止业务处理。"""
    project = api_user.project if api_user else False
    if not project:
        raise ValidationError("The authenticated API user has no WMS project")
    return project


def _resolve_ginlong_owner(env, owner_code, create=False):
    """按 Ginlong 货主编码复用或按获批 API01 规则创建联系人档案。

    参数：
        env: 当前 Odoo Environment。
        owner_code: Ginlong 货主编码，不是联系人显示名称。
        create: True 时编码不存在则创建；False 时不存在即报错。

    返回：
        唯一匹配的 `res.partner` 记录。
    """
    if not isinstance(owner_code, str) or not owner_code.strip():
        raise ValidationError("Ginlong owner must be a non-empty owner code")
    partner_model = env["res.partner"].sudo().with_context(active_test=False)
    owners = partner_model.search([("ginlong_owner_code", "=", owner_code)], limit=2)
    if len(owners) > 1:
        raise ValidationError("Ginlong owner code %s is ambiguous" % owner_code)
    if owners:
        return owners
    if not create:
        raise ValidationError("Ginlong owner code %s was not found" % owner_code)

    # 报文只有编码、没有货主名称，因此仅以编码作为新联系人的显示名；唯一约束防止并发重复建档。
    try:
        with env.cr.savepoint():
            return partner_model.create({
                "name": owner_code,
                "ginlong_owner_code": owner_code,
            })
    except Exception:
        # 首次查询后可能已有并发事务创建同码货主；若唯一约束已解决竞争，则重新查询并复用。
        owners = partner_model.search([("ginlong_owner_code", "=", owner_code)], limit=2)
        if len(owners) == 1:
            return owners
        raise


def ensure_api07_add_is_new(env, api_user, payload):
    """拒绝已存在货主与产品编码组合上的重复 API07 Add。

    参数：
        env: 当前 Odoo Environment。
        api_user: 已认证且关联 WMS 项目的 API 用户。
        payload: 已通过字段校验且 Action 已规范化的 API07 请求。

    返回：
        Add 对应组合不存在时返回 None；重复 Add 时抛出统一错误组件生成的 GinlongAPIError。

    此检查在控制器执行通用幂等重放前运行，因此完全相同和内容变化的重复 Add 都会失败；
    Edit 不受影响。归档产品也视为已存在，避免再次创建相同货主产品。
    """
    _project(api_user)
    internal_action, _external_action = _inbound_action("API07", payload)
    if internal_action != "CREATE":
        return

    owner_code = payload["owner"]
    product_code = payload["productCode"]
    existing = env["product.product"].sudo().with_context(active_test=False).search([
        ("ginlong_owner_code", "=", owner_code),
        ("ginlong_product_code", "=", product_code),
    ], limit=1)
    # HVR 重置或历史数据清理可能删除产品却遗留已提交的成功记录；
    # 在通用幂等器按指纹重放旧响应前，仍须按一次性业务键拒绝重复 Add。
    if existing or has_successful_once_for_business_key(env, "API07", payload):
        raise make_error(
            "IDM07",
            owner=owner_code,
            productCode=product_code,
        )


def _find_product(env, product_code, owner_code=None):
    """按 owner + Ginlong 原始 productCode 定位唯一产品变体。

    参数：
        env: 当前 Odoo Environment。
        product_code: 外部原始产品编码。
        owner_code: Ginlong 货主编码；提供时禁止退回跨货主的单字段匹配。

    返回：
        唯一匹配的 `product.product`；找不到或存在歧义时抛出 ValidationError。
    """
    product_model = env["product.product"].sudo()
    if owner_code:
        products = product_model.search([
            ("ginlong_product_code", "=", product_code),
            ("ginlong_owner_code", "=", owner_code),
        ], limit=2)
        if len(products) == 1:
            return products
        if len(products) > 1:
            raise ValidationError(
                "Product code %s is ambiguous for Ginlong owner %s" % (product_code, owner_code)
            )
        raise ValidationError(
            "Product code %s was not found for Ginlong owner %s" % (product_code, owner_code)
        )

    products = product_model.search(
        ["|", ("default_code", "=", product_code), ("barcode", "=", product_code)],
        limit=2,
    )
    if len(products) != 1:
        reason = "not found" if not products else "ambiguous"
        raise ValidationError("Product code %s is %s in the existing WMS product data" % (product_code, reason))
    return products


def _find_one_by_reference(model, project, reference, label):
    """在当前 WMS 项目内按单据编号查找且只接受唯一记录。"""
    records = model.sudo().search([("project", "=", project.id), ("reference", "=", reference)], limit=2)
    if len(records) != 1:
        reason = "not found" if not records else "ambiguous"
        raise ValidationError("%s %s is %s in this WMS project" % (label, reference, reason))
    return records


def api01(env, api_user, payload):
    """把 API01 入库指令映射到现有 Order—托盘—产品三级结构。

    参数：
        env: 当前 Odoo Environment。
        api_user: 已认证且关联 WMS 项目的 API 用户。
        payload: 已规范化的 Ginlong 入库指令。

    返回：
        创建、更新或取消后的订单结果；不会因此创建或过账 Picking。
    """
    project = _project(api_user)
    action, external_action = _inbound_action("API01", payload)
    order_model = env["world.depot.inbound.order"]

    if action == "DELETE":
        order = _find_one_by_reference(order_model, project, payload["inboundOrderNo"], "Inbound order")
        if order.state != "cancel":
            order.write({"state": "cancel"})
        return {"success": True, "data": {"action": external_action, "inboundOrderNo": payload["inboundOrderNo"]}}

    order = False
    if action == "UPDATE":
        order = _find_one_by_reference(order_model, project, payload["inboundOrderNo"], "Inbound order")
    details = payload.get("details")
    lines = []
    product_line_by_code = {}
    products_by_code = {}
    for index, detail in enumerate(details or []):
        product_name = detail["productName"]
        product = _find_product(env, detail["productCode"], payload["owner"])
        products_by_code[detail["productCode"]] = product
        quantity = _number(detail["quantity"], "API01 details[%s].quantity" % index)
        nested_product = {
            "product_id": product.id,
            "quantity": quantity,
            "ginlong_product_code": detail["productCode"],
            "ginlong_product_name": product_name,
            "ginlong_specification_model": detail["specificationModel"],
        }
        lines.append((0, 0, {
            # 保持现有入库单三级明细分组，由 WMS 自身默认值和计算方法处理待执行订单。
            "pallets": 1.0,
            "inbound_order_product_pallet_ids": [(0, 0, nested_product)],
        }))
        product_line_by_code.setdefault(detail["productCode"], []).append(index)

    # 非保税 Add 的 snList 不是业务数据；不解析、不保存，也不让它形成 Order 子记录。
    # Edit 维持原有本地兼容行为，保税 Add 则允许原材料只提交产品总量。
    process_forecast_sn = action != "CREATE" or api01_uses_bonded_forecast_sn(payload)
    sn_list = payload.get("snList") if process_forecast_sn else None
    if process_forecast_sn:
        validated_sn_by_code = _validate_sn_consistency(
            "API01", details, sn_list, products_by_code,
            ("productSN", "quantity", "palletCode", "productCode"),
            allow_missing_non_serial_allocations=(action == "CREATE"),
        )
    else:
        validated_sn_by_code = {}
    serial_values = [[] for _detail in (details or [])]
    for serial_product_code, serial_records in validated_sn_by_code.items():
        target_lines = product_line_by_code.get(serial_product_code, [])
        if not target_lines:
            continue
        # V3.2 的 SN 行只有 productCode，没有明细行 ID；同码分行时归入首个匹配行，汇总校验仍按产品编码执行。
        target_line = target_lines[0]
        for index, serial in enumerate(serial_records):
            serial_number = serial["productSN"]
            serial_quantity = serial["quantity"]
            serial_vals = {
                "serial_number": serial_number,
                "quantity": _number(serial_quantity, "API01 snList[%s].quantity" % index),
                "ginlong_quantity": _number(serial_quantity, "API01 snList[%s].quantity" % index),
                "ginlong_product_code": serial_product_code,
                "ginlong_pallet_code": serial.get("palletCode") or False,
                "ginlong_product_name": serial.get("productName") or serial.get("name") or False,
                "ginlong_specification_model": serial.get("specificationModel") or False,
            }
            serial_values[target_line].append((0, 0, serial_vals))

    for index, line in enumerate(lines):
        line[2]["product_serial_number_ids"] = serial_values[index]

    order_values = {
        "project": project.id,
        "ginlong_owner_id": _resolve_ginlong_owner(env, payload["owner"], create=True).id,
        "warehouse": project.warehouse.id if project.warehouse else False,
        "pick_type": project.inbound_pick_type.id if project.inbound_pick_type else False,
        "reference": payload["inboundOrderNo"],
        "remark": payload.get("remark") or False,
        "ginlong_owner_code": payload["owner"],
        "ginlong_warehouse_code": payload["warehouse"],
        "ginlong_business_type": payload["businessType"],
    }
    if details is not None:
        order_values["inbound_order_product_ids"] = [(5, 0, 0)] + lines
    if sn_list is not None:
        order_values["ginlong_sn_list_json"] = json.dumps(sn_list, ensure_ascii=False)
    if action == "CREATE":
        order_values["inbound_order_product_ids"] = lines
        order = order_model.sudo().create(order_values)
    else:
        order.write(order_values)
    return {"success": True, "data": {"id": order.id, "billno": order.billno, "state": order.state}}


def api03(env, api_user, payload):
    """按 A-003 本地开发假设映射出库指令到现有 WorldDepot Order。

    参数：
        env: 当前 Odoo Environment。
        api_user: 已认证且关联 WMS 项目的 API 用户。
        payload: 已规范化的 Ginlong 出库指令。

    返回：
        创建、更新或取消后的订单结果；所有产品明细必须按货主复合键存在。
    """
    project = _project(api_user)
    action, external_action = _inbound_action("API03", payload)
    order_model = env["world.depot.outbound.order"]

    if action == "DELETE":
        order = _find_one_by_reference(order_model, project, payload["outboundOrderNo"], "Outbound order")
        if order.state != "cancel":
            order.write({"state": "cancel"})
        return {"success": True, "data": {"action": external_action, "outboundOrderNo": payload["outboundOrderNo"]}}

    order = False
    if action == "UPDATE":
        order = _find_one_by_reference(order_model, project, payload["outboundOrderNo"], "Outbound order")
    owner = _resolve_ginlong_owner(env, payload["owner"])
    details = payload.get("details")
    if action == "UPDATE" and details is None:
        # 仅修改表头时也要检查旧明细，避免更换货主后遗留其他货主的产品变体。
        for existing_line in order.outbound_order_product_ids:
            existing_product = existing_line.product_id
            matched_product = _find_product(
                env, existing_product.ginlong_product_code, payload["owner"],
            )
            if matched_product != existing_product:
                raise ValidationError(
                    "Existing product %s on outbound order %s does not match Ginlong owner %s"
                    % (existing_product.ginlong_product_code, payload["outboundOrderNo"], payload["owner"])
                )
    customer_name = payload.get("customer")
    customers = False
    if customer_name:
        partner_model = env["res.partner"].sudo().with_context(active_test=False)
        customers = partner_model.search([
            ("name", "=", customer_name),
            "|", ("source_project_id", "=", project.id), ("source_project_id", "=", False),
        ], limit=2)
        if len(customers) != 1:
            reason = "not found" if not customers else "ambiguous"
            raise ValidationError("Customer %s is %s in the existing WMS recipient data" % (customer_name, reason))
    else:
        # Ginlong V3.2 将 customer 标为非必填；当前 WMS Order 仍要求 unload_company。
        # 报文未提供 customer 时，仅复用该项目唯一的既有收货方，不猜测名称或新建联系人。
        partner_model = env["res.partner"].sudo().with_context(active_test=False)
        customers = partner_model.search([("source_project_id", "=", project.id)], limit=2)
        if len(customers) != 1:
            reason = "not found" if not customers else "ambiguous"
            raise ValidationError(
                "Ginlong customer is optional, but API03 cannot resolve one existing project recipient (%s)"
                % reason
            )
        customer_name = customers.name

    order_lines = []
    line_numeric = [
        "net_wt_machine", "net_wt_total", "pack_qty", "pallet_qty", "pallet_len",
        "pallet_wid", "pallet_hgt", "unit_vol", "pack_wt", "pallet_total_wt", "total_vol",
        "carton_wt_total", "gross_wt_total",
    ]
    for index, detail in enumerate(details or []):
        product = _find_product(env, detail["productCode"], payload["owner"])
        values = {
            "product_id": product.id,
            "quantity": _number(detail["quantity"], "API03 details[%s].quantity" % index),
            "pallets": _number(detail["pallet_qty"], "API03 details[%s].pallet_qty" % index),
            "ginlong_product_name": detail["productName"],
            "ginlong_specification_model": detail["specificationModel"],
        }
        for field_name in line_numeric:
            values["ginlong_" + field_name] = _number(detail[field_name], "API03 details[%s].%s" % (index, field_name))
        for field_name in ["order_no", "unit", "standard", "pack_mode"]:
            if field_name in detail and detail[field_name] is not None:
                values["ginlong_" + field_name] = detail[field_name]
        order_lines.append((0, 0, values))

    order_values = {
        "project": project.id,
        "ginlong_owner_id": owner.id,
        "warehouse": project.warehouse.id if project.warehouse else False,
        "pick_type": project.outbound_pick_type.id if project.outbound_pick_type else False,
        "reference": payload["outboundOrderNo"],
        "remark": payload.get("remark") or False,
        "delivery_street": payload.get("address") or False,
        "delivery_email": payload.get("contactEmail") or False,
        "ginlong_owner_code": payload["owner"],
        "ginlong_warehouse_code": payload["warehouse"],
        "ginlong_business_type": payload["businessType"],
        "ginlong_customer": customer_name,
        "ginlong_address": payload.get("address") or False,
        "ginlong_consignee": payload.get("consignee") or False,
        "ginlong_contact": payload.get("contact") or False,
        "ginlong_contact_email": payload.get("contactEmail") or False,
        "ginlong_shipping_method": payload.get("shippingMethod") or False,
    }
    if customers:
        order_values["unload_company"] = customers.id
    if details is not None:
        # outbound_order_id 为必填字段，One2many 的 clear 会先将外键置空并触发数据库约束；
        # Edit 时明确删除旧明细再创建新明细，整个替换仍处于当前订单事务内。
        old_line_commands = [(2, line.id, 0) for line in order.outbound_order_product_ids] if order else []
        order_values["outbound_order_product_ids"] = old_line_commands + order_lines
    if action == "CREATE":
        order_values["outbound_order_product_ids"] = order_lines
        order = order_model.sudo().create(order_values)
    else:
        order.write(order_values)
    return {"success": True, "data": {"id": order.id, "billno": order.billno, "state": order.state}}


def api05(env, api_user, payload):
    """将客户盘点指令保存到 WorldDepot，不读取或写入库存台账。

    参数：
        env: 当前 Odoo Environment。
        api_user: 已认证且关联 WMS 项目的 API 用户。
        payload: Ginlong 盘点指令。

    返回：
        创建、更新或取消后的客户盘点订单信息。
    """
    project = _project(api_user)
    action, external_action = _inbound_action("API05", payload)
    task_model = env["world.depot.stocktake.order"].sudo()

    if action == "DELETE":
        tasks = task_model.search([
            ("project_id", "=", project.id),
            ("count_order_no", "=", payload["countOrderNo"]),
        ], limit=2)
        if len(tasks) != 1:
            reason = "not found" if not tasks else "ambiguous"
            raise ValidationError("Stocktake task %s is %s in this WMS project" % (payload["countOrderNo"], reason))
        if tasks.state != "cancel":
            tasks.write({"state": "cancel"})
        return {"success": True, "data": {"action": external_action, "countOrderNo": payload["countOrderNo"]}}

    details = payload.get("details")
    sn_list = payload.get("snList")
    task = False
    if action == "UPDATE":
        tasks = task_model.search([
            ("project_id", "=", project.id),
            ("count_order_no", "=", payload["countOrderNo"]),
        ], limit=2)
        if len(tasks) != 1:
            reason = "not found" if not tasks else "ambiguous"
            raise ValidationError("Stocktake task %s is %s in this WMS project" % (payload["countOrderNo"], reason))
        task = tasks
    effective_details = details
    effective_sn_list = sn_list
    if task and (details is not None or sn_list is not None):
        # Edit 只提交一侧列表时，另一侧沿用已保存内容并一并校验，避免留下新旧数据不一致。
        effective_details = details if details is not None else task.get_plan_details()
        effective_sn_list = sn_list if sn_list is not None else task.get_plan_sn_list()
    products_by_code = {}
    for index, detail in enumerate(effective_details or []):
        _number(detail["quantity"], "API05 details[%s].quantity" % index)
        products_by_code[detail["productCode"]] = _find_product(
            env, detail["productCode"], payload["owner"],
        )
    if action == "CREATE" or details is not None or sn_list is not None:
        _validate_sn_consistency(
            "API05", effective_details, effective_sn_list, products_by_code,
            ("productSN", "quantity", "palletCode", "productCode", "productName", "specificationModel"),
        )
    for index, serial in enumerate(sn_list or []):
        _number(serial["quantity"], "API05 snList[%s].quantity" % index)

    task_values = {
        "count_order_no": payload["countOrderNo"],
        "project_id": project.id,
        "owner_code": payload["owner"],
        "warehouse_code": payload["warehouse"],
        "remark": payload.get("remark") or False,
    }
    if details is not None:
        task_values["plan_details_json"] = json.dumps(details, ensure_ascii=False)
    if sn_list is not None or action == "CREATE":
        task_values["plan_sn_list_json"] = json.dumps(sn_list or [], ensure_ascii=False)
    if action == "CREATE":
        task = task_model.create(task_values)
    else:
        task.write(task_values)
    return {"success": True, "data": {"id": task.id, "countOrderNo": task.count_order_no}}


def api07(env, api_user, payload):
    """创建或更新共享产品模板，并维护指定货主的 Odoo 原生产品变体。

    参数：
        env: 当前 Odoo Environment。
        api_user: 已认证且关联 WMS 项目的 API 用户。
        payload: Ginlong 产品档案及货主编码。

    返回：
        所属产品变体 ID 和原始 Ginlong productCode。

    决策：
        Add 为新货主复用共享模板时要求共享字段一致；Edit 只接受已有货主产品并更新共享字段。
        `productForm` 是不可跨同码产品变化的模板属性，冲突时在任何写入前拒绝。
    """
    # 服务可被 HTTP 之外的调用方直接使用，因此在业务入口再次防止 Add 覆盖已有产品。
    ensure_api07_add_is_new(env, api_user, payload)
    internal_action, _external_action = _inbound_action("API07", payload)
    owner_code = payload["owner"]
    code = payload["productCode"]
    product_form = payload["productForm"].strip() if isinstance(payload["productForm"], str) else payload["productForm"]
    tracking_by_form = {"原材料": "none", "半成品": "serial", "成品": "serial"}
    if product_form not in tracking_by_form:
        # 对外明确列出已确认的产品形态枚举，便于调用方直接修正报文。
        raise make_error("BUS06", productForm=product_form)

    units = env["uom.uom"].sudo().search([("name", "=", payload["unit"])], limit=2)
    if len(units) > 1:
        raise make_error("BUS05", unit=payload["unit"])
    if not units:
        # Ginlong 未提供单位枚举；新单位放入 Odoo 标准 Unit 类别且因子为 1，不推断换算关系。
        unit_category = env.ref("uom.product_uom_categ_unit")
        reference_unit = env.ref("uom.product_uom_unit")
        units = env["uom.uom"].sudo().create({
            "name": payload["unit"],
            "category_id": unit_category.id,
            "uom_type": "smaller",
            "factor": 1.0,
            "rounding": reference_unit.rounding,
        })

    template_values = {
        "name": payload["productName"],
        "type": "consu",
        "is_storable": True,
        "uom_id": units.id,
        "uom_po_id": units.id,
        "ginlong_specification_model": payload["specificationModel"],
        "ginlong_unit": payload["unit"],
        "ginlong_product_form": product_form,
        "tracking": tracking_by_form[product_form],
    }
    payload_fields = {
        "power": ("ginlong_power", "char"),
        "nationalStandard": ("ginlong_national_standard", "char"),
        "certificationModel": ("ginlong_certification_model", "char"),
        "weight": ("ginlong_weight", "float"),
        "length": ("ginlong_length", "float"),
        "width": ("ginlong_width", "float"),
        "height": ("ginlong_height", "float"),
    }
    for source_name, (target_name, value_type) in payload_fields.items():
        if source_name in payload and payload[source_name] is not None:
            value = payload[source_name]
            if value_type == "float":
                value = _number(value, "API07.%s" % source_name)
            elif value_type == "char":
                value = str(value)
            template_values[target_name] = value

    product_model = env["product.product"].sudo().with_context(active_test=False)
    matching_products = product_model.search([("ginlong_product_code", "=", code)])
    templates = matching_products.mapped("product_tmpl_id")
    if len(templates) > 1:
        raise ValidationError("Ginlong productCode %s belongs to multiple product templates" % code)

    owner_products = product_model.search([
        ("ginlong_owner_code", "=", owner_code),
        ("ginlong_product_code", "=", code),
    ], limit=2)
    if len(owner_products) > 1:
        raise ValidationError("Owner/product key %s/%s is ambiguous in the existing WMS product data" % (owner_code, code))
    if internal_action == "UPDATE" and not owner_products:
        # Edit 只能修改已有业务档案；缺少目标时不得悄悄创建出一个看似成功的新产品。
        raise make_error("BUS03", owner=owner_code, productCode=code)

    internal_code = ginlong_internal_code(owner_code, code)
    code_collisions = product_model.search([("default_code", "=", internal_code)])
    if code_collisions and any(
        product.ginlong_owner_code != owner_code or product.ginlong_product_code != code
        for product in code_collisions
    ):
        raise ValidationError("Internal Ginlong product code collision for owner/product %s/%s" % (owner_code, code))

    # 同一原始 productCode 共用模板；不同 owner 只扩展 Owner 属性并对应独立变体。
    if templates:
        template = templates
        if internal_action == "CREATE":
            mismatches = []
            for field_name, expected in template_values.items():
                actual = template[field_name]
                if field_name in {"ginlong_weight", "ginlong_length", "ginlong_width", "ginlong_height"}:
                    differs = float_compare(float(actual or 0.0), float(expected or 0.0), precision_digits=6) != 0
                elif field_name in {"uom_id", "uom_po_id"}:
                    differs = actual.id != expected
                else:
                    differs = actual != expected
                if differs:
                    mismatches.append(field_name)
            if mismatches:
                if "ginlong_product_form" in mismatches:
                    # 相同 productCode 的 productForm 跨货主必须一致，不能借新增变体改写模板属性。
                    raise make_error(
                        "BUS02",
                        owner=owner_code,
                        productCode=code,
                        fields=", ".join(mismatches),
                    )
                raise ValidationError(
                    "Ginlong productCode %s conflicts with shared product fields: %s"
                    % (code, ", ".join(mismatches))
                )
        elif template.ginlong_product_form != product_form:
            # `productForm` 冲突始终拒绝；其他模板共享属性由已存在产品的 Edit 更新。
            raise make_error(
                "BUS02",
                owner=owner_code,
                productCode=code,
                fields="ginlong_product_form, tracking",
            )
    else:
        template = False

    owner_attribute = env.ref("ginlong_apis.product_attribute_ginlong_owner").sudo()
    attribute_values = env["product.attribute.value"].sudo().search([
        ("attribute_id", "=", owner_attribute.id), ("name", "=", owner_code),
    ], limit=1)
    if not attribute_values:
        attribute_values = env["product.attribute.value"].sudo().create({
            "attribute_id": owner_attribute.id,
            "name": owner_code,
        })

    if not template:
        template = env["product.template"].sudo().create({
            **template_values,
            "attribute_line_ids": [Command.create({
                "attribute_id": owner_attribute.id,
                "value_ids": [Command.set(attribute_values.ids)],
            })],
        })
    else:
        non_owner_lines = template.attribute_line_ids.filtered(
            lambda line: line.attribute_id != owner_attribute
        )
        if non_owner_lines:
            raise ValidationError(
                "Ginlong productCode %s already has non-owner product variants; "
                "owner identity cannot be resolved to one product variant." % code
            )
        owner_line = template.attribute_line_ids.filtered(lambda line: line.attribute_id == owner_attribute)
        if owner_line:
            owner_line.write({"value_ids": [Command.link(attribute_values.id)]})
        else:
            env["product.template.attribute.line"].sudo().create({
                "product_tmpl_id": template.id,
                "attribute_id": owner_attribute.id,
                "value_ids": [Command.set(attribute_values.ids)],
            })

    owner_ptavs = template.attribute_line_ids.filtered(
        lambda line: line.attribute_id == owner_attribute
    ).product_template_value_ids.filtered(
        lambda value: value.product_attribute_value_id == attribute_values
    )
    products = template.product_variant_ids.filtered(
        lambda product: bool(product.product_template_attribute_value_ids & owner_ptavs)
    )
    if len(products) != 1:
        raise ValidationError("Ginlong owner %s does not resolve to exactly one product variant for %s" % (owner_code, code))
    product = products
    if owner_products and owner_products != product:
        raise ValidationError("Owner/product key %s/%s does not match its native product variant" % (owner_code, code))
    if internal_action == "UPDATE":
        # 编辑已有 Owner 变体时更新其共享模板，所有同 productCode 货主变体继续读取同一套产品属性。
        template.write(template_values)
    product.write({
        "ginlong_owner_code": owner_code,
        "ginlong_product_code": code,
        "default_code": internal_code,
    })
    return {"success": True, "data": {"id": product.id, "productCode": code}}


def api09(env, payload):
    """只读返回指定货主和仓库的实际物理库存。

    参数：
        env: 当前 Odoo Environment。
        payload: 必须含 owner 和 warehouse 编码的请求对象。

    返回：
        按 owner、warehouse 和原始 productCode 隔离的库存清单；不存在编码时不泄露其他库存。

    口径：
        owner 匹配 `res.partner.ginlong_owner_code` 并关联 `stock.quant.owner_id`；
        数量读取物理在手 `quantity`，不扣 `reserved_quantity`，查询不改库存。
    """
    validate_payload("API09", payload, direction="request")

    warehouses = env["stock.warehouse"].sudo().with_context(active_test=False).search(
        [("code", "=", payload["warehouse"])], limit=2
    )
    if len(warehouses) != 1:
        raise ValidationError(
            "API09 warehouse code must match exactly one configured Odoo warehouse"
        )
    warehouse = warehouses
    owners = env["res.partner"].sudo().with_context(active_test=False).search(
        [("ginlong_owner_code", "=", payload["owner"])], limit=2
    )
    if len(owners) > 1:
        raise ValidationError("API09 owner code must match exactly one configured owner")
    if not owners:
        return {
            "returnStatus": "Y",
            "exceptionInfo": "OK",
            "operationTime": fields.Datetime.to_string(fields.Datetime.now()),
            "owner": payload["owner"],
            "warehouse": payload["warehouse"],
            "inventoryList": [],
        }

    quant_model = env["stock.quant"].sudo()
    domain = [
        ("location_id", "child_of", warehouse.view_location_id.id),
        ("location_id.usage", "=", "internal"),
        ("owner_id", "=", owners.id),
        ("product_id.ginlong_product_code", "!=", False),
    ]
    grouped = quant_model._read_group(domain, ["product_id"], ["quantity:sum"])
    quantities_by_code = {}
    for product, quantity in grouped:
        quantities_by_code[product.ginlong_product_code] = (
            quantities_by_code.get(product.ginlong_product_code, 0.0) + quantity
        )
    inventory = [
        {"productCode": product_code, "quantity": float_round(quantity, precision_digits=6)}
        for product_code, quantity in quantities_by_code.items()
    ]
    inventory.sort(key=lambda row: row["productCode"])
    return {
        "returnStatus": "Y",
        "exceptionInfo": "OK",
        "operationTime": fields.Datetime.to_string(fields.Datetime.now()),
        "owner": payload["owner"],
        "warehouse": payload["warehouse"],
        "inventoryList": inventory,
    }
