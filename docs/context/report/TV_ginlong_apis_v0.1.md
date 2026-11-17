# Ginlong API 技术验证报告（TV）

| 项目 | 内容 |
| --- | --- |
| 文档编号 | TV-GINLONG-API-001 |
| 项目 | `ginlong_apis` |
| 版本 | 0.1 |
| 状态 | **Review Draft（评审稿，未冻结）** |
| 验证日期 | 2026-11-16 |
| 需求基线 | [SRS-GINLONG-API v1.0 Frozen](../../requirement/SRS_ginlong_apis.md) |
| 总体结论 | **有条件通过** |
| 评审/批准 | 待评审 |

> 本报告记录源码和静态环境验证结果，不是 TDD，不构成实施授权，也不冻结 TV。Ginlong 外部协议和业务规则仍以双方正式确认资料为准。接口 03 仅依 SRS A-003 作为可替换的开发假设。

## 1. 摘要结论

Odoo 18 CE 的 `worlddepot` 已有入库单、出库单、库存查询、物料扩展字段，以及用户点击按钮后生成 Payload、调用外部接口并记录尝试结果的代码基础。现有 API 与回传实现主要绑定 Hoymiles；静态搜索没有发现 Ginlong/Solis 专用接口路由。现有模型和模式可作为 Ginlong 集成的复用基础，但不能直接视为 Ginlong 接口实现。

`worlddepot` API 用户、bcrypt Secret 校验、Token 发放/过期校验和 API 日志模型在源码中可见。不过，现有认证协议是否兼容 Ginlong 尚无法判断；认证入口日志会保存原始请求和响应，源码路径可将 API Secret 与 Access Token 一并写入日志。凭据日志问题须在真实联调前处理。权限边界、用户组和记录规则未在运行时验证。

因此，本 TV 对源码可复用性给出**有条件通过**：允许将已验证的现有模型和模式作为 TDD 输入；Ginlong 路由、字段映射、认证适配、业务关联日志和盘点单据集成需要扩展。Odoo 核心盘点能力已由源码验证；其在目标数据库中的安装/权限行为、真实接口集成和合同外语义仍待运行时或外部资料验证。

## 2. 范围、方法与限制

### 2.1 验证范围

- 检查 Odoo 18 CE 项目内 `mymodules/worlddepot` 的 WMS 模型、字段、控制器、回传方法、库存及产品扩展。
- 检查现有 API 用户、Secret、Token、权限配置和日志代码，判断其作为 Ginlong 接口基础的适配可行性。
- 将 V3.1 工作簿中接口 01–10 的现有字段清单与源码能力逐类比对。
- 验证 02/04/06/08/10 的人工按钮调用模式；本 TV 不增加自动触发或后台自动重试。
- 识别幂等、映射、分批、异常恢复及资料缺失对技术设计的影响。

### 2.2 方法与实际结果

| 方法 | 实际结果 |
| --- | --- |
| 检查项目版本 | `./odoo-bin --version` 返回 `Odoo Server 18.0`。 |
| 静态阅读 | 阅读 `worlddepot` 的入库/出库模型、状态扩展、Hoymiles 控制器、API 用户/Token/日志、库存报告、产品扩展及视图/ACL。 |
| 检查接口字段来源 | 阅读 `docs/ginlong_apis/海外WMS与第三方系统集成V3.1.xlsx` 的“海外WMS与第三方系统的接口与处理逻辑”工作表及相关字段行；没有将“与海航（英国）联调进度”工作表作为 Ginlong 验收证据。 |
| 静态语法/结构检查 | Python AST：53 个 `worlddepot` Python 文件，0 个解析错误。XML：入库单、出库单、API 用户、API 日志 4 个视图文件均可解析。 |
| Ginlong 路由搜索 | 在 `worlddepot/controllers` 与 `worlddepot/models` 中搜索 Ginlong/Solis，未找到对应接口实现。 |
| 运行时/生产数据 | 检出树包含 `addons/stock` 核心源码，并已静态检查原生盘点实现与视图；未连接数据库、未升级模块、未写入业务数据。没有可确认的测试数据库和 Ginlong 测试端点/凭据；因此未执行 ORM、模块升级或真实 API 调用，无法确认当前目标数据库的模块安装/配置状态。 |

