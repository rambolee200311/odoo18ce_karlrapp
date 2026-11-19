# CC-GIN-005 v0.1 — 本地 UI/WMS 集成与端到端验收（Draft）

| 项目 | 内容 |
|---|---|
| CC ID / 版本 | CC-GIN-005 / v0.1 Draft |
| 状态 | **Draft；待 Human Review；未冻结；未授权编码或测试** |
| Intent ID | `GINLONG-LOCAL-UI-WMS-E2E-005` |
| 模块 | `ginlong_apis`、现有 `worlddepot` / Odoo WMS；按可用性验证 Odoo ↔ Karl Rapp Gateway 本地接口 |
| 目标 | 在本地 Odoo 开发环境中，以完整业务操作路径验证 Ginlong 指令、Odoo Order、仓库执行记录、用户手动回传及库存查询的端到端衔接，并完成人工浏览器 UI/WMS 验收。 |
| SRS 基线 | [SRS ginlong_apis v1.0 Frozen](../requirement/SRS_ginlong_apis.md) |
| TDD 基线 | [TDD v0.9 Frozen](../ginlong_apis/TDD-v0.9.md)；保留其引用的历史版本，不改写已关闭 CC 基线 |
| Implementation Plan | [v1.6 Frozen](IMPLEMENTATION_PLAN_ginlong_apis-v1.6.md)；阶段状态见 [v1.7](IMPLEMENTATION_PLAN_ginlong_apis-v1.7.md) |
| 前序 CC | CC-GIN-001、002、003、004 均 Closed；不重开其组件验收 |
| 后续阶段 | CC-GIN-006：真实 Ginlong 测试环境联调，须另行授权 |
| 项目模板同步 | **BLOCKED**：项目模板来源缺失；沿用既有批准例外，草案仅参考 skill 模板结构，不伪记同步通过 |
| 人工评审 | 待定；不得推定已批准 |

> 本草案依据 Implementation Plan 阶段 4 起草。它不修改 SRS、TDD、Plan 或 CC-GIN-001–004，不授权实施。仓库当前工作树中未发现 `karlrapp_gateway` 模块或其测试接口；因此草案将 Odoo 端流程与 KR Gateway 衔接分别记录，避免以人工/模拟执行数据冒充真实 Gateway 端到端通过。

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

本项目无独立 DDD 基线；本 CC 不创建领域模型或新的业务不变量。

API03 的方向按后续 Ginlong 接口矩阵和 TDD v0.9 记录为 Ginlong → Odoo；SRS 中较早的 A-003 仅是历史开发假设，不在本 CC 重开。

## 2. 范围

### 2.1 本 CC 范围内

1. 在既有 Odoo 开发环境执行本地端到端流程，覆盖 Ginlong API01/03/05/07 入站、现有 WMS 订单处理、实际执行结果记录、五个手动回传接口及 API09 查询之间的连接。
2. 使用本地 Odoo HTTP 测试客户端/测试调用验证 Ginlong 入站接口；出站回传使用 Mock HTTP。不得调用 Ginlong 测试或正式环境。
3. 使用浏览器执行并记录完整 Odoo 用户流程：业务单据查找、数据保存、重新打开、必要编辑、实际 WMS 操作记录、单据回传、日志定位和 API09 查询。
4. 验证五个回传按钮均位于既有业务 Order；继续使用持久化 Form/Notebook，不使用 TransientModel Wizard、不向业务用户展示 JSON 编辑器。
5. 验证 API04/06 来自实际 `stock.picking` / `stock.move.line`；API10 来自 `worlddepot` 客户盘点订单关联的实盘结果；API02/08 使用现有 Order 业务状态。
6. 验证 WMS 原生出入库库存变动只由现有 Odoo WMS 流程处理，并由实际仓库执行数据触发；API01/03 收到 Ginlong 指令本身不构成实际执行或库存变化。
7. 在批准的本地测试数据条件下验证 API09 返回 Odoo 已记录的实际物理库存，按货主、仓库和产品区分，且查询不修改库存。
8. 执行本 CC 触及的必要 WMS 集成回归；沿用 CC-001–004 的既有测试证据，不为满足“完整”而无差别重跑已通过的组件套件。
9. 对集成缺陷进行最小修复仅在本 CC 获批后授权范围内；如需改变业务语义、外部契约、数据权威关系、WMS 核心行为或 TDD 设计，先停止并提交相应上游变更。

