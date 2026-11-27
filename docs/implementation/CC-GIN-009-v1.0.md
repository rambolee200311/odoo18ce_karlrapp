# CC-GIN-009 v1.0 Frozen — Inbound Callback Business Alignment

| 字段 | 值 |
|---|---|
| 文档编号 | CC-GIN-009 |
| 文档状态 | **v1.0 Frozen with Open Items — Human Review APPROVED** |
| 模块 | `ginlong_apis`；仅按需读取/扩展既有 `worlddepot` 与 Odoo `stock` 记录 |
| 工作类型 | 回传行为调整、表单界面调整、集成变更 |
| 目标 | API02 从 `inbound.order.status` 生成收货确认；API04 自动扫描当前订单关联的 Done/Incoming Picking，并以 Picking 为本地回传事件单位；用既有 Ginlong Event/API Log 展示回传结果。 |
| 当前冻结上游 | [SRS v1.6](../requirement/SRS_ginlong_apis-v1.6.md)、[TDD v1.9](../ginlong_apis/TDD-v1.9.md)、[Implementation Plan v2.4](IMPLEMENTATION_PLAN_ginlong_apis-v2.4.md) |
| 上游有效性 | **VALID — Human Review 已批准必要上游修订并冻结** |
| 模板同步 | **BLOCKED**：项目模板来源缺失；沿用项目已批准的模板同步例外，不伪记 PASS |
| 授权状态 | **已授权本地实施、模块升级及 Odoo 自动化/Mock 组件集成测试；不授权真实 Ginlong或生产环境访问；不组织独立 HVR** |

## 1. 变更概述

当前 API02 依赖 `ginlong.inbound.receipt.detail` 和逐行 `receipt_status`；API04 依赖用户在 Notebook 中勾选 `stock.picking.ginlong_callback_selected`。本 CC 改为从 `inbound.order.status` 生成 API02 Payload，并让 API04 自动发现符合条件的实际 Picking。两个接口分别在 Ginlong APIs Tab 提供回传按钮和只读结果。

本冻结契约记录已批准的 API02/API04 业务来源、实现边界和验收标准。v0.1/v0.2 仅作为评审历史；本版本 v1.0 是当前 CC 实施依据。

## 2. 上游基线与追溯

### 2.1 SRS

| SRS ID | 当前条款 | 与本 CC 的关系 |
|---|---|---|
| FR-GIN-002 | 用户手动点击 API02；按现有业务服务和确认字段生成 Payload；记录操作人、时间、Payload/关联信息及结果 | 改为从 `inbound.order.status` 取值；补充收货状态映射及需要时的最小业务操作 |
| FR-GIN-004 | API04 从实际 `stock.picking` / `stock.move.line` 取数；每次手动触发；分批语义待确认 | 明确按本订单自动扫描 `done` 且 `incoming` 的 Picking；项目侧按 Picking 区分 Event，V3.2 接受逐 Picking 请求仍需确认 |
| BR 6.1.1、6.1.5、6.1.6 | 区分收货确认与入库完成；只手动触发；未经列明不增加额外状态门禁 | API02 使用业务 `status`；API04 使用关联当前订单的 Done/Incoming Picking；不得扩展为额外状态审批 |
| 全局主动回传原则 | SRS v1.4 已明确区分业务事实维护与接口回传职责 | 适用于 API02/04/06/08/10：业务模块产生、维护业务事实；API 模块读取、转换、传输事实并记录回传结果；不得要求重复录入已有业务数据 |
| BR 6.1.3、NFR/异常追踪 | 业务操作与回传结果分别追踪；每次手动回传记录操作及结果 | 业务状态操作日志、Ginlong API Event 和 API Log 各自记录自身信息，不互相替代 |

### 2.2 TDD

