# CC-GIN-012 v0.1 Draft — Ginlong 项目级业务主链集成缺口修复

| 项目 | 内容 |
|---|---|
| 文档编号 | CC-GIN-012 |
| 状态 | **Draft；待 Human Review；未冻结、未授权实施** |
| 模块 | `ginlong_apis`；必要时扩展 `worlddepot` 现有业务能力 |
| 工作类型 | 集成缺陷修复、自动化组件集成验收 |
| 目标 | 以同一货主、仓库和产品为数据主线，验证 API01–API10 与现有 WMS 业务记录的连续集成；只修复经复现且违反当前冻结 SRS/TDD 的实现缺陷。 |
| 提出背景 | 项目级 HVR 已改为连续仓库业务链。单接口测试数据和独立测试结果不能证明同一入库、库存、出库及盘点业务链可贯通。 |
| 上游基线 | SRS v1.9 Frozen with Open Items；TDD v2.2 Frozen with Open Items；Implementation Plan v2.7 Frozen with Open Items。计划需先增加本 CC 的阶段映射并复核基线有效性，见 §2.4。 |
| 相关流程 | [项目级业务流程 HVR 指南](../ginlong_apis/hvr/HVR_Project_Business_Flow_Guide.md)；[CC-GIN-005 v1.1](CC-GIN-005-v1.1.md) |
| 模板同步 | `BLOCKED`：项目既有批准例外继续适用；本稿不将模板检查状态伪记为 PASS。 |

---

## 0. 文档治理

本文件是拟议实施契约，不是已冻结的代码授权。CC-GIN-005 v1.1 仍是阶段 4 的现有契约；本稿不覆盖、改写或关闭它。只有 Human Review 批准、必要的 Implementation Plan 修订完成并将本 CC 冻结后，才可按冻结范围开始代码实施。

## 1. 变更概述

本次提出的是阶段 4 主链集成缺口修复 CC。先用共享数据集建立端到端自动化复现场景，再仅修复实际复现且违反 SRS/TDD 的代码缺陷。若现有代码已满足契约，对应代码不改；本稿不预设缺陷位置。

## 2. 上游基线与追溯

### 2.1 SRS

| SRS 条目 | 本 CC 用途 |
|---|---|
| FR-GIN-001 | API01 接收入库指令；订单接收不代表实际入库或库存变化。 |
| FR-GIN-002 | API02 从同一入库订单 `status` 回传收货确认，不依赖 Picking。 |
| FR-GIN-003 | API03 接收出库指令；复用已存在的 `owner + productCode` 产品，不创建 Picking、预留或库存。 |
| FR-GIN-004 | API04 只从该入库订单关联的 Done/Incoming `stock.picking` 与实际作业行回传。 |
| FR-GIN-005 | API05 保存客户盘点指令，不记库存。 |
| FR-GIN-006 | API06 从现有实际备货记录生成备货完成 Payload，不表示实际发货完成。 |
| FR-GIN-007 | API07 建立同一货主及产品编码对应的产品变体，遵循已批准产品共享属性及 SN 规则。 |
| FR-GIN-008 | API08 从已保存的实际发货明细及其实际 Picking 作业行生成结果，不重复扣减库存。 |
| FR-GIN-009 | API09 只读返回同一 owner/warehouse 下的实际物理库存量，不扣预留量。 |
| FR-GIN-010 | API10 只从客户盘点单关联的已保存仓库实盘结果回传，不读取计划数据或 `stock.quant`。 |
| SRS §6.1 业务规则 | 复用适用于上述接口的已冻结规则；以 SRS v1.9 原文为准，不在 CC 中重述或扩张业务语义。 |

### 2.2 TDD

| TDD 条目 | 本 CC 用途 |
|---|---|
| §1 | 三系统职责及业务指令、实际作业、Odoo 库存记录分离。 |
| §2–5 | 持久化业务数据、接口来源、Payload 读取及现有 WMS 服务复用。 |
| §7.1、§7.4 | API09 `stock.quant.quantity` 只读来源、货主/仓库过滤和查询验收。 |
| §13 | API02 状态回传及 API04 每个 Done/Incoming Picking 的实际数据来源。 |
| §14–16 | 现有重复回传处理和入站通用组件；本 CC 不重做其独立组件验收。 |

