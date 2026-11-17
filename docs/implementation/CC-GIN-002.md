<!-- CC-GIN-002 v1.0：Frozen then Closed. Human Review: APPROVED. Project CC template sync: BLOCKED (project template source absent); handled under the user's approved process exception. -->

# Coding Contract：CC-GIN-002

## 文档状态

| 项目 | 内容 |
|---|---|
| CC ID | CC-GIN-002 |
| 版本 | v1.0（Frozen；现已 Closed） |
| 当前状态 | Closed；Human Review APPROVED |
| 本 CC 范围 | API01 入库单、API03 出库单、API05 盘点任务、API07 产品档案 |
| 上游基线 | SRS v1.0 Frozen；TDD v0.3 Frozen with Open Items |
| 计划参考 | Implementation Plan v1.0 阶段 1；本次不修改计划 |
| 项目架构认知 | [PROJECT_COGNITION.md](../context/cognition/PROJECT_COGNITION.md) v1.1 |
| 关联文件 | [SRS](../requirement/SRS_ginlong_apis.md)、[TDD](../ginlong_apis/TDD.md)、[Implementation Plan](IMPLEMENTATION_PLAN_ginlong_apis.md) |
| 前序 CC | [CC-GIN-001 v1.0 Closed](CC-GIN-001.md)；[FR-GIN-001 v1.0](FR-GIN-001.md) |
| Human Review | APPROVED（项目用户明确批准）；2026-11-17 |
| 模板同步 | BLOCKED：项目模板来源缺失。依据项目用户批准的流程例外冻结；检查结果仍为 BLOCKED，不代表模板同步通过 |
| 授权 | 已授权修订并冻结本 CC v1.0，且授权按本 CC 实施编码；范围外工作仍未授权 |
| 关闭状态 | Closed；Closure SATISFIED；Human Review APPROVED（项目用户明确批准）；2026-11-17 |

## 1. 目标与三系统职责

本 CC 仅为四个 Ginlong 入站接口准备可评审的 Odoo 实施边界：API01、API03、API05、API07。Ginlong 下达业务指令，Odoo 接收并管理订单、再经 Gateway 转发给 Karl Rapp；Karl Rapp 执行实际仓库作业；Odoo 收到实际执行结果后，使用现有 stock.picking 记录执行，并由 Odoo 原生库存流程反映实际库存变化。

订单 Order 记录业务指令，stock.picking 记录实际执行结果。两者不建立强制关联，可按业务标识及产品、数量、批次、托盘等数据核对；一张 Order 可对应多次实际执行。

**收到 API01/03 订单不代表仓库已执行，不得因此确认实际执行完成或实际库存变化。** 是否按现有 WMS 逻辑创建待执行 stock.picking 或 stock.move，完全遵循既有业务流程；本 CC 不自行创建执行完成状态或过账库存。本 CC 仅处理订单接收与字段映射，不重新实现仓库作业或库存逻辑。

## 2. 范围

### 2.1 本次纳入

