# CC-GIN-004 v1.1 — 关闭记录

| 字段 | 值 |
|---|---|
| 文档性质 | 冻结验收基线的关闭状态及用户追加验收记录；不覆盖 v1.0 原件 |
| 状态 | **Closed** |
| Human Review | **APPROVED**；李建强（项目用户）；2026-11-18；授权关闭 CC-GIN-004 |
| 冻结验收基线 | [CC-GIN-004 v1.0 Frozen](CC-GIN-004-v1.0.md) |
| 补充技术基线 | [TDD v0.9 Frozen](../ginlong_apis/TDD-v0.9.md)；v0.8 历史原件保留 |
| 关闭评估 | [FR-GIN-004 v1.0](FR-GIN-004.md)；Closure SATISFIED |
| 实施记录 | [IHR-GIN-004 v1.0](IHR-GIN-004.md)；[ATR-GIN-004 v1.0](ATR-GIN-004.md) |
| 实施代码基线 | `3a7ec9c2de954cd1c88fd6c3d598c75b167ad4fe` |

## 关闭决定

项目负责人于 2026-11-18 授权关闭 CC-GIN-004，并提交、推送 Git。CC-GIN-004 v1.0 的 API09 与 Ginlong 管理界面自动化/组件验收均有 PASS 证据。用户冻结后追加的 API09 未知仓库、未知货主及双货主×双仓隔离用例（CC-TEST-041–043）也已通过，作为本关闭记录的补充验收，不改写 v1.0 原冻结矩阵。

API09 货主来源按项目负责人的后续明确决定修订：通过 `res.partner.ginlong_owner_code` 定位货主，再以 `stock.quant.owner_id` 隔离库存；仓库按现有 `stock.warehouse.code` 精确匹配，未知值拒绝查询。该修订记录于 TDD v0.9；TDD v0.8 保留为历史冻结版本。

关闭状态依据 [FR-GIN-004 v1.0](FR-GIN-004.md)。最终全量 Ginlong 自动化为 40 个 post-tests、0 failed / 0 error（ATR-GIN-004 RUN-011；同一运行亦见 ATR-GIN-003 RUN-055）。当前代码提交即测试源代码；关闭提交仅更新治理与证据文档。

## 保留的非阻塞事项

- 模板同步仍为 `BLOCKED`，沿用既有用户批准的流程例外；不记为通过。
- 模拟 ORM 库存验证 API09 查询和隔离逻辑，不表示 Karl Rapp 实际库存同步已验证。
- 浏览器人工 UI/WMS E2E 由 CC-GIN-005 承接；真实 Ginlong 测试环境联调由 CC-GIN-006 在另行授权后承接。
- 当前 Odoo 仓库码为 5 字符；本 CC 证明本地已配置仓库码匹配与未知值拒绝行为，不声称任意 Ginlong 仓库码已完成真实环境兼容验证。若 Ginlong 实际仓库码与现有配置不符，按 CC-GIN-006 联调结果处理；未来多仓按 Ginlong 要求扩展现有仓库模型，不建映射模型。

上述事项不违反 CC-GIN-004 的本地自动化/组件关闭义务，也没有被伪记为 PASS。

## 状态及版本记录

| 版本 | 日期 | 状态 | 说明 |
|---|---|---|---|
| v1.0 | 2026-11-18 | Frozen | 原始验收基线，保持不变 |
| v1.1 | 2026-11-18 | Closed | 项目负责人批准关闭；依据 FR-GIN-004 v1.0；补录 CC-TEST-041–043、TDD v0.9 数据来源修订及非阻塞移交项 |
