# CC-GIN-005 v0.2 — 本地 UI/WMS 集成与端到端验收（Draft）

| 项目 | 内容 |
|---|---|
| CC ID / 版本 | CC-GIN-005 / v0.2 Draft |
| 状态 | **Draft；待 Human Review；未冻结；未授权编码或测试** |
| Intent ID | `GINLONG-LOCAL-UI-WMS-E2E-005` |
| 模块 | `ginlong_apis`、现有 `worlddepot` / Odoo WMS；`karlrapp_gateway` 为独立项目，仅可选验证接口衔接 |
| 目标 | 使用本地 HTTP、Mock Ginlong 回传及模拟 Karl Rapp 执行结果，在本地 Odoo 中验证 Ginlong API 与现有 WMS 的端到端业务流程及浏览器 UI。 |
| SRS 基线 | [SRS ginlong_apis v1.0 Frozen](../requirement/SRS_ginlong_apis.md) |
| TDD 基线 | [TDD v0.9 Frozen](../ginlong_apis/TDD-v0.9.md)；保留其引用的历史版本，不改写已关闭 CC 基线 |
| Implementation Plan | [v1.6 Frozen](IMPLEMENTATION_PLAN_ginlong_apis-v1.6.md)；阶段状态见 [v1.7](IMPLEMENTATION_PLAN_ginlong_apis-v1.7.md) |
| 前序 CC | CC-GIN-001、002、003、004 均 Closed；不重开其组件验收 |
| 后续阶段 | CC-GIN-006：真实 Ginlong 测试环境联调，须另行授权 |
| 项目模板同步 | **BLOCKED**：项目模板来源缺失；沿用既有批准例外，草案仅参考 skill 模板结构，不伪记同步通过 |
| 人工评审 | 待定；不得推定已批准 |

> 本草案依据 Implementation Plan 阶段 4 和 Human Review 意见修订。它不修改 SRS、TDD、Plan 或 CC-GIN-001–004，不授权实施。KR 执行结果使用明确标记的本地模拟数据，由现有 WMS 流程处理；`karlrapp_gateway` 属于独立项目，Gateway 验证为可选项，不影响本 CC Done Gate。任何模拟结果都不代表真实 KR Gateway、Ginlong 测试环境或生产联调通过。

## 1. 上游基线与职责

### 1.1 系统职责

- **Ginlong** 下达入库、出库、盘点和产品指令，查询库存并接收仓库执行结果。
- **Odoo / `worlddepot`** 接收并管理业务 Order、货主/API 用户/Token、盘点指令及实盘结果；依据 Karl Rapp 返回的实际结果使用 `stock.picking` 和 Odoo 原生库存机制记录实际移动。
- **Karl Rapp WMS** 执行收货、上架、拣选、发货及现场盘点，是实际仓库作业数据来源。
- **Karl Rapp Gateway** 负责 Odoo ↔ Karl Rapp 的文件通信和 XML/JSON 转换，不承担订单、库存计算或业务决策。
- **`ginlong_apis`** 负责 Ginlong 接口、数据转换、持久化回传界面及接口调用，不重做 WMS 或 Gateway 业务。

### 1.2 适用需求与技术依据

| 来源 | 范围 | 本 CC 用途 |
|---|---|---|
| SRS FR-GIN-001/003/005/007 | Ginlong 入站订单、盘点指令及产品资料 | 验证已实现接口与现有 Order/产品模型的业务流衔接；不重做已关闭接口组件测试 |
| SRS FR-GIN-002/004/006/008/010 | 五个人工回传接口 | 验证业务单据、持久化 Form、用户手动发送、结果与日志在实际 UI 流程中的衔接 |
| SRS FR-GIN-009 | 库存查询 | 验证已实现 API09 在 WMS 实际库存记录更新后的查询结果及只读性 |
| TDD v0.9 §§1–7 | 三系统数据流、Form、回传来源、调用、日志、API09 与管理入口 | 作为现行技术边界；外部未决协议仍按原接口隔离 |
| Plan v1.6 阶段 4 / Plan v1.7 阶段 4 | 本地集成及完整 UI/WMS E2E | 本 CC 的范围和顺序依据 |
| CC-GIN-001–004 | 已关闭实现与自动化证据 | 只验证集成链路和端到端 UI，不重复原 CC 的组件验收 |
| API01/API03 后续决策 | [IHR-GIN-003 IHR-021](IHR-GIN-003.md)；[ATR-GIN-003 RUN-049–055](ATR-GIN-003.md) | 项目负责人已批准的货主创建/复用、API03 复合键拒绝规则；不重开原 CC/FR |

