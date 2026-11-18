# Coding Contract：CC-GIN-004 v1.0

## 文档状态

| 项目 | 内容 |
|---|---|
| CC ID | CC-GIN-004 |
| 版本 | v1.0 Frozen |
| 状态 | Frozen — Human Review APPROVED；授权本地实施和自动化/Mock HTTP 测试 |
| 目标 | API09 只读库存查询；Ginlong 模块管理界面 |
| 上游需求基线 | [SRS ginlong_apis v1.0 Frozen](../requirement/SRS_ginlong_apis.md) |
| 上游技术基线 | [TDD v0.8 Frozen](../ginlong_apis/TDD-v0.8.md)（取代此前 v0.4 在本 CC 范围内的技术设计；历史版本保留） |
| 实施计划 | [Implementation Plan v1.6 Frozen](IMPLEMENTATION_PLAN_ginlong_apis-v1.6.md) |
| 前序工作 | CC-GIN-001、002、003 已关闭；不重做其验收范围 |
| 后续工作 | CC-GIN-005：本地集成及完整 UI/WMS E2E；CC-GIN-006：经授权的真实 Ginlong 联调 |
| 项目认知 | [PROJECT_COGNITION.md v2.4](../context/cognition/PROJECT_COGNITION.md) |
| 模板同步 | BLOCKED：模板源缺失；按已批准流程例外形成草案，不记为 PASS |
| 人工评审 | APPROVED；李建强（项目用户）；2026-11-18 |

Human Review 已批准本 CC、TDD v0.8 和 Plan v1.6；本版为冻结实施基线。Ginlong 货主标识必须使用货主编码；入库/出库单均为单货主单据，订单级货主编码适用于全部产品明细；产品按 `(ownerCode, productCode)` 识别，库存按 `(ownerCode, warehouseCode, productCode)` 区分。当前仅有一个本地仓库，无需 Ginlong 仓库编码映射；若以后扩为多仓，按 Ginlong 要求扩展既有仓库模型，不增加映射模型。API09 数量是 Odoo 当前库存记录所表达的实际物理在库量；现场出入库由 Karl Rapp 执行，Odoo 接收其结果并通过 `stock.picking` 和原生库存机制记账。具体实施依据见项目认知 v2.4。此处记录项目业务边界，不重开已关闭的 API01/03 CC。SRS v1.0、冻结 TDD v0.4 及历史 CC 不在本轮修改。

## 1. 目标与系统边界

本 CC 在现有 `ginlong_apis`/`worlddepot` 能力上补齐 API09 只读库存查询和管理入口。Ginlong 是业务指令来源；`worlddepot` 负责现有业务 Order、API 用户/Token 和盘点指令/实盘结果；Odoo `stock` 负责实际出入库记录及库存账；`ginlong_apis` 只承担 Ginlong 协议、数据转换、设置及接口调用。不得将其扩展为通用集成平台或重做 WMS。

API09 只能查询现有库存，不创建/修改/删除 `stock.quant`，不创建库存移动，不过账、不调整库存。读 API 日志属于既有审计能力，不改变库存业务数据。

## 2. 范围

### 2.1 本 CC 范围

- 核对 Ginlong V3.2 API09 字段和用户补充的接口对照资料，严格区分正式字段定义、示例字段和仍未定义的语义。
- 实现 API09 路由、请求解析、权限/认证及只读查询；`quantity` 返回实际物理在库量，不扣减预留量。请求、响应字段、按产品编码返回完整列表及不分页行为遵循最新 V3.2 正式字段表。
- 提供 Ginlong 独立管理入口，复用现有设置、`world.depot.api.log`、入库/出库/盘点/产品模型与现有按钮。
- 提供失败 API 日志到已有业务单据的定位能力；可恢复的源单据由用户打开后修正，并通过原有单据按钮人工重发。日志只追加，不修改既有请求/响应历史。
- 对新增视图、访问规则、过滤 Action 和定位能力执行 Odoo 自动化/组件验证。完整人工 UI/WMS E2E 按 CC-GIN-005 执行。

