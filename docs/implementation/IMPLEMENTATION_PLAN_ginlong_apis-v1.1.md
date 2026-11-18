<!-- 执行补充基线：不覆盖 Implementation Plan v1.0 冻结原文。 -->

# Ginlong APIs 实施计划执行补充

## 文档信息

| 项目 | 内容 |
|---|---|
| 文档 | `IMPLEMENTATION_PLAN_ginlong_apis` 执行补充 |
| 版本 | v1.1 |
| 状态 | Active Execution；CC-GIN-003 In Progress / Frozen with Open Items |
| 生效日期 | 2026-11-18 |
| 计划负责人 | 李建强 |
| 历史基线 | [Implementation Plan v1.0 Frozen](IMPLEMENTATION_PLAN_ginlong_apis.md)，原文保留不覆盖 |
| 当前需求/技术/编码基线 | [SRS v1.0 Frozen](../requirement/SRS_ginlong_apis.md)、[TDD v0.4 Frozen with Open Items](../ginlong_apis/TDD-v0.4.md) 与 [v0.4.1 Ginlong 地址/鉴权事实补充](../ginlong_apis/TDD-v0.4.1.md)、[CC-GIN-003 v1.1 Frozen with Open Items](CC-GIN-003-v1.1.md) |
| Human Review | CC-GIN-003 v1.1：APPROVED；批准本地开发、自动化测试与 Mock HTTP；不授权真实 Ginlong 或生产访问 |
| 模板同步 | BLOCKED：缺少项目模板源；沿用已批准例外，不表示通过 |

本文件只补充 v1.0 的当前实施基线与状态，不重新冻结或改写历史计划。用户已授权继续同一 CC，不新开 CC。TDD v0.4 仍为冻结技术设计基线，v0.4.1 仅记录后续确认的 Odoo→Ginlong 回传 Base URL 与无鉴权/Key，不改写冻结原件。项目按 Ginlong→Odoo→Karl Rapp 实际执行→Odoo 记录执行及库存→用户手动回传 Ginlong 的闭环实施；`worlddepot` 管业务订单/API User/盘点指令与实盘结果，Odoo `stock` 管实际出入库及库存，`ginlong_apis` 只处理 Ginlong 协议与数据交换。

## 1. CC 状态

| CC | 状态 | 执行范围 |
|---|---|---|
| CC-GIN-001 | Closed / Human Review APPROVED | 模块基础与现有 API 日志凭据保护；历史证据保留 |
| CC-GIN-002 | Closed / Human Review APPROVED | API01/03/05/07 入站基础接口；ATR-RUN-009 是前序有效测试基线 |
| CC-GIN-003 | Frozen with Open Items / In Progress | 入站幂等/限流、UPDATE/DELETE、五个人工回传、必要的 `worlddepot` 修改及自动化测试 |

当前继续 CC-GIN-003，不生成关闭 FR。CC-TEST-010/017/019 保留原验收标准，已由 ATR-RUN-026 自动化及 ATR-RUN-014/016 的本地 HTTP 证据完成；完整人工 WMS 流程及三系统 E2E 留最终集成 CC，不作为本轮前置条件。项目与货主解绑、托盘生命周期仍是后续必须完成的项目需求，不计入本 CC 的完成结论。

## 2. 当前实施状态

### 2.1 已实现并有定向证据

- 使用既有 `odoo.conf`、`venv` 和 `odooce_karlrapp`。`worlddepot` 18.0.0.3、`ginlong_apis` 18.0.2.0.1 均通过 Odoo 模块升级并在 ORM registry 中为 installed。
- 五个 Order 表单按钮与业务确认 Wizard 已接入。API02/08 显示 `worlddepot` Order 状态；API04/06 显示实际 picking/move line 数据；API10 读取关联的 `worlddepot` 实盘结果。业务界面不展示 JSON。
- `worlddepot` 持有客户盘点订单 `world.depot.stocktake.order` 与仓库实盘结果 `world.depot.stocktake.result` 两个模型。API05 写入客户指令及计划范围，API10 从实盘结果取数；不在 `ginlong_apis` 建平行盘点模型，不使用或读取 `stock.quant`。
- API06 既有备货完成来源已定位为出库订单 `status='picking'`、`picking_PICK`、`picking_PICK_date`。Wizard 展示既有事件且不增加状态门禁；Hoymiles 专属 `set_status_to_pick_finished` 不作为 KR 备货数据。
- Endpoint URL 与 HTTP method 按 API 在 Odoo Settings 配置。请求/响应/失败写入现有 `world.depot.api.log`；URL userinfo 与敏感查询字段会遮蔽。单次 HTTP helper 使用 15 秒 timeout，不自动重试。
- 协议语义未确认时，后台 Payload builder 显示具体 Open Item 并阻止 HTTP 发送；不猜 action、撤销、部分范围或现场操作信息。