本项目无独立 DDD 基线；本 CC 不创建领域模型或新的业务不变量。

API03 的方向按后续 Ginlong 接口矩阵和 TDD v0.9 记录为 Ginlong → Odoo；SRS 中较早的 A-003 仅是历史开发假设，不在本 CC 重开。

## 2. 范围

### 2.1 本 CC 范围内

1. 在既有 Odoo 开发环境执行本地端到端流程，覆盖 Ginlong API01/03/05/07 入站、现有 WMS 订单处理、模拟 KR 执行结果、五个手动回传接口及 API09 查询之间的连接。
2. 使用本地 Odoo HTTP 测试客户端/测试调用验证 Ginlong 入站接口；出站回传使用 Mock HTTP。不得调用 Ginlong 测试或正式环境。
3. 使用浏览器执行并记录完整 Odoo 用户流程：业务单据查找、数据保存、重新打开、必要编辑、实际 WMS 操作记录、单据回传、日志定位和 API09 查询。
4. 验证五个回传按钮均位于既有业务 Order；继续使用持久化 Form/Notebook，不使用 TransientModel Wizard、不向业务用户展示 JSON 编辑器。
5. 验证 API04/06 来自实际 `stock.picking` / `stock.move.line`；API10 来自 `worlddepot` 客户盘点订单关联的实盘结果；API02/08 使用现有 Order 业务状态。
6. 使用模拟 KR 执行结果，通过现有 Odoo WMS 流程记录出入库；不得直接修改 `stock.quant`。API01/03 收到 Ginlong 指令本身不构成实际执行或库存变化。
7. 验证 API09 的 `owner`、`warehouse` 按现有 Odoo 编码字段精确匹配，覆盖双货主×双仓库交叉隔离、未知货主、未知仓库和空库存；返回实际物理库存且不扣预留量，查询严格只读。
8. 执行本 CC 触及的必要 WMS 集成回归；沿用 CC-001–004 的既有测试证据，不为满足“完整”而无差别重跑已通过的组件套件。
9. 对集成缺陷进行最小修复仅在本 CC 获批后授权范围内；如需改变业务语义、外部契约、数据权威关系、WMS 核心行为或 TDD 设计，先停止并提交相应上游变更。

### 2.2 范围外

- 真实 Ginlong HTTP、Ginlong 测试/生产环境、生产数据库或真实凭据访问；属于 CC-GIN-006，须单独授权。
- 连接真实 Karl Rapp WMS 的 VPN/FTP、现场作业及真实仓库验收。
- 新建或重做 Karl Rapp Gateway、文件协议、XML Schema、库存同步机制；Gateway 属独立项目，不在本 CC 变更范围。
- 重复开发订单、库存、盘点、托盘、产品或 API 日志模型；新增通用集成层、队列、自动回传、自动重试、监控平台、审批或业务状态机。
- 重新执行 CC-GIN-001–004 的单元/组件验收矩阵；仅在 E2E 失败定位或回归风险明确时运行对应最小测试。
- 实施新的货主解绑、托盘生命周期或其他未纳入已批准 TDD / 本 CC 的需求。
- 修改官方 Odoo `stock` 代码、使用 `stock_barcode`，或以直接写 `stock.quant` 的方式模拟实盘/出入库。

## 3. 数据与业务防护栏