| 当前 TDD 位置 | v1.6 历史设计 | v1.7 冻结后的设计 |
|---|---|---|
| §2.2 / §3 API02 | API02 依赖持久化收货明细子表 | 停止读取该子表，改读 `inbound.order.status`；固定映射及收货确认入口见 v1.7 §13.1 |
| §2.2 / §3 API04 | API04 仅读取用户选择的 Picking | 自动按当前订单、Done、Incoming 条件搜索；每 Picking 独立 Event，成功跳过、失败人工重试 |
| §2.2 / §4.1 | Picking 选择字段及 move line 逐行操作人/时间由回传表单维护 | API04 不使用手选字段；操作时间取 Picking `date_done`，实际确认人取 Picking 级可靠记录；不逐 SN 补录 |
| §3 / §4.1 / §11 | 分批协议待决 | 本地按 Picking 组织 Mock Event；Ginlong 是否接受同订单多次 `CREATE` 留外部联调，不阻塞本地验收 |
| §2.2 / UI | API02 明细维护、API04 Picking 选择及结果显示 | 保留 Ginlong APIs Tab 的手动按钮和只读状态/时间/错误；复用现有 HTTP、Event、Log |

### 2.3 Implementation Plan

Implementation Plan v2.3 将阶段 4D 基线指向 SRS v1.5、TDD v1.8 和本 CC v1.0；v2.1/v2.2 历史文件保留，不覆盖。

## 3. 范围

### 3.1 在范围内

1. API02 从 `inbound.order.status` 生成 `receiptConfirmed`，固定映射 `planning→N`、`arrive/inbound→Y`。不读取 Picking、move line 或额外收货明细。收货确认操作只将 `status` 设为 `arrive`，不得改变订单生命周期 `state`。
2. 提供最小收货确认操作：将订单业务 `status` 写为 `arrive`，并通过现有字段跟踪/业务操作日志记录。API02 回传按钮只读取已保存状态，不改变订单状态。此操作不修改订单生命周期 `state`。
3. 业务状态变化写入现有业务操作日志；API Event 记录幂等事件；API Log 逐次记录 HTTP 回传尝试与结果。三种记录各司其职，不相互替代。
4. API04 用户在入库 Order 上点击回传按钮后，系统自动搜索：
   - `stock.picking.inbound_order_id = 当前 inbound.order`
   - `stock.picking.state = done`
   - `stock.picking.picking_type_id.code = incoming`
5. 一个 Picking 是本地独立回传及 API Event 单位。自动扫描出的 Picking 中，已成功回传者跳过，失败者保留人工重试能力；每次实际 HTTP 尝试追加 API Log。不增加 Picking 选择、批次模型或协议字段。
6. API04 从该 Picking 的实际 `stock.move.line` 构造 Payload，不用 API01 预报数据。操作时间取 Picking `date_done`；已批准在标准实际入库完成时记录 Picking 级实际确认人，并由该 Picking 的各 SN 行使用同一 Picking 确认人/完成时间。不得使用 Picking 负责人、订单确认人或回传按钮点击人代替。
7. 不新增逐 SN 操作人/时间业务要求。V3.2 若要求每条 `snList` 携带 `operator` 和 `operationTime`，使用经确认的 Picking 级实际确认人和 `date_done` 生成对应报文字段；若 Ginlong 要求逐 SN 独立值，列为外部待确认，不补造事实。
8. 入库单 Form 使用 Ginlong APIs Tab，分别提供 API02、API04 按钮及只读成功状态、回传时间、错误信息；优先从关联 API Log/Event 读取，不为回传结果另建业务模型或重复保存业务数据。
9. 复用现有业务模型、业务操作日志、`ginlong.api.idempotency`、`world.depot.api.log`、Endpoint 设置、认证/权限和标准 WMS 作业数据。
10. 增加 Odoo 自动化和组件集成测试作为 CC 验收；本 CC 不组织独立人工 HVR，关闭后返回原项目 API02/API04 人工 HVR。

### 3.2 范围外

- API06、API08、API10 的行为、视图或模型变更；本 CC 第 10 节仅记录横向发现。
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

### 4.1 已批准的修改范围

