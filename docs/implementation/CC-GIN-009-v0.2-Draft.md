# CC-GIN-009 v0.2 Draft — Inbound Callback Business Alignment

| 字段 | 值 |
|---|---|
| 文档编号 | CC-GIN-009 |
| 文档状态 | **v0.2 Draft — 等待 Human Review** |
| 模块 | `ginlong_apis`；仅按需读取/扩展既有 `worlddepot` 与 Odoo `stock` 记录 |
| 工作类型 | 回传行为调整、表单界面调整、集成变更 |
| 目标 | API02 从 `inbound.order.status` 生成收货确认；API04 自动扫描当前订单关联的 Done/Incoming Picking，并以 Picking 为本地回传事件单位；用既有 Ginlong Event/API Log 展示回传结果。 |
| 当前冻结上游 | SRS v1.3、TDD v1.6、Implementation Plan v2.1；本 CC 草案不覆盖或修改这些版本 |
| 上游有效性 | **Impact Review Required（如本草案获批，须先修订并冻结受影响上游基线）** |
| 模板同步 | **BLOCKED**：项目模板来源缺失；沿用项目已批准的模板同步例外，不伪记 PASS |
| 授权状态 | 仅授权修订 CC 草案；不授权代码修改、模块升级、测试、HVR、数据变更或 Git 操作 |

## 1. 变更概述

当前 API02 依赖 `ginlong.inbound.receipt.detail` 和逐行 `receipt_status`；API04 依赖用户在 Notebook 中勾选 `stock.picking.ginlong_callback_selected`。本 CC 改为从 `inbound.order.status` 生成 API02 Payload，并让 API04 自动发现符合条件的实际 Picking。两个接口分别在 Ginlong APIs Tab 提供回传按钮和只读结果。

本 Draft 区分 Human Review 已确认的设计方向、尚待确认的本地业务定义及外部协议 Open Item。v0.2 尚未冻结，不能作为实施基线。

## 2. 上游基线与追溯

### 2.1 SRS

| SRS ID | 当前条款 | 与本 CC 的关系 |
|---|---|---|
| FR-GIN-002 | 用户手动点击 API02；按现有业务服务和确认字段生成 Payload；记录操作人、时间、Payload/关联信息及结果 | 改为从 `inbound.order.status` 取值；补充收货状态映射及需要时的最小业务操作 |
| FR-GIN-004 | API04 从实际 `stock.picking` / `stock.move.line` 取数；每次手动触发；分批语义待确认 | 明确按本订单自动扫描 `done` 且 `incoming` 的 Picking；项目侧按 Picking 区分 Event，V3.2 接受逐 Picking 请求仍需确认 |
| BR 6.1.1、6.1.5、6.1.6 | 区分收货确认与入库完成；只手动触发；未经列明不增加额外状态门禁 | API02 使用业务 `status`；API04 使用关联当前订单的 Done/Incoming Picking；不得扩展为额外状态审批 |
| 全局主动回传原则（需新增） | 当前 SRS 未明确区分业务事实维护与接口回传职责 | 适用于 API02/04/06/08/10：业务模块产生、维护业务事实；API 模块读取、转换、传输事实并记录回传结果；不得要求重复录入已有业务数据 |
| BR 6.1.3、NFR/异常追踪 | 业务操作与回传结果分别追踪；每次手动回传记录操作及结果 | 业务状态操作日志、Ginlong API Event 和 API Log 各自记录自身信息，不互相替代 |

### 2.2 TDD

| 当前 TDD 位置 | 当前设计 | 拟变更影响 |
|---|---|---|
| §2.2 / §3 API02 | API02 持久化收货明细子表，并将明细 Y/N 汇总为订单级值 | 停止 API02 读取/依赖子表，改读 `inbound.order.status`；拟映射 `planning→N`、`arrive/inbound→Y`，待核实 `arrive` 的业务含义和操作入口 |
| §2.2 / §3 API04 | API04 仅读取已选择的 Picking | 改为按本订单关系和指定完成/类型域自动读取 |
| §2.2 / §4.1 | 在 Picking 上持久化选择字段；API04/06 读取所选 Picking；move line 上另填操作人员和时间 | API04 不再使用选择字段；改用 Picking `date_done` 和可核实的实际确认人；不要求逐 SN 派生操作人/时间 |
| §3 / §4.1 / §11 | API04 批次范围及重复回传仍有 Open Item | 本地按 Picking 识别 Event；核实 V3.2 对同一订单多次按 Picking 回传是否接受，未明确时作为待锦浪确认项 |
| §2.2 / UI | 当前要求持久化 Notebook，并展示业务数据 | 调整为类似现有 Hoymiles APIs Tab 的按钮及只读结果状态/时间/错误，不复制其 HTTP 实现 |

