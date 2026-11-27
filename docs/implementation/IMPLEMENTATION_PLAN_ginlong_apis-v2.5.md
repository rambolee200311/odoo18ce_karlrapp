# Ginlong API 实施计划 v2.5 — CC-GIN-010 冻结实施

| 项目 | 内容 |
|---|---|
| 文档性质 | v2.0 冻结计划的修订版本；不覆盖 v1.9/v2.0 原件 |
| 版本 | v2.5 |
| 状态 | Frozen；Human Review APPROVED |
| 当前批准基线 | [SRS v1.7 Frozen with Open Items](../requirement/SRS_ginlong_apis-v1.7.md)；[TDD v2.0 Frozen with Open Items](../ginlong_apis/TDD-v2.0.md) |
| 本计划基线 | v2.5；保留 v2.4、v2.3、v2.2、v2.1 及更早版本 |
| Baseline validity | **VALID**；本版本已完成上游影响更新及 CC 阶段映射 |
| 现有阶段依据 | [CC-GIN-007 v1.1 Closed](CC-GIN-007-v1.1.md)；[FR-GIN-007 v1.0](FR-GIN-007.md) |
| 日期 / 负责人 | 2026-11-25 / 项目负责人李建强 |
| 模板同步 | BLOCKED；沿用已批准流程例外，不伪记 PASS |

## 1. 执行状态

| 阶段 | 范围 | CC | 状态 | 证据 / 后续 |
|---|---|---|---|---|
| 阶段 0–2 | Ginlong 基础、API01–10 实施基础 | CC-GIN-001–003 | Closed | 各自 FR 与关闭记录 |
| 阶段 3A/3B | API09 只读库存查询及管理入口 | CC-GIN-004 | Closed | FR-GIN-004 v1.0 |
| 阶段 4 | API01–10 本地集成与完整 WMS E2E | CC-GIN-005 v1.1 | In Progress | 按原范围继续实施和最终验收 |
| 阶段 4B | API01 保税入库预报 `snList` 条件处理及预报/实绩边界 | CC-GIN-007 v1.0 | **Closed** | CC-TEST-057–070 PASS；Ginlong 全量 71 post-tests 0 failed/0 error；HVR-API01-01–06 PASS。HVR-API01-07 为 API04 辅助出站 UI 核查，NOT RUN 且不阻塞关闭；详见 FR-GIN-007 |
| 阶段 4C | API01/03/05/07 有效业务记录驱动的 Add 生命周期幂等、全局业务键及并发唯一 | [CC-GIN-008 v1.0 Closed](CC-GIN-008-v1.0.md) | **Closed（2026-11-24）** | FR-GIN-008 Closure SATISFIED；项目负责人 Human Review APPROVED。多 Worker HTTP 与独立人工 HVR 为 N/A/Deferred；模板同步 BLOCKED 沿用批准例外 |
| 阶段 4D | API02 收货确认状态来源与 API04 每 Picking 入库完成回传对齐 | [CC-GIN-009 v1.0 Frozen](CC-GIN-009-v1.0.md) | **Closure Review Pending（2026-11-24）** | SRS v1.6 / TDD v1.9；Ginlong 自动化 76/0、WorldDepot 回归 8/0；CC-TEST-093 浏览器会话过期，UI 浏览器证据待补；真实 Ginlong 分批协议留阶段 5 |
| 阶段 4E | API02/04/06/08 重复回传确认、稳定事件并发保护、规范化 Payload 指纹 | [CC-GIN-010 v1.0 Frozen](CC-GIN-010-v1.0.md) | **实施中** | SRS v1.7 / TDD v2.0；按稳定事件代次的 ORM 唯一槽位防并发；自动化、真实按钮/Mock HTTP、旧日志兼容及回归由 IHR/ATR-GIN-010 追踪；不设独立 HVR |
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
| 当前计划 | v2.2；阶段 4C / CC-GIN-008 Closed，阶段 4D / CC-GIN-009 In Progress；阶段 4 和阶段 5其余边界不变 |
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


## 10. CC-GIN-009 阶段基线与门禁（历史；当前执行状态见 v2.3 §12）

