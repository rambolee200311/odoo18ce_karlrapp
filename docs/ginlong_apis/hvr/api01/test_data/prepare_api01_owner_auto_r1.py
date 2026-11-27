"""用 Odoo ORM 准备 API01 自动建档复测所需的无货主产品夹具。"""

from odoo.exceptions import UserError

from odoo.addons.ginlong_apis.product_identity import ginlong_internal_code


OWNER_CODE = "HVR01-20261122-OWNER-AUTO-R1"
PRODUCT_CODE = "HVR01-20261122-PROD-AUTO-R1"


def prepare_owner_auto_r1_product():
    """创建产品变体但不创建货主联系人，以便 API01 实测自动建档。"""
    partner = env["res.partner"].sudo().with_context(active_test=False).search([
        ("ginlong_owner_code", "=", OWNER_CODE),
    ], limit=1)
    if partner:
        raise UserError("复测货主已经存在；请使用新编码，勿删除历史货主。")

    product_model = env["product.product"].sudo().with_context(active_test=False)
    if product_model.search_count([
        ("ginlong_owner_code", "=", OWNER_CODE),
        ("ginlong_product_code", "=", PRODUCT_CODE),
    ]):
        raise UserError("复测产品已经存在；为保持自动建档前置条件，脚本停止。")

    # 仅建立 API01 必需的 owner/productCode 产品识别夹具；不预建 res.partner。
    product = product_model.create({
        "name": "HVR01 API01 自动建档复测产品",
        "default_code": ginlong_internal_code(OWNER_CODE, PRODUCT_CODE),
        "ginlong_owner_code": OWNER_CODE,
        "ginlong_product_code": PRODUCT_CODE,
        "type": "consu",
        "is_storable": True,
    })
    env.cr.commit()
    print("API01 R1 ownerless product prepared: product_id=%s; owner contact remains absent." % product.id)


prepare_owner_auto_r1_product()
