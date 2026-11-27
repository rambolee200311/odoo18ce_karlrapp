"""供现有 Hoymiles、OFoundation API 共用的产品查找方法。"""

from odoo.http import request


def resolve_product(product_code):
    """按请求方所属项目解析产品，不任意选择重复的 default_code。

    只有旧编码或条码能唯一定位产品时才继续兼容旧查找。项目货主存在
    Ginlong owner code 时，以现有 Ginlong 产品编码和货主字段消除跨货主歧义。

    参数：
        product_code: 请求中的产品编码或条码。

    返回：
        唯一匹配的 `product.product` 记录集；未匹配时为空记录集。
    """
    project = getattr(getattr(request, "api_user", False), "project", False)
    return _resolve_product(request.env, product_code, project)


def _resolve_product(env, product_code, project=False):
    """在 Ginlong 复合身份优先和既有编码/条码回退间执行确定性查找。

    参数：
        env: 当前 Odoo Environment。
        product_code: 外部请求传入的编码。
        project: 可选 WMS 项目，用于取得货主编码。

    返回：
        唯一匹配的 `product.product` 记录集。

    异常：
        出现跨货主歧义时抛出 ValueError，避免把明细关联到错误货主的变体。
    """
    product_model = env["product.product"].sudo()
    owner_code = getattr(getattr(project, "owner", False), "ginlong_owner_code", False)

    if "ginlong_product_code" in product_model._fields:
        if owner_code:
            # 有项目货主时优先按 Ginlong 复合键定位；发现同码产品属于其他货主就明确拒绝。
            owner_products = product_model.search([
                ("ginlong_product_code", "=", product_code),
                ("ginlong_owner_code", "=", owner_code),
            ], limit=2)
            if len(owner_products) == 1:
                return owner_products
            if len(owner_products) > 1:
                raise ValueError(
                    "Ginlong product code %s is ambiguous for owner %s" % (product_code, owner_code)
                )
            if product_model.search([("ginlong_product_code", "=", product_code)], limit=1):
                raise ValueError(
                    "Ginlong product code %s was not found for owner %s" % (product_code, owner_code)
                )
        else:
            ginlong_products = product_model.search([
                ("ginlong_product_code", "=", product_code),
            ], limit=2)
            if ginlong_products:
                if len(ginlong_products) > 1:
                    raise ValueError(
                        "Ginlong product code %s is ambiguous; configure the project owner's Ginlong owner code "
                        "to identify the correct product" % product_code
                    )
                return ginlong_products

    # 非 Ginlong 产品或尚未迁移的旧资料继续走原有 default_code/barcode 兼容路径。
    code_products = product_model.search([("default_code", "=", product_code)], limit=3)
    if len(code_products) > 1:
        if owner_code and "ginlong_owner_code" in product_model._fields:
            owner_products = product_model.search([
                ("default_code", "=", product_code),
                ("ginlong_owner_code", "=", owner_code),
            ], limit=2)
            if len(owner_products) == 1:
                return owner_products
        raise ValueError(
            "Product code %s is ambiguous; configure the project owner's Ginlong owner code "
            "to identify the correct product" % product_code
        )

    if code_products:
        product = code_products[0]
        product_owner = getattr(product, "ginlong_owner_code", False)
        if owner_code and product_owner and product_owner != owner_code:
            return product_model.browse()
        return product

    barcode_products = product_model.search([("barcode", "=", product_code)], limit=2)
    if len(barcode_products) > 1:
        raise ValueError("Barcode %s is ambiguous in the existing WMS product data" % product_code)
    return barcode_products[:1]