### 2.2 范围外

- 真实 Ginlong HTTP、Ginlong 测试/生产环境、生产数据库或真实凭据访问；属于 CC-GIN-006，须单独授权。
- 连接真实 Karl Rapp WMS 的 VPN/FTP、现场作业及真实仓库验收；不在当前本地 Odoo E2E 授权范围内。
- 新建或重做 Karl Rapp Gateway、文件协议、XML Schema、库存同步机制；缺少 Gateway 代码或协议时不得在本 CC 自行补造。
- 重复开发订单、库存、盘点、托盘、产品或 API 日志模型；新增通用集成层、队列、自动回传、自动重试、监控平台、审批或业务状态机。
- 重新执行 CC-GIN-001–004 的单元/组件验收矩阵；仅在 E2E 失败定位或回归风险明确时运行对应最小测试。
- 实施新的货主解绑、托盘生命周期或其他未纳入已批准 TDD / 本 CC 的需求。
- 修改官方 Odoo `stock` 代码、使用 `stock_barcode`，或以直接写 `stock.quant` 的方式模拟实盘/出入库。

## 3. 数据与业务防护栏

| 数据/事件 | 验收依据 |
|---|---|
| API01 / API03 | 订单接收和既有 WMS 订单处理；不得把订单接收等同实际仓库执行。按既有 WMS 服务决定是否形成待执行作业记录，不因此确认完成或直接修改库存。API03 产品匹配使用 `owner + productCode`，不自动创建缺失产品。 |
| API05 / API10 | 客户盘点指令与仓库实盘结果分别核对。API10 只从已保存、与客户盘点订单相关联的实际盘点结果取数；API05/10 不读写 `stock.quant`，不执行库存调整。 |
| API07 | 产品由 `owner + productCode` 识别；相同 `productCode` 可属于不同货主，端到端过程不得串货主。 |
| API02 / API08 | 使用对应 `worlddepot` Order 上已有业务状态/持久化明细；混合 Y/N 状态继续按已批准行为阻止发送，不增加新的状态或审批规则。取消控制和取消回传若仍未获确认，不纳入 E2E 断言。 |
| API04 / API06 | 只读取实际 picking/move line。API06 必须验证备货完成事件与实际备货数据，不以 picking 创建或库存过账替代备货完成。逐行 SN、产品、数量、托盘及人员/时间使用 TDD 已定数据来源。 |
| API09 | 只读 Odoo 当前实际物理库存；按 `owner + warehouse + productCode` 隔离，不扣预留量、不因查询创建或修改 quant/move/picking。未知 owner/warehouse 不得返回其他主体的库存。 |
| 人工回传 | 用户在已保存的业务数据上手动点击对应 Order 按钮。HTTP 请求同步 POST、`application/json`，使用配置的 Endpoint 和 Mock 服务；每次尝试独立追加现有 API 日志，不覆盖历史日志。 |
| Order 与 `stock.picking` | 两者业务职责独立，不增加强制关联；允许按已批准业务标识及实际明细核对。多张 picking/分批语义仍遵从已确认契约，未确认场景隔离，不猜测。 |

## 4. 变更边界

### 4.1 获批后可涉及的范围

| 区域 | 允许范围 |
|---|---|
| `mymodules/ginlong_apis/**` | 本地 E2E 必需的既有 API/Form/日志路径最小修复、测试和测试数据辅助；不建立新框架或平行模型 |
| `mymodules/worlddepot/**` | 仅在 E2E 证明本项目既有 WMS 集成路径有缺陷且可追溯到已批准 SRS/TDD 时作最小修复，并增加现有 WMS 回归；不作无关重构 |
| 自动化/人工验证文档 | 本 CC 专属自动化结果追加 ATR；浏览器人工验证追加 HVR；实施历史追加 IHR；关闭评估另行形成 FR |
| Gateway 边界 | 仅在 Gateway 项目/测试接口可用时进行接口级集成验证；本 CC 不授权改造或创建 Gateway 模块 |

具体代码文件和方法必须在冻结版本中根据发现的实际缺陷进一步限定。本 Draft 不授权更改代码、模块、数据库或环境。

### 4.2 禁止

