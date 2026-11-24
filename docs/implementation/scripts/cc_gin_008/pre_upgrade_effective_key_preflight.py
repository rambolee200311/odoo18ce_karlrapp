"""在 Odoo Shell 中只读检查 CC-GIN-008 四类存量有效业务键。"""

from collections import defaultdict


def collect_duplicate_groups(model, domain, key_getter):
    """通过 ORM 查询并返回重复键及对应记录 ID。

    参数：
        model: Odoo ORM 模型记录集。
        domain: 只选取当前有效业务记录的 ORM domain。
        key_getter: 从记录提取业务键的函数。

    返回：
        仅含重复键的映射；不写入或修复任何业务记录。
    """
    groups = defaultdict(list)
    for record in model.search(domain, order="id"):
        key = key_getter(record)
        if key:
            groups[key].append(record.id)
    return {key: ids for key, ids in groups.items() if len(ids) > 1}


def run_preflight(env):
    """扫描订单全局键及产品复合键；发现冲突时以非零错误中止部署流程。"""
    checks = [
        (
            "API01 inboundOrderNo",
            env["world.depot.inbound.order"].sudo(),
            [("state", "!=", "cancel"), ("reference", "!=", False)],
            lambda record: record.reference,
        ),
        (
            "API03 outboundOrderNo",
            env["world.depot.outbound.order"].sudo(),
            [("state", "!=", "cancel"), ("reference", "!=", False)],
            lambda record: record.reference,
        ),
        (
            "API05 countOrderNo",
            env["world.depot.stocktake.order"].sudo(),
            [("state", "!=", "cancel"), ("count_order_no", "!=", False)],
            lambda record: record.count_order_no,
        ),
        (
            "API07 owner + productCode",
            env["product.product"].sudo().with_context(active_test=False),
            [("active", "=", True), ("ginlong_owner_code", "!=", False),
             ("ginlong_product_code", "!=", False)],
            lambda record: (record.ginlong_owner_code, record.ginlong_product_code),
        ),
    ]
    conflicts = []
    for label, model, domain, key_getter in checks:
        duplicate_groups = collect_duplicate_groups(model, domain, key_getter)
        print("PREFLIGHT", label, "duplicate_groups=", len(duplicate_groups))
        for key, record_ids in duplicate_groups.items():
            details = {"key": key, "record_ids": record_ids}
            conflicts.append((label, details))
            print("CONFLICT", label, details)

    if conflicts:
        raise SystemExit(
            "CC-GIN-008 preflight found %s duplicate effective key group(s); "
            "STOP. Do not upgrade or modify business records." % len(conflicts)
        )
    print("CC-GIN-008 PREFLIGHT PASS: no duplicate effective business keys; no records were changed.")


run_preflight(env)
env.cr.rollback()
