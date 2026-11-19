# CC-GIN-005 v0.3 — Ginlong 与 Odoo WMS 本地集成验收（Draft）

| 项目 | 内容 |
|---|---|
| CC ID / 版本 | CC-GIN-005 / v0.3 Draft |
| 状态 | Draft；待 Human Review；未冻结；未授权编码或测试 |
| Intent ID | `GINLONG-LOCAL-UI-WMS-E2E-005` |
| 范围 | Ginlong API 与 Odoo WMS 本地集成、产品变体适配、浏览器 UI/WMS 验收 |
| SRS | [SRS ginlong_apis v1.0 Frozen](../requirement/SRS_ginlong_apis.md) |
| TDD | [TDD v0.9 Frozen](../ginlong_apis/TDD-v0.9.md)；产品变体技术结论见本 CC 引用的 TV v1.0 |
| TV | [TV-GINLONG-PRODUCT-001 v1.0 Closed with Open Items](../context/report/TV_ginlong_product_variants_api07_sn_v1.0.md)；Human Review APPROVED |
| Implementation Plan | [v1.6 Frozen](IMPLEMENTATION_PLAN_ginlong_apis-v1.6.md)；阶段状态见 [v1.7](IMPLEMENTATION_PLAN_ginlong_apis-v1.7.md) |
| 前序 CC | CC-GIN-001–004 Closed；不重做其组件验收 |
| 后续阶段 | CC-GIN-006 真实 Ginlong 联调，须另行授权 |
| 模板同步 | BLOCKED；项目模板源缺失，沿用既有批准例外，不伪记为通过 |

## 修订记录

| 版本 | 状态 | 修订内容 |
|---|---|---|
| v0.1 | Draft | 初稿，覆盖本地 Ginlong API/Odoo WMS UI 集成与 E2E。 |
| v0.2 | Draft | 加入 API01/03 货主处理、API09 隔离及浏览器 HVR 范围；Gateway 作为可选测试。保留原稿。 |
| v0.3 | Draft | 根据已关闭 TV v1.0 重写产品变体与 API07 验收；仓库出入库测试改用 Odoo 标准 `stock.picking` 模拟，不再模拟 KR 作业或 KR XML/API；删除 Gateway 可选测试，明确上游基线门禁。 |

> 本文仅为 CC 草案。它不修改 SRS、TDD、Implementation Plan 或已关闭 CC-GIN-001–004，不授权编码、升级模块、写入数据库或运行测试。TV v1.0 中涉及产品模板/变体的新业务规则尚未纳入冻结 SRS/TDD/Plan；完成上游影响评估和批准后，方可冻结并实施本 CC。

## 1. 目的与系统边界

本 CC 验证已实现的 Ginlong 入站 API、Odoo WMS 业务模型、人工回传界面及 API09 库存查询在本地的衔接，并将 TV v1.0 批准的产品模板/变体方案及 API07 规则纳入后续 CC 验收建议。

系统实际职责不变：Ginlong 下达业务指令；Karl Rapp WMS 执行仓库现场作业；Gateway 负责文件通信及 XML/JSON 转换；Odoo 管理业务 Order，并根据实际作业记录使用 stock.picking、stock.move.line 和原生库存机制登记执行结果，再向 Ginlong 提供数据。

**本 CC 的出入库测试不模拟 KR。** 测试直接通过 Odoo 标准 stock.picking、stock.move.line 及原生确认/过账流程建立本地出入库执行记录，作为 Odoo 端已保存的作业数据，用来验证库存、SN、托盘和 Ginlong 回传读取。测试不构造 KR XML、KR HTTP 请求、Gateway 输出或现场操作脚本；不据此宣称 KR/Gateway 集成已通过。

## 2. 基线、决策与实施门禁

