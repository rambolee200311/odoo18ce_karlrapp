# ATR-GIN-008 — 验收测试记录

| 用例 / 验收项 | 状态 | 实际结果与证据 |
|---|---|---|
| TV-008 ORM 有效键只读盘点 | PASS | [TV-GIN-008-v0.1.md](../context/report/TV-GIN-008-v0.1.md)：API01/03/05 全局有效键重复组为 0；API07 active `(owner, productCode)` 重复组为 0。 |
| TV-008 API07 归档变体恢复 | PASS | ORM savepoint 中临时创建、归档并恢复同一 `product.product` ID，随后回滚；无持久测试记录。 |
| CC-TEST-071 首次 Add 及生命周期幂等记录 | PASS | `/private/tmp/ccgin008_ginlong_full_r13.log` 中 `74 post-tests` 全部通过；真实 Ginlong HTTP 路由断言 API01/03/05/07 记录及幂等行为。 |
| CC-TEST-072/073 有效对象重复 Add（相同/不同 Payload） | PASS | R13 API HTTP/ORM 测试断言返回重复错误、业务对象及历史行不变。 |
| CC-TEST-074/075 取消/归档后相同/不同 Payload 再 Add | PASS | R13 API01/03/05 生命周期 HTTP 测试；新增 API07 真实 HTTP 用例验证归档后同/不同 Payload 再 Add 均恢复同一变体 ID。 |
| CC-TEST-076/077 新周期再次重复、多轮生命周期和历史保留 | PASS | R13 生命周期测试检查有效记录数量、历史取消记录及幂等记录；模块升级前后 ORM ID 快照也核对保留。 |
| CC-TEST-078/079 并发相同/不同 Payload | PASS | `/private/tmp/ccgin008_effective_concurrency_targeted_r6.log` 与 R13：两个独立 ORM cursor/transaction 竞争；API01/03/05/07 × 相同及不同内容均只产生一个有效业务对象，竞争者收到相应重复错误。Human Review 确认该独立事务并发测试满足本 CC 并发验收要求。 |
| CC-TEST-080 Delete 取消及 project 权限边界 | PASS | R12 HTTP/ORM 生命周期用例验证当前 project 的订单取消及重复删除；不同 project 的已取消历史不改变对象定位。 |
| CC-TEST-081 Edit 与其余 Ginlong API 回归 | PASS | `/private/tmp/ccgin008_ginlong_full_r13.log`：Ginlong 全模块 `74` 个 post-tests，`0 failed, 0 error(s)`；包含 API01/03/05/07 Edit 和 API01–10 回归。 |
| CC-TEST-082 存量有效键预检及升级后保留性 | PASS | 预检 `/private/tmp/ccgin008_pre_upgrade_effective_key_preflight_20261124_r2.log`：API01/03/05/07 重复有效键组均为 0，ORM 只读且无记录修改。升级命令及模块加载见 `/private/tmp/ccgin008_human_review_retention_upgrade_r1.log`。升级前后快照 `/private/tmp/ccgin008_keyfields_before_20261124.json`、`/private/tmp/ccgin008_keyfields_after_20261124.json`；比较结果六类记录均 missing/added/changed=0：inbound 8、outbound 1、stocktake 1、product.product 29、幂等 17、WorldDepot API 日志 287。 |
| CC-TEST-083 跨 project 全局订单键 | PASS | `/private/tmp/ccgin008_cross_project_targeted_r2.log`：1 个定向测试通过；API01/03/05 同订单号在不同 project 被全局拒绝，且响应不泄露源单据详情；创建的订单归属仍按当前 API User project。 |
| Odoo Registry / 模块版本 | PASS | `odooce_karlrapp` 中 ORM 快照报告 `ginlong_apis=installed / 18.0.2.0.42`。8099 PID 47141 在升级后于 `/private/tmp/ginlong_8099_current.log` 记录 `Modules loaded`、`Registry loaded`；同一 PID 随后处理 `/web/login` 并返回 HTTP 200。 |
| 多 Worker HTTP 并发验收 | N/A（本 CC）/ Deferred（最终集成） | Human Review 认可 CC-TEST-078/079 独立数据库事务并发证据，明确不要求本 CC 再做多 Worker HTTP 并发。部署级验证移交最终项目集成验收；本 CC 不将其记为 PASS。 |
| 人工 HVR-GIN-008-01 至 06 | N/A（本 CC）/ Deferred（最终集成） | Human Review 取消本底层机制 CC 的独立人工 HVR 要求。完整业务流程人工验证移交最终项目集成验收；本 CC 未执行人工 HVR，不记为 PASS。 |
| HVR 可执行测试包 | N/A（本 CC 不设人工门禁） | [CC-GIN-008 HVR 包](../ginlong_apis/hvr/cc_gin_008/README.md) 保留为后续集成参考；既有 11 个 Payload 静态契约预检结果不等于人工 HVR。 |
| 模板同步 | BLOCKED | 模板来源缺失；沿用已批准流程例外，不记为 PASS。 |

