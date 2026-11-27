# Ginlong 一步入库、一步出库基线符合性审查

**状态：** Human Review Draft（待评审；未冻结、未实施）  
**日期：** 2026-11-26  
**审查范围：** SRS、TDD、Implementation Plan、WorldDepot / Ginlong 代码、KRWH 仓库配置、自动化测试、HVR 指南与实际模拟记录。

## 1. 评审结论

将“一步入库、一步出库”作为 Ginlong–Karl Rapp 项目的强制业务与技术基线后，当前代码和验收材料**尚不符合出库基线**；入库仓库路线本身符合一步入库，但 API04、测试和 HVR 仍允许多张入库 Picking，需收敛到单张实际 Incoming Picking。

本报告只提出最小纠正方案，不修改代码、仓库配置、冻结基线或既有历史记录。现有正确的接口协议、认证、幂等、日志及其他通用组件验收证据继续有效，不需要重做。

## 2. 本次采用的一步业务基线

1. 一张入库订单通过一张 Incoming `stock.picking` 完成实际入库；只有该 Picking 完成时发生入库库存移动。API01 创建订单指令，API02 只改变收货业务状态并回传，API04 读取该张已完成 Picking 并回传实际结果。
2. 一张出库订单通过一张 Outgoing `stock.picking` 完成备货/实际出库；这张 Picking 只产生一次库存移动。Picking 完成后回传 API06。
3. 实际离仓是出库订单上的业务状态操作：只改变订单状态、记录操作日志并回传 API08，不创建第二张 Picking、不创建 move、不再次改变库存。
4. API03 仅创建出库业务指令，不创建或预留 Picking；API05/07/09/10 及其他回传动作不得代替实际收发货 Picking 或造成库存移动。

## 3. 逐项审查结果