### 2.3 Implementation Plan

当前计划 v2.1 以 SRS v1.3/TDD v1.6 为有效基线。若 Human Review 批准本 Draft，应先在新版本 SRS/TDD 中修订 API02/API04 设计及主动回传通用职责原则，再更新 Implementation Plan 的基线与阶段映射；不得覆盖现行冻结版本。上述上游文档批准并冻结后，才能冻结本 CC 和开始实施。

## 3. 范围

### 3.1 在范围内（拟议）

1. API02 从 `inbound.order.status` 生成 `receiptConfirmed`；拟映射 `planning→N`、`arrive/inbound→Y`。不读取 Picking、move line 或额外收货明细。`arrive` 含义及业务操作入口核实前，该映射仍为 Draft 建议。
2. 若现有 WMS 没有收货确认入口，允许增加最小业务操作：将订单 `status` 改为 `arrive`，并记录业务操作日志。API02 回传按钮只读取已保存状态，不改变订单状态。
3. 业务状态变化写入现有业务操作日志；API Event 记录幂等事件；API Log 逐次记录 HTTP 回传尝试与结果。三种记录各司其职，不相互替代。
4. API04 用户在入库 Order 上点击回传按钮后，系统自动搜索：
   - `stock.picking.inbound_order_id = 当前 inbound.order`
   - `stock.picking.state = done`
   - `stock.picking.picking_type_id.code = incoming`
5. 一个 Picking 是本地独立回传及 API Event 单位。自动扫描出的 Picking 中，已成功回传者跳过，失败者保留人工重试能力；每次实际 HTTP 尝试追加 API Log。不增加 Picking 选择、批次模型或协议字段。
6. API04 从该 Picking 的实际 `stock.move.line` 构造 Payload，不用 API01 预报数据。完成时间优先读 Picking `date_done`；操作人优先读该 Picking 实际入库确认人。现有代码未找到 Picking 实际确认人的专用字段，须先核实可用审计来源；不得用 Picking 负责人、订单确认人或回传用户替代。
7. 不新增逐 SN 操作人/时间业务要求。V3.2 若要求每条 `snList` 携带 `operator` 和 `operationTime`，使用经确认的 Picking 级实际确认人和 `date_done` 生成对应报文字段；若 Ginlong 要求逐 SN 独立值，列为外部待确认，不补造事实。
8. 入库单 Form 使用 Ginlong APIs Tab，分别提供 API02、API04 按钮及只读成功状态、回传时间、错误信息；优先从关联 API Log/Event 读取，不为回传结果另建业务模型或重复保存业务数据。
9. 复用现有业务模型、业务操作日志、`ginlong.api.idempotency`、`world.depot.api.log`、Endpoint 设置、认证/权限和标准 WMS 作业数据。
10. 增加 Odoo 自动化和组件集成测试作为 CC 验收；本 CC 不组织独立人工 HVR，关闭后返回原项目 API02/API04 人工 HVR。

### 3.2 范围外

- API06、API08、API10 的行为、视图或模型变更；本 Draft 第 10 节仅记录横向发现。
- Ginlong 回传协议字段、Action 或响应格式变更；不访问真实 Ginlong。
- Karl Rapp Gateway、XML/FTP/VPN、库存同步或库存处理改造。
- 新 API 日志框架、新幂等模型、通用集成平台、额外状态机或审批流。
- 删除历史 API Event、API Log、废弃收货明细历史或 Picking 数据；废弃模型/字段停止使用，但其历史数据保留。
- 对 API04 没有符合条件 Picking 的入库单执行自动回传、定时任务或后台重试。