| 路径 | 允许范围 |
|---|---|
| `mymodules/ginlong_apis/models/ginlong_callbacks.py` | API02 读取状态并生成 Payload；API04 自动搜索合格 Picking、按 Picking 组织 Payload/Event；回传反馈读取现有 Log/Event |
| `mymodules/ginlong_apis/views/ginlong_callback_views.xml` | 入库 Order 的 Ginlong APIs Tab、两项按钮及只读结果区；移除 API02 明细维护和 API04 Picking 勾选入口 |
| `mymodules/ginlong_apis/tests/test_ginlong_api.py` | API02/API04 HTTP/ORM/Event/Log/视图及回归用例 |
| `mymodules/ginlong_apis/data/idempotency_rules.json` | 配置/API04 若需使用现有幂等入口时，为每 Picking 建立稳定 Event 身份 |
| `mymodules/worlddepot/models/inbound_order.py`、`views/inbound_order.xml` | 增加最小收货确认入口；只更新 `status=arrive`，由字段跟踪/chatter 记录，不改 `state` 生命周期 |
| `mymodules/ginlong_apis/models/ginlong_callbacks.py`（`StockPicking.button_validate` 扩展） | 若无可靠既有来源，在标准实际入库完成后记录当前实际确认用户到 Picking 级字段；不增加逐 SN 采集 |

不得修改禾麦 HTTP 代码、入库单生命周期 `state` 转换、库存核算或无关 API 路径。允许的 `status=arrive` 收货确认操作只改变业务状态字段，不改变订单生命周期状态；该最小扩展已由 Human Review 明确批准。

### 4.2 停用与保留边界

- `ginlong.inbound.receipt.detail` 及其字段：API02 停止读取/写入并移除对应业务维护入口；现存模型结构与历史行保留，本 CC 不做迁移或删除。项目完成后统一评估清理。
- `stock.picking.ginlong_callback_selected`、`stock.move.line.ginlong_operator_code` / `ginlong_operation_time`：API04 不再依赖其人工选择/补录；API06 仍依赖的共享字段及其现有入口必须保留，本 CC 不得删改 API06 所需能力。
- `ginlong.api.idempotency` 与 `world.depot.api.log`：保留全部既有行和字段，不重建、不清理。按钮区域只读展示最近一次相关 API Log 的结果、时间和错误；完整请求/响应仍在现有 API 日志中查看。

### 4.3 禁止

| 类型 | 禁止事项 |
|---|---|
| 协议/数据 | 不改变 Ginlong 字段、Action 或响应；不删除或迁移额外收货明细历史、幂等记录、API 日志、Picking、move line、Lot、Package 或库存 |
| 事实来源 | 不把订单确认人、Picking 负责人或回传用户冒充实际入库确认人；不为每个 SN 虚构不同的操作人/时间 |
| 业务 | 不改变入库单生命周期 `state` 转换；API02 收货确认仅按批准操作写 `status=arrive`；不新增其他订单状态门禁，不因没有 Picking 改变 inbound.order 状态，不自动发送或自动重试 |
| 范围 | 不修改 API06/API08/API10，不改变 API02/API04 之外的 Ginlong 行为 |
| 环境 | 不调用真实 Ginlong API，不访问生产环境，不做 Git 提交/推送 |

## 5. 必需行为变更（冻结）

| ID | 原行为 | 冻结后的实现要求 | 追溯 |
|---|---|---|---|
| CC-CHANGE-001 | API02 读取额外收货明细状态 | API02 读取订单 `status`；固定映射 `planning→N`、`arrive/inbound→Y`；收货确认入口只写 `status=arrive` 并记录操作日志，不改生命周期 `state` | SRS FR-GIN-002；TDD v1.7 §13.1 |
| CC-CHANGE-002 | API04 要用户选择关联 Picking；当前查询未自动限定 Done/Incoming | 自动筛选当前订单关联且 `state=done`、`picking_type_id.code=incoming` 的 Picking，并读实际 move line | SRS v1.4 FR-GIN-004；TDD v1.7 §3/§4.1 |
| CC-CHANGE-003 | API04 用订单级 Event 与整份 Payload 指纹；同订单新增作业时可能把成功批次重复带入 | 本地以 Picking 为独立 Event 单位；成功 Picking 跳过，失败 Picking 允许人工重试，不建批次模型 | TDD v1.7 §3/§4.1；V3.2 逐 Picking 调用支持情况列为 Ginlong Open Item |
| CC-CHANGE-004 | API04 的操作人员/时间来自 move line 人工补录字段 | 操作时间取 Picking `date_done`；优先复用可靠实际确认人记录；缺少时在 Picking 实际完成时记录 Picking 级确认人；不要求逐 SN 人工维护 | TDD v1.7 §13.2 |
| CC-CHANGE-005 | 入库页面有 API02 明细编辑、API04 Picking 勾选入口；无统一只读回传反馈 | 采用 Ginlong APIs Tab；显示按钮和现有 API Log/Event 对应的只读最近结果/时间/错误；业务操作日志与 API 事件、日志分别记录 | SRS v1.4 FR-GIN-002/004；TDD v1.7 §13.3 |
| CC-CHANGE-006 | 旧 API02 模型仍被代码/UI使用 | API02 停止使用旧收货明细模型/字段，移除其维护入口，保留历史行和 API06 使用的共享字段；项目完成后再统一评估物理清理 | TDD v1.7 §13.1；历史数据不迁移、不删除 |

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