| 项目 | 当前依据及处置 |
|---|---|
| 冻结需求与设计 | Ginlong SRS v1.0、TDD v0.9；已关闭 CC-001–004 的组件验收结果只引用，不重复执行。 |
| 产品变体技术验证 | TV-GINLONG-PRODUCT-001 v1.0 已关闭，Human Review APPROVED；其产品字段归属、tracking 规则及 API 影响纳入本稿。 |
| 产品新规则的基线状态 | 一个 raw productCode 一个 product.template、owner 作为 product.product 变体、共享固有属性一致等事项尚未进入冻结 SRS/TDD/Implementation Plan。按 TV OI-09，必须先完成上游影响评估、必要修订与批准，并更新计划及追溯；在此之前本 CC 仅为 Draft，不得冻结或实施。 |
| API01/03 项目负责人决定 | API01 按 Ginlong owner code 复用或创建货主档案；API03 要求货主与每条产品组合已存在，缺失时拒绝；产品档案由 API07 维护。引用 IHR-GIN-003 IHR-021 和 ATR-GIN-003 RUN-049–055。 |
| 已批准模板例外 | 技术验证模板同步脚本仍 BLOCKED，因项目模板源缺失；沿用既有批准的流程例外，不将 BLOCKED 写成 PASS。 |

## 3. 产品模型与 API 业务验收边界

产品方案以 TV v1.0 为技术评审依据；下列规则在上游批准后方可进入冻结 CC 和实施：

- 一个 Ginlong 原始 productCode 对应一个 product.template；同一编码的不同 owner 对应不同 product.product 变体。
- 模板共享产品名称、规格、重量、尺寸、productForm 和 tracking；变体保存 owner、内部组合编码及原始 Ginlong productCode。
- 相同 productCode 的固有属性不随 owner 改变。API07 收到同码共享属性或 productForm 冲突时，拒绝请求并明确报错，既有模板和变体不得被部分覆盖。
- API07 只接受 原材料、半成品、成品；原材料对应 tracking=none，半成品/成品对应 tracking=serial。不新增 snTrackingRequired。
- API01/03/07 按 owner + 原始 productCode 定位产品变体；API09 只读库存并返回原始 productCode。
- KR 负责现场 SN 采集。Odoo 依据已保存的 stock.move.line / Lot 记录使用 Odoo 原生序列号跟踪；不在 Odoo 开发现场扫码流程。
- Odoo 原生 WMS 产品查找须按 owner 消歧；重复编码无唯一 owner 依据时应明确报告歧义，不任取第一条产品。

本 CC 的 API01/03/07 本地流程应先由 API07 建立产品档案，再以已存在的 owner + productCode 处理订单。API01 的货主创建/复用行为和 API03 的无效组合拒绝行为遵循 IHR-021 已批准决定；不重复开发其组件功能。

## 4. 范围

### 4.1 纳入 CC-GIN-005

1. 本地 Odoo 浏览器及 ORM 集成验收：API01/03/05/07、现有业务 Order、产品变体、人工回传 API02/04/06/08/10 与 API09 的端到端衔接。
2. 在上游基线批准后，完成产品模板/变体字段调整和必要数据迁移；验证 API07 同码跨 owner 复用模板、创建/更新变体、共享属性一致性及冲突拒绝。
3. 对 API01/03 按 owner + raw productCode 的产品定位执行本地端到端回归；覆盖受影响的 worlddepot 产品查找路径及同码跨 owner 歧义处理。
4. 使用 Odoo 标准 stock.picking 和 stock.move.line 建立入库、出库测试记录，并经标准确认/过账操作形成库存；不直接改 stock.quant。用这些已保存业务记录验证 API04/06/08 数据读取、API09 库存隔离及产品、SN、托盘、货主关系。
5. API02 从入库 Order 已保存的收货明细/状态读取；API04 从实际已保存的入库 stock.picking / stock.move.line 读取。区分收货确认与入库完成。
6. API06 从实际备货业务事件及对应 picking/move line 读取；不以 picking 创建或库存过账本身冒充备货完成。API08 使用出库 Order 已保存的发货状态；实际发货明细以已保存 picking/move line 为依据。区分备货完成与发货完成。
7. API10 从 worlddepot 客户盘点 Order 关联的实盘结果取数；API05 盘点指令和实盘结果保持分离，不使用 stock.quant 推算盘点结果、不做库存调整。
8. 验证五个人工回传接口继续使用业务 Order 上的持久化 Ginlong Form/Notebook：先保存、重新打开、用户点击按钮、同步 POST 到 Mock Ginlong、记录每次独立日志；失败后修正并人工重发。
9. 使用标准 Odoo 库存流程建立 API09 测试库存，验证 owner/warehouse 隔离、实际物理数量、不扣预留量及严格只读；不把本地 stock.picking 测试称为 KR 库存同步验证。
10. 仅执行本 CC 触及的自动化、必要 ORM 集成和浏览器 E2E 回归，不重复 CC-001–004 的组件测试。

