"""通过 Odoo ORM 为 API07 HVR 创建隔离的测试前置数据和临时 Token。"""

from datetime import timedelta
from pathlib import Path
import secrets

from odoo import fields
from odoo.addons.ginlong_apis import services
from odoo.tools import config


RUN = "HVR07-20261119"
OWNER_A = RUN + "-OWNER-A"
OWNER_B = RUN + "-OWNER-B"
UNIT_ALT = RUN + "-UNIT-ALT"
PROJECT_NAME = RUN + " API07 HVR Project"
TEST_LOGIN = "hvr_api07_manual"
TEST_USER_NAME = RUN + " API07 HVR 人工验收用户"
DATA_DIR = Path.cwd() / "docs/ginlong_apis/hvr/api07/test_data"
ENV_FILE = DATA_DIR / ".api07_hvr.env"
PRODUCT_CODES = [
    RUN + "-RAW-A", RUN + "-SEMI-A", RUN + "-FIN-A",
    RUN + "-EDIT-NAME", RUN + "-EDIT-REPEAT",
    RUN + "-RETRY", RUN + "-BAD-FORM", RUN + "-NO-API-USER",
    RUN + "-INVALID-TOKEN", RUN + "-NULL-OWNER", RUN + "-BLANK-NAME",
    RUN + "-NULL-FORM", RUN + "-BAD-WEIGHT", RUN + "-BAD-VARCHAR-TYPE",
    RUN + "-BAD-FORM-TYPE",
]


def _unique_or_create(model, domain, values, label):
    """按明确测试键复用唯一记录，遇到重复数据时停止而不猜测。"""
    records = model.sudo().search(domain, limit=2)
    if len(records) > 1:
        raise RuntimeError("API07 HVR 测试数据存在重复%s，请先运行 reset_api07_hvr.py" % label)
    return records or model.sudo().create(values)


def _seed_product(api_user, owner_code, code, name, spec, unit, form, **optional):
    """通过现有 API07 业务服务建立仅供 Edit 场景使用的基准产品。"""
    payload = {
        "action": "Add", "owner": owner_code, "productCode": code,
        "productName": name, "specificationModel": spec,
        "unit": unit, "productForm": form,
    }
    payload.update(optional)
    result = services.api07(env, api_user, payload)
    if not result.get("success"):
        raise RuntimeError("无法建立 API07 Edit 基准产品 %s: %s" % (code, result))
    return env["product.product"].sudo().browse(result["data"]["id"])


