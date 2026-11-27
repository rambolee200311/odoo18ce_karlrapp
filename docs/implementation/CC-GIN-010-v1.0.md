# CC-GIN-010 v1.0 — API02/04/06/08 重复回传确认

| 项目 | 内容 |
|---|---|
| 状态 | **Closed** |
| Human Review | **APPROVED；项目负责人李建强；2026-11-25** |
| 范围 | API02、API04、API06、API08 |
| 上游基线 | [SRS v1.8](../requirement/SRS_ginlong_apis-v1.8.md)、[TDD v2.1](../ginlong_apis/TDD-v2.1.md)、[Implementation Plan v2.6](IMPLEMENTATION_PLAN_ginlong_apis-v2.6.md) |
| 实施授权 | 已批准，直接实施 |
| 模板同步 | BLOCKED；沿用批准例外，不作为 PASS |

## 1. 目标

为四个 Odoo 主动回传 API 提供统一的重复/未知结果确认及稳定业务事件并发保护，防止静默跳过、缓存成功冒充本次 HTTP、不同用户/标签页并发发送。不得改变接口业务事实来源、Payload、Action 或事件粒度。API10 不变。

## 2. 业务契约

1. 稳定业务事件身份按 API、来源记录、Action 和现有事件粒度形成，不含用户、标签页、确认令牌、`write_date` 或 Event 行 ID。API02/06/08 为既有订单事件；API04 每张 Done/Incoming Picking 一个事件。
2. Payload 指纹区分同一事件的内容版本。对象键顺序、JSON 空格/序列化紧凑度、等值数字 `1`/`1.0` 和 API04/06 `snList` 的非业务排列变化不改变指纹；实际发送报文不被改写。
3. 新/变化 Payload 且无该版本成功历史时直接发送；明确失败可直接人工重试；同 Payload 成功历史弹出确认；结果未知必须显示风险并经用户确认后才能重试。
4. 已明确 Ginlong `returnStatus=N` 或可证明未发送/明确拒绝的结果为 failed；POST 后超时/连接异常、未明确 N 的 5xx、无效/不完整成功 HTTP 响应为 unknown。未知不自动重试。
5. API04 混合多 Picking 提供“仅回传未成功项（默认）/回传全部/取消”。处理中项目跳过。未知事件只有用户明确勾选风险确认才可发。API06 多 Picking 数据仍为一个订单聚合事件。
6. 向导只存来源引用、指纹、事件范围、摘要和一次性令牌；确认时重读 ORM 并重建 Payload。数据变化后以当前 Payload 重判，禁止发送旧快照。
7. 用户确认重发成功/未知事件后真实 POST，现有幂等表追加子 Event 并关联原 Event、确认用户及时间。每个真实 HTTP 请求追加并关联一条 API Log。取消/未发送不能伪装 HTTP 成功；用户决定通过来源 Chatter 追加。历史 Event/Log 不覆盖。
8. 同一稳定事件同时最多一个 HTTP 请求。回传/确认按钮在当前 RPC 期间由标准 Odoo UI 显示忙碌/禁用；服务端使用既有幂等记录与 ORM 唯一/行竞争作为权威。处理中或请求等待期间刚完成时不发送、不弹历史成功确认。确认令牌一次消费。
9. 旧成功历史以旧 API Log 的 API、source_record、success 和规范化 request_data fingerprint 兼容识别；早期成功日志作为原始成功时间，不改写旧数据。

## 3. 范围与约束

- 复用既有 `ginlong.api.idempotency`、`world.depot.api.log`、Chatter 和同一个通用 TransientModel 确认向导；可按需为现有模型加最小字段及 ORM 唯一约束。
- 不新增独立幂等/锁/防抖服务、Event 模型或业务状态机。
- API10 维持原行为；不改 Ginlong 协议或业务 Payload；不触及 KR Gateway、库存/WMS 业务。
- 只在本地开发数据库运行 Odoo 自动化与本地 Mock HTTP，不访问真实 Ginlong、生产或真实 KR。
- 本 CC 不举行独立人工 HVR；完成后回到原项目业务 HVR 并更新其操作指南。

