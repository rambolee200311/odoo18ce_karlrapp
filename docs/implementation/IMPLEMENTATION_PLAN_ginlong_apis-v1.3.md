# Ginlong API Implementation Plan v1.3

| 项目 | 内容 |
|---|---|
| 版本 | v1.3 业务规则执行补充 |
| 状态 | CC-GIN-003 In Progress |
| 日期 | 2026-11-18 |
| 历史计划 | v1.0 Frozen、v1.1 执行补充均保留原文 |
| 当前设计输入 | [SRS v1.0](../requirement/SRS_ginlong_apis.md)、[TDD v0.6](../ginlong_apis/TDD-v0.6.md)、[CC-GIN-003 v1.3](CC-GIN-003-v1.3.md) |
| 模板同步 | BLOCKED；已批准模板缺失例外仍有效，不作为 PASS |
| 执行授权 | 本地开发、Odoo 自动化与 Mock HTTP；无真实 Ginlong/生产访问授权 |

本补充延续原实施计划，依据用户 2026-11-18 最终批准规则执行 API07 跨 owner 产品识别、API02/08 实际细节和 API06 实际托盘/重量回传。v1.0–v1.2 计划均保留；Ginlong/Odoo/Karl Rapp 的系统职责不变。CC-TEST-010/017/019 的既有证据不覆盖、不重跑。

## 1. 当前交付

- 五个人工回传接口继续使用既有业务 Form 的「Ginlong 回传数据」Notebook；API02/08 增加实际明细持久化子表，API06 提供实际汇总及可保存人工覆盖；按钮只读取已保存 ORM 记录。
- API07 允许不同 owner 相同 `productCode`；按 `owner + productCode` 查找及更新，相关 WMS 入口在重复编码时按项目货主编码消歧或报告歧义，不任取首条。
- 复用现有 Order、Picking、Move Line、Lot、Package 和 `product.product`；不新增产品映射模型或重复库存账。
- 固定 POST / `application/json`，API02=`UPDATE`，API04/06/08=`CREATE`，API10=`Add`/`Del`（不区分 Action 大小写）；同步发送，15 秒超时，无自动重试。
- 每个按钮尝试调用现有 API 日志新增独立记录，不修改旧日志；失败后允许修改已保存数据再发送。
- 按项目已登记的 Wizard/Form 认知，只有一次性参数选择适用 Wizard；需长期保存及失败后修改重试的回传数据使用持久化 Form，发送按钮仅读已保存 ORM 数据。
- ATR-RUN-032：七项指定 Odoo post-tests、0 failed / 0 error；ATR-RUN-033：ORM 核对模块版本、持久化字段、无回传 Wizard 和四个 Form 视图。仅使用 Mock HTTP；真实接口和完整人工 E2E 未执行。

## 2. 当前分项状态

| 项目 | 状态 | 下一步 |
|---|---|---|
| CC-TEST-001–007：持久化 Form 和五个回传接口 | 本轮 ATR-RUN-042 七项定向 Odoo post-tests 通过；API02/06/08 已有字段可 Mock | 完成全量回归；保留 API02/08 混合状态汇总和 API06 JSON number/string Open Item |
| CC-TEST-023 API07 owner+productCode | PARTIAL；同码跨 owner 创建、同 owner 更新、API01/03 复合查找及 resolver 消歧的定向测试通过 | 执行全量 Ginlong 自动化并确认旧 WMS 相关路径回归 |
| CC-TEST-024 `worlddepot` 保留能力回归 | In Progress；本轮 Ginlong 测试通过，尚未完成受影响 `worlddepot` 全套自动化 | 执行 `worlddepot` 标准自动化并检查 API User/Token、日志、Inbound/Outbound、盘点、库存路径 |
| API04 正常完成回传 | 本地 Mock 成功、HTTP 失败及编辑后重发通过 | Ginlong 确认的多 picking/撤销/时间语义留待联调确认 |
| API10 实盘完成回传 | 本地 Mock Add/Del、实盘行持久化选择通过 | 外部撤销/部分采集范围仍按 V3.2 Open Items |
| 完整人工 WMS E2E | 留最终集成 CC | 需要时另立最终集成验证，不在本轮伪记通过 |
| Ginlong 真实环境 | 未授权 / NOT RUN | 等待单独授权和正式联调准备 |

## 3. 环境及证据

- 使用项目既有 `odoo.conf`、`venv`、数据库 `odooce_karlrapp`，通过 Odoo 标准测试运行器及 ORM；不直接访问 PostgreSQL、不建新环境、不使用 `stock_barcode`。
- ATR-RUN-041 为首次失败运行（5 errors/1 failure），原样保留；ATR-RUN-042 为同范围修正后 7 个 Odoo post-tests，0 failed / 0 error。完整全量 Ginlong 与 `worlddepot` 回归尚未运行。
- 最终有效命令、执行结果和失败尝试保留于 [ATR-GIN-003](ATR-GIN-003.md)；实施事实追加于 [IHR-GIN-003](IHR-GIN-003.md)。
- 未确认字段及接口语义按 CC-GIN-003 v1.3 和 TDD v0.6 分字段跟踪；任何未验证的完整流程不标记 PASS。

## 修订记录

| 版本 | 日期 | 修订 | 状态 |
|---|---|---|---|
| v1.2 | 2026-11-18 | 追加持久化 Form/Notebook 实施基线和 ATR-RUN-032/033；记录 Wizard/Form 项目认知，明确 API02/06/08 独立 Open Items、CC-TEST-024 回归、最终人工 E2E 及真实接口授权边界 | Active Execution |
| v1.3 | 2026-11-18 | 纳入用户最终业务规则：API07 owner+productCode、API02/08 实际明细、API06 package_id/重量和手工覆盖；追加 ATR-RUN-041/042 与待确认项 | Active Execution |