### 4.2 明确排除

- 不模拟 KR 的收货、上架、拣货、发货或现场盘点；不构造 KR XML/JSON、KR HTTP 请求或 Gateway 转换结果。
- 不开发或修改 Karl Rapp Gateway，不连接 VPN/FTP，不访问真实 KR 环境。
- 不访问真实 Ginlong、正式环境或生产数据库；Ginlong 回传只使用本地 Mock HTTP。
- 不在 API03 建立预留 Picking 1；不实施 Odoo 原生 Reserve、预留托盘/库位建议或 KR 返回后取消 Picking 1 并创建 Picking 2。出库预分配另立 CC 并先完成 TV/TDD。
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

以下编号是本 v0.3 Draft 的建议验收 ID，不代表已经执行。CC-001–004 组件测试证据按引用使用。

| 测试 ID | 场景 | 验收标准 / 证据 |
|---|---|---|
| CC-TEST-044 | 环境与前置条件 | 记录模块版本、现有数据库/服务、用户权限、Mock Endpoint、上游基线批准状态及测试数据边界；上游影响未获批时记录 BLOCKED，不进入受影响实现验收。 |
| CC-TEST-045 | API01 owner 与产品变体 | 先有 API07 创建的 owner+productCode 变体；API01 对 owner 按 ginlong_owner_code 复用或按已批准规则创建货主，产品明细关联正确 owner 变体；重复请求不重复建货主或业务单据。收单不产生 picking 或库存变化。 |
| CC-TEST-046 | API03 owner + productCode | 已存在货主及产品组合成功处理；未知货主或任一缺失组合拒绝整单，不自动创建货主/产品；多明细部分无效时不留下部分 Order、明细、Picking 或库存影响。 |
| CC-TEST-047 | API07 产品模板/变体及一致性 | 同 raw productCode 不同 owner 复用单一 template 并形成各自 variant；验证共享名称、规格、重量、尺寸、productForm、tracking 和变体 owner/内部码/raw code；Add/Edit 正确；同码共享字段或 productForm 冲突时拒绝且既有记录不变；仅三种产品形态被接受，并按规则设置模板 tracking。 |
| CC-TEST-048 | worlddepot 产品查找兼容 | 相关 WMS 控制器和现有 resolver 对同码跨 owner 产品按可用 owner 信息正确定位；缺少唯一 owner 依据时报告歧义而不任取第一条；既有单 owner 产品流程回归通过。 |
| CC-TEST-049 | Odoo 入库 stock.picking、API02/API04 | 不调用 KR 或 KR Mock；在 Odoo 标准流程建立并完成入库 picking/move lines。API02 从入库 Order 已保存收货明细/状态生成回传；状态混合时按已批准规则阻止发送。API04 从已完成 picking/move lines 读取实际收货、产品、数量、SN/托盘数据。两者事件分离，分别发送到 Ginlong Mock 并留日志。 |
| CC-TEST-050 | Odoo 出库 stock.picking、API06/API08 | 不调用 KR 或 KR Mock；用 Odoo 标准 picking/move line 建立并完成本地出库测试记录。API06 从既有业务记录确认备货完成事件及实际备货数据，不能只凭 picking 创建/过账判定；`palletQty` 使用已保存的人工覆盖值或实际 move line `package_id` 去重计数，重量依据实际数量和 `product.ginlong_weight`，毛重使用已保存值或按既有规则默认，DECIMAL 按已批准契约回传为 JSON string。API08 使用出库 Order 已保存发货状态并读取适用实际 picking 数据；混合状态按已批准规则阻止发送。两接口分别验证和发送。 |
| CC-TEST-051 | API05 指令与 API10 实盘结果 | 使用 worlddepot 客户盘点 Order 和关联的已保存实盘结果；验证计划指令与实际结果独立，API10 只读实盘结果；不读写 stock.quant、不调整库存。 |
| CC-TEST-052 | API09 物理库存与只读 | 通过 Odoo 标准 picking 流程形成已过账库存；owner 用 `res.partner.ginlong_owner_code` 定位并匹配 `stock.quant.owner_id`，warehouse 按 TDD v0.9 精确匹配 `stock.warehouse.code`。验证 OWNER-A/WH-A/P001=100、OWNER-A/WH-B/P001=200、OWNER-B/WH-A/P001=300、OWNER-B/WH-B/P002=400 四种组合各自隔离；同 productCode 跨 owner 不合并。未知 owner 不泄漏并返回空清单；未知 warehouse 按现有错误契约拒绝且不回退到唯一仓库；已知 owner/warehouse 无库存时返回空 `inventoryList`。返回 `stock.quant.quantity` 物理量、不扣 reserved、输出原始 Ginlong productCode；请求前后库存、move、picking 状态和数量不变。 |
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
| OI-GIN-005-01 | TV v1.0 的产品 template/variant 身份、字段归属及一致性规则未纳入冻结 SRS v1.0、TDD v0.9 和 Implementation Plan 当前基线。 | 这是冻结和实施门禁；必须先完成人类批准的上游影响评估/必要修订、Plan 重新基线及追溯更新。之前本 CC 保持 Draft，受影响功能 BLOCKED。 |
| OI-GIN-005-02 | 现有 Ginlong 产品数据的同码多模板、共享字段冲突、订单/Picking/库存引用及 `default_code` 使用情况尚需实施前盘点。 | 制定可验证的数据迁移/冲突处理方案；不得由 API07 在线请求自动合并或静默覆盖。 |
| OI-GIN-005-03 | Ginlong V3.2 未正式列出 `productForm` 枚举；原材料/半成品/成品是项目负责人批准的本地规则。 | 本地测试按项目规则；Ginlong 外部兼容确认留 CC-GIN-006，不宣称对端已确认。 |
| OI-GIN-005-04 | 内部组合 `default_code` 生成格式及旧 WMS 数据迁移策略。 | TDD/CC 冻结前应确定长度、稳定性、查找和回传转换，不能让内部编码泄漏为 Ginlong productCode。 |
| OI-GIN-005-05 | API07 的 `unit`、`power`、`nationalStandard`、`certificationModel` 等剩余字段归属及同码一致性范围，TV v1.0 OI-02 尚未定案。 | 上游设计明确字段映射后再冻结受影响字段验收；本 CC 不擅自将其归为模板或变体字段。 |
| OI-GIN-005-06 | API09 仓库匹配的历史表述存在差异：CC-GIN-004 v1.0 记录单仓库直接读取、不做 Ginlong 编码映射；后续 TDD v0.9 / CC-GIN-004 v1.1 记录精确匹配 `stock.warehouse.code`。 | 本测试矩阵按后续 TDD v0.9 的精确匹配实现；Human Review 冻结前确认此后续补充作为当前验收控制依据。如需改变冻结基线，先走上游修订。 |
| OI-GIN-005-07 | KR 实际数据和 Gateway XML 转换未验证。 | 不属于本 CC 测试输入；真实 KR/Gateway 联调与验收由相应独立阶段处理，不作为本地 `stock.picking` 测试结论。 |
| OI-GIN-005-08 | 模板同步来源缺失。 | 沿用批准例外，仍记录 BLOCKED；不得标记通过。 |

