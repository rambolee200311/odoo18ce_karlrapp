<!-- TDD v0.4 Frozen with Open Items. Supersedes v0.3 for new implementation; v0.3 remains unchanged as a historical frozen baseline. Project template-source sync remains BLOCKED under the previously approved workflow exception; not represented as Passed. -->

# Ginlong API 技术设计说明书（TDD）

| 项 | 内容 |
|---|---|
| 文档路径 | `docs/ginlong_apis/TDD-v0.4.md` |
| 模块名称 | `ginlong_apis`（拟建 Odoo addon） |
| 文档编号 | TDD-GINLONG-API-001 |
| 文档版本 | **v0.4** |
| 状态 | **FROZEN WITH OPEN ITEMS（已冻结，保留外部联调依赖）** |
| 技术负责人 | 待项目指定 |
| 基线日期 | 2026-11-17 |
| 批准/冻结记录 | 李建强；2026-11-17；按 CC-GIN-003 v1.1 Human Review 有条件批准要求完成 v0.4 修订并批准作为实施基线；外部协议、API03 方向及 API09 口径保留为 Open Items |
| 上游需求 | [SRS `ginlong_apis` v1.0 Frozen](../requirement/SRS_ginlong_apis.md) |
| 技术验证输入 | [TV `ginlong_apis` v0.2，有条件通过；未冻结](../context/report/TV_ginlong_apis_v0.2.md) |
| 外部资料 | [海外 WMS 与第三方系统集成 V3.2](海外WMS与第三方系统集成V3.2.xlsx) |

> 本 TDD v0.4 按 CC-GIN-003 v1.1 Human Review 有条件批准意见修订并作为当前实施基线；历史 v0.3 冻结版本保留在 [TDD v0.3](TDD.md)，不覆盖。v0.4 固定 `worlddepot`、Odoo `stock`、`ginlong_apis` 职责；API02/08 取 `worlddepot` Order 状态，API04/06 取实际 `stock.picking`、`stock.move.line` 作业记录，API10 取 `worlddepot` 仓库实盘结果。若 `worlddepot` 缺少盘点实盘能力，只允许在其中最小扩展，不在 `ginlong_apis` 新建平行盘点模型。回传 Wizard 是业务数据确认界面，JSON 由后台生成并通过现有 API 日志留存。未决 Ginlong 协议和 API03 方向继续保留为 Open Items。项目模板来源同步检查因仓库缺少来源文件仍为 `BLOCKED`，沿用已批准流程例外，不标记为 Passed。

## 0 文档说明

### 0.1 文档定位

完整业务闭环为：锦浪向 Odoo 传入订单；Odoo 将订单经 `karlrapp_gateway` 转为 KR 指令；KR 执行后由 `karlrapp_gateway` 回写结果到 Odoo；Odoo 用户再从订单按钮将执行结果回传锦浪。Odoo 是业务数据交换枢纽，现有 WMS 继续管理订单、库存和业务数据。

本 TDD 只定义 `ginlong_apis` 负责的锦浪 ↔ Odoo 部分；`karlrapp_gateway` 负责 Odoo ↔ KR，现有 Odoo WMS 负责订单及库存业务。本文不设计统一集成框架，也不重复实现 WMS。外部 URL、HTTP 方法、鉴权细节和若干业务语义仍待 Ginlong 确认；相应接口只能先做本地模拟设计，不能据本稿宣称真实契约已确定。

| 组件 | 职责 |
|---|---|
| `worlddepot` | 负责业务 Order、API User、Token、客户盘点指令和仓库实盘结果；项目可按需要修改、扩展、精简。 |
| Odoo `stock` | 负责实际出入库记录、库存移动和库存台账。API04/06 的作业明细从 `stock.picking`、`stock.move.line` 读取。 |
| `ginlong_apis` | 仅负责 Ginlong 协议、数据转换、Endpoint 配置、回传 Wizard 和接口调用，不重复实现 WMS 业务模型。 |

API02/08 使用 `worlddepot` 对应 Order 的现有业务状态；API10 使用 `worlddepot` 仓库实盘结果关联客户盘点指令，不使用 `stock.quant` 推算。若盘点能力缺失，先核实并只在 `worlddepot` 内最小扩展。

### 0.2 上游基线

| 项 | 内容 |
|---|---|
| 业务基线 | SRS v1.0 Frozen；范围 01–10、五个人工回传按钮及 `worlddepot` 复用原则已冻结 |
| 技术验证 | TV v0.2 有条件通过；本稿不要求额外专项事务验证 |
| 领域基线 | DDD 不适用：当前范围是既有 WMS 订单集成、客户盘点订单/仓库实盘结果及只读查询；不引入库存过账、不变量或跨聚合生命周期，SRS + TV 足以定义业务边界 |
| 下游 | 本 TDD v0.4 Frozen with Open Items；供 CC-GIN-003 v1.1 及后续受影响阶段实施 |

### 0.3 本文档回答什么 / 不回答什么

| 本文回答 | 本文不决定 |
|---|---|
| addon 范围、现有 WMS 模型映射、盘点任务/采集结果、按钮调用、现有日志/权限复用 | Ginlong 尚未确认的 URL、HTTP 方法、字段枚举、签名、错误码、重试语义或库存口径 |
| 五个人工按钮的同步 HTTP 调用、请求/响应日志及凭据保护 | 新增 WMS 库存作业、盘点过账、库存调整或接口 05/10 对 `stock.quant` 的操作 |
| 本地模拟测试边界与进入真实联调的条件 | 任何额外业务状态拦截条件或未获批准的 Ginlong 业务规则 |

### 0.4 事实、决策与待决事项

