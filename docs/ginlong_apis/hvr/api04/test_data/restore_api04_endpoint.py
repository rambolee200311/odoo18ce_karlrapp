"""通过 Odoo ORM 恢复 API04 临时 Endpoint 配置。"""

import json
from pathlib import Path


PARAM_KEY = "ginlong_apis.api04_callback_url"
BACKUP_FILE = Path("docs/ginlong_apis/hvr/api04/test_data/.api04_endpoint_backup").resolve()

if not BACKUP_FILE.exists():
    raise RuntimeError("未找到 API04 Endpoint 备份；拒绝更改设置。")
with BACKUP_FILE.open("r", encoding="utf-8") as stream:
    backup = json.load(stream)
if not isinstance(backup, dict) or "existed" not in backup:
    raise RuntimeError("API04 Endpoint 备份格式错误；拒绝恢复。")

params = env["ir.config_parameter"].sudo()
if backup["existed"]:
    params.set_param(PARAM_KEY, backup.get("value") or "")
else:
    params.search([("key", "=", PARAM_KEY)]).unlink()
env.cr.commit()
if backup["existed"] and params.get_param(PARAM_KEY) != (backup.get("value") or ""):
    raise RuntimeError("Endpoint ORM 回读验证失败。")
BACKUP_FILE.unlink()
print("API04 Endpoint 已通过 Odoo ORM 恢复；未输出被恢复的原地址。")
