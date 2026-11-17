# Ginlong API 技术验证报告（TV）

| 项目 | 内容 |
| --- | --- |
| 文档编号 | TV-GINLONG-API-001 |
| 项目 | `ginlong_apis` |
| 版本 | 0.2 |
| 状态 | **Approved with Conditions（有条件通过；TV 未冻结）** |
| 验证日期 | 2026-11-16 |
| 需求基线 | [SRS-GINLONG-API v1.0 Frozen](../../requirement/SRS_ginlong_apis.md) |
| 总体结论 | **有条件通过** |
| 评审/批准 | 2026-11-16：用户批准有条件通过，并授权进入 TDD 起草阶段；不授权编码或冻结 TDD |

### 修订记录

| 版本 | 状态 | 修订内容 |
| --- | --- | --- |
| 0.1 | Review Draft | 初版 TV，基于 `worlddepot`、Odoo 核心源码及 Ginlong V3.1 字段清单形成静态验证结论。 |
| 0.2 | Approved with Conditions | 按新的对象映射方向重做：01/02/04 对接入库 order，03/06/08 对接出库 order，05/10 建议独立盘点任务/采集结果模型，07 对接产品模型，09 查询 `stock.quant`。明确 05/10 不读写 `stock.quant`，不推定盘点结果触发库存调整。2026-11-16 经用户批准有条件通过，进入 TDD 起草；TV 本身不冻结。 |

> 本报告记录源码和静态环境验证结果，不是 TDD，也不冻结 TV。用户批准范围仅为有条件通过及进入 TDD 起草，不包括编码或 TDD 冻结。Ginlong 外部协议和业务规则仍以双方正式确认资料为准。接口 03 仅依 SRS A-003 作为可替换的开发假设。

本版将“盘点任务/采集结果单独建模；入库/出库订单类接口映射现有 inbound/outbound order”作为 TV 建议。接口 05/10 不映射到 `stock.quant`，也不从其字段推定对 `stock.quant` 的读写或库存过账；接口 07 映射产品模型，接口 09 才查询 `stock.quant`。模型细节仍由 TDD 决定。

## 1. 摘要结论

Odoo 18 CE 的 `worlddepot` 已有入库单、出库单、库存查询、物料扩展字段，以及用户点击按钮后生成 Payload、调用外部接口并记录尝试结果的代码基础。现有 API 与回传实现主要绑定 Hoymiles；静态搜索没有发现 Ginlong/Solis 专用接口路由。现有模型和模式可作为 Ginlong 集成的复用基础，但不能直接视为 Ginlong 接口实现。

`worlddepot` API 用户、bcrypt Secret 校验、Token 发放/过期校验和 API 日志模型在源码中可见。不过，现有认证协议是否兼容 Ginlong 尚无法判断；认证入口日志会保存原始请求和响应，源码路径可将 API Secret 与 Access Token 一并写入日志。凭据日志问题须在真实联调前处理。权限边界、用户组和记录规则未在运行时验证。

因此，本 TV 对该对象映射方向给出**有条件通过**：01/02/04 可围绕现有入库 order 组织集成，03/06/08 可围绕现有出库 order 组织集成；05/10 应由独立盘点任务/采集结果模型承载。Ginlong 工作簿没有规定这两个接口读写 `stock.quant` 或触发库存过账，本 TV 不推定这些操作。07 映射产品模型，09 查询 `stock.quant`。Ginlong 路由、字段映射、认证适配、业务关联日志及盘点任务/结果关联需设计/扩展；目标数据库中的安装/权限行为、真实接口集成和合同外语义仍待运行时或外部资料验证。

## 2. 范围、方法与限制

### 2.1 验证范围

- 检查 Odoo 18 CE 项目内 `mymodules/worlddepot` 的 WMS 模型、字段、控制器、回传方法、库存及产品扩展。
- 检查现有 API 用户、Secret、Token、权限配置和日志代码，判断其作为 Ginlong 接口基础的适配可行性。
- 将 V3.1 工作簿中接口 01–10 的现有字段清单与源码能力逐类比对。
- 验证 02/04/06/08/10 的人工按钮调用模式；本 TV 不增加自动触发或后台自动重试。
- 评估将接口 05/10 置于独立盘点单模型、将其他订单类接口接入现有入库/出库 order 的适配依据；该评估不冻结最终模型设计。
- 识别幂等、映射、分批、异常恢复及资料缺失对技术设计的影响。

### 2.2 方法与实际结果

| 方法 | 实际结果 |
| --- | --- |
| 检查项目版本 | `./odoo-bin --version` 返回 `Odoo Server 18.0`。 |
| 静态阅读 | 阅读 `worlddepot` 的入库/出库模型、状态扩展、Hoymiles 控制器、API 用户/Token/日志、库存报告、产品扩展及视图/ACL。 |
| 检查接口字段来源 | 阅读 `docs/ginlong_apis/海外WMS与第三方系统集成V3.1.xlsx` 的“海外WMS与第三方系统的接口与处理逻辑”工作表及相关字段行；没有将“与海航（英国）联调进度”工作表作为 Ginlong 验收证据。 |
| 静态语法/结构检查 | Python AST：53 个 `worlddepot` Python 文件，0 个解析错误。XML：入库单、出库单、API 用户、API 日志 4 个视图文件均可解析。 |
| Ginlong 路由搜索 | 在 `worlddepot/controllers` 与 `worlddepot/models` 中搜索 Ginlong/Solis，未找到对应接口实现。 |
| 运行时/生产数据 | 检出树包含 `addons/stock` 核心源码；本次只将 `stock.quant` 作为接口 09 库存查询的候选数据来源进行静态检查，未将原生盘点流程用于接口 05/10。未连接数据库、未升级模块、未写入业务数据。没有可确认的测试数据库和 Ginlong 测试端点/凭据；因此未执行 ORM、模块升级或真实 API 调用，无法确认当前目标数据库的模块安装/配置状态。 |