### 2.2 最近测试与验证

| 证据 | 结果 | 范围与边界 |
|---|---|---|
| ATR-RUN-018 | 7 项，0 failed / 0 error | 盘点双模型、API05 写入/更新/取消、API10 实盘摘要、API02 状态摘要、API06 无状态门禁、协议缺失时不发送、Mock HTTP helper |
| ATR-RUN-019 | 2 项，0 failed / 0 error | 真实 ORM `stock.picking`/`stock.move.line`/lot/package 数据的 API04/06 Wizard 摘要 |
| ATR-RUN-020 | 3 项，0 failed / 0 error | API08 状态摘要、未决协议日志、Endpoint URL 凭据不进入现有 API 日志 |
| ATR-RUN-021 | ORM 检查完成 | 模块状态/版本、模型字段、五个按钮方法、视图已注册，旧 Ginlong 盘点模型不再注册；只使用 ORM |
| ATR-RUN-022/023 | 5 项，0 failed / 0 error | Endpoint 缺失提示/阻断、URL 凭据日志遮蔽、Wizard 复用 `stock.group_stock_user` 权限 |
| ATR-RUN-024 | 1 项，0 failed / 0 error | Endpoint 凭据从模拟响应/异常内容中遮蔽 |
| ATR-RUN-010/016/017 | 历史已通过证据继续有效 | API07 100/s 多 worker、响应丢失重放、既有 15 项自动化；未重跑 |
| ATR-RUN-025 | 29 post-tests，2 failures | 首次事务自动化运行失败，原始记录保留，不作为通过 |
| ATR-RUN-026 | 29 post-tests，0 failed / 0 error | 修复测试断言后重跑；完成 CC-TEST-010/017/019 自动化证据。010 为四 Worker HTTP 同请求提交证据加独立 ORM cursor 回滚接管测试；017 为 Cursor commit 故障原子性测试；019 为本机 HTTP 响应丢失重放加 ORM 并发仲裁 |

上述测试只证明本地 ORM、业务展示、日志与安全阻断等已执行部分。完整按钮→协议 Payload→HTTP 成功 Mock 流程尚未通过，真实 Ginlong 和生产接口未访问。

## 3. 按接口隔离的剩余工作

| 接口 | 当前可继续部分 | 仍然阻塞的部分 |
|---|---|---|
| API02 | `TPL_Receipt_Confirmation` 已确认；Order 状态来源和业务 Wizard 已就绪 | Ginlong：HTTP Method、`action` 与 `receiptConfirmed` 的状态/撤销组合仍未定且 V3.2 表格/样例有冲突。Odoo：字段到 Payload 映射尚未实现；完整 Payload/HTTP 验收未通过 |
| API04 | `TPL_Inbound_Completion` 已确认；可从实际 picking/move line 读取产品、SN、数量、托盘和完成时间 | Ginlong：HTTP Method、撤销 wire 值/范围、部分过账与整单触发说明冲突、时间格式/时区及每 SN 时间粒度待确认。Odoo：实际 operator 字段不存在；其余可用字段映射及允许的缺失值补充输入尚未实现 |
| API06 | `TPL_Picking_Completed` 已确认；备货事件为现有 `status='picking'`/`picking_PICK`/`picking_PICK_date`，可读取 picking/move line 实绩 | Ginlong：HTTP Method、撤销/部分范围、`palletQty`/`totalWeight` 的计数与重量口径/JSON 类型、操作时间格式待确认。Odoo：逐 SN operator 字段不存在；部分实绩字段映射和补充输入尚未实现 |
| API08 | `TPL_Shipment_Completed` 已确认；Order 状态来源和业务 Wizard 已就绪 | Ginlong：HTTP Method、`action` 与 `shipmentConfirmed` 的 wire/撤销组合未定且资料冲突。Odoo：状态字段映射尚未实现；V3.2 API08 请求无 picking/SN 范围字段，不把多 picking 列为其阻塞项 |
| API10 | `TPL_Stocktaking_Completed` 已确认；`worlddepot` 两模型及实盘字段、操作人关系、实际时间已可读 | Ginlong：HTTP Method、撤销 action/撤回范围、部分采集与整单触发冲突、operator 字符串表示及时间格式待确认。Odoo：实盘 Payload 映射及部分实盘结果选择尚未实现；不使用计划数据或 `stock.quant` |

