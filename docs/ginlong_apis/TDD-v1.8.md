# Ginlong API 技术设计说明书（TDD）v1.8

| 项目 | 内容 |
|---|---|
| 文档编号 | TDD-GINLONG-API-001 |
| 版本 | v1.8：CC-GIN-009 实施基线 |
| 状态 | **Frozen with Open Items** |
| 日期 | 2026-11-24 |
| 适用模块 | `ginlong_apis`、按需扩展的 `worlddepot` 现有记录 |
| 当前批准 TDD 基线 | [TDD v1.7 Frozen with Open Items](TDD-v1.7.md)；本版本 v1.8 为当前技术基线 |
| 当前批准上游需求 | [SRS v1.5 Frozen with Open Items](../requirement/SRS_ginlong_apis-v1.5.md) |
| 当前实施契约 | [CC-GIN-005 v1.1 Frozen](../implementation/CC-GIN-005-v1.1.md)；[CC-GIN-007 v1.0 Frozen](../implementation/CC-GIN-007-v1.0.md)；[CC-GIN-008 v1.0 Frozen](../implementation/CC-GIN-008-v1.0.md)；已关闭 CC-GIN-001–004 按原冻结版本追溯 |
| 用户批准的对象边界 | [PROJECT_COGNITION.md v3.0](../context/cognition/PROJECT_COGNITION.md) |
| 外部资料 | [Ginlong V3.2 参数核对记录](V3.2参数核对记录.md) 与 V3.2 工作簿 |
| 修订依据 | 项目负责人 2026-11-24 批准全局业务键及归档 Add 规则；TV-GIN-008 ORM/源码验证 |
| 模板同步 | BLOCKED：模板源缺失；沿用既有批准例外，不记为通过 |
| CC-GIN-005 OI 处置 | [处置记录 v0.1](../implementation/CC-GIN-005-OI-disposition-v0.1.md)；不覆盖 CC v1.0 |
| productForm 决策 | [TV OI closure v1.1](../context/report/TV_ginlong_product_variants_api07_sn_OI-closure-v1.1.md)；客户已明确枚举及 SN 规则 |

本版本在保留 TDD v1.5 API01 预报 SN 与实绩边界的基础上，冻结 API01/03/05/07 有效性驱动的 Add 生命周期幂等设计。TDD v1.5 作为历史基线保留。模板同步仍 BLOCKED，沿用既有批准例外，不记为 PASS。

## 1. 系统边界及数据流

> 本版 API02/API04 设计取代 v1.6 §2.2、§3、§4.1 中关于 API02 明细状态和 API04 Picking 手选/逐行补录的旧方案；v1.6 原文件保留为历史基线。

本文件保留 v1.5 及更早版本的设计快照和验证记录。若历史章节中出现 API02 收货明细、API04 手选 Picking 或 API04 未修改等旧状态描述，以本版 §3、§4.1、§13 及冻结的 CC-GIN-009 v1.0 为当前有效设计；历史内容仅用于追溯，不作为现行实施要求。

完整业务闭环：Ginlong 下达订单 → Odoo `worlddepot` 接收/保存业务 Order → Odoo 按既有流程转交 Karl Rapp Gateway → Karl Rapp WMS 执行 → Gateway 将实际结果交回 Odoo → `stock.picking` / `stock.move.line` 记录实际出入库及库存移动 → Odoo 用户手动回传 Ginlong。

| 组件 | 职责 |
|---|---|
| `worlddepot` | 既有业务 Order、API User/Token、客户盘点指令和仓库实盘结果；在本项目授权范围内按需最小扩展 |
| Odoo `stock` | 实际出入库记录、move line 与库存账。API04/06 读取实际 picking/move line |
| `ginlong_apis` | Ginlong HTTP 契约、数据读取/转换、Endpoint 设置、现有 Form 回传入口及调用；不实现 WMS 业务或 KR 文件网关 |
| Ginlong | 业务指令与产品资料来源、库存查询方、仓库执行结果接收方 |
| Karl Rapp / Gateway | 仓库现场执行及 Odoo↔KR 文件/格式通信；与本修订无代码变更 |

API01/03 订单接收不等于仓库执行完成或库存变化。API04/06/08 必须从其规定的实际业务记录构造执行数据；API10 只从 `worlddepot` 实盘结果读取，不用 `stock.quant` 或订单计划替代。

API03 的当前接口方向由后续 Ginlong 接口矩阵确认为 Ginlong → Odoo；早期 A-003 仅是历史开发假设。该方向确认不代表已执行真实接口联调。

## 2. 持久化 Form 设计

### 2.1 用户流程

```text
业务 Order Form
  → 打开「Ginlong 回传数据」Notebook
  → 检查现有业务状态/关联实际作业/实盘结果
  → 在确实缺失且需补充的字段上输入并保存
  → 点击 Order 上「回传锦浪」
  → 按钮从已保存 ORM 记录生成 Payload
  → 同步 POST JSON
  → 追加一条现有 API 日志并显示成功/失败
```

- 不创建回传 `TransientModel` 或 Wizard。一次性选择/确认但无保存价值时才使用 Wizard；本项目的回传数据须长期保存、反复检查及失败后修改，使用标准 Form 和持久化模型。
- Inbound/Outbound Order 的现有 Form 增加 Notebook 页并保留对应 API 按钮。API04 自动发现当前入库订单的 Done/Incoming Picking，并按 Picking 独立发送；不展示 Picking 勾选入口。API06 仍按原方案使用已保存的 Picking 选择及 move line 数据。API10 的 Action、结果选择和需要的外部人员编码保存在既有 `world.depot.stocktake.order` / `.result` Form。
- 按钮方法不接受 Payload、前端临时输入或 JSON 编辑文本。Odoo 保存后，后端从 ORM 读取已保存值；若值尚未保存，不能从前端状态发送。
- JSON 只在后台构造。业务页面不显示或编辑 JSON；请求/响应仅进入现有 API 日志，供技术人员/管理员审阅。
- Form 中已有业务事实保持只读展示；只有实际业务记录缺失、V3.2 必填且已确定允许补充的值才提供持久化输入。

### 2.2 最小字段扩展

五个回传仍使用持久化 Form/Notebook；API02/08 按用户明确要求增加实际业务明细子表。其余能力继续扩展现有业务对象，不增加产品映射模型或通用集成层：

| 模型 | Ginlong 字段 | 实际用途 |
|---|---|---|
| `stock.move.line` | `ginlong_operator_code: Char` | 仅供 API06 保存其既有实际操作人员对外编码；API04 改从 Picking 级实际确认人读取 |
| `stock.move.line` | `ginlong_operation_time: Datetime` | 仅保留 API06 既有逐行字段；API04 使用 Picking `date_done`，不要求逐 SN 人工维护 |
| `stock.picking` | `ginlong_callback_selected: Boolean` | 仅供 API06 持久化本次实际作业选择；API04 按当前订单 + Done + Incoming 自动筛选 |
| `world.depot.stocktake.order` | `ginlong_api10_action: Selection(Add, Del)` | 保存 API10 本次操作；发送端允许大小写不一致并规范化为标准值 |
| `world.depot.stocktake.result` | `ginlong_callback_selected: Boolean` | 持久化本次 API10 的实际采集记录范围，支持部分采集/撤回时选择对应实际记录 |
| `world.depot.stocktake.result` | `ginlong_operator_code: Char` | 在 V3.2 要求字符串但现有实盘模型只有实际操作人关系 `operator_id` 时，保存其已确认的 Ginlong 人员编码。保留并展示原有 `operator_id`，不以回传用户替代 |
| `res.partner` | `ginlong_owner_code: Char` | 在现有货主档案保存 Ginlong owner code，供现有 WMS 项目货主消歧；不新增货主映射模型 |
| `ginlong.inbound.receipt.detail` | `order_id`、`move_line_id`、实际产品/SN/数量/托盘关联字段、`receipt_status` | 入库 Order 的持久化实际收货明细；实际事实引用所属 Order 的 stock move line，状态采用契约样例支持的 Y/N |
| `ginlong.outbound.shipment.detail` | `order_id`、`move_line_id`、实际产品/SN/数量/托盘关联字段、`shipment_status` | 出库 Order 的持久化实际发货明细；实际事实引用所属 Order 的 stock move line，状态采用契约样例支持的 Y/N |
| 出库 Order | 托盘数/毛重手工覆盖值及是否启用；自动托盘数、实际净重和有效总重量为 ORM 计算值 | 手工值持久化；关闭覆盖时按已保存实际作业数据计算；毛重默认使用实际净重 |
| `product.template` | 产品名称、Ginlong 共享属性、原生 `uom_id` / `uom_po_id` 与 `tracking` | 同一 Ginlong `productCode` 唯一对应一个模板；其共享属性仅维护一份 |
| `product.product` | `ginlong_owner_code`、原始 Ginlong `productCode` 及内部唯一 `default_code` | 每个 owner 在共享模板下对应一个变体；API01/03/07 按 `(owner, productCode)` 定位；不新增产品映射模型 |