## 4. 实施范围

1. 规范化 Payload fingerprint，并静态配置 API04/06 无序明细路径。
2. 扩展现有幂等记录：稳定事件协调键、执行状态/代次和时间、重复 Event 父关系、一次性确认 token、确认用户/时间；API Log 增加幂等 Event 关联。
3. 实现一个通用确认向导：显示业务对象、上次状态/时间/结果摘要；单 Event 确认/取消，API04 多 Event 三选项和未知风险确认。
4. API02/04/06/08 回传入口接入事件判定、历史兼容、事务并发序列化和真实 HTTP Log。API10 保持不变。
5. 标准 Odoo 按钮交互期间保持 loading/disabled；确认令牌后端一次消费。

## 5. 测试矩阵

| ID | 测试场景 | 主要断言 |
|---|---|---|
| CC-TEST-101 | API02/04/06/08 首发 | 真实按钮触发 Mock POST；Payload、Event、Log 来源正确 |
| CC-TEST-102 | 成功同 Payload 再点 | 显示确认摘要；用户决策前 HTTP/Event/Log 数不变 |
| CC-TEST-103 | 成功确认重发 | 新 POST、子 Event parent、确认用户/时间、关联新 Log |
| CC-TEST-104 | 成功取消 | HTTP/Event/Log 不增加；来源 Chatter 记录取消 |
| CC-TEST-105 | 明确失败重试 | 不弹成功框，允许直接重试；每次 HTTP 单独 Log |
| CC-TEST-106 | 网络超时/连接异常未知 | 未确认不重试；取消零发送；风险确认后实际 POST |
| CC-TEST-107 | 无 N 的 5xx / 无效 2xx | 分类 unknown 并要求用户风险确认 |
| CC-TEST-108 | payload 业务内容改变 | 无对应成功版本则直接发送；旧历史保留 |
| CC-TEST-109 | 无关字段/`write_date` 改变 | 同 Payload 仍识别为已有成功版本 |
| CC-TEST-110 | 字段顺序、空白、1/1.0、snList 排列 | 指纹等价；实际 Payload 原样保留 |
| CC-TEST-111 | 确认打开后 Payload 变化 | 重读 ORM；不发送旧快照并按新 Payload 判定 |
| CC-TEST-112 | 同一 token 重复确认 | 实际 HTTP 最多一次；令牌消费一次 |
| CC-TEST-113 | 多用户/标签页不同令牌并发 | 同稳定事件 HTTP 恰一次；第二请求无并发发送或成功弹窗 |
| CC-TEST-114 | 连续按钮/确认点击 | 实际 HTTP 计数符合单事件执行；UI pending 状态和后端保护有效 |
| CC-TEST-115 | API04 成功/失败/首次混合 | 默认只发未成功项；全部/取消分支准确；unknown 需确认 |
| CC-TEST-116 | API04 Picking 事件粒度 | 每张 Picking 独立 Event/Log，不改变 Payload 与筛选条件 |
| CC-TEST-117 | API06 多 Picking 聚合 | 单订单聚合一个 Event，不拆成 Picking 事件 |
| CC-TEST-118 | 旧格式成功历史 | API Log source/API/success/fingerprint 识别旧成功；最早成功时间显示 |
| CC-TEST-119 | API10 回归 | 本次修改不改变 API10 的事件和发送行为 |
| CC-TEST-120 | API Log/Event/Chatter 关联 | 仅实际 HTTP 有 HTTP Log；历史不覆写，确认决定可追踪 |

自动化需分层统计单元、ORM 事务组件集成及真实 Odoo 按钮/本机 Mock HTTP；逐 API 断言实际请求数、Payload、Event、API Log 和 Chatter。未运行/失败/阻塞分别记录。