静态解析只证明源文件可以被解析，不证明 Odoo 模块可安装、数据库模型已注册或业务流程可运行。视图 XML 检查不等于完整 Odoo View 校验。

### 2.3 项目工作流状态

TV 指南说明 TV 不要求固定模板；每项重要验证应记录问题、方法、结果、证据和 TDD 影响。项目模板同步脚本 `python3 docs/skill/odoo-project-workflow/scripts/check_template_sync.py --repo-root /Users/lijianqiang/Documents/odoo18ce_karlrapp --template technical-verification` 返回 `BLOCKED：找不到项目模板来源`。因此本文件按项目工作流标为 Review Draft，供评审；本次不将其作为已冻结 TV 基线。报告格式依据项目 TV 指南的最小记录要求，未把未同步模板宣称为权威来源。

## 3. 技术验证事项

### TV-001 — WMS 模型与 10 个接口字段映射

**Question**  
现有 WMS 模型、字段和业务操作是否能承接接口 01–10 所需数据？

**Method**  
静态检查 `world.depot.inbound.order`、`world.depot.outbound.order`、产品扩展、包装记录、库存报告及 Hoymiles 入库控制器；按工作簿逐接口字段范围对照。

**Result — VERIFIED（现有模型/结构事实）；映射覆盖 INCONCLUSIVE（运行时和完整逐字段语义未验证）**

**Evidence**

