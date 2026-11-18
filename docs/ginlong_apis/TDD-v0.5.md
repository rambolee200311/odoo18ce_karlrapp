# Ginlong API 技术设计说明书（TDD）v0.5

| 项目 | 内容 |
|---|---|
| 文档编号 | TDD-GINLONG-API-001 |
| 版本 | v0.5 实施修订 |
| 状态 | 本轮实施设计；Open Items 保留；尚未声明冻结 |
| 日期 | 2026-11-18 |
| 适用模块 | `ginlong_apis`、按需扩展的 `worlddepot` 现有记录 |
| 上游技术基线 | [TDD v0.4](TDD-v0.4.md) 与 [v0.4.1](TDD-v0.4.1.md) 历史保留 |
| 当前实施契约 | [CC-GIN-003 v1.2](../implementation/CC-GIN-003-v1.2.md)，其余沿用 v1.1 Frozen with Open Items |
| 用户批准的对象边界 | [PROJECT_COGNITION.md v1.7](../context/cognition/PROJECT_COGNITION.md) |
| 外部资料 | [Ginlong V3.2 参数核对记录](V3.2参数核对记录.md) 与 V3.2 工作簿 |
| 模板同步 | BLOCKED：模板源缺失，沿用已批准流程例外；未伪记通过 |

> 本版本只修订五个人工回传接口的界面、数据持久化和调用方式。其余 TDD v0.4/v0.4.1 的技术边界与 Open Items 保持不变。所有数据库操作、测试均通过现有 Odoo ORM/标准测试运行器；不直接访问 PostgreSQL。

## 1. 系统边界及数据流

完整业务闭环：Ginlong 下达订单 → Odoo `worlddepot` 接收/保存业务 Order → Odoo 按既有流程转交 Karl Rapp Gateway → Karl Rapp WMS 执行 → Gateway 将实际结果交回 Odoo → `stock.picking` / `stock.move.line` 记录实际出入库及库存移动 → Odoo 用户手动回传 Ginlong。

| 组件 | 职责 |
|---|---|
| `worlddepot` | 既有业务 Order、API User/Token、客户盘点指令和仓库实盘结果；在本项目授权范围内按需最小扩展 |
| Odoo `stock` | 实际出入库记录、move line 与库存账。API04/06 读取实际 picking/move line |
| `ginlong_apis` | Ginlong HTTP 契约、数据读取/转换、Endpoint 设置、现有 Form 回传入口及调用；不实现 WMS 业务或 KR 文件网关 |
| Ginlong | 业务指令与产品资料来源、库存查询方、仓库执行结果接收方 |
| Karl Rapp / Gateway | 仓库现场执行及 Odoo↔KR 文件/格式通信；与本修订无代码变更 |

API01/03 订单接收不等于仓库执行完成或库存变化。API04/06/08 必须从其规定的实际业务记录构造执行数据；API10 只从 `worlddepot` 实盘结果读取，不用 `stock.quant` 或订单计划替代。

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
- Inbound/Outbound Order 的现有 Form 增加 Notebook 页并保留对应 API 按钮。API04/06 的本次 picking 选择保存于现有 `stock.picking`；Order Notebook 展示并允许选中关联作业单，再打开作业单 Form 保存逐 SN 现场值于 move line。API10 的 Action、结果选择和需要的外部人员编码保存在既有 `world.depot.stocktake.order` / `.result` Form。
- 按钮方法不接受 Payload、前端临时输入或 JSON 编辑文本。Odoo 保存后，后端从 ORM 读取已保存值；若值尚未保存，不能从前端状态发送。
- JSON 只在后台构造。业务页面不显示或编辑 JSON；请求/响应仅进入现有 API 日志，供技术人员/管理员审阅。
- Form 中已有业务事实保持只读展示；只有实际业务记录缺失、V3.2 必填且已确定允许补充的值才提供持久化输入。

### 2.2 最小字段扩展

不新增模型或子表，仅扩展现有持久化业务模型：