### 7.1 Human Review 已批准并冻结的事项

| ID | 批准决定 | 冻结要求 |
|---|---|---|
| DEC-01 / OI-01 | API02 使用既有 `inbound.order.status`；映射 `planning→N`、`arrive/inbound→Y`。如无现成收货确认操作，增加最小操作及业务操作记录 | 不改订单生命周期 `state`；API02 不依赖 Picking、move line 或收货明细子表 |
| DEC-02 / OI-02 | API04 自动扫描当前订单关联 Done/Incoming Picking；每 Picking 独立 Event；成功跳过、失败由用户手动重试 | 外部 Ginlong 分批协议未确认，但不阻塞本地 Mock；真实调用仍待阶段 5 |
| DEC-03 / OI-03 | API04 优先使用真实入库确认人；若现有来源不可靠，在实际入库完成时最小记录 Picking 级确认人；时间取 `date_done` | 不增加逐 SN 人工维护要求；不以订单确认人、assigned user 或回传用户冒充实际作业人 |
| DEC-04 | 停用旧 API02 收货明细维护与读取，移除 UI 入口；保留模型结构、历史行及 API06 依赖的共享字段 | 不清理历史数据，不扩大功能范围 |
| DEC-05 | API02/API04 显示手动按钮和只读成功状态、回传时间、错误信息 | 业务操作日志、Ginlong Event、API Log 分别保留职责 |
| DEC-06 | API06/API08/API10 横向检查只记录在案 | 不进入本 CC 实施范围 |

### 7.2 Open Items

| ID | 内容 | 处置 | 是否阻塞 |
|---|---|---|---|
| OI-02-EXT | Ginlong 是否接受同一 `inboundOrderNo` 下按 Picking 多次发送 `CREATE` | 本地按已批准每 Picking Event 实现并使用 Mock 验证；真实 Ginlong 确认留最终外部联调 | 不阻塞 CC-009 本地开发/测试；阻塞真实 API04 联调 |
| TEMPLATE | 模板同步 | 模板源缺失；沿用既有批准流程例外 | 记录 BLOCKED，不影响本 CC 冻结/实施 |

## 8. 自动化验收契约

