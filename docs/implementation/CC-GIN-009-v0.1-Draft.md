# CC-GIN-009 v0.1 Draft — Inbound Callback Business Alignment

| 字段 | 值 |
|---|---|
| 文档编号 | CC-GIN-009 |
| 文档状态 | **Draft — 等待 Human Review** |
| 模块 | `ginlong_apis`；仅按需读取/扩展既有 `worlddepot` 与 Odoo `stock` 记录 |
| 工作类型 | 回传行为调整、表单界面调整、集成变更 |
| 目标 | 使 API02 从入库单现有业务状态生成回传；使 API04 自动从当前入库单的已完成入库 Picking 读取实际作业数据；使用既有 Ginlong Event/Log 反馈结果。 |
| 当前冻结上游 | SRS v1.3、TDD v1.6、Implementation Plan v2.1；本 CC 草案不覆盖或修改这些版本 |
| 上游有效性 | **Impact Review Required（如本草案获批，须先修订并冻结受影响上游基线）** |
| 模板同步 | **BLOCKED**：项目模板来源缺失；沿用项目已批准的模板同步例外，不伪记 PASS |
| 授权状态 | 仅授权起草和评审；不授权代码修改、模块升级、测试、HVR、数据变更或 Git 操作 |

## 1. 变更概述

当前 API02 依赖 `ginlong.inbound.receipt.detail` 和逐行 `receipt_status`；API04 依赖用户在 Notebook 中勾选 `stock.picking.ginlong_callback_selected`。本 CC 提议改为复用入库单业务状态和现有实际 Picking 自动发现流程，并以 Ginlong API Tab 显示只读回传结果。

本 Draft 保留待决事项，不把技术方案中的建议当成已批准规则。API02 状态映射、API04 批次单位及现场人员/时间来源确认前，不得冻结或实施。

## 2. 上游基线与追溯

### 2.1 SRS

| SRS ID | 当前条款 | 与本 CC 的关系 |
|---|---|---|
| FR-GIN-002 | 用户手动点击 API02；按现有业务服务和确认字段生成 Payload；记录操作人、时间、Payload/关联信息及结果 | 需明确来源改为 `inbound.order` 业务状态，并澄清 `receiptConfirmed` 的状态映射 |
| FR-GIN-004 | API04 从实际 `stock.picking` / `stock.move.line` 取数；每次手动触发；分批语义待确认 | 需明确按当前订单自动扫描 `done` 且 `incoming` 的关联 Picking，并决定批次/重复回传边界 |
| BR 6.1.1、6.1.5、6.1.6 | 区分收货确认与入库完成；只手动触发；未经列明不增加额外状态门禁 | API04 的 Picking 域需作为明确的数据来源条件写入基线；不得扩展成其他状态审批规则 |
| BR 6.1.3、NFR/异常追踪 | 业务操作、结果回传独立追踪；每次手动回传记录操作及结果 | UI 展示和 Event/Log 追踪依据 |

### 2.2 TDD

| 当前 TDD 位置 | 当前设计 | 拟变更影响 |
|---|---|---|
| §2.2 / §3 API02 | API02 持久化收货明细子表，并将明细 Y/N 汇总为订单级值 | 停止 API02 读取/依赖该子表，改由批准的订单状态映射生成 Payload |
| §2.2 / §3 API04 | API04 仅读取已选择的 Picking | 改为按本订单关系和指定完成/类型域自动读取 |
| §2.2 / §4.1 | 在 Picking 上持久化选择字段；API04/06 读取所选 Picking；move line 上另填操作人员和时间 | API04 不再使用选择字段；人员/时间不可继续要求用户重复录入，须先确认权威来源 |
| §3 / §4.1 / §11 | API04 批次范围及撤销仍有 Open Item | 需确定每个实际 Picking 是否构成独立回传事件，以及当前 Event 键如何识别每批 |
| §2.2 / UI | 当前要求持久化 Notebook，并展示业务数据 | 调整为类似现有 Hoymiles APIs Tab 的按钮及只读结果状态/时间/错误，不复制其 HTTP 实现 |

### 2.3 Implementation Plan

当前计划 v2.1 以 SRS v1.3/TDD v1.6 为有效基线。若 Human Review 批准本 Draft 的上游语义修改，应先修订、审批并冻结 SRS/TDD，更新计划基线、影响分析和 CC 阶段映射，再冻结本 CC 和实施。该 Draft 不能作为实施基线。