| 数据/事件 | 验收依据 |
|---|---|
| API01 | 按 `res.partner.ginlong_owner_code` 查询货主：不存在时自动创建并关联订单，已存在时复用。相同请求重复提交不得重复创建货主；幂等及订单处理遵循已批准实现。接收订单不等同实际执行或库存变化。 |
| API03 | 先按 `res.partner.ginlong_owner_code` 查找已有货主，再按 `owner + productCode` 匹配每条明细；货主或任一产品组合不存在时拒绝整单，不自动创建货主/产品。多明细中有无效组合时不得留下部分订单/明细/库存业务记录。 |
| API05 / API10 | 客户盘点指令与仓库实盘结果分别核对。API10 只从已保存、与客户盘点订单相关联的实际盘点结果取数；API05/10 不读写 `stock.quant`，不执行库存调整。 |
| API07 | 产品由 `owner + productCode` 识别；相同 `productCode` 可属于不同货主，端到端过程不得串货主。 |
| API02 / API08 | 使用对应 `worlddepot` Order 上已有业务状态/持久化明细；混合 Y/N 状态继续按已批准行为阻止发送，不增加新的状态或审批规则。取消控制和取消回传若仍未获确认，不纳入 E2E 断言。 |
| API04 / API06 | 只读取实际 picking/move line。API06 必须验证备货完成事件与实际备货数据，不以 picking 创建或库存过账替代备货完成。逐行 SN、产品、数量、托盘及人员/时间使用 TDD 已定数据来源。 |
| API09 | `owner` 精确匹配 `res.partner.ginlong_owner_code`，并以其 partner 记录匹配 `stock.quant.owner_id`；`warehouse` 精确匹配 `stock.warehouse.code`；响应 `productCode` 取 `stock.quant.product_id.default_code`。不按 Contact Name/仓库名称匹配，不因只有一个仓库而忽略请求编码或回退查询。 |
| API09 数据语义 | 按 `(owner, warehouse, productCode)` 隔离，返回 `stock.quant.quantity` 的实际物理数量，不扣预留量；未知货主/仓库不得泄露其他范围库存，空库存返回空清单。 |
| 人工回传 | 用户在已保存的业务数据上手动点击对应 Order 按钮。HTTP 请求同步 POST、`application/json`，使用配置的 Endpoint 和 Mock 服务；每次尝试独立追加现有 API 日志，不覆盖历史日志。 |
| Order 与 `stock.picking` | 两者业务职责独立，不增加强制关联；允许按已批准业务标识及实际明细核对。多张 picking/分批语义仍遵从已确认契约，未确认场景隔离，不猜测。 |

## 4. 变更边界

### 4.1 获批后可涉及的范围

| 区域 | 允许范围 |
|---|---|
| `mymodules/ginlong_apis/**` | 本地 E2E 必需的既有 API/Form/日志路径最小修复、测试和测试数据辅助；不建立新框架或平行模型 |
| `mymodules/worlddepot/**` | 仅在 E2E 证明本项目既有 WMS 集成路径有缺陷且可追溯到已批准 SRS/TDD 时作最小修复，并增加现有 WMS 回归；不作无关重构 |
| 自动化/人工验证文档 | 本 CC 专属自动化结果追加 ATR；浏览器人工验证追加 HVR；实施历史追加 IHR；关闭评估另行形成 FR |
| Gateway 边界 | 不修改或创建 Gateway；若独立项目的本地测试入口可用，可执行 CC-TEST-056 可选验证 |

具体代码文件和方法必须在冻结版本中根据发现的实际缺陷进一步限定。本 Draft 不授权更改代码、模块、数据库或环境。

### 4.2 禁止

- 数据库检查、准备和清理仅经现有 Odoo ORM/测试框架；不新建隔离数据库/虚拟环境，不替换项目既有配置。
- 不使用 `stock_barcode`，不直接写 `stock.quant` 或伪造已过账 Picking；出入库测试必须走现有 WMS 流程。
- 不访问真实 Ginlong/生产或真实 KR 现场；不改建独立 Gateway；不破坏既有用户数据、工作区内容或历史证据。

### 4.3 必需的集成行为

