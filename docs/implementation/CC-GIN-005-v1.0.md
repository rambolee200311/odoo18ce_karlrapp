# CC-GIN-005 v1.0 — Ginlong 与 Odoo WMS 本地集成验收（Frozen with Open Items）

| 项目 | 内容 |
|---|---|
| CC ID / 版本 | CC-GIN-005 / v1.0 Frozen with Open Items |
| 状态 | Frozen with Open Items；Human Review：APPROVED（仅批准范围）；实施授权待上游基线更新 |
| Intent ID | `GINLONG-LOCAL-UI-WMS-E2E-005` |
| 范围 | Ginlong API 与 Odoo WMS 本地集成、产品变体适配、浏览器 UI/WMS 验收 |
| SRS | [SRS ginlong_apis v1.0 Frozen](../requirement/SRS_ginlong_apis.md) |
| TDD | [TDD v0.9 Frozen](../ginlong_apis/TDD-v0.9.md)；产品变体技术结论见本 CC 引用的 TV v1.0 |
| TV | [TV-GINLONG-PRODUCT-001 v1.0 Closed with Open Items](../context/report/TV_ginlong_product_variants_api07_sn_v1.0.md)；Human Review APPROVED |
| Implementation Plan | [v1.6 Frozen](IMPLEMENTATION_PLAN_ginlong_apis-v1.6.md)；阶段状态见 [v1.7](IMPLEMENTATION_PLAN_ginlong_apis-v1.7.md) |
| 前序 CC | CC-GIN-001–004 Closed；不重做其组件验收 |
| 后续阶段 | CC-GIN-006 真实 Ginlong 联调，须另行授权 |
| 模板同步 | BLOCKED；项目模板源缺失，沿用既有批准例外，不伪记为通过 |
| Human Review | APPROVED；李建强（项目用户）；2026-11-19；批准冻结范围，实施授权待上游基线更新 |
| 批准决定 | **APPROVED（范围批准，实施授权待上游基线更新）** |

## 修订记录

| 版本 | 状态 | 修订内容 |
|---|---|---|
| v0.1 | Draft | 初稿，覆盖本地 Ginlong API/Odoo WMS UI 集成与 E2E。 |
| v0.2 | Draft | 加入 API01/03 货主处理、API09 隔离及浏览器 HVR 范围；Gateway 作为可选测试。保留原稿。 |
| v0.3 | Draft | 根据已关闭 TV v1.0 重写产品变体与 API07 验收；仓库测试使用 Odoo 标准 `stock.picking`，不模拟 KR 作业或 Gateway。 |
| v0.4 | Review Draft | 按最新决策仅以现有 `KRWH` 测 API09 三组货主/产品库存；排除多仓库设计；限定 API07 冲突校验到已明确归属的共享字段；补充上游修订清单。 |
| v1.0 | Frozen with Open Items | Human Review APPROVED，仅冻结范围；实施授权待上游基线更新。 |

Human Review 于 2026-11-19 批准本 CC 的范围并冻结为 v1.0。该决定**仅批准范围，不授权编码或测试**。TV v1.0 中的产品模板/变体规则尚未纳入冻结 SRS、TDD 和 Implementation Plan；受影响实施须等待这些上游文档修订、批准并完成基线更新。模板同步保持 BLOCKED，按既有批准例外继续，不记为 PASS。本 CC 不修改上游文档、已关闭 CC-GIN-001–004 或历史证据。

## 1. 目的与系统边界

本 CC 包含 Ginlong 全部 10 个 API 的本地开发、Odoo WMS 集成和完整浏览器验收，并将 TV v1.0 批准的产品模板/变体方案及 API07 规则纳入验收。无需 KR 参与即可完成本地工作：入站 API 使用本地 Ginlong 请求；出站回传使用按业务来源准备的持久化 Odoo 测试记录及本地 Ginlong Mock；API09 查询 Odoo 库存。完成本地验收后，再由 CC-GIN-006 与 Ginlong 进行真实接口联调。

系统实际职责不变：Ginlong 下达业务指令；Karl Rapp（KR）负责实际收货、上架、拣货、SN 扫描及发货；Odoo 使用现有唯一仓库 `KRWH`，根据 KR 实际作业结果以 `stock.picking`、`stock.move.line` 和原生库存机制记录执行结果及库存，再向 Ginlong 提供数据。Gateway 属独立通信组件，不属于本 CC。