| ID | 变更项 | 范围及追溯 |
|---|---|---|
| CC-CHANGE-001 | API01 入库单 | 实现 SRS FR-GIN-001 的创建/删除核心行为；处理 owner、action、inboundOrderNo、warehouse、businessType、remark、details（productCode、name/productName、specificationModel、quantity）及 snList（productSN、quantity、palletCode、productCode、name/productName、specificationModel）字段，按现有 WMS 服务映射完整数据。订单接收不得确认仓库实际执行或实际库存变化；待执行 picking/move 是否生成完全遵循现有 WMS 逻辑。追溯：SRS FR-GIN-001、TDD §3.1、§3.2.1、§5.1、§6.1、T-WMS-001。 |
| CC-CHANGE-002 | API03 出库单 | 实现 SRS FR-GIN-003 的创建/删除核心行为；在 A-003「Solis → Odoo」开发假设下处理表头 owner、action、outboundOrderNo、warehouse、businessType、remark、customer、address、consignee、contact、contactEmail、shippingMethod，以及 details 中 productCode、productName、specificationModel、quantity、order_no、unit、net_wt_machine、net_wt_total、pack_qty、pallet_qty、pallet_len、pallet_wid、pallet_hgt、unit_vol、pack_unit、pack_wt、pallet_total_wt、total_vol、carton_wt_total、gross_wt_total、standard、pack_mode。逐字段映射至现有 Odoo WMS 订单/产品/包装对象或为保留未能由现有对象表达的已批准数据作最小继承扩展；不静默丢弃。订单接收不得确认实际执行或库存变化，待执行 picking/move 是否生成遵循现有 WMS 逻辑。方向及正式协议仍待 Ginlong 确认。追溯：SRS FR-GIN-003/A-003、TDD §3.1、§3.2.1、§5.1、§6.1、T-API03-001、T-WMS-001。 |
| CC-CHANGE-003 | API05 盘点任务 | 实现 SRS FR-GIN-005 的创建/删除核心行为；处理 owner、action、countOrderNo、warehouse、remark、details 中产品编码/名称/规格/数量及 snList 中目标 SN/数量/托盘/产品编码/名称/规格字段，映射到独立盘点任务和明细。不得将目标数量作为库存，不读写 stock.quant、不执行库存调整或过账。追溯：SRS FR-GIN-005、TDD §3.1、§3.2.2、§5.1、§6.1、T-COUNT-001。 |
| CC-CHANGE-004 | API07 产品档案 | 实现 SRS FR-GIN-007 的产品新增/修改核心行为；覆盖 owner、productCode、name、specificationModel、unit、power、nationalStandard、certificationModel、productForm、weight、length、width、height，复用 product.product、必要时按 TDD 扩展，并调用现有 WMS 产品主数据能力。不建立 Ginlong 产品档案或默认映射表，不新增 owner-product 归属规则。追溯：SRS FR-GIN-007、TDD §3.1、§3.2.1、§3.2.3、§5.1、§6.1、T-WMS-001。 |

**字段完整性与阻塞规则：** 本地模拟及验收必须覆盖上述 SRS 明确的核心字段和行为。Ginlong 未确认的 endpoint、HTTP 细节、action 枚举、字段类型/必填性、外部删除限制、单位转换或重复规则，不得成为省略已明确字段/核心功能的理由。测试可使用明确标注为本地模拟的输入契约。若实现某接口的完整核心字段映射或创建/删除/新增/修改行为确实被缺失信息阻塞，该接口验收状态必须为 BLOCKED；不得用部分字段映射判定该接口通过。

### 2.2 明确排除

- API02、04、06、08、10 的 Odoo 手动回传按钮及对外调用。
- API09 库存查询接口。
- Karl Rapp Gateway、VPN/FTP、XML 与 JSON 转换及真实三系统端到端联调。
- 订单货主与项目货主解绑，以及托盘生命周期完整管理和验收；两者仍是项目必须完成的需求，另安排独立 CC 或后续适当阶段。
- 新建通用映射、订单、库存、产品、托盘或日志模型；增加 owner-product 归属校验、强制 Order 与 stock.picking 关联、未经批准的业务规则或审批门禁。
- 任何由接收 Ginlong 指令直接确认完成收货/发货、确认实际库存变化或执行库存调整。现有 WMS 因订单处理生成待执行 picking/move 不在此禁止项内。

货主解绑与托盘生命周期不构成本 CC 整体冻结的前置条件。凡场景直接依赖货主脱离项目绑定的，仅将该场景排除或延后；API01/03 可按当前已支持的有效数据完成其余字段映射与自动化验收。凡字段处理直接依赖完整托盘生命周期语义的，仅延后该受影响场景；不得因此把生命周期验收塞入本 CC，也不得宣称已完成生命周期要求。

### 2.3 既有行为保持与技术约束

- 复用现有 Odoo Order、产品模型、WMS 服务、worlddepot 认证、Token、权限和 API 日志；不建立平行认证或日志框架。
- 不使用、不安装、不启用 stock_barcode。
- 不修改无关 WMS 作业、库存、订单行为，不新增业务映射或强关联。
- 数据库检查和操作仅通过项目现有 odoo.conf 的 Odoo Shell 使用 ORM；自动化测试使用 Odoo 标准测试机制及 ORM，不使用 SQL、psql 或数据库驱动直接访问。
- 复用现有开发环境、venv 和数据库 odooce_karlrapp，不新建虚拟环境或数据库。测试仅使用回滚测试数据或专用非业务数据，不改动真实业务单据和库存。
- 中间 CC 以 Odoo 自动化测试及组件/ORM 集成测试验收；人工业务流程与完整三系统 E2E 验收安排在最终集成 CC。