| 测试 ID | 测试行为 | 类型 | 预期断言 |
|---|---|---|---|
| CC-TEST-084 | API02 状态与 Payload 映射 | Odoo ORM 集成 | 按最终批准映射验证 `planning→N`、`arrive/inbound→Y`；API02 不查询 Picking、move line 或收货明细子表 |
| CC-TEST-085 | API02 无作业单时发送 | HTTP 组件集成 | 即使没有 Picking/额外收货明细，仅凭已保存订单状态也能从真实按钮调用 Mock；断言 POST、响应、Event 与 API Log |
| CC-TEST-086 | API02 收货状态操作和业务审计 | ORM/业务组件集成 | 验证收货确认操作只改业务 `status=arrive`、由现有 tracking/chatter 记录操作；生命周期 `state` 不变；回传只读状态 |
| CC-TEST-087 | API02 重复点击及状态变化 | HTTP/幂等集成 | 按冻结幂等规则核对重复点击的实际 HTTP 行为、Event 复用和每次 API Log；状态变化按批准映射生成正确 Payload，不把缓存响应冒充实际 POST |
| CC-TEST-088 | API04 Picking 自动筛选 | ORM 集成 | 构造当前订单 incoming/done、incoming 非 done、outgoing/done、其他订单 incoming/done；Payload 只包含第一类 |
| CC-TEST-089 | API04 读取实际作业记录 | Mock HTTP/ORM 集成 | 产品/SN/数量/托盘来自实际 move line；`operationTime` 来自 Picking `date_done`；`operator` 来自 Picking 级实际确认人；不读 API01 预报，不要求逐 SN 补录 |
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
| 初始审查需求（历史） | `docs/requirement/SRS_ginlong_apis-v1.3.md`；当前有效需求见 SRS v1.6 FR-GIN-002/004 | 收货确认与入库完成分离；状态映射及每 Picking 实施详见当前基线 |
| 初始审查设计（历史） | TDD v1.6/v1.7 历史条款；当前设计见 TDD v1.9 §13 | 旧明细/手选方案已由批准的 CC-009 实施设计取代 |
| 初始审查计划（历史） | Implementation Plan v2.1/v2.2；当前执行计划见 v2.4 | 本 CC 冻结并实施时使用 SRS v1.6/TDD v1.9 |
| Odoo 入库单 | `mymodules/worlddepot/models/inbound_order.py`，`state`、`status`、`action_confirm()` | `status` 是只读选择字段 `planning/arrive/inbound`；静态检索未发现将其写为 `arrive` 的操作。`action_confirm()` 写入的是生命周期 `state=confirm`，不是 `status=arrive` |
| Picking 状态与时间 | `mymodules/worlddepot/models/my_stock.py`，`button_validate()`、`_update_inbound_order_status()` | incoming Picking 完成后，订单 `status` 可写为 `inbound`，`i_date` 来自 `picking.date_done`；定制代码未发现专用 Picking 实际确认人字段 |
| Ginlong 回传当前实现 | `mymodules/ginlong_apis/models/ginlong_callbacks.py`，`_api02_payload()`、`_api04_payload()`、`_write_api_log()`、`send_callback()` | API02 读收货明细；API04 读手选 Picking 与 move lines；现有日志关联来源业务单，手动点击追加 API Log |
| 当前页面 | `mymodules/ginlong_apis/views/ginlong_callback_views.xml` | 当前入库单回传页提供 API02 明细和 API04 Picking 选择控件 |
| 禾麦页面参考 | `mymodules/worlddepot/views/inbound_order.xml` §“Hoymiles APIs”；`mymodules/worlddepot/models/inbound_order_status.py` | 已有分组按钮及只读成功标志、时间、错误信息布局；只借鉴交互布局，不复用其 HTTP 发送实现 |

## 11. 实施停止条件

1. API02 固定使用本 CC 批准的 `status` 映射；实现不得改写生命周期 `state`。
2. API04 若需对真实 Ginlong 发送而 OI-02 未确认：只允许 Mock 本地验收，不得声称协议联调通过或发送真实请求。
3. API04 必须使用可靠实际确认人来源；若既有来源不存在，则按本 CC 记录 Picking 级实际确认人，不得改用订单确认人、负责人或回传按钮用户。
4. 不得访问真实 Ginlong/生产环境；逐 Picking 外部协议确认继续留最终联调。
5. 若改动会破坏 API06 仍依赖的共享字段/入口，或影响无关 WMS 流程：停止并重新评估范围。
6. 旧 API02 模型/字段和历史行只停用、不物理删除；如发现删除必要，留待项目结束后的统一清理评估，不扩大本 CC。

## 12. 完成定义

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
| v0.2 | 2026-11-24 | **Review Draft — 历史版本** | 按评审意见调整 API02 状态来源、API04 每 Picking Event、旧模型停用但留存、主动回传原则和自动化验收边界。原稿保留为评审历史。 |
| v1.0 | 2026-11-24 | **Frozen with Open Items — Human Review APPROVED**；实施授权已给出 | 批准 `planning→N`、`arrive/inbound→Y`；批准 Picking 级实际确认人最小扩展条件；批准每 Picking Event、成功跳过与失败人工重试；修正 §4.1/§4.3 生命周期边界冲突。授权本地实施、模块升级和自动化/Mock 测试。 |

| 评审项 | 当前状态 |
|---|---|
| Human Review | v1.0 APPROVED；项目负责人李建强；2026-11-24 |
| 实施授权 | 已授权（本地开发、模块升级及 Odoo 自动化/Mock HTTP） |
| 独立人工 HVR | N/A（本 CC）；关闭后返回原项目 API02/API04 人工 HVR |
| 模板同步 | BLOCKED；沿用已批准例外，不记为 PASS |



## 14. 冻结与授权记录

