"""Move Ginlong product identity/properties into native template variants."""

from odoo import SUPERUSER_ID, Command, api
from odoo.exceptions import UserError

from odoo.addons.ginlong_apis.product_identity import ginlong_internal_code


SHARED_FIELDS = (
    "ginlong_specification_model",
    "ginlong_unit",
    "ginlong_weight",
    "ginlong_power",
    "ginlong_national_standard",
    "ginlong_certification_model",
    "ginlong_product_form",
    "ginlong_length",
    "ginlong_width",
    "ginlong_height",
)
TRACKING_BY_FORM = {
    "原材料": "none",
    "半成品": "serial",
    "成品": "serial",
}


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    products = env["product.product"].sudo().with_context(active_test=False).search([
        ("ginlong_owner_code", "!=", False),
    ])
    if not products:
        return

    templates_by_code = {}
    pair_counts = {}
    for product in products:
        code = product.default_code
        owner_code = product.ginlong_owner_code
        if not code:
            raise UserError(
                "Ginlong product %s has an owner code but no default_code; "
                "the raw productCode cannot be inferred." % product.id
            )
        templates_by_code.setdefault(code, set()).add(product.product_tmpl_id.id)
        pair_counts[(owner_code, code)] = pair_counts.get((owner_code, code), 0) + 1
    duplicate_templates = {
        code: sorted(ids) for code, ids in templates_by_code.items() if len(ids) > 1
    }
    if duplicate_templates:
        detail = "; ".join("%s: %s" % (code, ids) for code, ids in sorted(duplicate_templates.items()))
        raise UserError(
            "Ginlong productCode values exist on multiple product templates. "
            "The migration stopped to preserve stock and business references: %s" % detail
        )
    duplicate_pairs = [key for key, count in pair_counts.items() if count > 1]
    if duplicate_pairs:
        raise UserError("Duplicate Ginlong owner/productCode variants found: %s" % duplicate_pairs)

    owner_attribute = env.ref("ginlong_apis.product_attribute_ginlong_owner").sudo()
    for product in products:
        template = product.product_tmpl_id
        form = product.ginlong_product_form
        tracking = TRACKING_BY_FORM.get(form)
        if not tracking:
            raise UserError(
                "Ginlong product %s has unsupported productForm %r; "
                "the migration stopped without guessing." % (product.default_code, form)
            )
        if template.type != "consu":
            raise UserError(
                "Ginlong product template %s has non-stockable product type %s; "
                "the migration stopped rather than changing its type." % (template.id, template.type)
            )

        other_variants = template.with_context(active_test=False).product_variant_ids - product
        if other_variants:
            raise UserError(
                "Ginlong template %s has other variants; owner migration cannot safely infer their identities."
                % template.id
            )
        non_owner_lines = template.attribute_line_ids.filtered(lambda line: line.attribute_id != owner_attribute)
        if non_owner_lines:
            raise UserError(
                "Ginlong template %s already has other variant attributes; "
                "the migration stopped to avoid changing its variant combinations." % template.id
            )

        template_values = {name: product[name] or False for name in SHARED_FIELDS}
        template_values["tracking"] = tracking
        template_values["is_storable"] = True
        template.write(template_values)

        owner_code = product.ginlong_owner_code
        owner_value = env["product.attribute.value"].sudo().search([
            ("attribute_id", "=", owner_attribute.id), ("name", "=", owner_code),
        ], limit=1)
        if not owner_value:
            owner_value = env["product.attribute.value"].sudo().create({
                "attribute_id": owner_attribute.id,
                "name": owner_code,
            })
        owner_line = template.attribute_line_ids.filtered(lambda line: line.attribute_id == owner_attribute)
        if owner_line:
            owner_line.write({"value_ids": [Command.link(owner_value.id)]})
        else:
            env["product.template.attribute.line"].sudo().create({
                "product_tmpl_id": template.id,
                "attribute_id": owner_attribute.id,
                "value_ids": [Command.set([owner_value.id])],
            })

        ptavs = template.attribute_line_ids.filtered(
            lambda line: line.attribute_id == owner_attribute
        ).product_template_value_ids.filtered(
            lambda value: value.product_attribute_value_id == owner_value
        )
        owner_variant = template.with_context(active_test=False).product_variant_ids.filtered(
            lambda variant: bool(variant.product_template_attribute_value_ids & ptavs)
        )
        if len(owner_variant) != 1 or owner_variant != product:
            raise UserError(
                "Adding the Ginlong owner attribute did not preserve product variant %s." % product.id
            )

        internal_code = ginlong_internal_code(owner_code, product.default_code)
        collisions = env["product.product"].sudo().with_context(active_test=False).search([
            ("default_code", "=", internal_code), ("id", "!=", product.id),
        ], limit=1)
        if collisions:
            raise UserError("Internal Ginlong code %s is already used by product %s." % (internal_code, collisions.id))
        product.write({
            "ginlong_product_code": product.default_code,
            "default_code": internal_code,
        })