### 3.3 非目标

- 不把 API02 收货确认解释为 API04 入库完成。
- 不以 `inbound.order.status = inbound` 自动推定“整单收货完成”；现有 WMS 在一个 incoming Picking 完成时即可将订单状态写成 `inbound`。
- 不将按钮点击用户、订单确认人、Picking 负责人或 Picking 创建者直接认定为 KR 实际作业人员。

## 4. 变更边界

### 4.1 拟允许修改（Human Review 批准并完成上游基线更新后）

| 路径 | 允许范围 |
|---|---|
| `mymodules/ginlong_apis/models/ginlong_callbacks.py` | API02 读取状态并生成 Payload；API04 自动搜索合格 Picking、按 Picking 组织 Payload/Event；回传反馈读取现有 Log/Event |
| `mymodules/ginlong_apis/views/ginlong_callback_views.xml` | 入库 Order 的 Ginlong APIs Tab、两项按钮及只读结果区；移除 API02 明细维护和 API04 Picking 勾选入口 |
| `mymodules/ginlong_apis/tests/test_ginlong_api.py` | API02/API04 HTTP/ORM/Event/Log/视图及回归用例 |
| `mymodules/ginlong_apis/data/idempotency_rules.json` | 配置/API04 若需使用现有幂等入口时，为每 Picking 建立稳定 Event 身份 |
| `mymodules/worlddepot/models/inbound_order.py`、`views/inbound_order.xml` | 若核实没有 `arrive` 操作，增加最小收货确认入口；更新 `status` 并用现有业务日志/chatter 记录，不改 `state` 生命周期 |
| `mymodules/worlddepot/models/my_stock.py` | 仅当确认现有 stock picking 审计中没有可用的实际确认人时，考虑在完成入库确认时最小记录 Picking 级确认人；不增加逐 SN 采集 |

不得修改禾麦 HTTP 代码、`worlddepot` 入库状态转换、库存核算或无关 API 路径。若实现发现需要修改，应暂停并提交范围/基线变更。

### 4.2 停用与保留边界

- `ginlong.inbound.receipt.detail` 及其字段：API02 停止读取/写入并移除对应业务维护入口；现存模型结构与历史行保留，本 CC 不做迁移或删除。项目完成后统一评估清理。
- `stock.picking.ginlong_callback_selected`、`stock.move.line.ginlong_operator_code` / `ginlong_operation_time`：API04 不再依赖其人工选择/补录；API06 仍依赖的共享字段及其现有入口必须保留，本 CC 不得删改 API06 所需能力。
- `ginlong.api.idempotency` 与 `world.depot.api.log`：保留全部既有行和字段，不重建、不清理。按钮区域只读展示最近一次相关 API Log 的结果、时间和错误；完整请求/响应仍在现有 API 日志中查看。

### 4.3 禁止

| 类型 | 禁止事项 |
|---|---|
| 协议/数据 | 不改变 Ginlong 字段、Action 或响应；不删除或迁移额外收货明细历史、幂等记录、API 日志、Picking、move line、Lot、Package 或库存 |
| 事实来源 | 不把订单确认人、Picking 负责人或回传用户冒充实际入库确认人；不为每个 SN 虚构不同的操作人/时间 |
| 业务 | 不新增订单状态门禁，不因没有 Picking 改变 inbound.order 状态，不自动发送或自动重试 |
| 范围 | 不修改 API06/API08/API10，不改变 API02/API04 之外的 Ginlong 行为 |
| 环境 | 不调用真实 Ginlong API，不访问生产环境，不做 Git 提交/推送 |

## 5. 必需行为变更（拟议）