### 2.3 Implementation Plan 影响

Implementation Plan v2.7 当前仍将 CC-GIN-005 v1.1 作为“API01–10 本地集成与完整 WMS E2E”阶段 4 的在途契约，并将 CC-GIN-006 保留为真实 Ginlong 联调阶段。拟议 CC-GIN-012 是阶段 4 的有界增补，不替代阶段 4，也不改变阶段 5。

在冻结本 CC 前，须修订并批准新的 Implementation Plan 版本：仅增加 CC-GIN-012 的目的、范围、依赖和 Done Gate 映射，明确 CC-GIN-005 与 CC-GIN-012 的不重复边界，并重新评估 `Baseline validity`。本稿不得被视作已批准的计划修订或基线。

### 2.4 DDD 与模板状态

- 本 CC 不新增 DDD 概念或领域不变量；DDD：N/A（当前 SRS/TDD 未要求独立 DDD 基线）。
- CC 模板同步脚本本轮返回 `BLOCKED`（仓库中无可核对的项目模板来源）；项目计划已记录并批准沿用模板同步例外。此项不表示模板同步 PASS。

## 3. 范围冻结

### 3.1 在范围内

1. 建立一个可重复的项目级自动化/组件集成场景：相同 API User 所属项目、同一 owner、同一 Odoo 仓库 `KRWH`、同一 Ginlong 产品编码及其同一 `product.product` 变体贯穿入库、库存、出库和盘点链。
2. 通过真实 Ginlong HTTP 入口调用入站 API01、API03、API05、API07、API09；通过 Odoo 真实业务按钮及本地 Mock HTTP 接收端验证出站 API02、API04、API06、API08、API10。
3. 使用 Odoo 标准/WMS 业务流程创建并完成 Incoming、Outgoing `stock.picking`，并由该流程产生真实 move line、SN/Lot、package/pallet 和库存变化。测试不直接创建或修改 `stock.quant`。
4. 验证 API01/API03/API05 只产生各自业务指令，不伪造实际 WMS 作业；验证回传/查询 API 不替代业务作业或改变库存。
5. 修复自动化主链复现出的、可明确追溯至 SRS v1.9 与 TDD v2.2 的最小代码缺陷；修复范围限于本项目 `ginlong_apis`，或为满足已冻结数据来源确有必要的 `worlddepot` 现有模型/视图/方法。
6. 保留并执行本 CC 必需的 API 入口、ORM 持久化、标准 Picking 过账、HTTP Mock、Event/Log 与库存结果断言；更新本 CC 对应 IHR、ATR，记录每个实际运行及代码版本。

### 3.2 范围外

- 真实 Ginlong、生产环境、真实 Karl Rapp 或 `karlrapp_gateway` / XML / VPN / FTP 联调。
- 新增订单、库存、SN、托盘、盘点或通用集成平台模型；直接写入 `stock.quant`；绕过 Odoo 标准 Picking 过账。
- 新增预留、Reserve、Picking 预分配、自动拣货或新的仓库业务状态/审批门禁。
- 修改 Ginlong 协议、现有 API 字段、Action、业务键、库存口径、已批准状态语义或回传事件粒度。
- 重做 CC-GIN-001–011 已通过的通用组件测试；仅运行由本 CC 变更影响的必要回归。
- 把模拟/本地 Mock 结果描述为真实 Ginlong 或 KR 集成通过；代填业务人员人工 HVR 结果。
- 删除、取消、重置已有业务数据、API Log、Event 或幂等记录；清理现有工作区修改或提交 Git。

### 3.3 非目标

本 CC 不以“所有接口独立返回成功”作为项目主链通过。目标是证明每个阶段读写的是同一业务链真实产生的数据，并且库存变化只由实际完成的标准 Picking 引起。

## 4. 允许修改边界

