# Ginlong API 实施计划 v1.9 — CC-GIN-007 基线与授权

| 项目 | 内容 |
|---|---|
| 文档性质 | 冻结计划的基线和阶段状态补充；保留 v1.6–v1.8 历史文件 |
| 版本 | v1.9 |
| 状态 | Frozen；Human Review APPROVED（落实 CC-GIN-007 有条件评审决定） |
| 计划范围 | 沿用 [Implementation Plan v1.6 Frozen](IMPLEMENTATION_PLAN_ginlong_apis-v1.6.md)；更新 CC-GIN-007 上游基线与实施阶段映射 |
| 当前 SRS 基线 | [SRS v1.2 Frozen with Open Items](../requirement/SRS_ginlong_apis-v1.2.md)；v1.1、v1.0 保留 |
| 当前技术基线 | [TDD v1.5 Frozen with Open Items](../ginlong_apis/TDD-v1.5.md)；TDD v1.0 与早期版本保留 |
| Baseline validity | **VALID**；2026-11-23 已完成 SRS/TDD 影响更新、CC 映射与有条件审批项核对 |
| 当前 CC | [CC-GIN-007 v1.0 Frozen](CC-GIN-007-v1.0.md)（本地实施授权）；CC-GIN-005 v1.1 保留其独立范围和状态 |
| 关闭记录 | [CC-GIN-004 v1.1 Closed](CC-GIN-004-v1.1.md)；[FR-GIN-004 v1.0](FR-GIN-004.md) |
| 最近已关闭 CC 代码基线 | `3a7ec9c2de954cd1c88fd6c3d598c75b167ad4fe`（CC-GIN-004 关闭记录；不是 CC-GIN-007 实施提交） |
| 日期 / 负责人 | 2026-11-23 / 李建强（项目负责人） |
| 模板同步 | BLOCKED：源模板缺失；沿用批准例外，不伪记 PASS |

## 1. 执行状态

| 阶段 | 范围 | CC | 状态 | 证据 / 结果 |
|---|---|---|---|---|
| 阶段 0–2 | CC-GIN-001–003 | CC-GIN-001、002、003 | Closed | 各自 FR 与关闭记录；不在本补充重开 |
| 阶段 3A | API09 只读实际物理库存查询 | CC-GIN-004 | **Closed** | FR-GIN-004 v1.0 Closure SATISFIED；CC-TEST-025–033、041–043 PASS；模拟库存，不代表 KR 同步 |
| 阶段 3B | Ginlong 管理菜单、日志与业务查询入口 | CC-GIN-004 | **Closed** | CC-TEST-034–040 PASS；日志关联、只读 ACL 与来源导航通过自动化/组件验证 |
| 阶段 4 | Ginlong API01–10 本地集成、产品变体与受影响 WMS 回归、浏览器 E2E | CC-GIN-005 v1.1 | **In Progress** | CC-GIN-005 按其冻结时的 SRS v1.1 / TDD v1.0 基线实施；本地开发、ORM/自动化和浏览器 Mock 验收已获授权；实际结果记录在 IHR/ATR/HVR。CC-GIN-007 的增量范围单独列于阶段 4B |
| 阶段 4B | API01 保税入库预报 snList 条件处理及预报/实绩边界 | CC-GIN-007 v1.0 | **Authorized / Ready to Implement** | SRS v1.2、TDD v1.5 已冻结并基线化；本地开发及 Odoo HTTP/ORM 自动化、组件集成测试已授权；不得扩展为预报/实收比较功能 |
| 阶段 5 | 真实 Ginlong 测试环境联调 | 拟建 CC-GIN-006 | Blocked pending separate authorization/environment | 需要真实测试环境、接口确认及单独授权；当前未访问 |

## 2. CC-GIN-004 关闭基线

- 冻结验收契约为 CC-GIN-004 v1.0；关闭状态与用户追加的 API09 隔离用例记录在 v1.1，不覆盖 v1.0。
- API09 货主按 `res.partner.ginlong_owner_code` 定位，库存用 `stock.quant.owner_id` 隔离；未知 owner 返回空库存，未知 warehouse 拒绝查询，不回退到其他仓库。
- 单仓库不增加 Ginlong 仓库映射；未来多仓按 Ginlong 要求扩展现有仓库模型。当前仓库码字段为 5 字符；任意真实 Ginlong 仓库码的环境兼容性仍交 CC-GIN-006 按实际值确认。
- 最终 `ginlong_apis` 回归为 40 post-tests、0 failed / 0 error；实现代码基线为 `3a7ec9c2de954cd1c88fd6c3d598c75b167ad4fe`。关闭提交仅更新文档。
- 模拟库存测试验证 API09 组件，不声称已完成 Karl Rapp 库存同步。