- **已验证事实**：项目为 Odoo 18.0；`worlddepot` 已有入库/出库模型、API 用户/Token、共享 API 日志；原生产品模型可继承扩展。事实来源见 TV v0.2 与附录 D。
- **本稿保留的设计**：`worlddepot` 持有业务订单、盘点指令和实盘结果；Odoo `stock` 持有实际库存移动；`ginlong_apis` 只承载 Ginlong 协议和调用。API05/10 复用 `worlddepot` 客户盘点指令/实盘结果；API10 不读写或推算 `stock.quant`，不在 `ginlong_apis` 建平行盘点模型。五个人工回传按钮使用标准 Wizard 展示业务数据，确认后由后台生成 JSON 并同步发送。
- **本稿删除的机制**：独立 API/业务 Adapter 框架、内部 canonical JSON Schema、技术状态机、回传锁/事务调度、独立监控指标与告警体系、专用多角色体系、独立 endpoint/mapping 模型、业务用户可见的 JSON 预览/编辑器。Endpoint/Method 使用 Odoo Settings 配置；不新建额外业务模型。
- **待外部确认**：Ginlong 正式 URL/方法/鉴权/报文、API03 方向（当前按 Solis→Odoo 开发假设）、API07 产品字段规则、API09 库存口径，以及幂等/重复/结果未知/批次语义。未确认的内容不得据本稿补造规则。
- **盘点边界**：API05/10 只管理worlddepot 客户盘点订单和仓库实盘结果，不访问/写入 `stock.quant`，不执行库存调整。

### 0.5 评审与变更

本 TDD v0.4 按 CC-GIN-003 v1.1 Human Review 有条件批准意见形成；李建强批准其作为当前技术实施基线，状态为 `FROZEN WITH OPEN ITEMS`。历史 v0.3 保留不覆盖。模板来源同步仍为 `BLOCKED`，沿用此前用户批准的流程例外，不伪装为通过。Ginlong 协议或业务规则确认后，先判断是否影响 SRS；业务含义变化先修订 SRS，纯技术变化按 TDD 变更流程升级版本。

### 0.6 编号规则

本文使用 `T-*`（Implementation Guardrail）、`ORM-*`、`SVC-*`、`ADPT-*`、`API-*`、`UI-*`、`SEC-*`、`ERR-*`、`TEST-*`、`TD-*` 编号。编号一经发布不复用。无 DDD 时不生成 `AGG-*`、`ENT-*`、`INV-*`、`DS-*` 或 `DV-*`。

### 0.7 规范措辞

“必须/禁止/不得”为本稿拟定的实现门禁；“应”为原则要求；“待确认/开放”表示不能据本稿补造外部契约或业务语义。评审和冻结后这些技术约束才成为实现基线。

### 0.8 SSOT

| 内容 | 定义位置 |
|---|---|
| ORM 模型与字段 | §3–4 |
| 10 个接口字段来源与协议待决项 | §5 |
| Odoo 业务处理和按钮 | §6、§13 |
| HTTP、认证、配置 | §7、§16 |
| 日志与异常 | §9、§11、§15 |
| 权限与凭据保护 | §12 |
| 测试计划 | §14 |
| 冻结实施约束 | §18 |

## 1 技术上下文

### 1.1 技术栈

| 层次 | 选型 | 版本/状态 | 说明 |
|---|---|---|---|
| 平台 | Odoo Community Edition | 18.0（仓库源码检查已验证） | 与当前项目一致 |
| 语言 | Python | 部署 Python 次版本待环境核实 | Implementation 前从目标环境核实 |
| 数据库 | PostgreSQL | 目标环境版本未提供 | Implementation 前从部署基线核实 |
| UI | Odoo XML/QWeb 表单视图 | 随 Odoo 18.0 | 本期不计划新增 Owl 前端 |
| 异步设施 | 不引入 | 本期不需要队列、worker、cron 或异步投递 | 五个人工按钮在标准 Odoo 按钮方法中同步调用 HTTP，见 §8 |
| 缓存 | 无 | 不适用 | 不缓存权限敏感的库存或凭据 |

### 1.2 依赖

| 依赖 | 类型 | 用途 | 必需 |
|---|---|---|---|
| `worlddepot` | 项目 addon | 复用 inbound/outbound order、API 用户/Token、API 日志、既有 WMS 服务与视图能力 | 是 |
| Odoo 现有依赖模块 | Odoo 模块 | 仅按实现需要使用 ORM、用户/组、仓库、产品和单据能力 | 是 |
| `wd_product_profile` | 项目 addon（`worlddepot` 已依赖） | 可复用的产品档案扩展字段 | 按依赖链 |
| Ginlong API | 外部服务 | 01–10 的真实调用 | 是，当前资料/环境未提供 |

### 1.3 关键非功能约束

| SRS 要求 | TDD 处理 |
|---|---|
| 权限与认证 | 复用 `worlddepot` API 用户/Token 和现有 WMS 用户权限；Ginlong 协议兼容性待确认 |
| 审计 | 复用 `world.depot.api.log` 已有请求、响应、错误、状态和时间字段；只补确实缺少的筛选字段 |
| 手动回传 | API02/04/06/08/10 只由用户按钮触发；同步请求、合理超时、不自动重试 |
| 盘点隔离 | API05/10 使用独立盘点模型；不操作 `stock.quant`、`stock.move` 或库存调整 |

## 2 模块目录结构

`mymodules/ginlong_apis/` 只包含 Ginlong 接口入口、协议字段转换、Endpoint 配置、Transient Wizard、权限衔接及模拟测试。业务 Order 和盘点指令/实盘结果由 `worlddepot` 提供；实际库存作业由 Odoo `stock` 提供。不得在 `ginlong_apis` 创建平行业务模型、第二套盘点数据或 JSON 预览/编辑工具。

集成模块负责将锦浪字段映射到现有 Odoo 模型并调用现有 WMS 能力；不复制入库、出库、库存和产品主数据业务。

## 3 ORM 模型设计

### 3.1 模型映射