### 2.3 Ginlong 产品模板与货主变体

| Ginlong 属性 | Odoo 权威归属 | 设计 / 当前兼容情况 |
|---|---|---|
| `productCode` | `product.product` 变体存储原始值；同码变体关联同一 `product.template` | 作为 `(owner, productCode)` 复合业务键的一部分；同一个原始码不得形成多个产品模板 |
| `owner` | `product.product.ginlong_owner_code` | 不同 owner 对应同模板下各自变体；不得按 `default_code` 单字段误选跨货主产品 |
| `productName` | `product.template.name` | 模板共享；API07 同码跨 owner 更新不得写入冲突名称 |
| `specificationModel` | `product.template.ginlong_specification_model` | 从现有变体字段迁移/提升为模板权威值 |
| `unit` | `product.template.uom_id`、`uom_po_id` | 通过现有 `uom.uom` 档案解析；Ginlong 单位文本按模板级业务属性处理，不按 owner 分叉 |
| `power` | `product.template.ginlong_power` | 从现有变体字段迁移/提升为模板共享属性 |
| `nationalStandard` | `product.template.ginlong_national_standard` | 从现有变体字段迁移/提升为模板共享属性 |
| `certificationModel` | `product.template.ginlong_certification_model` | 从现有变体字段迁移/提升为模板共享属性 |
| `productForm` | `product.template.ginlong_product_form` | 模板共享；仅接受原材料、半成品、成品；同码冲突先校验并拒绝，不修改已有记录 |
| `weight`、`length`、`width`、`height` | 对应 `product.template.ginlong_*` 字段 | 模板共享；API06 重量按已批准规则使用 `ginlong_weight` |
| Odoo `tracking` | `product.template.tracking` | 原材料映射 `none`；半成品/成品映射 `serial`；全部货主变体继承 |
| 内部编码 | `product.product.default_code` | 由实现生成稳定、无歧义的 owner+productCode 组合码；仅作为 Odoo 内部编码，不对外回传。其字符串格式不构成 Ginlong 契约或项目 Open Item |

`unit`、`power`、`nationalStandard`、`certificationModel` 的模板归属是项目负责人本轮明确决定；不宣称 Ginlong 对 Odoo 字段层级作了要求。上述四项纳入 API07 同码共享属性一致性检查。API07 对任一已确认模板共享字段发现冲突时，应在写入前拒绝请求，并保证现有模板、变体不被部分修改。

现代码在 `product.product` 定义重复的 Ginlong 属性字段，API07 也按每个变体写入共享值。迁移实现应保留模板单一权威值，调整所有受影响的 WMS / Ginlong 读取路径；不新建第二套产品档案或映射模型。既有重复模板审计和数据搬迁属于 CC-GIN-005 的迁移实现及验收工作，不再作为独立业务 Open Item；遇到无法无损迁移的数据时暂停该批迁移并提交项目负责人处理。

字段归属决定记录：项目负责人已确认 `unit`、`power`、`nationalStandard`、`certificationModel` 均属于 `product.template`。此决定关闭 CC-GIN-005 OI-GIN-005-05；字段冲突需在 API07 写入前按共享字段规则处理。该决定是 Odoo 模型设计，不表示 Ginlong 规定了 Odoo 的存储层级。客户已明确 `productForm` 仅接受原材料、半成品、成品，及其 SN 规则；其他值拒绝。TV OI-01 已由补充记录关闭，本地规则不等待 CC-GIN-006。

实际产品、SN、数量、托盘、实盘操作关系和实盘时间优先取现有模型字段。API10 不新建并行实盘模型、不访问 `stock.quant`。API08 发货子表仍按原批准设计引用现有 move line；API02 旧收货明细子表在 v1.7 停止使用，仅保留模型结构和历史行，不再作为回传来源。如果后续证明现有数据已能提供外部操作人员编码，则移除冗余输入字段前先更新 TDD/验收及代码；当前不臆造 `operator_id` 的外部编码规则。

## 3. 固定接口调用契约

| API | 按钮记录 | Action | 对外调用 | 当前本地字段状态 |
|---|---|---|---|---|
| API02 | 入库 Order | `UPDATE` | `POST` / JSON / 配置的 API02 Endpoint | 从 `status` 映射 `planning→N`、`arrive/inbound→Y`；不读取 Picking、move line 或旧收货明细。收货确认操作只写 `status=arrive`，不改变生命周期 `state` |
| API04 | 入库 Order | `CREATE` | `POST` / JSON / 配置的 API04 Endpoint | 自动筛选当前订单关联且 Done/Incoming 的 Picking；每 Picking 作为独立 Event；每行实际数据取其 move line，操作人取 Picking 实际确认人，操作时间取 `date_done` |
| API06 | 出库 Order | `CREATE` | `POST` / JSON / 配置的 API06 Endpoint | 托盘数取本次已选实际 move line `package_id` 去重；手工托盘数优先；重量读取 `product.ginlong_weight` 并按实际数量计算；`palletQty`/`totalWeight` 按 DECIMAL(18,6) 的 V3.2 字符串示例序列化为规范化 JSON 字符串 |
| API08 | 出库 Order | `CREATE` | `POST` / JSON / 配置的 API08 Endpoint | 从已保存发货明细及状态生成订单级 `shipmentConfirmed`；所有明细均为 Y 才回传 Y，出现 N 时回传 N；明细混合 Y/N 时按用户决策阻止发送并记错误 |
| API10 | 客户盘点 Order | `Add` / `Del` | `POST` / JSON / 配置的 API10 Endpoint | 只从关联实盘结果中读取已选实际行；Action 匹配不区分大小写，发送规范化值 |

- 管理员配置完整 URL，含 Ginlong objectid；Ginlong 回传接口无需认证/Key 的事实来自用户提供资料。Ginlong→Odoo 入站仍复用 `worlddepot` API User/Token/权限。
- Header 固定 `Content-Type: application/json`，使用 Odoo `requests.post(..., json=payload, ...)`；同步调用，15 秒超时；不加入自动重试、队列、cron 或后台补偿。
- API10 的 `Add`/`Del` 按大小写不敏感比较。HTTP 成功状态仍须按 V3.2 回包字段处理：2xx 且 JSON `returnStatus` 为 `Y` 视为确认成功；响应解析失败、非 2xx 或其他返回状态记录失败。
- 不同接口分别处理 Open Items。已确认的 API04/API10 本地模拟不等待 API02/API06/API08 外部字段映射。

## 4. Payload 数据读取

### 4.1 API04 入库完成（v1.7 设计）