def prepare_api07_hvr():
    """创建人工验收登录/API 用户、Owner、项目、基准产品和本地凭据。"""
    module = env["ir.module.module"].sudo().search([("name", "=", "ginlong_apis")], limit=1)
    if not module or module.state != "installed":
        raise RuntimeError("ginlong_apis 模块必须先安装")

    products = env["product.product"].sudo().with_context(active_test=False).search([
        ("ginlong_product_code", "in", PRODUCT_CODES),
    ])
    if products:
        raise RuntimeError("已存在 API07 HVR 产品数据；请先执行 reset_api07_hvr.py，再准备新一轮")
    if ENV_FILE.exists():
        raise RuntimeError("已存在 HVR 本地凭据文件；请先执行 reset_api07_hvr.py，避免遗失凭据")

    units = env["uom.uom"].sudo().search([("name", "in", ["台", "个"])])
    if set(units.mapped("name")) != {"台", "个"} or len(units) != 2:
        raise RuntimeError("数据库必须各有且仅有一个“台”和“个”单位档案")
    base_unit = units.filtered(lambda unit: unit.name == "台")
    alternate_units = env["uom.uom"].sudo().search([("name", "=", UNIT_ALT)], limit=2)
    if len(alternate_units) > 1:
        raise RuntimeError("HVR 同类别测试单位重复，请先运行 reset_api07_hvr.py")
    if alternate_units:
        if alternate_units.category_id != base_unit.category_id:
            raise RuntimeError("HVR 同类别测试单位已存在但类别不符，请先运行 reset_api07_hvr.py")
    else:
        env["uom.uom"].sudo().create({
            "name": UNIT_ALT,
            "category_id": base_unit.category_id.id,
            "uom_type": "bigger",
            "factor": 1.0,
            "rounding": base_unit.rounding,
        })

    owner_a = _unique_or_create(env["res.partner"], [("ginlong_owner_code", "=", OWNER_A)], {
        "name": RUN + " 测试货主 A", "is_company": True, "ginlong_owner_code": OWNER_A,
    }, "货主 A")
    owner_b = _unique_or_create(env["res.partner"], [("ginlong_owner_code", "=", OWNER_B)], {
        "name": RUN + " 测试货主 B", "is_company": True, "ginlong_owner_code": OWNER_B,
    }, "货主 B")

    project = _unique_or_create(env["project.project"], [("name", "=", PROJECT_NAME)], {
        "name": PROJECT_NAME,
        "owner": owner_a.id,
        "category": env.ref("product.product_category_all").id,
        "warehouse": env.ref("stock.warehouse0").id,
        "is_check_origin_doc": False,
    }, "项目")

    user_model = env["res.users"].sudo().with_context(no_reset_password=True)
    test_users = user_model.search([("login", "=", TEST_LOGIN)], limit=2)
    if len(test_users) > 1:
        raise RuntimeError("HVR 登录名重复，请先人工核对")
    if test_users and test_users.name != TEST_USER_NAME:
        raise RuntimeError("登录名 %s 已被非 HVR 用户占用，停止修改" % TEST_LOGIN)
    test_password = secrets.token_urlsafe(24)
    group_ids = [
        env.ref("base.group_user").id,
        env.ref("stock.group_stock_manager").id,
    ]
    user_values = {
        "name": TEST_USER_NAME,
        "login": TEST_LOGIN,
        "password": test_password,
        "active": True,
        "company_id": env.company.id,
        "company_ids": [(6, 0, [env.company.id])],
        "groups_id": [(6, 0, group_ids)],
    }
    if test_users:
        test_user = test_users
        test_user.write(user_values)
    else:
        test_user = user_model.create(user_values)

    existing_links = env["world.depot.api.user"].sudo().search([("user_id", "=", test_user.id)])
    matching_links = existing_links.filtered(lambda record: record.project == project)
    if existing_links and not matching_links:
        raise RuntimeError("HVR 登录用户已关联其他 API User；停止准备以避免改变现有权限")
    if len(matching_links) > 1:
        raise RuntimeError("HVR 项目存在多个 API User，请先运行 reset_api07_hvr.py")
    api_user = matching_links or env["world.depot.api.user"].sudo().create({
        "user_id": test_user.id, "project": project.id,
    })
    api_key = secrets.token_urlsafe(24)
    api_secret = secrets.token_urlsafe(32)
    api_user.write({"api_key": api_key, "secret": api_secret})

    public_user = env.ref("base.public_user")
    if env["world.depot.api.user"].sudo().search_count([("user_id", "=", public_user.id)]):
        raise RuntimeError("公共用户已关联 API User；为避免覆盖现有身份，停止创建无项目权限场景")
    no_project_api_user = env["world.depot.api.user"].sudo().create({"user_id": public_user.id})

    valid_token = secrets.token_urlsafe(32)
    no_api_user_token = secrets.token_urlsafe(32)
    port = config.get("http_port", 8099)
    if not port:
        port = 8099
    token_model = env["world.depot.api.token"].sudo()
    expires = fields.Datetime.now() + timedelta(days=7)
    token_model.create({"user_id": test_user.id, "token": valid_token, "expires": expires})
    token_model.create({"user_id": public_user.id, "token": no_api_user_token, "expires": expires})

    ENV_FILE.write_text(
        "API07_BASE_URL=http://127.0.0.1:%s\nAPI07_LOGIN=%s\nAPI07_PASSWORD=%s\n"
        "API07_API_KEY=%s\nAPI07_API_SECRET=%s\n"
        "API07_TOKEN=%s\nAPI07_NO_API_USER_TOKEN=%s\n"
        "API07_API_USER_ID=%s\nAPI07_NO_PROJECT_API_USER_ID=%s\n"
        % (port, TEST_LOGIN, test_password, api_key, api_secret, valid_token, no_api_user_token,
           api_user.id, no_project_api_user.id),
        encoding="utf-8",
    )
    ENV_FILE.chmod(0o600)

    seeds = [
        _seed_product(
            api_user, OWNER_A, RUN + "-EDIT-NAME", "HVR07 名称修改旧值", "HVR07-NAME-OLD",
            "台", "原材料", power="1kW", weight=1.25, length=100, width=50, height=40,
        ),
        _seed_product(
            api_user, OWNER_A, RUN + "-EDIT-REPEAT", "HVR07 重复编辑基准产品", "HVR07-REPEAT-MODEL",
            "台", "半成品", power="3kW", weight=2.5, length=100, width=60, height=40,
        ),
    ]

    env.cr.commit()
    print("API07 HVR 前置数据及专用登录/API User 已通过 ORM 创建并提交。")
    print("RUN=%s OWNER_A=%s OWNER_B=%s" % (RUN, OWNER_A, OWNER_B))
    print("LOGIN=%s USER_ID=%s" % (TEST_LOGIN, test_user.id))
    print("PROJECT_ID=%s API_USER_ID=%s NO_PROJECT_API_USER_ID=%s" % (
        project.id, api_user.id, no_project_api_user.id,
    ))
    print("OWNER_PARTNER_IDS=%s" % ",".join(str(record.id) for record in (owner_a, owner_b)))
    print("SEED_PRODUCT_IDS=%s" % ",".join(str(record.id) for record in seeds))
    print("UNIT_ALT_ID=%s" % env["uom.uom"].sudo().search([("name", "=", UNIT_ALT)], limit=1).id)
    print("API07_BASE_URL=http://127.0.0.1:%s" % port)
    print("本地 Token 写入权限为 0600 的隐藏文件：%s（不会打印 Token）" % ENV_FILE)
    print("产品菜单：WorldDepot / Ginlong APIs / 产品；日志菜单：WorldDepot / Ginlong APIs / API 日志")


prepare_api07_hvr()