## API01 Delete + Add 补充覆盖（2026-11-24）

本节为关闭后按项目负责人要求补充的 API01 回归断言，不改变 CC-GIN-008 关闭状态或已批准业务规则。

| 场景 | 状态 | 证据 |
|---|---|---|
| 首次 Add → Delete → 取消后相同报文 Add → Delete | PASS | `/private/tmp/api01_delete_add_lifecycle_targeted_r2.log`：真实 Ginlong HTTP 路由和 ORM 断言通过。 |
| 首次有效记录取消后，不同报文 Add → Delete | PASS | 同一真实 HTTP 用例断言不同报文创建独立历史订单，随后 Delete 成功；最终三条历史单据均 cancel，0 条有效业务键，3 条 Add 与 3 条 Delete 幂等记录均保留。 |
| 重复 Delete | PASS | 最后一轮 Delete 重发复用相同事件结果，不新增业务副作用；对应幂等记录数保持按每个业务生命周期一条。 |
| 人工 HVR 场景 | PREPARED / NOT RUN | [HVR-008-01 API01](../ginlong_apis/hvr/cc_gin_008/HVR_GIN_008_Test_Cases.md) 已列出两轮完整生命周期；实际人工请求未执行，仍按 CC-008 的 Human Review 决定不作为其关闭门禁。 |

定向测试首次运行 R1 因该测试累计 HTTP 请求超过限流窗口，后续非法字段断言得到 429 而失败；使用现有限流重置测试辅助方法隔离后，R2 为 1 post-test、0 failed、0 error。失败证据保留于 `/private/tmp/api01_delete_add_lifecycle_targeted_r1.log`。

## 运行摘要

- Ginlong 模块最终完整回归：74 post-tests，0 failed，0 errors；日志：`/private/tmp/ccgin008_ginlong_full_r13.log`。
- WorldDepot 回归：8 post-tests，0 failed，0 errors；日志：`/private/tmp/ccgin008_worlddepot_regression_r2.log`。
- 并发定向验证：1 个测试通过，覆盖四 API、相同及不同请求内容、独立数据库事务；日志：`/private/tmp/ccgin008_effective_concurrency_targeted_r6.log`。
- 跨 project 定向验证：1 个测试通过；日志：`/private/tmp/ccgin008_cross_project_targeted_r2.log`。
- 有效键升级前预检：`/private/tmp/ccgin008_pre_upgrade_effective_key_preflight_20261124_r2.log`，四类键均为 0 个冲突组。
- 模块升级后保留性：升级前后六类 ORM 记录关键字段逐条一致；比较结果 PASS，升级日志：`/private/tmp/ccgin008_human_review_retention_upgrade_r1.log`。
- 当前 8099 服务：PID 47141 仍指向 `odooce_karlrapp`；升级后的 Registry 加载及 `/web/login` HTTP 200 见 `/private/tmp/ginlong_8099_current.log`；模块版本 `18.0.2.0.42`。
- HVR 请求文件：11 个 JSON 均通过 `ginlong_apis.validators.payload_validator.validate_payload`（Required + Type）检查；调用脚本通过 `bash -n`。该预检只证明字段结构/类型有效，不等同真实 HTTP 或人工业务验收。

## 当前结论

CC-GIN-008 的冻结范围验收已满足。项目负责人于 2026-11-24 批准关闭，FR-GIN-008 记录 Closure SATISFIED / Human Review APPROVED，CC 状态为 **Closed**。多 Worker HTTP 并发与独立人工 HVR 为本 CC 的 N/A，并移交最终项目集成；两项均未伪记为 PASS。部署前 ORM 有效键预检、升级后业务/幂等/API 日志保留性及本地 8099 `.42` Registry 加载均已验证。模板同步 BLOCKED 继续沿用已批准流程例外。

