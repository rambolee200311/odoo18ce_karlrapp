"""通过 Odoo ORM 准备 API01 人工验收所需货主、产品、项目和 Token。"""

from datetime import timedelta
import os
from pathlib import Path
import secrets

from odoo import fields
from odoo.tools import config
from odoo.addons.ginlong_apis import services
from odoo.addons.ginlong_apis.product_identity import ginlong_internal_code


RUN = "HVR01-20261121"
OWNER_A = RUN + "-OWNER-A"
OWNER_B = RUN + "-OWNER-B"
OWNER_AUTO = RUN + "-OWNER-AUTO"
COMMON_CODE = RUN + "-PROD-COMMON"
AUTO_CODE = RUN + "-PROD-AUTO"
WAREHOUSE_CODE = "KRWH"
PROJECT_NAME = RUN + " API01 HVR Project"
TEST_LOGIN = "hvr_api01_manual"
NO_PROJECT_LOGIN = "hvr_api01_no_project"
DATA_DIR = Path.cwd() / "docs/ginlong_apis/hvr/api01/test_data"
ENV_FILE = DATA_DIR / ".api01_hvr.env"


def _create_api_user(login, display_name, project=False):
    """创建 HVR 专用 Odoo 用户、API User 和 Bearer Token。"""
    password = secrets.token_urlsafe(24)
    user = env["res.users"].sudo().with_context(no_reset_password=True).create({
        "name": display_name,
        "login": login,
        "password": password,
        "active": True,
        "company_id": env.company.id,
        "company_ids": [(6, 0, [env.company.id])],
        "groups_id": [(6, 0, [env.ref("base.group_user").id,
                              env.ref("stock.group_stock_manager").id])],
    })
    api_user = env["world.depot.api.user"].sudo().create({
        "user_id": user.id,
        "project": project.id if project else False,
    })
    token = secrets.token_urlsafe(32)
    env["world.depot.api.token"].sudo().create({
        "user_id": user.id,
        "token": token,
        "expires": fields.Datetime.now() + timedelta(days=7),
    })
    return user, api_user, token, password


def _seed_product(api_user, owner_code, product_code):
    """通过已实现的 API07 业务服务准备 API01 所需货主产品变体。"""
    result = services.api07(env, api_user, {
        "action": "Add",
        "owner": owner_code,
        "productCode": product_code,
        "productName": "HVR01 Ginlong 入库产品",
        "specificationModel": "HVR01-MODEL-01",
        "unit": "台",
        "productForm": "原材料",
        "power": "1kW",
        "weight": 1.25,
        "length": 100,
        "width": 50,
        "height": 40,
    })
    if not result.get("success"):
        raise RuntimeError("无法通过 API07 业务服务准备产品 %s/%s: %s" % (
            owner_code, product_code, result,
        ))
    return env["product.product"].sudo().browse(result["data"]["id"])


def _seed_ownerless_product(owner_code, product_code):
    """准备产品编码但不预建货主联系人的 API01 自动建档夹具。

    API07 会按自身规则自动创建货主联系人，无法用于验证 API01 自动建档。
    此用例按 API01 既有 ORM 测试方式只建立产品变体，确保请求前该 owner 编码确实不存在。
    """
    return env["product.product"].sudo().create({
        "name": "HVR01 API01 自动建档产品",
        "default_code": ginlong_internal_code(owner_code, product_code),
        "ginlong_owner_code": owner_code,
        "ginlong_product_code": product_code,
        "type": "consu",
        "is_storable": True,
    })