- 用户从入库订单 Form 点击 API04 按钮；后端查询 `inbound_order_id = 当前订单`、`state = done`、`picking_type_id.code = incoming` 的 `stock.picking`。不使用 `ginlong_callback_selected`，不要求用户选择 Picking。
- 每个合格 Picking 单独构造一个 `CREATE` Payload、单独建立现有 `ginlong.api.idempotency` Event，并分别追加 `world.depot.api.log`。Event 身份由 Picking 记录身份及 `date_done` 确定，不包含可变 Payload 指纹；该 Picking 成功后再次点击跳过且不再次发送，失败/未知 Event 由用户再次点击按钮重试。一个 Picking 失败不应重复发送已成功的其他 Picking。
- 每条 `snList` 从该 Picking 的已完成 `stock.move.line` 读取产品、Lot/SN、实际数量和托盘。操作人从 Picking 级实际确认人 `ginlong_actual_inbound_operator_id.login` 读取；同一 Picking 的操作人值重复用于其实际明细行。操作时间取 Picking `date_done`，同样用于该 Picking 的明细行。不从订单确认人、Picking 负责人、回传点击人或 API01 预报推导作业事实。
- Odoo 标准入库完成入口成功将 Picking 置为 `done` 后，最小扩展记录当前实际执行用户至 Picking 级字段；不增加逐 SN 人工字段。历史 Done Picking 若没有可靠确认人，不伪造来源，Payload 校验应给出明确缺失字段并允许按真实来源修正。
- 当前 V3.2 对同一订单部分处理/整单完成的调用说明不一致。项目侧按 Picking 拆分事件供本地 Mock 验收；真实 Ginlong 分批 `CREATE` 契约仍留 CC-GIN-006 确认，不宣称本地 Mock 等于外部确认。
- 无合格 Picking 时不发送；既有业务状态、库存和 Picking 不作修改。旧 API02 收货明细模型及历史行保留但停止用于 API02；Picking/move line 上 API06 仍依赖的字段保留。

### 4.2 API10 盘点完成

- 主单字段来自 `world.depot.stocktake.order`：货主、盘点单号和已保存 Action。
- 明细只从 `order.result_ids` 中 `ginlong_callback_selected=True` 的既有实盘结果读取 SN、数量、托盘、产品编码和实际操作时间。
- 操作人实际关系 `operator_id` 保留为已有数据；Ginlong wire 的人员编码从已保存 `ginlong_operator_code` 读取。该字段为空时提示并阻止本次发送，不默认用登录用户、人员显示名称或计划人员补值。
- 未选实盘行时停止发送；不读取计划 JSON 生成结果，不访问 `stock.quant`，不做库存调整。
- `Add`、`Del` 与本次已选实盘行一起在业务 Form 保存。撤回的具体对象范围遵守 Ginlong 已确认语义；当前仅对用户显式选择的现有实际记录构造本地模拟。

### 4.3 Open Item 接口

- API02：只从既有 `inbound.order.status` 生成接口字段；`planning→N`、`arrive/inbound→Y`。收货确认按钮写入 `status=arrive` 并依赖字段 tracking/chatter 记录操作，不改变订单生命周期 `state`。旧收货明细模型停止用于 API02，历史数据保留。
- API06：识别既有备货完成事件，不增加状态门禁。托盘数为已选实际备货 `stock.move.line.package_id` 去重计数，保存的手工覆盖值优先。V3.2 API07 的产品重量写入现有 `product.ginlong_weight`，故按该产品档案单件重量乘实际数量；毛重默认净重并可覆盖。用户确认 `palletQty` 和 `totalWeight` 以 JSON string 发送，按 DECIMAL(18,6) 规范化到最多六位小数。
- API08：从持久化发货明细状态生成接口字段。所有明细状态相同时发送该状态；同一订单出现混合 Y/N 时不发送并记录错误。取消控制/取消回传不属于本次实施。
- API07：允许不同货主使用相同 `productCode`，产品业务键为 `owner + productCode`。仅接受原材料、半成品、成品；原材料对应 `tracking='none'`，半成品/成品对应 `tracking='serial'`，其他值拒绝且不改已有产品。现有 Hoymiles/OFoundation WMS 代码查找调用共享 resolver：唯一编码保持原行为；重复编码按项目 owner 的 Ginlong owner code 定位；无法唯一定位时明确报歧义，不任取首条。服务与 resolver 自动化覆盖同码跨 owner 创建、查询、更新和 API01/03 产品定位。

### API07 人工验收与错误处理补充（v1.1 Review Draft）

- **Add 幂等：** 首次 `(owner, productCode)` Add 创建产品；同一键后续 Add，无论请求内容是否相同，均拒绝并返回专用错误码 `IDM07`，不重复创建、不更新已有档案。Edit 使用既有产品并允许重复执行，包括相同 Payload；目标不存在时返回明确业务错误，不转入创建路径。
- **产品业务错误：** 同一 `productCode` 的模板共享 `productForm` 不一致时拒绝并保留已有数据（`BUS02`）；Edit 目标不存在时明确返回 `BUS03`；仅允许“原材料/半成品/成品”，其他值返回 `BUS06`。不存在的 `unit` 按已批准项目决定加入 Odoo 标准 `Unit` 类别，factor/factor_inv 为 1，不建立单位换算关系。
- **统一错误响应：** Ginlong 入站响应仅包含 `returnStatus`、`exceptionInfo`、`operationTime`；成功为 `Y / OK`。失败的 `exceptionInfo` 使用 `ErrorCode: ErrorMsg`，消息受 V3.2 40 字符长度限制，不暴露堆栈。Required/Type Validator 一次收集同类字段错误；对外摘要只保留完整字段名并在长度边界用 `...` 表示省略，完整错误清单和诊断写入现有 API 日志。该约定不增加 API07 专属错误处理框架。
- **`productName` HVR 判定：** V3.2 将 `productName` 定义为 VARCHAR。HVR07-19 以 JSON number `12345` 发送，现有 VARCHAR 类型校验按配置跳过类型检查，Odoo `Char` 字段保存成文本 `'12345'`。项目负责人于 2026-11-21 确认该名称可接受，故 HVR07-19 判定 PASS。此记录是对该测试输入的项目验收决定，不修改 Ginlong V3.2 字段定义，也不表示所有任意 JSON 类型输入都自动有效。
- **HVR 关闭及证据：** 项目负责人批准 HVR07-01–22 全部 PASS 并关闭 API07 HVR 包。HVR07-22 按负责人判定通过，但实际失败日志为 `Invalid token`，未独立证明有效且无 WMS Project 的 Token 业务路径；保留为验证证据限制，不伪称技术覆盖。详见 [HVR 执行记录](hvr/api07/HVR_API07_Execution_Record.md) 与 [IHR-GIN-005 v0.3](../implementation/IHR-GIN-005.md)。
- API04/06/10 的逐行 `operator`、`operationTime` 必须是实际记录或明确的外部编码补充；不使用回传操作者/点击时间。

### API01 Add：按 businessType 条件化的入库预报数据（v1.5）

#### 业务分支

本节仅改变 API01 Add 的 snList 处理。API01 Delete 的字段适用范围和现有取消语义不变；API05 完全保留 v1.4 规则；API03 不含 snList，本修订不影响 API03。

当 businessType 精确等于「保税_海外收货入库」时：

- 产品 SN 管理方式依已解析的 Odoo 产品 tracking 判断。tracking=serial 的产品必须提供完整真实 SN 清单；每条 snList.quantity 必须为 1；同一请求内，同一 productCode 不得重复 productSN，托盘不同也不豁免重复。
- 非 SN 管理原材料可以不提供 snList。若提供分配行，每行 productSN 必须等于 productCode；quantity 是该托盘上此原材料的预报数量，可以大于 1。同一产品允许分布在多个托盘，因而可有多条相同 productCode / productSN、不同 palletCode 的预报行。
- 每条提供的 snList 行必须关联 details 中的产品，并有 `palletCode`。相同托盘可包含多个产品；同一产品可分布于多个托盘。`palletCode` 是 Ginlong 预报字段，按行保存；不创建 Odoo 实体托盘或库存 package。
- 对每个在 snList 中出现的产品，汇总 `snList.quantity` 并与该产品的 `details.quantity` 比较，必须相等。每个 SN 管理产品必须完整出现；未提供 snList 的非 SN 原材料不因缺少托盘分配行而失败。此校验只检查订单预报内部一致性，不比较实际收货结果。
- 不同产品允许具有相同 productSN 文本；SN 管理产品仅以本请求内的 (productCode, productSN) 判重。原材料的 productSN 是产品编码占位值，不作为 SN 身份。
- 先做完整报文及业务一致性校验，成功后才写入 Order。失败拒绝整单，不保留部分订单/明细或成功幂等结果。复用现有统一业务错误和 API 日志：对外 exceptionInfo 不超过 40 字符，必要时以 ... 收尾；完整产品、SN、托盘、字段和数量诊断写入现有 API 日志。
- snList 内其他字段的必填性、类型和长度继续依 V3.2；本修订不把可选字段升级为必填，也不改变固定的三字段 Ginlong 响应。

