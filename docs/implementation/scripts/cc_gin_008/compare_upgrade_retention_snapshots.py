"""比较两个脱敏 ORM 快照；发现业务/幂等/API 日志变化时返回非零状态。"""

import json
import sys
from pathlib import Path


def load(path):
    """读取并解析一份 ORM 快照 JSON。"""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def compare(before, after):
    """比较关键历史记录；模块版本元数据单独输出，不作为数据保留差异。"""
    failures = []
    if before.get("module", {}).get("state") != after.get("module", {}).get("state"):
        failures.append(("module.state", before.get("module"), after.get("module")))
    for name in ("inbound", "outbound", "stocktake", "products", "idempotency", "api_logs"):
        old_rows = before.get(name, [])
        new_rows = after.get(name, [])
        old_by_id = {row["id"]: row for row in old_rows}
        new_by_id = {row["id"]: row for row in new_rows}
        missing = sorted(set(old_by_id) - set(new_by_id))
        added = sorted(set(new_by_id) - set(old_by_id))
        changed = sorted(
            record_id for record_id in set(old_by_id) & set(new_by_id)
            if old_by_id[record_id] != new_by_id[record_id]
        )
        print("RETENTION", name, "before=", len(old_rows), "after=", len(new_rows),
              "missing=", len(missing), "added=", len(added), "changed=", len(changed))
        if missing or added or changed:
            failures.append((name, {"missing_ids": missing, "added_ids": added, "changed_ids": changed}))

    print("MODULE_VERSION before=", before.get("module", {}).get("installed_version"),
          "after=", after.get("module", {}).get("installed_version"))
    if failures:
        for failure in failures:
            print("RETENTION_MISMATCH", failure)
        raise SystemExit(1)
    print("CC-GIN-008 RETENTION PASS: historical business, idempotency and API log key fields are unchanged.")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("Usage: compare_upgrade_retention_snapshots.py BEFORE.json AFTER.json")
    compare(load(sys.argv[1]), load(sys.argv[2]))
