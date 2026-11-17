"""Small ORM mapping functions for the local Ginlong simulation contract.

These functions deliberately do not define Ginlong's production URL, transport,
action enums, retry rules, or unit conversions. The four controller routes are
local simulation entry points until Ginlong supplies the external contract.
"""

import json

from odoo.exceptions import ValidationError


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


def _find_product(env, product_code):
    products = env["product.product"].sudo().search(
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
    action = str(payload["action"]).upper()
    order_model = env["world.depot.inbound.order"]

    if action == "DELETE":
        order = _find_one_by_reference(order_model, project, payload["inboundOrderNo"], "Inbound order")
        if order.state != "cancel":
            order.write({"state": "cancel"})
        return {"success": True, "data": {"action": action, "inboundOrderNo": payload["inboundOrderNo"]}}
    if action not in ("CREATE", "UPDATE"):
        raise ValidationError("API01 local simulation action must be CREATE, UPDATE, or DELETE")

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
        product = _find_product(env, detail["productCode"])
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
    action = str(payload["action"]).upper()
    order_model = env["world.depot.outbound.order"]

    if action == "DELETE":
        order = _find_one_by_reference(order_model, project, payload["outboundOrderNo"], "Outbound order")
        if order.state != "cancel":
            order.write({"state": "cancel"})
        return {"success": True, "data": {"action": action, "outboundOrderNo": payload["outboundOrderNo"]}}
    if action not in ("CREATE", "UPDATE"):
        raise ValidationError("API03 local simulation action must be CREATE, UPDATE, or DELETE")

    order = False
    if action == "UPDATE":
        order = _find_one_by_reference(order_model, project, payload["outboundOrderNo"], "Outbound order")
    details = payload.get("details")
    if action == "CREATE" or "details" in payload:
        if not isinstance(details, list) or not details:
            raise ValidationError("API03 details must contain at least one product row")
    else:
        details = None
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
        product = _find_product(env, detail["productCode"])
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
    """Store a standalone stocktake task; this function never accesses stock models."""
    _required(payload, ["owner", "action", "countOrderNo", "warehouse"], "API05")
    project = _project(api_user)
    action = str(payload["action"]).upper()
    task_model = env["ginlong.stocktake.task"].sudo()

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
        return {"success": True, "data": {"action": action, "countOrderNo": payload["countOrderNo"]}}
    if action not in ("CREATE", "UPDATE"):
        raise ValidationError("API05 local simulation action must be CREATE, UPDATE, or DELETE")

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
    line_values = []
    for index, detail in enumerate(details or []):
        if not isinstance(detail, dict):
            raise ValidationError("API05 details[%s] must be an object" % index)
        _required(detail, ["productCode", "productName", "specificationModel", "quantity"], "API05 details[%s]" % index)
        line_values.append((0, 0, {
            "product_code": detail["productCode"],
            "product_name": detail["productName"],
            "specification_model": detail["specificationModel"],
            "quantity": _number(detail["quantity"], "API05 details[%s].quantity" % index),
        }))
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
        task_values["line_ids"] = [(5, 0, 0)] + line_values
    if sn_list is not None or action == "CREATE":
        task_values["sn_list_json"] = json.dumps(sn_list or [], ensure_ascii=False)
    if action == "CREATE":
        task_values["line_ids"] = line_values
        task = task_model.create(task_values)
    else:
        task.write(task_values)
    return {"success": True, "data": {"id": task.id, "countOrderNo": task.count_order_no}}


def api07(env, api_user, payload):
    """Upsert product fields on native Odoo product models."""
    _required(payload, ["owner", "productCode", "productName", "specificationModel", "unit", "productForm"], "API07")
    _project(api_user)
    code = payload["productCode"]
    products = env["product.product"].sudo().search([
        ("default_code", "=", code),
        ("ginlong_owner_code", "=", payload["owner"]),
    ], limit=2)
    if len(products) > 1:
        raise ValidationError("Owner/product key %s/%s is ambiguous in the existing WMS product data" % (payload["owner"], code))
    if not products:
        conflicting = env["product.product"].sudo().search([("default_code", "=", code)], limit=1)
        if conflicting:
            raise ValidationError(
                "Product code %s already belongs to a different Ginlong owner; the existing WMS product code cannot be reassigned implicitly" % code
            )

    units = env["uom.uom"].sudo().search([("name", "=", payload["unit"])], limit=2)
    if len(units) != 1:
        reason = "not found" if not units else "ambiguous"
        raise ValidationError("Unit %s is %s in the existing Odoo units of measure" % (payload["unit"], reason))

    if products:
        product = products
        template = product.product_tmpl_id
        template.write({"name": payload["productName"], "uom_id": units.id, "uom_po_id": units.id})
        product.write({"default_code": code})
    else:
        template = env["product.template"].sudo().create({
            "name": payload["productName"],
            "uom_id": units.id,
            "uom_po_id": units.id,
        })
        product = template.product_variant_id
        product.write({"default_code": code})

    values = {
        "ginlong_owner_code": payload["owner"],
        "ginlong_specification_model": payload["specificationModel"],
        "ginlong_unit": payload["unit"],
        "ginlong_product_form": payload["productForm"],
    }
    source_fields = {
        "power": "ginlong_power",
        "nationalStandard": "ginlong_national_standard",
        "certificationModel": "ginlong_certification_model",
        "weight": "ginlong_weight",
        "length": "ginlong_length",
        "width": "ginlong_width",
        "height": "ginlong_height",
    }
    for source_name, target_name in source_fields.items():
        if source_name in payload and payload[source_name] is not None:
            values[target_name] = _number(payload[source_name], "API07.%s" % source_name) if source_name in {"weight", "length", "width", "height"} else payload[source_name]
    product.write(values)
    return {"success": True, "data": {"id": product.id, "productCode": product.default_code}}