| ID | 现状/边界 | 本 CC 期望验证 | 来源 |
|---|---|---|---|
| CC-CHANGE-001 | 已实现的 Ginlong 入站接口和 WMS Order 分属不同组件，尚无阶段 4 的完整用户流程证据 | API01/03/05/07 经本地入站路径进入现有业务记录，并能由用户在 Odoo 中继续既有 WMS 流程；接收业务指令不冒充仓库执行 | SRS FR-GIN-001/003/005/007；TDD v0.9 §1；Plan 阶段 4 |
| CC-CHANGE-002 | 五个人工回传接口已有持久化 Form、按钮、HTTP 和日志组件证据，尚未完成人工完整 UI 路径验收 | 从 Order Form 保存/重新打开业务数据，到用户手动发送、Mock 响应、失败修正和日志定位，逐项验证 API02/04/06/08/10 的实际业务数据来源 | SRS FR-GIN-002/004/006/008/010；TDD v0.9 §§2–5 |
| CC-CHANGE-003 | API09 组件测试以明确标记的模拟库存为主，未证明其与完成的本地 WMS 流程衔接 | 在本地 WMS 已通过标准流程生成库存记录后验证 API09 返回物理库存并保持只读；模拟结果与实际开发库业务数据来源分别记录 | SRS FR-GIN-009；TDD v0.9 §7；Plan 阶段 4 |
| CC-CHANGE-004 | 组件级验收已分别记录，完整角色和 WMS 浏览器流程尚未执行 | 完成受影响 WMS 回归和人工浏览器 UI/WMS E2E；Gateway 交接单列状态，不可用时不得把单边 Odoo 流程报为三系统 E2E 完成 | Plan 阶段 4；CC-TEST-054–056 |

## 5. 环境、数据与执行前置条件

| 前置条件 | Draft 约定 |
|---|---|
| Odoo 环境 | 使用现有 `venv`、`odoo.conf` 和 `odooce_karlrapp`；只经 Odoo Shell/测试框架 ORM 访问数据库。测试前记录实际模块版本和服务状态。 |
| 本地数据 | 先识别可安全使用的测试货主、产品、仓库和订单。测试数据以 ORM 建立并标记；只清理本次创建的数据。需要实际 `stock.picking` 记账时走现有 WMS 方法/界面，禁止直接写库存。无法避免影响现有业务数据时停止，提交隔离数据方案供项目负责人决定。 |
| 出站 HTTP | 仅使用本地 Mock HTTP；所有回传 Endpoint 指向 Mock，测试期间核对不会请求 `10.0.3.182` 或其他真实外部主机。 |
| 浏览器 | 使用具备批准角色权限的本地 Odoo 用户；HVR 记录角色、操作路径、输入数据引用、预期/实际结果及截图或等价证据。不得在报告中记录 Secret/Token 明文。 |
| Gateway | 属独立项目；本仓库未发现其模块。定位到独立项目/测试服务后可选做接口级验证；缺失时 CC-TEST-056 记为 NOT RUN/BLOCKED，不影响 CC-005 Done Gate。 |
| 外部协议 Open Items | 继续沿用 CC-GIN-003/TDD 按接口管理的 Open Items。只运行有已确认契约和已保存数据来源的本地场景；未确认部分逐项 BLOCKED/NOT RUN，不阻塞不依赖它们的场景。 |
| 文档模板 | 当前模板来源检查 BLOCKED；沿用已批准流程例外。草案需 Human Review；后续不得将模板同步写为 PASS。 |

## 6. 测试契约

下表为拟议 CC-TEST 编号。起草时所有项目均为 **NOT RUN**；此表不是测试结果或授权。已关闭 CC-001–004 的组件测试不重复执行。

