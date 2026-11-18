# Ginlong API 技术设计说明书（TDD）v0.9

| 项目 | 内容 |
|---|---|
| 文档编号 | TDD-GINLONG-API-001 |
| 版本 | v0.9 API09 货主/仓库字段来源修订及 CC-GIN-004 关闭基线 |
| 状态 | Frozen — Human Review APPROVED；模板同步例外仍 BLOCKED |
| 日期 | 2026-11-18 |
| 适用模块 | `ginlong_apis`、按需扩展的 `worlddepot` 现有记录 |
| 上游技术基线 | [TDD v0.4](TDD-v0.4.md) 与 [v0.4.1](TDD-v0.4.1.md) 历史保留 |
| 当前实施契约 | [CC-GIN-003 v1.4](../implementation/CC-GIN-003-v1.4.md)；[CC-GIN-004 v1.0 Frozen](../implementation/CC-GIN-004-v1.0.md)；[v1.1 关闭补充](../implementation/CC-GIN-004-v1.1.md) |
| 用户批准的对象边界 | [PROJECT_COGNITION.md v2.9](../context/cognition/PROJECT_COGNITION.md) |
| 外部资料 | [Ginlong V3.2 参数核对记录](V3.2参数核对记录.md) 与 V3.2 工作簿 |
| Human Review | APPROVED；李建强（项目用户）；2026-11-18；依据项目负责人 API09 数据来源决定及授权关闭 CC-GIN-004 |
| 模板同步 | BLOCKED：模板源缺失；沿用既有批准例外，不记为通过 |

> 本版本保留 v0.8 与更早版本，不覆盖历史；依项目负责人的后续明确决定，API09 货主编码经 `res.partner.ginlong_owner_code` 定位后，以 `stock.quant.owner_id` 隔离库存；仓库编码直接精确匹配现有 `stock.warehouse.code`，未知值拒绝查询。当前仅一个仓库，不建映射模型；若未来多仓，按 Ginlong 要求扩展现有仓库字段。此修订只校正 API09 本地数据来源和隔离规则，不扩展 CC 范围。模拟库存仍不证明 Karl Rapp 库存同步；真实 Ginlong/生产访问未执行。模板同步保持 BLOCKED。

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
- Inbound/Outbound Order 的现有 Form 增加 Notebook 页并保留对应 API 按钮。API04/06 的本次 picking 选择保存于现有 `stock.picking`；Order Notebook 展示并允许选中关联作业单，再打开作业单 Form 保存逐 SN 现场值于 move line。API10 的 Action、结果选择和需要的外部人员编码保存在既有 `world.depot.stocktake.order` / `.result` Form。
- 按钮方法不接受 Payload、前端临时输入或 JSON 编辑文本。Odoo 保存后，后端从 ORM 读取已保存值；若值尚未保存，不能从前端状态发送。
- JSON 只在后台构造。业务页面不显示或编辑 JSON；请求/响应仅进入现有 API 日志，供技术人员/管理员审阅。
- Form 中已有业务事实保持只读展示；只有实际业务记录缺失、V3.2 必填且已确定允许补充的值才提供持久化输入。

### 2.2 最小字段扩展

五个回传仍使用持久化 Form/Notebook；API02/08 按用户明确要求增加实际业务明细子表。其余能力继续扩展现有业务对象，不增加产品映射模型或通用集成层：

