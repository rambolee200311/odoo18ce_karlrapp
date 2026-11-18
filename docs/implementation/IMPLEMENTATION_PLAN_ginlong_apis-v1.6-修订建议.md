# Ginlong API 实施计划 v1.6 — 修订建议稿

| 项目 | 内容 |
|---|---|
| 文档性质 | 对冻结 Implementation Plan v1.0 及执行补充的最小修订建议；不修改或取代既有版本 |
| 建议版本 | v1.6 |
| 状态 | Draft v0.7 — 待 Human Review |
| 日期 | 2026-11-18 |
| 依据 | [Implementation Plan v1.0 Frozen](IMPLEMENTATION_PLAN_ginlong_apis.md)、[v1.1–v1.5 执行补充](IMPLEMENTATION_PLAN_ginlong_apis-v1.5.md)、[SRS v1.0](../requirement/SRS_ginlong_apis.md)、冻结 [TDD v0.4](../ginlong_apis/TDD-v0.4.md)、实施补充 [TDD v0.8](../ginlong_apis/TDD-v0.8.md) |
| 模板同步 | BLOCKED：仓库缺少项目模板源；按已批准例外形成评审稿，未记为通过 |

## 1. 修订目的

在不覆盖冻结计划 v1.0 的前提下，将 Ginlong 管理界面纳入 CC-GIN-004 的交付范围，并细化 API09 只读库存查询的契约核对、数据来源和验收门槛。TDD v0.8 是本轮 API09 与管理界面修订稿，尚未冻结；CC-GIN-004 冻结及编码前，应先评审并批准 TDD v0.8 与本 Plan v1.6 建议。

## 2. 最小范围调整建议

| 计划阶段 | v1.0 原范围 | 建议 v1.6 补充 | 责任 CC |
|---|---|---|---|
| 阶段 3 | API09 语义确认后实施只读库存查询 | 按 V3.2 正式字段实现必填 owner/warehouse 查询并返回完整产品库存列表，不分页、不增加 productCode 请求条件；quantity 返回 Odoo 当前库存记录所表达的实际物理在库量，不扣预留量，按 `(ownerCode, warehouseCode, productCode)` 区分。Karl Rapp 执行现场作业，Odoo 接收结果并通过 stock.picking/原生库存机制记录；本 CC 不增加同步或出入库实现，也不假定 KR 同步完成。Ginlong 入库/出库单为单货主，订单级 ownerCode 作用于全部明细；该认知不重开 CC-GIN-002/003。增加精简管理入口：现有 API Settings、Ginlong API 日志、入库/出库/盘点/产品查询、失败日志定位源单据。复用现有设置/日志/业务操作，不新增接口启用开关、监控或重发中心 | [CC-GIN-004 v0.7 Draft](CC-GIN-004-v0.7.md) |
| 阶段 4 | 本地集成与 WMS 回归 | 保持不变；继续承担本地集成、完整 UI/WMS 流程和回归验收。API09 实际物理数量口径按本轮确认；仓库主数据编码映射问题只阻塞受影响的查询场景 | CC-GIN-005 |
| 阶段 5 | Ginlong 测试环境联调 | 保持不变；真实 Ginlong 环境和逐接口联调仍须另行授权并按确认契约执行 | CC-GIN-006 |

本建议不改变 CC-GIN-001–003 已批准范围或验收结果，不重复开发其已通过功能。API09 和管理 UI 在 CC-GIN-004 进行定向实现与组件验证；完整人工 E2E 留 CC-GIN-005，真实 Ginlong 联调留 CC-GIN-006。

只读 ORM 核验结果作为本计划实施前置事实：当前开发库内部 `stock.quant` 为 0、`res.partner.ginlong_owner_code` 非空记录为 0，`stock.warehouse` 仅有 `KRWH` / `KarlRapp-WH` 且没有 Ginlong 仓库编码字段。代码/registry 中存在 `stock.quant.quantity`、`reserved_quantity`、`owner_id`、`location_id`、`product_id`，以及 `product.product.default_code`、`ginlong_owner_code`。因此源码字段可用于设计查询，但 owner/warehouse 对实际 quant 的映射和 Karl Rapp 库存同步无法从当前开发库证明。实施测试如需验证 API09 聚合/隔离，须明确标记 ORM 模拟库存数据；报告不得称为真实库存同步验证。

## 3. 执行及基线门禁

1. SRS v1.0 继续作为业务需求基线。最新 V3.2 正式字段表已明确必填 owner/warehouse、响应结构及类型、完整产品库存列表；不分页且不增加 productCode 请求条件。用户确认 API09 `quantity` 为 Odoo 当前库存记录所表达的实际物理在库量，不扣预留量；实际出入库由 Karl Rapp 执行，Odoo 接收其结果并通过 `stock.picking` 和原生库存机制记录。用户同时确认货主传输编码而非名称、入库/出库单均为单货主、库存按 `(ownerCode, warehouseCode, productCode)` 区分。SRS OPEN-GIN-008 保持原文，不在本修订中改写；TDD v0.8 记录本次对该事项的用户决定。
2. 冻结 TDD v0.4 尚未覆盖新增管理 UI 的完整行为，TDD v0.7 为 CC-GIN-003 的实施验证资料且尚未冻结。已形成 TDD v0.8 Draft，引用项目认知 v2.4 的 KR 实际作业来源、实际物理库存口径、单货主订单、货主编码、产品复合键及 `(ownerCode, warehouseCode, productCode)` 库存隔离规则，并记录源码与只读 ORM 核对：现有入库转 Picking 会传递 owner 伙伴，产品定位按 default_code 与 ginlong_owner_code；但开发库内部 stock.quant 为 0、带 Ginlong owner code 的 partner 为 0、仓库只有 `KRWH` / `KarlRapp-WH` 且无 Ginlong 仓库编码字段。故真实库存 owner/warehouse 映射和 KR 库存同步均未被证明；Human Review 批准后，API09 可用明确标记的模拟库存数据验证组件逻辑，不能记作真实同步通过。管理界面复用与访问边界见 TDD/CC v0.7。
3. 本 Plan v1.6 仅在 Human Review 批准后作为补充执行计划；v1.0 及 v1.1–v1.5 均保留原文。
4. Ginlong V3.2 正式字段表作为 API09 字段和类型依据；其中 `operationTime` 的正式格式与 JSON 样例存在差异，正式字段表作为实现基准并在技术记录中保留该资料差异。未列出的分页、productCode 请求条件及可用量/预留量字段均不增加。
5. 现有 Odoo 开发环境、`odoo.conf`、`venv`、数据库及“禁止 `stock_barcode`、仅经 Odoo ORM 操作数据库”等项目约束保持不变。真实 Ginlong/生产端点访问不属于本 CC 授权。

## 4. 建议修订记录

| 版本 | 日期 | 状态 | 说明 |
|---|---|---|---|
| v1.0 | 2026-11-17 | Frozen | 原实施计划，保持不变 |
| v1.1–v1.5 | 2026-11-17 至 2026-11-18 | 历史执行补充 | 保留现有内容，含 CC-GIN-003 关闭记录 |
| v1.6 | 2026-11-18 | Draft v0.7 | 确认 API09 实际物理在库量（不扣预留）及 `(ownerCode, warehouseCode, productCode)` 区分；纳入开发库 ORM 数据映射缺口、模拟库存验收边界和未证实 KR 同步的事实；管理界面继续精简；CC-005/006 边界不变；待 Human Review |
