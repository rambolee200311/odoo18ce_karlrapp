"""通过 Odoo ORM 恢复配置前的 API02 Endpoint。

在项目根目录执行：
    ./venv/bin/python odoo-bin shell -c odoo.conf -d odooce_karlrapp --no-http \
      < docs/ginlong_apis/hvr/api02/test_data/restore_api02_endpoint.py

只有确认人工 HVR 已结束后才运行；脚本不会打印被恢复的原 URL。
"""

import json
from pathlib import Path


PARAM_KEY = "ginlong_apis.api02_callback_url"
BACKUP_FILE = Path("docs/ginlong_apis/hvr/api02/test_data/.api02_endpoint_backup").resolve()

if not BACKUP_FILE.exists():
    raise RuntimeError("No API02 Endpoint backup found; refusing to change configuration.")

with BACKUP_FILE.open("r", encoding="utf-8") as stream:
    backup = json.load(stream)
if not isinstance(backup, dict) or "existed" not in backup:
    raise RuntimeError("API02 Endpoint backup has an invalid format; refusing to change configuration.")

params = env["ir.config_parameter"].sudo()
if backup["existed"]:
    params.set_param(PARAM_KEY, backup.get("value") or "")
else:
    params.search([("key", "=", PARAM_KEY)]).unlink()
env.cr.commit()
BACKUP_FILE.unlink()
print("API02 Endpoint restored through ORM; temporary backup removed.")
