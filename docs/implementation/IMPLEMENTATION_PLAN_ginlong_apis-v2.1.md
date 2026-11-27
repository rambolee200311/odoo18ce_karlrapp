# Ginlong API 实施计划 v2.1 — CC-GIN-008 基线

| 项目 | 内容 |
|---|---|
| 文档性质 | v2.0 冻结计划的修订版本；不覆盖 v1.9/v2.0 原件 |
| 版本 | v2.1 |
| 状态 | Frozen；Human Review APPROVED |
| 当前批准基线 | [SRS v1.3 Frozen with Open Items](../requirement/SRS_ginlong_apis-v1.3.md)；[TDD v1.6 Frozen with Open Items](../ginlong_apis/TDD-v1.6.md) |
| 本计划基线 | v2.1；保留 v2.0 历史版本 |
| Baseline validity | **VALID**；本版本已完成上游影响更新及 CC 阶段映射 |
| 现有阶段依据 | [CC-GIN-007 v1.1 Closed](CC-GIN-007-v1.1.md)；[FR-GIN-007 v1.0](FR-GIN-007.md) |
| 日期 / 负责人 | 2026-11-24 / 项目负责人李建强 |
| 模板同步 | BLOCKED；沿用已批准流程例外，不伪记 PASS |

## 1. 执行状态

| 阶段 | 范围 | CC | 状态 | 证据 / 后续 |
|---|---|---|---|---|
| 阶段 0–2 | Ginlong 基础、API01–10 实施基础 | CC-GIN-001–003 | Closed | 各自 FR 与关闭记录 |
| 阶段 3A/3B | API09 只读库存查询及管理入口 | CC-GIN-004 | Closed | FR-GIN-004 v1.0 |
| 阶段 4 | API01–10 本地集成与完整 WMS E2E | CC-GIN-005 v1.1 | In Progress | 按原范围继续实施和最终验收 |
| 阶段 4B | API01 保税入库预报 `snList` 条件处理及预报/实绩边界 | CC-GIN-007 v1.0 | **Closed** | CC-TEST-057–070 PASS；Ginlong 全量 71 post-tests 0 failed/0 error；HVR-API01-01–06 PASS。HVR-API01-07 为 API04 辅助出站 UI 核查，NOT RUN 且不阻塞关闭；详见 FR-GIN-007 |
| 阶段 4C | API01/03/05/07 有效业务记录驱动的 Add 生命周期幂等、全局业务键及并发唯一 | [CC-GIN-008 v1.0 Closed](CC-GIN-008-v1.0.md) | **Closed（2026-11-24）** | FR-GIN-008 Closure SATISFIED；项目负责人 Human Review APPROVED。多 Worker HTTP 与独立人工 HVR 为 N/A/Deferred；模板同步 BLOCKED 沿用批准例外 |
| 阶段 5 | 真实 Ginlong 测试环境联调 | 拟建 CC-GIN-006 | Blocked pending separate authorization/environment | 真实测试环境、协议及单独授权仍需具备；当前未访问 |

## 2. CC-GIN-007 关闭边界

- API01 保税/非保税预报处理已按冻结 SRS/TDD 实施，并通过真实本地 HTTP/ORM 自动化和项目负责人 HVR。
- API04 在 CC-GIN-007 中未修改。自动化 CC-TEST-069 证明其 Payload 来自实际 Picking/Move Line。额外的 HVR-API01-07 预期报文是 Odoo 自动生成的出站 JSON，不是测试者提交的入站 Payload；该 UI/Mock 核查保留 NOT RUN，按项目负责人决定不设为关闭门槛。
- 模板同步继续 BLOCKED，沿用既有批准例外。
- 未声称真实 Ginlong、KR/Gateway 或完整 WMS E2E 已通过。

## 3. Human Review 与版本记录

| 项目 | 记录 |
|---|---|
| Human Review | APPROVED；项目负责人李建强；2026-11-24；批准冻结文档并进入 CC-GIN-008 实施 |
| 当前计划 | v2.1（含本页收尾修订）；阶段 4C / CC-GIN-008 Closed；阶段 4 和阶段 5 状态不变 |
| 历史计划 | v1.9 保留原冻结基线及其当时状态 |

| 版本 | 日期 | 变更 | 状态 |
|---|---|---|---|
| v1.9 | 2026-11-23 | SRS v1.2/TDD v1.5 基线与 CC-GIN-007 实施授权 | Frozen；历史版本保留 |
| v2.0 | 2026-11-23 | 记录 CC-GIN-007 Closed、自动化/HVR 证据及 API04 补充 HVR NOT RUN 非阻塞决定 | Frozen；Human Review APPROVED |


## 7. v2.1 基线更新与阶段门禁

本稿只建议在现有阶段后增加阶段 4C，不重开 CC-GIN-001–007，也不改变阶段 5 真实 Ginlong 联调授权边界。CC-GIN-008 处理四类入站 Add 的有效性、生命周期幂等、历史留存及数据库并发唯一性。