| 阶段 | Picking 数据来源 | 目的 |
|---|---|---|
| 当前 CC-GIN-005 | 开发并本地验收 API01–10。API01/03/05/07 使用本地 Ginlong 请求调用 Odoo；API02/04/06/08/10 使用按业务来源准备的 Odoo 记录发送至本地 Ginlong Mock；API09 查询 Odoo `stock.quant`。测试在 Odoo 中建立 `inbound.order`、`outbound.order`、`count.order`、产品、实盘结果及标准 `stock.picking` 记录。 | 不依赖 KR 完成 API01–10 的本地开发和端到端集成验收；验证订单、库存、托盘、SN、货主归属及 Ginlong API 读写。 |
| 后续 KR 集成 | KR XML → Gateway → Odoo；由转换后的 KR 实际作业结果自动创建/完成 `stock.picking`。 | 接通真实数据来源；库存仍由相同的 Odoo Picking/原生库存机制记录。 |

**两阶段使用相同的 Odoo 库存记录机制，区别仅在 Picking 数据来源。** 当前 CC-005 在 Odoo 中模拟创建并完成 `stock.picking`，作为 KR 实际作业结果写入 Odoo 后的本地测试记录；不需要 KR 参与，也不模拟 KR 现场操作，不构造 KR XML，不开发 XML 解析。测试直接通过 Odoo 标准 `stock.picking`、`stock.move.line` 及原生确认/过账流程建立本地记录，用来验证库存、SN、托盘和 Ginlong 回传读取；结果不代表 KR/Gateway 集成已通过。

Ginlong 的真实 HTTP 联调安排在本地 API01–10 集成验收完成后由 CC-GIN-006 承接；CC-GIN-005 不依赖 KR/Gateway 是否已接入。

## 2. 基线、决策与实施门禁

| 项目 | 当前依据及处置 |
|---|---|
| 冻结需求与设计 | Ginlong SRS v1.0、TDD v0.9；已关闭 CC-001–004 的组件验收结果只引用，不重复执行。 |
| 产品变体技术验证 | TV-GINLONG-PRODUCT-001 v1.0 已关闭，Human Review APPROVED；其产品字段归属、tracking 规则及 API 影响纳入本稿。 |
| 产品新规则的基线状态 | 一个 raw productCode 一个 product.template、owner 作为 product.product 变体、共享固有属性一致等事项尚未进入冻结 SRS/TDD/Implementation Plan。按 TV OI-09，CC 范围可按 Human Review 冻结；受影响实施须先完成上游影响评估、必要修订与批准，并更新计划及追溯。 |
| API01/03 项目负责人决定 | API01 按 Ginlong owner code 复用或创建货主档案；API03 要求货主与每条产品组合已存在，缺失时拒绝；产品档案由 API07 维护。引用 IHR-GIN-003 IHR-021 和 ATR-GIN-003 RUN-049–055。 |
| 已批准模板例外 | 技术验证模板同步脚本仍 BLOCKED，因项目模板源缺失；沿用既有批准的流程例外，不将 BLOCKED 写成 PASS。 |

## 3. 产品模型与 API 业务验收边界

产品方案以 TV v1.0 为技术评审依据；下列规则已纳入本 CC 的冻结范围，受影响实施须等待上游基线批准：

- 一个 Ginlong 原始 `productCode` 对应一个 `product.template`；同码不同 `owner` 对应不同 `product.product` 变体。
- 模板共享字段为产品名称、规格型号、重量、长度、宽度、高度、`productForm` 和由 `productForm` 决定的 `tracking`；变体保存 owner、内部组合编码和原始 Ginlong `productCode`。
- API07 对已明确为模板共享的字段校验同码一致性；发现冲突则拒绝请求并明确报错，现有模板/变体不得被部分修改。尚未确定字段归属的 `unit`、`power`、`nationalStandard`、`certificationModel` 等字段不增加额外冲突校验。
- API07 仅接受 原材料、半成品、成品；原材料对应 `tracking=none`，半成品/成品对应 `tracking=serial`。非法 `productForm` 拒绝；不新增 `snTrackingRequired`。
- API01/03/07 按 owner + 原始 productCode 定位产品变体；API09 只读库存并返回原始 productCode。
- KR 负责现场 SN 采集。Odoo 依据已保存的 stock.move.line / Lot 记录使用 Odoo 原生序列号跟踪；不在 Odoo 开发现场扫码流程。
- Odoo 原生 WMS 产品查找须按 owner 消歧；重复编码无唯一 owner 依据时应明确报告歧义，不任取第一条产品。