静态解析只证明源文件可以被解析，不证明 Odoo 模块可安装、数据库模型已注册或业务流程可运行。视图 XML 检查不等于完整 Odoo View 校验。

### 2.3 项目工作流状态

TV 指南说明 TV 不要求固定模板；每项重要验证应记录问题、方法、结果、证据和 TDD 影响。项目模板同步脚本 `python3 docs/skill/odoo-project-workflow/scripts/check_template_sync.py --repo-root /Users/lijianqiang/Documents/odoo18ce_karlrapp --template technical-verification` 返回 `BLOCKED：找不到项目模板来源`。用户已批准 v0.2 有条件通过并进入 TDD 起草；由于模板来源仍缺失，TV 保持未冻结状态，仅作为本次 TDD 起草的已批准技术输入，不宣称为 Frozen 基线。

## 3. 技术验证事项

### TV-001 — WMS 模型与 10 个接口字段映射

**Question**  
订单类接口能否映射现有入库/出库 order；盘点接口是否需要独立单据模型；产品与库存接口应使用什么现有业务对象？

**Method**  
静态检查 `world.depot.inbound.order`、`world.depot.outbound.order`、产品扩展、包装记录、库存报告及 Hoymiles 入库控制器；按工作簿逐接口字段范围对照。

**Result — VERIFIED（现有模型/结构事实）；映射覆盖 INCONCLUSIVE（运行时和完整逐字段语义未验证）**

**Evidence**