| 范围 | 现状与证据 | 判定 | 最小纠正方案 |
|---|---|---|---|
| SRS | 当前基线为 `SRS_ginlong_apis-v1.9.md`。已区分备货与实际发货、订单指令与实际库存作业，但没有明确“一张订单只允许一张入库/出库 Picking”，也未明确 API06 前 Picking 已完成、API08 是纯订单状态操作且不产生第二次库存移动。 | 基线不完整，旧描述可被解释为两段出库 | 新增版本化 SRS 修订，明确上述四条基线、库存移动时点及禁止的第二 Picking；保留 v1.9，不覆盖历史。 |
| TDD | 当前技术基线 `TDD-v2.2.md` 描述 API06 读取所选作业 Picking、API08 读取发货明细；未将单一 Outgoing Picking 设为唯一实绩来源，也未定义订单级实际离仓动作不建 Picking/Move。 | 设计与新基线不一致 | 增量修订 TDD：API06 读取同一张已完成 Outgoing Picking；API08 读取出库订单状态并发送；停止以重复维护的发货明细作为 API08 状态来源。 |
| Implementation Plan | `IMPLEMENTATION_PLAN_ginlong_apis-v2.9.md` 引用当前主链 HVR 指南，但未声明一步路线约束。 | 缺少部署及验收门槛 | 新增版本修订，列出迁移/升级前配置核对、订单单 Picking 防重、测试与 HVR 更新；不修改旧计划。 |
| KRWH 仓库配置 | 只读 ORM 核查 `odooce_karlrapp`：KRWH `reception_steps=one_step`、`delivery_steps=ship_only`；接收和发货路线分别使用 Vendors→Stock、Stock→Customers。 | 符合一步路线；不需要改全局仓库配置 | 保持 KRWH Route 不变。Ginlong 项目应明确使用该仓库已有 Incoming、Outgoing operation type。 |
| 项目 Picking 类型配置 | `wd_project_profile` 的 `outbound_pick_type` 允许 `outgoing` 或 `internal`；检查的项目 236 未设置 `outbound_pick_type`。API03 服务只在项目值存在时复制到出库订单。 | 允许选择违背基线的内部 Picking，且空值无明确一步出库默认值 | 对 Ginlong 项目配置限定为 KRWH 的 `outgoing` 类型；如果字段为空，阻止创建/执行，或按 Human Review 批准的 Ginlong 默认策略解析为 KRWH `out_type_id`。不要改变其他项目/客户的配置。 |
| 出库单 Picking 类型 | `worlddepot/models/outbound_order.py` 的 `pick_type` 域只允许 `code='internal'`，与 KRWH 一步 Outgoing 路线冲突。 | 直接代码冲突 | 仅对 Ginlong 项目放行并使用 KRWH Outgoing operation type；保留其他客户原有内部拣货流程。 |
| 出库 Picking 创建与防重 | `action_create_picking_PICK` 按“订单 + 当前 pick_type”检查既有 Picking。若先有 Internal、再改成 Outgoing，代码可能再建另一张；并无跨类型的单 Picking 约束。 | 不满足“一张订单一张 Picking” | Ginlong 订单在任何类型下只允许一个非取消库存 Picking；创建前按订单检查所有 Picking，并在创建路径防并发重复。非 Ginlong 业务保持原逻辑。 |
| 完成 Picking 后的订单状态 | `my_stock.py` 对非 outgoing Picking 设置 `status=picking`；Outgoing 更新 `status=outbound` 的逻辑则只查找其 `origin` 指向的 Internal Picking。`cron_update_outbound_date` 也实现了 Internal→Outgoing 两张 Picking 关系。 | 当前是两步出库的状态联动 | 为 Ginlong 直接 Outgoing Picking 建立最小联动：Done 时一次性记录备货/出库完成状态和时间；不再查找/创建内部来源 Picking。保持其他客户的两步状态逻辑。 |
| API06 | `ginlong_callbacks.py` 从被勾选的 Picking 取 move lines，允许多条/多张选择；当前构造器没有将来源限定为该订单唯一的 Done/Outgoing Picking。 | 来源范围比一步基线宽 | 只从该订单唯一已完成的 Outgoing Picking 读取数据；API06 在此 Picking 完成后触发。接口 Payload、协议和通用回传机制不变。 |
| API08 | 当前 `_api08_payload` 从 `ginlong.outbound.shipment.detail` 多行 Y/N 折叠生成订单级状态；页面有明细维护区域，没有批准的一步订单级“实际离仓”操作。 | 依赖重复录入，未实现新基线 | 在出库订单上提供实际离仓状态按钮：变更业务状态、记录操作日志、发送 API08。Payload 从订单现有状态生成；该按钮不得调用 Picking/Move 或触发库存变更。先确认状态值映射与时间字段复用。 |
| 多 Picking 回传机制 | API04/API06 通用回传代码和自动化用例覆盖多个 Picking、混合成功/失败、选择范围。该通用能力本身不能证明本项目允许一张订单多张实际作业 Picking。 | 与项目“一张订单一张 Picking”验收口径冲突 | Ginlong 项目验收约束为每单一张 Picking；保留通用回传组件的既有通用能力测试，但 Ginlong API04/06 项目验收不得把多 Picking 作为业务要求。按影响范围调整具体接口测试，不撤销通用组件证据。 |
| 自动化业务主链 | `test_ginlong_api.py` CC-TEST-149～152 先创建 Outgoing Picking 并仅预留库存，在 Picking 未 Done 时发送 API06；之后 Done 才扣库存，再用额外 shipment detail 触发 API08。 | 顺序和 API08 数据来源不符合基线 | 更新测试契约：API03 后创建唯一 Outgoing Picking，完成一次并断言库存只减少一次；随后 API06 从该 Done Picking 回传；再点订单实际离仓按钮触发 API08，并断言 Picking/Move/quant 均不再变化。保留已有测试执行历史，新增修订记录，不回写旧 RUN 为 PASS。 |
| 入库自动化与 API04 | API04 测试覆盖多张 Done/Incoming Picking 及逐 Picking Event；主链使用一张 Incoming Picking。 | 主链符合；多 Picking 项目语义超出一步基线 | 主链维持单张 Incoming Picking；接口组件原有能力测试可保留，但 Ginlong 业务验收只要求当前订单唯一 Done/Incoming Picking。若规范允许分批收货则需另行评审；当前基线不隐含分批。 |
| HVR 操作指南 | `HVR_Project_Business_Flow_Guide.md` 当前描述 API06 在 Picking Validate 前执行，之后再 Validate；API08 要求增加并保存 shipment detail。与新基线不符。 | HVR 步骤必须修订 | 更新指南为“完成唯一 Outgoing Picking → API06 → 出库订单实际离仓按钮/API08”，并要求核对 API08 前后库存与 Picking/Move 数量不变。 |
| HVR 历史结果 | `CC-GIN-005_Final_Simulation_HVR_Report.md` 记录 OUT-01 有 Done Internal Picking 1934 + Done Outgoing Picking 1935；本次 OUT-02（订单 1402）有 Done Internal Picking `KRWH/KRINT/00009`，API06 日志 9491 / Event 7969 成功。 | 这些是历史实际操作，不能作为新一步路线的 PASS；也不得删除/改写 | 原样保留历史证据，并追加“按后续批准的一步路线不构成路线验收证据”的更正注记。为后续 HVR 准备全新订单/数据；不得在 OUT-02 上补造第二张 Picking 来修正。 |