### 2.2 排除

- CC-GIN-001–003 已通过功能的重复实现或无关重构。
- 更改现有 WMS 库存计算、所有权规则、库存调整、订单流程或引入新的业务规则。
- 新建平行库存模型、API 日志模型、统一集成框架、监控/审批/状态机或不必要的映射层。
- 真实 Ginlong 网络调用、生产访问及真实环境联调；归 CC-GIN-006，且须有单独授权。
- 完整 WMS 人工端到端验收；归 CC-GIN-005。

## 3. API09 契约核对

### 3.1 有来源支持的资料

| 项目 | 当前有据内容 | 来源和限制 |
|---|---|---|
| 方向 | Ginlong → Odoo | SRS FR-GIN-009、V3.2 |
| Object ID / Route | `TPL_Stock_Query`；`/api/ginlong/TPL_Stock_Query` | 用户提供的 API 对照表；不把旧文档的历史缺项说明当作当前依据 |
| HTTP | POST；`Content-Type: application/json` | 用户确认的统一 HTTP 契约 |
| Action | 无 | 用户提供的对照表写明 N/A |
| 请求 | `owner`、`warehouse` 均必填，均为 `VARCHAR(40)`；请求不含 Action | V3.2 正式字段表及用户提供的 API 对照表 |
| 请求样例 | `{"owner":"CNSG001","warehouse":"SHANGHAI_WAREHOUSE_01"}` | V3.2 样例 |
| 响应 Header 字段 | `returnStatus`、`exceptionInfo` 均必填 `VARCHAR(40)`；`operationTime` 必填 `DateTime`；`owner`、`warehouse` 均必填 `VARCHAR(40)` | V3.2 正式字段表；不另立响应业务 Open Item |
| 响应明细 | `inventoryList` 按 `productCode` 列库存数量；每项 `productCode` 必填 `VARCHAR(40)`，`quantity` 必填 `DECIMAL(18,6)`，示例为 JSON number | V3.2 正式字段表及示例；返回指定 owner/warehouse 的完整产品库存列表 |
| 产品筛选/分页/扩展数量 | 请求不增加 `productCode` 筛选；不设计分页；不增加 available/reserved 等协议外字段 | 用户最新确认的 API09 契约修订 |

V3.2 样例中的 `operationTime` 为 `2026-06-01 14:30:25`，正式字段表列出的格式为 `DateTime(yyyy-MM-dd 00:00:00)`。字段类型/格式按正式字段表记录；样例差异作为资料呈现差异保留，不改变业务 Open Item 清单。V3.2 提及不同仓库可调用不同 URL，本 CC 的请求为必填 `warehouse`，不因此为 Odoo 增加按仓库配置 Endpoint 的功能。

### 3.2 WMS 数据来源及边界

| Ginlong 字段 | 现有模型字段 | 映射说明 |
|---|---|---|
| `owner` | `product.product.ginlong_owner_code`；`stock.quant.product_id` | 请求及库存隔离使用货主编码；以产品上的 Ginlong owner code + default_code 识别产品，不依赖货主名称或 `stock.quant.owner_id` 建映射 |
| `warehouse` | `stock.quant.location_id.warehouse_id`；当前唯一 `stock.warehouse` | 当前只有一个本地仓库，直接查询该仓库内部库位，不校验或映射 Ginlong 仓库编码；若未来多仓，按 Ginlong 要求扩展现有仓库模型，不建映射模型 |
| `inventoryList[].productCode` | `stock.quant.product_id.default_code`；`product.product.ginlong_owner_code` | 同一 `default_code` 可属于不同货主；库存结果必须按 owner code 与 productCode 同时区分，禁止只按 `default_code` 汇总或跨货主合并 |
| `inventoryList[].quantity` | `stock.quant.quantity` | Odoo 当前实存量；对同一 owner、warehouse、productCode 下的库存行汇总，不扣除 `reserved_quantity`。实际仓库作业结果由 Karl Rapp 返回后通过 Odoo `stock.picking` / 原生库存机制反映 |

