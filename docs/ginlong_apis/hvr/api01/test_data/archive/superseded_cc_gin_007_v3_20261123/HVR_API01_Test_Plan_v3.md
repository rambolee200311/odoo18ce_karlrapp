> **已归档：本 v3 计划不再用于当前 CC-GIN-007 HVR。** 请使用 [CC-GIN-007 HVR v0.1 Draft](../cc_gin_007_v0.1_draft/README.md)。v3 的 STANDARD payload 不触发保税 snList 规则；原请求文件已移到 archive，历史结果不变。

# API01 入库单 HVR 测试计划 v3（精简必测）

| 项目 | 内容 |
|---|---|
| 状态 | 测试包已准备；5 个人工用例均 `NOT RUN` |
| 范围 | 只复验本轮 API01 SN 身份、单件数量和原材料托盘分配规则 |
| 本地接口 | `POST http://127.0.0.1:8099/api/ginlong/TPL_Pending_Receipt_Note` |
| 数据库 | 既有 `odooce_karlrapp`、`odoo.conf`、`venv` |
| 代码版本 | `ginlong_apis 18.0.2.0.39`；运行前确认服务进程已加载该版本 |

## 你只需执行的文件

按 [HVR_API01_Test_Cases.md](HVR_API01_Test_Cases.md) 的顺序执行 **5 个** curl：

1. HVR01-29：有效复杂订单，三托盘 × 三产品。
2. HVR01-30：单条真实 SN 数量不是 1，必须拒绝。
3. HVR01-31：同一真实 SN 跨托盘重复，必须拒绝。
4. HVR01-32：不同产品使用相同 SN 文本，必须允许。
5. HVR01-33：不同 API01 单据引用相同产品 SN，必须允许。

原材料、成品和半成品变体已通过 Odoo ORM 核实存在，tracking 分别为 `none`、`serial`、`serial`；无需执行额外 API07 准备请求。

## HVR01-29 主场景

| 产品 | tracking | 订单数量 | 托盘 A | 托盘 B | 托盘 C | 合计 |
|---|---|---:|---:|---:|---:|---:|
| 原材料 `HVR01-20261121-PROD-COMMON` | none | 9 | 3 | 3 | 3 | 9 |
| 成品 `HVR01-20261122-PROD-SERIAL` | serial | 6 | 2 个 SN，各 1 | 2 个 SN，各 1 | 2 个 SN，各 1 | 6 |
| 半成品 `HVR01-20261122-PROD-SEMIFINISHED` | serial | 6 | 2 个 SN，各 1 | 2 个 SN，各 1 | 2 个 SN，各 1 | 6 |

每托盘应有 5 行：原材料 1 行 + 成品 2 行 + 半成品 2 行。Odoo 必须保留 15 行的 `productCode`、SN/伪 SN、数量和 `palletCode`。原材料同一个 `productSN=productCode` 在不同托盘重复是合法分配，不得合并丢失托盘信息。

## 其他报文的处置

- HVR01-01–19、HVR01-21–28 本轮不是人工必测项，不要执行。
- 旧 v2 中未执行且本轮不需要的 27 个用例、两个 API07 准备报文和 manifest 已删除，不保留重复副本。
- v2 包中的所有用例此前都未开始人工执行；本轮只对 v3 的五个必测场景记录结果。

## 核查要求

- 只使用 Odoo Form/API 菜单和 Odoo Shell ORM 核对，不直接操作 PostgreSQL。
- 成功响应只有 `returnStatus=Y`、`exceptionInfo=OK`、`operationTime`；失败按表中预期检查。
- 成功 API01 只创建订单数据，不表示实际入库；不得生成 Picking 或库存移动。
- 失败实例确认没有 Order、明细或成功幂等记录；API 日志保留错误诊断。
- 不清理 HVR 过程中产生的业务记录、日志或幂等数据。