| 模型 | Ginlong 字段 | 实际用途 |
|---|---|---|
| `stock.move.line` | `ginlong_operator_code: Char` | 保存每条 API04/06 执行明细的实际操作人员对外编码；不得用 picking 负责人、创建人或点击回传用户代替 |
| `stock.move.line` | `ginlong_operation_time: Datetime` | 保存每条 API04/06 执行明细的真实操作时间；picking 完成时间不是逐 SN 时间，不自动复制到每一行 |
| `stock.picking` | `ginlong_callback_selected: Boolean` | 持久化订单下本次实际作业单选择；API04/06 读取已保存选中的 picking，不把未选作业混进本次回传 |
| `world.depot.stocktake.order` | `ginlong_api10_action: Selection(Add, Del)` | 保存 API10 本次操作；发送端允许大小写不一致并规范化为标准值 |
| `world.depot.stocktake.result` | `ginlong_callback_selected: Boolean` | 持久化本次 API10 的实际采集记录范围，支持部分采集/撤回时选择对应实际记录 |
| `world.depot.stocktake.result` | `ginlong_operator_code: Char` | 在 V3.2 要求字符串但现有实盘模型只有实际操作人关系 `operator_id` 时，保存其已确认的 Ginlong 人员编码。保留并展示原有 `operator_id`，不以回传用户替代 |

实际产品、SN、数量、托盘、实盘操作关系和实盘时间优先取现有模型字段。API10 不新建并行实盘模型、不访问 `stock.quant`。如果后续证明现有数据已能提供外部操作人员编码，则移除冗余输入字段前先更新 TDD/验收及代码；当前不臆造 `operator_id` 的外部编码规则。

## 3. 固定接口调用契约

| API | 按钮记录 | Action | 对外调用 | 当前本地字段状态 |
|---|---|---|---|---|
| API02 | 入库 Order | `UPDATE` | `POST` / JSON / 配置的 API02 Endpoint | `receiptConfirmed` 与 Order 状态映射未确认；不发不完整 Payload |
| API04 | 入库 Order | `CREATE` | `POST` / JSON / 配置的 API04 Endpoint | 已从实际 picking/move line 取数并做 Mock 成功/失败重试；逐行操作人/时间必须来自已保存字段 |
| API06 | 出库 Order | `CREATE` | `POST` / JSON / 配置的 API06 Endpoint | 既有备货事件可识别；`palletQty` / `totalWeight` 实际聚合口径仍未确认，完整 Payload 不发送 |
| API08 | 出库 Order | `CREATE` | `POST` / JSON / 配置的 API08 Endpoint | `shipmentConfirmed` 与 Order 状态映射未确认；不发不完整 Payload |
| API10 | 客户盘点 Order | `Add` / `Del` | `POST` / JSON / 配置的 API10 Endpoint | 只从关联实盘结果中读取已选实际行；Action 匹配不区分大小写，发送规范化值 |

- 管理员配置完整 URL，含 Ginlong objectid；Ginlong 回传接口无需认证/Key 的事实来自用户提供资料。Ginlong→Odoo 入站仍复用 `worlddepot` API User/Token/权限。
- Header 固定 `Content-Type: application/json`，使用 Odoo `requests.post(..., json=payload, ...)`；同步调用，15 秒超时；不加入自动重试、队列、cron 或后台补偿。
- API10 的 `Add`/`Del` 按大小写不敏感比较。HTTP 成功状态仍须按 V3.2 回包字段处理：2xx 且 JSON `returnStatus` 为 `Y` 视为确认成功；响应解析失败、非 2xx 或其他返回状态记录失败。
- 不同接口分别处理 Open Items。已确认的 API04/API10 本地模拟不等待 API02/API06/API08 外部字段映射。

## 4. Payload 数据读取

### 4.1 API04 入库完成

- 主单字段来自对应 `world.depot.inbound.order`：货主和入库单号。
- 明细来自用户已保存选择的实际 `stock.picking.move_line_ids`；逐行读取 `lot_id.name`、实际 `quantity`、`product_id.default_code`、`result_package_id`（无结果包裹时读现有 `package_id`）。只处理具有实际数量的作业行，未选 picking 不进入 Payload；未选择任何 picking 时提示并停止发送。
- 每 SN 的 `operator` 与 `operationTime` 读当前已保存的 `ginlong_operator_code` / `ginlong_operation_time`；缺项时指出具体行并停止发送，不把 `date_done`、订单计划、picking 负责人或回传用户冒充现场事实。
- Ginlong Action 固定 `CREATE`。撤销和多批次范围遵守 V3.2 Open Items；本地按钮不自动撤销或推断增量/累计。

### 4.2 API10 盘点完成