现有 `worlddepot` 库存报表从 `stock.quant` 读取内部库位数量，可按 Odoo 仓库、库位和产品过滤，但没有 owner code 过滤或 Ginlong 汇总逻辑。本 CC 使用现有 `stock.quant` 数据源表达 Odoo 当前实际物理在库量；owner/product 以现有产品 `ginlong_owner_code + default_code` 识别，仓库限定为当前唯一仓库的内部库位，数量汇总 `stock.quant.quantity`，不使用 `quantity - reserved_quantity`。Ginlong 模块不独立执行收货、发货或库存移动；这些实际作业来自 Karl Rapp，Odoo 由 `stock.picking` 和原生库存机制记录。

当前单仓库不做仓库编码映射；API09 按该唯一 Odoo 仓库查询，响应中的 `warehouse` 回显请求编码。若未来增加仓库，再依据 Ginlong 当时的要求扩展现有 `stock.warehouse`，不新建映射模型。

### 3.3 只读约束

- API09 查询不得对库存模型调用 `create`、`write`、`unlink`，不得创建 `stock.move` / `stock.move.line`，不得调用调整/过账方法。
- 查询使用必填 owner 过滤现有 Ginlong 产品，并在当前唯一仓库的内部库位范围内读取 quant；不做仓库编码映射。
- 认证复用 `worlddepot` API User/Token 验证；请求、响应及错误复用现有 API logger，继续保护 Secret/Token。
- 不增设 API09 专属幂等、限流或认证框架；如 SRS/既有基线明确覆盖，则按既有能力验证，不另行实现。

## 4. 管理界面方案

### 4.1 菜单、Action、View 清单

| 管理入口 | 现有对象/候选 Action | 本 CC 最小变更 | 访问和范围约束 |
|---|---|---|---|
| Ginlong APIs（独立菜单） | 新建顶层入口，挂在现有 WorldDepot 菜单体系下 | 作为 Ginlong 相关设置、日志及业务查询入口；不改现有 WMS 顶层业务菜单 | 复用现有 Odoo 菜单组/用户组；Ginlong 日志查询复用 `stock.group_stock_manager` 只读权限；Settings 继续由 Odoo 系统管理员访问 |
| API Settings | 现有 `res.config.settings` / `ir.config_parameter`；复用现有 Ginlong APIs 设置区 | 从 Ginlong 菜单提供现有 Settings 入口；保留并管理现有回传 Endpoint 与 API01/03/05/07 限流设置，不增加每接口启用开关或新的配置模型 | 只提供现有配置项；如后续出现启用/停用需求，另行提出需求变更 |
| Ginlong API 日志 | 现有 `world.depot.api.log` | Ginlong 过滤查询；在现有日志模型增加单一业务记录 Reference 字段，回传日志可打开原单；日志只读 | 复用现有 `stock.group_stock_manager`，不新建角色 |
| 入库单查询 | `world.depot.inbound.order` 现有模型/Form/Action | 添加独立 Ginlong 查询 Action/菜单及必要列表列；保留原 Action 与原域不变 | 仅按已持久化 Ginlong 标识过滤；具体域按实际现有字段确认，不加 owner-product 校验 |
| 出库单查询 | `world.depot.outbound.order` 现有模型/Form/Action | 添加独立 Ginlong 查询 Action/菜单；保留原 Action 与原域不变 | 同上；继续从源单据使用原有回传按钮 |
| 盘点单查询 | `world.depot.stocktake.order` 现有模型/Action | 添加独立 Ginlong 查询 Action/菜单，复用指令及实盘结果页面 | 不访问 `stock.quant` 推算盘点结果；只查看现有盘点记录 |
| Ginlong 产品查询 | `product.product`，现有 WorldDepot 产品菜单目前为模板层级 Action | 提供 `product.product` 的 Ginlong 筛选 Action/列表入口，展示现有 Ginlong owner/product 字段；不新建产品模型 | 以已存在 Ginlong 字段过滤；若存量记录无法区分项目数据，先记录缺口，不扩大过滤域 |
| 失败日志返回业务单据 | 现有 API 日志行 + 原业务 Form/回传按钮 | 在同一日志模型增加最小可定位 Reference 字段，由现有出站调用写入；允许从日志打开源单据，修正后使用原按钮发送 | 不建日志副本或重发框架；不改写历史日志。入站失败若尚未创建单据，不伪造单据链接，关联留空 |