本 CC 的 API01/03/07 本地流程应先由 API07 建立产品档案，再以已存在的 owner + productCode 处理订单。API01 的货主创建/复用行为和 API03 的无效组合拒绝行为遵循 IHR-021 已批准决定；不重复开发其组件功能。

## 4. 范围

### 4.1 纳入 CC-GIN-005

1. 完成本地 API01–API10 开发及 Odoo 浏览器、ORM 集成验收：覆盖现有业务 Order、产品变体、五个人工回传 API02/04/06/08/10、API09 查询和相关 WMS 记录的端到端衔接；此阶段不依赖 KR 参与。
2. 在上游基线批准后，完成产品模板/变体字段调整和必要数据迁移；验证 API07 同码跨 owner 复用模板、创建/更新变体、共享属性一致性及冲突拒绝。
3. 对 API01/03 按 owner + raw productCode 的产品定位执行本地端到端回归；覆盖受影响的 worlddepot 产品查找路径及同码跨 owner 歧义处理。
4. 使用 Odoo 标准 stock.picking 和 stock.move.line 建立入库、出库测试记录，并经标准确认/过账操作形成库存；不直接改 stock.quant。用这些已保存业务记录验证 API04/06/08 数据读取、API09 库存隔离及产品、SN、托盘、货主关系。
5. API02 从入库 Order 已保存的收货明细/状态读取；API04 从实际已保存的入库 stock.picking / stock.move.line 读取。区分收货确认与入库完成。
6. API06 从 `outbound.order` 的模拟备货完成业务数据及对应已保存作业明细读取；不以 picking 创建或库存过账本身冒充备货完成。API08 使用出库 Order 已保存的发货状态；实际发货明细以已保存 picking/move line 为依据。区分备货完成与发货完成。
7. API10 从 worlddepot 客户盘点 Order 关联的实盘结果取数；API05 盘点指令和实盘结果保持分离，不使用 stock.quant 推算盘点结果、不做库存调整。
8. 验证五个人工回传接口继续使用业务 Order 上的持久化 Ginlong Form/Notebook：先保存、重新打开、用户点击按钮、同步 POST 到 Mock Ginlong、记录每次独立日志；失败后修正并人工重发。
9. API09 只使用现有唯一仓库 `KRWH`，通过标准 Odoo 库存流程建立测试库存，验证货主/产品隔离、实际物理数量、不扣预留量、原始 `productCode` 回传及严格只读；不创建第二个仓库、不设计多仓库分配，也不把本地 `stock.picking` 测试称为 KR 库存同步验证。
10. 仅执行本 CC 触及的自动化、必要 ORM 集成和浏览器 E2E 回归，不重复 CC-001–004 的组件测试。

#### API01–API10 本地测试数据来源

| API | 接口 | 本地集成测试数据来源 |
|---|---|---|
| 01 | 入库单 | 本地 Ginlong API 请求 → Odoo `inbound.order`。 |
| 02 | 收货确认 | 模拟已保存的 `inbound.order` 收货明细及确认状态。 |
| 03 | 出库单 | 本地 Ginlong API 请求 → Odoo `outbound.order`。 |
| 04 | 入库完成 | Odoo 标准流程建立并完成的入库 `stock.picking`。 |
| 05 | 盘点单 | 本地 Ginlong API 请求 → Odoo `count.order`。 |
| 06 | 备货完成 | 模拟 `outbound.order` 备货完成业务数据；涉及实际产品、数量、SN 或托盘时读取其已保存关联作业明细。 |
| 07 | 物料档案 | 本地 Ginlong API 请求 → Odoo 产品模板及 owner 对应的产品变体。 |
| 08 | 发货完成 | Odoo 标准流程建立并完成的出库 `stock.picking`。 |
| 09 | 库存查询 | Odoo `stock.quant`；测试库存由标准 `stock.picking` 流程形成，仅使用现有 `KRWH`。 |
| 10 | 盘点完成 | 模拟 `count.order` 关联的已保存实际盘点结果。 |