- 主单字段来自 `world.depot.stocktake.order`：货主、盘点单号和已保存 Action。
- 明细只从 `order.result_ids` 中 `ginlong_callback_selected=True` 的既有实盘结果读取 SN、数量、托盘、产品编码和实际操作时间。
- 操作人实际关系 `operator_id` 保留为已有数据；Ginlong wire 的人员编码从已保存 `ginlong_operator_code` 读取。该字段为空时提示并阻止本次发送，不默认用登录用户、人员显示名称或计划人员补值。
- 未选实盘行时停止发送；不读取计划 JSON 生成结果，不访问 `stock.quant`，不做库存调整。
- `Add`、`Del` 与本次已选实盘行一起在业务 Form 保存。撤回的具体对象范围遵守 Ginlong 已确认语义；当前仅对用户显式选择的现有实际记录构造本地模拟。

### 4.3 Open Item 接口

- API02：保留 Order 状态来源，但未擅自将 Odoo 状态翻译为 `receiptConfirmed`。提示、日志和 Open Item 只提 API02。
- API06：识别现有备货完成信息与 actual picking/move line，但不增加状态门禁。必填 `palletQty` 与 `totalWeight` 没有获确认口径前，不以计划数或不明重量字段填充，不发送半成品。
- API08：保留 Order 发货业务状态来源；未确认 `shipmentConfirmed` wire 映射前不发送。
- API04/06/10 的逐行 `operator`、`operationTime` 必须是实际记录或明确的外部编码补充；不使用回传操作者/点击时间。

## 5. 日志与失败重试

- 复用 `world.depot.api.log`。每次调用按钮都创建独立新日志行，记录 Endpoint（脱敏后）、请求 JSON、HTTP 响应、状态码与错误；代码不得 write/unlink 之前的 API 日志。
- Endpoint 未配置、Payload 缺必填、传输异常、HTTP 非成功或响应无效时，当前 attempt 记失败并返回可理解提示；不触发后台重试。
- 用户编辑并保存 Form 后再次点击，会读取最新 ORM 值，并新增另一条日志；上一日志的请求、响应和结果不改变。
- URL userinfo 及敏感 query 值不得进入日志明文；不对业务 Payload 做整体脱敏。
- 不新增 attempt、回传状态、监控、告警、专用日志或认证模型。

## 6. 自动化测试输入与验证结果

依据 [CC-GIN-003 v1.2](../implementation/CC-GIN-003-v1.2.md) 的 CC-TEST-001–007。已运行测试详细命令和历史见 [ATR-GIN-003](../implementation/ATR-GIN-003.md)。本次最终有效的七项 Odoo post-tests 使用既有 `odoo.conf`、`venv`、`odooce_karlrapp`，0 failed / 0 error；包括 Form/Wizard 移除、API02/06/08 独立阻塞、API04 Mock 成功及失败后修改重试、API10 保存后重读/Add/Del、日志追加与凭据保护。

已完成的 Mock 证据不等于完整 Ginlong 契约通过：

| 接口/场景 | 当前状态 |
|---|---|
| 持久化 Notebook、无回传 Wizard、API04 / API10 Form 数据保存后重读 | 自动化通过 |
| API04 完整可用字段 Mock POST / 成功响应 / 失败修改重试 | 自动化通过；真实 Ginlong 未调用 |
| API10 从选中的实盘结果 Mock POST，Add/Del | 自动化通过；撤销/部分范围外部语义仍 Open |
| API02 `receiptConfirmed`、API06 `palletQty/totalWeight`、API08 `shipmentConfirmed` | 各自因具体字段映射/口径 Open Item 阻止发送并记录原因；不互相阻塞 |
| 完整浏览器人工操作、真实 Ginlong、生产 | NOT RUN；完整人工 WMS E2E 留最终集成 CC |
| CC-TEST-010/017/019 | 引用既有 ATR-RUN-026/014/016，通过且本次未重做 |
| 完整保留 WMS 回归 CC-TEST-024 | 按既有状态单独跟踪；本次回传测试不代替 |

## 7. 版本追踪

| 版本 | 日期 | 变更 | 状态 |
|---|---|---|---|
| v0.4 | 2026-11-18 | 原冻结设计基线，Wizard 业务数据确认界面 | Frozen with Open Items；保留原件 |
| v0.4.1 | 2026-11-18 | 回传 Base URL/无鉴权事实补充 | 历史事实补充；保留原件 |
| v0.5 | 2026-11-18 | 依用户确认改用标准持久化 Form/Notebook；明确最小持久化字段、已保存 ORM 读取、固定 POST/JSON/Action、追加式日志及逐接口 Open Items | 实施修订；待后续技术评审/冻结 |