| ID | 当前行为 | 拟议期望 | 追溯 |
|---|---|---|---|
| CC-CHANGE-001 | API02 读取额外收货明细状态；`status=arrive` 当前未发现写入入口 | 读取业务 `status`；拟映射 `planning→N`、`arrive/inbound→Y`；如确认无操作入口，最小增加设为 `arrive` 的业务操作并记录业务日志 | SRS FR-GIN-002（须修订）；TDD §2.2 / §3（须修订） |
| CC-CHANGE-002 | API04 要用户选择关联 Picking；当前查询未自动限定 Done/Incoming | 自动筛选当前订单关联且 `state=done`、`picking_type_id.code=incoming` 的 Picking，并读实际 move line | SRS FR-GIN-004（须修订）；TDD §2.2 / §4.1（须修订） |
| CC-CHANGE-003 | API04 用订单级 Event 与整份 Payload 指纹；同订单新增作业时可能把成功批次重复带入 | 本地以 Picking 为独立 Event 单位；成功 Picking 跳过，失败 Picking 允许人工重试，不建批次模型 | TDD §3 / §4.1（须修订）；V3.2 逐 Picking 调用支持情况列为锦浪 Open Item |
| CC-CHANGE-004 | API04 的操作人员/时间来自 move line 人工补录字段 | 先读取 Picking `date_done` 和可核实的实际确认人；不要求逐 SN 维护不同操作人/时间；若实际确认人没有稳定记录，评估 Picking 级最小记录 | TDD §2.2 / §4.1（须修订）；按 V3.2 `snList` 必填结构验证 |
| CC-CHANGE-005 | 入库页面有 API02 明细编辑、API04 Picking 勾选入口；无统一只读回传反馈 | 采用 Ginlong APIs Tab；显示按钮和现有 API Log/Event 对应的只读最近结果/时间/错误；业务操作日志与 API 事件、日志分别记录 | SRS FR-GIN-002/004 及通用主动回传原则（须修订）；TDD UI 设计（须修订） |
| CC-CHANGE-006 | 旧 API02 模型仍被代码/UI使用 | API02 停止使用旧收货明细模型/字段，移除其维护入口，保留历史行和 API06 使用的共享字段；项目完成后再统一评估物理清理 | TDD §2.2（须修订）；历史数据不迁移、不删除 |

## 6. 既有行为保留

| ID | 保留内容 | 原因 |
|---|---|---|
| CC-PRESERVE-001 | API02/04 仍是用户手动按钮触发；同步 POST JSON；使用配置 Endpoint | SRS 与现有 API 约定 |
| CC-PRESERVE-002 | API02 收货确认与 API04 实际入库完成是不同事件 | SRS BR 6.1.1；不得相互推断 |
| CC-PRESERVE-003 | API04 只以关联当前订单的实际 Picking/move line 生成作业数据，不读 API01 预报数据 | SRS FR-GIN-004、TDD §4.1 |
| CC-PRESERVE-004 | 业务状态操作日志、API Event、API Log 各自保留并分别表达业务动作、幂等事件、HTTP 尝试/结果 | 复用现有三类记录机制，不互相替代 |
| CC-PRESERVE-005 | API04 字段遵循 V3.2；使用已核实的 Picking 级作业人员/时间，不用回传点击信息伪装现场事实 | Ginlong API04 契约及本次确认边界 |
| CC-PRESERVE-006 | API06 继续使用其所需的 `ginlong_callback_selected`、操作人员/时间等共享能力及现有重量/托盘行为 | 本 CC 不改 API06 |

## 7. 已确认事项与剩余待决事项

### 7.1 本次 Human Review 已确认的设计方向

| ID | 已确认事项 | 执行边界 |
|---|---|---|
| DEC-01 | API02 用 `inbound.order.status`，不使用订单生命周期 `state`；拟议映射为 `planning→N`、`arrive/inbound→Y` | `arrive` 语义和操作入口须先核实；确认无入口时允许最小增加状态操作并记录业务日志 |
| DEC-02 | API04 自动扫描当前订单关联的 Done/Incoming Picking；本地按 Picking 独立组织回传 Event | 成功 Picking 不重复发送；失败 Picking 可人工重试；V3.2 外部逐 Picking 支持仍需确认 |
| DEC-03 | API04 优先用 Picking 实际入库确认人和 `date_done`，不增加逐 SN 操作人/时间要求 | 如现有记录没有实际确认人，核实可用审计来源；必要时只在 Picking 级记录一次，不从无关用户字段推导 |
| DEC-04 | 停止使用 API02 额外收货明细模型/字段并移除维护入口 | 保留历史数据；API06 仍依赖的共享字段继续保留；项目完成后统一评估清理 |
| DEC-05 | UI 采用 Ginlong APIs Tab；业务操作日志、API Event、API Log 分别记录 | 每个接口提供按钮和只读成功状态、回传时间、错误信息；不重复维护已有业务事实 |
| DEC-06 | API06/API08/API10 只保留横向审查，不扩展本 CC | 不修改其行为、模型、界面或业务测试范围 |

