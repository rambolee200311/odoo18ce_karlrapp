"""加载 Ginlong 静态字段规则并提供通用 Action 条件匹配。"""

import json
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def get_field_rules():
    """读取模块中的只读字段配置，不访问 Odoo ORM 或数据库。"""
    path = Path(__file__).resolve().parents[1] / "data" / "field_rules.json"
    with path.open(encoding="utf-8") as config_file:
        return json.load(config_file)


def action_for(api_config, payload):
    """使用字段配置中的别名表归一化 Action 规则键，不改写 Payload。"""
    value = payload.get(api_config.get("action_field", "action"))
    if not isinstance(value, str):
        return None
    normalized = value.strip().casefold()
    return api_config.get("action_aliases", {}).get(normalized, normalized)


def action_matches(actions, action):
    """判断 Action 条件列表是否命中当前动作。"""
    return "*" in actions or action in actions