| 测试 ID | 集成场景 | 预期结果 / 证据 |
|---|---|---|
| CC-TEST-044 | 环境与路由准备 | 确认使用既有配置/数据库、Ginlong 与 WorldDepot 模块版本、测试用户角色、Mock Endpoint；确认测试数据来源及清理边界。不满足前置条件时停止并记录 BLOCKED。 |
| CC-TEST-045 | API01 货主档案与幂等整单流程 | 对不存在的 owner code 发入库请求，验证按编码自动创建并关联一条 `res.partner`；已存在编码再次发单时复用同一档案；相同请求重放不重复创建货主或订单，遵循已批准幂等结果。订单接收不确认实际收货或库存变化。 |
| CC-TEST-046 | API03 货主/产品复合键与事务完整性 | 已存在 owner 下按 `owner + productCode` 匹配每条明细；未知 owner 或任一缺失产品组合时拒绝订单，不创建 owner/product。多明细中前项有效、后项无效时验证请求回滚/拒绝后无订单、部分明细、Picking 或库存副作用；UPDATE 失败时原订单不被部分修改。 |
| CC-TEST-047 | API07 产品主数据到后续订单的端到端使用 | 通过本地入站路径维护产品；不同货主可有相同 `productCode`；后续订单查找只关联对应 `owner + productCode`。保存/重新打开记录可追溯。 |
| CC-TEST-048 | 入库模拟作业、Order 状态及 API02/API04 | 将模拟 KR 收货结果交给现有 WMS 流程处理并生成实际收货业务记录/Picking；仅由原生 WMS 流程更新库存。分别验证 API02 从已保存 Order 收货明细和状态取数（收货确认），API04 从实际 Picking/move line 取数（入库完成）；两者不能互相替代，用户分别手动发送到 Mock 并追加日志。 |
| CC-TEST-049 | 出库模拟作业、备货/发货及 API06/API08 | 由现有 WMS 流程处理模拟执行结果；验证 API06 对应备货完成事件与实际 move line 数据，不能因 Picking 创建或过账自动等同备货完成；API08 对应 Order 发货状态。两接口分别手动发送到 Mock，日志可定位原单。 |
| CC-TEST-050 | API05 盘点指令与 API10 实盘回传 | API05 客户盘点订单与实盘结果保持独立；用户在 UI 保存/重开实盘结果后，API10 只发送该订单下选中的实际结果。不得读取计划值或 `stock.quant` 推算结果，不做库存调整；Mock 日志关联客户盘点订单。 |
| CC-TEST-051 | API09 编码匹配、交叉隔离、空结果及只读 | `owner` 精确匹配 `res.partner.ginlong_owner_code` 并用于隔离 `stock.quant.owner_id`；`warehouse` 精确匹配 `stock.warehouse.code`。用现有 WMS 流程形成测试库存，不直接写 quant。覆盖 OWNER-A/WH-A/P001=100、OWNER-A/WH-B/P001=200、OWNER-B/WH-A/P001=300、OWNER-B/WH-B/P001=400，四种请求各只返回对应数量；相同 productCode 跨 owner 不合并。未知 owner 返回空列表且不泄漏；未知 warehouse 按既有错误契约拒绝且不回退到唯一仓库；已知 owner/warehouse 无库存返回空 `inventoryList`。数量为 `stock.quant.quantity` 物理量，不扣 reserved；请求前后 quant/move/picking 快照一致。 |
| CC-TEST-052 | 五个回传接口的完整 UI 操作 | 逐项打开既有 Order Form/Notebook，检查订单号、业务事件、关联实际作业/实盘和关键字段；保存后关闭并重新打开；由 Order 上的按钮使用 ORM 已保存值发送。无 Wizard、JSON 编辑器或未保存前端值依赖。由 Codex 使用浏览器模拟用户操作并将过程与截图/结果记入 HVR，明确标注为 Codex 浏览器模拟，不标为业务负责人已验收。 |
| CC-TEST-053 | 人工回传失败、修正、重发和日志追溯 | Mock 首次返回失败；用户保存修正并再次点击；第二次从 ORM 读取新值并新增日志，旧日志请求/响应不变；日志可定位源单。无后台自动重试。 |
| CC-TEST-054 | E2E 菜单导航与日志追溯 | 从 Ginlong 业务列表进入原单；从失败日志打开该原单并返回现有按钮。CC4 已通过的菜单/ACL 组件结果引用原 ATR；仅在本 CC 变更权限/导航时补跑相应自动化。 |
| CC-TEST-055 | 受影响 WMS 流程回归 | 浏览器 E2E 经过现有入库、出库、Picking/Move Line 及原生库存流程；盘点指令与实盘结果独立，跨货主同码不串货主。引用 CC3 既有自动化回归证据；仅在本 CC 代码变更或 E2E 暴露风险时运行最小相关回归。 |
| CC-TEST-056（可选） | Odoo ↔ 独立 Karl Rapp Gateway 本地接口交接 | 仅在 Gateway 独立项目和本地测试接口可用时执行；验证模拟结果经过该既有接口进入现有 WMS。当前未发现 Gateway 代码，暂记 NOT RUN；为非阻断性可选测试，不属于 Done Gate。若执行，结果仅说明本地模拟接口，不代表真实 KR Gateway/VPN/FTP 联调。 |