- 使用直接 PostgreSQL/SQL、`psql`、`psycopg2` 或绕过 Odoo ORM；所有数据库检查、数据准备和清理仅经 Odoo ORM。
- 新建隔离数据库、虚拟环境，或替换项目既有 `venv`、`odoo.conf`、`odooce_karlrapp`。
- 安装、启用、调用或新增 `stock_barcode`。
- 直接增删改 `stock.quant`、直接伪造已过账 Picking，或让 Ginlong 请求本身产生库存调整。
- 访问真实 Ginlong/生产环境；把 Mock/模拟记录的结果写成外部联调或真实 KR 同步通过。
- 破坏或清理现有用户数据、既有工作区修改、历史日志或历史测试失败记录。

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
| Gateway | 当前仓库搜索未发现 `karlrapp_gateway` 模块。开始 Gateway 路径测试前须定位独立项目/可用测试服务，并获得其接口、文件约定及本地安全测试方式；缺失时对应验收项保持 BLOCKED。 |
| 外部协议 Open Items | 继续沿用 CC-GIN-003/TDD 按接口管理的 Open Items。只运行有已确认契约和已保存数据来源的本地场景；未确认部分逐项 BLOCKED/NOT RUN，不阻塞不依赖它们的场景。 |
| 文档模板 | 当前模板来源检查 BLOCKED；沿用已批准流程例外。草案需 Human Review；后续不得将模板同步写为 PASS。 |

## 6. 测试契约

下表为拟议 CC-TEST 编号。起草时所有项目均为 **NOT RUN**；此表不是测试结果或授权。

| 测试 ID | 集成场景 | 预期结果 / 证据 |
|---|---|---|
| CC-TEST-044 | 环境与路由准备 | 确认使用既有配置/数据库、Ginlong 与 WorldDepot 模块版本、测试用户角色、Mock Endpoint；确认测试数据来源及清理边界。不满足前置条件时停止并记录 BLOCKED。 |
| CC-TEST-045 | API07 产品主数据到后续订单的端到端使用 | 通过本地入站路径维护产品；不同货主可有相同 `productCode`；后续订单查找只关联对应 `owner + productCode`，缺失产品不得被静默创建（API03 规则）。保存/重新打开记录可追溯。 |
| CC-TEST-046 | API01 入库指令到现有 WMS Order | 本地请求经既有认证/日志处理后创建或处理正确入库 Order；订单字段/明细可从 UI 查阅；仅有指令时不确认实际收货、不造成已完成库存移动。实际待执行 Picking 行为遵从当前 WMS 逻辑。 |
| CC-TEST-047 | API03 出库指令到现有 WMS Order | 本地请求按货主和产品编码关联正确出库 Order；相同产品编码跨货主不串货；缺失组合按已批准拒绝行为记录错误；接收指令不表示备货/发货完成，不产生实际库存变动。 |
| CC-TEST-048 | 入库实际执行、Order 状态和 API02/API04 回传 | 从可用的 KR 结果输入路径形成实际收货业务记录和已处理 Picking；原生 WMS 处理按实际结果记账。API02 从已保存入库 Order 收货明细/状态取数，API04 从已选实际 Picking/move line 取数；分别由用户点击、Mock 接收并追加各自日志。不可用 KR 结果输入路径时，只能报告 Odoo 端片段测试，不得报告 Gateway E2E PASS。 |
| CC-TEST-049 | 出库备货、发货和 API06/API08 回传 | 从已处理出库 Order 和实际执行记录区分备货与发货事件；API06 使用实际备货明细、托盘和已保存重量字段，不能以 Picking 创建/过账替代备货完成；API08 按 Order 发货状态取数。两接口独立手动回传至 Mock，结果和日志可定位原单。 |
| CC-TEST-050 | API05 盘点指令与 API10 实盘回传 | API05 客户盘点订单与实盘结果保持独立；用户在 UI 保存/重开实盘结果后，API10 只发送该订单下选中的实际结果。不得读取计划值或 `stock.quant` 推算结果，不做库存调整；Mock 日志关联客户盘点订单。 |
| CC-TEST-051 | API09 与 WMS 库存变更衔接 | 经合法 WMS 出入库处理后，API09 读取 Odoo 当前物理数量并按 owner/warehouse/product 分隔；查询前后 `stock.quant`、move 和 picking 快照不变。真实 KR 同步未验证时注明测试数据是本地/模拟来源。 |
| CC-TEST-052 | 五个回传接口的完整 UI 操作 | 逐项打开既有 Order Form/Notebook，检查订单号、业务事件、关联实际作业/实盘和关键字段；保存后关闭并重新打开；由 Order 上的按钮使用 ORM 已保存值发送。无 Wizard、JSON 编辑器或未保存前端值依赖。 |
| CC-TEST-053 | 人工回传失败、修正、重发和日志追溯 | Mock 首次返回失败；用户保存修正并再次点击；第二次从 ORM 读取新值并新增日志，旧日志请求/响应不变；日志可定位源单。无后台自动重试。 |
| CC-TEST-054 | 多角色菜单、权限及单据定位 | 按批准用户角色完成从 Ginlong 菜单/业务列表进入原单、查看日志和返回原单操作；未授权角色按现有 ACL 被限制；既有 WMS 菜单、API User/Token 及日志行为未退化。 |
| CC-TEST-055 | 受影响 WMS 回归 | 通过现有 WMS 入库、出库、实际 Picking/Move Line 及库存原生流程；盘点指令和实盘结果独立；产品跨货主同码不串货；本项目 UI/日志变更不破坏已有 WMS 功能。限定为与 E2E 触及路径相关的自动化回归，不重复无关套件。 |
| CC-TEST-056 | 本地 Odoo ↔ Karl Rapp Gateway 结果交接（前置项） | 仅在 Gateway 项目/服务、文件约定及测试入口定位后执行：确认一次本地测试执行结果经现有交接路径进入 Odoo，并能形成正确 Picking/Move Line。当前 Gateway 未在本仓库发现；本项暂为 **BLOCKED / 未运行**，不得用手工创建 Picking 或 Mock 订单冒充该路径通过。 |