### 7.2 剩余 Open Items

| OI | 当前证据 | 最小处理建议 | 需确认内容 / 影响 |
|---|---|---|---|
| OI-01 `arrive` 的业务含义及操作入口 | `status` 有 `planning/arrive/inbound` 三个值；静态检索仅发现枚举声明和 `inbound` 写入，未发现将订单置为 `arrive` 的操作。`inbound` 由 incoming Picking 完成流程写入 | 业务确认 `arrive` 表示收货确认；没有入口时增加最小状态操作，并以现有 tracking/chatter 作为业务操作记录 | 请确认 `planning→N`、`arrive/inbound→Y` 是否为最终 API02 映射，以及新增/现有操作的业务名称和触发时机。未确认前不冻结 API02 映射 |
| OI-02 V3.2 是否接受 API04 逐 Picking 调用 | V3.2 说明目标系统支持部分过账，但触发说明又写“整单确认上架完成时调用”；两段对发送方调用粒度并不一致 | 保留项目本地每 Picking 一个 Event、成功跳过、失败人工重试的设计；向锦浪确认同一 `inboundOrderNo` 是否可多次发送不同 Picking 的 `CREATE` 数据 | 真实接口调用须在锦浪确认后进行；本地 Mock 自动化可按项目侧 per-Picking 规则验收。该 Open Item 不把模拟结果描述为外部联调通过 |
| OI-03 Picking 实际确认人的可核实来源 | WorldDepot 定制 `stock.picking` 有订单关联及 `date_done` 流程，未找到专用的 Picking 确认人字段；`inbound.order.confirm_user_id` 是订单确认人，不等同于 Picking 确认人 | 优先检查现有 Picking chatter/审计是否可靠记录实际验证用户；若无，考虑在实际 `button_validate()` 成功后最小记录 Picking 级验证用户。`date_done` 取实际完成时间 | 实施前确认审计来源是否可靠，以及 V3.2 每条 `snList` 所需字段可否使用同一 Picking 级人员/时间；不得按 SN 虚构不同人员/时间 |

## 8. 测试契约（实施阶段拟执行；当前均未运行）

| 测试 ID | 测试行为 | 类型 | 预期断言 |
|---|---|---|---|
| CC-TEST-084 | API02 状态与 Payload 映射 | Odoo ORM 集成 | 按最终批准映射验证 `planning→N`、`arrive/inbound→Y`；API02 不查询 Picking、move line 或收货明细子表 |
| CC-TEST-085 | API02 无作业单时发送 | HTTP 组件集成 | 即使没有 Picking/额外收货明细，仅凭已保存订单状态也能从真实按钮调用 Mock；断言 POST、响应、Event 与 API Log |
| CC-TEST-086 | API02 收货状态操作和业务审计 | ORM/业务组件集成 | 若新增 `arrive` 操作，验证其只改业务 `status`、业务操作日志记录操作者/时间；回传只读状态且不再改变业务状态；生命周期 `state` 不变 |
| CC-TEST-087 | API02 重复点击及状态变化 | HTTP/幂等集成 | 按冻结幂等规则核对重复点击的实际 HTTP 行为、Event 复用和每次 API Log；状态变化按批准映射生成正确 Payload，不把缓存响应冒充实际 POST |
| CC-TEST-088 | API04 Picking 自动筛选 | ORM 集成 | 构造当前订单 incoming/done、incoming 非 done、outgoing/done、其他订单 incoming/done；Payload 只包含第一类 |
| CC-TEST-089 | API04 读取实际作业记录 | Mock HTTP/ORM 集成 | 产品/SN/数量/托盘来自实际 move line；`operationTime` 来自 Picking `date_done`；`operator` 来自经确认的 Picking 实际确认人；不读 API01 预报，不要求逐 SN 补录 |
| CC-TEST-090 | API04 每 Picking Event、防重及重试 | HTTP/Event 集成 | 一个 Picking 对应稳定 Event；成功 Picking 在后续点击跳过；另一个 Done Picking 可单独发送；失败 Picking 可人工重试；不重复旧批次数据 |
| CC-TEST-091 | API04 不合格 Picking 排除 | HTTP/ORM 集成 | 不符合订单、state、picking type 任一筛选条件的 Picking 不进入 Payload；若无合格作业，发送被阻止并留下清晰 Log，不更改 WMS 状态/库存 |
| CC-TEST-092 | 回传失败后重试 | Mock HTTP/ORM 集成 | 首次 Mock 失败；修正已确认的数据源后人工再点击；旧 Log 保持不变，新 Log 追加；无后台重试 |
| CC-TEST-093 | Ginlong APIs Tab 只读反馈 | Odoo 浏览器/ORM 集成 | 两个接口分别显示按钮及最近成功、时间、错误；结果由当前 API Log/Event 读取；业务用户不能编辑/清除日志或 Event |
| CC-TEST-094 | 停用旧 API02 明细且保留共享字段 | ORM/View 回归 | API02 不再读写旧收货明细，维护入口移除且历史行仍存在；API06 仍能使用其共享 Picking/Move Line 字段，不改变 API06 行为 |