## 4. 两步设计的来源与责任说明

KRWH 运行配置不是两步设计来源：只读 ORM 显示仓库收货和发货路线均为一步。两步出库来自历史设计/实现兼容路径：项目允许 `internal`，`outbound.order.pick_type` 强制 internal，状态联动和定时任务按 Internal→Outgoing 两张 Picking 编写，旧 HVR 指南与 OUT-01 历史记录也沿用该流程。当前 OUT-02 的 Internal Picking 是本轮模拟期间的实际操作记录；它不代表项目负责人批准了两步路线。

因此纠正对象是 Ginlong 项目配置、订单 Picking 类型/创建行为、状态联动、API06/API08 来源和测试/HVR 契约；不是 KRWH 全局 Route，也不是已经正确的一步 Incoming Route。

本地数据库的实际案例与配置进一步印证该偏差：项目 236 的 `outbound_pick_type` 为空；活动出库订单 1402（`CC5HVR-20261126-OUT-02`）关联 Done/Internal Picking 1936（`KRWH/KRINT/00009`），其 move line 1967 记录 SN-002 数量 1 和来源托盘；对应 API06 Log 9491、Event 7969 成功。ORM 库存核对显示该 Internal Picking 没有产生物理出库扣减。这些记录证明按钮/数据源允许 Internal Picking，但不能证明一步 Outgoing Picking 或其库存扣减、API08 订单状态动作已验收。该订单、Picking、Log、Event 和测试记录均保持原样。

## 5. 最小修正顺序建议

1. Human Review 确认第 2 节业务基线，并确认 Ginlong 出库单 `status` 的备货/离仓映射及实际离仓时间来源；无需改变 API06/API08 V3.2 字段。
2. 版本化修订 SRS、TDD、Implementation Plan、CC-005 测试契约；冻结后再实施。
3. Ginlong 专属地将 Picking 类型收敛到 KRWH Outgoing，并实现订单级唯一 Picking 防重；不改其他客户 WMS 路径。
4. 修正完成 Picking 后的 Ginlong 订单状态联动；API06 只取该单 Done/Outgoing Picking；实际离仓按钮只写状态/日志并触发 API08。
5. 调整 API04/API06/API08 的项目级测试和 HVR 操作指南。保留原测试结果和失败/偏差记录；新增修订后的 RUN/证据，不覆盖旧记录。
6. 执行受影响的自动化和组件集成回归，再进行新的项目主链模拟/人工 HVR；其他接口和通用组件的正确既有验收证据继续复用。

## 6. 评审请求

请 Human Review 确认：

- 是否批准“每张业务订单至多一张非取消的实际 Picking”，入库为 Incoming、出库为 Outgoing。
- 是否批准出库 Outgoing Picking 在备货操作中完成并只移动库存一次；实际离仓仅更新订单状态及发送 API08。
- 是否批准 Ginlong API06 仅在唯一 Done/Outgoing Picking 完成后发送。
- API08 的 `shipmentConfirmed` 是否按现有出库 `status` 生成，以及离仓时间是否复用 `actual_outbound_datetime`。
- 是否批准保留 OUT-01/OUT-02 历史操作和日志，只将其标注为不满足新路线基线的历史证据，不删除或重跑。