当 businessType 不等于「保税_海外收货入库」时：

- 不要求 `snList`。即使请求包含 `snList`，也不解析、不校验其内容、不写入任何 API01 订单 SN 预报字段或订单 SN 子记录。
- 此分支仍执行其余字段的通用契约校验；businessType 本身仍按 V3.2 的请求字段规则处理。
- 分支判定使用 businessType 与上述值的精确相等比较；本修订不另行定义 businessType 枚举表。
- 现有 API 日志按既有机制保存收到的原始请求报文。日志保留不表示 `snList` 进入业务校验或 Order 持久化。

#### 预报数据与实际库存数据的模型边界

源码核对显示，现有 API01 使用 world.depot.inbound.order 作为客户入库预报单：

- API01 当前入口先在控制器中对完整报文调用 validate_payload，再进入服务；服务无 businessType 分支，始终对 snList 调用一致性校验，且 raw 原材料未提供 snList 时当前逻辑会要求托盘分配行。v1.5 拟议规则因此需要修改 API01 调用前的条件校验和服务处理；不得把这描述为现有行为。
- 订单扩展字段 `ginlong_business_type` 保存业务类型；`ginlong_sn_list_json` 是现有 Text 字段。
- `world.depot.inbound.order.product.serial.number` 是现有 Order 子记录，API01 扩展了 `ginlong_quantity`、`ginlong_pallet_code`、`ginlong_product_code`、名称及规格字段。API01 当前会将 snList 同时写入 `ginlong_sn_list_json` 和 Order 子记录；结构化 Order 子记录是客户预报业务数据，JSON 字段若保留仅作为原始报文快照，不是第二个业务事实来源。
- Order 子记录中的 serial_number / productSN 字符串（包括原材料的 productSN=productCode）不是 stock.lot，不代表已确认的物理 SN 身份，不得建立跨单据唯一性，也不得直接用于库存或 API04。
- 现有 API01 服务还通过既有 Order—产品分组模型保存 details 数量；其中 pallets=1.0 是当前数量计算的乘数，pallet_no 未由 API01 填充。该字段不得被解释成真实托盘数或托盘编号；不得把 Ginlong palletCode 写入 Odoo 物理托盘字段。
- 对 API01 函数和调用链的源码检查未发现其创建 stock.quant.package、stock.lot、stock.move、stock.picking 或 stock.quant；API01 不得调用这些实际库存写入流程。真实收货事实只能在后续实际入库作业中形成。

源码定位：控制器校验入口见 mymodules/ginlong_apis/controllers/ginlong_controller.py 的 api_logger 与 api01；API01 映射/保存见 mymodules/ginlong_apis/services.py 的 api01；订单扩展字段见 mymodules/ginlong_apis/models/wms_extensions.py 的 InboundOrder 与 InboundOrderProductSerialNumber；订单子模型见 mymodules/worlddepot/models/inbound_order.py 的 InboundOrderProduct、InboundOrderProductsOfPallet 和 InboundOrderProductSerialNumber；实际 Picking / Move Line 到 API04 的读取见 mymodules/ginlong_apis/models/ginlong_callbacks.py 的 _api04_payload；独立的 Picking 创建流程见 mymodules/worlddepot/models/inbound_order.py 的 action_create_stock_picking_old。API01 当前服务不调用该实际作业方法。

#### 当前行为与 v1.5 设计的差异

| 项目 | 当前实现 / v1.4 草案 | v1.5 提议 |
|---|---|---|
| API01 snList 适用范围 | API01 与 API05 共用一套 tracking/数量规则；API01 入口校验整份请求 | API01 Add 仅当 businessType 精确匹配保税业务时处理 snList；API05 保留旧规则 |
| 非保税业务 | 当前服务仍读取、校验并在提供时保存 snList；原材料数量非零但没有行时当前会报错 | snList 缺省或存在均忽略，不校验、不写入订单预报字段或子记录 |
| 预报持久化 | 提供 snList 时同时保存原始 JSON 与结构化 Order 子记录 | 保税预报继续复用现有结构化子记录作为预报业务数据；JSON 若保留仅为原始快照 |
| 物理库存对象 | API01 handler 当前不创建 Picking、Move、Lot、Package 或 Quant，但预报数据与库存身份边界未写清 | 明确预报记录不代表实际 SN/托盘，不得产生物理对象；实际收货另由 Picking / Move Line 表达 |
| API04 | 从所选实际 Picking / Move Line 读取，不依赖 API01 SN JSON | 保持原状，不修改 API04 实现或 Payload |

#### 后续业务需求（不属于本 TDD/CC 的 Open Item）

- API01 预报与实际收货数据的自动比较、差异展示、责任人及差异处置不在本次范围。若后续需要，应另行提出并批准需求；本 CC 不实现或验证该功能，也不据此新增实际收货/API04 门禁。

实际收货及 API04：

- 实际收货由仓库作业结果在 Odoo stock.picking / stock.move.line 记录。实际产品、数量、序列号及托盘分别从实际作业字段读取，不从 API01 预报行创建或补造。
- API04 自动读取关联当前订单且已完成的 Incoming stock.picking 的 move_line_ids，并以实际 lot_id.name、实际 package、product code 及数量组装 Payload。API04 不读取 ginlong_sn_list_json 或预报 SN 子记录。
- 预报字段可以作为未来业务比较的输入，但本 TDD/CC 不实现数据比较、差异展示、差异处理或由差异触发的限制。
- CC-GIN-007 不修改 API04 的 Payload、发送、幂等、回传日志或库存行为。其后 CC-GIN-009 已按本节设计调整 API04：仍只从实际 Picking / Move Line 取数；不比较预报与实绩，也不定义差异处置。

#### 适用范围保留

API05 继续应用 TDD v1.4 规则：按 product.tracking 区分真实 SN 与原材料托盘分配行；完成自身 snList 与盘点指令的数量、产品关联校验；不读写 stock.quant。API01 的 businessType 条件不得套用到 API05。API03 无 snList。

#### API01 设计追踪

| 规则 | 设计落实 | 后续 CC-GIN-007 验证 |
|---|---|---|
| 保税业务 serial 产品完整 SN、单条数量为 1、请求内去重 | API01 Add 在写 Order 前按 owner、productCode、product.tracking 校验 | CC-TEST-059–063、067 |
| 保税业务 raw 原材料可省略 SN；有行时以 productCode 占位并按托盘数量汇总 | 复用现有 Order 预报明细字段，不创建物理托盘 | CC-TEST-064–067 |
| 非保税业务忽略 snList | API01 按 businessType 分支绕过 snList 的 required/type/业务校验和持久化 | CC-TEST-057、058 |
| 预报与实际数据分离 | API01 写 Order 预报；API04 仅读取已保存实际 picking/move line | CC-TEST-068、069 |
| 错误整单原子性、40 字符响应和完整日志 | 复用现有事务、Error 与 API 日志组件，不新建模型 | CC-TEST-063、066、068 |
## 5. 日志与失败重试

- 复用 `world.depot.api.log`。每次调用按钮都创建独立新日志行，记录 Endpoint（脱敏后）、请求 JSON、HTTP 响应、状态码与错误；代码不得 write/unlink 之前的 API 日志。
- Endpoint 未配置、Payload 缺必填、传输异常、HTTP 非成功或响应无效时，当前 attempt 记失败并返回可理解提示；不触发后台重试。
- 用户编辑并保存 Form 后再次点击，会读取最新 ORM 值，并新增另一条日志；上一日志的请求、响应和结果不改变。
- URL userinfo 及敏感 query 值不得进入日志明文；不对业务 Payload 做整体脱敏。
- 不新增 attempt、回传状态、监控、告警、专用日志或认证模型。

## 6. 自动化测试输入与验证结果