| 上游对象 | 来源 | ORM 模型 | 处理 |
|---|---|---|---|
| 入库单 | SRS FR-GIN-001/002/004 | `world.depot.inbound.order`、其产品/托盘/SN 明细 | 复用，不新建第二套入库模型；确需保存的外部单号放入现有订单可用字段，缺字段时再做最小扩展 |
| 出库单 | SRS FR-GIN-003/006/008 | `world.depot.outbound.order`、产品/包装/SN 明细 | 复用；API03 当前按 A-003 Solis→Odoo 开发假设实现，Ginlong 确认相反时再调整 |
| 客户盘点指令 | SRS FR-GIN-005/010 | `world.depot.stocktake.order` | 源码及既有 ORM 核查确认当前缺失；在 `worlddepot` 增加最小业务模型，保存 API05 指令字段和计划范围；不访问库存账 |
| 仓库实盘结果 | SRS FR-GIN-010 / V3.2 API10 | `world.depot.stocktake.result` | 源码及既有 ORM 核查确认当前缺失；在 `worlddepot` 增加最小实盘结果模型，每条结果关联客户盘点指令并保存实际 SN、产品、数量、托盘及真实作业人/时间；不创建库存移动或调整 |
| Ginlong 产品主数据 | V3.2 API07 | `_inherit = 'product.product'`；共享属性按字段语义扩展 `product.template` | 复用现有产品主数据；不新建产品模型或默认映射表；产品定位及建档行为服从现有 WMS 规则和已确认契约 |
| API 追溯日志 | SRS NFR-GIN-AUD-001 | `world.depot.api.log` | 复用现有请求/响应/异常/状态/时间字段；只补齐检索接口和业务记录所必需且当前确实缺失的字段 |
| 回传记录 | SRS §6.1(7) | `world.depot.api.log` | 复用现有日志字段记录本次请求、响应及结果；不另建尝试模型或状态字段 |

### 3.2 字段契约

#### 3.2.1 订单映射字段

| 外部字段 | Odoo 候选来源 | 映射规则/状态 |
|---|---|---|
| `owner` | 现有 inbound/outbound order 货主字段 | 按接口字段映射；不增加 owner 与 product 归属校验 |
| `warehouse` | 现有订单/仓库字段 | 按 Ginlong 确认的字段映射到现有对象 |
| `inboundOrderNo` / `outboundOrderNo` | 现有订单编号字段；必要时最小扩展 | 不新建外部映射模型；重复规则待契约确认 |
| `businessType` | 订单 `type` / 项目类型 | 源值到 Odoo 值的映射尚未提供，按正式契约和现有 WMS 字段确定，不设置默认转换 |
| API02 `receiptConfirmed` | `world.depot.inbound.order.status` | 从现有入库 Order 状态取值；不从 picking 创建/状态或库存过账推断。外部字段若要求布尔值，只有在 Ginlong 与业务映射确认后才序列化；不擅自定义撤销值 |
| API08 `shipmentConfirmed` | `world.depot.outbound.order.status` | 从现有出库 Order 状态取值；不从 picking 创建/状态或库存过账推断。外部字段若要求布尔值，只有在 Ginlong 与业务映射确认后才序列化；不擅自定义撤销值 |
| `remark` | order `remark` | 按工作簿字符上限验证；不截断静默写入 |
| `productCode` | 现有订单行的 `product.product` | 按接口数据映射到订单行产品；不要求与 owner 建立归属关系。产品代码的查找字段/歧义处理按现有 WMS 产品主数据规则及正式接口契约确认 |
| `productName`, `specificationModel` | API07 的 `product.product` / `product.template` 扩展字段候选 | 按字段是否为变体级或模板共享属性选择存储层；更新/创建规则服从现有 WMS 产品主数据规则，迟到、重复及乱序覆盖仍待正式契约确认 |
| `quantity` | 现有入/出库行或盘点字段 | 使用 Odoo 现有字段类型和精度；单位、数量小数位和序列化规则按正式契约确认 |
| API03 收件方字段 | `unload_company`、`delivery_street/city/zip/country`、`delivery_phone/mobile/email` | 多个来源字段到 `address/contact` 的拼装规则待确认；不丢弃原始输入 |
| API03 包装字段 | `world.depot.outbound.order.pack.info`、产品/包装字段 | 现有尺寸为 cm，工作簿尺寸为 mm；统一映射和换算经确认后才启用；重量、包装粒度待字段映射表确认 |
| `operator`, `operationTime` | 现有可追溯业务字段 | 按确认后的字段映射取值；不以点击按钮者或当前时间代替业务来源 |

#### 3.2.2 盘点专用模型字段

| 模型/字段 | 类型 | 来源/约束 |
|---|---|---|
| `world.depot.stocktake.order.count_order_no` | Char | API05/10 `countOrderNo`；按项目/调用方范围查找，不增加模型全局唯一约束 |
| 盘点指令货主、项目、仓库、备注、目标范围 | Char / Many2one / Text | 由 `worlddepot` 客户订单模型保存；计划明细与计划 SN 范围以 JSON 字段保存在订单上，不创建第三个计划明细模型 |
| `world.depot.stocktake.result.order_id` | Many2one | 关联对应客户盘点指令；不关联 `stock.quant` |
| 实盘结果 SN、产品、数量、托盘、操作人、作业时间 | Char / Many2one / Float / Datetime | 由 `worlddepot` 实盘结果模型逐条记录；缺失值保持空，不用回传用户/点击时间或计划值填充 |

API05/10 只访问 `worlddepot` 盘点指令与实盘结果，不读写或推算 `stock.quant`，不调用 `stock.move`、库存调整或过账服务。完整源码及 `odoo shell -c odoo.conf --no-http` ORM registry/field 核查确认原 `worlddepot` 缺少这两个模型；旧 `ginlong.stocktake.task` 与 `.line` 的 ORM 记录数均为 0，除 Ginlong 服务、测试及 ACL 外无引用。因此在 `worlddepot` 内实现两个最小模型，将 API05 改为写客户盘点指令，API10 只从实盘结果读取；移除旧 Ginlong 盘点模型及其 ACL。API09 的库存查询按已确认范围只读库存。数量采用 Odoo 现有字段类型及精度处理。

#### 3.2.3 产品与日志扩展

- API07 直接使用 `product.product`，确需的 SKU 字段通过 `_inherit` 扩展；模板共享属性才放 `product.template`。不新建 Ginlong 产品档案或映射表。
- `world.depot.api.log` 已有 `request_time`、`request_data`、`response_data`、`exception_details`、`status`。优先复用这些字段；如实现中确实需要按接口/单据检索且现有字段无法表达，仅增加必要的接口编号和业务记录引用。操作者使用 Odoo 标准创建人字段。
- 请求、响应和异常中必须过滤 Secret、Token、Authorization、签名等凭据；业务 Payload 不做整体脱敏。

