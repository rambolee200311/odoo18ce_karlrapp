"""Small ORM mapping functions for the local Ginlong simulation contract.

These functions use the provisional Ginlong path/action table supplied by the
project owner. The action values are normalized case-insensitively before the
idempotency fingerprint is computed.
"""

import json

from odoo import Command, fields
from odoo.exceptions import ValidationError
from odoo.tools.float_utils import float_compare, float_round

from .product_identity import ginlong_internal_code


_INBOUND_ACTIONS = {
    "API01": {"add": ("CREATE", "Add"), "del": ("DELETE", "Del")},
    "API03": {"add": ("CREATE", "Add"), "del": ("DELETE", "Del"), "edit": ("UPDATE", "Edit")},
    "API05": {"add": ("CREATE", "Add"), "del": ("DELETE", "Del"), "edit": ("UPDATE", "Edit")},
    "API07": {"add": ("UPSERT", "Add"), "edit": ("UPSERT", "Edit")},
}
_LOCAL_ACTIONS = {
    **_INBOUND_ACTIONS,
    # API01's previously approved local update behavior remains available to
    # the legacy simulation route while the supplied external table is pending
    # Ginlong confirmation and lists only Add/Del for its public route.
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


def normalize_inbound_action(api_code, payload, strict=True):
    """Return a copy with the documented action spelling for stable fingerprints."""
    actions_by_api = _INBOUND_ACTIONS if strict else _LOCAL_ACTIONS
    if api_code not in actions_by_api:
        raise ValidationError("Unsupported Ginlong inbound API: %s" % api_code)
    _required(payload, ["action"], api_code)
    raw_action = payload["action"]
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
    normalized = normalize_inbound_action(api_code, payload, strict=False)
    external_action = normalized["action"]
    internal_action = next(
        value[0] for value in _LOCAL_ACTIONS[api_code].values()
        if value[1] == external_action
    )
    return internal_action, external_action


def _required(data, names, label):
    missing = [name for name in names if name not in data or data[name] is None or data[name] == ""]
    if missing:
        raise ValidationError("%s missing required field(s): %s" % (label, ", ".join(missing)))


def _number(value, field_name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValidationError("%s must be a JSON number in the local simulation input" % field_name)
    return float(value)


def _project(api_user):
    project = api_user.project if api_user else False
    if not project:
        raise ValidationError("The authenticated API user has no WMS project")
    return project


def _resolve_ginlong_owner(env, owner_code, create=False):
    """Resolve Ginlong's owner code to one existing res.partner record."""
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

    # The inbound payload supplies a code but no owner name, so use the code
    # as the partner's display name. The SQL unique constraint prevents
    # concurrent requests for different orders from creating duplicate owners.
    try:
        with env.cr.savepoint():
            return partner_model.create({
                "name": owner_code,
                "ginlong_owner_code": owner_code,
            })
    except Exception:
        # Another transaction may have created this code after our first
        # search. Reuse it if the unique constraint resolved that race.
        owners = partner_model.search([("ginlong_owner_code", "=", owner_code)], limit=2)
        if len(owners) == 1:
            return owners
        raise


def _find_product(env, product_code, owner_code=None):
    """Resolve Ginlong product codes within their owner namespace."""
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
    records = model.sudo().search([("project", "=", project.id), ("reference", "=", reference)], limit=2)
    if len(records) != 1:
        reason = "not found" if not records else "ambiguous"
        raise ValidationError("%s %s is %s in this WMS project" % (label, reference, reason))
    return records


def api01(env, api_user, payload):
    """Map API01 to the existing inbound order / pallet / product structure."""
    _required(payload, ["owner", "action", "inboundOrderNo", "warehouse", "businessType"], "API01")
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
    if action == "CREATE" or "details" in payload:
        if not isinstance(details, list) or not details:
            raise ValidationError("API01 details must contain at least one product row")
    else:
        details = None
    lines = []
    product_line_by_code = {}
    for index, detail in enumerate(details or []):
        if not isinstance(detail, dict):
            raise ValidationError("API01 details[%s] must be an object" % index)
        _required(detail, ["productCode", "specificationModel", "quantity"], "API01 details[%s]" % index)
        product_name = detail.get("productName") or detail.get("name")
        if not product_name:
            raise ValidationError("API01 details[%s] missing required field(s): productName/name" % index)
        product = _find_product(env, detail["productCode"], payload["owner"])
        quantity = _number(detail["quantity"], "API01 details[%s].quantity" % index)
        nested_product = {
            "product_id": product.id,
            "quantity": quantity,
            "ginlong_product_code": detail["productCode"],
            "ginlong_product_name": product_name,
            "ginlong_specification_model": detail["specificationModel"],
        }
        lines.append((0, 0, {
            # The existing WMS order is three-level. Keep its line grouping and
            # let its own defaults/compute methods govern pending order data.
            "pallets": 1.0,
            "inbound_order_product_pallet_ids": [(0, 0, nested_product)],
        }))
        product_line_by_code.setdefault(detail["productCode"], []).append(index)

    sn_list = payload.get("snList", [] if action == "CREATE" else None)
    if sn_list is not None and not isinstance(sn_list, list):
        raise ValidationError("API01 snList must be a list when provided")
    serial_values = [[] for _detail in (details or [])]
    for index, serial in enumerate(sn_list or []):
        if not isinstance(serial, dict):
            raise ValidationError("API01 snList[%s] must be an object" % index)
        _required(serial, ["productSN", "quantity", "productCode"], "API01 snList[%s]" % index)
        target_lines = product_line_by_code.get(serial["productCode"], [])
        if len(target_lines) != 1:
            raise ValidationError(
                "API01 snList[%s] productCode must identify exactly one details row in the current WMS order" % index
            )
        serial_vals = {
            "serial_number": serial["productSN"],
            "quantity": _number(serial["quantity"], "API01 snList[%s].quantity" % index),
            "ginlong_quantity": _number(serial["quantity"], "API01 snList[%s].quantity" % index),
            "ginlong_product_code": serial["productCode"],
            "ginlong_pallet_code": serial.get("palletCode") or False,
            "ginlong_product_name": serial.get("productName") or serial.get("name") or False,
            "ginlong_specification_model": serial.get("specificationModel") or False,
        }
        serial_values[target_lines[0]].append((0, 0, serial_vals))

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
    """Map the A-003 local assumption to the existing outbound order model."""
    _required(payload, ["owner", "action", "outboundOrderNo", "warehouse", "businessType"], "API03")
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
    if action == "CREATE" or "details" in payload:
        if not isinstance(details, list) or not details:
            raise ValidationError("API03 details must contain at least one product row")
    else:
        details = None
    if action == "UPDATE" and details is None:
        # A header-only edit must not change the order owner while leaving
        # saved detail products under a different owner namespace.
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
    if action == "CREATE" and not customer_name:
        raise ValidationError("The existing WMS outbound order requires a customer/recipient")
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

    order_lines = []
    line_required = [
        "productCode", "productName", "specificationModel", "quantity", "net_wt_machine",
        "net_wt_total", "pack_qty", "pallet_qty", "pallet_len", "pallet_wid", "pallet_hgt",
        "unit_vol", "pack_unit", "pack_wt", "pallet_total_wt", "total_vol",
        "carton_wt_total", "gross_wt_total",
    ]
    line_numeric = [
        "net_wt_machine", "net_wt_total", "pack_qty", "pallet_qty", "pallet_len",
        "pallet_wid", "pallet_hgt", "unit_vol", "pack_wt", "pallet_total_wt", "total_vol",
        "carton_wt_total", "gross_wt_total",
    ]
    for index, detail in enumerate(details or []):
        if not isinstance(detail, dict):
            raise ValidationError("API03 details[%s] must be an object" % index)
        _required(detail, line_required, "API03 details[%s]" % index)
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
        order_values["outbound_order_product_ids"] = [(5, 0, 0)] + order_lines
    if action == "CREATE":
        order_values["outbound_order_product_ids"] = order_lines
        order = order_model.sudo().create(order_values)
    else:
        order.write(order_values)
    return {"success": True, "data": {"id": order.id, "billno": order.billno, "state": order.state}}


def api05(env, api_user, payload):
    """Store the customer stocktake instruction in WorldDepot; never touch stock."""
    _required(payload, ["owner", "action", "countOrderNo", "warehouse"], "API05")
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
    if action == "CREATE" and not isinstance(sn_list, list):
        raise ValidationError("API05 snList must be a list")
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
    if action == "CREATE" or "details" in payload:
        if not isinstance(details, list) or not details:
            raise ValidationError("API05 details must contain at least one product row")
    else:
        details = None
    if sn_list is not None and not isinstance(sn_list, list):
        raise ValidationError("API05 snList must be a list")
    for index, detail in enumerate(details or []):
        if not isinstance(detail, dict):
            raise ValidationError("API05 details[%s] must be an object" % index)
        _required(detail, ["productCode", "productName", "specificationModel", "quantity"], "API05 details[%s]" % index)
        _number(detail["quantity"], "API05 details[%s].quantity" % index)
    for index, serial in enumerate(sn_list or []):
        if not isinstance(serial, dict):
            raise ValidationError("API05 snList[%s] must be an object" % index)
        _required(serial, ["productSN", "quantity", "palletCode", "productCode", "productName", "specificationModel"], "API05 snList[%s]" % index)
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
    """Upsert one shared product template and one owner-specific native variant."""
    _required(payload, ["action", "owner", "productCode", "productName", "specificationModel", "unit", "productForm"], "API07")
    _inbound_action("API07", payload)
    _project(api_user)
    owner_code = payload["owner"]
    code = payload["productCode"]
    product_form = payload["productForm"].strip() if isinstance(payload["productForm"], str) else payload["productForm"]
    tracking_by_form = {"原材料": "none", "半成品": "serial", "成品": "serial"}
    if product_form not in tracking_by_form:
        raise ValidationError("API07 productForm must be one of: 原材料, 半成品, 成品")

    units = env["uom.uom"].sudo().search([("name", "=", payload["unit"])], limit=2)
    if len(units) != 1:
        reason = "not found" if not units else "ambiguous"
        raise ValidationError("Unit %s is %s in the existing Odoo units of measure" % (payload["unit"], reason))

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

    internal_code = ginlong_internal_code(owner_code, code)
    code_collisions = product_model.search([("default_code", "=", internal_code)])
    if code_collisions and any(
        product.ginlong_owner_code != owner_code or product.ginlong_product_code != code
        for product in code_collisions
    ):
        raise ValidationError("Internal Ginlong product code collision for owner/product %s/%s" % (owner_code, code))

    if templates:
        template = templates
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
            raise ValidationError(
                "Ginlong productCode %s conflicts with shared product fields: %s"
                % (code, ", ".join(mismatches))
            )
    else:
        template = False

    owner_products = product_model.search([
        ("ginlong_owner_code", "=", owner_code),
        ("ginlong_product_code", "=", code),
    ], limit=2)
    if len(owner_products) > 1:
        raise ValidationError("Owner/product key %s/%s is ambiguous in the existing WMS product data" % (owner_code, code))

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
    product.write({
        "ginlong_owner_code": owner_code,
        "ginlong_product_code": code,
        "default_code": internal_code,
    })
    return {"success": True, "data": {"id": product.id, "productCode": code}}


def api09(env, payload):
    """Return the current physical inventory for the requested Odoo warehouse.

    Ginlong warehouse codes directly identify ``stock.warehouse.code``; no
    separate mapping model or name-based lookup is used. The owner code first
    resolves to ``res.partner.ginlong_owner_code`` and stock is isolated by
    ``stock.quant.owner_id``.
    """
    _required(payload, ["owner", "warehouse"], "API09")
    for field_name in ("owner", "warehouse"):
        value = payload[field_name]
        if not isinstance(value, str) or len(value) > 40:
            raise ValidationError("API09 %s must be a string of at most 40 characters" % field_name)

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
