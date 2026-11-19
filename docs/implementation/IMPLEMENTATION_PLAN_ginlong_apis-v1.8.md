# Ginlong API 实施计划 v1.8 — 上游基线更新与 CC-GIN-005 实施启动

| 项目 | 内容 |
|---|---|
| 文档性质 | 冻结计划的基线和阶段状态补充；不覆盖 v1.6–v1.7 历史 |
| 版本 | v1.8 |
| 状态 | Frozen；Human Review APPROVED |
| 计划范围 | 沿用 [Implementation Plan v1.6 Frozen](IMPLEMENTATION_PLAN_ginlong_apis-v1.6.md)；本补充更新上游基线与阶段 4 执行状态 |
| 当前 SRS 基线 | [SRS v1.1 Frozen with Open Items](../requirement/SRS_ginlong_apis-v1.1.md) |
| 当前技术基线 | [TDD v1.0 Frozen with Open Items](../ginlong_apis/TDD-v1.0.md)；TDD v0.9 保留为历史版本 |
| Baseline validity | **VALID**；2026-11-19 已完成影响评估、基线更新及 CC 映射 |
| 当前 CC | [CC-GIN-005 v1.1 Frozen with Open Items](CC-GIN-005-v1.1.md)；项目负责人已授权本地实施 |
| 关闭记录 | [CC-GIN-004 v1.1 Closed](CC-GIN-004-v1.1.md)；[FR-GIN-004 v1.0](FR-GIN-004.md) |
| 当前代码提交 | `3a7ec9c2de954cd1c88fd6c3d598c75b167ad4fe` |
| 日期 / 负责人 | 2026-11-19 / 李建强（项目负责人） |
| 模板同步 | BLOCKED：源模板缺失；沿用批准例外，不伪记 PASS |

## 1. 执行状态

| 阶段 | 范围 | CC | 状态 | 证据 / 结果 |
|---|---|---|---|---|
| 阶段 0–2 | CC-GIN-001–003 | CC-GIN-001、002、003 | Closed | 各自 FR 与关闭记录；不在本补充重开 |
| 阶段 3A | API09 只读实际物理库存查询 | CC-GIN-004 | **Closed** | FR-GIN-004 v1.0 Closure SATISFIED；CC-TEST-025–033、041–043 PASS；模拟库存，不代表 KR 同步 |
| 阶段 3B | Ginlong 管理菜单、日志与业务查询入口 | CC-GIN-004 | **Closed** | CC-TEST-034–040 PASS；日志关联、只读 ACL 与来源导航通过自动化/组件验证 |
| 阶段 4 | Ginlong API01–10 本地集成、产品变体与受影响 WMS 回归、浏览器 E2E | CC-GIN-005 v1.1 | **In Progress** | SRS v1.1 / TDD v1.0 已冻结并基线化；本地开发、ORM/自动化和浏览器 Mock 验收已获授权；实际结果记录在 IHR/ATR/HVR |
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

这些事项不阻塞 CC-GIN-004 的本地组件关闭，不把任何 `BLOCKED`、`NOT RUN` 或 `NOT VERIFIED` 改写为通过。

## 4. 追溯更新

| 需求/设计 | 阶段 / CC | 当前状态 |
|---|---|---|
| SRS FR-GIN-009：库存查询 | 阶段 3A / CC-GIN-004 | 本地自动化满足；真实数据同步未验证 |
| TDD v0.9 API09 owner/warehouse 来源与只读边界 | 阶段 3A / CC-GIN-004 | 已实现并测试；v0.8 历史保留；新产品原始编码输出遵循 TDD v1.0 后续验收 |
| Ginlong 管理界面、日志与来源定位 | 阶段 3B / CC-GIN-004 | 自动化/组件验收满足 |
| SRS v1.1 / TDD v1.0 产品模板与 owner 变体基线 | 阶段 4 / CC-GIN-005 v1.1 | 已批准并冻结；具体实施证据待记录 |
| 完整本地集成与人工 E2E | 阶段 4 / CC-GIN-005 v1.1 | In Progress；不得把未运行场景记为通过 |
| 真实 Ginlong 外部联调 | 阶段 5 / 拟建 CC-GIN-006 | 待环境、契约与单独授权 |

## 5. 版本记录

| 版本 | 日期 | 变更 | 状态 |
|---|---|---|---|
| v1.6 | 2026-11-18 | 冻结范围、基线与阶段计划，保持原件不变 | Frozen；Human Review APPROVED |
| v1.7 | 2026-11-18 | 记录 TDD v0.9 API09 字段来源修订、CC-GIN-004 Closed 与 FR 证据、CC-GIN-005/006 后续状态；不改范围 | 状态补充；项目负责人授权 |
| v1.8 | 2026-11-19 | SRS v1.1、TDD v1.0 更新为当前冻结基线；将阶段 4 追溯至 CC-GIN-005 v1.1 并记录实施授权；保留阶段 5 真实 Ginlong 联调门禁 | Frozen；Human Review APPROVED；阶段 4 In Progress |

## 6. Human Review 与计划冻结

| 项目 | 记录 |
|---|---|
| Human Review | APPROVED；项目负责人李建强；2026-11-19 |
| 冻结决定 | Plan v1.8 Frozen；基于 SRS v1.1、TDD v1.0，阶段 4 映射 CC-GIN-005 v1.1 |
| 实施授权 | CC-GIN-005 本地实施已获授权；真实 Ginlong/KR/Gateway 仍不在授权范围 |
| 模板同步 | BLOCKED；沿用已批准例外，不标 PASS |