| 类型 | 允许范围 |
|---|---|
| 集成模块 | `mymodules/ginlong_apis/**` 中为修复经复现的冻结契约偏差所必需的代码、视图和测试。 |
| 现有 WMS 模块 | `mymodules/worlddepot/**` 中直接提供 SRS/TDD 指定业务记录来源所必需的最小变更及回归测试；修改前核对依赖和调用，不改无关 WMS 功能。 |
| 测试 | `ginlong_apis` / `worlddepot` 相关自动化测试、测试夹具及本 CC 的 IHR/ATR。 |
| 不允许 | Odoo 官方源码、`stock_barcode`、其他客户接口、`karlrapp_gateway`、无关模块及冻结上游基线。 |

若复现证明缺口源于 SRS/TDD 未定义或相互冲突，必须停止受影响实现并提交上游文档修订，不得在本 CC 临时决定业务含义。

## 5. 必需行为与数据链

### 5.1 CC-CHANGE 范围登记

| CC-CHANGE ID | 本次工作 | 验收追溯 |
|---|---|---|
| CC-CHANGE-001 | 建立隔离的自动化主链夹具，使同一 owner、warehouse、Ginlong productCode、产品变体及测试项目贯穿 API01–API10。 | CC-TEST-140/141/157 |
| CC-CHANGE-002 | 验证并修复入库指令、收货状态、实际 Incoming Picking、API04 实绩及 API09 入库后数量之间违反冻结来源/行为的缺口。 | CC-TEST-142–147 |
| CC-CHANGE-003 | 验证并修复出库指令、实际备货、API06、实际 Outgoing Picking、API08 与库存结果之间违反冻结来源/行为的缺口。 | CC-TEST-148–152/157 |
| CC-CHANGE-004 | 验证并修复 API09 实际数量查询及 API05 指令—实盘结果—API10 回传的来源/副作用缺口。 | CC-TEST-153–156 |
| CC-CHANGE-005 | 仅修复上述测试实际复现且可追溯到冻结 SRS/TDD 的代码缺陷，不扩大契约。 | 对应失败测试及必要回归 |

### 5.2 主线节点及断言

| 主线节点 | 期望行为及必须断言 | CC-CHANGE |
|---|---|---|
| API07 → API01 | API07 建立的同一 owner 产品变体供 API01 后续订单引用；API01 仅建立预报订单，不创建 Picking、Lot、Package、Move 或库存。 | CC-CHANGE-001/002 |
| API01 → API02 | API02 从同一 `inbound.order.status` 回传 N/Y；状态确认本身不改变库存，不依赖 Picking 或 move line。 | CC-CHANGE-002 |
| WMS 入库 → API04 → API09 | 通过标准 Incoming Picking 实际录入该变体、SN、托盘并过账；API04 从当前订单关联 Done/Incoming Picking 读取作业实绩；API09 同 owner/仓库查询物理数量。回传或查询本身不产生库存移动。 | CC-CHANGE-002/004 |
| API03 → WMS 备货 | API03 以同一 owner、同一 Ginlong `productCode` 和同一已存在变体创建出库指令；只产生订单，不创建 Picking、预留或库存变化。标准 WMS 实际备货使用此前入库形成的库存及 SN。 | CC-CHANGE-003 |
| API06 → 实际出库 → API08 → API09 | API06 从已保存实际备货记录生成备货结果；标准 Outgoing Picking 完成后，API08 从已保存的实际发货明细/实际 move line 关联生成结果；API09 反映 Picking 造成的库存变化。备货回传不等于发货，API08 不再次扣库存。 | CC-CHANGE-003/004 |
| API05 → 实盘 → API10 | API05 对同 owner/产品的客户盘点指令不记库存；验收人通过现有盘点流程保存真实实盘结果；API10 只从已保存实盘结果读取，不用订单计划或 `stock.quant` 反推结果，不修改库存。 | CC-CHANGE-004 |

实际数量由标准业务操作形成；测试主链可沿用项目 HVR 指南中的逻辑数量变化（入库后 2、发货后 1），但自动化测试应使用隔离回滚的测试数据，不复用/清理人工 HVR 业务数据。主链 SKU、单号、SN 或包裹若冲突，测试夹具需使用隔离的唯一后缀，不修改人工 HVR 数据。

## 6. 既有行为保留

