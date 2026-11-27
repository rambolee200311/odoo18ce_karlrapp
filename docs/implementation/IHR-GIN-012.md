# IHR-GIN-012 — 实施历史记录

| 项目 | 内容 |
|---|---|
| CC | [CC-GIN-012 v1.0 Frozen](CC-GIN-012-v1.0.md) |
| 实施状态 | **Closed；Closure SATISFIED；Human Review APPROVED（2026-11-25）** |
| 日期 | 2026-11-25 |
| 数据库 | 本地开发库 `odooce_karlrapp` |
| Ginlong 模块 | `18.0.2.0.49` |
| WorldDepot 模块 | `18.0.0.6` |
| 计划基线 | [Implementation Plan v2.8 Frozen](IMPLEMENTATION_PLAN_ginlong_apis-v2.8.md)；CC-GIN-012 为阶段 4F |
| 测试报告 | [ATR-GIN-012](ATR-GIN-012.md) |
| 关闭记录 | [FR-GIN-012 v1.0](FR-GIN-012.md) |

## 1. 实施范围与边界

按冻结 CC-GIN-012 完成同一测试 Project、owner、`KRWH`、Ginlong `productCode` 与 `product.product` 变体贯穿 API01–API10 的自动化业务主链。入站接口经真实 Odoo HTTP 路由；出站接口通过实际 Odoo 回传入口向本地 Mock HTTP 接收端发出 `POST application/json`。库存只由标准 Incoming/Outgoing `stock.picking` Done 操作产生。

没有访问真实 Ginlong、生产或 Karl Rapp Gateway；没有组织独立人工 HVR；没有清理人工 HVR 数据；没有清理、提交或推送 Git。

## 2. 缺陷调查与最小修复

### 2.1 收货确认操作记录

主链实际调用 `inbound.action_mark_arrived()`，检查 `status=arrive`、订单生命周期 `state=confirm`、API02 的 `receiptConfirmed=Y`，并要求 Chatter 留下收货确认操作记录。状态值正确且库存不变，但 Odoo 自动字段跟踪没有形成可见的 `status` 操作消息，CC-TEST-144 因此失败。

只修改 `worlddepot` 的 `action_mark_arrived()`：仍只写入业务 `status`，用 `mail_notrack=True` 避免自动跟踪消息合并，再显式追加包含原状态、目标状态的中文 Chatter note。没有改变生命周期、库存或 API02 映射。修复后主链断言确认消息存在、包含 planning 与 arrive，作者为当前操作用户。

### 2.2 盘点测试数据来源

代码审查发现早期主链测试通过 `stock.quant` 查找盘点计划和实盘结果的 SN/托盘。这不符合 CC-TEST-155。已改为从前序 Done Incoming Picking 的 move line 获取剩余 SN 与 `result_package_id`，再写入客户盘点指令及现有实盘结果模型。`stock.quant` 仅用于只读库存快照，不生成盘点数据或 API10 Payload。

### 2.3 标准出库 SN 作业

测试发现标准出库 reservation 可能先预留未带 Lot 的数量；实际仓库扫描后才在作业行确定 SN。测试通过现有 outgoing Picking 作业行录入此前实际收货的一个 SN，再执行标准 Picking 完成。未直接写入/创建/修改 `stock.quant`，未新增业务规则。

## 3. 事务、HTTP 与测试隔离

- 自动化主链使用 Odoo `HttpCase` 对真实路由发 HTTP 请求；五个出站 API 由真实业务回传入口发送到仅监听本机的 Mock Receiver。
- 测试业务夹具、订单、Picking、SN、托盘及实盘结果带运行级唯一标记，并处在 Odoo 测试事务中。teardown 通过独立 ORM cursor 仅清理该测试标记的已提交 API Log、幂等与限流行，并断言日志和限流清零。
- 独立 API Log cursor 行为由集成测试验证：用新 ORM cursor 观察已提交日志，再用 ORM 删除唯一标记并提交。HttpCase Registry TestCursor 对测试内事务的代理与生产路径独立提交不同；没有宣称测试游标等于生产独立事务。
- 最终运行后通过 Odoo Shell ORM 检查 `GINLONG-HTTP-`、`GINLONG-CC012-LOG-` 标记：API Log、幂等、入库单、出库单、盘点单、产品及 Picking 均为零残留。
- 使用现有 `odoo.conf`、venv 和 `odooce_karlrapp`。最初受限执行环境拒绝本地 DB 端口连接；在审批本地数据库访问后，同一 Odoo 测试命令完成运行，没有新建数据库。

## 4. 实际结果

- 最终 Ginlong 回归 `/private/tmp/cc_gin_012_ginlong_final4.log`：93 post-tests，0 failed，0 error；模块统计 97 tests、18,067 queries。
- 最终 WorldDepot 回归 `/private/tmp/cc_gin_012_worlddepot_final2.log`：8 post-tests，0 failed，0 error；模块统计 12 tests、112 queries。
- 主链单独运行 `/private/tmp/cc_gin_012_targeted_final9.log`：1 post-test，0 failed，0 error，1,631 queries。
- 最终 Odoo Shell ORM 核实 Ginlong `installed_version=latest_version=18.0.2.0.49`，WorldDepot `installed_version=latest_version=18.0.0.6`。
- 开发用 8099 仍由既有 PID 20853 监听，没有重启或停止。

CC-TEST-140～157 的实际运行证据和断言映射见 [ATR-GIN-012 §2](ATR-GIN-012.md#2-cc-test-140157-证据映射)。早期失败 RUN 保留于 ATR，不被最终通过记录覆盖。

## 5. 后续边界

CC-GIN-012 自动化及组件集成验收已通过并正式关闭。CC-GIN-005 浏览器模拟 E2E、负责人真实人工 HVR 和指南修订仍需执行；不得以本 CC 自动化结果替代。真实 Ginlong/KR 联调继续 Deferred；模板同步继续 `BLOCKED` 并沿用已批准例外，不伪记 PASS。

## 6. 关闭记录（2026-11-25）

- Human Review：**APPROVED**；项目负责人批准 Closure SATISFIED 并正式关闭 CC-GIN-012。
- CC-TEST-140～157 全部自动化/组件集成验收通过；正式报告见 [ATR-GIN-012](ATR-GIN-012.md)。
- 后续项目级 UI/WMS 模拟 HVR 与真实人工 HVR 返回 CC-GIN-005；本 CC 的测试结论不代替人工验收。