### 6.1 验收证据

- 自动化与 ORM 集成结果记录在 ATR；浏览器人工流程逐步记录在 HVR；实现/配置变更记录在 IHR。每条测试注明环境、模块/代码版本、输入数据类型（真实 Odoo 业务数据或模拟数据）、操作路径、结果及证据位置。
- Codex 先以浏览器模拟用户完成 CC-TEST-052 并形成 HVR 证据，明确记录操作者为 Codex、测试方式为浏览器模拟。随后由业务负责人在实际浏览器中进行最终人工验收并签署 HVR/评审记录；两者状态分开记录。
- 本地 Ginlong 请求和 Mock 回传仅证明本地契约路径，不证明真实 Ginlong 可用。
- CC-TEST-056 为可选项；未执行或不可用时如实记录 NOT RUN/BLOCKED，不阻塞本 CC 关闭，也不得宣称真实 Gateway 联调通过。
- 不执行 SQL；测试夹具/清理仅使用 Odoo 测试事务或 ORM。保持已有用户数据、日志和先前 ATR/IHR 历史。

## 7. 既有行为保留

| ID | 保留行为 | 依据 |
|---|---|---|
| CC-PRESERVE-001 | Ginlong 指令只建立/更新业务要求；不冒充 KR 实际执行，不直接改库存 | SRS §4/§6；项目认知 v2.9 §3 |
| CC-PRESERVE-002 | `worlddepot` Order、盘点订单/实盘记录及 Odoo `stock.picking` 的数据权威关系不变；Order 与 Picking 不强关联 | TDD v0.9 §1；项目认知 §3 |
| CC-PRESERVE-003 | 五个回传按钮保留为用户手动操作；持久化 Form、POST JSON、同步调用、失败后手动修正/重发、日志追加 | TDD v0.9 §§2–5；CC-GIN-003 v1.4 |
| CC-PRESERVE-004 | API05/API10 不把客户盘点指令当作实际结果，不读写 `stock.quant` 或调整库存 | 项目认知 §3；TDD v0.9 §§1、4 |
| CC-PRESERVE-005 | 复用 `worlddepot` 现有 API 认证、Token、权限及日志；不新增认证、日志、重发或限流系统 | CC-GIN-001–004；TDD v0.9 §§5、7 |
| CC-PRESERVE-006 | 不使用 `stock_barcode`；不触碰真实 Ginlong/生产接口；不以模拟数据声称真实 KR 库存同步通过 | 用户明确约束；Plan v1.6/v1.7 |

## 8. 风险与 Open Items