API01/03/05/07 使用本地请求覆盖 Ginlong→Odoo 路径；API02/04/06/08/10 使用上述已保存或模拟业务记录，调用本地 Ginlong Mock 验证 Odoo→Ginlong 路径。全部十个接口均纳入 CC-005 本地集成验收，不表示真实 Ginlong 联调已完成。

### 4.2 明确排除

- 不模拟 KR 的收货、上架、拣货、发货或现场盘点；不构造 KR XML/JSON、KR HTTP 请求或 Gateway 转换结果。
- 不开发或修改 Karl Rapp Gateway，不连接 VPN/FTP，不访问真实 KR 环境。
- 不访问真实 Ginlong、正式环境或生产数据库；Ginlong 回传只使用本地 Mock HTTP。
- 不在 API03 建立预留 Picking 1；不开发或改变 Odoo Reserve、预留托盘/库位建议或 KR 返回后取消 Picking 1 并创建 Picking 2 的预分配功能。出库预分配另立 CC 并先完成 TV/TDD。API09 若需验证预留量，只使用现有标准 WMS 流程产生的测试数据，不把 Reserve 功能纳入本 CC。
- 不创建第二个仓库，不实施多仓库库存分配或新的跨仓业务规则。
- 不增加平行产品、库存、盘点或 API 日志模型；不增加 API 开关、状态机、审批、自动回传或后台自动重试。
- 不使用 stock_barcode；不直接写 stock.quant，不以 SQL 准备、查询或清理数据库。
- 不修改官方 Odoo 源码；不重构无关 WMS 功能；不改写已关闭 CC-001–004 及 FR 的历史证据。

## 5. 环境与测试数据约束

| 项目 | 要求 |
|---|---|
| Odoo 环境 | 使用项目现有 venv、odoo.conf 和 odooce_karlrapp；不得新建虚拟环境、隔离数据库或替换项目配置。 |
| 数据库操作 | 仅通过 Odoo 测试框架或 odoo shell -c odoo.conf 使用 ORM；禁止 psql、psycopg2、直接 SQL。 |
| 测试产品 | 用 API07 或现有 ORM 夹具创建有明确标记的 product.template / product.product 变体；不同 owner 的变体使用相同 raw productCode。 |
| 入出库数据 | 使用 Odoo 标准 stock.picking / stock.move.line 及标准确认、验证/过账流程建立测试作业记录。不得写 quant 来伪造库存，也不得声称执行了 KR 仓库作业。 |
| Mock HTTP | 所有 Ginlong 回传 Endpoint 指向本地 Mock；测试前核实不会请求 Ginlong 测试/正式地址。 |
| 清理 | 仅通过 ORM 清理本轮可识别的测试记录；不得删除或改写既有业务记录和历史日志。不能安全隔离时停止受影响场景。 |
| 浏览器/HVR | Codex 使用本地浏览器完成用户路径并记录 HVR；业务负责人最终人工验收单独记录。角色、操作、输入数据和结果可追溯，不记录 Secret/Token 明文。 |

## 6. 测试矩阵（全部初始状态 NOT RUN）

以下编号是本 v1.0 Frozen with Open Items 的验收 ID。冻结只批准验收范围和标准，不代表测试已经执行；CC-001–004 组件测试证据按引用使用。