所有测试须通过真实 Odoo 按钮/业务入口和 Mock HTTP 接收端，断言响应、Payload、ORM 状态、业务操作日志、Event、API Log 与必要副作用。静态检查不能作为 PASS。只运行与本次共享路径直接相关的既有回归；API06/API08/API10 不增加本 CC 的业务功能验收。外部 per-Picking 契约未确认时，可完成本地 Mock 验证，但不得标记真实 Ginlong 联调通过。实际状态只能在 IHR/ATR 中按执行证据记录。

## 9. 人工 HVR 安排

CC-GIN-009 不设独立人工 HVR，也不以人工 HVR 作为关闭条件。自动化和组件集成验收完成、CC 关闭后，返回原项目 API02/API04 HVR 安排，由项目负责人按原流程进行人工验证。API04 的真实 Ginlong 请求须等待 OI-02 的逐 Picking 协议确认；本地 Mock 结果不能代替该确认或真实联调。

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
| Ginlong V3.2 | `docs/ginlong_apis/海外WMS与第三方系统集成V3.2.xlsx`，工作表“海外WMS与第三方系统的接口与处理逻辑”，API02 第 21–23 行、API04 第 24–32 行 | API02 的 `receiptConfirmed` 为订单级字段；API04 `snList` 含产品、数量、托盘、操作人和操作时间字段。API04 一处说明支持部分过账，触发说明又要求整单确认后调用，逐 Picking 发送仍需锦浪确认 |
| 冻结需求 | `docs/requirement/SRS_ginlong_apis-v1.3.md`，BR 6.1、FR-GIN-002/004、异常追踪 | 收货确认与入库完成分离；回传由用户手动触发；API04 数据来自实际 Picking；批次/重复语义留待决 |
| 冻结设计 | `docs/ginlong_apis/TDD-v1.6.md`，§2.2、§3、§4.1、§11 | 现有设计包含 API02 收货明细、API04 Picking 手选、move line 操作人/时间字段及批次 Open Item |
| 当前计划 | `docs/implementation/IMPLEMENTATION_PLAN_ginlong_apis-v2.1.md`，阶段 4B/CC-GIN-007 与当前基线表 | 当前批准基线指向 SRS v1.3/TDD v1.6；本 Draft 不覆盖该冻结计划 |
| Odoo 入库单 | `mymodules/worlddepot/models/inbound_order.py`，`state`、`status`、`action_confirm()` | `status` 是只读选择字段 `planning/arrive/inbound`；静态检索未发现将其写为 `arrive` 的操作。`action_confirm()` 写入的是生命周期 `state=confirm`，不是 `status=arrive` |
| Picking 状态与时间 | `mymodules/worlddepot/models/my_stock.py`，`button_validate()`、`_update_inbound_order_status()` | incoming Picking 完成后，订单 `status` 可写为 `inbound`，`i_date` 来自 `picking.date_done`；定制代码未发现专用 Picking 实际确认人字段 |
| Ginlong 回传当前实现 | `mymodules/ginlong_apis/models/ginlong_callbacks.py`，`_api02_payload()`、`_api04_payload()`、`_write_api_log()`、`send_callback()` | API02 读收货明细；API04 读手选 Picking 与 move lines；现有日志关联来源业务单，手动点击追加 API Log |
| 当前页面 | `mymodules/ginlong_apis/views/ginlong_callback_views.xml` | 当前入库单回传页提供 API02 明细和 API04 Picking 选择控件 |
| 禾麦页面参考 | `mymodules/worlddepot/views/inbound_order.xml` §“Hoymiles APIs”；`mymodules/worlddepot/models/inbound_order_status.py` | 已有分组按钮及只读成功标志、时间、错误信息布局；只借鉴交互布局，不复用其 HTTP 发送实现 |