| ID | 行为 / 契约 | CC-PRESERVE ID |
|---|---|---|
| 1 | API01/03/05 入站接口的字段、校验、业务键、Action、生命周期及权限范围不变。 | CC-PRESERVE-001 |
| 2 | API01 的预报数据与实际 Picking/库存事实分离；非保税 snList 处理及保税 SN 规则不变。 | CC-PRESERVE-002 |
| 3 | API02 收货确认与 API04 实际入库完成分离；API06 备货与 API08 实际发货分离。 | CC-PRESERVE-003 |
| 4 | API09 依据 `owner + warehouse + productCode` 返回实际物理库存，只读且不扣预留量。 | CC-PRESERVE-004 |
| 5 | API05 客户盘点计划与实际盘点结果分离；API10 使用实际结果，不更新库存。 | CC-PRESERVE-005 |
| 6 | 复用现有认证、Error、限流、字段校验、幂等、API Event、API Log 及重复回传确认；外部契约/错误格式不得因主链测试改变。 | CC-PRESERVE-006 |

## 7. 技术约束

1. 仅依据当前有效冻结基线实现；TDD 未规定的技术方案或业务规则不在 CC 中新增。
2. 入站请求通过真实 HTTP 路由；出站回传必须点击真实 Odoo 按钮并观察本地 Mock 收到的 HTTP 请求，不能直接调用 Payload builder 代替端到端断言。
3. 自动化库存数据仅通过现有 WMS/标准 Picking 的业务方法生成；禁止 SQL、直接改 `stock.quant`、人工创建库存量或在测试外保留模拟库存。
4. 统一使用项目级主线同一逻辑 owner/仓库/产品身份。API User 的项目归属及权限照既有配置执行，不通过切换用户绕过访问范围。
5. 代码新增或修改须遵守仓库根目录 `AGENTS.md` 中文注释规范；公共方法、复杂业务处理需有中文 Docstring/注释。
6. 自动化通过不等于人工项目 HVR 通过；项目级业务操作仍由业务负责人亲自验收并记录。


### 7.1 适用的 TDD 防护栏

TDD v2.2 没有为本项目主链约束分配独立 `T-xxx` 编号；以下直接引用其规范性章节，不另造 TDD ID。

| TDD 条款 | 适用性 | 本 CC 落实位置 | 验证方式 |
|---|---|---|---|
| §1 系统职责及实际作业数据边界 | 适用 | §5、§6 | CC-TEST-143–156 |
| §2.1/§2.2 保存后 ORM 读取与既有模型复用 | 适用 | API 回传来源 | CC-TEST-144/146/150/152/155/156 |
| §3/§4 Payload 来源及 API04/10 实际数据 | 适用 | 入库、出库、盘点主链 | CC-TEST-146/150/152/155/156 |
| §7.2 API09 严格只读及物理数量 | 适用 | §5 的库存断言 | CC-TEST-142/147/153 |
| §13–§16 回传、幂等、错误和组件边界 | 适用 | 仅回归本 CC 影响 | 现有结果 + CC-TEST-157 |
## 8. 数据与迁移影响

| 项目 | 当前拟议 |
|---|---|
| 生产数据迁移 | 否；不访问生产环境。 |
| 开发库持久化测试数据 | 不新增清理/删除要求。自动化夹具应按现有测试框架事务回滚；人工 HVR 数据保持不变。 |
| 库存 | 仅由标准 Picking 工作流产生测试库存；不得创建/写入 `stock.quant`。 |
| 新业务模型 | 不允许；若冻结模型无法提供已批准数据来源，停止并提交上游修订，而非建立平行模型。 |

## 9. API / 集成影响

API01–API10 均纳入同一测试主链，但仅修复冻结基线已定义而当前实现不能满足的本地集成行为。所有出站请求走本地 Mock；任何真实 Ginlong 或生产 Endpoint 在实施和验收中均不得调用。

## 10. 安全 / 权限影响

- 复用现有 API User、Token、Odoo 用户权限和项目访问规则；不得记录/截图 Token、Secret、Cookie。
- Mock Endpoint 仅监听本地开发环境；实施前确认 Ginlong API Settings 不指向真实服务。
- 业务日志、API Event/API Log 保持现有权限边界；不得扩大跨项目数据可见性。