| 项目 | 记录 |
|---|---|
| Human Review | **APPROVED**；项目负责人李建强；2026-11-24 |
| 冻结状态 | **CC-GIN-009 v1.0 Frozen with Open Items**；v0.1/v0.2 草案保留为历史，不覆盖 |
| 上游需求/技术基线 | SRS v1.4 Frozen with Open Items；TDD v1.7 Frozen with Open Items；Implementation Plan v2.2 Frozen |
| 实施授权 | 本地实施、模块升级、自动化测试及 Mock HTTP 组件集成测试 |
| 排除事项 | 不访问真实 Ginlong/生产；不做独立人工 HVR；不修改 API06/08/10；不物理删除历史收货明细或共享字段 |
| 外部事项 | Ginlong 对同订单分 Picking `CREATE` 的协议语义待真实联调确认，不阻塞本地实现 |
| 模板同步 | BLOCKED；沿用已批准流程例外，不伪记 PASS |


## 15. 实施与验收状态（2026-11-24）

### 15.1 验收矩阵
> 注：本表是早期执行快照；其中 CC-TEST-093 的 BLOCKED 与 8099 NOT VERIFIED 已由 §16.4 的后续证据更新。原记录保留作历史，当前结论以 §16.4–16.5 为准。


| 测试 ID | 状态 | 实际证据 |
|---|---|---|
| CC-TEST-084 | PASS | `test_api02_status_mapping_preserves_order_lifecycle`：planning/arrive/inbound 三态映射；state 不变 |
| CC-TEST-085 | PASS | `test_api02_uses_order_status_and_logs_retry_without_picking` 与五回调本地 HTTP 接收器测试：无 Picking/旧明细仍由按钮发出 API02 POST |
| CC-TEST-086 | PASS | `action_mark_arrived` 写 `status=arrive`、Chatter 跟踪可见，生命周期 `state` 不变 |
| CC-TEST-087 | PASS | API02 状态变化产生不同 Payload；成功事件重复点击按当前事件规则去重，每次按钮尝试的日志保留 |
| CC-TEST-088 | PASS | 自动筛选当前订单 Done/Incoming；测试含当前订单未完成、其他订单 Done/Incoming、另一订单出库作业，均不进入发送 |
| CC-TEST-089 | PASS | Payload 产品/SN/数量/托盘取实际 move line；operator 来自 Picking 实际确认人，operationTime 来自 `date_done` |
| CC-TEST-090 | PASS | 两个合格 Picking 各自创建成功 Event/Log；第二次点击跳过两个成功 Picking；失败 Picking 再点击重试 |
| CC-TEST-091 | PASS | 不合格 Picking 排除；没有 Done/Incoming Picking 时不发 HTTP，返回明确失败并追加订单来源 API Log |
| CC-TEST-092 | PASS | 首次失败/再次人工点击成功；历史 Log 不修改，新 Log 追加；没有后台重试 |
| CC-TEST-093 | **PARTIAL / BLOCKED** | ORM/View 自动化验证 Form Notebook、按钮及只读字段；Codex in-app browser 当前标签刷新后进入 Odoo 登录页（Session Expired），真实浏览器页面检查未完成，未登录或触发回传按钮 |
| CC-TEST-094 | PASS | 历史 API02 收货明细模型/行仍存在但不再读取或显示；API06 共享 Picking/Move Line 能力仍通过现有 API06 回归 |

### 15.2 执行证据

- Ginlong 全量 Odoo 自动化：命令 `./venv/bin/python odoo-bin -c odoo.conf -d odooce_karlrapp -u worlddepot,ginlong_apis --test-enable --test-tags /ginlong_apis --stop-after-init --http-port=0 --gevent-port=0 --log-level=info --log-handler=odoo.tests:INFO --logfile=/private/tmp/cc-gin-009-ginlong-20261124-final3.log`；`76 post-tests`、`0 failed`、`0 error(s)`、14,488 queries。首轮新增排除用例因测试辅助函数对出库 Picking 错误断言入库确认人而失败；仅修正测试夹具后全量复跑通过，保留首轮 `/private/tmp/cc-gin-009-ginlong-20261124-final2.log`。
- WorldDepot 自动化回归：`8 post-tests`、`0 failed`、`0 error(s)`、112 queries；日志 `/private/tmp/cc-gin-009-worlddepot-20261124-final1.log`。
- 静态校验：改动 Python `py_compile`、XML 解析、JSON 解析、相关 diff whitespace 校验通过。
- 测试数据库为既有 `odooce_karlrapp`，通过 `odoo.conf` 与 Odoo 标准测试运行器/ORM；未使用直接 SQL、未访问生产或真实 Ginlong。数据库安装版本为 `ginlong_apis 18.0.2.0.44`。
- 8099 的两条既有服务进程未重启。浏览器刷新后为 Session Expired；没有浏览器人工 HVR，也没有证据确认这些长期进程当前已载入本次 registry，因此不将 live 8099 标记为已验证。

