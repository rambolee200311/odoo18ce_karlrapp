# Ginlong API 实施计划 v2.1 — CC-GIN-008 Review Draft

| 项目 | 内容 |
|---|---|
| 文档性质 | v2.0 冻结计划的评审修订草案；不覆盖 v1.9/v2.0 原件 |
| 版本 | v2.1（Review Draft） |
| 状态 | Review Draft；待 Human Review；未冻结 |
| 当前批准基线 | SRS v1.2；TDD v1.5；计划 v2.0 |
| 拟议修订基线 | [SRS v1.3 Review Draft](../requirement/SRS_ginlong_apis-v1.3-Review-Draft.md)；[TDD v1.6 Review Draft](../ginlong_apis/TDD-v1.6-Review-Draft.md) |
| Baseline validity | **IMPACT REVIEW REQUIRED**；上游草案批准冻结前不取代现行基线 |
| 现有阶段依据 | [CC-GIN-007 v1.1 Closed](CC-GIN-007-v1.1.md)；[FR-GIN-007 v1.0](FR-GIN-007.md) |
| 日期 / 负责人 | 2026-11-24 / Review Draft |
| 模板同步 | BLOCKED；沿用已批准流程例外，不伪记 PASS |

## 1. 执行状态

| 阶段 | 范围 | CC | 状态 | 证据 / 后续 |
|---|---|---|---|---|
| 阶段 0–2 | Ginlong 基础、API01–10 实施基础 | CC-GIN-001–003 | Closed | 各自 FR 与关闭记录 |
| 阶段 3A/3B | API09 只读库存查询及管理入口 | CC-GIN-004 | Closed | FR-GIN-004 v1.0 |
| 阶段 4 | API01–10 本地集成与完整 WMS E2E | CC-GIN-005 v1.1 | In Progress | 按原范围继续实施和最终验收 |
| 阶段 4B | API01 保税入库预报 `snList` 条件处理及预报/实绩边界 | CC-GIN-007 v1.0 | **Closed** | CC-TEST-057–070 PASS；Ginlong 全量 71 post-tests 0 failed/0 error；HVR-API01-01–06 PASS。HVR-API01-07 为 API04 辅助出站 UI 核查，NOT RUN 且不阻塞关闭；详见 FR-GIN-007 |
| 阶段 4C（拟议） | API01/03/05/07 有效业务记录驱动的 Add 生命周期幂等与并发唯一 | [CC-GIN-008 v0.1 Draft](CC-GIN-008-v0.1-Draft.md) | Draft / not authorized | 依赖 SRS v1.3、TDD v1.6 与通用架构规范评审冻结；本稿不授权编码/测试 |
| 阶段 5 | 真实 Ginlong 测试环境联调 | 拟建 CC-GIN-006 | Blocked pending separate authorization/environment | 真实测试环境、协议及单独授权仍需具备；当前未访问 |

## 2. CC-GIN-007 关闭边界

- API01 保税/非保税预报处理已按冻结 SRS/TDD 实施，并通过真实本地 HTTP/ORM 自动化和项目负责人 HVR。
- API04 在 CC-GIN-007 中未修改。自动化 CC-TEST-069 证明其 Payload 来自实际 Picking/Move Line。额外的 HVR-API01-07 预期报文是 Odoo 自动生成的出站 JSON，不是测试者提交的入站 Payload；该 UI/Mock 核查保留 NOT RUN，按项目负责人决定不设为关闭门槛。
- 模板同步继续 BLOCKED，沿用既有批准例外。
- 未声称真实 Ginlong、KR/Gateway 或完整 WMS E2E 已通过。

## 3. Human Review 与版本记录

| 项目 | 记录 |
|---|---|
| Human Review | APPROVED；李建强；2026-11-23；授权关闭 CC-GIN-007 并提交、推送 Git |
| 当前计划 | v2.0；阶段 4B 已 Closed，阶段 4 和阶段 5 状态不变 |
| 历史计划 | v1.9 保留原冻结基线及其当时状态 |

| 版本 | 日期 | 变更 | 状态 |
|---|---|---|---|
| v1.9 | 2026-11-23 | SRS v1.2/TDD v1.5 基线与 CC-GIN-007 实施授权 | Frozen；历史版本保留 |
| v2.0 | 2026-11-23 | 记录 CC-GIN-007 Closed、自动化/HVR 证据及 API04 补充 HVR NOT RUN 非阻塞决定 | Frozen；Human Review APPROVED |


## 7. v2.1 Review Draft 变更与门禁

本稿只建议在现有阶段后增加阶段 4C，不重开 CC-GIN-001–007，也不改变阶段 5 真实 Ginlong 联调授权边界。CC-GIN-008 处理四类入站 Add 的有效性、生命周期幂等、历史留存及数据库并发唯一性。

| 门禁 | 要求 | 状态 |
|---|---|---|
| 上游业务基线 | SRS v1.3 Review Draft 获批并冻结 | 待评审 |
| 上游技术基线 | TDD v1.6 Review Draft 获批并冻结 | 待评审 |
| 通用组件规范 | 通用 Idempotency 架构规范 Draft 获批 | 待评审；仓库原独立文件缺失 |
| CC-GIN-008 | Draft 评审、冻结，明确实施授权 | 未批准 |
| 存量重复键 | 使用 ORM 只读盘点，发现冲突先报告 | NOT RUN |
| 模板同步 | 批准例外沿用 | BLOCKED；不标 PASS |

只有上述上游基线和 CC 获批冻结后才可实施阶段 4C。当前 Baseline validity 为 IMPACT REVIEW REQUIRED。

## 8. 版本记录

| 版本 | 日期 | 变更 | 状态 |
|---|---|---|---|
| v2.0 | 2026-11-23 | CC-GIN-007 关闭状态更新 | Frozen；历史保留 |
| v2.1 | 2026-11-24 | 提议阶段 4C / CC-GIN-008，要求上游影响评审 | Review Draft；未批准、未冻结 |