### 6.1 验收证据

- 自动化与 ORM 集成结果记录在 ATR；浏览器人工流程逐步记录在 HVR；实现/配置变更记录在 IHR。每条测试注明环境、模块/代码版本、输入数据类型（真实 Odoo 业务数据或模拟数据）、操作路径、结果及证据位置。
- 人工 UI/WMS E2E 至少由业务用户在实际 Odoo 浏览器界面完成；截图或录屏不得包含凭据。自动化浏览器脚本不能替代要求的人工流程验收。
- 本地 Ginlong 请求和 Mock 回传仅证明本地契约路径，不证明真实 Ginlong 可用。
- 若 CC-TEST-056 因 Gateway 不可用仍 BLOCKED，则三系统完整 E2E 未完成；不得以 Odoo 两端测试代替。是否允许将其拆分或改变边界须由项目负责人评审。
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
| OI-GIN-005-01 | `karlrapp_gateway` 代码与本地测试入口未定位 | 当前仓库 `mymodules`/全仓文件清单中未发现该模块；Plan 阶段 4 要求本地集成，但无法凭空定义文件传输和结果交接 | 冻结/执行前需定位 Gateway 项目及现有本地测试接口；在此之前 CC-TEST-056 BLOCKED，不能宣称三系统 E2E 完成 |
| OI-GIN-005-02 | VPN/FTP/XML 具体配置与测试数据 | 当前本地仓库未提供真实 KR 通信和协议环境；真实接入另受 CC-006/单独授权约束 | CC-005 只可使用已批准本地 Gateway 测试接口/夹具；不定义或开发外部协议 |
| OI-GIN-005-03 | 既有 Ginlong 外部语义 Open Items | CC-GIN-003/TDD 中保留 API02/04/06/08/10 的字段或分批/撤回相关 Open Items；只影响直接依赖场景 | 按接口/场景隔离。已确定正常路径继续验证；未确认场景 BLOCKED/NOT RUN，不猜测、不拖累无依赖场景 |
| OI-GIN-005-04 | 开发库真实 KR 库存链路未验证 | CC-GIN-004 使用模拟 ORM 库存验证 API09，只证明查询组件 | 若没有实际 Gateway/作业数据，API09 仅报告对已存在 Odoo 库存记录的本地验证；真实同步留后续环境验收 |
| OI-GIN-005-05 | 安全测试数据隔离 | 复用开发数据库，用户要求不新建隔离数据库 | 开始人工 WMS E2E 前记录专用可识别数据和 ORM 清理计划；若无法证明不影响既有业务数据，相关场景停止并升级 |
| OI-GIN-005-06 | 模板同步 | 项目模板源缺失；检查结果 BLOCKED | 沿用已批准流程例外；保持 BLOCKED，不作为 PASS，也不妨碍本 Draft 评审 |

