#!/usr/bin/env python3
"""格式化显示 API02/API04 本地 Mock 已捕获的请求与响应。"""

import argparse
import json
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
CAPTURE_FILES = {
    "API02": REPOSITORY_ROOT / "docs/ginlong_apis/hvr/api02/test_data/received.jsonl",
    "API04": REPOSITORY_ROOT / "docs/ginlong_apis/hvr/api04/test_data/received.jsonl",
}


def read_tail(path, count):
    """读取 JSONL 捕获文件末尾指定数量的完整记录。"""
    if not path.exists():
        return []
    records = []
    with path.open("r", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as error:
                records.append({"line": line_number, "parse_error": str(error), "raw": line.rstrip()})
            else:
                records.append(record)
    return records[-count:]


def main():
    """按接口分别格式化打印最近捕获记录，不修改任何证据文件。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tail", type=int, default=10, help="每个接口显示的最近记录数")
    args = parser.parse_args()
    if args.tail < 1:
        parser.error("--tail 必须大于 0")
    for api_name, path in CAPTURE_FILES.items():
        print("=== %s (%s) ===" % (api_name, path))
        records = read_tail(path, args.tail)
        if not records:
            print("尚无捕获记录。")
            continue
        for index, record in enumerate(records, start=1):
            print("--- %s #%s ---" % (api_name, index))
            print(json.dumps(record, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
