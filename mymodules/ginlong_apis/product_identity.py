"""Stable identifiers shared by Ginlong API and product migration code."""


def ginlong_internal_code(owner_code, product_code):
    """Encode the external identity without delimiter ambiguity."""
    owner_code = str(owner_code or "")
    product_code = str(product_code or "")
    return "GL:%s:%s:%s:%s" % (
        len(owner_code), owner_code, len(product_code), product_code,
    )