本 CC 只提供 Ginlong 管理菜单、现有 Settings 入口、日志查询、业务记录查询及失败日志定位。不创建独立监控平台、重发中心或新的管理流程；不增加订单复制/导入界面、JSON 编辑器、额外审批或业务状态门禁。业务用户不查看原始 JSON；管理员/技术人员按批准权限查看现有 API 日志。

### 4.2 失败定位与人工重发

出站回传失败时，日志必须能定位原入库/出库/盘点单据；用户打开原单、修正已持久化业务数据，再通过 CC-GIN-003 已实现的「回传锦浪」按钮发起新的尝试。每次尝试追加新的现有 API 日志记录，历史日志不得更新或删除。对于入站请求失败且没有成功创建订单的情况，来源 Reference 留空，不生成不存在的单据关联。

## 5. 验收条件

1. 请求严格使用必填 `owner`、`warehouse`；响应严格按 V3.2 字段表和 `inventoryList[productCode, quantity]` 结构；不增加请求产品筛选、分页或协议外数量字段。
2. API09 仅访问授权范围，认证拒绝、合法请求和格式错误均由 Mock/Odoo 自动化覆盖；现有认证、日志和凭据保护不回退。
3. 对查询前后库存量/记录数及 ORM 写操作进行断言，证明 API09 不创建、更新或删除库存/作业记录。
4. `quantity` 按实际物理在库量验收：读取 Odoo 当前实存量，按 `(ownerCode, warehouseCode, productCode)` 汇总，不减预留量；不得把可用量或 Ginlong 计划数量冒充物理库存量。
5. 管理菜单、现有 Settings 入口、日志、入库/出库/盘点/产品 Action 均可按批准权限访问；过滤结果只展示对应 Ginlong 范围，不改变原有 WMS 菜单、Action 或业务规则。
6. 现有 Endpoint 和限流设置可查看、保存和重新打开；本 CC 不增加启用开关或改变现有接口启用行为。
7. 日志查询只读；敏感凭据不显示；请求/响应内容仅对批准的管理/技术角色可见。
8. 对已有失败回传日志可打开正确业务单据；原单修改保存后经原回传按钮发送新请求，新日志追加、旧日志不变。无源业务单据的失败请求不得出现假链接。
9. 自动化/组件测试作为 CC-GIN-004 验收；完整人工 UI/WMS E2E 不在本 CC 判 PASS，留 CC-GIN-005。真实 Ginlong 联调留 CC-GIN-006。

## 6. API09 测试矩阵（草案）

所有项当前为 `Not Run`；只有具有已批准字段/口径的案例进入 PASS 判定。待确认项目保持 `BLOCKED / OPEN`，不得以 Mock 自定义规则充当契约。