## 11. 实施停止条件

1. `arrive` 的业务含义、操作入口或状态映射未确认：停止 API02 状态转换/回传语义实施；不把生命周期 `state` 作为替代。
2. API04 若需对真实 Ginlong 发送而 OI-02 未确认：只允许 Mock 本地验收，不得声称协议联调通过或发送真实请求。
3. Picking 实际确认人的来源未核实：停止声称 API04 Payload 完整；不得用订单确认人、负责人或回传用户填充。
4. SRS/TDD/Implementation Plan 尚未完成获批修订与冻结：本 CC 维持 Draft，不得开始编码。
5. 若改动会破坏 API06 仍依赖的共享字段/入口，或影响无关 WMS 流程：停止并重新评估范围。
6. 旧 API02 模型/字段和历史行只停用、不物理删除；如发现删除必要，留待项目结束后的统一清理评估，不扩大本 CC。

## 12. 完成定义（拟议）

- API02 状态含义、`arrive` 操作入口及映射已确认；SRS/TDD/Implementation Plan 修订完成、获批并建立新基线。
- API02 的 Odoo 自动化和组件集成测试通过：从 `status` 生成 Payload，不读 Picking/move line/额外明细；业务操作日志、Event、API Log 分别可追溯。
- API04 的 Odoo 自动化和组件集成测试通过：按关联订单、Done、Incoming 自动扫描；每 Picking Event 独立；成功跳过、失败可人工重试；Payload 使用实际 Picking/move line 数据。
- 操作人来源经过核实，时间取 `date_done`；若需最小 Picking 级确认人记录，其自动化验证通过。
- Ginlong APIs Tab 的两个按钮及只读成功状态、回传时间、错误信息通过组件/浏览器自动化验证；旧收货明细维护入口移除且历史数据保留，API06 共享能力未破坏。
- 必要的自动化和组件集成测试全部通过，并更新 IHR/ATR。**不要求独立人工 HVR**；真实 API04 逐 Picking 契约 Open Item 不伪记为已获 Ginlong 确认。
- 满足上述自动化验收并经 Human Review 后可关闭 CC；关闭后再继续原项目 API02/API04 人工 HVR，真实 Ginlong 调用仍遵守外部协议确认要求。

## 13. 评审状态与版本记录

| 版本 | 日期 | 状态 | 说明 |
|---|---|---|---|
| v0.1 | 2026-11-24 | **Draft** | 根据 API02/API04 业务设计审查起草；列出状态映射、批次和人员/时间 Open Items；不改代码、不改上游冻结文档、不执行测试/HVR，等待 Human Review。 |
| v0.2 | 2026-11-24 | **Draft — 待 Human Review** | 按有条件通过意见调整：API02 使用 `status` 和建议映射；API04 每 Picking Event、成功跳过/失败重试、优先 Picking 实际确认人及 `date_done`；旧模型停用但保留历史；加入主动回传通用职责原则；CC 只以自动化/组件集成测试验收，不设独立 HVR。原 v0.1 保留。 |

| 评审项 | 当前状态 |
|---|---|
| Human Review | v0.2 Pending |
| 实施授权 | 未授权 |
| 代码/测试/HVR/Git | 本轮均未执行；本 CC 不设独立 HVR |
| 模板同步 | BLOCKED；沿用已批准例外，不记为 PASS |