| 测试 ID | 场景 | 验收标准 / 证据 |
|---|---|---|
| CC-TEST-044 | 环境与前置条件 | 记录模块版本、现有数据库/服务、用户权限、Mock Endpoint、上游基线批准状态及测试数据边界；上游影响未获批时记录 BLOCKED，不进入受影响实现验收。 |
| CC-TEST-045 | API01 owner 与产品变体 | 先有 API07 创建的 owner+productCode 变体；API01 对 owner 按 ginlong_owner_code 复用或按已批准规则创建货主，产品明细关联正确 owner 变体；重复请求不重复建货主或业务单据。收单不产生 picking 或库存变化。 |
| CC-TEST-046 | API03 owner + productCode | 已存在货主及产品组合成功处理；未知货主或任一缺失组合拒绝整单，不自动创建货主/产品；多明细部分无效时不留下部分 Order、明细、Picking 或库存影响。 |
| CC-TEST-047 | API07 产品模板/变体及一致性 | 同 raw productCode 不同 owner 复用单一 template 并形成各自 variant；验证已确认共享的名称、规格、重量、尺寸、productForm、tracking 和变体 owner/内部码/raw code；Add/Edit 正确；仅对这些已确认共享字段做同码一致性检查，冲突时拒绝且既有记录不变；非法 productForm 拒绝，并按规则设置模板 tracking。对归属未定的其他字段不增设冲突校验。 |
| CC-TEST-048 | worlddepot 产品查找兼容 | 相关 WMS 控制器和现有 resolver 对同码跨 owner 产品按可用 owner 信息正确定位；缺少唯一 owner 依据时报告歧义而不任取第一条；既有单 owner 产品流程回归通过。 |
| CC-TEST-049 | Odoo 入库 stock.picking、API02/API04 | 无 KR 参与。为 API02 在 Odoo 准备模拟的已保存 `inbound.order` 收货明细和确认状态；另用 Odoo 标准流程建立并完成入库 picking/move lines，作为 API04 的本地实绩测试记录。API02 从 Order 已保存数据生成回传；状态混合时按已批准规则阻止发送。API04 从已完成 picking/move lines 读取产品、数量、SN/托盘数据。两者事件分离，分别发送到 Ginlong Mock 并留日志。 |
| CC-TEST-050 | Odoo 出库 stock.picking、API06/API08 | 无 KR 参与。为 API06 准备模拟的 `outbound.order` 备货完成业务数据及已保存关联作业明细；另用 Odoo 标准流程建立并完成出库 picking/move lines，作为 API08 的本地实绩测试记录。API06 不能只凭 picking 创建/过账判定备货完成；`palletQty` 使用已保存的人工覆盖值或实际 move line `package_id` 去重计数，重量依据实际数量和 `product.ginlong_weight`，毛重使用已保存值或按既有规则默认，DECIMAL 按已批准契约回传为 JSON string。API08 使用出库 Order 已保存发货状态并读取适用 picking 数据；混合状态按已批准规则阻止发送。两接口分别验证和发送。 |
| CC-TEST-051 | API05 指令与 API10 实盘结果 | 使用 worlddepot 客户盘点 Order 和关联的已保存实盘结果；验证计划指令与实际结果独立，API10 只读实盘结果；不读写 stock.quant、不调整库存。 |
| CC-TEST-052 | API09 `KRWH` 货主/产品隔离与只读 | 只使用现有仓库 `KRWH`，通过标准 `stock.picking` 流程形成过账库存，不创建第二仓库。测试数据为 OWNER-A/P001=100、OWNER-B/P001=300、OWNER-A/P002=200。分别按 owner 请求 `KRWH`：OWNER-A 只返回 P001=100、P002=200；OWNER-B 只返回 P001=300；相同产品跨货主隔离，P001 与 P002 分开返回。若验证预留量不扣减，则只用既有标准 WMS 流程产生测试预留；API 仍返回 OWNER-A/P001 物理数量 100，不扣减预留量，不新增 Reserve 功能。owner 按 `res.partner.ginlong_owner_code` 对应 `stock.quant.owner_id` 隔离，warehouse 使用现有 `KRWH`；响应返回原始 Ginlong `productCode`。查询前后库存、move、picking 状态与数量不变。此测试不覆盖多仓库业务规则。 |
| CC-TEST-053 | 五个持久化回传 Form 的浏览器流程 | 对 API02/04/06/08/10 逐个保存、关闭并重开 Form，再点击 Order 上的回传按钮；发送只读取 ORM 已保存值，业务用户看不到 JSON 编辑器；按业务事件/选中记录展示必要信息。记录 HVR 和 Mock 响应。 |
| CC-TEST-054 | 回传失败、修正、重发及日志 | Mock 首次失败；用户保存修正再手动发送；第二次读取新 ORM 数据，现有日志新增一条记录，旧日志不变且可定位源单；无自动重试。 |
| CC-TEST-055 | 必要 WMS/UI 回归 | 浏览器验证受影响的 Order、stock.picking、move line、产品变体和 API 日志定位；API01/03 不因收单产生实际库存变化；盘点结果不触发库存调整；已关闭 CC 的组件证据不重复运行。 |

## 7. 证据与结果记录