| 门禁 | 要求 | 状态 |
|---|---|---|
| 上游业务基线 | SRS v1.3 Frozen with Open Items | 满足 |
| 上游技术基线 | TDD v1.6 Frozen with Open Items | 满足 |
| TV 验证 | [TV-GIN-008-v0.1](../context/report/TV-GIN-008-v0.1.md) | 已完成；ORM/原生变体事实通过；并发运行测试留 CC |
| 通用组件规范 | [3PL WMS API 通用组件架构规范 v1.0](../context/cognition/3PL_WMS_API_Common_Component_Architecture-v1.0.md) | Frozen；Human Review APPROVED |
| CC-GIN-008 | [v1.0 Frozen](CC-GIN-008-v1.0.md)；Human Review APPROVED；实施授权已给出 | In Progress |
| 存量重复键 | Odoo Shell ORM 全局有效键预检 | 完成：API01/03/05/07 均为 0 个重复组 |
| 模板同步 | 批准例外沿用 | BLOCKED；不标 PASS |

阶段 4C 按 CC-GIN-008 v1.0 执行。冻结范围内自动化、实际多事务竞争及 IHR/ATR 完成后可提交关闭评审；本 CC 独立人工 HVR 及多 Worker HTTP 依下方已批准收尾决定移交最终集成。完整 WMS E2E 及真实 Ginlong 联调仍分别留在阶段 4/5。

## 9. CC-GIN-008 Human Review 收尾修订（2026-11-24）

本节是 v2.1 冻结计划的执行状态补充，不改写 SRS/TDD 或既有业务基线。

- Human Review 认可独立数据库事务并发证据满足 CC-GIN-008；本 CC 不再要求多 Worker HTTP 并发（N/A）。部署级并发验证留给最终项目集成（Deferred）。
- 本底层机制 CC 不要求独立人工 HVR；人工完整业务验收留给最终项目集成（N/A / Deferred），不记 PASS。
- 部署执行顺序固定为：ORM 保留性快照 → ORM 有效业务键预检 → 执行模块升级 → ORM 后快照 → 比较历史关键字段。任一有效键冲突必须停止升级，不自动修改业务数据。具体命令见 `docs/implementation/scripts/cc_gin_008/README.md`。
- 本轮升级前后比较结果：inbound 8、outbound 1、stocktake 1、product.product 29、幂等 17、WorldDepot API 日志 287，六类均无 ID 丢失/新增或关键字段变化。当前 8099 Registry 已加载 `ginlong_apis 18.0.2.0.42`。
- 项目负责人 Human Review 已批准关闭 CC-GIN-008；阶段 4C 为 **Closed**，依据 FR-GIN-008。模板同步 BLOCKED 继续使用已批准例外；阶段 4 完整 WMS E2E 和阶段 5 真实 Ginlong 联调边界不变。

## 10. CC-GIN-008 Human Review 后续规则补充（2026-11-24）

Human Review 将 API01/03/05 的订单有效性检查扩展到支持的 Edit/Del：Del 只取消当前项目权限范围内的有效订单；订单已取消或没有有效订单时返回业务错误，不能重放历史成功响应；相同/不同 Payload 均适用。重新 Add 后，新有效订单可再次 Del。API01 V3.2 Action 仍为 Add/Del。

此项纳入 CC-GIN-008 的后续收尾验证，不另开 CC；保持业务键、Add 规则、历史保留及 project 权限不变。自动化和升级验证结果追加到 ATR/IHR，原 CC-008 Closed 记录作为历史基线保留。

### 10.1 补充规则实施结果

- API01/03/05 Add、Edit、Del 已按当前有效业务记录实现；Del 在幂等结果读取前检查当前项目内有效订单。重复 Del 返回 `BUS01: 有效订单不存在或已取消`，不会重放或新增成功幂等结果。取消后重新 Add 的订单可再次 Del。
- 最终 Ginlong 全量自动化 R3：74 post-tests、0 failed、0 error(s)；API01/03/05 的同/不同 Payload 重复 Del、cancel 后 Edit 拒绝、重新 Add 后 Del 成功均由真实 HTTP 路由和 ORM 断言覆盖。详见 ATR/IHR-GIN-008。
- 本地 8099 已重启加载 `ginlong_apis 18.0.2.0.43`；ORM 状态为 installed，Registry loaded，`/web/login` 返回 HTTP 200。
- 原 CC-GIN-008 Closed 记录、人工 HVR N/A/Deferred 和模板同步 BLOCKED 均按历史及批准状态保留；本次未另开 CC、未执行真实外部联调或 Git 提交。

## 8. 版本记录

| 版本 | 日期 | 变更 | 状态 |
|---|---|---|---|
| v2.0 | 2026-11-23 | CC-GIN-007 关闭状态更新 | Frozen；历史保留 |
| v2.1 | 2026-11-24 | 纳入 SRS v1.3、TDD v1.6、TV-GIN-008 实际报告、通用组件架构规范 v1.0 及阶段 4C / CC-GIN-008 v1.0，并记录实施授权 | Frozen；Human Review APPROVED；模板同步沿用批准例外 |
| v2.1 执行状态补充 | 2026-11-24 | 记录 CC-GIN-008 收尾 Human Review 决定、部署前 ORM 预检、升级留存结果及正式关闭状态 | 执行记录补充；不覆盖原冻结业务基线 |