## 3. 上游基线与待决事项

本 CC 只要求其范围内所引用的 SRS/TDD 内容具备已批准依据。SRS v1.0 的 FR-GIN-001、FR-GIN-003、FR-GIN-005、FR-GIN-007 及 A-003，和 TDD v0.3 相应对象映射、字段处理、复用原则及防护约束，构成本稿的上游依据。未确认的 Ginlong 协议细节仅阻塞依赖这些资料的真实联调，不阻塞已批准字段的本地模拟测试。

| 事项 | 当前处置 |
|---|---|
| API03 方向 | 仅按 A-003 Solis → Odoo 假设进行本地开发；正式接口方向及协议待 Ginlong 确认。若确认方向不同，暂停并按变更流程调整受影响接口。 |
| Ginlong 报文与业务细节 | endpoint、认证/响应、枚举、单位、删除、重复、迟到及更新规则按外部正式契约确认；不得从示例推定。只验证已有批准字段。 |
| 货主解绑 | 项目必需后续需求，当前不是本 CC 的总体冻结门槛；订单 Owner 与项目 Owner 不同的具体场景由后续独立 CC/阶段处理。 |
| 托盘生命周期 | 项目必需后续需求，当前不要求本 CC 设计或证明完整生命周期；仅将确实依赖生命周期语义的字段/场景延后。 |
| API05 库存读取表述 | 本 CC 的 API05 不实现库存查询，不读写 stock.quant，不执行库存调整/过账；这不是对其他独立只读查询的一般禁令。TDD v0.3 T-COUNT-001 对 API05/10 还写有不读取 stock.quant/stock.move 的较严限制；本 CC 无需进行此类读取。若实施发现 API05 需要只读库存数据，暂停该受影响场景并先澄清/修订 TDD，不以 CC 覆盖冻结 TDD。 |
| CC 模板同步 | 仍为 BLOCKED：项目模板来源缺失。按用户指示沿用此前批准的流程例外进行后续评审准备，绝不伪记为同步 Passed。 |

Implementation Plan v1.0 保持不变，本次不修订其阶段或追溯表；本稿缩小 CC 候选范围，不代表已更新 Plan 基线。此项不列为本稿的 SRS/TDD 上游门禁。

## 4. 自动化与组件集成验收

测试使用 Odoo 标准测试运行器和 ORM；运行结果记录至对应 ATR/IHR。真实 Ginlong 联调、人工仓库操作及完整业务流程由最终集成 CC 验收。每个接口测试须同时覆盖本 CC 列出的全部 SRS 核心字段及核心行为；缺少任何一项时该接口不得标记 Passed，确实无法完成则标记 BLOCKED 并记录阻塞原因。

| ID | 范围 | 验收条件 |
|---|---|---|
| CC-TEST-001 | API01 | 使用覆盖全部 CC-CHANGE-001 字段的本地模拟请求，分别验证 SRS 核心创建和删除行为及现有 WMS 服务调用；字段映射不缺项。接收指令不得将 picking/move 置为实际完成或确认库存变化；允许现有 WMS 服务按其既有逻辑创建待执行 picking/move。 |
| CC-TEST-002 | API03 | 在 A-003 本地模拟下使用覆盖全部 CC-CHANGE-002 字段的请求，分别验证核心创建和删除行为及现有 WMS 服务调用；字段映射不缺项。不得将 picking/move 置为实际完成或确认库存变化；允许现有 WMS 服务按其既有逻辑创建待执行 picking/move。测试不得把 A-003 表述为 Ginlong 已确认方向。 |
| CC-TEST-003 | API05 | 使用覆盖全部 CC-CHANGE-003 字段的请求，验证核心创建/删除行为以及独立盘点任务和明细映射；不得把目标数量写成现存量，不读写 stock.quant，不调用库存调整/过账。 |
| CC-TEST-004 | API07 | 使用覆盖全部 CC-CHANGE-004 字段的新增和修改模拟请求，验证完整字段经现有产品对象及 WMS 主数据能力处理；不创建 Ginlong 产品/映射模型，不增加 owner-product 归属校验。 |
| CC-TEST-005 | 共用入口 | 对四个接口覆盖现有认证/权限及 API 日志复用路径；校验未授权请求不改变业务对象，日志不泄露 Secret、Token、Authorization 等凭据。 |
| CC-TEST-006 | 安装与回归 | 使用现有 Odoo 配置和数据库运行模块相关自动化/组件集成测试；必要的现有 WMS 回归只覆盖被调用服务及其既有行为，不将未执行的人工流程记为通过。 |