## 6. Done Gate

- 上述适用测试通过；模块及受影响回归通过；无实际 HTTP 重复发送缺陷。
- API02/04/06/08 各自事件粒度、成功/失败/未知分类、历史兼容、回传日志关系有执行证据。
- `ATR-GIN-010` 保留测试 RUN、命令、数据库、日志路径；`IHR-GIN-010` 记录实施和边界；`FR-GIN-010` 提交关闭评审。
- 不要求人工 HVR，不执行真实 Ginlong 联调。

## 7. Open Items

| 项目 | 状态 | 影响 |
|---|---|---|
| Ginlong 外部 5xx/超时后业务接收语义 | 按本 CC 保守视为 unknown | 本地确认机制不阻塞；真实重试策略仍由业务用户确认 |
| 模板同步 | BLOCKED，沿用已批准例外 | 不阻塞 CC-010 |
| 真实 Ginlong 联调 | Deferred 至最终联调 CC | 本 CC 只用 Mock |

## 8. 冻结记录

| 版本 | 日期 | 状态 | 审批 |
|---|---|---|---|
| v1.0 | 2026-11-25 | **Frozen** | Human Review APPROVED；授权本地实现及 Mock 自动化/组件集成测试 |

## 9. 实施及关闭评审证据

| 项目 | 状态 | 证据 |
|---|---|---|
| API02/04/06/08 实施 | 完成 | 复用 `ginlong.api.idempotency`、API Log、Chatter 和通用确认向导；API10 未改变 |
| 模块全量自动化 | PASS | [ATR-GIN-010](ATR-GIN-010.md)：最终 ATR-RUN-008 为 82 post-tests，0 failed，0 error；早期失败 RUN 保留 |
| 稳定事件并发专项 | PASS | 同一稳定事件跨不同确认令牌/标签页并发，Mock HTTP 仅一个请求；ORM Event/Log 断言通过 |
| 本地服务 | PASS | Odoo Shell ORM 确认 `ginlong_apis` state=installed，`installed_version=latest_version=18.0.2.0.47`；8099 监听 |
| 人工 HVR | N/A | Human Review 决定本 CC 不单独组织人工 HVR；关闭后回到项目业务 HVR |
| 外部/模板事项 | Deferred / BLOCKED | 真实 Ginlong 结果语义留最终联调；模板同步沿用批准例外，不伪记 PASS |

**关闭记录：** Done Gate 已满足；项目负责人于 2026-11-25 Human Review 批准关闭。证据见 [FR-GIN-010](FR-GIN-010.md)、[ATR-GIN-010](ATR-GIN-010.md) 与 [IHR-GIN-010](IHR-GIN-010.md)。

## 10. 关闭记录

| 项目 | 结果 | 证据 |
|---|---|---|
| CC-TEST-101～120 证据映射 | SATISFIED | [ATR-GIN-010 §3](ATR-GIN-010.md) 将每项映射到实际测试方法、RUN 和执行结果；冻结测试无未执行的必要自动化项 |
| 全量 Ginlong 自动化 | PASS | ATR-RUN-008：82 post-tests，0 failed，0 error |
| 冻结矩阵缺口补测 | PASS | ATR-RUN-011：7 个补充/强化场景，7 post-tests，0 failed，0 error；不将定向运行冒充全量运行 |
| 本地模块版本 | PASS | ATR-RUN-009：8099 HTTP 200；ORM 核实安装版本及 latest version 为 `18.0.2.0.47` |
| CC 独立人工 HVR | N/A | 按已批准范围不单独组织；项目级 HVR 继续单独执行，未在本 CC 标记 PASS |
| 模板同步 | BLOCKED（批准例外） | 保留原状态，不作为 PASS |
| 真实 Ginlong/生产 | Deferred | 留待最终集成授权，不属于本地 CC 验收 |

**Human Review：APPROVED；Closure：SATISFIED；状态：Closed。**