## 3. 范围

### 3.1 在范围内（拟议）

1. API02 从已确认的 `inbound.order` 业务状态生成 `receiptConfirmed`；不读取 Picking、move line 或额外收货明细。
2. API02 仍由用户点击 Order 上的回传按钮手动触发；复用 Ginlong API Event、现有 HTTP Endpoint 和 API Log。每次点击的尝试记录追加到 API Log；Event 的创建/复用遵循现有幂等语义，不为点击次数另建事件模型。
3. API04 用户在入库 Order 上点击回传按钮后，系统自动搜索：
   - `stock.picking.inbound_order_id = 当前 inbound.order`
   - `stock.picking.state = done`
   - `stock.picking.picking_type_id.code = incoming`
4. API04 从符合条件 Picking 的实际 `stock.move.line` 构造 Payload；不使用 API01 预报数据，不要求用户勾选 Picking。
5. 入库单 Form 增设/调整 `Ginlong APIs` Tab，分别提供 API02、API04 按钮及只读的最近回传结果、回传时间和错误信息。
6. 复用现有 `ginlong.api.idempotency`、`world.depot.api.log`、Endpoint 设置、认证/权限和标准 WMS 作业数据。
7. 针对 API02/API04 变更增加 Odoo 自动化及组件集成测试；实施完成后按批准 CC 执行人工 HVR。

### 3.2 范围外

- API06、API08、API10 的行为、视图或模型变更；本 Draft 第 10 节仅记录横向发现。
- Ginlong 回传协议字段、Action 或响应格式变更；不访问真实 Ginlong。
- Karl Rapp Gateway、XML/FTP/VPN、库存同步或库存处理改造。
- 新 API 日志框架、新幂等模型、通用集成平台、额外状态机或审批流。
- 清理或删除历史 API Event、API Log、业务明细或 Picking 数据。
- 对 API04 没有符合条件 Picking 的入库单执行自动回传、定时任务或后台重试。

### 3.3 非目标

- 不把 API02 收货确认解释为 API04 入库完成。
- 不以 `inbound.order.status = inbound` 自动推定“整单收货完成”；现有 WMS 在一个 incoming Picking 完成时即可将订单状态写成 `inbound`。
- 不将按钮点击用户、订单负责人或 Picking 创建者直接认定为 KR 实际作业人员。

## 4. 变更边界

### 4.1 拟允许修改（Human Review 批准并完成上游基线更新后）

| 路径 | 允许范围 |
|---|---|
| `mymodules/ginlong_apis/models/ginlong_callbacks.py` | API02 状态取值；API04 自动搜索合格 Picking、Payload、Event 上下文；API Tab 只读结果字段/查询；复用日志 |
| `mymodules/ginlong_apis/views/ginlong_callback_views.xml` | 入库 Order 的 Ginlong APIs Tab、两项按钮及只读结果区；移除 API02 明细编辑和 API04 Picking 勾选入口 |
| `mymodules/ginlong_apis/tests/test_ginlong_api.py` | API02/API04 HTTP/ORM/Event/Log/视图及回归用例 |
| `mymodules/ginlong_apis/data/idempotency_rules.json` | 仅当批准的 API04 批次事件设计要求为每 Picking 构造稳定 Event 身份时，调整 API04 事件键规则 |
| `mymodules/ginlong_apis/models/wms_extensions.py` | 仅在上游批准的清理决策明确后处理废弃字段/关系；默认保留现状及历史数据 |

不得修改禾麦 HTTP 代码、`worlddepot` 入库状态转换、库存核算或无关 API 路径。若实现发现需要修改，应暂停并提交范围/基线变更。

### 4.2 默认保留

- `ginlong.inbound.receipt.detail` 模型和历史行：拟停止 API02 读写，但不删除模型、字段或数据；是否后续正式废弃列为待 Human Review 决策。
- `stock.picking.ginlong_callback_selected`：API06 仍使用，不能在本 CC 中删除；API04 改为忽略该字段。
- `stock.move.line.ginlong_operator_code` / `ginlong_operation_time`：API06 仍依赖；API04 是否复用或停止要求人工填写须待真实数据源决定。
- `ginlong.api.idempotency` 与 `world.depot.api.log`：保留全部既有行和字段，不重建、不清理。按钮区域只读展示最近一次相关 API Log 的结果、时间和错误；完整请求/响应仍在现有 API 日志中查看。

