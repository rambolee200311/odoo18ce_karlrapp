"""使用 Odoo ORM 备份并配置本地 API04 Mock Endpoint。"""

import json
import os
from pathlib import Path


PARAM_KEY = "ginlong_apis.api04_callback_url"
MOCK_URL = "http://127.0.0.1:18104/API/WMS_JSON/TPL_Inbound_Completion"
BACKUP_FILE = Path("docs/ginlong_apis/hvr/api04/test_data/.api04_endpoint_backup").resolve()

if BACKUP_FILE.exists():
    raise RuntimeError("API04 Endpoint 备份已存在；请先核查并恢复，不覆盖既有备份。")

params = env["ir.config_parameter"].sudo()
record = params.search([("key", "=", PARAM_KEY)], limit=1)
backup = {"existed": bool(record), "value": record.value if record else None}
descriptor = os.open(str(BACKUP_FILE), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
    json.dump(backup, stream, ensure_ascii=False)
    stream.write("\n")
os.chmod(BACKUP_FILE, 0o600)

params.set_param(PARAM_KEY, MOCK_URL)
env.cr.commit()
if params.get_param(PARAM_KEY) != MOCK_URL:
    raise RuntimeError("ORM 回读 Endpoint 与本地 Mock 地址不一致。")
print("API04 Endpoint 已经 Odoo ORM 更新；原值仅保存于权限 0600 的本地备份。")
print("当前配置为本机回环 Mock。")
