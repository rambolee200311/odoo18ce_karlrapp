# Ginlong API Implementation Plan v1.4

| 项目 | 内容 |
|---|---|
| 版本 | v1.4 实施验证补充 |
| 状态 | 本地实施和自动化完成；CC-GIN-003 待 Human Review 关闭评估 |
| 日期 | 2026-11-18 |
| 历史计划 | v1.0 Frozen、v1.1 执行补充均保留原文 |
| 当前设计输入 | [SRS v1.0](../requirement/SRS_ginlong_apis.md)、[TDD v0.7](../ginlong_apis/TDD-v0.7.md)、[CC-GIN-003 v1.4](CC-GIN-003-v1.4.md) |
| 模板同步 | BLOCKED；已批准模板缺失例外仍有效，不作为 PASS |
| 执行授权 | 本地开发、Odoo 自动化与 Mock HTTP；无真实 Ginlong/生产访问授权 |

本补充延续原实施计划，依据用户 2026-11-18 最终批准规则执行 API07 跨 owner 产品识别、API02/08 实际细节和 API06 实际托盘/重量回传，并记录完成的 Odoo 自动化。v1.0–v1.3 计划均保留；Ginlong/Odoo/Karl Rapp 的系统职责不变。CC-TEST-010/017/019 的既有证据不覆盖、不重跑。

## 1. 当前交付

- 五个人工回传接口继续使用既有业务 Form 的「Ginlong 回传数据」Notebook；API02/08 增加实际明细持久化子表，API06 提供实际汇总及可保存人工覆盖；按钮只读取已保存 ORM 记录。
- API07 允许不同 owner 相同 `productCode`；按 `owner + productCode` 查找及更新，相关 WMS 入口在重复编码时按项目货主编码消歧或报告歧义，不任取首条。
- 复用现有 Order、Picking、Move Line、Lot、Package 和 `product.product`；不新增产品映射模型或重复库存账。
- 固定 POST / `application/json`，API02=`UPDATE`，API04/06/08=`CREATE`，API10=`Add`/`Del`（不区分 Action 大小写）；同步发送，15 秒超时，无自动重试。
- 每个按钮尝试调用现有 API 日志新增独立记录，不修改旧日志；失败后允许修改已保存数据再发送。
- 按项目已登记的 Wizard/Form 认知，只有一次性参数选择适用 Wizard；需长期保存及失败后修改重试的回传数据使用持久化 Form，发送按钮仅读已保存 ORM 数据。
- ATR-RUN-032：七项指定 Odoo post-tests、0 failed / 0 error；ATR-RUN-033：ORM 核对模块版本、持久化字段、无回传 Wizard 和四个 Form 视图。仅使用 Mock HTTP；真实接口和完整人工 E2E 未执行。
- ATR-RUN-042：7 个 API07/API02/06/08 定向测试，0 failed / 0 error；ATR-RUN-043：Ginlong 全量 30 个 post-tests，0 failed / 0 error；ATR-RUN-044：worlddepot 全量 8 个 post-tests，0 failed / 0 error。Odoo Shell ORM 只读确认回传子表、计算字段、owner/weight 字段、move line 来源均注册，回传 Wizard 不在 registry。
- 用户最终确认 API02/08 混合状态不发送、API06 DECIMAL 采用 V3.2 样例 JSON string、重量来源为 `product.ginlong_weight`。ATR-RUN-046 对这些规则的 3 个定向测试、ATR-RUN-047/048 Ginlong 最终全量复测通过；RUN-048 另覆盖最多六位小数；ATR-RUN-041 首次失败仍保留。

## 2. 当前分项状态

| 项目 | 状态 | 下一步 |
|---|---|---|
| CC-TEST-001–006：Form 与已确定回传行为 | PASS（本地 Odoo/Mock）；RUN-042/043 及最终 RUN-046/047 通过，保存重开、状态/实绩 Payload、API06 覆盖、失败重试和日志追加有证据 | 无本地测试剩余；完整人工操作留最终集成 CC |
| CC-TEST-007：Open Item 隔离 | PASS；API02/08 混合状态按用户决策阻止发送并记日志；API06 DECIMAL 字段按 V3.2 样例发送 JSON string | 不将撤销/部分执行等外部 Open Items 伪记解决，留接口联调 |
| CC-TEST-023 API07 owner+productCode | PASS（Odoo 自动化）；跨 owner 同码创建、同 owner 查询/更新、API01/03 复合定位及 WMS resolver 消歧均通过 | 无自动化剩余；真实 Ginlong 不在本 CC 范围 |
| CC-TEST-024 `worlddepot` 保留能力回归 | PASS（自动化范围）；RUN-044 8 项全部通过，并结合 RUN-043 对 Ginlong 改动、owner resolver、Order/Picking 与回传关联测试 | 完整人工 WMS E2E 留最终集成 CC |
| API04 正常完成回传 | 本地 Mock 成功、HTTP 失败及编辑后重发通过 | Ginlong 确认的多 picking/撤销/时间语义留待联调确认 |
| API10 实盘完成回传 | 本地 Mock Add/Del、实盘行持久化选择通过 | 外部撤销/部分采集范围仍按 V3.2 Open Items |
| 完整人工 WMS E2E | 留最终集成 CC | 需要时另立最终集成验证，不在本轮伪记通过 |
| Ginlong 真实环境 | 未授权 / NOT RUN | 等待单独授权和正式联调准备 |

## 3. 环境及证据

- 使用项目既有 `odoo.conf`、`venv`、数据库 `odooce_karlrapp`，通过 Odoo 标准测试运行器及 ORM；不直接访问 PostgreSQL、不建新环境、不使用 `stock_barcode`。
- ATR-RUN-041 为首次失败运行（4 errors/1 failure），原样保留；ATR-RUN-042 为修复后 7 个定向测试；ATR-RUN-043/044 为 Ginlong 30 项、worlddepot 8 项全量测试，均 0 failed / 0 error。用户最终确认后，ATR-RUN-046 三项定向测试及 ATR-RUN-047/048 Ginlong 全量复测也通过。
- API06 重量来源和 JSON string 序列化、API02/08 混合状态阻止规则均已确认并纳入代码/测试；剩余外部 Open Items 按接口隔离，不阻塞已确认的本地核心场景。
- 最终有效命令、执行结果和失败尝试保留于 [ATR-GIN-003](ATR-GIN-003.md)；实施事实追加于 [IHR-GIN-003](IHR-GIN-003.md)。
- 外部撤销/部分执行及真实联调语义继续按 CC-GIN-003 v1.4 和 TDD v0.7 分接口跟踪；任何未执行的外部流程不标记 PASS。

## 修订记录

| 版本 | 日期 | 修订 | 状态 |
|---|---|---|---|
| v1.2 | 2026-11-18 | 追加持久化 Form/Notebook 实施基线和 ATR-RUN-032/033；记录 Wizard/Form 项目认知，明确 API02/06/08 独立 Open Items、CC-TEST-024 回归、最终人工 E2E 及真实接口授权边界 | Active Execution |
| v1.3 | 2026-11-18 | 纳入用户最终业务规则：API07 owner+productCode、API02/08 实际明细、API06 package_id/重量和手工覆盖；追加 ATR-RUN-041/042 与待确认项 | Active Execution |
| v1.4 | 2026-11-18 | 纳入用户最终字段规则及最终专项/全量 Odoo 自动化、ORM registry 证据；CC-TEST-001–024 自动化验收通过，外部 Open Items 继续隔离；提交 Human Review 关闭评估 | 本地实施完成；待 Human Review |