### 4.3 禁止

| 类型 | 禁止事项 |
|---|---|
| 协议 | 不自行确定 API02 状态映射、API04 批次/增量/整单语义、API04 `operator`/`operationTime` 来源 |
| 数据 | 不删除或迁移额外收货明细历史、幂等记录、API 日志、Picking、move line、Lot、Package 或库存 |
| 业务 | 不新增订单状态门禁，不因没有 Picking 改变 inbound.order 状态，不自动发送或自动重试 |
| 范围 | 不修改 API06/API08/API10，不改变 API02/API04 之外的 Ginlong 行为 |
| 环境 | 不调用真实 Ginlong API，不访问生产环境，不做 Git 提交/推送 |

## 5. 必需行为变更（拟议）

| ID | 当前行为 | 拟议期望 | 追溯 |
|---|---|---|---|
| CC-CHANGE-001 | API02 读取 `ginlong.inbound.receipt.detail.receipt_status`；无行时无值，混合 Y/N 时拒发 | 读取 Human Review 指定的现有 inbound.order 状态字段，按批准映射构造 Y/N；不查 Picking/move line/明细子表 | SRS FR-GIN-002（须修订）；TDD §2.2 / §3（须修订） |
| CC-CHANGE-002 | API04 要用户选择关联 Picking；未筛选 done/incoming | 按批准域自动检索当前订单的 done/incoming Picking 并读取实际 move line | SRS FR-GIN-004（须修订）；TDD §2.2 / §4.1（须修订） |
| CC-CHANGE-003 | API04 使用 Order 级事件上下文加全量 Payload 指纹；批次重叠可能使旧行再次进入新事件 | 按批准的批次单位定义 Event 身份，使相同作业批次的重复点击不重复发送、不同批次不重发已成功批次 | TDD §3 / §4.1（须修订）；Ginlong 部分/整单语义待决 |
| CC-CHANGE-004 | Ginlong Notebook 暴露 API02 明细输入、API04 Picking 勾选；无只读的分接口回传结果区 | 采用 APIs Tab 分组展示两个按钮及各自最近成功状态、时间、错误；数据从现有 Log/Event 读取，不为界面再造持久化审计状态 | SRS FR-GIN-002/004；TDD UI 设计（须修订） |

## 6. 既有行为保留

| ID | 保留内容 | 原因 |
|---|---|---|
| CC-PRESERVE-001 | API02/04 仍是用户手动按钮触发；同步 POST JSON；使用配置 Endpoint | SRS 与现有 API 约定 |
| CC-PRESERVE-002 | API02 收货确认与 API04 实际入库完成是不同事件 | SRS BR 6.1.1；不得相互推断 |
| CC-PRESERVE-003 | API04 只以关联当前订单的实际 Picking/move line 生成作业数据，不读 API01 预报数据 | SRS FR-GIN-004、TDD §4.1 |
| CC-PRESERVE-004 | 每次用户触发均写现有 API Log；历史日志不可覆盖；同一成功事件按批准的 Event 身份防重 | 现有日志与幂等契约 |
| CC-PRESERVE-005 | API04 必需字段仍遵循 V3.2；不得用人工点击时间/操作人填充现场事实 | V3.2 API04 行及既有 TDD 防护栏 |
| CC-PRESERVE-006 | API06 继续使用 `ginlong_callback_selected` 和其现有重量/托盘行为 | 本 CC 不改 API06 |

## 7. 人类决策项（冻结前必须处置）

