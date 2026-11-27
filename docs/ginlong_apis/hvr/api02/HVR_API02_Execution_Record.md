# API02 收货确认 HVR 执行记录

> 旧记录及其 NOT RUN 行保留为历史；当前 CC-GIN-009 操作按文末“冻结后当前场景”记录。CC-009 不设独立人工 HVR，项目人工验收仍待 CC 关闭后执行。

> **人工验收状态：NOT RUN。** 执行者须为项目负责人/业务验收人。Codex 不点击回传按钮，不填写 PASS/FAIL。

## 环境记录

| 项目 | 记录 |
| --- | --- |
| Odoo 数据库 | `odooce_karlrapp` |
| Odoo Backend | `http://127.0.0.1:8099/odoo`（执行前确认服务可用） |
| API02 Mock Endpoint | `http://127.0.0.1:18102/API/WMS_JSON/TPL_Receipt_Confirmation` |
| Mock 捕获文件 | `docs/ginlong_apis/hvr/api02/test_data/received.jsonl` |
| Ginlong 真实环境 | 未连接；本 HVR 不访问真实 Ginlong |
| 执行者 / 日期 | 待人工填写 |

## 执行前 ORM 只读核查（不是 HVR 结果）

- 此前被错误指引的 Inbound Order ID `334` / Reference `HVR-GIN005-IN-001` 是 CC-GIN-007 历史测试单，关联 Picking 已为 `done`；本 API02 HVR 排除它，本轮未修改它。
- Project、非 SN 产品、Incoming Picking Type 和测试 Reference 已通过 ORM 只读核实；具体新建步骤见测试实例。Codex 未创建或修改任何业务订单、Picking、明细、库存、日志或幂等记录。
- 人工 HVR 尚未开始；所有实例保持 NOT RUN。

## 实例结果

| HVR | 场景 | 状态（初始 NOT RUN） | Order ID / Reference | Mock 捕获行/结果 | API 日志 ID | 人工证据/备注 |
| --- | --- | --- | --- | --- | --- | --- |
| HVR-API02-01 | 全部明细 Y | NOT RUN |  |  |  |  |
| HVR-API02-02 | 全部明细 N | NOT RUN |  |  |  |  |
| HVR-API02-03 | 混合 Y/N，本地阻止发送 | NOT RUN |  |  |  |  |
| HVR-API02-04 | 相同成功事件重复点击 | NOT RUN |  |  |  |  |
| HVR-API02-05 | 无收货明细，本地阻止发送 | NOT RUN |  |  |  |  |

## 人工确认

- 人工验收结论：待填写（PASS / FAIL / BLOCKED）。
- 验收人：待填写。
- 日期：待填写。
- 备注：待填写。

## CC-GIN-009 冻结后当前场景（人工 HVR 尚未开始）

| 场景 | 预期 | 状态 | Order Reference | Mock 捕获 | API 日志 ID | 证据 |
|---|---|---|---|---|---|---|
| HVR-API02-C01 planning→N | 订单 status 保持 planning；收到 receiptConfirmed=N | NOT RUN |  |  |  |  |
| HVR-API02-C02 收货确认后 arrive→Y | 点击业务按钮只改 status、不改 state；收到 receiptConfirmed=Y | NOT RUN |  |  |  |  |
| HVR-API02-C03 现有 WMS inbound→Y（可选） | 若既有流程生成 inbound，则回传 Y；不为测试伪造状态 | NOT RUN |  |  |  |  |
| HVR-API02-C04 相同状态再次点击（可选） | 按现有 Event/Log 机制核对实际发送行为 | NOT RUN |  |  |  |  |

人工验收人填写本表；Codex 不代填 PASS/FAIL。API02 本地 Mock 不代表真实 Ginlong 联调。

## CC-GIN-010 项目级重复回传场景

人工 HVR 使用独立订单 `HVR-GIN010-MANUAL-IN-20261125-01`（Order ID `2011`，Bill No `IO202611251978`），不使用 Codex 模拟单 `SIM-GIN010-IN-20261125-01`。通过 API02 首发、重复成功后的取消/确认、明确失败重试、unknown 风险确认及跨标签页连续点击；具体操作和每个 Mock 行数预期见[通用 HVR 执行记录](../HVR_Callback_Repeat_Confirmation_Execution_Record.md)。

| 场景 | 状态 | Mock 行增量 | API Event / Log | 人工证据 |
|---|---|---|---|---|
| HVR-REP-01 API02 成功后取消重复确认 | NOT RUN |  |  |  |
| HVR-REP-01 API02 确认后实际重发 | NOT RUN |  |  |  |
| HVR-REP-02 API02 明确失败重试 | NOT RUN |  |  |  |
| HVR-REP-02 API02 unknown 风险取消/确认 | NOT RUN |  |  |  |
| HVR-REP-08 API02 连续点击/跨标签页并发 | NOT RUN |  |  |  |