| ID | 项目 | 现有依据/影响 | Draft 处置 |
|---|---|---|---|
| OI-GIN-005-01 | API09 仓库匹配的历史基线差异 | 冻结的 Plan v1.6 / CC-GIN-004 v1.0 描述单仓库直接查唯一仓库且不匹配 Ginlong 编码；后续 TDD v0.9 / CC-GIN-004 v1.1 补充采用 `stock.warehouse.code` 精确匹配并覆盖多仓隔离 | 本草案按最新已记录实现列出编码匹配测试，但不改历史文件。Human Review 冻结前确认后续补充是否作为当前控制基线；若不接受，应先走上游文档变更，不得在 CC 中改写旧基线 |
| OI-GIN-005-02 | Ginlong warehouse 编码与 Odoo 字段长度 | 请求允许 VARCHAR(40)；现有 `stock.warehouse.code` 为短码字段，真实 Ginlong 仓库编码兼容性未联调 | 只按 Odoo 配置值精确匹配，不截断、不按名称匹配、不回退唯一仓库；真实编码兼容留 CC-GIN-006 |
| OI-GIN-005-03 | `karlrapp_gateway` 独立项目可用性 | 当前仓库未发现 Gateway 模块或测试入口；本 CC 主流程使用模拟 KR 结果交给 Odoo WMS 处理 | CC-TEST-056 为可选、非阻断；有本地接口时执行并如实记录，无接口时 NOT RUN/BLOCKED，不声称真实 KR 联调 |
| OI-GIN-005-04 | Ginlong 外部语义 Open Items | CC-GIN-003/TDD 对 API02/04/06/08/10 的部分分批、撤回或特定字段语义仍有未决项 | 按接口和场景隔离。正常且已有依据的本地 E2E 可执行；未确认场景 BLOCKED/NOT RUN，不猜测 |
| OI-GIN-005-05 | 安全测试数据隔离 | 使用开发库，用户明确不新建隔离数据库 | 测试前确定可识别数据并计划仅用 ORM 清理本次新增数据；不能避免影响既有业务记录时，暂停该场景 |
| OI-GIN-005-06 | 模板同步 | 项目模板源缺失；检查结果 BLOCKED | 沿用已批准例外；保持 BLOCKED，不作为 PASS |

### 8.1 冻结基线差异供 Human Review

| 差异 | 冻结历史基线 | 后续记录/本草案 | 需评审决定 |
|---|---|---|---|
| API09 仓库过滤 | Plan v1.6、CC-GIN-004 v1.0：当前单仓库，直接查唯一 Odoo 仓库，不映射/匹配请求仓库编码 | TDD v0.9、CC-GIN-004 v1.1 与后续测试：请求 `warehouse` 精确匹配 `stock.warehouse.code`，多仓交叉隔离，未知值拒绝 | 确认后续补充作为阶段 4 的控制技术依据；如需修改 Frozen 上游，先另行走上游修订流程。本 CC v0.2 不覆盖两种历史表述 |
| API01/API03 货主处理 | CC-GIN-003 原冻结版本不含其关闭后实施的完整货主创建/拒绝补充 | 项目负责人决策已通过 IHR-021、ATR-RUN-049–055 记录；TDD v0.9 描述当前处理 | 按已批准的项目负责人决定用于 E2E 验收；不重新打开 CC-GIN-003/FR-GIN-003 |

## 9. 停止条件与升级

1. 发现已冻结 SRS/TDD/Plan/CC 与本草案的业务或技术语义冲突时，记录差异并提交 Human Review；不得自行修改上游或在 E2E 中补造规则。
2. 测试需访问真实 Ginlong/生产/真实 KR VPN/FTP，或需要绕过 ORM、直接改库存、启用 `stock_barcode` 时，停止受影响场景。
3. 测试数据可能破坏既有业务数据且无法通过 ORM 安全隔离/清理时，停止该场景。
4. 外部 Open Item 只阻断直接依赖的场景；未决内容如实记 BLOCKED/NOT RUN，不影响有依据场景的独立验收。

## 10. Done Gate（拟议）

CC-GIN-005 只有在 Human Review 批准本 Draft 并另行授权实施后，才进入执行。建议关闭需满足：

1. 本 CC 范围内的 UI/WMS 端到端场景均有 ATR/HVR 证据；PASS、PARTIAL、FAIL、BLOCKED、NOT RUN 如实记录。
2. API01 不存在 owner 自动创建、已存在复用、相同请求不重复建档均通过；API03 未知 owner/owner-product 组合被拒绝，含多明细无效行时事务无部分业务记录。
3. API09 编码字段映射、双货主×双仓隔离、未知 owner/warehouse、空库存、实际物理数量、不扣 reserved 和严格只读均通过；基线差异 OI-GIN-005-01 在 Human Review 中有明确处置。
4. 五个人工回传接口均经持久化 Form 保存、重开、用户点击、Mock 接收和日志追溯；区分 API02 收货确认/API04 入库完成及 API06 备货完成/API08 发货完成。
5. 所有模拟实际出入库均通过现有 WMS 流程处理；API05/API10 不改变库存；受影响 WMS 回归通过。
6. Codex 浏览器模拟操作的 HVR 证据完成，业务负责人另行完成最终人工验收并记录批准；真实 Ginlong和生产访问保持未执行。
7. CC-TEST-056 可选，不属于 Done Gate；如执行需如实报告，仅为本地 Gateway 接口测试，不代表真实联调。
8. 更新 IHR、ATR、HVR 和 FR 并提交 Human Review；不将 BLOCKED、NOT RUN 或未批准事项记为 PASS。