| OI | 当前证据 | 最小方案 / 建议 | Human Review 必须确认 |
|---|---|---|---|
| OI-01 API02 收货状态与 Y/N 映射 | `inbound.order.state` 为 `new/confirm/cancel`；现有 `action_confirm()` 将 `new→confirm` 并记录确认人/时间；另一个 `status` 字段为 `planning/arrive/inbound`，其中 `inbound` 可由 incoming Picking 完成时写入 | 以订单现有业务状态为唯一来源；优先评估不依赖 Picking 的 `state`，不要把 Picking 驱动的 `status=inbound` 当作独立收货确认 | 哪个现有订单状态表示收货确认，以及该状态对应 `receiptConfirmed=Y` 还是 `N`；未达到该状态或已取消时应回传何值，或是否阻止发送。API02 Action 和协议结构不在本 CC 擅自更改 |
| OI-02 API04 批次单位及防重 | V3.2 一处说明支持部分过账，另一处要求第三方整单确认后调用；现 Event 绑定 Order 和完整 Payload 指纹 | 推荐将单个 `stock.picking` 作为一个回传事件，Event 身份包含 picking 标识；按钮自动扫描所有符合条件 Picking，只发送尚未成功的独立批次。这样避免新 Picking 到达时把已成功旧行再次放入累计 Payload | 是否批准 per-picking 多次 POST；若要求整单聚合，谁/何种既有业务状态表示“最后一批已完成”，以及如何识别/排除此前已回传批次。不得把 `status=inbound` 当整单完成，因为它可在一张 Picking 完成时设置 |
| OI-03 API04 实际操作人/时间 | V3.2 `snList` 要求每条 `operator`、`operationTime`；现 `ginlong_*` move-line 字段由用户手工维护，不是自动提取 | 优先核实现有 WMS 实际作业来源；如果没有逐行人员/时间，先明确是否接受可靠的既有字段或需由 Ginlong 调整契约。未获批准前不得用回传用户、负责人或 `date_done` 冒充逐 SN 实绩 | 权威字段/粒度；是否每 SN 真实操作时间必需；如果现有数据不存在，选择补充业务采集还是调整外部契约 |
| OI-04 额外模型、共享字段及历史数据处置 | `ginlong.inbound.receipt.detail`/订单 One2many 服务于现 API02；`ginlong_callback_selected`、`ginlong_operator_code`、`ginlong_operation_time` 还被 API06 使用 | API02 停止读写额外收货明细并从业务页移除其维护入口；默认保留模型、字段和历史行，不迁移、不删除；API04 忽略共享选择字段的同时保留 API06 所需数据 | 确认是否接受“停用 API02 写入与界面、保留模型/字段/历史数据”的最小方案。若后续要求物理删除，先核对所有调用方及历史引用，再走独立数据处置批准 |

## 8. 测试契约（实施阶段拟执行；当前均未运行）

| 测试 ID | 测试行为 | 类型 | 预期断言 |
|---|---|---|---|
| CC-TEST-084 | API02 状态与 Payload 映射 | Odoo ORM 集成 | 按批准状态逐项执行现有业务操作；Payload 的 `receiptConfirmed` 符合明确映射；API02 不查询 Picking、move line 或收货明细子表 |
| CC-TEST-085 | API02 无作业单时发送 | HTTP 组件集成 | 仅有有效 inbound.order 状态而没有任何 Picking/明细子表时，真实按钮仍按映射调用 Mock；断言实际 POST、响应、Event 与 Log |
| CC-TEST-086 | API02 状态操作追踪 | ORM/回归 | 执行现有 `action_confirm()` 后状态、确认人/时间和 chatter tracking 保持 WMS 行为；API 回传不改写订单状态 |
| CC-TEST-087 | API02 重复点击及状态变化 | HTTP/幂等集成 | 重复点击和状态变化分别按已冻结的幂等规则及 OI-01 批准映射验证；逐次核对实际 HTTP 次数、Event 复用/记录及追加的 API Log，不把缓存响应冒充实际 POST |
| CC-TEST-088 | API04 Picking 自动筛选 | ORM 集成 | 构造当前订单 incoming/done、incoming 非 done、outgoing/done、其他订单 incoming/done；Payload 只包含第一类 |
| CC-TEST-089 | API04 读取实际 move line | Mock HTTP/ORM 集成 | 实际 product/SN/quantity/package/operator/time 来源符合批准字段映射；不读取 API01 预报，不需要人工勾选或重录已有字段 |
| CC-TEST-090 | API04 多 Picking 和批次界限 | HTTP/Event 集成 | 严格按 Human Review 批次决定验证：批次独立、成功批次不重发、失败/未知批次可按既定同事件重试；无重复旧明细 |
| CC-TEST-091 | API04 不合格 Picking 排除 | HTTP/ORM 集成 | 不符合订单、state、picking type 任一筛选条件的 Picking 不进入 Payload；若无合格作业，发送被阻止并留下清晰 Log，不更改 WMS 状态/库存 |
| CC-TEST-092 | 回传失败后重试 | Mock HTTP/ORM 集成 | 首次 Mock 失败；修正已确认的数据源后人工再点击；旧 Log 保持不变，新 Log 追加；无后台重试 |
| CC-TEST-093 | Ginlong APIs Tab 只读反馈 | Odoo 浏览器/ORM 集成 | 两个接口分别显示按钮及最近成功、时间、错误；结果由当前 API Log/Event 读取；业务用户不能编辑/清除日志或 Event |
所有测试须通过真实 Odoo 按钮/业务入口和 Mock HTTP 接收端，断言响应、Payload、ORM 状态、Event、Log 与必要副作用。静态检查不能作为 PASS。若实现触及共享回传或视图路径，只运行与变更直接相关的既有 API06/API08/API10 回归；不为它们增加本 CC 的业务功能验收。实际状态只能在 IHR/ATR 中按执行证据记录。