| 测试 ID | 场景 | 预期 / 验收点 | 状态 |
|---|---|---|---|
| CC-TEST-025 | 路由及请求 | POST JSON 路由/Object ID 正确；`owner`、`warehouse` 均必填 VARCHAR(40)；无 Action、productCode 请求条件或分页字段 | Not Run |
| CC-TEST-026 | 认证及权限 | 复用现有 API User/Token；未授权请求不得读取库存；日志不记录凭据 | Not Run |
| CC-TEST-027 | 现有字段读取 | owner 由 `product.ginlong_owner_code` + `default_code` 区分；当前唯一仓库内部库位经 `location_id.warehouse_id` 查询；不校验或创建 Ginlong 仓库映射 | Not Run |
| CC-TEST-028 | 跨货主同码隔离 | 使用明确标记的 ORM 模拟库存夹具覆盖相同 productCode、不同 owner；查询分别返回各自数量，不按产品码单字段合并 | Not Run |
| CC-TEST-029 | V3.2 响应结构和类型 | 验证必需 Header 字段及 inventoryList 明细字段；`quantity` 输出 JSON number、DECIMAL(18,6)，不增加协议外字段 | Not Run |
| CC-TEST-030 | 完整、无分页产品列表 | 对指定 owner/warehouse 返回完整产品清单；不引入分页或请求 productCode 过滤 | Not Run |
| CC-TEST-031 | 实际物理库存数量 | 从 Odoo 当前库存记录读取对应 owner/warehouse/productCode 的物理数量；同组 `stock.quant.quantity` 汇总，不减 `reserved_quantity`。开发库无内部 quant 时使用明确标注的 ORM 模拟记录，不能宣称已验证 KR 同步 | Not Run |
| CC-TEST-032 | 库存严格只读 | 查询前后库存 ORM 快照一致；无 stock.quant create/write/unlink、无 move/adjustment/过账调用 | Not Run |
| CC-TEST-033 | 日志与异常 | 复用现有 API logger；凭据不进入日志；合法、验证失败及查询异常均可追踪 | Not Run |

## 7. 管理界面验收矩阵（草案）

| 测试 ID | 场景 | 预期 / 验收点 | 状态 |
|---|---|---|---|
| CC-TEST-034 | Ginlong 独立菜单 | 从 WorldDepot 入口进入；可访问现有 API Settings、Ginlong 日志和四类业务记录查询；原有 WMS 菜单行为不变 | Not Run |
| CC-TEST-035 | 现有 API Settings 入口 | 可查看、保存并重新打开现有 Endpoint/限流配置；无新增接口启用开关 | Not Run |
| CC-TEST-036 | Ginlong API 日志查询 | 可按 Ginlong 接口、结果和时间查阅现有日志；历史记录只读 | Not Run |
| CC-TEST-037 | 日志访问控制 | 为现有 `world.depot.api.log` 配置 `stock.group_stock_manager` 只读 ACL；其他用户无此模型读取权限，不新建角色体系 | Not Run |
| CC-TEST-038 | 失败回传定位 | 失败回传日志打开正确原单；修正后使用原按钮；新尝试追加日志且旧日志不变 | Not Run |
| CC-TEST-039 | 入站失败无单据 | 未创建订单时不出现伪造关联；可用日志请求业务键检索 | Not Run |
| CC-TEST-040 | 业务记录查询入口 | 入库、出库、盘点、产品记录均从现有模型查询；不改变原 Action/WMS 业务方法；不增加重发中心 | Not Run |

## 8. 冻结决策与未验证边界

| 项目 | 已冻结决定 |
|---|---|
| 仓库范围 | 当前单仓库直接读取唯一 Odoo 仓库的内部库位，不做 Ginlong 编码映射；未来多仓库时依 Ginlong 要求扩展现有仓库模型，不新增映射模型 |
| 货主/产品 | 使用现有 `product.product.ginlong_owner_code + default_code` 标识产品；库存按 owner、warehouse、product 三维隔离 |
| 日志业务关联 | 在现有 `world.depot.api.log` 增加 Ginlong `Reference` 字段；回传日志指向原业务单据；无已创建业务记录时保持空引用 |
| 日志读取权限 | 通过现有 ACL 赋予 `stock.group_stock_manager` 只读权限，不建新角色；Odoo Settings 仍受系统管理员权限控制 |
| 业务查询过滤 | 入库/出库订单按 `ginlong_owner_code`，盘点记录按既有 `owner_code`，产品按 `ginlong_owner_code` 查询 |
| 开发库库存数据 | 当前没有内部 quants；自动化通过明确标注的 ORM 模拟数据验证 API09。真实 KR 库存同步不在本 CC 验收，不宣称 PASS |