### 3.3 方法契约

| 行为 | 实现 |
|---|---|
| API01/03/05/07/09 入站 | 在控制器中校验必要格式及权限，映射到现有业务对象；API03 当前按 A-003 开发假设处理；API05 写入 `worlddepot` 客户盘点指令 |
| API02/04/06/08/10 回传 | 对应业务 Order 上的普通 Odoo 按钮打开业务确认 Wizard；用户确认后后台生成 JSON、同步 HTTP 调用并写现有 API 日志；不自动触发或重试 |
| 盘点 API05/10 | API05 客户盘点指令与 API10 仓库实盘结果分别由 `worlddepot` 两个业务模型持有；不读写或推算库存账 |
| API07 | 更新现有 `product.product`，遵循现有 WMS 产品主数据能力 |

## 4 数据约束与索引

只添加接口契约和 Odoo ORM 正常运行所必需的字段约束。`countOrderNo` 的唯一范围、订单外部编号重复处理等以 Ginlong 正式契约为准；未确认前不新增猜测性唯一键、覆盖规则或归属约束。盘点任务和结果按其父子关系关联。

## 5 接口字段与报文

### 5.1 对外接口契约清单

V3.2 字段表含示例与数据类型，但最终 URL/HTTP 方法/鉴权/错误码契约尚未提供；下表用于本地模拟和字段映射，不是 Ginlong 正式报文契约。路由、方法、Content-Type、签名、状态码必须从正式文档导入。

| API | 方向（SRS/A-003） | Odoo 对象 | 字段组（V3.2 来源行） | 协议状态 |
|---|---|---|---|---|
| 01 待入库单 | Solis→Odoo | inbound order | owner/action/inboundOrderNo/warehouse/businessType/remark；details(productCode/name/specificationModel/quantity)；snList(productSN/quantity/palletCode/productCode/name/specificationModel)；行5–20 | 字段可模拟；action/重复/更新行为和 wire contract 待确认 |
| 02 收货确认 | Odoo 手动→Solis | `worlddepot` inbound Order button | inboundOrderNo、对应 Order 的现有收货业务状态→receiptConfirmed；响应字段行21–23 | 复用现有 Order 字段；action 值/撤销语义待 Ginlong 确认 |
| 03 待出库单 | Solis→Odoo（A-003 开发假设） | outbound order | owner/action/outboundOrderNo/warehouse/businessType/remark/customer/address/consignee/contact/email/shippingMethod；details 含商品、数量、包装、重量、尺寸；行33–66 | A-003 非外部确认；方向及协议细节待确认 |
| 04 入库完成 | Odoo 手动→Solis | inbound Order button | 关联实际 `stock.picking`/`stock.move.line` 的 productSN/quantity/palletCode/productCode/operator/operationTime；行24–32 | 以实际入库作业记录为来源；整单/部分及撤销语义待确认 |
| 05 盘点单 | Solis→Odoo | `worlddepot` 客户盘点指令模型 | owner/action/countOrderNo/warehouse/remark；details 与 snList 指令范围；行81–95 | 不新建 Ginlong 盘点业务模型，不访问库存账；动作/删除判据待确认 |
| 06 备货完成 | Odoo 手动→Solis | outbound Order button | Odoo `stock.picking`/`stock.move.line` 实际作业记录；payload 字段见行67–77 | 源码发现 `set_status_to_pick_finished` 是 Hoymiles 外部回调成功标记，不是 Ginlong/KR 现场备货事件；不将其冒充业务数据，不以 picking 创建/确认/库存过账替代备货完成信息；不增加状态门禁、审批或业务限制。真实备货事件字段/语义缺失只阻塞依赖它的 Payload 场景 |
| 07 物料档案 | Solis→Odoo | 现有 `product.product`（必要时扩展 `product.template` 共享属性） | owner/productCode/name/specificationModel/unit/power/nationalStandard/certificationModel/productForm/weight/length/width/height；行105–117 | 不建 Ginlong 产品模型/默认映射表；owner 字段及产品创建/更新行为待确认 |
| 08 发货完成 | Odoo 手动→Solis | `worlddepot` outbound Order button | outboundOrderNo、对应 Order 现有出库业务状态→shipmentConfirmed；响应通用字段；行78–80 | 使用现有订单状态，不从库存过账推断；action 示例与字段表冲突，待确认 |
| 09 库存查询 | Solis→Odoo | 只读库存查询服务 | request(owner, warehouse)；response(returnStatus/exceptionInfo/operationTime/owner/warehouse/inventoryList[productCode,quantity])；行118–124 | 数量口径、过滤、分页和状态待确认；只读 `stock.quant` 候选 |
| 10 盘点完成 | Odoo 手动→Solis | `worlddepot` 客户盘点指令按钮；读取关联仓库实盘结果 | owner/action/countOrderNo；snList(productSN/quantity/palletCode/productCode/operator/operationTime)；行96–104 | 只从实盘结果读取；不使用计划值、`stock.quant` 或平行模型；部分采集及 action 待确认 |

### 5.2 字段解析

不建立第二套内部 canonical JSON Schema。正式协议确认后，直接按已确认的字段名、类型和必填规则解析报文。现阶段可按 V3.2 已知字段做本地模拟，并执行 SRS 要求的格式、完整性和权限检查；字段冲突、未定义枚举和单位不自行推断。

### 5.3 外部协议差异登记