## 9. 停止条件与升级

1. 任何测试要求修改 SRS 业务行为、Ginlong 外部协议、TDD 数据来源、WMS 状态语义或 API 幂等/事务/限流机制时，停止该场景并先修订相应上游文档；不得在 E2E 中临时补规则。
2. 若实际 Gateway 项目不存在、接口/文件格式不明、或不能安全连接本地测试入口，停止 Gateway 段验收，记录 `BLOCKED`，不以手工 Picking、Mock 数据或 Odoo 单边流程替代。
3. 若测试需要访问真实 Ginlong、生产环境、真实 KR VPN/FTP 或真实库存数据，停止并等待相应授权和环境确认。
4. 若因现有 WMS 业务流程需要直接 SQL、`stock_barcode`、库存模型绕行或扩大 `worlddepot` 改动，停止并提交范围/设计修订。
5. 某一接口 Open Item 仅阻断直接依赖场景；不能因此省略已确认字段或将其他已具备场景整体标为通过。

## 10. Done Gate（拟议）

CC-GIN-005 只有在 Human Review 批准本 Draft 并另行授权实施后，才进入执行。建议关闭需满足：

1. 本 CC 范围内的 UI/WMS 端到端场景均有 ATR/HVR 证据；PASS、PARTIAL、FAIL、BLOCKED、NOT RUN 如实记录。
2. 所有五个人工回传接口均经 Odoo Form 保存、重开、用户点击、Mock 接收和日志追溯；未使用 Wizard/JSON 编辑器。
3. 所有实际出入库均通过现有 WMS 正常业务路径处理；API05/API10 未改变库存；API09 为只读。
4. 受影响 WMS 回归通过，且未破坏 CC-GIN-001–004 已有行为。
5. 浏览器人工流程 HVR 完成；真实 Ginlong 和生产访问仍未执行且未伪记 PASS。
6. 如范围包括完整 Odoo↔KR Gateway 交接，CC-TEST-056 必须 PASS；若仍 BLOCKED，CC-005 不得宣称完成本地三系统端到端验收，须由 Human Review 决定后续边界。
7. 更新 IHR、ATR、HVR 和 FR，提交 Human Review；不得在本 Draft 预填任何测试 PASS 或关闭结果。

## 11. 追溯矩阵

| 上游 | CC 范围/测试 | 追溯关系 |
|---|---|---|
| SRS FR-GIN-001/003/005/007 | CC-CHANGE-001；CC-TEST-045–047 | 入站指令/产品数据与现有 Odoo Order/WMS 连接 |
| SRS FR-GIN-002/004/006/008/010 | CC-CHANGE-002；CC-TEST-048–050、052–053 | 实际执行/实盘来源、人工回传及日志 |
| SRS FR-GIN-009 | CC-CHANGE-003；CC-TEST-051 | 实际物理库存查询与无副作用 |
| TDD v0.9 §§1–5 | CC-PRESERVE-001–005；CC-TEST-045–053 | 三系统职责、持久化 Form、回传来源、同步调用及日志 |
| TDD v0.9 §7 / CC-GIN-004 | CC-CHANGE-003/004；CC-TEST-051、054 | API09、菜单/日志与失败单据定位在完整用户流程中的行为 |
| Plan v1.6 阶段 4、Plan v1.7 阶段 4 | 全部本 CC | 本地完整 UI/WMS 集成及浏览器人工 E2E |

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
| CC-DEC-002 | 测试报告必须把 Odoo 本地流程、KR Gateway 交接和真实外部联调分开；模拟数据不能代替 Gateway 或真实库存同步证据 | 项目认知与 Plan v1.7 已记录的边界 |
| CC-DEC-003 | Gateway 不在当前仓库可见时将 Gateway E2E 独立标 BLOCKED，不据此伪造完成 | 当前工作树源码盘点；具体接入范围由 Human Review 决定 |

## 附录 B — 版本记录

| 版本 | 日期 | 状态 | 说明 |
|---|---|---|---|
| v0.1 | 2026-11-18 | Draft | 按 Plan 阶段 4 起草本地 UI/WMS 集成与端到端验收；记录 Gateway 代码/测试入口未定位这一阻塞项；不修改上游文档，不授权编码或测试。 |