| 门禁/范围 | 基线或处理 | 状态 |
|---|---|---|
| 需求基线 | [SRS v1.4 Frozen with Open Items](../requirement/SRS_ginlong_apis-v1.4.md) | Human Review APPROVED |
| 技术基线 | [TDD v1.7 Frozen with Open Items](../ginlong_apis/TDD-v1.7.md) | Human Review APPROVED |
| 实施契约 | [CC-GIN-009 v1.0 Frozen](CC-GIN-009-v1.0.md) | Human Review APPROVED；实施授权已给出 |
| API02 | `status` 映射 planning→N、arrive/inbound→Y；最小收货确认操作只改变 status，不改变 lifecycle state | 本地实施/自动化验收 |
| API04 | 当前订单的 Done/Incoming Picking 自动扫描；每 Picking Event；成功跳过，失败人工重试；实际确认人 + `date_done` | 本地 Mock 组件集成验收 |
| 自动化 | API02/API04 按 CC-TEST-084–094 及相关回归执行；不重做无关 CC-001–008 的全量历史测试 | In Progress |
| 人工 HVR | 本 CC 不组织；关闭后返回原 API02/API04 HVR | N/A（本 CC）/ Deferred（项目集成） |
| 外部协议 | Ginlong 是否接受同订单多次 Picking `CREATE` 尚待真实联调确认 | Open；不阻塞本地 Mock |
| 真实环境 | 不访问真实 Ginlong 或生产环境 | 保留 CC-GIN-006 门禁 |
| 模板同步 | 按既有批准例外记录 | BLOCKED；不伪记 PASS |

## 11. v2.2 历史修订记录

| 版本 | 日期 | 变更 | 状态 |
|---|---|---|---|
| v2.1 | 2026-11-24 | CC-GIN-008 收尾基线，保留原冻结文件 | Frozen；历史版本 |
| v2.2 | 2026-11-24 | 更新 SRS/TDD 基线至 v1.4/v1.7，新增阶段 4D 与 CC-GIN-009 验收门禁 | Frozen；Human Review APPROVED |


## 12. CC-GIN-009 执行及关闭评估（2026-11-24）

| 项目 | 实际状态 | 证据/处置 |
|---|---|---|
| 上游基线 | Frozen | SRS v1.6、TDD v1.9；CC-GIN-009 v1.0；Implementation Plan v2.4 |
| Ginlong 自动化 | PASS | `/private/tmp/cc-gin-009-ginlong-20261124-final5.log`：76 post-tests、0 failed、0 error(s)，14,484 queries |
| WorldDepot 回归 | PASS | `/private/tmp/cc-gin-009-worlddepot-20261124-final2.log`：8 post-tests、0 failed、0 error(s)，112 queries |
| API02/API04 实际本地 HTTP/Mock | PASS（组件集成） | 五个回调共用本地 HTTP 接收器用例通过；API04 覆盖每 Picking、重复成功跳过及失败重试；不表示真实 Ginlong 协议通过 |
| CC-TEST-093 浏览器 UI | BLOCKED / PARTIAL | 当前 Codex 内置浏览器标签页刷新后转到 Odoo 登录页（Session Expired）；没有登录，也没有点击任何业务/回传按钮。View/ORM 自动化已通过，真实浏览器界面检查未完成 |
| 独立人工 HVR | N/A（本 CC） | CC-GIN-009 明确不设独立人工 HVR；关闭后回到原项目 API02/API04 HVR |
| Ginlong 分批协议 | OPEN | 同一订单的多个 Picking 各自 `CREATE` 待真实联调确认；不阻塞本地开发/Mock |
| 模板同步 | BLOCKED | 继续按已批准例外记录，不记 PASS |
| 本地 8099 live Registry | NOT VERIFIED | 测试运行器已升级既有 DB registry 并通过 ORM 测试；两条既有 8099 进程未重启，以免中断现有会话。浏览器已显示 Session Expired，不能据此声称服务加载版本 |

**关闭建议：** 自动化、组件集成及 WorldDepot 回归通过；CC-TEST-093 的实时浏览器检查尚未完成，故本计划将 CC-GIN-009 保持 Closure Review Pending，FR 不宣称全部 SATISFIED。补齐该 UI 证据后可重新评估；不需独立人工 HVR。

## 13. v2.3 修订记录（历史）

| 版本 | 日期 | 变更 | 状态 |
|---|---|---|---|
| v2.2 | 2026-11-24 | CC-GIN-009 冻结基线 | Frozen；历史保留 |
| v2.3 | 2026-11-24 | 更新 SRS/TDD 至 v1.5/v1.8；记录 CC-GIN-009 自动化、组件集成、回归及 UI 浏览器阻塞状态 | Frozen with Open Items；Human Review APPROVED |

