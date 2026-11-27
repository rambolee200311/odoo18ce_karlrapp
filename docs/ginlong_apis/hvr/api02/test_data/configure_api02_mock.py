"""通过 Odoo ORM 安全备份并设置 API02 本地 Mock Endpoint。

在项目根目录执行：
    ./venv/bin/python odoo-bin shell -c odoo.conf -d odooce_karlrapp --no-http \
      < docs/ginlong_apis/hvr/api02/test_data/configure_api02_mock.py

脚本使用 Odoo shell 提供的 `env`，不直接访问 PostgreSQL。
"""

import json
import os
from pathlib import Path


PARAM_KEY = "ginlong_apis.api02_callback_url"
MOCK_URL = "http://127.0.0.1:18102/API/WMS_JSON/TPL_Receipt_Confirmation"
BACKUP_FILE = Path("docs/ginlong_apis/hvr/api02/test_data/.api02_endpoint_backup").resolve()

if BACKUP_FILE.exists():
    raise RuntimeError("Endpoint backup already exists; inspect it and restore before reconfiguring.")

params = env["ir.config_parameter"].sudo()
record = params.search([("key", "=", PARAM_KEY)], limit=1)
previous_value = record.value if record else None
backup = {"existed": bool(record), "value": previous_value}
descriptor = os.open(str(BACKUP_FILE), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
    json.dump(backup, stream, ensure_ascii=False)
    stream.write("\n")
os.chmod(BACKUP_FILE, 0o600)

params.set_param(PARAM_KEY, MOCK_URL)
env.cr.commit()
if params.get_param(PARAM_KEY) != MOCK_URL:
    raise RuntimeError("ORM read-back did not match the local API02 Mock URL.")
print("API02 Endpoint updated through ORM; prior value backup is permission 0600.")
print("Configured URL: %s" % MOCK_URL)