| 模型 | Ginlong 字段 | 实际用途 |
|---|---|---|
| `stock.move.line` | `ginlong_operator_code: Char` | 保存每条 API04/06 执行明细的实际操作人员对外编码；不得用 picking 负责人、创建人或点击回传用户代替 |
| `stock.move.line` | `ginlong_operation_time: Datetime` | 保存每条 API04/06 执行明细的真实操作时间；picking 完成时间不是逐 SN 时间，不自动复制到每一行 |
| `stock.picking` | `ginlong_callback_selected: Boolean` | 持久化订单下本次实际作业单选择；API04/06 读取已保存选中的 picking，不把未选作业混进本次回传 |
| `world.depot.stocktake.order` | `ginlong_api10_action: Selection(Add, Del)` | 保存 API10 本次操作；发送端允许大小写不一致并规范化为标准值 |
| `world.depot.stocktake.result` | `ginlong_callback_selected: Boolean` | 持久化本次 API10 的实际采集记录范围，支持部分采集/撤回时选择对应实际记录 |
| `world.depot.stocktake.result` | `ginlong_operator_code: Char` | 在 V3.2 要求字符串但现有实盘模型只有实际操作人关系 `operator_id` 时，保存其已确认的 Ginlong 人员编码。保留并展示原有 `operator_id`，不以回传用户替代 |
| `res.partner` | `ginlong_owner_code: Char` | 在现有货主档案保存 Ginlong owner code，供现有 WMS 项目货主消歧；不新增货主映射模型 |
| `ginlong.inbound.receipt.detail` | `order_id`、`move_line_id`、实际产品/SN/数量/托盘关联字段、`receipt_status` | 入库 Order 的持久化实际收货明细；实际事实引用所属 Order 的 stock move line，状态采用契约样例支持的 Y/N |
| `ginlong.outbound.shipment.detail` | `order_id`、`move_line_id`、实际产品/SN/数量/托盘关联字段、`shipment_status` | 出库 Order 的持久化实际发货明细；实际事实引用所属 Order 的 stock move line，状态采用契约样例支持的 Y/N |
| 出库 Order | 托盘数/毛重手工覆盖值及是否启用；自动托盘数、实际净重和有效总重量为 ORM 计算值 | 手工值持久化；关闭覆盖时按已保存实际作业数据计算；毛重默认使用实际净重 |
| `product.product` | 现有 `ginlong_owner_code`、`default_code` 与 Ginlong 产品属性 | API07 以 `(owner, productCode)` 查找/创建/更新；不新增映射模型 |

实际产品、SN、数量、托盘、实盘操作关系和实盘时间优先取现有模型字段。API10 不新建并行实盘模型、不访问 `stock.quant`。API02/08 的两个子表是本轮明确批准的实际收/发货业务细节，不作为库存账或第二套作业事实；其行引用现有 move line。如果后续证明现有数据已能提供外部操作人员编码，则移除冗余输入字段前先更新 TDD/验收及代码；当前不臆造 `operator_id` 的外部编码规则。

## 3. 固定接口调用契约

| API | 按钮记录 | Action | 对外调用 | 当前本地字段状态 |
|---|---|---|---|---|
| API02 | 入库 Order | `UPDATE` | `POST` / JSON / 配置的 API02 Endpoint | 从已保存收货明细与收货状态生成订单级 `receiptConfirmed`；所有明细均为 Y 才回传 Y，出现 N 时回传 N；明细混合 Y/N 时按用户决策阻止发送并记错误 |
| API04 | 入库 Order | `CREATE` | `POST` / JSON / 配置的 API04 Endpoint | 已从实际 picking/move line 取数并做 Mock 成功/失败重试；逐行操作人/时间必须来自已保存字段 |
| API06 | 出库 Order | `CREATE` | `POST` / JSON / 配置的 API06 Endpoint | 托盘数取本次已选实际 move line `package_id` 去重；手工托盘数优先；重量读取 `product.ginlong_weight` 并按实际数量计算；`palletQty`/`totalWeight` 按 DECIMAL(18,6) 的 V3.2 字符串示例序列化为规范化 JSON 字符串 |
| API08 | 出库 Order | `CREATE` | `POST` / JSON / 配置的 API08 Endpoint | 从已保存发货明细及状态生成订单级 `shipmentConfirmed`；所有明细均为 Y 才回传 Y，出现 N 时回传 N；明细混合 Y/N 时按用户决策阻止发送并记错误 |
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

- API02：从持久化收货明细的状态生成接口字段。所有明细状态相同时发送该状态；同一订单出现混合 Y/N 时不发送并记录错误。取消控制/取消回传不属于本次实施。
- API06：识别既有备货完成事件，不增加状态门禁。托盘数为已选实际备货 `stock.move.line.package_id` 去重计数，保存的手工覆盖值优先。V3.2 API07 的产品重量写入现有 `product.ginlong_weight`，故按该产品档案单件重量乘实际数量；毛重默认净重并可覆盖。用户确认 `palletQty` 和 `totalWeight` 以 JSON string 发送，按 DECIMAL(18,6) 规范化到最多六位小数。
- API08：从持久化发货明细状态生成接口字段。所有明细状态相同时发送该状态；同一订单出现混合 Y/N 时不发送并记录错误。取消控制/取消回传不属于本次实施。
- API07：允许不同货主使用相同 `productCode`，产品业务键为 `owner + productCode`。现有 Hoymiles/OFoundation WMS 代码查找调用共享 resolver：唯一编码保持原行为；重复编码按项目 owner 的 Ginlong owner code 定位；无法唯一定位时明确报歧义，不任取首条。服务与 resolver 自动化覆盖同码跨 owner 创建、查询、更新和 API01/03 产品定位。
- API04/06/10 的逐行 `operator`、`operationTime` 必须是实际记录或明确的外部编码补充；不使用回传操作者/点击时间。

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