| ID | V3.2 资料差异 | 处理 |
|---|---|---|
| EXT-01 | API02/08 字段表写“确认/取消”，JSON 示例写 `action: UPDATE` 且另带布尔值 | 不映射 action 值，待 Ginlong 定义合法请求与撤销方式 |
| EXT-02 | API05/10 字段表写 CREATE/DELETE，API10 名称/触发逻辑描述为“盘点完成” | 按用户批准仅做手动按钮；CREATE/DELETE 对应的回传动作待确认 |
| EXT-03 | API10 一处支持同单分批采集，另一处要求整单采集完成后调用 | 不决定多次回传/局部选行/撤销规则；设计可保存多条采集结果，发送范围待确认 |
| EXT-04 | API07 owner 在头部/示例/蓝图表出现，但接口主字段列表从 productCode 起 | owner 是否为必填字段待确认；不得据此建立 owner+productCode 唯一键或归属校验 |
| EXT-05 | API03 示例 JSON 有全角逗号、缺逗号/键顺序等格式问题；方向描述不一致 | 示例仅作字段参考；当前按 A-003 Solis→Odoo 假设实现，正式方向确认后调整入口和字段映射 |
| EXT-06 | API03 尺寸字段 mm 与现有包装字段 cm 不同；product dimension 单位未说明 | 禁止无单位转换；待双方签认长度、重量、体积和舍入规则 |

## 6 领域行为实现

### 6.1 接口到现有对象

| 接口 | Odoo 处理对象 | 处理方式 |
|---|---|---|
| API01 | `world.depot.inbound.order` 及现有明细 | 按接口字段创建/更新现有入库单；调用现有 WMS 作业能力 |
| API03 | `world.depot.outbound.order` 及现有明细 | 当前按 Solis→Odoo 开发假设处理；确认反向后调整入口和字段映射 |
| API05 | `worlddepot` 客户盘点指令 | 复用等价现有模型；如无则在 `worlddepot` 最小扩展，不在 `ginlong_apis` 建模；不访问库存账 |
| API07 | `product.product` | 复用现有产品档案，必要时以 `_inherit` 增加字段 |
| API09 | 现有库存查询数据 | 按确认的过滤条件只读查询 |
| API02/04/06/08/10 | 对应入库/出库/盘点 Order 按钮与 Transient Wizard | 用户点击后展示业务数据；确认后后台生成 JSON，同步调用 Ginlong API 并记入现有日志 |

API01/03 的 owner 和 product 字段分别映射，不增加归属校验。不得复制 WMS 的入库、出库、拣货、上架或库存记账逻辑。

### 6.2 处理流程

**入站接口**：接收请求 → 复用现有认证 → 做权限及字段格式/完整性检查 → 映射到现有 WMS/产品/盘点对象 → 使用现有 API 日志记录请求、处理结果和响应。

**五个人工回传按钮**：业务 Order → 点击「回传锦浪」→ 标准 Wizard 展示订单号、业务事件、关联作业单和关键数据 → 仅补充确实缺失且已确认必填的信息 → 用户确认 → 后台生成 JSON → 设置超时并同步 HTTP 发送 → 现有 API 日志保存请求 JSON/响应/错误，供管理员和技术人员查看 → 页面向业务用户显示成功或失败。业务用户不查看或编辑 JSON，不提供 JSON 编辑器/技术调试页；失败或超时不自动重试。

API05/10 使用 `worlddepot` 客户盘点指令与仓库实盘结果模型；API10 从实盘结果关联客户盘点指令取数，不读取 `stock.quant` 推算或改写 Odoo 库存数量。若实盘模型缺失，仅可在 `worlddepot` 最小扩展。

### 6.3 作业复用界限

直接复用现有 WMS 模型和业务方法，不复制入库、出库、拣货、上架、扣减或库存记账逻辑。若某项现有功能没有可直接调用的方法，实施时只做满足 Ginlong 接口所需的最小补充，并保持原 WMS 行为不变。

## 7 HTTP、认证与配置

- 回传使用标准 Python HTTP 客户端，在 Odoo 按钮方法中同步调用；设置合理的连接和读取超时，不自动重试。实际超时值可沿用项目现有设置；若没有，再按 Ginlong SLA 配置。
- 入站认证优先复用 `worlddepot` 当前 API 用户和 Token 校验；是否与 Ginlong 的正式认证契约兼容仍待确认，不新建平行用户/Token 体系。
- 回传鉴权严格按 Ginlong 正式资料实现；不复制 Hoymiles 专属鉴权。优先沿用现有配置入口，不新建 endpoint 配置模型或 secret provider。
- Endpoint 和凭据只放入项目现有受控配置；不得写入源码、XML、请求 URL、日志或错误提示。HTTP 使用 HTTPS 并校验证书。
- 请求/响应使用锦浪确认的原始字段结构，不经额外中间 Schema 或通用 Adapter 转换。

## 8 调用方式

本稿确定五个人工回传按钮同步调用：API02/04/06/08/10 由用户点击后各调用一次 HTTP，显示结果并写入现有 API 日志；不自动触发或重试。其余入站接口按 SRS 及 Ginlong 已确认契约实现，本稿不额外引入异步处理设施。

按钮使用标准 Odoo 方法同步处理。外部请求一旦被对方处理，Odoo 后续事务回滚无法撤销该外部处理；超时按结果未知记录，不自动重试。

## 9 结果记录

不建立 Ginlong 专用技术状态机。复用 `world.depot.api.log` 的 `status`、`request_data`、`response_data`、`exception_details` 和 `request_time` 记录处理结果。HTTP 响应只表示对端返回了响应；是否表示业务接受，按正式契约解释。超时或连接中断写入现有错误详情并向用户说明结果未知，不自动重发。

## 10 重复操作

外部编号唯一范围、重复点击及结果未知后的再次操作按 Ginlong 确认规则处理；未确认前不实现覆盖或自定义幂等规则。

## 11 错误处理

沿用 Odoo 现有异常和用户提示方式。格式/完整性错误指出对应字段；HTTP 错误、超时和响应解析失败写入现有 API 日志，并向操作人员显示简明原因。不得向页面或日志输出 Secret、Token、Authorization、签名、SQL 或完整堆栈。外部状态码及业务成功标志待锦浪契约确认，不建立独立错误码体系或告警服务。

## 12 权限与安全

- 复用现有 WMS 用户组、API 用户、record rules 和菜单权限。新增盘点模型只配置必要 ACL；只有证据表明现有权限无法覆盖时，才另行评审最小权限补充，不预设 Ginlong 操作员/管理员/审计员角色体系。
- 入站请求使用现有 API 用户权限边界，禁止未经授权的 `sudo()` 访问数据。按 SRS 执行必要的权限、安全、数据完整性和格式校验，不增加业务状态门槛。
- 修复共享 API logger 中可能把 Secret、Token、Authorization 或签名写入应用日志/数据库日志的路径。出错时只记录安全错误信息。
- HTTPS/TLS 必须开启并验证证书；配置界面和凭据权限沿用现有 Odoo 管理方式，不引入独立安全框架。