## 11. 追溯矩阵

| 上游 | CC 范围/测试 | 追溯关系 |
|---|---|---|
| SRS FR-GIN-001 | CC-CHANGE-001；CC-TEST-045 | API01 owner 不存在创建、存在复用、重复请求不重复建档并关联入库 Order |
| SRS FR-GIN-003 | CC-CHANGE-001；CC-TEST-046 | API03 owner 与产品复合键、拒绝无效请求及多明细事务完整性 |
| SRS FR-GIN-005/007 | CC-CHANGE-001；CC-TEST-047、050 | 盘点指令/产品主数据进入现有业务模型，盘点事实保持分离 |
| SRS FR-GIN-002/004/006/008/010 | CC-CHANGE-002；CC-TEST-048–050、052–053 | 执行/实盘来源、事件区分、人工回传及日志 |
| SRS FR-GIN-009 | CC-CHANGE-003；CC-TEST-051 | 编码匹配、跨 owner/warehouse 隔离、物理库存与只读行为 |
| TDD v0.9 §§1–5 | CC-PRESERVE-001–005；CC-TEST-045–053 | 三系统职责、持久化 Form、回传来源、同步调用及日志 |
| TDD v0.9 §7 / CC-GIN-004 | CC-CHANGE-003/004；CC-TEST-051、054 | API09、菜单/日志与失败单据定位在完整用户流程中的行为 |
| Plan v1.6 阶段 4、Plan v1.7 阶段 4 | CC-CHANGE-001–004；CC-TEST-044–055 | 本地完整 UI/WMS 集成；CC-TEST-056 可选，不纳入 Done Gate |

## 12. 评审与授权

| 项目 | 当前状态 |
|---|---|
| Human Review | **待评审** |
| CC 冻结 | **未冻结** |
| 编码/测试授权 | **本轮未授权**；须在批准的 CC 冻结版本中确认 |
| 本轮访问边界 | 文档起草；未编码、未运行 E2E、未访问 Ginlong/KR/生产 |
| 模板例外 | 沿用既有项目负责人批准的模板缺失流程例外；模板同步仍 BLOCKED |

## 附录 A — 变更决策

| ID | Draft 决定 | 依据 |
|---|---|---|
| CC-DEC-001 | CC-005 验收真实 UI/WMS 集成路径，但不重做 CC-001–004 的单元/组件矩阵 | Implementation Plan v1.6 阶段 4 |
| CC-DEC-002 | 使用模拟 KR 执行数据经现有 Odoo WMS 流程处理；Gateway 测试可选，模拟结果不冒充真实联调 | Human Review 对 CC-GIN-005 的范围意见 |
| CC-DEC-003 | API09 按 owner/warehouse 实际编码字段精确匹配并执行 2×2 隔离矩阵；历史基线差异留 Human Review 决定 | TDD v0.9、CC-GIN-004 v1.1 与原 Frozen v1.0/v1.6 差异 |
| CC-DEC-004 | Codex 先执行浏览器模拟用户流程并形成 HVR 证据，业务负责人之后完成最终人工验收 | Human Review 对验收顺序的明确要求 |

## 附录 B — 版本记录

| 版本 | 日期 | 状态 | 说明 |
|---|---|---|---|
| v0.1 | 2026-11-18 | Draft | 初稿；原件保留。 |
| v0.2 | 2026-11-19 | Draft | 按 Human Review 调整为 Ginlong API/Odoo WMS 本地集成；加入 API01/03 owner 与事务验收、API09 双 owner×双仓编码隔离、Codex 浏览器模拟 HVR 与最终业务负责人验收；Gateway 测试改为可选；列出冻结基线差异；未修改上游、未编码、未测试、未冻结。 |
