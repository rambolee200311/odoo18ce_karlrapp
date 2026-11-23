"""集中生成 Ginlong 产品变体的内部标识，供 API 处理和数据迁移共用。"""


def ginlong_internal_code(owner_code, product_code):
    """将货主和原始产品编码无歧义地编码为 Odoo 内部产品编码。

    参数：
        owner_code: Ginlong 货主编码。
        product_code: Ginlong 原始产品编码。

    返回：
        仅供 Odoo 内部使用的稳定复合编码；不用于 Ginlong 报文。
    """
    owner_code = str(owner_code or "")
    product_code = str(product_code or "")
    return "GL:%s:%s:%s:%s" % (
        len(owner_code), owner_code, len(product_code), product_code,
    )