依据 [CC-GIN-003 v1.4](../implementation/CC-GIN-003-v1.4.md) 的自动化条件。ATR-RUN-041 首次失败和 ATR-RUN-042 七项定向通过均保留。ATR-RUN-043 Ginlong 全量 30 个 post-tests、ATR-RUN-044 `worlddepot` 全量 8 个 post-tests 均通过；ATR-RUN-046 针对用户最后确认的混合状态阻止与 JSON string 序列化测试通过；ATR-RUN-047/048 最终全量均为 31 项、0 failed / 0 error，RUN-048 还覆盖六位小数舍入和尾零清理。Odoo Shell ORM 只读确认 API02/08 持久化明细、API06 计算字段、产品 owner/weight 与 move line 字段均已在 registry，且无 Ginlong callback Wizard。测试覆盖同码跨 owner 创建/更新、项目货主查询消歧、API01/03 产品定位、API02/08 已保存明细与状态 Payload、混合状态禁止发送/追加日志、API06 实际托盘计数/重量/覆盖及 string Payload、失败重试和日志追加。重量来源依 V3.2 API07 `weight` 确定为 `product.ginlong_weight`；上述用户确认事项不再是 Open Items。

已完成的 Mock 证据不等于完整 Ginlong 契约通过：

| 接口/场景 | 当前状态 |
|---|---|
| 持久化 Notebook、无回传 Wizard、API04 / API10 Form 数据保存后重读 | 自动化通过 |
| API04 完整可用字段 Mock POST / 成功响应 / 失败修改重试 | 自动化通过；真实 Ginlong 未调用 |
| API10 从选中的实盘结果 Mock POST，Add/Del | 自动化通过；撤销/部分范围外部语义仍 Open |
| API02/08 状态 | 单明细与一致状态的本地 Mock Payload 通过；若明细混合 Y/N，则阻止发送并追加错误日志，专项自动化通过 |
| API06 托盘数 | 选中实际 `package_id` 去重、手工覆盖、净/毛重保存与 Mock 自动化通过 |
| API06 重量 | 使用 V3.2 API07 `weight` 字段落入的 `product.ginlong_weight` 乘实际备货数量；WMS 原生 `product.weight` 不作为本接口重量来源。此来源已由资料与实现确认 |
| API06 数值类型 | 按用户最后确认和 V3.2 JSON 示例发送规范化 JSON 字符串；专项自动化覆盖整数及小数值 |
| API07 | API01/03/05/07 使用货主+产品编码复合键；跨 owner 同码创建、查询及更新自动化覆盖；相关 WMS 单字段搜索改为 owner 消歧或报歧义 |
| 完整浏览器人工操作、真实 Ginlong、生产 | NOT RUN；完整人工 WMS E2E 留最终集成 CC |
| CC-TEST-010/017/019 | 引用既有 ATR-RUN-026/014/016，通过且本次未重做 |
| 完整保留 WMS 回归 CC-TEST-024 | 按既有状态单独跟踪；本次回传测试不代替 |


### TDD v1.5 提议验收（尚未实施 / NOT RUN）

以下仅为拟议的 API01 专项验证要求，不是执行结果，也不替代 CC 验收：

- 使用真实 Ginlong HTTP 路由及 Odoo ORM，覆盖保税 businessType 下 serial 必填、完整单件 SN、重复 SN、产品匹配、raw 原材料省略 snList、raw 多托盘分配、同托盘混装及逐产品数量核对。
- 覆盖非保税 businessType 下 snList 缺省、合法、null、错误类型和错误行内容；只要其余报文合法，snList 均不进入业务验证或持久化。
- 各失败请求须证明无部分 Order、Order 子行、货主新建副作用或成功幂等结果，并核对固定 Ginlong 响应格式及完整错误日志。
- 成功请求须通过 ORM 断言只写入入库 Order 预报数据；前后对比 stock.lot、stock.quant.package、stock.move、stock.picking、stock.quant 无新增或变化。
- API04 回归仅验证它从实际已完成 picking/move line 取数，不读取 API01 预报；本 TDD 不要求改写或重测其既有独立组件功能。
- 完整测试范围、运行顺序和 HVR 操作由新 CC-GIN-007 冻结后执行；本轮没有运行测试或人工 HVR。
## 7. API09 与 Ginlong 管理界面（CC-GIN-004 修订）

### 7.1 API09 数据语义与来源

- Ginlong V3.2 API09 请求必填 `owner`、`warehouse`；响应为完整 `inventoryList`，明细字段为 `productCode` 与 `quantity`，不分页、不增加请求产品过滤或协议外字段。
- `quantity` 定义为 Odoo 当前库存记录所表达的**实际物理在库数量**。查询 `stock.quant.quantity`，不减 `reserved_quantity`，不以可用量代替，不执行任何库存写入或库存移动。
- 结果按 `(ownerCode, warehouseCode, raw productCode)` 区分和汇总；必须通过货主编码及原始 Ginlong 产品编码识别数据，不依赖内部 `default_code` 作外部产品码。
- Karl Rapp WMS 执行现场作业并提供结果；Odoo 接收结果并由既有 `stock.picking` / 原生库存机制记录。此设计只读取 Odoo 已有库存记录；不实现或假定 Karl Rapp 库存同步已完成。

只读源码和 Odoo ORM 检查（数据库 `odooce_karlrapp`，未写入数据，结束时回滚）发现：

| 对象 | 源码/Registry 可用字段 | 当前开发库实际数据 | 结论 |
|---|---|---|---|
| 货主 | `res.partner.ginlong_owner_code`；`stock.quant.owner_id` 关联 `res.partner` | 开发库当前无 Ginlong owner partner、内部 quants 为 0 | API09 先以请求 owner code 精确查找 partner，再以其 ID 过滤 `stock.quant.owner_id`；不存在的 owner 返回空清单，绝不回退到其他货主 |
| 仓库 | `stock.warehouse.code`；内部库位通过 `view_location_id` 界定 | 当前仅 1 个仓库：`KRWH` / `KarlRapp-WH` | API09 按请求 warehouse code 精确匹配现有仓库；未知编码返回校验错误且不回退到其他仓库。当前不建映射模型；未来多仓时按 Ginlong 要求扩展现有仓库字段 |
| 产品 | 当前有 `product.product.default_code`、`ginlong_owner_code`；TV 只读核查未发现独立原始 `ginlong_product_code` 字段 | 8 个产品有 Ginlong owner code，当前均为 `2110`；无跨 owner 同码样本 | 目标设计新增/迁移原始 Ginlong `productCode` 到变体字段；`default_code` 仅用于 Odoo 内部 owner+productCode 组合编码 |
| 库存 | `stock.quant.quantity`、`reserved_quantity`、`location_id`、`owner_id`、`product_id` | 当前内部 `stock.quant` 为 0 | 货主维度由 `stock.quant.owner_id` 与 `res.partner.ginlong_owner_code` 匹配；目标响应产品编码从 `product_id.ginlong_product_code` 读取。模拟夹具验证隔离，未验证真实库存或 KR 同步 |

源码核对还发现，现有 `worlddepot` `/my/stock_report` 只筛内部库位，并可按 Odoo `warehouse_id`、location、product 过滤，直接搜索 `stock.quant`，没有 Ginlong owner 隔离。本设计按项目负责人决定以 `res.partner.ginlong_owner_code` 定位 partner，并用 `stock.quant.owner_id` 限定该货主库存；目标响应产品编码来自 quant 产品的原始 `ginlong_product_code`，不暴露内部组合 `default_code`。API07 产品主数据仍按 `owner + raw productCode` 识别，但 API09 库存所有权以 quant 的 owner 关系为准，不从产品模板/变体 owner 字段推算或跨货主合并。

API09 先精确查找 `res.partner.ginlong_owner_code`，再按 `stock.quant.owner_id` 过滤；对指定 `warehouse` 精确查找一个 `stock.warehouse.code`，不存在或不唯一时拒绝请求，不能回退到唯一仓库。当前数据库字段 `stock.warehouse.code` 为短码；本地测试验证匹配短码及未知值隔离，不声称任意 40 字符 Ginlong 仓库码已联调兼容。响应回显请求中的 owner、warehouse；不以显示名称匹配或跨货主合并。

### 7.2 API09 只读实现约束与组件验证