## 9. 冻结后允许的实施边界

Human Review 批准本稿、完成 OI-GIN-005-01 上游门禁并冻结后，才授权 CC 范围内的代码和测试工作。实现限于 `ginlong_apis`、必要的 `worlddepot` 变体查找/字段扩展，以及测试与验收文档；任何超出已批准 SRS/TDD/CC 的业务规则、WMS 状态或数据模型均先回到上游评审。

不得因本 CC 建设 KR 模拟器、Gateway、通用 WMS 集成层、旁路库存账、自动重试或额外审批。Odoo 库存记录必须经标准 stock.picking 工作流生成；严禁直接修改 stock.quant。

## 10. Done Gate（拟议）

1. OI-GIN-005-01 上游影响评估和批准完成，CC 冻结版本准确引用已批准基线。
2. API07 模板/变体、同码共享属性一致、productForm→tracking、冲突无副作用及必要迁移有自动化/ORM 证据。
3. API01/03 以 owner+raw productCode 使用正确变体，并通过受影响 WMS 产品查找回归。
4. 使用 Odoo 标准 stock.picking 建立的入库/出库记录通过 API02/04/06/08 的分离事件、数据来源、Form 保存/重开、Mock 发送和日志验收；不把它们称为 KR 模拟或 KR 联调。
5. API05/API10 使用客户盘点单及实盘结果且不修改库存；API09 由标准 picking 流程产生的库存验证 owner/仓库隔离、物理数量与只读性。
6. 受影响 WMS 自动化回归通过；Codex 浏览器 E2E 的 HVR 证据完整，业务负责人最终验收另行签署。
7. ATR/IHR/HVR/FR 如实记录未执行或阻塞项目；无未解决的本 CC 强制验收项被伪记为通过。
8. 不要求模拟 KR/Gateway 或访问真实 Ginlong；CC-GIN-006 继续负责真实 Ginlong 联调。