## 11. 测试契约

每个用例必须记录前置 ORM 状态、真实入口/动作、HTTP/按钮结果、ORM 业务变化及副作用断言。以下 CC-TEST ID 为本 Draft 提案，批准冻结后作为正式测试契约。

| 测试项 | 场景与必须断言 |
|---|---|
| CC-TEST-140 | 自动化测试隔离准备：同一个 owner、仓库、productCode、模板/变体和测试 Project/API User；测试前后不触碰人工 HVR 数据。 |
| CC-TEST-141 | API07 真实 HTTP 建立可供主链使用的成品变体；验证 owner+productCode 指向唯一产品，tracking 符合冻结产品规则。 |
| CC-TEST-142 | API09 入库前查询同一 owner/warehouse；目标产品库存为 0 或不存在，查询前后库存记录无变化。 |
| CC-TEST-143 | API01 经 HTTP Add；订单引用 API07 的相同变体；无 Picking/Move/Lot/Package/库存副作用。 |
| CC-TEST-144 | API02 对同一入库单状态规划态及收货确认态各使用真实订单按钮回传；分别检查 N/Y、业务操作日志和无库存变化。 |
| CC-TEST-145 | 标准 WMS Incoming Picking 真实完成两个不同 SN 的收货并关联实际托盘；检查 Done move line、lot/package 关系及物理数量 +2。 |
| CC-TEST-146 | API04 从上述订单关联的 Done/Incoming Picking 自动生成每 Picking 事件；Mock 收到实际产品、SN、数量、托盘、确认人/时间；API04 不改变库存。 |
| CC-TEST-147 | API09 经真实 HTTP 查询入库后实际库存；只返回同 owner/warehouse 的目标产品数量 2，查询保持只读。 |
| CC-TEST-148 | API03 经 HTTP 创建同 owner、同项目和同 productCode 的出库单；产品映射到 API07/API01 使用的变体；不建 Picking、不预留、不改变库存。 |
| CC-TEST-149 | 按既有 WMS 流程对该出库单执行备货，选取实际入库形成的一个 SN/托盘；检查保存的 picking/move line 作业数据。 |
| CC-TEST-150 | API06 真实按钮回传同一订单的已保存备货数据；Mock 请求、API Event/API Log 与实际作业数据一致；不代表发货完成。 |
| CC-TEST-151 | 完成标准 Outgoing Picking；只发出备货选中的 SN，另一 SN 仍在库；物理库存减少 1，出库动作不来自 API03/06/08。 |
| CC-TEST-152 | API08 真实按钮从已保存发货明细及实际 move line 关系回传；Mock Payload 对应真实 Done Picking；API08 不再次扣减库存。 |
| CC-TEST-153 | API09 经真实 HTTP 查询发货后库存为 1；owner、warehouse、productCode 匹配并保持只读。 |
| CC-TEST-154 | API05 经真实 HTTP 创建同 owner、同产品的客户盘点指令；请求不创建实盘结果、不改变库存。 |
| CC-TEST-155 | 通过现有盘点业务流程创建并保存实际盘点结果；结果关联 API05 指令及真实产品/SN/数量/托盘，不经计划 JSON 或 quant 推算。 |
| CC-TEST-156 | API10 真实业务按钮只将上述已保存实盘结果发送至 Mock；检查 API Log/Event、业务来源及库存无副作用。 |
| CC-TEST-157 | 主链完整回归：按顺序执行 140–156，汇总证明同一业务身份贯穿各 API；每个库存变化可归因于标准 Picking，盘点与回传不改库存；失败时保留原始失败状态并阻止依赖步骤冒充通过。 |

### 分层要求

- 组件层：只对本 CC 修改影响的业务路径补必要单元/模型测试。
- 组件集成层：真实 Odoo ORM、HTTP 路由、按钮方法、Mock 接收端及标准 Picking 事务协作。
- 本 CC 不把 HVR 执行记录、单纯静态 Payload 检查、直接调用内部方法或 Mock Picker 记录当作完整主链集成通过。
- 项目级人工 HVR 沿用 [HVR_Project_Business_Flow_Guide.md](../ginlong_apis/hvr/HVR_Project_Business_Flow_Guide.md)，由业务负责人执行；本 CC 不代填 PASS。