### 15.3 当前状态与交接

代码实现、Ginlong 自动化、组件 HTTP/ORM 集成及 WorldDepot 必要回归通过。CC-TEST-093 的实时浏览器查看仍为 BLOCKED，FR-GIN-009 不宣称关闭条件全部满足；本 CC 状态为 **Closure Review Pending**，待补浏览器只读检查后提交关闭 Human Review。CC 内不安排人工 HVR。CC 关闭后，API02/API04 人工 HVR 回到项目原验收流程并按本目录下更新的操作指南执行。

OI-02-EXT（Ginlong 是否接受同一订单号按 Picking 分批 `CREATE`）继续 Open；只阻塞真实 Ginlong API04 联调，不阻塞本地 Mock。模板同步 BLOCKED，按已批准例外保留。

## 16. Human Review 冻结决定与最终实施记录（2026-11-24）

项目负责人批准 CC-GIN-009 v0.2 主体设计并授权冻结实施。本节记录批准后的基线和本地执行结果，不覆盖 §14–15 中的历史运行记录。

### 16.1 冻结决定

| 事项 | 冻结决定 |
|---|---|
| API02 状态 | planning→N；arrive/inbound→Y。使用 status；收货确认动作写 arrive 并留下操作记录，不修改 lifecycle state |
| API04 分批 | 每张符合条件的 Picking 一个独立本地 Event；成功跳过，失败可人工重试。Ginlong 接受同单多次 CREATE 留待真实联调 |
| API04 作业人/时间 | 复用可靠确认人；无可靠来源时，在实际 Done 操作记录 Picking 级确认人；operationTime 取 date_done，不维护逐 SN 操作人 |
| 范围冲突 | 允许上表所述最小 status/Picking 扩展；不改变订单生命周期转换，不修改 API06/API08/API10；保留历史及 API06 共享字段 |
| 上游版本 | SRS v1.6、TDD v1.9、Implementation Plan v2.4；均 Frozen with Open Items，模板同步例外保留 |

### 16.2 最终自动化证据

| 测试 | 状态 | 证据 |
|---|---|---|
| Ginlong 自动化及本地 HTTP/ORM 组件集成 | PASS | `/private/tmp/cc-gin-009-ginlong-20261124-final5.log`：76 post-tests，0 failed、0 error(s)，14,484 queries。API04 多 Picking 独立发送、第二次点击跳过成功批次、失败后真实本地 HTTP 重试及追加日志均通过 |
| WorldDepot 必要回归 | PASS | `/private/tmp/cc-gin-009-worlddepot-20261124-final2.log`：8 post-tests，0 failed、0 error(s)，112 queries |
| CC-TEST-093 浏览器页面检查 | PARTIAL / BLOCKED | 自动化核对 Notebook、回传按钮与只读结果字段通过；内置浏览器会话过期并进入登录页，未登录、未打开具体订单页，故浏览器检查未运行，不伪记 PASS |
| 8099 持久服务 Registry | NOT VERIFIED | 本轮未重启既有服务进程；模块升级和测试由 Odoo 标准测试运行器针对既有数据库完成。没有 live 8099 加载版本证据 |
| 人工 HVR | N/A（本 CC） | 按 Human Review，不设独立人工 HVR；CC 关闭后返回原项目 API02/API04 HVR |
| 真实 Ginlong API04 分批契约 | OPEN | 留待 CC-GIN-006 真实联调；本地 Mock 只验证本地实现 |

### 16.3 当前处置