## 11. 追溯矩阵

| 来源 | 测试/范围 | 追溯 |
|---|---|---|
| SRS FR-GIN-001/003 | CC-TEST-045/046 | 入库/出库订单处理和现有产品定位；订单接收不等于库存执行。 |
| SRS FR-GIN-007 与 TV v1.0 | CC-TEST-047/048 | 产品变体、共享产品属性、owner+raw productCode、WMS 查找兼容；TV 新规则须先纳入上游批准基线。 |
| SRS FR-GIN-002/004 | CC-TEST-049/053/054 | API02 收货确认与 API04 实际入库完成的来源分离、持久化回传与日志。 |
| SRS FR-GIN-006/008 | CC-TEST-050/053/054 | API06 备货完成与 API08 发货完成的事件和数据来源分离。 |
| SRS FR-GIN-005/010 | CC-TEST-051 | 客户盘点指令与实盘结果分离；API10 不以 stock.quant 推算。 |
| SRS FR-GIN-009、TDD v0.9 §7 | CC-TEST-052 | API09 只读库存、owner/warehouse 过滤、物理 quantity 和编码输出。 |
| TDD v0.9 §§1–7、CC-GIN-001–004 | CC-PRESERVE、CC-TEST-044–055 | 复用既有 WMS、认证、日志、回传和库存能力；不重做已关闭组件测试。 |
| Implementation Plan v1.6 阶段 4 / v1.7 状态 | CC-TEST-044–055 | 本地 Ginlong/Odoo UI/WMS 集成；KR/Gateway 和真实 Ginlong 验收边界按本 CC 修订稿执行。 |

## 12. Human Review 与授权

| 项目 | 当前状态 |
|---|---|
| Human Review | 待评审 |
| CC 冻结 | 未冻结 |
| 编码/测试 | 未授权；须在上游门禁完成、CC 冻结后另行授权 |
| KR/Gateway | 本 CC 不模拟、不连接、不改动 |
| 外部 Ginlong | 仅本地 Mock；真实联调留 CC-GIN-006 |
| 文档模板 | BLOCKED；沿用既有批准例外，不记为 PASS |

## 附录 A — 本次重写决策

| 决策 | 内容 |
|---|---|
| 测试作业数据 | 使用 Odoo 标准 stock.picking / stock.move.line 作为本地出入库记录；不模拟 KR 作业过程、KR 数据格式或 Gateway。 |
| 库存生成 | 仅由标准 Odoo picking 验证/过账产生；不直接写 stock.quant。 |
| 产品主数据 | 按 TV-GINLONG-PRODUCT-001 v1.0 提出的 template/variant 方案纳入 CC；上游更新是冻结/实施门禁。 |
| 历史证据 | v0.1/v0.2 原稿保留；本稿为 Draft，不覆盖已关闭 CC-001–004 的任何历史结果。 |

## 附录 B — 版本记录

| 版本 | 日期 | 状态 | 说明 |
|---|---|---|---|
| v0.3 | 2026-11-19 | Draft | 按已关闭 TV v1.0 重写产品变体及 API07 规则；出入库用 Odoo `stock.picking` 建立本地测试记录，不模拟 KR/Gateway；保留外部联调和上游基线门禁。 |

**本次仅修改 CC-GIN-005 Draft。未修改代码、SRS、TDD、Implementation Plan 或既有 ATR/IHR；未运行测试。等待 Human Review。**