## 12. 停止条件 / 升级闸门

1. 若任何期望行为在 SRS v1.9 或 TDD v2.2 找不到依据，暂停受影响代码，提交需求/TDD 修订建议。
2. 若 CC-GIN-005 与本 CC 的测试/实施边界冲突，或 Implementation Plan v2.7 的阶段映射无法形成清晰边界，先修订并重新批准计划，不覆盖历史基线。
3. 若真实 WMS 业务方法、字段或当前业务数据无法提供 TDD 指定事实，不得从 API 计划数据、回传用户、`stock.quant` 或人工填充推导；记录 BLOCKED 和证据。
4. 若任一失败会影响后续链条，后续依赖场景标记 `BLOCKED`；不得将 Mock 成功或独立接口成功替代失败的业务前置步骤。
5. 任一测试触碰人工 HVR 单据/库存，或产生需要清理的非回滚业务数据时，停止并报告；未经授权不得删除、取消或重置。

## 13. 完成条件与交付

1. Implementation Plan 新版本已批准，CC-GIN-012 与 CC-GIN-005 阶段边界、依赖、基线有效性及追溯映射明确。
2. 按冻结后确认的 CC-TEST ID 完成适用自动化/组件集成验收；逐条记录 PASS/FAIL/BLOCKED/NOT RUN、执行命令、运行环境/模块版本、日志路径及 ORM/HTTP 断言证据。
3. 主链所有通过项均基于同 owner、仓库、productCode、产品变体和真实前序业务结果；不得使用手工库存补齐。
4. 明确保留并解释所有失败、阻塞或未运行项；若存在本 CC 强制门禁未满足，则保持 In Progress，不生成满足关闭条件的 FR。
5. 更新 IHR、ATR；完成后生成 FR 提交 Human Review。模板同步 BLOCKED 继续沿用批准例外，不记 PASS。
6. CC 关闭后，项目级真实人工 HVR 仍由业务负责人按项目指南执行。自动化/模拟证据不替代人工判定。


## 14. 追溯矩阵

| 上游来源 | CC-CHANGE | CC-TEST |
|---|---|---|
| SRS FR-GIN-001、FR-GIN-002、FR-GIN-004 | CC-CHANGE-001/002 | CC-TEST-140–147 |
| SRS FR-GIN-003、FR-GIN-006、FR-GIN-008 | CC-CHANGE-001/003 | CC-TEST-148–152 |
| SRS FR-GIN-009 | CC-CHANGE-004 | CC-TEST-142/147/153 |
| SRS FR-GIN-005、FR-GIN-010 | CC-CHANGE-004 | CC-TEST-154–157 |
| SRS FR-GIN-007 | CC-CHANGE-001 | CC-TEST-140/141/143/148/154 |
| TDD §1、§2、§3、§4、§7、§13–§16 | CC-CHANGE-001–005 | CC-TEST-140–157（按上表细化） |

## 附录 A — 变更决策（CC-DEC）

本 Draft 不提出新的业务或架构决策。CC-CHANGE-005 只允许修复可复现、可追溯到冻结基线的实现偏差；不能作为更改契约的授权。

## 附录 D — 版本历史

| 版本 | 日期 | 变更 | 状态 |
|---|---|---|---|
| v0.1 | 2026-11-25 | 根据项目级共享数据主链提出 API01–API10 的本地自动化/组件集成缺口修复契约；限定为冻结 SRS/TDD 的可复现偏差；要求先修订 Implementation Plan | Draft；待 Human Review |

## 当前评审状态

| 项目 | 状态 |
|---|---|
| Human Review | 待评审 |
| 代码修改授权 | 未授权；需冻结后依审批决定执行 |
| Implementation Plan 修订 | 冻结前置事项；本轮未修改 |
| 测试执行 | NOT RUN；本轮仅起草 CC |
| 外部联调 | 不在本 CC 授权范围 |