- 入库单含 project、owner（由 project 关联）、warehouse、reference、状态、入库产品关系和 stock picking 关系；入库明细具有托盘/产品层级。[`inbound_order.py`](../../../mymodules/worlddepot/models/inbound_order.py#L10-L105) [`inbound_order.py`](../../../mymodules/worlddepot/models/inbound_order.py#L592-L634)
- 出库单含项目、货主、仓库、收货公司、地址/联系方式、reference、产品明细和 picking 关联。[`outbound_order.py`](../../../mymodules/worlddepot/models/outbound_order.py#L19-L55) [`outbound_order.py`](../../../mymodules/worlddepot/models/outbound_order.py#L82-L105) [`outbound_order.py`](../../../mymodules/worlddepot/models/outbound_order.py#L121-L145)
- Odoo 18 核心 `stock.quant` 有 product/location/lot/package/owner、quantity/reserved/available quantity、inventory_quantity（实盘数）、inventory_diff_quantity（差异）、inventory_date、inventory_quantity_set 等字段；盘点应用会创建并完成 stock.move，再清除实盘数。原生库存调整视图提供实盘数、差异、Apply/Set/Clear 操作。[`stock_quant.py`](../../../addons/stock/models/stock_quant.py#L46-L118) [`stock_quant.py`](../../../addons/stock/models/stock_quant.py#L436-L475) [`stock_quant.py`](../../../addons/stock/models/stock_quant.py#L1016-L1037) [`stock_quant_views.xml`](../../../addons/stock/views/stock_quant_views.xml#L432-L462)
- Odoo 核心测试源码包含带 lot 的盘点调整测试，但本次没有运行 Odoo 测试或 ORM 实验；这是源码证据，不是本项目数据库的运行结果。[`test_inventory.py`](../../../addons/stock/tests/test_inventory.py#L66-L85)
- 出库包装模型含包件编号/数量、尺寸（cm）、体积（m³）、毛重、净重及包内产品。[`outbound_order_pack_info.py`](../../../mymodules/worlddepot/models/outbound_order_pack_info.py#L35-L73)
- 产品档案扩展覆盖部分 Ginlong 属性，如危险品、UN 编码、每托数量、品牌、重量、尺寸；导入暂存模型另含商品名、条码、追踪方式、HS 编码等字段。它们不等于工作簿全部物料字段的已确认语义映射。[`product_template.py`](../../../mymodules/wd_product_profile/models/product_template.py#L5-L15) [`my_product_template.py`](../../../mymodules/worlddepot/models/my_product_template.py#L5-L27)
- 现有入库控制器按 `barcode` 或 `default_code` 找产品，再通过 ORM 创建 WMS 入库单及托盘/产品行，是可参考的转换模式；该控制器是 Hoymiles 路由，不是 Ginlong 契约或 Ginlong 业务服务。[`inbound_controller.py`](../../../mymodules/worlddepot/controllers/hoymiles/inbound_controller.py#L12-L18) [`inbound_controller.py`](../../../mymodules/worlddepot/controllers/hoymiles/inbound_controller.py#L28-L45) [`inbound_controller.py`](../../../mymodules/worlddepot/controllers/hoymiles/inbound_controller.py#L69-L101)
- 工作簿接口 03 的产品包装尺寸以 mm 表达，而现有包装记录字段以 cm 表达；需要在 TDD 明确并以确认契约校验单位换算。不能静默沿用字段单位。

**TDD Impact**  
逐接口建立来源字段→Odoo 字段→转换/校验→目标字段的映射表。货主、仓库、产品编码和单位/尺寸换算应作为显式配置或映射规则验证；不能将 Hoymiles 字段名、默认值或路由直接复用为 Ginlong 契约。

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
接口 01/03/05/07/09 的入站映射、现有业务操作及库存查询能否复用？

**Method**  
检查 Hoymiles 入库/出库控制器、入库/出库模型、物料档案、stock.quant 查询和现有库存报表；检查项目中是否已有 count 单据/ Ginlong 路由。

**Result — WMS 与 Odoo 原生盘点/调整原语 VERIFIED（源码层面）；Ginlong 请求端到端处理 INCONCLUSIVE；外部盘点单关联需扩展**

**Evidence**

- 01 可借用入库模型层级和现有产品检索示例，但现有入库 API 仅检查并通过 ORM 建立 Hoymiles 入库单，不提供 Ginlong route，也未覆盖 Ginlong 全部字段/删除语义。[`inbound_controller.py`](../../../mymodules/worlddepot/controllers/hoymiles/inbound_controller.py#L22-L45) [`inbound_controller.py`](../../../mymodules/worlddepot/controllers/hoymiles/inbound_controller.py#L69-L101)
- 03 可借用出库单、收货方地址和产品/包装模型；项目中没有 Ginlong/Solis 路由。SRS A-003 允许暂按 Solis→Odoo 做开发假设，但不能把假设当作正式契约。
- 05/10：在 `worlddepot` 自定义模型中未发现 Ginlong 盘点单据/完成接口实现；但 Odoo 18 核心 `stock.quant` 静态源码确有实盘数、差异、实盘状态、产品/库位/lot/package/owner 维度及应用盘点后生成 stock.move 的能力。可复用其库存调整能力；核心 quant 本身没有本项目 Ginlong `countOrderNo` 的接口级单据关联和五接口审计，所以外部盘点单头/行与盘点生命周期仍需集成扩展。当前未连接数据库，模块安装、用户权限及实际操作仍未运行验证。[`stock_quant.py`](../../../addons/stock/models/stock_quant.py#L46-L118) [`stock_quant.py`](../../../addons/stock/models/stock_quant.py#L436-L475) [`stock_quant.py`](../../../addons/stock/models/stock_quant.py#L1016-L1037)
- 07 可复用 `product.template` 扩展字段和物料导入暂存模式；未找到覆盖工作簿所有物料字段、货主+物料编码唯一性及 Ginlong 新增/修改语义的 Ginlong 接口。
- 通用库存页按 stock.quant 搜索内部库位，并可按仓库、库位、产品过滤；没有货主条件，也不是面向 Ginlong 的接口。[`my_report.py`](../../../mymodules/worlddepot/models/my_report.py#L9-L49)
- 名为 Linglong 的库存报告通过 stock.move 计算期初/入库/出库/在手数量，但筛选硬编码产品分类 ID 11，并非通用当前库存 API，不能直接作为接口 09 的数量口径。[`my_stock_report_linglong.py`](../../../mymodules/worlddepot/models/my_stock_report_linglong.py#L58-L78) [`my_stock_report_linglong.py`](../../../mymodules/worlddepot/models/my_stock_report_linglong.py#L102-L146) [`my_stock_report_linglong.py`](../../../mymodules/worlddepot/models/my_stock_report_linglong.py#L259-L271)

**TDD Impact**  
区分“API 接收/转换层”与现有 Odoo WMS 业务服务，明确失败、删除/重建、部分处理与重复请求对既有单据的影响。接口 09 需以确认的货主、仓库、产品、库位/状态、数量口径及快照时间定义查询，不能把报表字段直接当作合同。05/10 可把 Odoo 原生 `stock.quant` 实盘数及盘点应用操作作为候选复用能力；仍需在测试库验证模块状态、权限、SN/包装场景，并设计其与 Ginlong countOrderNo、明细和审计记录的关联。

### TV-004 — 五个人工回传按钮

**Question**  
接口 02/04/06/08/10 能否采用用户手动点击 Odoo 单据按钮生成 Payload、调用接口并留痕？

**Method**  
检查入库/出库状态扩展中的按钮方法、视图、Payload 组装、HTTP 调用、结果字段及日志写入。

**Result — 手动 UI/HTTP/结果模式 VERIFIED；Ginlong Payload 与响应兼容性 INCONCLUSIVE**

**Evidence**

- 入库单存在人工确认和入库结果方法；按现有 picking/move 数据生成 Payload，调用 Hoymiles URL，写每次请求/响应日志并更新当前成功/时间/错误字段。[`inbound_order_status.py`](../../../mymodules/worlddepot/models/inbound_order_status.py#L59-L125) [`inbound_order_status.py`](../../../mymodules/worlddepot/models/inbound_order_status.py#L192-L280)
- 出库单存在备货完成与发货结果方法；出库结果根据已完成的 picking/move 汇总行项目，调用外部 URL并记录响应；表单视图有对应 object 按钮及状态展示字段。[`outbound_order_status.py`](../../../mymodules/worlddepot/models/outbound_order_status.py#L252-L340) [`outbound_order_status.py`](../../../mymodules/worlddepot/models/outbound_order_status.py#L815-L935) [`outbound_order.xml`](../../../mymodules/worlddepot/views/outbound_order.xml#L232-L314)
- 现有这些页面及方法按 Hoymiles 项目/权限组显示或执行；不是 Ginlong 按钮。每次调用的 API 日志提供逐请求留痕，但业务单据上的 Boolean/时间/错误字段主要表示最近状态，不能代替完整的按单据回传历史。[`outbound_order.xml`](../../../mymodules/worlddepot/views/outbound_order.xml#L232-L314) [`outbound_order_status.py`](../../../mymodules/worlddepot/models/outbound_order_status.py#L79-L99)
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
| 01 待入库单 | Solis→Odoo；行 5–20。入库单、货主/仓库、产品、托盘/SN 等 | `world.depot.inbound.order` 和托盘/产品层级存在；Hoymiles 控制器展示产品匹配与创建模式。无 Ginlong 路由，删除/修改、货主/仓库映射及完整字段转换需实现/验证。 | **需扩展**；WMS 模型和映射范式可复用。 |
| 02 收货确认 | 用户手动 Odoo→Solis；行 21–23 | 入库单确认按钮、Payload/HTTP 调用及逐请求日志模式存在，但绑定 Hoymiles，Ginlong字段/鉴权/响应未确认。 | **需扩展**；人工按钮与日志模式可复用。 |
| 03 待出库单 | SRS A-003 开发假设 Solis→Odoo；行 33–66 | 出库单、收件方、地址、产品/包装模型存在；无 Ginlong 接口。包装字段存在 cm，而工作簿尺寸字段为 mm。方向仍待 Ginlong 确认。 | **需扩展 + 待外部确认**；只可按 A-003 做可替换适配准备。 |
| 04 入库完成 | 用户手动 Odoo→Solis；行 24–32 | 入库结果按钮按 picking/move/SN 准备回传并记录请求；字段语义、分批过账和 Ginlong 响应未知。 | **需扩展**；人工触发和 picking 数据准备模式可复用。 |
| 05 盘点单 | Solis→Odoo；行 81–95 | `worlddepot` 未发现 Ginlong盘点单据/接口。Odoo 18 `stock.quant` 提供实盘数、差异及盘点应用能力，且可按 product/location/lot/package/owner 区分；未发现与 Ginlong countOrderNo 生命周期的现成关联。 | **需扩展**；复用原生盘点/库存调整，补充外部单据关联和映射；数据库运行状态待验证。 |
| 06 备货完成 | 用户手动 Odoo→Solis；行 67–77 | 出库单有人工拣货完成调用模式；当前实现绑定 Hoymiles，Picking/批次规则和 Ginlong载荷未确认。 | **需扩展**；手动按钮/调用模式可复用，不带入未批准状态拦截。 |
| 07 物料档案 | Solis→Odoo；行 105–117 | 有产品扩展和导入暂存字段，但完整属性、货主+物料编码唯一性、修改规则及产品编码映射不齐/未确认。 | **需扩展**；产品与暂存能力部分可复用。 |
| 08 发货完成 | 用户手动 Odoo→Solis；行 78–80 | 有人工出库结果按钮、已完成 picking/move 聚合、请求日志；现有数量转为整数，Ginlong 数量精度/部分发货语义未确认。 | **需扩展**；Payload 聚合模式可复用，需按契约校正。 |
| 09 库存查询 | Solis→Odoo；行 118–124 | 有 stock.quant 内部库存过滤和 Linglong 历史库存报表；无 Ginlong API，通用查询缺货主过滤，Linglong报告类别硬编码且为历史移动计算。 | **需扩展**；stock.quant 查询原语可复用，准确库存口径/快照/分页待业务确认。 |
| 10 盘点完成 | 用户手动 Odoo→Solis；行 96–104 | 未发现 Ginlong盘点完成按钮/回传服务。Odoo 原生盘点差异/实盘字段在源码存在，但没有 Ginlong countOrderNo 与盘点结果的现成关联。 | **需扩展 + 运行时待验证**；可用原生盘点结果作为候选来源，补人工按钮及关联；按钮仍须手动触发。 |

**不可行结论：无。** 这里表示源码未证明技术上不可行；不代表已完成运行时证明或可立即联调。**可直接作为 Ginlong 成品复用的接口：无。** 目前可复用的是 WMS 模型/数据源、产品匹配范式、人工按钮与日志机制等基础能力，且均需要适配。

## 5. 主要发现与风险

| ID | 发现/风险 | 影响 | TDD/后续处理 |
| --- | --- | --- | --- |
| R-01 | 现有 Ginlong 专用 API 路由未发现；Hoymiles 入站 controller 和出站 callback 都带对方专用地址/字段/规则。 | 不能将现有接口直接对外使用。 | 取得 Ginlong 协议后，定义独立路由/映射和配置；复用现有 WMS 能力，不复制库存/作业逻辑。 |
| R-02 | 认证 API 日志会落原始请求和响应；源码路径会记录 API Secret 与 Access Token；无效/过期 Token 也写入应用日志。 | 违反 SRS 凭据不得入日志的安全要求。 | TDD 列明凭据过滤/日志字段规则；实施前用测试凭据验证日志不含 Secret、Token、Authorization。 |
| R-03 | Token 以明文值保存；Token 装饰器按 Odoo user 查找 API user，未见对 API user active 的逐请求检查。 | 撤销、停用和凭据轮换边界未被证实。 | 确认现有行为是否满足 Ginlong 安全要求，并在测试库验证到期、停用、撤销和用户隔离。 |
| R-04 | 既有接口及回传逻辑大量 `sudo()` 并由 API 用户绑定 project；记录级权限/货主隔离运行时未验证。 | 请求可能越过普通 ACL，需要证明 project/owner 约束完整。 | 在 TDD 列出威胁/授权边界；测试不同 API user/project/owner 的越权场景。 |
| R-05 | 入库模型 project+reference 唯一性与控制器全局 reference 查询范围不一致；出库控制器也以 reference 检查重复。 | 多项目同单号或请求重放可能错误冲突/漏判；无法将其视作 Ginlong幂等规则。 | 先确认外部业务键及作用域，再设计对应唯一性/幂等处理。 |
| R-06 | 现有回传单据状态字段只留当前状态，API log 未显式关联业务单据 ID/接口触发用户；历史每次操作虽有日志但关联性不足。 | 难以完整满足 SRS 的逐次回传审计、结果未知人工核对。 | TDD 决定在既有日志模型上补充接口编号、业务模型/记录、操作人、尝试序号/关联键等字段；不建平行日志体系。 |
| R-07 | 现有出库回传数量转 `int`；Ginlong数量精度尚无确认。包装单位存在 cm 与工作簿 mm 的差异。 | 潜在数量截断和尺寸单位错误。 | 以接口字段定义核验精度、单位、舍入策略；未确认前不要复用转换逻辑。 |
| R-08 | Odoo 18 核心 `stock.quant` 已有实盘、差异及应用盘点能力；`worlddepot` 未发现 Ginlong盘点单头/回传关联，且尚未连接 runtime。 | 可复用原生库存调整，但不能据静态源码确认目标数据库模块状态、权限和 Ginlong单据/结果关联。 | 在隔离测试库验证 quant 盘点（含序列号/包装/owner）与权限；TDD 设计 countOrderNo、明细/盘点结果关联和手动完成回传。 |
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
6. Odoo 18 核心 `stock.quant` 源码已证实存在原生实盘数、差异和应用库存调整能力，也包含 lot/package/owner 字段；目标数据库运行状态及 Ginlong 盘点单号/结果关联尚未验证，自定义 `worlddepot` Ginlong盘点集成未发现。
7. 当前 API log 的 success/error、WMS 单据状态和回传结果字段彼此分开；尚无三阶段结果统一关联的源码证据，TDD 需显式定义该追踪能力。

### 6.2 进入 TDD 前或 TDD 中需关闭的问题

| 问题 | 责任/关闭条件 | 影响范围 |
| --- | --- | --- |
| Ginlong 十个接口的 URL、HTTP 方法、编码、鉴权、签名/Token、请求/响应样例、错误码和环境信息 | Ginlong 提供版本化接口文档及可用测试环境 | 全部接口；阻塞真实协议实现/联调，不阻止已确认映射的模拟验证 |
| 请求接收、Odoo 业务处理、Ginlong 回传/确认的独立状态及共同关联标识 | TDD 定义阶段状态和关联方式；通过本地模拟分别验证接收失败、业务失败、回传失败/未知和成功 | 全部接口 |
| 接口 03 方向、用途及 V3.1 内容冲突 | Ginlong 书面确认；如偏离 A-003，先评估 SRS 变更 | 03 |
| owner、warehouse、productCode 映射和唯一作用域 | 双方确认映射表/主数据责任及示例 | 01/03/05/07/09 及相关回传 |
| 如何把 Ginlong countOrderNo/行明细关联到 Odoo `stock.quant` 原生盘点数及最终库存调整 | 在目标 Odoo 18 测试库验证模块状态、模型字段、权限、SN/包装场景和现行流程；业务方确认盘点生命周期 | 05/10 |
| 分批/部分完成、重试、重复请求、回传结果未知、撤销/删除重建规则 | Ginlong 与 BeeSmart/仓库方书面确认业务语义和幂等键 | 01–10 中涉及重试/分批的接口，特别 04/06/08/10 |
| 09 数量口径、库位/库存状态、已分配量、快照时间、分页/大结果集 | 业务/双方签认接口字段及边界案例 | 09 |
| API user 停用、Token 失效/轮换、project/owner/warehouse授权隔离 | TDD 安全分析；在测试库按不同用户和项目验证 | 全部入站接口 |
| 日志字段、Payload 保存期限、关联关系与凭据保护 | 按 SRS 凭据不得记录要求完成方案；使用假凭据验证日志 | 全部请求及五个出站回传 |
| 五个回传的合法触发入口与复用字段来源 | 依据已确认字段/格式完成逐接口 mapping；验证按钮只由用户触发，点击一次只产生一次尝试 | 02/04/06/08/10 |

### 6.3 建议

- TDD 将 Ginlong 适配与 `worlddepot` 的业务单据/库存操作明确分层，优先调用或补齐现有 Odoo 业务服务，不另造入库、出库和库存逻辑。
- 用可替换的本地模拟端点/夹具先验证已确认的字段映射、payload 序列化、响应解析和错误留痕；该模拟验收不能代替 Ginlong真实契约联调。
- 在真实联调前关闭凭据日志风险并验证权限隔离；不将 token、secret 或 Authorization 头写入日志。
- 五个回传继续采用用户按钮；失败后由用户再次点击。结果未知时应保留记录供人工核实，不在没有外部幂等规则时自动重发。
- 开始 TDD 前可先取得 Ginlong正式协议资料，并在隔离 Odoo 18 测试库确认盘点和 ACL 行为。接口 03 方向正式确认前，设计需保留适配方向可替换性。

## 7. 总体判定

### **有条件通过（源码/静态证据层面）**

理由：

- 01/03 所需入库、出库单据及部分字段来源存在；04/06/08 有人工回传技术范式；07 有产品扩展；09 有库存查询基础。
- `worlddepot` 有 API 用户、Token 和请求日志机制，且五个人工回传按钮的模式从源码可见。
- Odoo 18 原生盘点/调整能力可复用，但 05/10 仍需盘点单号关联、生命周期/回传集成；09 需要 Ginlong 专用查询和授权映射。所有 Ginlong 接口都没有可直接复用的现成 Ginlong endpoint。
- 凭据可能写入现有日志、权限隔离未运行时验证、盘点核心模型和 Ginlong契约未验证，故不得判为完整通过或已具备真实联调条件。

本结论只回答技术验证目标的当前证据状态。它不批准任何额外业务状态拦截，不确定同步/异步方式，不确认 A-003 为 Ginlong 合同，也不启动 TDD 或编码。TV 评审后由项目授权人决定是否冻结本报告及后续阶段。

## 8. 证据索引

- [冻结 SRS v1.0](../../requirement/SRS_ginlong_apis.md)
- Ginlong接口字段来源：[海外WMS与第三方系统集成 V3.1](../../ginlong_apis/海外WMS与第三方系统集成V3.1.xlsx)（逐接口逻辑工作表行范围见第 4 节）
- 认证与日志源码：[`my_api_user.py`](../../../mymodules/worlddepot/models/my_api_user.py)、[`auth_controller.py`](../../../mymodules/worlddepot/controllers/auth_controller.py)、[`validator_token.py`](../../../mymodules/worlddepot/controllers/validator_token.py)、[`api_logs.py`](../../../mymodules/worlddepot/controllers/api_logs.py)
- WMS与回传源码：[`inbound_order.py`](../../../mymodules/worlddepot/models/inbound_order.py)、[`inbound_order_status.py`](../../../mymodules/worlddepot/models/inbound_order_status.py)、[`outbound_order.py`](../../../mymodules/worlddepot/models/outbound_order.py)、[`outbound_order_status.py`](../../../mymodules/worlddepot/models/outbound_order_status.py)
- 库存/产品/权限源码：[`my_report.py`](../../../mymodules/worlddepot/models/my_report.py)、[`my_stock_report_linglong.py`](../../../mymodules/worlddepot/models/my_stock_report_linglong.py)、[`my_product_template.py`](../../../mymodules/worlddepot/models/my_product_template.py)、[`ir.model.access.csv`](../../../mymodules/worlddepot/security/ir.model.access.csv)
- 项目 TV 指南：[Technical_Verification_Guide.md](../../skill/odoo-project-workflow/references/templates/Designing/Technical_Verification_Guide.md)