## 9. 人工 HVR（实施后计划；本轮未执行）

| HVR | 人工动作 | 核对点 |
|---|---|---|
| HVR-GIN-009-01 | 通过入库单现有收货确认操作改变业务状态，打开 `Ginlong APIs` Tab，点击 API02 按钮 | 状态显示、`receiptConfirmed`、Mock 收到的 HTTP、API Event/Log、成功/时间/错误只读信息；无需创建 Picking 或收货明细子表 |
| HVR-GIN-009-02 | 通过 Ginlong 入站 API01 创建入库单，完成并过账至少两张关联 incoming Picking，再从该 Order 点击 API04 | 系统只扫描正确 Order 的 `done/incoming` Picking；用户无需勾选；核对批次方案规定的 Payload 数量及 Event 防重 |
| HVR-GIN-009-03 | 修改 Mock 为失败后重新点击 API02/API04 | 失败提示、用户手动重试、日志追加及只读错误/时间刷新；历史日志保留 |

HVR 由项目负责人执行并填写。本 Draft 阶段 HVR 状态为 **NOT RUN**，不得预填 PASS。

## 10. 横向检查（仅报告，不纳入本 CC）

| API | 代码现状 | 同类问题评估 |
|---|---|---|
| API06 | 同样通过 `ginlong_callback_selected` 选择 Picking；读取 move line 与 Order 手工覆盖的托盘/重量 | 有 API04 类似的人工选择，但 API06 属备货业务，是否自动筛选及批次策略须单独评审。本 CC 保持不变 |
| API08 | 通过 `ginlong.outbound.shipment.detail` 逐明细维护 `shipment_status`，再汇总为订单级字段；混合值阻止发送 | 与旧 API02 的“明细状态推导订单状态”结构相似。是否可直接使用 outbound.order 状态需独立核对 SRS/TDD/WMS，不在本 CC 处理 |
| API10 | 从当前 stocktake order 的真实 `result_ids` 中读取用户已选结果；V3.2 支持部分采集与撤回范围 | “选择结果范围”可能是部分采集/撤回的业务输入，不能直接按 API04 规则删除。保持现状，除非独立评审确认不再需要 |

以上是源码观察，不等于已经批准这些 API 的业务变更。

### 10.1 静态审查证据