- 自动化和 ORM 集成结果追加至 ATR-GIN-005；浏览器路径及截图/等价证据记录至 HVR-GIN-005；实施事实及修改记录至 IHR-GIN-005。
- 每个结果标明 PASS、PARTIAL、FAIL、BLOCKED 或 NOT RUN，并注明运行环境、代码/模块版本、数据是既有业务记录还是 Odoo stock.picking 测试夹具。
- Odoo stock.picking 测试夹具只证明本地 Odoo 对执行记录、库存、SN、托盘及 Ginlong 回传读取的集成行为；不证明 KR 实际作业、KR→Odoo 转换、Gateway 或真实库存同步。
- Ginlong Mock HTTP 不代表 Ginlong 测试环境或生产可用；真实 Ginlong 联调留 CC-GIN-006。
- 未决外部协议按接口/场景隔离；不猜测、不将 BLOCKED、NOT RUN 或 PARTIAL 改写为 PASS。

## 8. Open Items 与上游门禁

| ID | 待解决事项 | 对本 CC 的影响 |
|---|---|---|
| OI-GIN-005-01 | TV v1.0 的 productCode/template、owner/variant、共享字段及一致性规则尚未纳入冻结 SRS v1.0、TDD v0.9 和 Implementation Plan 当前基线。 | 本 CC 范围已按 Human Review 冻结；受影响实施门禁仍未通过。完成必要上游影响评估/修订并获批，更新计划基线和追溯后，方可评估并授权受影响实施。 |
| OI-GIN-005-02 | 现有 Ginlong 产品数据中的同码多模板、共享字段冲突、订单/Picking/库存引用及 `default_code` 使用情况尚需盘点。 | 实施前形成数据迁移及冲突处理方案；不得由 API07 在线请求自动合并或静默覆盖。 |
| OI-GIN-005-03 | Ginlong V3.2 未正式列出 `productForm` 枚举；原材料/半成品/成品是项目负责人批准的本地规则。 | 本地测试按本规则；不宣称 Ginlong 已确认枚举，外部兼容留 CC-GIN-006。 |
| OI-GIN-005-04 | 内部组合 `default_code` 格式、长度及既有产品数据迁移策略。 | 上游设计需明确稳定查找与回传转换，不能把内部组合码作为 Ginlong `productCode` 回传。 |
| OI-GIN-005-05 | `unit`、`power`、`nationalStandard`、`certificationModel` 等字段的模型归属/共享范围在 TV v1.0 OI-02 尚未定案。 | 不对这些字段新增同码冲突校验；在上游明确字段映射后再补相应验收。 |
| OI-GIN-005-06 | 项目模板同步来源缺失。 | 沿用已批准例外，保持 BLOCKED，不标为 PASS。 |

本 CC 按本次负责人决策只使用现有仓库 `KRWH`；该测试范围不构成永久的单仓库产品规则，也不引入未来多仓库分配设计。未来新增仓库或相关业务要求须另行明确范围和验收，不属于本 CC。

## 9. 必要的上游文档修订清单（本轮不修改）

| 上游文档 | 差异 | 建议修订内容 | 当前处理 |
|---|---|---|---|
| SRS ginlong_apis v1.0 Frozen | FR-GIN-001/003/007 需要区分业务键、共享模板及 owner 变体；FR-GIN-003 仍以历史 A-003 假设标识 API03 方向；FR-GIN-007 未定义共享字段、三种 `productForm`、tracking 映射及冲突拒绝；FR-GIN-009 仍把库存数量口径列为待确认。 | 更新 API03 方向为已确认的 Ginlong→Odoo；补入一个 raw `productCode` 对应一个 template、owner 对应 variant 的产品身份及已批准字段/规则，明确仅对已定归属字段校验；FR-GIN-009 补明数量为实际物理库存、不减预留。不得把当前只有 `KRWH` 写成永久单仓业务规则，也不加入多仓分配规则。 | 本轮保留冻结原件；由负责人批准后另版修订。 |
| TDD v0.9 Frozen | 未反映新 template/variant 字段归属、必要数据迁移、共享字段冲突处理及 `productForm`→`tracking` 映射；API09 原始编码来源也随产品模型调整受影响。 | 修订产品模型和迁移方案；说明 API01/03/07 通过 owner+raw productCode 查找 variant，API04/06/08/09 对外使用 raw code。保留 API09 已确认的实际物理数量、owner 隔离、当前仓库编码读取和只读边界；不设计多仓分配。 | 本轮不改冻结 TDD。 |
| Implementation Plan v1.6 Frozen / v1.7 状态补充 | 阶段 4 尚未基线化 TV v1.0 产品变体规则；拟建 CC-005 的十个 API 测试数据来源、Picking 两阶段和单仓库存范围需同步。 | 完成 SRS/TDD 更新审批后，更新 Plan 基线有效性、阶段 4 范围、CC-005 引用、十个 API 本地测试数据来源、当前 Odoo Picking 记录模拟与后续 KR 数据源接入的区别；Ginlong 真实 HTTP 联调在本地验收后进入 CC-006。API09 仅用 `KRWH`。 | 本轮只记录差异，不修改 Plan。 |
| TV-GINLONG-PRODUCT-001 v1.0 Closed with Open Items | TV 已批准关闭；OI-02（未映射字段归属）、OI-09（上游基线）仍保留。 | 作为技术依据引用；不回写已关闭 TV。上游字段决策按 SRS/TDD 变更流程处理。 | 本轮不修改 TV。 |