## 13 Odoo 按钮和页面

五个按钮都放在对应 Order 表单：API02/04 位于入库单，API06/08 位于出库单，API10 位于 `worlddepot` 客户盘点指令。点击后打开标准 Transient Wizard，展示订单号、回传业务事件、关联作业单及关键业务数据；API02/08 展示对应 Order 业务状态，API04/06 展示实际产品/SN/数量/托盘等作业信息，API10 展示仓库实盘结果。仅对现有记录确实缺失且 Ginlong 已确认必填的字段显示补充输入。业务用户不查看、不编辑 JSON。用户确认后后台生成 JSON 并发送 HTTP；请求 JSON、响应及错误写入现有 API 日志，供管理员和技术人员查看，业务用户只见成功/失败反馈。权限沿用现有 WMS 用户组；不增加额外状态机或库存调整动作。

## 14 测试设计

### 14.1 测试分层

| 层级 | 目标 |
|---|---|
| Odoo 单元/ORM | 字段映射、`worlddepot` 盘点指令/实盘结果、权限和正常 ORM 行为 |
| 本地模拟 HTTP | 后台 Payload 字段、成功/失败/超时结果、无自动重试及日志内容 |
| 手工界面 | 五个按钮从 Order 打开业务确认 Wizard；用户查看业务数据，确认后结果正常显示 |
| 真实联调 | Ginlong 提供正式协议、环境和测试凭据后执行；当前未执行 |

### 14.2 必测约束

- 每个 SRS FR/AC 至少一个 `TEST-*`；T guardrails 必须有负向测试。
- API05/10 只读写 `worlddepot` 盘点指令/实盘结果；禁止使用 `stock.quant` 推算盘点、调用库存调整或过账服务；验证盘点记录不会改变库存数据。API09 单独覆盖只读查询。
- 用假凭据测试日志和错误路径；检查 DB log/application log/response/trace 不含明文。
- 每个回传按钮只在用户点击时发起一次 HTTP；状态变化、cron、安装/升级或重启不触发回传；失败后无自动重发。
- 外部重复键、action 枚举、批量/撤销、stock query 数量口径等未确认场景只验证系统不擅自写入/发送，不为外部规则判通过。

### 14.3 测试矩阵

| TEST | 契约 | Given / When / Then | 状态 |
|---|---|---|---|
| TEST-GIN-001 | FR-GIN-001 / T-API-001 | 有效 API user + 映射字段；发 API01；创建现有 inbound order 与关联日志 | Planned / Not Run |
| TEST-GIN-002 | FR-GIN-003 / T-API03-001 | 按 A-003 Solis→Odoo 假设模拟 API03 并写现有 outbound order | Planned / Not Run; external direction unconfirmed |
| TEST-GIN-003 | FR-GIN-005 / T-COUNT-001 | API05 将指令写入 `worlddepot` 客户盘点订单；旧 Ginlong task 路径不再作为业务模型；无 `stock.quant`/库存记账 | Planned / Not Run |
| TEST-GIN-004 | FR-GIN-010 / T-COUNT-001 | API10 从 `worlddepot` 仓库实盘结果关联客户盘点指令，读取真实结果；不使用计划值/`stock.quant`；无库存过账 | Planned / Not Run; batch semantics OPEN |
| TEST-GIN-005 | FR-GIN-007 | API07 对现有 `product.product` 执行经 WMS 主数据规则允许的字段更新/建档；不创建 Ginlong mapping，也不验证 owner-product 归属 | Planned / Not Run; WMS 产品定位规则待核实 |
| TEST-GIN-006 | FR-GIN-009 | API09 只读；owner、warehouse/location、product 分别按已确认的字段映射限定查询，不执行 owner-product 归属校验；口径确认后比对数量边界 | Blocked by inventory semantics / Not Run |
| TEST-GIN-007 | FR-GIN-002/004/006/008/010 / T-CALLBACK-001 | 用户点击 Order 按钮后 Wizard 展示业务数据；用户确认后后台生成 JSON、只产生一次对应 Mock HTTP 请求并写入现有日志；业务用户不可查看/编辑 JSON | Planned / Not Run |
| TEST-GIN-008 | T-CALLBACK-002 | 模拟 timeout、HTTP error、malformed response；业务页面显示错误或结果未知，管理员可从现有日志查看 JSON/响应/错误；无自动重试 | Planned / Not Run |
| TEST-GIN-009 | T-SEC-001 | 注入 api_secret/access_token/Authorization/signature；数据库日志、应用日志及错误提示均无明文 | Planned / Not Run; security remediation prerequisite |
| TEST-GIN-010 | T-SEC-001 | 缺 token、过期 token、inactive API user 或越权请求被现有认证/权限拒绝 | Planned / Not Run |
| TEST-GIN-011 | 原 TD-003 | Retired in v0.3：专项事务验证已取消；常规按钮行为由 TEST-GIN-007/008 覆盖 | Not Applicable / retired |
| TEST-GIN-012 | NFR-GIN-AUD-001 / T-LOG-001 | 按现有日志字段查看请求、响应、错误和结果；日志中无凭据明文 | Planned / Not Run |

除明确标为 retired 的 TEST-GIN-011 外，其余状态均为计划状态，不代表执行结果。实施阶段应记录实际证据。

## 15 日志

复用 `world.depot.api.log`。现有字段覆盖请求时间、请求内容、响应内容、错误详情和结果状态；实现前核对接口/单据检索是否已有字段，确有缺口时只增加必要字段。按钮调用记录一次请求和响应/错误。使用现有日志视图和访问权限，不另建指标、监控或告警体系。

## 16 配置与迁移