本 CC 冻结时没有尚待业务方决定的范围或协议事项。开发库没有实际库存数据、故 KR→Odoo 同步未被本 CC 验证，这是已知范围边界，不阻塞 API09 组件实现和标注明确的 ORM 模拟数据测试；若后续需要证明同步链路，须由 CC-GIN-005/006 按其范围另行验证。

## 9. 验证与关闭规则

- 本 CC 冻结时的测试矩阵均为 Not Run；实施和测试尚未开始。只读 ORM 基线核对已完成。
- API09 的请求/响应结构、owner/warehouse 查询条件及实际物理库存数量口径均可独立验收。实存量来自 Odoo 当前库存，按货主编码、仓库和产品编码区分；不得扣减预留量或将 Ginlong 计划数据作为库存。当前只有一个 Odoo 仓库，按冻结方案直接查询其内部库位；未来多仓时另按 Ginlong 要求扩展既有仓库字段。
- 管理界面可以独立完成并形成组件测试证据；但 CC-GIN-004 整体关闭须逐项判断冻结 CC 的强制范围，未通过或 BLOCKED 项须按批准的 CC 关闭规则处理，不得隐去。
- 保留模板同步 `BLOCKED` 历史和已批准流程例外，不标记为 PASS。
- 真实 Ginlong/生产接口访问仍未授权，不得访问。

## 10. 评审决定

| 项目 | 状态 |
|---|---|
| Human Review | APPROVED；李建强（项目用户）；2026-11-18 |
| Plan v1.6 | Frozen；Human Review APPROVED |
| TDD v0.8 | Frozen；Human Review APPROVED |
| CC-GIN-004 冻结 | Frozen v1.0 |
| 编码/测试授权 | 已授权：本地开发、Odoo 自动化/ORM、Mock HTTP |
| 真实 Ginlong/生产访问 | 未授权 |

## 修订记录

| 版本 | 日期 | 状态 | 说明 |
|---|---|---|---|
| v0.1 | 2026-11-18 | Draft | 初稿；保留历史审阅版本记录 |
| v0.2 | 2026-11-18 | Draft | 删除接口启用开关；精简管理入口；API09 Open Items 收敛；保留历史评审迭代记录 |
| v0.3 | 2026-11-18 | Draft | 纳入最新 API09 正式字段表：owner/warehouse 必填、完整产品列表、无分页；数量含义为唯一 API09 业务 Open Item |
| v0.4 | 2026-11-18 | Draft | 登记货主传编码而非名称；同产品码可跨货主重复，库存按 ownerCode+productCode 隔离；新增跨货主同码测试 |
| v0.5 | 2026-11-18 | Draft | 补充 Ginlong 入库/出库单均为单货主单据，订单级货主编码适用于全部明细；不重开 API01/03 已关闭范围 |
| v0.6 | 2026-11-18 | Draft | 明确 API09 quantity 为 Odoo 实际物理在库量，由 KR 实际作业经 stock.picking/原生库存机制反映，不扣预留量；删除 quantity 业务待决项；待 Human Review |
| v0.7 | 2026-11-18 | Draft | 加入实际只读 ORM 字段/数据核对结果；等待用户澄清单仓库和日志关联决策 |
| v1.0 | 2026-11-18 | Frozen | 纳入用户澄清：单仓库无需 Ginlong 仓库映射；多仓时按 Ginlong 要求扩展现有仓库；现有 API 日志增加业务记录关联；权限复用库存管理员组。Human Review APPROVED；授权本地实施和测试 |
