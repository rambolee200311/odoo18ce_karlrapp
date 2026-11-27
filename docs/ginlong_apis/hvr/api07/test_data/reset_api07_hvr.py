"""通过 Odoo ORM 安全删除本 HVR 专用测试记录和临时 Token。"""

from pathlib import Path

from odoo.exceptions import UserError


RUN = "HVR07-20261119"
OWNER_CODES = [RUN + "-OWNER-A", RUN + "-OWNER-B"]
PROJECT_NAME = RUN + " API07 HVR Project"
UNIT_ALT = RUN + "-UNIT-ALT"
TEST_LOGIN = "hvr_api07_manual"
TEST_USER_NAME = RUN + " API07 HVR 人工验收用户"
DATA_DIR = Path.cwd() / "docs/ginlong_apis/hvr/api07/test_data"
ENV_FILE = DATA_DIR / ".api07_hvr.env"


def _read_env(path):
    """读取准备脚本生成的本地 Token 文件，不输出其敏感值。"""
    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            values[key] = value
    return values


def reset_api07_hvr():
    """仅删除 HVR07-20261119 标记的数据，并在有关联风险时停止。"""
    if not ENV_FILE.exists():
        raise UserError("未找到隐藏 Token 文件；为避免误删认证记录，请先确认测试数据状态")
    local_env = _read_env(ENV_FILE)
    api_user_model = env["world.depot.api.user"].sudo()
    project = env["project.project"].sudo().search([("name", "=", PROJECT_NAME)], limit=2)
    if len(project) > 1:
        raise UserError("HVR 测试项目重复，已停止重置")
    test_project = project[:1]
    test_users = env["res.users"].sudo().search([("login", "=", TEST_LOGIN)], limit=2)
    if len(test_users) > 1:
        raise UserError("HVR 专用登录名重复，停止重置")
    if test_users and test_users.name != TEST_USER_NAME:
        raise UserError("HVR 登录名已被非测试用户占用，停止重置")
    owner_partners = env["res.partner"].sudo().search([("ginlong_owner_code", "in", OWNER_CODES)])

    other_projects = env["project.project"].sudo().search([
        ("owner", "in", owner_partners.ids), ("id", "not in", test_project.ids or [0]),
    ])
    if other_projects:
        raise UserError("HVR 货主已被其他项目引用；为保护 WMS 数据，停止重置")
    if owner_partners and env["stock.quant"].sudo().search_count([("owner_id", "in", owner_partners.ids)]):
        raise UserError("HVR 货主已有 stock.quant 记录；为保护库存数据，停止重置")
    if owner_partners and env["stock.move.line"].sudo().search_count([("owner_id", "in", owner_partners.ids)]):
        raise UserError("HVR 货主已有 stock.move.line 记录；为保护库存数据，停止重置")

    products = env["product.product"].sudo().with_context(active_test=False).search([
        ("ginlong_product_code", "like", RUN + "-%"),
    ])
    templates = products.mapped("product_tmpl_id")
    for template in templates:
        variants = template.with_context(active_test=False).product_variant_ids
        outsiders = variants.filtered(
            lambda product: not product.ginlong_product_code
            or not product.ginlong_product_code.startswith(RUN + "-")
        )
        if outsiders:
            raise UserError("HVR 测试模板含有非测试变体；为保护现有产品，停止重置")
    if products and env["stock.move"].sudo().search_count([("product_id", "in", products.ids)]):
        raise UserError("HVR 产品已被库存移动引用；为保护库存历史，停止重置")
    if products and env["stock.quant"].sudo().search_count([("product_id", "in", products.ids)]):
        raise UserError("HVR 产品已有库存量记录；为保护库存数据，停止重置")

    alternate_unit = env["uom.uom"].sudo().search([("name", "=", UNIT_ALT)], limit=2)
    if len(alternate_unit) > 1:
        raise UserError("HVR 同类别测试单位重复，停止重置")
    if alternate_unit:
        unit_templates = env["product.template"].sudo().with_context(active_test=False).search([
            "|", ("uom_id", "=", alternate_unit.id), ("uom_po_id", "=", alternate_unit.id),
        ])
        if unit_templates - templates:
            raise UserError("HVR 测试单位已被非 HVR 产品引用；为保护产品主数据，停止重置")

    api_user_ids = [
        int(local_env.get("API07_API_USER_ID", 0)),
        int(local_env.get("API07_NO_PROJECT_API_USER_ID", 0)),
    ]
    test_api_users = api_user_model.browse([record_id for record_id in api_user_ids if record_id]).exists()
    if test_project:
        test_api_users |= api_user_model.search([
            ("user_id", "=", test_users.id if test_users else 0),
            ("project", "=", test_project.id),
        ])
    if test_api_users.filtered(lambda record: record.project and record.project != test_project):
        raise UserError("Token 文件中的 API User ID 不属于 HVR 测试项目，停止重置")
    if test_users:
        unrelated_api_users = api_user_model.search([
            ("user_id", "=", test_users.id),
            ("id", "not in", test_api_users.ids or [0]),
        ])
        if unrelated_api_users:
            raise UserError("HVR 登录用户还关联其他 API User；为保护现有权限，停止重置")
    tokens = env["world.depot.api.token"].sudo().search([
        ("token", "in", [
            local_env.get("API07_TOKEN", ""),
            local_env.get("API07_NO_API_USER_TOKEN", ""),
        ]),
    ])
    logs = env["world.depot.api.log"].sudo().search([
        ("request_path", "=", "/api/ginlong/TPL_Product_Master"),
        ("request_data", "ilike", RUN),
    ])
    idem = env["ginlong.api.idempotency"].sudo().search([
        ("api_code", "=", "API07"), ("business_key", "ilike", RUN),
    ])

    tokens.unlink()
    logs.unlink()
    idem.unlink()
    test_api_users.unlink()
    test_users.write({"active": False})
    templates.unlink()
    alternate_unit.unlink()

    owner_attribute = env.ref("ginlong_apis.product_attribute_ginlong_owner")
    owner_values = env["product.attribute.value"].sudo().search([
        ("attribute_id", "=", owner_attribute.id), ("name", "in", OWNER_CODES),
    ])
    used_values = env["product.template.attribute.line"].sudo().search([
        ("value_ids", "in", owner_values.ids),
    ]) if owner_values else env["product.template.attribute.line"].browse()
    if used_values:
        raise UserError("货主变体值仍被其他模板引用；已停止继续删除")
    owner_values.unlink()
    test_project.unlink()
    owner_partners.unlink()
    env.cr.commit()
    ENV_FILE.unlink(missing_ok=True)
    print("已通过 ORM 重置 %s 测试数据、日志、幂等记录、临时 Token，并停用 HVR 登录用户。" % RUN)
    print("未删除任何非 HVR 产品、库存记录或历史 WMS 业务记录。")


reset_api07_hvr()