## 7. API09 与 Ginlong 管理界面（CC-GIN-004 修订）

### 7.1 API09 数据语义与来源

- Ginlong V3.2 API09 请求必填 `owner`、`warehouse`；响应为完整 `inventoryList`，明细字段为 `productCode` 与 `quantity`，不分页、不增加请求产品过滤或协议外字段。
- `quantity` 定义为 Odoo 当前库存记录所表达的**实际物理在库数量**。查询 `stock.quant.quantity`，不减 `reserved_quantity`，不以可用量代替，不执行任何库存写入或库存移动。
- 结果按 `(ownerCode, warehouseCode, productCode)` 区分和汇总。跨货主即使 `default_code` 相同也不得合并。
- Karl Rapp WMS 执行现场作业并提供结果；Odoo 接收结果并由既有 `stock.picking` / 原生库存机制记录。此设计只读取 Odoo 已有库存记录；不实现或假定 Karl Rapp 库存同步已完成。

只读源码和 Odoo ORM 检查（数据库 `odooce_karlrapp`，未写入数据，结束时回滚）发现：

| 对象 | 源码/Registry 可用字段 | 当前开发库实际数据 | 结论 |
|---|---|---|---|
| 货主 | `res.partner.ginlong_owner_code`；`stock.quant.owner_id` 关联 `res.partner` | 开发库当前无 Ginlong owner partner、内部 quants 为 0 | API09 先以请求 owner code 精确查找 partner，再以其 ID 过滤 `stock.quant.owner_id`；不存在的 owner 返回空清单，绝不回退到其他货主 |
| 仓库 | `stock.warehouse.code`；内部库位通过 `view_location_id` 界定 | 当前仅 1 个仓库：`KRWH` / `KarlRapp-WH` | API09 按请求 warehouse code 精确匹配现有仓库；未知编码返回校验错误且不回退到其他仓库。当前不建映射模型；未来多仓时按 Ginlong 要求扩展现有仓库字段 |
| 产品 | `product.product.default_code`、`ginlong_owner_code` | 8 个产品有 Ginlong owner code，当前均为 `2110`；无跨 owner 同码样本 | 产品编码字段存在；真实跨货主库存隔离尚无开发库数据证明 |
| 库存 | `stock.quant.quantity`、`reserved_quantity`、`location_id`、`owner_id`、`product_id` | 当前内部 `stock.quant` 为 0 | 货主维度由 `stock.quant.owner_id` 与 `res.partner.ginlong_owner_code` 匹配；产品按 `product_id.default_code` 返回。模拟夹具验证隔离，未验证真实库存或 KR 同步 |

源码核对还发现，现有 `worlddepot` `/my/stock_report` 只筛内部库位，并可按 Odoo `warehouse_id`、location、product 过滤，直接搜索 `stock.quant`，没有 Ginlong owner 隔离。本设计按项目负责人决定以 `res.partner.ginlong_owner_code` 定位 partner，并用 `stock.quant.owner_id` 限定该货主库存；响应产品编码来自 quant 产品的 `default_code`。API07 产品主数据仍按 `owner + productCode` 识别，但 API09 库存所有权以 quant 的 owner 关系为准，不从 product owner 字段推算或跨货主合并。

API09 先精确查找 `res.partner.ginlong_owner_code`，再按 `stock.quant.owner_id` 过滤；对指定 `warehouse` 精确查找一个 `stock.warehouse.code`，不存在或不唯一时拒绝请求，不能回退到唯一仓库。当前数据库字段 `stock.warehouse.code` 为短码；本地测试验证匹配短码及未知值隔离，不声称任意 40 字符 Ginlong 仓库码已联调兼容。响应回显请求中的 owner、warehouse；不以显示名称匹配或跨货主合并。

### 7.2 API09 只读实现约束与组件验证

- 请求以 Ginlong owner code 查找 `res.partner.ginlong_owner_code`，并以 partner ID 过滤 `stock.quant.owner_id`；仓库参数精确匹配现有 `stock.warehouse.code`，未知值拒绝。产品编码取 `stock.quant.product_id.default_code`。不增加映射模型。
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