- 入库单含 project、owner（由 project 关联）、warehouse、reference、状态、入库产品关系和 stock picking 关系；入库明细具有托盘/产品层级。[`inbound_order.py`](../../../mymodules/worlddepot/models/inbound_order.py#L10-L105) [`inbound_order.py`](../../../mymodules/worlddepot/models/inbound_order.py#L592-L634)
- 出库单含项目、货主、仓库、收货公司、地址/联系方式、reference、产品明细和 picking 关联。[`outbound_order.py`](../../../mymodules/worlddepot/models/outbound_order.py#L19-L55) [`outbound_order.py`](../../../mymodules/worlddepot/models/outbound_order.py#L82-L105) [`outbound_order.py`](../../../mymodules/worlddepot/models/outbound_order.py#L121-L145)
- 订单字段结构支持将 01/02/04 映射到现有入库 order，将 03/06/08 映射到现有出库 order；其间仍需要字段转换及 Ginlong endpoint，不是直接复用现有 Hoymiles API。
- `stock.quant` 的源码只作为接口 09 库存查询能力证据；05/10 不使用该模型作为盘点任务或采集结果对象。[`stock_quant.py`](../../../addons/stock/models/stock_quant.py#L46-L93)
- 出库包装模型含包件编号/数量、尺寸（cm）、体积（m³）、毛重、净重及包内产品。[`outbound_order_pack_info.py`](../../../mymodules/worlddepot/models/outbound_order_pack_info.py#L35-L73)
- 产品档案扩展覆盖部分 Ginlong 属性，如危险品、UN 编码、每托数量、品牌、重量、尺寸；导入暂存模型另含商品名、条码、追踪方式、HS 编码等字段。它们不等于工作簿全部物料字段的已确认语义映射。[`product_template.py`](../../../mymodules/wd_product_profile/models/product_template.py#L5-L15) [`my_product_template.py`](../../../mymodules/worlddepot/models/my_product_template.py#L5-L27)
- 现有入库控制器按 `barcode` 或 `default_code` 找产品，再通过 ORM 创建 WMS 入库单及托盘/产品行，是可参考的转换模式；该控制器是 Hoymiles 路由，不是 Ginlong 契约或 Ginlong 业务服务。[`inbound_controller.py`](../../../mymodules/worlddepot/controllers/hoymiles/inbound_controller.py#L12-L18) [`inbound_controller.py`](../../../mymodules/worlddepot/controllers/hoymiles/inbound_controller.py#L28-L45) [`inbound_controller.py`](../../../mymodules/worlddepot/controllers/hoymiles/inbound_controller.py#L69-L101)
- 工作簿接口 03 的产品包装尺寸以 mm 表达，而现有包装记录字段以 cm 表达；需要在 TDD 明确并以确认契约校验单位换算。不能静默沿用字段单位。

**TDD Impact**  
以 `world.depot.inbound.order` 承接 01/02/04，以 `world.depot.outbound.order` 承接 03/06/08；05/10 建议新建独立盘点任务/采集结果模型，保存 Ginlong 盘点单头、产品/SN/托盘明细和采集回传所需操作信息。05/10 不以 `stock.quant` 为数据对象，也不由 TV 推导库存调整行为。07 对接产品模型，09 从 `stock.quant` 查询。逐接口建立来源字段→目标模型/字段→转换/校验→结果的映射；货主、仓库、产品编码和单位/尺寸换算需要明确，不能直接复用 Hoymiles 契约。

### TV-002 — API 身份验证、Token、权限与日志

**Question**  
`worlddepot` 认证、Token、权限及日志能力能否复用于 Ginlong？

**Method**  
检查 API 用户/Token 模型、认证控制器、Token 装饰器、日志装饰器、日志视图和 ACL CSV。

**Result — 现有组件 VERIFIED；Ginlong 兼容性 INCONCLUSIVE；凭据安全缺口 VERIFIED**

**Evidence**

- API 用户有 API Key、bcrypt hashed Secret、active、关联 Odoo user 和 project；API Secret 最低长度检查后以 bcrypt 存储。Token 模型持有 token 字符串和 expires 字段。[`my_api_user.py`](../../../mymodules/worlddepot/models/my_api_user.py#L10-L45) [`my_api_user.py`](../../../mymodules/worlddepot/models/my_api_user.py#L69-L97) [`my_api_user.py`](../../../mymodules/worlddepot/models/my_api_user.py#L107-L119)
- 认证端点校验 API Key/Secret，创建 32 字节 URL-safe Token，设置一小时有效期。Token 装饰器接受 Bearer 或原始 Token，检查过期并设置请求用户。[`auth_controller.py`](../../../mymodules/worlddepot/controllers/auth_controller.py#L11-L69) [`validator_token.py`](../../../mymodules/worlddepot/controllers/validator_token.py#L11-L67)
- 认证端点使用 `api_logger`。装饰器将原始 HTTP 请求体保存为 request_data、将接口返回值 JSON 化保存为 response_data；故认证请求中的 `api_secret` 和成功响应中的 `access_token` 会进入该日志路径。[`auth_controller.py`](../../../mymodules/worlddepot/controllers/auth_controller.py#L14-L16) [`api_logs.py`](../../../mymodules/worlddepot/controllers/api_logs.py#L98-L120) [`api_logs.py`](../../../mymodules/worlddepot/controllers/api_logs.py#L163-L184)
- Token 无效/过期时，当前装饰器把 Token 值写入应用日志；Token 记录存储明文 Token。Token 校验时未见对 `api_user.active` 的逐请求复查；Token 记录关联的是 Odoo user，随后按 user 搜索 API user。[`validator_token.py`](../../../mymodules/worlddepot/controllers/validator_token.py#L33-L64) [`my_api_user.py`](../../../mymodules/worlddepot/models/my_api_user.py#L107-L119)
- Hoymiles 出站 OAuth Token 获取属于另一套出站鉴权组件，不等同于上述入站 API Key/Token 流程。Ginlong 的出站认证方式尚无正式契约。
- ACL CSV 明确列有 Hoymiles 日志模型权限行，但未看到 API 用户、Token、通用 `world.depot.api.log` 的专用 ACL 行；视图/菜单可见性和实际 record rule、运行用户权限未通过数据库验证。[`ir.model.access.csv`](../../../mymodules/worlddepot/security/ir.model.access.csv#L1-L13) [`my_api_user.xml`](../../../mymodules/worlddepot/views/my_api_user.xml#L1-L55) [`api_logs.xml`](../../../mymodules/worlddepot/views/api_logs.xml#L1-L50)

**TDD Impact**  
可将现有 API 用户和 Token 机制列为候选复用组件，但须先对照 Ginlong 已确认的鉴权方式。日志实现需先设计凭据排除/遮蔽策略；不得照搬当前认证端点的原始请求/响应日志行为。TDD 还需明确 project/owner/warehouse 授权边界、停用 API 用户后既有 Token 的行为及 Token 生命周期。运行时 ACL/record rule 需在测试库验证。

### TV-003 — 入站接口与库存查询

**Question**  
入站订单、盘点单、物料主数据和库存查询分别适配到哪些现有 Odoo 对象，哪些对象需要新增关联？

**Method**  
检查 Hoymiles 入库/出库控制器、入库/出库模型、物料档案、stock.quant 查询和现有库存报表；检查项目中是否已有 count 单据/ Ginlong 路由。

**Result — 订单模型、产品模型和接口 09 库存查询能力 VERIFIED（源码层面）；Ginlong 请求端到端处理 INCONCLUSIVE；05/10 建议独立建模**

**Evidence**

- 01 的入站数据可映射 `world.depot.inbound.order` 及其产品/托盘层级；现有 Hoymiles controller 展示查产品并创建订单的路径，但没有 Ginlong route，也未覆盖 Ginlong 删除语义和完整字段映射。[`inbound_order.py`](../../../mymodules/worlddepot/models/inbound_order.py#L10-L105) [`inbound_controller.py`](../../../mymodules/worlddepot/controllers/hoymiles/inbound_controller.py#L22-L45) [`inbound_controller.py`](../../../mymodules/worlddepot/controllers/hoymiles/inbound_controller.py#L69-L101)
- 03 的待出库数据可映射 `world.depot.outbound.order` 及收件方、产品/包装字段；没有 Ginlong route。方向仍按 SRS A-003 临时假设，不能视为外部契约。包装尺寸字段的 cm/mm 差异须在映射中处理并验证。[`outbound_order.py`](../../../mymodules/worlddepot/models/outbound_order.py#L19-L55) [`outbound_order.py`](../../../mymodules/worlddepot/models/outbound_order.py#L82-L105) [`outbound_order_pack_info.py`](../../../mymodules/worlddepot/models/outbound_order_pack_info.py#L35-L73)
- 05：工作簿定义 Solis 下发盘点单，Odoo 侧创建/删除，并以 `countOrderNo` 为唯一主键；字段包括 owner、warehouse、remark、product 明细及 SN/quantity/palletCode 列表，删除前需确认整单未操作。`worlddepot` 未发现相应 Ginlong 盘点单据，故建议新建独立盘点任务模型。该单据是盘点任务/范围载体，不等同库存 quant 或库存调整。
- 10：工作簿回传 `countOrderNo` 和已采集 SN、数量、托盘、产品、操作人及操作时间；SRS 要求用户手动点击盘点完成按钮。按钮和结果记录应归属独立盘点任务/采集结果模型；不从接口字段推导读写 `stock.quant` 或库存过账。
- 工作簿一处描述 Solis 支持同一盘点单分批采集，一处又规定第三方在整单采集完成时调用接口；分批何时回传、是否允许多次提交、撤销删除的范围仍有语义待确认，本 TV 不补造规则。
- 07 应映射产品模型而非 order。现有 `product.template` 扩展和导入暂存能力只能覆盖部分 Ginlong 属性；完整字段、货主+物料编码唯一性和新增/修改规则还需映射/扩展。[`product_template.py`](../../../mymodules/wd_product_profile/models/product_template.py#L5-L15) [`my_product_template.py`](../../../mymodules/worlddepot/models/my_product_template.py#L5-L27)
- 通用库存页按 stock.quant 搜索内部库位，并可按仓库、库位、产品过滤；没有货主条件，也不是面向 Ginlong 的接口。[`my_report.py`](../../../mymodules/worlddepot/models/my_report.py#L9-L49)
- 名为 Linglong 的库存报告通过 stock.move 计算期初/入库/出库/在手数量，但筛选硬编码产品分类 ID 11，并非通用当前库存 API，不能直接作为接口 09 的数量口径。[`my_stock_report_linglong.py`](../../../mymodules/worlddepot/models/my_stock_report_linglong.py#L58-L78) [`my_stock_report_linglong.py`](../../../mymodules/worlddepot/models/my_stock_report_linglong.py#L102-L146) [`my_stock_report_linglong.py`](../../../mymodules/worlddepot/models/my_stock_report_linglong.py#L259-L271)

**TDD Impact**  
在 TDD 中按对象边界分组：01/02/04 使用现有 inbound order；03/06/08 使用现有 outbound order；05/10 使用独立盘点任务/采集结果模型；07 使用产品模型；09 查询 `stock.quant`。05/10 的接口对象不映射到 `stock.quant`；是否存在其他库存业务服务关联，按冻结 SRS 澄清后再定，不能由 Ginlong接口字段或本 TV 推导。

### TV-004 — 五个人工回传按钮

**Question**  
接口 02/04/06/08/10 能否采用用户手动点击相应 Odoo 业务对象按钮生成 Payload、调用接口并留痕？

**Method**  
检查入库/出库状态扩展中的按钮方法、视图、Payload 组装、HTTP 调用、结果字段及日志写入。

**Result — 手动 UI/HTTP/结果模式 VERIFIED；Ginlong Payload 与响应兼容性 INCONCLUSIVE**

**Evidence**

- 入库单存在人工确认和入库结果方法；按现有 picking/move 数据生成 Payload，调用 Hoymiles URL，写每次请求/响应日志并更新当前成功/时间/错误字段。[`inbound_order_status.py`](../../../mymodules/worlddepot/models/inbound_order_status.py#L59-L125) [`inbound_order_status.py`](../../../mymodules/worlddepot/models/inbound_order_status.py#L192-L280)
- 出库单存在备货完成与发货结果方法；出库结果根据已完成的 picking/move 汇总行项目，调用外部 URL并记录响应；表单视图有对应 object 按钮及状态展示字段。[`outbound_order_status.py`](../../../mymodules/worlddepot/models/outbound_order_status.py#L252-L340) [`outbound_order_status.py`](../../../mymodules/worlddepot/models/outbound_order_status.py#L815-L935) [`outbound_order.xml`](../../../mymodules/worlddepot/views/outbound_order.xml#L232-L314)
- 现有这些页面及方法按 Hoymiles 项目/权限组显示或执行；不是 Ginlong 按钮。每次调用的 API 日志提供逐请求留痕，但业务单据上的 Boolean/时间/错误字段主要表示最近状态，不能代替完整的按单据回传历史。[`outbound_order.xml`](../../../mymodules/worlddepot/views/outbound_order.xml#L232-L314) [`outbound_order_status.py`](../../../mymodules/worlddepot/models/outbound_order_status.py#L79-L99)
- 05/10 的按钮对象应归属建议新增的盘点任务/采集结果模型；02/04 属于 inbound order，06/08 属于 outbound order。10 仍须由用户手动点击。05/10 只承载盘点任务及采集结果；本 TV 不将其映射到库存现存量或定义库存过账动作。
- 现有方法包含 Hoymiles 自己的业务前置逻辑（如已完成 picking 检查）。这些逻辑不应自动复制到 Ginlong；SRS v1.0 对回传按钮只批准权限、安全、数据完整性和格式校验。
- 出库结果当前把聚合数量转换为 `int`；Ginlong 数量精度/单位须按确认契约核对，避免小数数量被截断。[`outbound_order_status.py`](../../../mymodules/worlddepot/models/outbound_order_status.py#L861-L887)

**TDD Impact**  
复用“表单按钮→准备数据→外部调用→逐次结果留痕”的模式，不复用 Hoymiles Payload、URL、OAuth、项目过滤条件或状态拦截。02/04/06/08/10 均须由用户手动触发；重试也由用户点击。审计记录需绑定操作人、时间、接口编号、业务单据、Payload/关联信息和本次结果，并与凭据安全要求一致。

### TV-005 — 幂等、分批、异常恢复和外部依赖

**Question**  
现有代码能否证明 Ginlong 对重复、分批、未知结果和恢复的处理语义？

**Method**  
检查现有唯一性约束、重复单据检查、分批/结果聚合、API 日志及 SRS OPEN 条目；核对 Ginlong 文档/测试环境可用性。

**Result — INCONCLUSIVE（缺少 Ginlong 契约和运行环境）**

**Evidence**

- 入库模型按 project + reference 约束有效单据唯一；现有 Hoymiles 入库/出库 API 在控制器内做的重复 reference 查询未包含 project 条件。二者范围不一致，不能直接作为 Ginlong 幂等规则。[`inbound_order.py`](../../../mymodules/worlddepot/models/inbound_order.py#L160-L173) [`inbound_controller.py`](../../../mymodules/worlddepot/controllers/hoymiles/inbound_controller.py#L41-L45) [`outbound_controller.py`](../../../mymodules/worlddepot/controllers/hoymiles/outbound_controller.py#L41-L45)
- 出库结果方法把已完成 picking 名称合并并汇总产品数量；这仅证明现有 Hoymiles 实现有聚合路径，不能证明 Ginlong 批次键、部分完成、去重或撤销语义。[`outbound_order_status.py`](../../../mymodules/worlddepot/models/outbound_order_status.py#L815-L887)
- SRS OPEN-GIN-004/006/007/008/012 将协议、部分作业、幂等/结果未知、库存口径、同步/异步列为外部确认或 TV/TDD 项；本次未获得 Ginlong API 契约、测试地址或凭据。
- 当前通用 API 日志的 status 是 success/error；WMS 入库单另有 state/status，手动回传另有成功/时间/错误字段。静态源码未发现将请求接收、业务处理和 Ginlong 回传确认作为三个阶段分别关联到同一外部请求/业务单据的跟踪记录。[`api_logs.py`](../../../mymodules/worlddepot/controllers/api_logs.py#L11-L29) [`inbound_order.py`](../../../mymodules/worlddepot/models/inbound_order.py#L75-L105) [`outbound_order_status.py`](../../../mymodules/worlddepot/models/outbound_order_status.py#L79-L99)

**TDD Impact**  
不得把现有 reference 检查、分批聚合或超时行为写成 Ginlong 事实。TDD 应将幂等键/重复请求、回传结果未知后的人工核对、部分批次与撤销、删除后重建、超时及恢复路径作为设计输入；凡依赖外部语义的决定须等正式确认。

## 4. 十个接口逐项技术结论

工作簿行号指“海外WMS与第三方系统的接口与处理逻辑”工作表对应接口内容；字段类型、必填、枚举及完整数据样例需以 Ginlong 版本化契约补齐。

| 接口 | 方向（按 SRS）与工作簿范围 | 现有 Odoo 证据/缺口 | 技术结论 |
| --- | --- | --- | --- |
| 01 待入库单 | Solis→Odoo；行 5–20。入库单、货主/仓库、产品、托盘/SN 等 | `world.depot.inbound.order` 和托盘/产品层级存在；Hoymiles 控制器有映射/建单范式。需增加 Ginlong route、删除/修改映射及外部字段配置。 | **需扩展**；接入现有 inbound order。 |
| 02 收货确认 | 用户手动 Odoo→Solis；行 21–23 | 已有入库单确认回传按钮模式，但绑定 Hoymiles。 | **需扩展**；按钮归属 inbound order，手动触发。 |
| 03 待出库单 | SRS A-003 开发假设 Solis→Odoo；行 33–66 | `world.depot.outbound.order` 有收件方、地址、产品/包装层级；无 Ginlong route。包装字段 cm 与工作簿 mm 不同，且方向待确认。 | **需扩展 + 待外部确认**；接入 outbound order，只按 A-003 做可替换适配准备。 |
| 04 入库完成 | 用户手动 Odoo→Solis；行 24–32 | 入库回传可从 picking/move/SN 准备数据；字段/分批/响应合同未确认。 | **需扩展**；回传按钮归属 inbound order，按用户点击触发。 |
| 05 盘点单 | Solis→Odoo；行 81–95 | 工作簿要求创建/删除盘点单，单号唯一，包含仓库、产品明细和 SN/托盘清单；删除限未操作整单。未发现现有 Ginlong 盘点任务模型。 | **建议新增独立盘点任务模型**；保存外部任务和盘点范围；不映射到或操作 `stock.quant`。 |
| 06 备货完成 | 用户手动 Odoo→Solis；行 67–77 | 有 outbound order 人工拣货完成回传范式；当前绑定 Hoymiles，载荷/分批规则未确认。 | **需扩展**；按钮归属 outbound order，手动触发且不照搬额外状态拦截。 |
| 07 物料档案 | Solis→Odoo；行 105–117 | 产品扩展和导入暂存字段部分可复用；全量 Ginlong 字段、货主+物料编码唯一性及修改规则未覆盖。 | **需扩展**；对接产品模型，不属于 order。 |
| 08 发货完成 | 用户手动 Odoo→Solis；行 78–80 | 有 outbound order 已完成 picking/move 汇总和回传日志；当前数量转整数，Ginlong 数量精度/分批语义未确认。 | **需扩展**；按钮归属 outbound order，手动触发，Payload 按合同映射。 |
| 09 库存查询 | Solis→Odoo；行 118–124 | 有 stock.quant 查询基础，但现有查询缺 owner 条件；Linglong 历史报表不等同库存 API。 | **需扩展**；对接 stock.quant 查询，不属于 order；库存口径/授权/分页待确认。 |
| 10 盘点完成 | 用户手动 Odoo→Solis；行 96–104 | 工作簿回传盘点单号及采集到的 SN、数量、托盘、产品、操作人员和时间；未发现现成结果记录/手动按钮。工作簿对部分采集时机的描述不一致。 | **建议复用独立盘点任务模型并扩展采集结果记录**；按钮由用户手动点击；不以 `stock.quant` 作为数据来源或写入目标。 |

**不可行结论：无。** 这里表示源码未证明技术上不可行；不代表已完成运行时证明或可立即联调。**可直接作为 Ginlong 成品复用的接口：无。** 映射建议是 01/02/04→inbound order、03/06/08→outbound order、05/10→独立盘点任务/采集结果模型、07→产品模型、09→`stock.quant` 查询。05/10 不读写 `stock.quant`。

## 5. 主要发现与风险

| ID | 发现/风险 | 影响 | TDD/后续处理 |
| --- | --- | --- | --- |
| R-01 | 现有 Ginlong 专用 API 路由未发现；Hoymiles 入站 controller 和出站 callback 都带对方专用地址/字段/规则。 | 不能将现有接口直接对外使用。 | 取得 Ginlong 协议后，定义独立路由/映射和配置；复用现有 WMS 能力，不复制库存/作业逻辑。 |
| R-02 | 认证 API 日志会落原始请求和响应；源码路径会记录 API Secret 与 Access Token；无效/过期 Token 也写入应用日志。 | 违反 SRS 凭据不得入日志的安全要求。 | TDD 列明凭据过滤/日志字段规则；实施前用测试凭据验证日志不含 Secret、Token、Authorization。 |
| R-03 | Token 以明文值保存；Token 装饰器按 Odoo user 查找 API user，未见对 API user active 的逐请求检查。 | 撤销、停用和凭据轮换边界未被证实。 | 确认现有行为是否满足 Ginlong 安全要求，并在测试库验证到期、停用、撤销和用户隔离。 |
| R-04 | 既有接口及回传逻辑大量 `sudo()` 并由 API 用户绑定 project；记录级权限/货主隔离运行时未验证。 | 请求可能越过普通 ACL，需要证明 project/owner 约束完整。 | 在 TDD 列出威胁/授权边界；测试不同 API user/project/owner 的越权场景。 |
| R-05 | 入库模型 project+reference 唯一性与控制器全局 reference 查询范围不一致；出库控制器也以 reference 检查重复。 | 多项目同单号或请求重放可能错误冲突/漏判；无法将其视作 Ginlong 幂等规则。 | 先确认外部业务键及作用域，再设计对应唯一性/幂等处理。 |
| R-06 | 现有回传单据状态字段只留当前状态，API log 未显式关联业务单据 ID/接口触发用户；历史每次操作虽有日志但关联性不足。 | 难以完整满足 SRS 的逐次回传审计、结果未知人工核对。 | TDD 决定在既有日志模型上补充接口编号、业务模型/记录、操作人、尝试序号/关联键等字段；不建平行日志体系。 |
| R-07 | 现有出库回传数量转 `int`；Ginlong数量精度尚无确认。包装单位存在 cm 与工作簿 mm 的差异。 | 潜在数量截断和尺寸单位错误。 | 以接口字段定义核验精度、单位、舍入策略；未确认前不要复用转换逻辑。 |
| R-08 | 05/10 是盘点任务创建/删除与采集数据回传；Ginlong V3.1 未规定这两个接口读取或修改 Odoo 库存现存量，也未规定其触发库存过账。 | 将接口 05/10 直接接到库存数量或过账流程，会把盘点任务/采集结果与库存记账混为一体。 | 05/10 使用独立盘点任务/采集结果模型，不映射到 `stock.quant`。SRS FR-GIN-010 对“盘点业务及库存调整由现有 Odoo 业务服务负责”的表述，其与接口 05/10 的业务关系须由需求方澄清；本 TV 不据此补造调用或库存变更路径。 |
| R-09 | 请求/业务处理/回传分阶段状态、同步/异步、超时后结果未知和批次语义均缺 Ginlong契约。 | 技术设计和真实联调验收条件尚不闭合。 | 取得正式契约并确认外部行为后，在 TDD 中定义状态关联和人工恢复；后台不得自动触发五项回传。 |
| R-10 | SRS 功能需求引用“BR 6.1.6”，但业务规则目前为 §6.1 项目符号列表，无稳定的 BR 编号。 | 需求追溯引用可读性不足。 | 建议 SRS 后续编辑性修订为明确规则 ID 或 §6.1 第 6 条引用；该文档追溯问题不改变本次技术事实结论。 |
| R-11 | 当前 API 日志状态、WMS业务状态与回传结果字段分开存在，未发现按外部请求/业务单据关联的三阶段状态跟踪。 | 现状不能直接证明 SRS 所要求的“接收成功≠业务处理成功≠回传成功”可追溯性。 | TDD 定义关联标识和阶段结果记录；在本地模拟分别验证接收失败、业务失败、回传失败/未知及成功场景。 |

## 6. TDD 技术输入、待解决问题与建议

### 6.1 可作为 TDD 事实输入

1. Odoo 为 18.0；现有 WMS 入库、出库、产品、包装、库存查询和人工回传代码均在 `worlddepot` 中，但 Ginlong 专属路由未发现。
2. 入库/出库单模型和 stock picking/move 数据可作为接口字段映射候选来源；现有 Hoymiles controller 主要直接通过 ORM 创建单据，现有代码没有证明一个 Ginlong 可直接调用的通用服务边界。
3. API 用户使用 bcrypt Secret 验证和一小时 Token；当前日志实现捕获原始 HTTP body/响应，有凭据泄露日志路径，必须纳入安全设计。
4. 五个回传节点可以采用 Odoo 表单按钮显式调用；现有可见范式包含准备 Payload、HTTP 调用、逐请求日志和当前结果字段。Ginlong按钮需独立适配并遵守“不自动触发”。
5. 09 有 stock.quant 查询基础，但需增加 Ginlong endpoint、授权过滤和合同字段映射；历史库存报表不等同库存 API。
6. `worlddepot` 没有 Ginlong 盘点任务/采集结果模型；工作簿的 05/10 字段和动作支持将两接口放在同一独立业务对象边界。该对象不映射到 `stock.quant`。SRS 关于“盘点业务及库存调整”的表述与 05/10 的具体关联尚需需求方澄清，不能据此推定接口操作或库存过账。
7. 当前 API log 的 success/error、WMS 单据状态和回传结果字段彼此分开；尚无三阶段结果统一关联的源码证据，TDD 需显式定义该追踪能力。
8. 按本版架构建议，01/02/04 对接 inbound order，03/06/08 对接 outbound order，05/10 使用独立盘点任务/采集结果模型，07 对接产品模型，09 查询 `stock.quant`。05/10 与 `stock.quant` 分离。

### 6.2 进入 TDD 前或 TDD 中需关闭的问题

| 问题 | 责任/关闭条件 | 影响范围 |
| --- | --- | --- |
| Ginlong 十个接口的 URL、HTTP 方法、编码、鉴权、签名/Token、请求/响应样例、错误码和环境信息 | Ginlong 提供版本化接口文档及可用测试环境 | 全部接口；阻塞真实协议实现/联调，不阻止已确认映射的模拟验证 |
| 请求接收、Odoo 业务处理、Ginlong 回传/确认的独立状态及共同关联标识 | TDD 定义阶段状态和关联方式；通过本地模拟分别验证接收失败、业务失败、回传失败/未知和成功 | 全部接口 |
| 接口 03 方向、用途及 V3.1 内容冲突 | Ginlong 书面确认；如偏离 A-003，先评估 SRS 变更 | 03 |
| owner、warehouse、productCode 映射和唯一作用域 | 双方确认映射表/主数据责任及示例 | 01/03/05/07/09 及相关回传 |
| 盘点任务模型、采集结果记录和部分采集/撤销语义 | TDD 明确单头、产品明细、SN/托盘清单、采集结果及操作人/时间的记录关系；Ginlong 澄清分批调用与撤销范围；不预设额外状态规则 | 05/10 |
| SRS FR-GIN-010 所述“盘点业务及库存调整”是否属于接口 05/10 范围 | 需求方澄清 SRS 该句与 Ginlong 盘点任务/采集结果接口的边界；当前 TV 将 05/10 限定为任务创建/删除和采集结果回传，不映射到 `stock.quant`，不由 TV 定义库存过账动作 | SRS FR-GIN-010、05/10 |
| 分批/部分完成、重试、重复请求、回传结果未知、撤销/删除重建规则 | Ginlong 与 BeeSmart/仓库方书面确认业务语义和幂等键 | 01–10 中涉及重试/分批的接口，特别 04/06/08/10 |
| 09 数量口径、库位/库存状态、已分配量、快照时间、分页/大结果集 | 业务/双方签认接口字段及边界案例 | 09 |
| API user 停用、Token 失效/轮换、project/owner/warehouse授权隔离 | TDD 安全分析；在测试库按不同用户和项目验证 | 全部入站接口 |
| 日志字段、Payload 保存期限、关联关系与凭据保护 | 按 SRS 凭据不得记录要求完成方案；使用假凭据验证日志 | 全部请求及五个出站回传 |
| 五个回传的合法触发入口与复用字段来源 | 依据已确认字段/格式完成逐接口 mapping；验证按钮只由用户触发，点击一次只产生一次尝试 | 02/04/06/08/10 |

### 6.3 建议

- TDD 将 Ginlong 适配与 `worlddepot` 的业务单据/库存操作明确分层，优先调用或补齐现有 Odoo 业务服务，不另造入库、出库和库存逻辑。
- 按对象建立集成边界：01/02/04 复用 inbound order，03/06/08 复用 outbound order；05/10 建议新增独立盘点任务/采集结果模型，承载外部单号、盘点范围、SN/托盘/数量、操作人和时间及人工回传审计；07 使用产品模型，09 查询 `stock.quant`。05/10 不映射到 `stock.quant`。先澄清 SRS FR-GIN-010 中“盘点业务及库存调整”与 API05/10 的范围关系，不从接口字段推导任何库存操作。
- 用可替换的本地模拟端点/夹具先验证已确认的字段映射、payload 序列化、响应解析和错误留痕；该模拟验收不能代替 Ginlong真实契约联调。
- 在真实联调前关闭凭据日志风险并验证权限隔离；不将 token、secret 或 Authorization 头写入日志。
- 五个回传继续采用用户按钮；失败后由用户再次点击。结果未知时应保留记录供人工核实，不在没有外部幂等规则时自动重发。
- 开始 TDD 前可先取得 Ginlong正式协议资料，并在隔离 Odoo 18 测试库确认独立盘点任务模型的权限行为。接口 03 方向正式确认前，设计需保留适配方向可替换性。

## 7. 总体判定

### **有条件通过（源码/静态证据层面）**

理由：

- 01/02/04 与现有 inbound order 结构匹配，03/06/08 与现有 outbound order 结构匹配；04/06/08 有人工回传技术范式；07 有产品扩展；09 有库存查询基础。
- `worlddepot` 有 API 用户、Token 和请求日志机制，且五个人工回传按钮的模式从源码可见。
- 05/10 建议独立建模以承载盘点任务和采集结果；本 TV 不将其映射到或操作 `stock.quant`。07 使用产品模型，09 查询 `stock.quant`。所有 Ginlong 接口都没有可直接复用的现成 Ginlong endpoint。
- 凭据可能写入现有日志、权限隔离未运行时验证、盘点核心模型和 Ginlong契约未验证，故不得判为完整通过或已具备真实联调条件。

本结论只回答技术验证目标的当前证据状态。独立盘点任务/采集结果模型是本版 TV 建议，不是已冻结 TDD。接口 05/10 不映射到 `stock.quant`；SRS FR-GIN-010 中“盘点业务及库存调整”与 05/10 的关系列为需求澄清项，不由本 TV 代为解释或补造库存操作。用户批准 TV v0.2 有条件通过并进入 TDD 起草；本报告仍未冻结，实施及 TDD 冻结须等待相应文档门禁、外部依赖和技术评审完成。

## 8. 证据索引

- [冻结 SRS v1.0](../../requirement/SRS_ginlong_apis.md)
- Ginlong接口字段来源：[海外WMS与第三方系统集成 V3.1](../../ginlong_apis/海外WMS与第三方系统集成V3.1.xlsx)（逐接口逻辑工作表行范围见第 4 节）
- 认证与日志源码：[`my_api_user.py`](../../../mymodules/worlddepot/models/my_api_user.py)、[`auth_controller.py`](../../../mymodules/worlddepot/controllers/auth_controller.py)、[`validator_token.py`](../../../mymodules/worlddepot/controllers/validator_token.py)、[`api_logs.py`](../../../mymodules/worlddepot/controllers/api_logs.py)
- WMS与回传源码：[`inbound_order.py`](../../../mymodules/worlddepot/models/inbound_order.py)、[`inbound_order_status.py`](../../../mymodules/worlddepot/models/inbound_order_status.py)、[`outbound_order.py`](../../../mymodules/worlddepot/models/outbound_order.py)、[`outbound_order_status.py`](../../../mymodules/worlddepot/models/outbound_order_status.py)
- 库存/产品/权限源码：[`my_report.py`](../../../mymodules/worlddepot/models/my_report.py)、[`my_stock_report_linglong.py`](../../../mymodules/worlddepot/models/my_stock_report_linglong.py)、[`my_product_template.py`](../../../mymodules/worlddepot/models/my_product_template.py)、[`ir.model.access.csv`](../../../mymodules/worlddepot/security/ir.model.access.csv)
- 项目 TV 指南：[Technical_Verification_Guide.md](../../skill/odoo-project-workflow/references/templates/Designing/Technical_Verification_Guide.md)

## 9. 批准记录

| 项 | 记录 |
|---|---|
| 决议 | 有条件通过 TV v0.2，进入 TDD 起草阶段 |
| 批准日期 | 2026-11-16 |
| 批准依据 | 用户在本会话明确指令批准 TV v0.2 有条件通过并进入 TDD 起草 |
| 批准人 | 当前会话项目用户；未提供额外姓名/签署标识 |
| 条件/边界 | 仅授权文档起草；不授权编码、不冻结 TDD、不启动 Implementation Plan。未确认的 Ginlong 协议和业务规则仍为待决；接口 03 保持可替换假设；05/10 独立建模且不读写 `stock.quant`、不引入库存调整。 |
| TV 状态 | Approved with Conditions；TV 未冻结 |