Ginlong 与 WorldDepot 自动化及本地 HTTP 组件集成通过。CC-TEST-093 的浏览器只读页面检查尚未完成，因此本 CC 仍为 **Closure Review Pending**，FR-GIN-009 记录 **Closure SATISFIED: NO**。此项不是独立人工 HVR；需在可用的已登录 Odoo 浏览器会话中完成只读页面核对后再提交关闭评审。不得访问真实 Ginlong 或生产环境。

### 16.4 补充验收证据（2026-11-24）

本节补充并更新当前执行状态；§15、§16.2–16.3 中较早的失败、BLOCKED 和未验证记录保留为历史，不删除、不覆盖。

| 项目 | 当前结果 | 证据 |
|---|---|---|
| 8099 本地服务重启 | PASS | 使用既有 `odoo.conf`、`odooce_karlrapp` 和仓库 `venv`；新进程 PID 84612 监听 `*:8099`；`GET /web/login` 返回 HTTP 200；启动日志 `/private/tmp/ginlong_8099_hr_del_20261124.log` 记录加载该数据库 Registry |
| `ginlong_apis` 在线版本 | PASS | Odoo Shell ORM 查询 `state=installed`、`installed_version=18.0.2.0.44`、`latest_version=18.0.2.0.44`；仓库 Manifest 与该版本一致 |
| CC-TEST-093 登录后页面只读检查 | PASS | 使用 Codex 内置浏览器打开既有 Inbound Order `IO202611190301` / `HVR-GIN005-IN-001` 的 Ginlong APIs Notebook；实际看到 API02/API04 按钮、只读结果区及关联 Picking 列表；未点击按钮、修改字段或发送回传 |
| 项目级 HVR | NOT RUN | 仅准备指南、测试报文和本地 Mock。CC-009 关闭评审通过且项目负责人确认开始后才执行；没有创建测试订单或发送 API01/API02/API04 业务 Payload |

浏览器证据截图：[CC-GIN-009-CC-TEST-093.png](CC-GIN-009-CC-TEST-093.png)；运行记录见 [IHR-GIN-009 IHR-005](IHR-GIN-009.md#ihr-005--8099-在线版本cc-test-093-与项目-hvr-准备2026-11-24) 与 [ATR-GIN-009 §5](ATR-GIN-009.md#5-补充运行历史2026-11-24)。本次页面只读核对补齐 CC-TEST-093，不构成人工 HVR。

### 16.5 关闭评审提交状态（2026-11-24）

基于 §15 的自动化/组件集成证据及 §16.4 补充证据，实施方评估本地验收关闭条件 **Closure SATISFIED: YES**，并提交 [FR-GIN-009 v0.2](FR-GIN-009.md) 供 Human Review。当前状态为 **Closure Review Submitted — Human Review Pending**；负责人批准前，本 CC 不标记为 Closed。Ginlong 同单分 Picking `CREATE` 语义仍为 Open；模板同步继续依已批准例外标记 BLOCKED。两者均未伪记 PASS。项目级 HVR 仍须等待 CC 正式关闭及负责人确认开始。

### 16.6 回传按钮位置更正记录（2026-11-25）

后续核对发现 `.44` 时订单表单上的 Ginlong 回传按钮仍在标准表头，与 CC 的 Ginlong APIs Tab 入口要求不符。此处保留原 §16.4/16.5 历史记录，不覆盖当时的证据；本次只修正 UI 入口：移除入库、出库和盘点订单表头的 API02/API04/API06/API08/API10 按钮，将其放入各自“Ginlong 回传数据”Notebook。WMS 自身业务操作仍留在原位置。

在 Manifest `18.0.2.0.45` 上完成 8099 模块升级后，使用内置浏览器实际检查既有入库单、出库单及客户盘点订单：三个标准表头均无 Ginlong 回传按钮；对应 Notebook 分别显示 API02/API04、API06/API08 和 API10 按钮。没有点击回传按钮或改变业务数据。截图和操作记录见 [IHR-GIN-009 IHR-007](IHR-GIN-009.md#ihr-007--ginlong-回传按钮入口修正2026-11-25) 及 [ATR-GIN-009 §7](ATR-GIN-009.md#7-回传按钮-notebook-位置修正2026-11-25)。本轮未重跑自动化回归；既有 `.44` 回归证据仍按其实际版本标识，不能视为 `.45` 回归结果。