- 请求以 Ginlong owner code 查找 `res.partner.ginlong_owner_code`，并以 partner ID 过滤 `stock.quant.owner_id`；仓库参数精确匹配现有 `stock.warehouse.code`，未知值拒绝。产品编码从 `stock.quant.product_id.ginlong_product_code` 读取。该原始编码字段属于变体；不得将内部组合 `default_code` 放入响应。不增加映射模型。
- `quantity` 对同一 `(ownerCode, warehouseCode, productCode)` 的物理库存行求和，保留 V3.2 的 DECIMAL(18,6) 响应定义；不得减预留量。
- API09 调用链只做搜索/读取和响应构造，不调用 `stock.quant.create/write/unlink`，不创建或过账 picking/move，不做库存调整。
- 若开发库仍无真实库存记录，组件测试通过 Odoo ORM fixture 建立**明确标记为模拟数据**的库存记录，覆盖两个货主同码隔离、指定仓库过滤、物理数量汇总、不扣预留量及查询前后库存不变。此类测试只能证明 API09 查询逻辑，不证明 Karl Rapp → Odoo 的真实同步。
- 真实库存同步/数据来源验证不在本 CC 伪记通过；由后续本地集成或经授权的联调工作按实际环境核验。

### 7.3 管理界面边界

Ginlong 菜单作为现有 WMS 管理入口的轻量导航，只提供：

1. 已有 API Settings 入口（沿用现有 Endpoint、限流和设置能力，不增加 API01–10 启用开关）；
2. 现有 `world.depot.api.log` 的 Ginlong 过滤查询；
3. 现有入库、出库、盘点和产品记录的查询入口；
4. 失败出站日志到原业务单据的定位，之后由用户在原单据修正并调用现有手动回传按钮。

不创建监控平台、重发中心、平行 API 日志、独立业务流程或 JSON 编辑器。现有 `world.depot.api.log` 增加一个 Ginlong 业务记录 `Reference` 字段，失败回传日志关联原业务单据；尚未创建业务记录的失败日志不伪造链接。由 `stock.group_stock_manager` 取得只读访问，不新建角色；Settings 仍由 Odoo 系统管理员访问。业务查询域分别使用入库/出库单 `ginlong_owner_code`、盘点单 `owner_code`、产品 `ginlong_owner_code`。

### 7.4 API09 测试范围

CC-GIN-004 自动化和组件测试至少覆盖：必填请求字段和响应契约；按 owner+warehouse 过滤；跨 owner 同 productCode 隔离；完整产品列表且无分页；`stock.quant.quantity` 汇总且不减 reservations；模拟库存数据标识；严格只读；无真实 KR 同步证据时明确保持“未验证”。管理 UI 覆盖菜单、现有 Settings 入口、日志过滤、业务记录入口、失败日志源单定位；完整浏览器/WMS 人工 E2E 留 CC-GIN-005，真实 Ginlong HTTP 联调留 CC-GIN-006。

## 8. 版本追踪

| 版本 | 日期 | 变更 | 状态 |
|---|---|---|---|
| v0.4 | 2026-11-18 | 原冻结设计基线，Wizard 业务数据确认界面 | Frozen with Open Items；保留原件 |
| v0.4.1 | 2026-11-18 | 回传 Base URL/无鉴权事实补充 | 历史事实补充；保留原件 |
| v0.5 | 2026-11-18 | 依用户确认改用标准持久化 Form/Notebook；明确最小持久化字段、已保存 ORM 读取、固定 POST/JSON/Action、追加式日志及逐接口 Open Items | 实施修订；待后续技术评审/冻结 |
| v0.6 | 2026-11-18 | 用户最终规则：API07 owner+productCode，API02/08 新增持久化实收/实发明细，API06 基于实际 package_id/数量和产品重量并提供人工覆盖；补充测试和未决项 | 用户授权实施；未冻结 |
| v0.7 | 2026-11-18 | 记录 API07 跨 owner 查询与受影响 WMS resolver 回归、API02/08 持久化明细 Payload、API06 实际数量/托盘/重量及覆盖测试；纳入用户最终确认的混合状态阻止、API06 JSON string 与 Ginlong weight 来源；记录全量自动化及 ORM 核验 | 历史实施验证修订；保留 |
| v0.8 | 2026-11-18 | 补充 API09 实际物理库存语义、产品 owner+productCode 身份及 owner+warehouse+productCode 库存维度；明确单仓库直接查询、失败日志业务关联字段、既有库存管理员只读权限、模拟库存测试与真实 KR 同步验证边界 | Frozen — Human Review APPROVED |
| v0.9 | 2026-11-18 | 按项目负责人后续明确决定，修订 API09 owner 来源为 `res.partner.ginlong_owner_code` → `stock.quant.owner_id`，warehouse 按 `stock.warehouse.code` 精确匹配并隔离未知值；引用 CC-GIN-004 v1.1 关闭补充，v0.8 原件保留 | Frozen — Human Review APPROVED；模板同步仍 BLOCKED |
| v1.0 | 2026-11-19 | 将 Ginlong `productCode` 映射为 template、owner 建 variant；确认共享属性归属、productForm/tracking、本地产品识别和旧数据迁移设计；保留 v0.9 Frozen 原件 | Frozen with Open Items；Human Review APPROVED |
| v1.1 | 2026-11-21 | 补充 API07 HVR 人工结果、Add/重复 Add 与 Edit 行为、业务错误及字段错误摘要；记录 `productName=12345` 的项目负责人验收决定和 HVR07-22 证据限制；保留 v1.0 冻结原件 | Review Draft；等待 Human Review |
| v1.2 | 2026-11-22 | 根据项目负责人确认，补充 API01/API05 基于 `product.tracking` 的 SN 清单、产品匹配、数量汇总、重复 SN、写入前拒绝和明确错误要求；保留 V3.2 示例差异说明、API01/API05 HVR 及 Odoo 自动化证据；不修改 v1.0 冻结原件 | Review Draft；等待 Human Review |
| v1.3 | 2026-11-22 | 明确单条真实 SN quantity=1、请求内 `(productCode, productSN)` 身份键、托盘不参与查重、不同产品/业务单据可复用 SN、API05 可引用未入库 SN；补充多产品多托盘 API01 HVR 和自动化证据 | 历史 Review Draft；保留 |
| v1.4 | 2026-11-23 | 为非 SN 原材料定义 `productSN=productCode` 的托盘数量分配行；允许相同原材料伪 SN 跨托盘重复；要求所有产品按 `snList` 汇总与 details 对账并持久化托盘分布 | Review Draft；等待 Human Review |
| v1.5 | 2026-11-23 | 将 API01 snList 规则限定于 businessType=保税_海外收货入库；其他业务类型不处理、不校验、不保存到 Order，但日志按既有机制留存原始请求；区分 Order 预报与实际 Picking；明确本 CC 不实现预报/实收差异比较；API04 不变 | Frozen with Open Items；Human Review APPROVED |

## 9. TDD v1.0 Human Review 与冻结记录（历史）

| 项目 | 记录 |
|---|---|
| Human Review | TDD v1.0 获 APPROVED；项目负责人李建强；2026-11-19（不代表 v1.1 已批准） |
| 冻结决定 | TDD v1.0 Frozen with Open Items；取代 v0.9 为当前设计基线，旧版保留 |
| 实施授权 | 按 CC-GIN-005 v1.1 与 Implementation Plan v1.8 执行本地开发、自动化/ORM 集成及浏览器验证 |
| 外部边界 | 不访问真实 Ginlong、生产或 KR/Gateway 环境；真实 Ginlong 联调留 CC-GIN-006 |
| 模板同步 | BLOCKED；沿用已批准例外，不标记 PASS |

## 10. TDD v1.5 冻结记录（历史批准基线）