## 3. 保留的后续边界

| 事项 | 状态 | 责任阶段 |
|---|---|---|
| 项目模板同步 | BLOCKED；批准例外保留，不标 PASS | 项目文档治理 |
| 完整浏览器 UI/WMS 人工 E2E | NOT RUN | CC-GIN-005 |
| Karl Rapp 库存真实同步验证 | NOT VERIFIED | 后续本地集成/CC-GIN-006 依实际数据确认 |
| 真实 Ginlong HTTP/生产访问 | NOT RUN；本轮未授权 | CC-GIN-006，须单独授权 |
| 真实 warehouse 编码与本地仓库码兼容 | NOT VERIFIED；当前单仓库组件仅验证已配置短码和未知值隔离 | CC-GIN-006；若多仓则按 Ginlong 要求扩展现有仓库字段 |
| API01 预报/实收差异比较与处置 | 不属于当前已批准范围；如需开发，另行提出需求变更 | 后续 CC / 需求变更 |

这些事项不阻塞 CC-GIN-004 的本地组件关闭，不把任何 `BLOCKED`、`NOT RUN` 或 `NOT VERIFIED` 改写为通过。

## 4. 追溯更新

| 需求/设计 | 阶段 / CC | 当前状态 |
|---|---|---|
| SRS FR-GIN-009：库存查询 | 阶段 3A / CC-GIN-004 | 本地自动化满足；真实数据同步未验证 |
| TDD v0.9 API09 owner/warehouse 来源与只读边界 | 阶段 3A / CC-GIN-004 | 已实现并测试；v0.8 历史保留；新产品原始编码输出遵循 TDD v1.0 后续验收 |
| Ginlong 管理界面、日志与来源定位 | 阶段 3B / CC-GIN-004 | 自动化/组件验收满足 |
| SRS v1.1 / TDD v1.0 产品模板与 owner 变体基线 | 阶段 4 / CC-GIN-005 v1.1 | 已批准并冻结；具体实施证据待记录 |
| 完整本地集成与人工 E2E | 阶段 4 / CC-GIN-005 v1.1 | In Progress；不得把未运行场景记为通过 |
| SRS v1.2 FR-GIN-001 API01 条件化 snList 与 TDD v1.5 预报/实绩边界 | 阶段 4B / CC-GIN-007 v1.0 | 已批准冻结；本地实施授权；差异比较明确排除 |
| 真实 Ginlong 外部联调 | 阶段 5 / 拟建 CC-GIN-006 | 待环境、契约与单独授权 |

## 5. 版本记录

| 版本 | 日期 | 变更 | 状态 |
|---|---|---|---|
| v1.6 | 2026-11-18 | 冻结范围、基线与阶段计划，保持原件不变 | Frozen；Human Review APPROVED |
| v1.7 | 2026-11-18 | 记录 TDD v0.9 API09 字段来源修订、CC-GIN-004 Closed 与 FR 证据、CC-GIN-005/006 后续状态；不改范围 | 状态补充；项目负责人授权 |
| v1.8 | 2026-11-19 | SRS v1.1、TDD v1.0 更新为当前冻结基线；将阶段 4 追溯至 CC-GIN-005 v1.1 并记录实施授权；保留阶段 5 真实 Ginlong 联调门禁 | Frozen；Human Review APPROVED；阶段 4 In Progress |
| v1.9 | 2026-11-23 | 更新当前基线至 SRS v1.2 / TDD v1.5；新增阶段 4B 和 CC-GIN-007 v1.0 映射；记录本地实施授权与预报/实收比较排除范围；v1.8 历史保留 | Frozen；Human Review APPROVED |

## 6. Human Review 与计划冻结

| 项目 | 记录 |
|---|---|
| Human Review | APPROVED；项目负责人李建强；2026-11-23；落实 CC-GIN-007 有条件评审要求 |
| 冻结决定 | Plan v1.9 Frozen；当前基线为 SRS v1.2、TDD v1.5；新增阶段 4B / CC-GIN-007 v1.0 |
| 实施授权 | CC-GIN-007 本地代码、Odoo 自动化/组件集成测试及 Mock HTTP 已授权；不包括真实 Ginlong、生产、KR/Gateway 访问 |
| 模板同步 | BLOCKED；沿用已批准例外，不标 PASS |