## 10. 冻结后允许的实施边界

本 CC v1.0 已获 Human Review 批准并冻结范围，但该决定不授权代码或测试。实施授权待 OI-GIN-005-01 所列 SRS/TDD/Implementation Plan 上游修订、批准和基线更新；在相关基线更新前，受影响实现不得开始。上游完成后，按更新后的基线明确实施授权。实现范围仍限于 `ginlong_apis`、必要的 `worlddepot` 产品变体查找/字段扩展，以及测试与验收文档；任何超出已批准 SRS/TDD/CC 的业务规则、WMS 状态或数据模型均先回到上游评审。

KR→Gateway→Odoo 的后续集成只负责把真实 KR 结果转换成现有 Odoo `stock.picking` 及相关记录；不另建库存处理机制。本 CC 不实现该转换，也不建设 KR 模拟器、Gateway、通用 WMS 集成层、旁路库存账、自动重试或额外审批。库存记录必须经标准 Odoo Picking 工作流生成，严禁直接修改 `stock.quant`。

## 11. Done Gate

1. OI-GIN-005-01 上游影响评估和批准完成，CC 冻结版本准确引用已批准基线。
2. API07 模板/变体、同码共享属性一致、productForm→tracking、冲突无副作用及必要迁移有自动化/ORM 证据。
3. API01/03 以 owner+raw productCode 使用正确变体，并通过受影响 WMS 产品查找回归。
4. 使用 Odoo 标准 stock.picking 建立的入库/出库记录通过 API02/04/06/08 的分离事件、数据来源、Form 保存/重开、Mock 发送和日志验收；不把它们称为 KR 模拟或 KR 联调。
5. API05/API10 使用客户盘点单及实盘结果且不修改库存；API09 仅以现有 `KRWH` 验证 owner/product 隔离、物理数量与只读性，不创建第二仓库或测试多仓业务。
6. 受影响 WMS 自动化回归通过；Codex 浏览器 E2E 的 HVR 证据完整，业务负责人最终验收另行签署。
7. ATR/IHR/HVR/FR 如实记录未执行或阻塞项目；无未解决的本 CC 强制验收项被伪记为通过。
8. 不要求模拟 KR/Gateway 或访问真实 Ginlong；CC-GIN-006 继续负责真实 Ginlong 联调。

## 12. 追溯矩阵