| 项目 | 记录 |
|---|---|
| Human Review | APPROVED；项目负责人李建强；2026-11-23；有条件评审意见已落实 |
| 冻结决定 | TDD v1.5 Frozen with Open Items；作为当前 TDD 基线；TDD v1.0 与 v1.1–v1.4 历史文件保留 |
| 上游基线 | [SRS v1.2 Frozen with Open Items](../requirement/SRS_ginlong_apis-v1.2.md)；[Implementation Plan v1.9 Frozen](../implementation/IMPLEMENTATION_PLAN_ginlong_apis-v1.9.md) |
| 当前 CC | [CC-GIN-007 v1.0 Frozen](../implementation/CC-GIN-007-v1.0.md)；授权本地实施与自动化/组件集成测试 |
| 本次范围 | API01 预报接收与保存；API04 仅验证实际 Picking 数据来源独立性；不开发预报/实收比较、差异展示或差异处置 |
| 先前草稿 | TDD v1.1–v1.5 Review Draft 保留；本文件为修订后冻结版本 |
| 模板同步 | BLOCKED；沿用既有批准例外，不标 PASS |


## 11. 业务有效性驱动的 Add 生命周期幂等

### 11.1 目标及源码证据

API01/03/05/07 的 Add 判重依据“当前业务对象是否有效”，不依据历史成功幂等记录。API01/03/05 订单取消后可重加；API07 货主产品变体归档后可重加。相同/不同 Payload 遵循同一有效性判断。旧业务对象、幂等记录及 API 日志不覆盖、不删除。

源码核对发现：`mymodules/ginlong_apis/idempotency.py` 的 `has_successful_once_for_business_key` 与 `duplicate_error_for_completed_request` 只检查历史成功幂等行；`execute` 在指纹重放前会拦截历史成功业务键，而移除该拦截后相同指纹仍可能重放旧成功响应。`mymodules/ginlong_apis/models/api_control.py` 当前唯一键 `(api_code,business_key,request_fingerprint)` 不容许相同 Payload 的后续生命周期建立独立历史行。`services.py:ensure_api07_add_is_new` 以 `active_test=False` 搜索任意 owner+productCode 变体，并检查成功幂等历史，故归档产品也永久阻塞。API01/03/05 Delete 搜索所有状态，存在多轮 cancel 历史时可能 `limit=2` 歧义。WorldDepot 入库单现有 `@api.constrains` 通过 ORM 搜索同项目、同 reference、非 cancel 单；该搜索型 constraint 不能单独保证并发原子性。未发现出库单、盘点单相应的数据库有效键唯一保障。

### 11.2 通用组件边界与业务键作用域

通用 Idempotency 不引用 Odoo 业务模型名、状态字段或取消/归档值。业务适配器提供有效性策略：按本对象定义的业务键查找当前有效记录，并提供不透明记录身份；通用层只协调策略结果、请求指纹、事务执行、生命周期事件键和历史审计，不决定业务模型/字段/状态或重复错误语义。

适配器矩阵：API01 全局按 `inboundOrderNo` 查询，API03 全局按 `outboundOrderNo` 查询，API05 全局按 `countOrderNo` 查询，三个键均不含 `project`，`state != cancel` 有效。API07 按 `(owner, productCode)` 查询，匹配变体 `active=True` 有效。跨 project 的 Add 判重是全局的；新订单归属和 Delete 目标仍遵循当前 API User 的 project 访问机制，冲突响应不得泄露其他 project 单据详情。

### 11.3 Add 执行顺序提案

1. 认证、Required/Type 校验、Action 解析及已有契约校验按原顺序完成。
2. 对 Add 调用业务适配器的有效性策略；若有效对象存在，立即返回重复业务错误，不论 Payload 指纹是否相同，不调用创建 Handler，也不重放旧成功响应。
3. 若没有有效对象，使用现有 `ginlong.api.idempotency.event_key` 保存本次业务生命周期的事件身份；Add 创建新周期时生成新的不透明事件键，Delete 事件键关联到适配器返回的当前订单记录身份。无需新增 `lifecycle_id` 字段。当前事件结果可重放；历史生命周期结果不匹配新事件键，因此不阻塞、不回放。
4. 业务创建与该生命周期幂等成功结果在同一 Odoo 事务中提交；业务失败时整体回滚，不留下部分业务记录或成功幂等行。
5. 由业务模型的数据库级有效键唯一性裁决并发 Add。竞争失败事务回滚后，仅将已识别的有效身份唯一冲突映射成重复错误；其他完整性异常按原错误分类处理。
6. API01/03/05 Delete 仅定位有效记录并按原规则置 `cancel`。已取消历史记录不参与 Delete 目标选择；不物理删除历史。API07 使用标准归档，无 Ginlong Delete。

### 11.4 幂等历史与生命周期事件键

现有 `event_key` 字段可表达新业务周期身份。将现有唯一约束由 `(api_code,business_key,request_fingerprint)` 调整为 `(api_code,business_key,event_key,request_fingerprint)`；执行器的结果查找域同时包含 `event_key`。入口适配器先判断有效记录：Add 已存在则返回重复错误；没有有效记录的 Add 生成新事件键；Delete 使用当前订单记录的稳定不透明身份。历史行的 `event_key=False` 旧数据保留原值，成功响应、指纹、状态和日志不改写。事件失败随 Odoo 事务回滚，不留下成功幂等行；无外部 Request ID 时不宣称跨网络 exactly-once。

### 11.5 并发有效键唯一性

ORM search 后 create 不是并发保障。需为四类业务模型分别建立数据库原子唯一性：模型保存一个由其自身有效状态派生的 active identity；有效时携带业务键，订单取消/产品归档时释放该 identity，历史记录仍保留。数据库唯一约束允许无效历史记录并存。API01 现有 Python `@api.constrains` 需增加原子保障；API03、API05 和产品变体也需补齐。实现不得用进程内锁、Worker 本地缓存或串行测试替代数据库唯一约束。

采用存储计算的有效身份字段（有效时写全局业务键，cancel/archive 时写空值）及 ORM `_sql_constraints` 唯一约束。入库、出库和盘点身份只包含各自订单号，不含 `project`；产品身份使用无歧义的 `(owner, productCode)` 编码。ORM 只读预检已在 odooce_karlrapp 中完成：API01/03/05 全局有效订单号及 API07 active owner+productCode 均未发现重复组。若其他环境升级前发现冲突，停止升级并报告，不自动合并、删除或取消任何记录。

### 11.6 API07 归档后的 Add

Odoo 18 `product.product` 原生在 `(product_tmpl_id, combination_indices)` 上使用仅对 `active=True` 生效的唯一索引。TV 源码核对及 Odoo Shell 回滚事务验证表明：归档后恢复原变体可以保持原记录 ID 和 owner/productCode 关联，并恢复唯一 active 组合。最小方案是 API07 Add 忽略归档记录的重复拦截，并在共享模板及属性校验通过后恢复同一归档变体；不新建第二个变体，不改写历史业务关联，不新增恢复/归档状态机。当前数据库没有归档 Ginlong 产品变体，故现存历史引用统计为零；自动化测试仍需覆盖带引用记录的归档/恢复行为。

### 11.7 Delete 与存量数据

API01/03/05 Add 的存在性查询按全局业务键；Delete、Edit 目标仍按业务键、当前 API User 的 project 和有效状态查询。多条已 cancel 历史不构成歧义；同一 project 若存在有效对象则只允许命中该对象。跨 project 冲突错误不包含源 project 的单据详情。历史单据、幂等行和日志完整保留。

迁移/约束启用前检查四类对象的有效重复业务键。发现已有重复时只输出记录 ID、键和状态供处理，不自行修改业务数据。历史成功幂等记录与请求日志完整保留。

### 11.8 自动化与人工 HVR 追踪

详细矩阵见 [CC-GIN-008 v1.0 Frozen](../implementation/CC-GIN-008-v1.0.md)。每类对象均覆盖：首次 Add；有效记录相同/不同 Payload 再 Add 拒绝；Cancel/Archive 后相同/不同 Payload 新建；新生命周期再次重复拒绝；多次失效/重建；历史保留；并发同/不同 Payload。Delete 场景须证明只处理当前权限范围内的有效对象。测试走真实 HTTP 入口、Odoo ORM 和实际数据库事务；HVR 由负责人执行，不由自动化 PASS 代替。

### 11.9 冻结决策和剩余 Open Items

