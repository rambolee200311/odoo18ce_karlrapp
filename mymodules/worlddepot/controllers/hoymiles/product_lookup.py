"""Product lookup shared by the existing Hoymiles and OFoundation APIs."""

from odoo.http import request


def resolve_product(product_code):
    """Resolve a product without choosing an arbitrary duplicate default_code.

    Legacy single-code and barcode requests remain supported when they resolve
    to one product. If a project owner has a Ginlong owner code, it disambiguates
    duplicate internal references using the product's existing Ginlong field.
    """
    project = getattr(getattr(request, "api_user", False), "project", False)
    return _resolve_product(request.env, product_code, project)


def _resolve_product(env, product_code, project=False):
    product_model = env["product.product"].sudo()
    owner_code = getattr(getattr(project, "owner", False), "ginlong_owner_code", False)

    if "ginlong_product_code" in product_model._fields:
        if owner_code:
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