**本次执行记录：**完成文档、源码、自动化用例及 HVR 指南静态审查；KRWH/项目/OUT-02 证据来自本地开发库只读 ORM 核查。未修改业务代码、仓库配置、数据库记录、既有 SRS/TDD/Plan、自动化测试或历史验收记录；未执行测试、未调用真实 Ginlong 接口。

## 7. 证据索引

- [SRS v1.9：业务事件区分及库存职责](../requirement/SRS_ginlong_apis-v1.9.md#L56)、[业务约束](../requirement/SRS_ginlong_apis-v1.9.md#L111)、[API04/API06/API08 功能要求](../requirement/SRS_ginlong_apis-v1.9.md#L142)。
- [TDD v2.2：当前 UI/Picking 设计](../ginlong_apis/TDD-v2.2.md#L58)、[API04/06/08 数据来源](../ginlong_apis/TDD-v2.2.md#L111)、[API04 多 Picking 事件与 API08 发货明细方案](../ginlong_apis/TDD-v2.2.md#L126)。
- [Implementation Plan v2.9：项目级 HVR 入口](IMPLEMENTATION_PLAN_ginlong_apis-v2.9.md#L29)。
- [CC-GIN-005 v1.1：当前范围和 Picking 验收](CC-GIN-005-v1.1.md#L36)；[CC-GIN-012：库存主链与 CC-TEST-149～152](CC-GIN-012-v1.0.md#L180)。
- [项目允许 internal/outgoing 的字段](../../mymodules/wd_project_profile/models/project_project.py#L18)、[项目设置视图域](../../mymodules/wd_project_profile/views/project_project_views.xml#L26)。
- [Outbound Order 的 Internal-only `pick_type`](../../mymodules/worlddepot/models/outbound_order.py#L47)、[订单状态 selection](../../mymodules/worlddepot/models/outbound_order.py#L141)、[按订单和类型防重的 Picking 创建](../../mymodules/worlddepot/models/outbound_order_create_picking.py#L261)。
- [API03 从 Project 复制 pick type](../../mymodules/ginlong_apis/services.py#L726)、[Picking 完成后的两步状态逻辑](../../mymodules/worlddepot/models/my_stock.py#L168)、[定时任务查找 Internal→Outgoing Picking](../../mymodules/worlddepot/models/outbound_order.py#L1417)。
- [API04 的单 Picking Payload 构造器](../../mymodules/ginlong_apis/models/ginlong_callbacks.py#L60)、[API06 当前所选 Picking 数据源](../../mymodules/ginlong_apis/models/ginlong_callbacks.py#L133)、[API08 当前发货明细来源](../../mymodules/ginlong_apis/models/ginlong_callbacks.py#L211)、[现有出库回传 Notebook](../../mymodules/ginlong_apis/views/ginlong_callback_views.xml#L47)。
- [API04 多 Picking 自动化用例](../../mymodules/ginlong_apis/tests/test_ginlong_api.py#L2521)、[主链 CC-TEST-149～152 当前顺序](../../mymodules/ginlong_apis/tests/test_ginlong_api.py#L7522)。
- [项目级 HVR 的当前 API06/API08 步骤](../ginlong_apis/hvr/HVR_Project_Business_Flow_Guide.md#L76)、[历史 OUT-01 两张 Picking 记录](../ginlong_apis/hvr/project_flow/CC-GIN-005_Final_Simulation_HVR_Report.md#L28)、[历史 HVR 对 API06 时序的说明](../ginlong_apis/hvr/project_flow/CC-GIN-005_Final_Simulation_HVR_Report.md#L95)。

## 8. 本轮操作边界

本轮只新增本审查稿。未改动任何既有 SRS、TDD、Implementation Plan、CC、测试、HVR、代码或仓库配置；没有写入或删除 Odoo 业务数据，没有执行自动化测试，没有调用真实 Ginlong 接口。当前工作区在本轮开始前已有大量未提交改动；这些既有改动均未触碰。