直接依赖货主解绑或托盘生命周期的测试数据/行为不属于上述验收：相应单独场景标记为未覆盖并交后续 CC，不阻止本 CC 其余适用验收。每项实际测试须在 ATR/IHR 记录原始结果、运行环境和证据；未运行或受阻项如实标记 NOT RUN/BLOCKED。

## 5. 不确定项及停止条件

1. 未确认的外部规则不得由实现者或测试者补造。若某字段的实际映射必须依赖未批准的单位换算、业务键、删除/重复处理或订单执行语义，暂停该字段/场景并记录依赖，不扩大为整个 CC 的阻塞。
2. API03 保持可替换的本地假设入口；收到 Ginlong 正式方向后，先评估其对 SRS/TDD/本 CC 的影响，再实施相应变更。
3. 若代码实施发现冻结 TDD 与本 CC 的解释不一致，或要求突破现有 WMS 服务边界，暂停受影响范围并升级处理；本 CC 不授权偏离 TDD。
4. 货主解绑、托盘生命周期、API09、出站按钮和 Gateway 均不得以“顺手完善”方式并入本 CC。

## 6. 冻结与完成条件

Human Review 已批准本 CC v0.2，经限定修订后冻结为 v1.0。随后依据 FR-GIN-002 v1.0（Closure SATISFIED；Human Review APPROVED）关闭本 CC。模板同步保持 BLOCKED，并按项目用户批准的流程例外记录；不把模板缺失伪记为同步通过。编码授权仅限本 CC v1.0 明确的范围和验收条件。

实际开发完成后，依 CC 冻结版本执行自动化及组件集成验收，并按项目流程完成 IHR、ATR 与 FR。完整人工业务验证和三系统 E2E 留待最终集成 CC。

## 7. 当前项目状态

- CC-GIN-001 v1.0：Closed，Human Review APPROVED；其范围不包含本 CC 四个接口。
- CC-GIN-002 v1.0：Closed；FR-GIN-002 v1.0 Closure SATISFIED；Human Review APPROVED。
- HTTP E2E、Ginlong 真实联调、完整 WMS 人工流程及模板来源同步：沿用既有 NOT RUN/BLOCKED 记录，不改写为 Passed。
- 货主解绑与托盘生命周期：作为项目必须完成的后续需求保留，分别安排独立 CC 或后续适当阶段。

## 附录：版本记录

| 版本 | 日期 | 状态 | 说明 |
|---|---|---|---|
| v0.1 | 2026-11-17 | Draft | 首版阶段 1 候选契约；曾把货主解绑与托盘生命周期上游更新列作 CC 门禁，并纳入相应验收项。 |
| v0.2 | 2026-11-17 | Draft | 按评审意见将范围收窄为 API01/03/05/07；把货主解绑与托盘生命周期移出本 CC 整体门禁及验收；明确三系统职责、订单接收不等于仓库执行、A-003 外部待确认、盘点库存边界和自动化/组件集成验收。模板同步仍 BLOCKED；未冻结、未授权编码。 |
| v1.0 | 2026-11-17 | Frozen | Human Review APPROVED。按批准意见明确 API01/03 接收订单与实际执行/库存变化的区别，待执行 picking/move 遵循现有 WMS；CC-TEST-001/002 同步调整。补齐四接口的 SRS 核心字段及行为覆盖，并规定核心功能无法完成时标记 BLOCKED，不以部分字段映射判为通过。模板同步仍 BLOCKED，按用户批准的流程例外冻结；授权本 CC 范围内编码实施。 |
| 关闭记录（v1.0） | 2026-11-17 | Closed | 依据 FR-GIN-002 v1.0：Closure SATISFIED、Human Review APPROVED。ATR 最终有效基线为 ATR-RUN-009。模板同步、Ginlong 外部协议及 API03 方向继续保留 BLOCKED/待确认状态。 |