API02/04/06/08/10 objectid 已由用户提供并登记于 [V3.2 参数核对记录](../ginlong_apis/V3.2参数核对记录.md)，不再是这些接口的 Open Item；管理员仍须按环境将其配置到完整 Endpoint。各接口 HTTP Method 尚未提供。以上按 ATR §7.1 区分 Ginlong 协议缺口、本地来源缺口和映射未实现。接口 03 方向继续按 A-003 Solis→Odoo 本地开发假设，正式方向待 Ginlong 确认。

## 4. 下一步执行顺序

1. 继续完善无需补造外部语义的组件验收：多 picking 数据选择和保留 WMS 功能回归；已通过的 API02/08 状态、API10 实盘来源、Endpoint 缺项提示及 Wizard 库存用户组 ACL 不重复作为未测项。
2. 将 Ginlong 每项待确认契约按接口登记。获得书面依据后，仅实现该接口确认的字段映射和 wire Payload，并使用本地 Mock HTTP 测成功、失败、超时、日志及无自动重试；未授权前不访问 Ginlong 网络。
3. 分别完成 API02/04/06/08/10 的 CC-TEST-001–007，不以其他接口 PASS 代替受阻接口；完整字段与核心行为未执行时保持 PARTIAL/BLOCKED。
4. 按 CC-TEST-024 对受本次修改影响且要保留的 `worlddepot` 功能执行自动化回归，IHR 记录重要删除和实际影响。完整人工 WMS 业务流程不在本 CC 验收，安排最终集成 CC。
5. CC-TEST-010/017/019 自动化验收已完成，不重复运行。完整人工 WMS E2E 留最终集成 CC；CC-TEST-024 中受本次修改影响的自动回归仍按冻结要求单独完成，不与人工 E2E 混为一项。
6. 追加更新 ATR/IHR。每次测试记录既有 Odoo 环境、精确命令、测试数、日志路径、实际结果和未完成事项。模板同步继续 BLOCKED，真实联调未授权时不得执行。

## 5. 环境与范围限制

- 仅使用本项目 `venv`、`odoo.conf`、数据库 `odooce_karlrapp`；不新建数据库或虚拟环境。
- 数据库检查/测试使用 Odoo Shell ORM 和 Odoo 标准测试运行器，不直接访问 PostgreSQL或执行 SQL。
- 不安装、启用或使用 `stock_barcode`；不接触 `stock.quant` 作为 API10 数据来源。
- 不修改 `karlrapp_gateway`、生产 `stock.picking` 库存流程或无关 WMS 逻辑。
- 仅本地开发、ORM 自动化和 Mock HTTP；不访问 Ginlong 测试/正式 URL或生产环境。
- 不自动回传、不后台重试、不增加队列/定时任务/状态机/独立日志或认证框架。
- Ginlong 尚未确认的业务规则、协议字段和操作来源均保留 Open Item；禁止用计划数据、Order 负责人、回传按钮用户或点击时间冒充现场作业结果。

## 6. 版本记录

| 版本 | 日期 | 变更 | 状态 |
|---|---|---|---|
| v1.1 | 2026-11-18 | 在 Plan v1.0 Frozen 历史基线上，追加用户提供的 Ginlong objectid、ATR-RUN-025/026 事务自动化结果和逐接口/字段级回传阻塞；明确完整人工 WMS E2E 留最终集成 CC；不修改 Plan v1.0 原文 | Active Execution；模板同步 BLOCKED |