## Human Review 补充规则收尾验收（2026-11-24）

Human Review 决定：API01/03/05 的 Del 必须先判断当前有效业务记录；没有有效记录（包括仅有 cancel 历史）时返回业务错误，不重放历史成功结果。此补充纳入 CC-GIN-008 收尾，不改变 API01/03/05 的业务键、project 权限、历史保留或其他规则。以下结果更新该补充验收；早前“重复 Del 重放成功”的测试记录保留为历史，已由本规则取代。

| 场景 | 状态 | 实际证据 |
|---|---|---|
| API01：首次 Del 成功；同/不同 Payload 再 Del 返回 `BUS01`；重新 Add 后 Del 成功 | PASS | `/private/tmp/ccgin008_del_validity_20261124_r3.log`：真实 HTTP 路由及 ORM 断言；订单历史、有效键、幂等行均核对 |
| API03：首次 Del 成功；同/不同 Payload 再 Del 返回 `BUS01`；取消后 Edit 被拒；重新 Add 后 Del 成功 | PASS | 同一 R3 全模块测试日志；`test_http_api03_valid_owner_product_add_edit_delete_and_rejection` |
| API05：首次 Del 成功；同/不同 Payload 再 Del 返回 `BUS01`；取消后 Edit 被拒；相同及不同 Payload 重新 Add 后均可 Del | PASS | 同一 R3 全模块测试日志；`test_http_api05_add_repeatable_edit_and_delete` |
| 重复 Del 不新增成功幂等记录；历史订单及既有幂等记录保留 | PASS | 三个 HTTP 用例均核对 Del 幂等记录数、cancel 历史；拒绝重试不增加成功记录 |
| Ginlong 完整自动化回归 | PASS | R3：74 post-tests、0 failed、0 error(s)，14,126 queries；完整命令及日志见 IHR |
| 8099 重启后模块版本 | PASS | ORM 只读显示 `installed / 18.0.2.0.43`；最终重启 PID 65649 的 Registry 加载日志及 `/web/login` HTTP 200 |
| 人工 HVR | N/A（本 CC）/ Deferred（最终集成） | 沿用 Human Review 对 CC-GIN-008 的决定；本轮未执行人工 HVR |

R1 首轮回归保留失败证据：API05 用例连续请求触发测试限流，导致重新 Add 收到 429 并产生 1 个测试 error；不是业务错误。测试改用现有限流重置辅助方法后，R2 全量回归为 74 post-tests、0 failed、0 error。之后为 API05 增加“不同 Payload 重新 Add 后 Del 成功”断言，R3 再次全量回归通过。模板同步仍 BLOCKED，沿用批准例外。

## Human Review 收尾决定（2026-11-24）

Human Review：**APPROVED**；项目负责人李建强；批准既有独立事务并发证据作为本 CC 并发验收，并取消本 CC 独立人工 HVR 和多 Worker HTTP 验收门槛。

Human Review 关闭决定：**APPROVED**；项目负责人李建强；2026-11-24；批准 FR-GIN-008 并关闭 CC-GIN-008。

| 决定 | 当前处理 |
|---|---|
| 独立数据库事务并发测试满足本 CC 并发要求 | CC-TEST-078/079 保持 PASS；不再要求多 Worker HTTP 并发测试 |
| 取消本 CC 独立人工 HVR | HVR-GIN-008-01 至 06 标为 N/A（本 CC），完整业务人工验证 Deferred 至最终项目集成 |
| 存量有效键预检纳入部署步骤 | 已纳入 `scripts/cc_gin_008/README.md`；发现重复组必须停止升级，不自动修改业务数据 |
| 升级前后历史记录保留核验 | 已通过 ORM 快照验证业务、幂等及 API 日志关键字段；六类记录无新增、丢失或字段变化 |
| 本地运行服务加载版本 | 8099 PID 47141 的升级后 Registry 加载日志及 HTTP 200 已核实；数据库模块版本为 `18.0.2.0.42` |
| 模板同步 | 继续 BLOCKED；沿用已批准流程例外，不记 PASS |

当前处置：已生成 [FR-GIN-008 关闭评审稿](FR-GIN-008.md)，等待项目负责人 Human Review；尚未将 CC 标记为 Closed。