| 决策点 | 当前状态 |
|---|---|
| 全局业务键 / project 权限边界 | 已冻结；业务键不含 project，订单归属、Delete/Edit 权限仍按现有 project |
| 幂等生命周期字段 | 已冻结；复用 `event_key`，不新增 `lifecycle_id` |
| Odoo 有效键唯一性 | 已冻结；存储计算有效身份 + ORM 唯一约束；迁移前发现重复即停止 |
| API07 归档 Add | 已冻结；恢复既有变体，保留原 ID 与业务关联 |
| 并发事务测试 | CC-GIN-008 自动化门禁；未执行项必须如实记入 ATR，不得在 CC 关闭前留未决强制项 |
| 模板同步 | BLOCKED；沿用已批准例外，不记 PASS |

TV-GIN-008 的实证见 [报告](../context/report/TV-GIN-008-v0.1.md)。

### 11.10 Human Review 补充：Edit/Del 仅作用于有效订单

项目负责人于 2026-11-24 确认，API01/03/05 的业务有效性必须同时约束支持的 Add、Edit、Del 操作：

1. Add 继续按全局业务键检查有效记录；存在有效单据时拒绝，不存在有效单据时允许新生命周期。
2. Edit 只能定位当前 API User 项目内的有效订单；已取消历史不能被 Edit 恢复或修改。API01 V3.2 对外 Action 仍为 Add/Del，本补充不增加 Ginlong API01 Edit。
3. Del 只能定位当前 API User 项目内的有效订单并将其设为 `cancel`。没有有效订单（包括只存在 `cancel` 历史订单）时返回业务错误，不调用取消 Handler。
4. Del 的有效性判断必须在幂等结果查找/重放前执行。无有效记录时不得因历史成功幂等行返回成功，也不得为拒绝请求新增成功幂等记录。这个拒绝不区分相同或不同 Payload；历史订单、既有幂等记录和日志均保留。
5. 重新 Add 创建新的有效订单后，Del 使用新订单记录身份建立新的生命周期事件并可成功取消。

以上为对第 11 节已冻结生命周期设计的补充；不改变业务唯一键、project 权限、历史留存、API 字段或其他幂等规则。

## 12. TDD v1.6 冻结记录

| 版本 | 日期 | 内容 | 状态 |
|---|---|---|---|
| v1.5 | 2026-11-23 | API01 预报规则及实绩边界 | Frozen with Open Items；历史批准基线 |
| v1.6 | 2026-11-24 | 全局有效对象 Add、事件键生命周期幂等、有效键数据库唯一性及 API07 归档恢复 | Frozen with Open Items；Human Review APPROVED |
| v1.6 Human Review 补充 | 2026-11-24 | API01/03/05 Edit/Del 先检查当前有效记录；重复 Del 在订单取消后返回业务错误，不重放旧成功结果 | 已批准；纳入 CC-GIN-008 收尾验证 |

Human Review：APPROVED；项目负责人李建强；2026-11-24；批准冻结文档并进入 CC-GIN-008 实施。模板同步 BLOCKED，沿用已批准例外，不伪记 PASS。


## 13. CC-GIN-009：API02/API04 业务来源对齐（v1.8 当前设计）

本节取代 TDD v1.7 §13 中已实施部分。TDD v1.7 原件保留为历史；其他 API 的既有设计、共享字段和数据模型不因本节改变。

### 13.1 API02：订单状态回传

- 数据来源是 `world.depot.inbound.order.status`；固定映射 `planning→N`、`arrive→Y`、`inbound→Y`。不读取 Picking、move line 或 `ginlong.inbound.receipt.detail`。
- 入库单提供“收货确认”业务操作，将 `status` 更新为 `arrive`。通过现有 `mail.thread` 字段跟踪记录操作人、时间和状态变化；不改订单生命周期 `state`。该按钮只记录业务事实，不自动发送 API02。
- API02 回传按钮按当前已保存 `status` 生成 `receiptConfirmed`，同步 POST 到管理员配置的 Endpoint，复用现有认证配置、`ginlong.api.idempotency`、`world.depot.api.log`。
- 旧收货明细模型、字段和历史行停止被 API02 读写，移除维护入口；模型和历史数据保留。API06 共用的 Picking/Move Line 字段与入口保持不变。

### 13.2 API04：每张 Picking 独立事件

- 用户在 Inbound Order 的 Ginlong APIs Tab 手动点击回传。服务端查询当前订单的 `stock.picking`，条件为 `inbound_order_id = 当前订单`、`state = done`、`picking_type_id.code = incoming`；不读取手选标记，不要求用户选择 Picking。
- 每张 Picking 单独生成 API04 Payload、`ginlong.api.idempotency` Event 与 `world.depot.api.log` 发送记录。Event 身份使用 Picking 模型/ID、订单业务键和 `date_done`；API04 配置不将可变 Payload 指纹并入 Event 身份。已成功 Event 再次触发时跳过；失败或结果未知仅在用户再次点击时重试，并为实际 HTTP 尝试追加新 API Log。无合格 Picking 时不发送并记录失败日志。
- Payload 的产品、SN、数量和托盘取该 Picking 的完成 move lines；`operator` 使用 Picking 实际确认用户的 login，`operationTime` 从 `date_done` 格式化。标准 `button_validate` 使 Incoming Picking 进入 Done 后，如该 Picking 有所属 Inbound Order 且尚无记录，写入 `ginlong_actual_inbound_operator_id`；不覆盖历史确认人。历史 Done Picking 若该字段为空，不推断或补造身份，本次 Payload 校验失败并提示缺少实际确认人。
- 不增加逐 SN 人工维护，不读 API01 预报数据，不创建批次模型，不改变库存和 Picking 状态。一个 Picking 的操作员/完成时间按现有 Picking 级事实用于该 Picking 的 SN 项。
- 同一订单多张 Picking 分别发送 `CREATE` 是本地项目约定；Ginlong 是否接受该外部调用模式仍留真实联调。Mock 成功不表示外部契约已确认。

### 13.3 UI 与结果记录

- 入库单原有 Ginlong APIs Notebook 只保留 API02/API04 手动回传按钮和只读成功状态、回传时间、错误信息。
- API02 最近结果根据订单来源 API Log 查询；API04 最近结果汇总订单及相关 Picking 来源 API Log。业务状态 Chatter、API Event 和 API Log 保持各自用途，不相互替代。
- 不恢复 Wizard、不增加用户 JSON 编辑器、不要求重复录入收货事实。

### 13.4 实施及验收要求

- CC-GIN-009 v1.0 冻结并已授权实施。自动化和组件集成使用本地 Odoo、Mock HTTP；不访问真实 Ginlong/生产。
- API02 核验状态映射、收货操作不改变 `state`、无 Picking 时仍可回传、旧详情不再作为数据源、业务日志/Event/API Log 独立可查。
- API04 核验当前订单 + Done + Incoming 条件、无合格作业阻止发送且记录 Log、每 Picking 独立 Event/Log、成功跳过、失败人工重试、实际 Move Line 数据和实际确认人/`date_done`、库存无副作用。
- 模板同步继续 BLOCKED，沿用批准的流程例外，不记 PASS。独立人工 HVR 不属于 CC-GIN-009 验收；关闭后回到项目 API02/API04 人工 HVR。

### 13.5 外部待确认

| 事项 | 当前处理 | 阻塞范围 |
|---|---|---|
| Ginlong 是否接受同一 `inboundOrderNo` 下每张 Picking 各自发送 `CREATE` | 本地按 Picking 单独 POST，并以 Mock 验证 | 不阻塞本地开发与 CC-009 自动化；阻塞真实 API04 联调 |
| 模板同步 | 继续沿用批准例外 | 不阻塞本 CC |

### 13.6 版本与冻结

| 版本 | 日期 | 内容 | 状态 |
|---|---|---|---|
| v1.7 | 2026-11-24 | CC-GIN-009 业务来源设计及冻结基线 | Frozen with Open Items；历史保留 |
| v1.8 | 2026-11-24 | 按 Human Review 批准完成 API02 状态操作、API04 Picking/Event/实际确认人设计及 CC-009 测试追踪 | Frozen with Open Items；Human Review APPROVED |

Human Review：APPROVED；项目负责人李建强；2026-11-24；批准 CC-GIN-009 文档修订及本地实施。真实 Ginlong、生产和独立人工 HVR 不在本 CC 授权范围。模板同步仍 BLOCKED，沿用批准例外。