复用 Odoo `res.config.settings` 与 `ir.config_parameter` 配置每个回传 API 的 Endpoint URL 和 HTTP Method，不新增 endpoint 表或 secret provider；配置不完整时禁止发送并显示提示。Ginlong 暂无鉴权/Key；其余协议字段不得由配置默认值猜测。已通过源码及 ORM 确认 `worlddepot` 原先缺少盘点订单与实盘结果模型，按批准范围在其中最小扩展；删除 `ginlong.stocktake.task` 前已通过 ORM 确认任务及明细记录均为 0，并通过源码核对其仅被旧 API05 服务、测试和 ACL 引用；升级时移除旧模型与 ACL，不直接 SQL。

## 17 风险与待确认项

| 风险/依赖 | 影响与处理 |
|---|---|
| Ginlong 协议资料不完整 | 先按已知字段本地模拟；正式 endpoint、方法、鉴权和返回语义确认后再联调 |
| API03 方向未确认 | 暂按 Solis→Odoo 开发；收到 Ginlong 确认后调整接口方向 |
| 超时后结果未知 | 写现有 API 日志并提示用户，不自动重试；重复操作规则待外部确认 |
| Secret/Token 进入日志 | 修复共享 logger 并验证后方可启用接口 |
| API09 库存口径未定 | 只读查询；货主/仓库/产品过滤和数量口径待确认 |
| 盘点职责误入库存记账 | API05/10 隔离盘点任务和结果，禁止操作库存账 |

## 18 实施约束

| 编号 | 约束 |
|---|---|
| T-API-001 | 路由、HTTP 方法及报文按 Ginlong 正式契约实现；资料未齐时只做本地模拟 |
| T-API03-001 | API03 暂按 Solis→Odoo 开发假设，不声称为已确认外部事实 |
| T-WMS-001 | 复用现有 WMS 订单、产品和业务处理，不复制库存/订单作业 |
| T-COUNT-001 | API05/10 使用worlddepot 客户盘点订单和仓库实盘结果；不访问/读写 `stock.quant` 或 `stock.move` |
| T-CALLBACK-001 | API02/04/06/08/10 只由对应 Odoo 按钮手动触发 |
| T-CALLBACK-002 | 回传同步调用、设置超时、不自动重试 |
| T-SEC-001 | 复用现有权限和认证；凭据不得进入数据库日志、应用日志或用户提示 |
| T-LOG-001 | 使用现有 API 日志记录请求、响应/错误和结果 |
| T-STOCK-009 | API09 只读；库存数量口径和过滤条件按确认后的字段契约实现 |

## 19 需求追溯矩阵

### 19.1 SRS → TDD

| SRS | TDD 落点 | 后续验证 |
|---|---|---|
| FR-GIN-001 | §§3.1, 3.2.1, 5.1, 6.1, API01 | TEST-GIN-001 |
| FR-GIN-002 | §§5.1, 6.1, 7, 13, T-CALLBACK-001 | TEST-GIN-007/008 |
| FR-GIN-003 | §§3.1, 3.2.1, 5.1, 6.1, 7 | TEST-GIN-002 |
| FR-GIN-004 | §§3.2.1, 5.1, 6.1, 13 | TEST-GIN-007 |
| FR-GIN-005 | §§3.1–3.2.2, 5.1, 6.1, T-COUNT-001 | TEST-GIN-003 |
| FR-GIN-006 | §§3.2.1, 5.1, 6.1, 13 | TEST-GIN-007 |
| FR-GIN-007 | §§3.1, 3.2.3, 5.1, 6.1 | TEST-GIN-005 |
| FR-GIN-008 | §§5.1, 6.1, 7, 13 | TEST-GIN-007/008 |
| FR-GIN-009 | §§3.1, 3.2.1, 5.1, 6.1, T-STOCK-009 | TEST-GIN-006 |
| FR-GIN-010 | §§3.1–3.2.2, 5.1, 6.1, 13, T-COUNT-001 | TEST-GIN-004 |
| SRS §6.1(3),(7) / §6.2 | §§9, 11, 15, T-LOG-001 | TEST-GIN-008/012 |
| NFR-GIN-SEC-001/002 | §§7, 12, T-SEC-001 | TEST-GIN-009/010 |
| NFR-GIN-REL-001 | §§7–10, T-CALLBACK-002 | TEST-GIN-008 |
| NFR-GIN-AUD-001 | §§3.2.3, 12, 15, T-LOG-001 | TEST-GIN-009/012 |
| OPEN-GIN-002/004/005/006/007/008/011/012 | §§0.4, 5.1/5.3, 7, 8, 16/17 | 对应接口真实联调前按依赖确认 |

### 19.2 TDD → TEST

| 约束 | 覆盖用例 | 状态 |
|---|---|---|
| T-COUNT-001 | TEST-GIN-003/004 | Planned / Not Run |
| T-CALLBACK-001/002 | TEST-GIN-007/008 | Planned / Not Run |
| T-SEC-001 | TEST-GIN-009 | Planned / Not Run |
| T-LOG-001 | TEST-GIN-009/012 | Planned / Not Run |
| API01/03/05/07/09 字段处理 | TEST-GIN-001/002/003/005/006 | Planned / Not Run |

## 附录 A 术语表

| 术语 | 含义 |
|---|---|
| 本地模拟 | 无 Ginlong endpoint 时，通过模拟数据验证字段映射和处理路径；不代表真实联调 |
| 未知结果 | 请求可能到达对方但无可确认响应；记录现有日志并等待外部规则，不自动重试 |

## 附录 B 技术决策记录（TD）