| 来源 | 测试/范围 | 追溯 |
|---|---|---|
| SRS FR-GIN-001/003 | CC-TEST-045/046 | 入库/出库订单处理和现有产品定位；订单接收不等于库存执行。 |
| SRS FR-GIN-007 与 TV v1.0 | CC-TEST-047/048 | 产品变体、共享产品属性、owner+raw productCode、WMS 查找兼容；TV 新规则须先纳入上游批准基线。 |
| SRS FR-GIN-002/004 | CC-TEST-049/053/054 | API02 收货确认与 API04 实际入库完成的来源分离、持久化回传与日志。 |
| SRS FR-GIN-006/008 | CC-TEST-050/053/054 | API06 备货完成与 API08 发货完成的事件和数据来源分离。 |
| SRS FR-GIN-005/010 | CC-TEST-051 | 客户盘点指令与实盘结果分离；API10 不以 stock.quant 推算。 |
| SRS FR-GIN-009、TDD v0.9 §7 | CC-TEST-052 | API09 使用现有 `KRWH`，验证货主/产品过滤、物理 quantity 和原始编码输出；不扩展多仓库规则。 |
| TDD v0.9 §§1–7、CC-GIN-001–004 | CC-PRESERVE、CC-TEST-044–055 | 复用既有 WMS、认证、日志、回传和库存能力；不重做已关闭组件测试。 |
| Implementation Plan v1.6 阶段 4 / v1.7 状态 | CC-TEST-044–055 | 本地 Ginlong/Odoo UI/WMS 集成；KR/Gateway 和真实 Ginlong 验收边界按本 CC 修订稿执行。 |

## 13. Human Review 与授权

| 项目 | 当前状态 |
|---|---|
| Human Review | **APPROVED**；李建强（项目用户）；2026-11-19；仅批准范围冻结，实施授权待上游基线更新 |
| 批准决定 | **APPROVED（范围批准，实施授权待上游基线更新）** |
| CC 冻结 | **Frozen with Open Items**；v1.0 |
| 编码/测试 | **未授权**；须先完成并批准上游基线更新，再明确实施授权 |
| KR/Gateway | 本 CC 不模拟、不连接、不改动 |
| 外部 Ginlong | 仅本地 Mock；真实联调留 CC-GIN-006 |
| 文档模板 | BLOCKED；沿用既有批准例外，不记为 PASS |

## 附录 A — 本次重写决策

| 决策 | 内容 |
|---|---|
| 测试作业数据 | 当前 CC 在 Odoo 用标准 stock.picking / stock.move.line 模拟创建完成的 Picking，测试数据符合 KR 实际作业结果写入 Odoo 后的业务形态；不模拟 KR 现场操作、KR XML 或 Gateway。后续才实施 KR XML→Gateway→Odoo 自动生成 Picking；两阶段共用 Odoo 库存机制，只改变数据来源。 |
| 十个 API 的本地验收 | API01/03/05/07 使用本地 Ginlong 请求进入 Odoo；API02/04/06/08/10 使用对应已保存/模拟业务记录发送至 Ginlong Mock；API09 读取由标准 Picking 流程形成的 `stock.quant`。 |
| 库存生成 | 仅由标准 Odoo picking 验证/过账产生；不直接写 stock.quant。 |
| 产品主数据 | 按 TV-GINLONG-PRODUCT-001 v1.0 提出的 template/variant 方案纳入 CC；上游更新是受影响实施门禁，CC 范围已冻结。 |
| 历史证据 | v0.1–v0.4 原稿保留；本 v1.0 为冻结范围基线，不覆盖已关闭 CC-001–004 的任何历史结果。 |

## 附录 B — 版本记录

| 版本 | 日期 | 状态 | 说明 |
|---|---|---|---|
| v0.3 | 2026-11-19 | Draft | 按已关闭 TV v1.0 重写产品变体及 API07 规则；出入库用 Odoo `stock.picking` 建立本地测试记录，不模拟 KR/Gateway；保留外部联调和上游基线门禁。 |
| v0.4 | 2026-11-19 | Review Draft | 按最新决策收窄 API09 到 `KRWH` 三组库存，不测试双仓；仅对已明确归属的共享字段校验冲突；明确 API01–10 本地开发及测试数据来源、Odoo Picking 两阶段及 CC-006 真实 Ginlong 联调顺序；加入 SRS/TDD/Plan 差异及后续修订清单。本轮仅修改 CC 草案，未编码、未测试、未修改上游冻结文档。 |
| v1.0 | 2026-11-19 | Frozen with Open Items | Human Review APPROVED，仅冻结 CC 范围；实施授权待 SRS/TDD/Implementation Plan 上游基线修订、批准及更新。模板同步仍 BLOCKED，沿用既有批准例外；未编码、未测试。 |

**CC-GIN-005 v1.0 范围已冻结。SRS、TDD、Implementation Plan、TV v1.0、代码及既有 ATR/IHR 均未修改；本次未编码、未运行测试。模板同步保持 BLOCKED。实施授权待上游基线更新。**