def prepare_api01_hvr():
    """准备隔离的 API01 HVR 数据，凭据写入仓库忽略的 0600 文件。"""
    module = env["ir.module.module"].sudo().search([("name", "=", "ginlong_apis")], limit=1)
    if not module or module.state != "installed":
        raise RuntimeError("ginlong_apis 必须先安装")
    if ENV_FILE.exists():
        raise RuntimeError("已有 .api01_hvr.env；避免覆盖凭据，本脚本停止")

    partner_model = env["res.partner"].sudo().with_context(active_test=False)
    project_model = env["project.project"].sudo()
    product_model = env["product.product"].sudo().with_context(active_test=False)
    user_model = env["res.users"].sudo()
    existing = (
        partner_model.search([("ginlong_owner_code", "like", RUN + "%")], limit=1)
        or project_model.search([("name", "=", PROJECT_NAME)], limit=1)
        or product_model.search([("ginlong_product_code", "like", RUN + "%")], limit=1)
        or user_model.search([("login", "in", [TEST_LOGIN, NO_PROJECT_LOGIN])], limit=1)
    )
    if existing:
        raise RuntimeError("已检测到 HVR01 前缀数据；请先人工核对，再决定是否运行 reset_api01_hvr.py")

    units = env["uom.uom"].sudo().search([("name", "=", "台")], limit=2)
    if len(units) != 1:
        raise RuntimeError("数据库中必须有且仅有一个“台”单位档案")
    warehouse = env.ref("stock.warehouse0")
    if warehouse.code != WAREHOUSE_CODE:
        raise RuntimeError(
            "当前唯一测试仓库代码为 %s，HVR 报文预期为 %s；请先核对，不要继续准备。"
            % (warehouse.code, WAREHOUSE_CODE)
        )
    owner_a, owner_b = partner_model.create([
        {"name": RUN + " 测试货主 A", "is_company": True, "ginlong_owner_code": OWNER_A},
        {"name": RUN + " 测试货主 B", "is_company": True, "ginlong_owner_code": OWNER_B},
    ])
    project = project_model.create({
        "name": PROJECT_NAME,
        "owner": owner_a.id,
        "category": env.ref("product.product_category_all").id,
        "warehouse": warehouse.id,
        "is_check_origin_doc": False,
    })
    user, api_user, token, password = _create_api_user(
        TEST_LOGIN, RUN + " API01 HVR 人工验收用户", project,
    )
    no_project_user, no_project_api_user, no_project_token, _no_project_password = _create_api_user(
        NO_PROJECT_LOGIN, RUN + " API01 无项目权限测试用户",
    )

    # 相同 productCode 的两个变体用于验证 API01 按 owner + productCode 选中正确 SKU。
    product_a = _seed_product(api_user, OWNER_A, COMMON_CODE)
    product_b = _seed_product(api_user, OWNER_B, COMMON_CODE)
    # 此货主联系人故意不预建；产品变体已存在时，API01 应按获批规则创建联系人。
    product_auto = _seed_ownerless_product(OWNER_AUTO, AUTO_CODE)

    base_url = "http://127.0.0.1:%s" % (config.get("http_port", 8099) or 8099)
    env_content = (
        "API01_BASE_URL=%s\nAPI01_LOGIN=%s\nAPI01_PASSWORD=%s\n"
        "API01_TOKEN=%s\nAPI01_NO_PROJECT_TOKEN=%s\n"
        "API01_API_USER_ID=%s\nAPI01_NO_PROJECT_API_USER_ID=%s\n"
        % (base_url, TEST_LOGIN, password, token,
           no_project_token, api_user.id, no_project_api_user.id)
    )
    file_descriptor = os.open(
        str(ENV_FILE), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600,
    )
    with os.fdopen(file_descriptor, "w", encoding="utf-8") as env_file:
        env_file.write(env_content)
    env.cr.commit()

    print("API01 HVR 前置记录已通过 Odoo ORM 创建并提交。")
    print("RUN=%s" % RUN)
    print("OWNER_A=%s OWNER_B=%s OWNER_AUTO=%s" % (OWNER_A, OWNER_B, OWNER_AUTO))
    print("PROJECT_ID=%s WAREHOUSE_CODE=%s" % (project.id, warehouse.code))
    print("USER_ID=%s API_USER_ID=%s" % (user.id, api_user.id))
    print("NO_PROJECT_USER_ID=%s API_USER_ID=%s" % (no_project_user.id, no_project_api_user.id))
    print("PRODUCT_A_ID=%s PRODUCT_B_ID=%s PRODUCT_AUTO_ID=%s" % (
        product_a.id, product_b.id, product_auto.id,
    ))
    print("Bearer Token 和登录密码已写入本地权限为 0600 的隐藏文件，不会打印到终端。")


prepare_api01_hvr()