| 编号 | 决策 | 评估/理由 |
|---|---|---|
| TD-001 | 建立轻量 addon `ginlong_apis` 并复用 `worlddepot` | 集成层只负责数据映射和 API 调用，不复制 WMS 业务 |
| TD-002 | API05/10 使用worlddepot 客户盘点订单及仓库实盘结果 | 满足盘点用途；不读写库存账。结果模型保留，以支持多条采集结果及操作人/时间追溯 |
| TD-003 | **原专项事务验证已撤销；编号保留，不作为当前实现方案或冻结条件** | 原 v0.2 评估不再约束本稿；普通按钮流程由 TD-010 决定 |
| TD-004 | 复用现有 API 日志，修复凭据泄露 | 使用现有字段，只补充检索接口/业务记录必需的缺失字段 |
| TD-005 | API03 暂按 Solis→Odoo 开发假设 | 不建立 direction adapter；收到正式方向后调整路由和字段映射 |
| TD-006 | 产品字段直接复用 `product.product` | 不另建 Ginlong 产品档案/映射表或 owner-product 规则 |
| TD-007 | 五个人工回传按钮不自动触发、不自动重试 | 按 SRS 手动触发要求执行 |
| TD-008 | 直接按 Ginlong 确认的报文字段解析 | 不建立额外 canonical schema；字段冲突仍待外部澄清 |
| TD-009 | 已撤销（与 TD-006 重复） | 编号保留，不形成额外设计要求 |
| TD-010 | 手动按钮使用标准 Odoo 方法同步调用 HTTP | 只做一次有超时请求，复用现有日志并显示结果 |

## 附录 C 版本变更记录

| 版本 | 日期 | 变更摘要 | 决策人/状态 |
|---|---|---|---|
| v0.1 | 2026-11-16 | 初版 TDD 草案；记录 10 接口对象映射、独立盘点模型、手动回传及外部待决事项 | Draft |
| v0.2 | 2026-11-16 | 按评审修订产品复用、盘点独立建模、字段映射、日志安全及外部依赖 | Draft；未冻结 |
| v0.3 | 2026-11-16 | 按减法评审撤销 TD-003 专项事务验证及原 T-TRX-001/002 事务 Guardrails，简化技术状态、Adapter/Schema/配置/监控/角色设计；回传改普通 Odoo 按钮同步调用并全部放在对应订单表单；复用现有 API 日志、认证、配置和 WMS 权限；数量使用 Odoo 常规字段精度 | 李建强（项目用户明确指令）；FROZEN WITH OPEN ITEMS。项目模板同步检查 BLOCKED，按用户授权冻结 |
| v0.4 | 2026-11-17 | 按 CC-GIN-003 v1.1 Human Review APPROVED，修订 API02/08、API04/06、API10 数据来源与三系统职责；回传 Wizard 仅呈现业务数据，JSON 后台生成；API06 不新增备货状态门禁；经源码/ORM 确认缺少客户盘点订单及实盘结果后，限定在 `worlddepot` 内补足两模型并移除 0 记录的 Ginlong 平行盘点模型；外部 action/objectid/method 等未决项继续隔离 | 李建强；FROZEN WITH OPEN ITEMS；模板同步 BLOCKED（沿用已批准流程例外） |

## 附录 D 设计依据与源码证据

| 证据 | 用途 |
|---|---|
| [冻结 SRS v1.0](../requirement/SRS_ginlong_apis.md) | 唯一业务需求基线及 OPEN 项 |
| [有条件批准的 TV v0.2](../context/report/TV_ginlong_apis_v0.2.md) | 静态验证事实、对象映射建议和批准记录 |
| [Ginlong V3.2 工作簿](海外WMS与第三方系统集成V3.2.xlsx) | 字段、样例、触发说明的来源；不是已确认最终 wire contract |
| [`worlddepot` manifest](../../mymodules/worlddepot/__manifest__.py) | 模块依赖及当前集成模块边界 |
| [入库模型](../../mymodules/worlddepot/models/inbound_order.py) | `world.depot.inbound.order` 与产品/托盘/SN 结构 |
| [出库模型](../../mymodules/worlddepot/models/outbound_order.py) | `world.depot.outbound.order`、产品及序列号结构 |
| [出库包装模型](../../mymodules/worlddepot/models/outbound_order_pack_info.py) | 当前包装尺寸（cm）和重量字段 |
| [API 用户与 Token 模型](../../mymodules/worlddepot/models/my_api_user.py) | 当前 bcrypt Secret、API user、明文 Token 存储结构 |
| [API 日志模型与 logger](../../mymodules/worlddepot/controllers/api_logs.py) | 当前原始请求/响应记录路径及日志扩展目标 |
| [认证控制器](../../mymodules/worlddepot/controllers/auth_controller.py) | 当前 token 发放和 auth response 路径 |
| [Token validator](../../mymodules/worlddepot/controllers/validator_token.py) | 当前 token 校验及应用日志风险 |
| [产品档案扩展](../../mymodules/wd_product_profile/models/product_template.py) | 可复用产品 profile 字段候选 |
| [`worlddepot` 产品继承](../../mymodules/worlddepot/models/my_product.py) | 验证已有 `_inherit` 扩展 `product.template` / `product.product`；未发现货主+产品编码字段/唯一约束 |
| [`wd_product_profile` 产品变体扩展](../../mymodules/wd_product_profile/models/product_product.py) | 验证现有 `product.product` 可由项目 addon 继承扩展 |
| [worlddepot 盘点模型](../../mymodules/worlddepot/models/stocktake.py) | 两模型源码及字段边界；实际 ORM 升级/验收结果以 ATR-GIN-003 为准 |
| [TDD 模板副本](../skill/odoo-project-workflow/references/templates/Designing/TDD模板.md) | 结构参考；项目模板同步脚本因来源缺失而 BLOCKED |

## 冻结自查清单

- [x] 10 个接口及字段来源保留；外部协议未确认项明确列出。
- [x] API05/10 独立盘点任务和结果，不触碰库存账。
- [x] 五个人工按钮同步调用、超时、无自动重试。
- [x] 复用现有 WMS 模型、认证、权限、配置和日志；凭据不进入日志。
- [x] 不新增 canonical schema、专用状态机、回传锁、独立监控和多角色机制。
- [x] CC-GIN-003 v1.1 Human Review APPROVED 后，TDD v0.4 修订为当前实施基线；历史 v0.3 原文件保留不覆盖。
- [x] 10 个接口、五个订单表单回传按钮和 API05/10 库存隔离已追溯。
- [x] Ginlong 协议、API03 方向和 API09 数量口径等未决项按真实联调依赖保留。
- [ ] 项目模板来源同步检查：BLOCKED，缺少 `docs/context/cognition/template/Designing/TDD模板.md`；用户授权本次冻结，检查未改写为 Passed。
