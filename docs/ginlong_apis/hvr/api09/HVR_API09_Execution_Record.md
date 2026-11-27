# API09 项目级 HVR 执行记录

**状态：** 所有用例 `NOT RUN`。业务验收人填写实际结果；不得以静态检查或自动化结果代填。

## 主线库存快照

| Case | 业务时间点 | Payload / 同一数据集 | API 响应与目标 SKU 数量 | 前后库存未改变 | API Log ID | 判定 / 执行人时间 |
|---|---|---|---|---|---|---|
| FLOW-09A | API07 后、实际入库前 | `project_flow/test_data/payloads/api09_owner_warehouse_query.json` | — | — | — | NOT RUN |
| FLOW-09B | FLOW-IN Incoming Picking Done 后 | 同上 | — | — | — | NOT RUN |
| FLOW-09C | FLOW-SHIP Outgoing Picking Done 后 | 同上 | — | — | — | NOT RUN |

只核对 `HVR-PROJECT-FLOW-20261125-SN-001`；完整 `inventoryList` 可包含同 Owner/仓库的其他既有产品。期望数量 0（或没有正库存行）、2、1。若实际 Picking 数量不符，停止并记录；禁止改 quant 来对齐预期。

## 参数隔离专项

| Case | 请求文件 | 实际 HTTP 状态/响应 | 哨兵库存及隔离结果 | API Log ID | 判定 / 执行人时间 |
|---|---|---|---|---|---|
| API09-HVR-UNK-OWNER | `project_flow/test_data/payloads/api09_unknown_owner.json` | — | — | — | NOT RUN |
| API09-HVR-UNK-WH | `project_flow/test_data/payloads/api09_unknown_warehouse.json` | — | — | — | NOT RUN |
| API09-HVR-MISSING-OWNER | `project_flow/test_data/payloads/api09_missing_owner.json` | — | — | — | NOT RUN |
| API09-HVR-MISSING-WH | `project_flow/test_data/payloads/api09_missing_warehouse.json` | — | — | — | NOT RUN |

未知 Owner 按当前服务实现预期成功返回空 `inventoryList`；若需证明已有其他货主库存不会泄露，必须找到数据库中现存的同仓哨兵库存。若没有哨兵，不创建/调整库存，该隔离断言记 `BLOCKED`。未知 Warehouse 预期 BUS01 错误且无 `inventoryList`。所有异常请求都须核对库存数据不变。