## 14. CC-GIN-009 v1.0 实施状态（v2.4）

| 项目 | 状态 | 证据/处置 |
|---|---|---|
| 冻结基线 | Frozen | SRS v1.6、TDD v1.9、CC-GIN-009 v1.0；Human Review APPROVED |
| Ginlong 自动化 | PASS | `/private/tmp/cc-gin-009-ginlong-20261124-final5.log`：76 post-tests、0 failed、0 error(s) |
| WorldDepot 必要回归 | PASS | `/private/tmp/cc-gin-009-worlddepot-20261124-final2.log`：8 post-tests、0 failed、0 error(s) |
| API02/API04 本地 HTTP 组件集成 | PASS | 本地 Mock 收到真实按钮 POST；覆盖状态映射、Picking 筛选、每 Picking Event、成功跳过、失败重试和追加 API Log |
| CC-TEST-093 浏览器只读检查 | BLOCKED / PARTIAL | 内置浏览器会话已过期并转到登录页；未登录、未触发业务按钮。Form/View/ORM 自动化已通过，但不代替该浏览器证据 |
| 独立人工 HVR | N/A（本 CC） | 按 Human Review 不设独立 HVR；CC 关闭后返回项目 API02/API04 HVR |
| Ginlong 分批 CREATE 语义 | OPEN | 留真实联调确认，不阻塞本地开发/Mock |
| 模板同步 | BLOCKED | 沿用已批准例外，不伪记 PASS |
| 8099 live Registry | NOT VERIFIED | 未重启既有进程；本轮只由 Odoo 测试运行器升级既有 DB registry 并运行测试 |

**关闭状态：** 自动化及 Mock 组件集成通过，但 CC-TEST-093 浏览器检查尚未执行，FR 不宣称 Closure SATISFIED；CC-GIN-009 保持 Closure Review Pending。该浏览器检查不是独立人工 HVR。

## 15. v2.4 修订记录

| 版本 | 日期 | 内容 | 状态 |
|---|---|---|---|
| v2.4 | 2026-11-24 | 记录 CC-GIN-009 冻结基线及自动化/回归结果；保留浏览器检查与 live 8099 Registry 的未验证状态 | Frozen with Open Items；Human Review APPROVED |
| v2.5 | 2026-11-25 | 纳入已批准 CC-GIN-010：稳定业务事件串行执行、成功/未知重复确认、规范指纹与自动化验收；实施状态由 ATR/IHR 追踪 | Frozen；Human Review APPROVED |


## 16. CC-GIN-010 v1.0 冻结实施计划

| 项目 | 冻结内容 |
|---|---|
| 范围 | API02、API04、API06、API08；保持既有数据来源、Payload、Action、事件粒度 |
| 代码复用 | 现有 `ginlong.api.idempotency`、`world.depot.api.log`、来源 Chatter、通用一次性 TransientModel 向导 |
| 并发 | 稳定身份排除用户/标签/确认令牌；ORM 唯一 execution_slot 按稳定事件及代次原子竞争，同一事件同时最多一个 HTTP |
| 结果未知 | 发送后传输异常、无明确 Ginlong `returnStatus=N` 的非 2xx、无效/不完整响应；风险确认后人工重试 |
| 指纹 | 忽略 JSON 字段顺序/空白、等值数字格式及 API04/06 无序 `snList` 排列；不改真实发送 Payload |
| Event/Log | 已确认重复发送追加子 Event，关联原事件及用户时间；每次实际 POST 追加关联 API Log；取消不建 HTTP Log |
| 测试 | 单元、事务/并发组件、真实 Odoo 按钮与 Mock HTTP；核验 HTTP 次数及 ORM Event/Log/Chatter |
| 退出边界 | API10 不变；不访问真实 Ginlong/生产；本 CC 不设人工 HVR，完整业务验收回归项目 HVR |
| 模板同步 | BLOCKED；沿用批准例外，不记 PASS |

**授权记录：** Human Review APPROVED，2026-11-25。SRS v1.7、TDD v2.0、Implementation Plan v2.5 与 CC-GIN-010 v1.0 为本次实施基线；历史版本保留。
