# Ginlong API Implementation Plan v1.2

| 项目 | 内容 |
|---|---|
| 版本 | v1.2 执行补充 |
| 状态 | CC-GIN-003 In Progress |
| 日期 | 2026-11-18 |
| 历史计划 | v1.0 Frozen、v1.1 执行补充均保留原文 |
| 当前设计输入 | [SRS v1.0](../requirement/SRS_ginlong_apis.md)、[TDD v0.5](../ginlong_apis/TDD-v0.5.md)、[CC-GIN-003 v1.2](CC-GIN-003-v1.2.md) |
| 模板同步 | BLOCKED；已批准模板缺失例外仍有效，不作为 PASS |
| 执行授权 | 本地开发、Odoo 自动化与 Mock HTTP；无真实 Ginlong/生产访问授权 |

本补充延续原实施计划，只更新本轮回传界面和证据。Ginlong/Odoo/Karl Rapp 的职责边界不变；不重跑已通过的 CC-TEST-010/017/019，不覆盖历史实施计划。

## 1. 当前交付

- 五个人工回传接口移除回传 Wizard，改用既有业务 Form 的「Ginlong 回传数据」Notebook；按钮只读取已保存 ORM 记录。
- 在既有 `stock.move.line`、`world.depot.stocktake.order`、`world.depot.stocktake.result` 上保留满足必填字段的最小持久化字段；没有新增平行回传或盘点模型。
- 固定 POST / `application/json`，API02=`UPDATE`，API04/06/08=`CREATE`，API10=`Add`/`Del`（不区分 Action 大小写）；同步发送，15 秒超时，无自动重试。
- 每个按钮尝试调用现有 API 日志新增独立记录，不修改旧日志；失败后允许修改已保存数据再发送。
- 按项目已登记的 Wizard/Form 认知，只有一次性参数选择适用 Wizard；需长期保存及失败后修改重试的回传数据使用持久化 Form，发送按钮仅读已保存 ORM 数据。
- ATR-RUN-032：七项指定 Odoo post-tests、0 failed / 0 error；ATR-RUN-033：ORM 核对模块版本、持久化字段、无回传 Wizard 和四个 Form 视图。仅使用 Mock HTTP；真实接口和完整人工 E2E 未执行。

## 2. 当前分项状态

| 项目 | 状态 | 下一步 |
|---|---|---|
| CC-TEST-001–006：持久化 Form、API04/API10 保存/重读/发送、失败重试和日志 | 本地自动化通过 | 按字段级契约补齐后扩展映射；保留现有证据 |
| CC-TEST-007：API02/06/08 Open Item 隔离 | 组件测试通过；各自完整 Payload 仍受字段问题阻塞 | 只在收到确切映射后实现对应字段，不影响已可模拟接口 |
| API04 正常完成回传 | 本地 Mock 成功、HTTP 失败及编辑后重发通过 | Ginlong 确认的多 picking/撤销/时间语义留待联调确认 |
| API10 实盘完成回传 | 本地 Mock Add/Del、实盘行持久化选择通过 | 外部撤销/部分采集范围仍按 V3.2 Open Items |
| CC-TEST-024 `worlddepot` 保留能力回归 | 按既有 ATR/IHR 状态继续跟踪 | 执行受修改影响的自动化回归；不得用本轮七项回传测试替代 |
| 完整人工 WMS E2E | 留最终集成 CC | 需要时另立最终集成验证，不在本轮伪记通过 |
| Ginlong 真实环境 | 未授权 / NOT RUN | 等待单独授权和正式联调准备 |

## 3. 环境及证据

- 使用项目既有 `odoo.conf`、`venv`、数据库 `odooce_karlrapp`，通过 Odoo 标准测试运行器及 ORM；不直接访问 PostgreSQL、不建新环境、不使用 `stock_barcode`。
- 最终有效命令、执行结果和失败尝试保留于 [ATR-GIN-003](ATR-GIN-003.md)；实施事实追加于 [IHR-GIN-003](IHR-GIN-003.md)。
- 未确认字段及接口语义按 CC-GIN-003 v1.2 §5 和 TDD v0.5 §4 分接口跟踪；任何未验证核心字段不标记 PASS。

## 修订记录

| 版本 | 日期 | 修订 | 状态 |
|---|---|---|---|
| v1.2 | 2026-11-18 | 追加持久化 Form/Notebook 实施基线和 ATR-RUN-032/033；记录 Wizard/Form 项目认知，明确 API02/06/08 独立 Open Items、CC-TEST-024 回归、最终人工 E2E 及真实接口授权边界 | Active Execution |