| 依据 | 文件 / 位置 | 本 Draft 使用的事实 |
|---|---|---|
| Ginlong V3.2 | `docs/ginlong_apis/海外WMS与第三方系统集成V3.2.xlsx`，工作表“海外WMS与第三方系统的接口与处理逻辑”，API02 第 21–23 行、API04 第 24–32 行 | API02 的 `receiptConfirmed` 为订单级字段；API04 `snList` 包含产品、数量、托盘、操作人和操作时间；接口描述同时出现部分处理与整单回传语义，故批次边界需 Human Review |
| 冻结需求 | `docs/requirement/SRS_ginlong_apis-v1.3.md`，BR 6.1、FR-GIN-002/004、异常追踪 | 收货确认与入库完成分离；回传由用户手动触发；API04 数据来自实际 Picking；批次/重复语义留待决 |
| 冻结设计 | `docs/ginlong_apis/TDD-v1.6.md`，§2.2、§3、§4.1、§11 | 现有设计包含 API02 收货明细、API04 Picking 手选、move line 操作人/时间字段及批次 Open Item |
| 当前计划 | `docs/implementation/IMPLEMENTATION_PLAN_ginlong_apis-v2.1.md`，阶段 4B/CC-GIN-007 与当前基线表 | 当前批准基线指向 SRS v1.3/TDD v1.6；本 Draft 不覆盖该冻结计划 |
| Odoo 入库单 | `mymodules/worlddepot/models/inbound_order.py`，`state`、`status`、`action_confirm()` | `state` 为 `new/confirm/cancel`；确认动作要求既有单据资料并将 `new` 改为 `confirm`；该名称本身不能证明是实际收货完成 |
| Picking 状态写入 | `mymodules/worlddepot/models/my_stock.py`，`_update_inbound_order_status()` | incoming Picking 验证后可将关联入库单 `status` 写成 `inbound`；不能据此推断整张订单所有分批入库均完成 |
| Ginlong 回传当前实现 | `mymodules/ginlong_apis/models/ginlong_callbacks.py`，`_api02_payload()`、`_api04_payload()`、`_write_api_log()`、`send_callback()` | API02 读收货明细；API04 读手选 Picking 与 move lines；现有日志关联来源业务单，手动点击追加 API Log |
| 当前页面 | `mymodules/ginlong_apis/views/ginlong_callback_views.xml` | 当前入库单回传页提供 API02 明细和 API04 Picking 选择控件 |
| 禾麦页面参考 | `mymodules/worlddepot/views/inbound_order.xml` §“Hoymiles APIs”；`mymodules/worlddepot/models/inbound_order_status.py` | 已有分组按钮及只读成功标志、时间、错误信息布局；仅借鉴交互布局，不复用其 HTTP 发送实现 |

## 11. 实施停止条件

1. OI-01 未决定 `state` 字段及其 Y/N 映射：停止 API02 实施。
2. OI-02 未确定 API04 是逐 Picking 还是整单聚合，以及同批重复规则：停止 API04 Event/发送改造。
3. OI-03 仍无真实 operator/operationTime 来源：停止声称 API04 自动 Payload 完整；不得以假的用户/时间填充。
4. 既有冻结 SRS/TDD/Plan 尚未完成获批修订：本 CC 维持 Draft，不得冻结或启动编码。
5. 发现既有 WMS 状态操作、权限、库存或 API06 行为需改动：停止并重新评估范围。
6. 发现旧子表有非 API02 依赖或删除会丢失审计/业务历史：保留数据并提交 Human Review；禁止自动清理。

## 12. 完成定义（拟议）

- OI-01–04 均由 Human Review 明确处置；SRS/TDD/Implementation Plan 完成必要修订并重新批准、基线有效。
- API02 通过自动化验证：从批准的现有业务状态生成报文，不依赖 Picking/move line/额外明细；事件及日志可追溯。
- API04 通过自动化验证：严格按订单、done、incoming 自动筛选实际 Picking；批次去重行为符合批准的外部语义；无人工选择或重复维护已有作业事实。
- Ginlong APIs Tab 两接口按钮及只读结果展示通过自动化/浏览器验证。
- 相关既有 WMS 定向回归通过；若共享路径受影响，则相应既有回归通过。API06/API08/API10 不因此纳入本 CC 的业务变更范围；没有未执行项被伪记 PASS。
- IHR/ATR/HVR 保留实际执行证据；未调用真实 Ginlong，不声称真实联调通过。
- 项目负责人完成人工 HVR 和关闭评审后，方可生成关闭 FR。

## 13. 评审状态与版本记录

| 版本 | 日期 | 状态 | 说明 |
|---|---|---|---|
| v0.1 | 2026-11-24 | **Draft** | 根据 API02/API04 业务设计审查起草；列出状态映射、批次和人员/时间 Open Items；不改代码、不改上游冻结文档、不执行测试/HVR，等待 Human Review。 |

| 评审项 | 当前状态 |
|---|---|
| Human Review | Pending |
| 实施授权 | 未授权 |
| 代码/测试/HVR/Git | 未执行 |
| 模板同步 | BLOCKED；沿用已批准例外，不记为 PASS |

