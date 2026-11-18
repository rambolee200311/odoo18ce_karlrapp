<!-- CC-GIN-003 v1.1 Frozen with Open Items：Human Review APPROVED；模板同步仍 BLOCKED，沿用批准例外但不记为 Passed。 -->

# Coding Contract：CC-GIN-003

## 文档状态

| 项目 | 内容 |
|---|---|
| CC ID | CC-GIN-003 |
| 版本 | v1.1 Frozen with Open Items |
| 当前状态 | Frozen with Open Items；批准后继续本 CC 剩余实施 |
| 本 CC 候选范围 | API01/03/05/07 入站幂等与限流；API02/04/06/08/10 手动回传 |
| 上游基线 | SRS v1.0 Frozen；TDD v0.4 Frozen with Open Items；Implementation Plan v1.1 执行基线（v1.0 保留历史） |
| 前序 CC | CC-GIN-002 v1.0 Closed；ATR-RUN-009 为最终有效测试基线 |
| 项目架构认知 | [PROJECT_COGNITION.md](../context/cognition/PROJECT_COGNITION.md) v1.6 |
| Human Review | 李建强；2026-11-17；APPROVED；按评审意见修订并冻结 v1.1 |
| 模板同步 | BLOCKED：项目模板来源缺失；沿用用户批准的流程例外作评审准备，不代表同步通过 |
| 授权 | 已授权继续实施本 CC 剩余范围，包括回传功能、必要的 `worlddepot` 修改及自动化测试；限本地开发、测试和 Mock HTTP，不访问真实 Ginlong 或生产环境 |

本项目仅用于 Ginlong 与 Karl Rapp 的业务对接，不建设通用第三方 WMS 集成框架。Odoo 作为业务单据、库存执行记录及三方数据交换枢纽；项目可按需修改现有 `worlddepot`，但不得重做现场 WMS 作业。

本文件是 CC-GIN-003 v1.1 Frozen with Open Items，取代 v1.0 作为后续实施验收基线；历史版本保留。本修订细化三系统职责、五个回传接口的数据来源、Endpoint 配置、Wizard、按接口隔离阻塞、盘点双模型要求及 `worlddepot` 项目范围内修改/删除与保留功能回归；四个入站 API 的幂等/限流标准及 CC-TEST-008–024 验收要求不降低。API10 模型缺口仅阻塞 API10；API02/04/06/08 具备条件的部分继续实施。外部协议、API03 正式方向、API07 DELETE 契约及模板同步等 Open Items 保留原状态。

## 1. 目标与三系统职责

本 CC 候选范围涵盖四个 Ginlong 入站接口的幂等/限流，以及五个由 Odoo 用户手动触发的回传接口。完整数据流保持：Ginlong 下达业务指令 → Odoo 接收订单并转发给 Karl Rapp → Karl Rapp 执行实际仓库作业 → Odoo 根据 Karl Rapp 返回的实际执行结果，使用现有 `stock.picking` 记录执行与库存变化 → 用户从相应 Odoo 业务订单按钮将结果回传 Ginlong。

Odoo 是业务记录及数据交换枢纽，不重新开发 WMS。Order 记录业务指令，`stock.picking` 记录实际执行；两者不建立强制关联，按订单标识及实际业务数据核对。回传来源使用现有 WMS 订单/执行记录，不将下达指令视为仓库执行完成。

| 组件 | 职责边界 |
|---|---|
| `worlddepot` | 负责业务 Order、API User、Token、客户盘点指令及仓库实盘结果；按项目需要可修改、扩展或精简，但须核实当前实现并保护保留的 WMS 核心功能。 |
| Odoo `stock` | 负责实际出入库记录、库存移动及库存台账；API04/06 的实际作业数据从现有 `stock.picking`、`stock.move.line` 读取。 |
| `ginlong_apis` | 仅负责 Ginlong 接口协议、数据转换、Endpoint 配置、回传 Wizard 和接口调用；不重复实现 `worlddepot` 已有业务模型或 Odoo `stock` 职责。 |

API10 从 `worlddepot` 仓库实盘结果读取实际采集数据，并关联客户盘点指令；不得使用 `stock.quant` 推算实盘结果。若源码或 ORM 核查发现所需业务能力缺失，先记录具体缺口和当前实现状态，再按批准范围评估扩展现有 `worlddepot`；不得在 `ginlong_apis` 新建平行业务模型。

## 2. 范围

### 2.1 候选接口与数据来源

| 接口 | 业务事件 | Odoo 按钮所在单据 | 后台 Payload 数据来源 | 边界 |
|---|---|---|---|---|
| API02 | 收货确认 | 入库 Order | `worlddepot` 对应入库 Order 的现有业务状态 | 使用现有状态、字段和方法；不从 picking 状态推断，也不因按钮点击另做库存记账 |
| API04 | 入库完成 | 入库 Order | Odoo `stock` 的实际 `stock.picking`、`stock.move.line` | 产品、SN、数量、托盘等来自实际执行记录；多 picking 按本次选择范围处理 |
| API06 | 备货完成 | 出库 Order | Odoo `stock` 的实际 `stock.picking`、`stock.move.line` 作业记录，以及 WMS 现有备货完成信息（如有） | 识别已有备货完成信息；不得以 picking 创建、确认或库存过账代替；不新增状态门禁、审批或业务限制 |
| API08 | 发货完成 | 出库 Order | `worlddepot` 对应出库 Order 的现有业务状态 | 使用现有状态、字段和方法；不以 picking 创建或库存过账替代该业务状态 |
| API10 | 盘点完成 | 客户盘点 Order | `worlddepot` 客户盘点指令及其关联的仓库实盘结果 | 实际 SN、产品及数量必须来自实盘结果；不使用 `stock.quant` 或订单计划数据 |

五个按钮都位于对应 Odoo 业务 Order 上：API02/04 在入库 Order，API06/08 在出库 Order，API10 在客户盘点 Order。统一流程为“业务 Order → 点击回传按钮 → Wizard 业务数据确认界面 → 必要时补充缺失字段 → 用户确认 → 后台生成 JSON 并发送 HTTP 请求”。Wizard 展示订单号、回传业务事件、关联作业单及关键业务数据；API04/06 展示实际产品、SN、数量、托盘等信息，API02/08 展示对应 Order 的业务确认状态，API10 展示仓库实盘结果。业务用户不查看或编辑 JSON。Wizard 复用现有业务状态、字段和方法；仅允许补充确实缺失且需要的回传必填字段，不新增平行业务模型、JSON 编辑器、技术调试页面或额外状态机。已确认必需字段不得因外部协议缺失而静默省略。缺项按接口和场景隔离：API10 实盘模型安装/验收未完成只阻塞 API10；API02/04/06/08 的具体数据来源或事件未核实，则只阻塞对应接口/场景。任何未验证的核心行为仍标 BLOCKED，不以部分字段映射冒充完整验收。

### 2.2 明确排除

- 本 CC 只服务 Ginlong 与 Karl Rapp 对接，不扩展成通用第三方集成框架。`ginlong_apis` 仅承载协议、转换、Endpoint 配置、Wizard 和接口调用；业务 Order、API User/Token、盘点指令及实盘结果由 `worlddepot` 负责，实际出入库和库存记录由 Odoo `stock` 负责。允许为本项目修改、扩展、精简 `worlddepot`；优先复用既有模型，不重复开发业务模型或建立平行模型。API09 库存查询不属于本 CC。
- 不重做实际仓库收货、上架、拣选、发货、盘点现场作业或库存业务；Ginlong 订单接收、回传和必要字段映射按批准契约接入现有 WMS 服务。
- 可按 Ginlong–Karl Rapp 项目需要修改、精简或删除 `worlddepot` 中确认不再使用的模型、字段、方法、视图及相关代码；无须为每项删除单独申请批准。删除前必须检查模块 manifest 依赖、Python/XML 导入与引用、模型/字段关系、菜单/动作/视图、路由及实际调用路径，确认不会破坏项目保留的 WMS 功能。无需为无实际用途的历史兼容代码保留兼容层。
- `worlddepot` 中项目涉及及明确保留的 WMS 行为必须保持可用。实施需对受影响的入库/出库单据、picking 创建与处理、共享 API 认证/日志及视图路径增加必要自动化回归。IHR 记录重要删除项、核查依据及影响；明确删除的项目外功能记录为范围移除，不将其误报为回归通过或失败。不得进行与项目目标无关的大规模重构。
- 回传自动触发、cron、后台队列、自动重试、状态变化触发、安装/升级或服务重启触发。
- 新建回传状态机、attempt/游标模型、事务调度、并发锁、独立 Adapter 框架、专用日志/监控体系或认证框架。
- 由集成层确认、完成或记账仓库作业；不得因点击回传按钮而执行 `stock.picking` 过账、库存扣减或其他 WMS 动作。
- API10 库存调整；按 TDD 盘点隔离约束，不读写 `stock.quant` / `stock.move`，不创建库存移动。
- 已有 `audit_log`/`auditlog` 字段变更跟踪模块的开发、修改、配置改造及专项测试；字段变更跟踪复用现有能力，不由本 CC 增加另一套审计记录。
- 强制 Order 与 `stock.picking` 建立关系；允许按现有业务标识和数据核对。
- 本地模拟以外的真实 Ginlong 网络联调、完整人工 WMS 业务流程及三系统端到端验收；这些由后续集成 CC 安排。

项目必须完成的订单货主与项目货主解绑、托盘生命周期管理不纳入本 CC 整体验收，也不得宣称已完成。若特定按钮 Payload 或其来源场景直接依赖这两项能力，则只将该受影响场景标记 BLOCKED/延期，并记录依赖；不扩大阻塞到不依赖的回传场景。

### 2.3 API01/03/05/07 入站幂等及业务键

本 CC 候选范围覆盖已确认的业务唯一键：

| 接口 | 业务键 | 当前调用路径/规则（源码核对） |
|---|---|---|
| API01 | `inboundOrderNo` | `ginlong_controller.py` 调用 `services.api01`；当前支持 CREATE/DELETE，CREATE 直接创建入库订单 |
| API03 | `outboundOrderNo` | `ginlong_controller.py` 调用 `services.api03`；当前支持 CREATE/DELETE，CREATE 直接创建出库订单；方向仍仅为 A-003 本地假设 |
| API05 | `countOrderNo` | 入站服务已改为写 `world.depot.stocktake.order`；订单保存计划范围，实盘结果由关联 `world.depot.stocktake.result` 保存；模型不新增全局唯一约束 |
| API07 | `owner + productCode` | 当前 `services.api07` 只按 `default_code=productCode` 查找产品，未将 owner 纳入识别条件；需按确认的复合键修订 TDD 设计，复用 `product.product` 扩展字段，不默认新建产品映射模型 |

表中业务键是 Ginlong 接口幂等判定使用的外部业务标识，不代表对应 Odoo/WMS 模型必须对该字段或字段组合施加全局唯一约束。幂等记录自身仅对 `(api_code, business_key, request_fingerprint)` 建立防重复约束；本 CC 不增删或改变 `inbound.order`、`outbound.order`、盘点、`product.product` 等 WMS 模型现有唯一性规则，也不以接口幂等需求为由新增业务唯一校验。

### 2.4 UPDATE/DELETE 与现有模型支持情况

以下结论来自当前 `services.py`、控制器及对应 WMS 模型源码。Ginlong 接口操作语义与模型能力分别判断；本 CC 不据接口业务键新增模型全局唯一规则。

| API | 当前 UPDATE 支持 | 当前 DELETE/取消支持 | 本 CC 处理要求 |
|---|---|---|---|
| API01 入库单 | `services.api01` 当前没有 UPDATE 分支，只支持 CREATE/DELETE；现有 `world.depot.inbound.order` 可通过 ORM `write` 修改，但未发现 Ginlong 专用更新服务。 | 当前服务调用 `order.unlink()`；模型有 `cancel` 状态和 `action_cancel()`，但该方法对已取消单据报错，并可能删除关联的未完成 `stock.picking`；模型还允许特定状态下物理删除订单。 | UPDATE 按已批准字段映射使用现有入库模型修改逻辑；DELETE 只把订单状态写为 `cancel`，保留订单及相关原始记录，不调用 `unlink()` 或带有删除拣货副作用的 `action_cancel()`。已取消记录再次 DELETE 返回幂等成功。 |
| API03 出库单 | `services.api03` 当前没有 UPDATE 分支，只支持 CREATE/DELETE；现有 `world.depot.outbound.order.write()` 可用于修改，并保留其现有日期换算逻辑。 | 当前服务调用 `order.unlink()`；模型有 `cancel` 状态和 `action_cancel()`，但该方法对已取消单据报错，并可能删除关联的未完成 `stock.picking`；模型还允许特定状态下物理删除订单。 | UPDATE 复用现有出库模型 `write()`；DELETE 只把订单状态写为 `cancel`，保留订单及相关原始记录，不调用 `unlink()` 或带有删除拣货副作用的 `action_cancel()`。已取消记录再次 DELETE 返回幂等成功。 |
| API05 盘点单 | `services.api05` 当前没有 UPDATE 分支；现有 `world.depot.stocktake.order` 通过 ORM `write` 更新指令字段。 | 旧 Ginlong 盘点任务模型及 ACL 已按 ORM 0 记录和源码引用核查移除；API05 DELETE 对 `world.depot.stocktake.order` 仅将状态改为 `cancel`，保留指令及关联实盘记录；重复取消返回幂等成功。 |
| API07 产品档案 | 当前 `services.api07` 已执行原生产品 upsert：存在产品时对 `product.template`/`product.product` 调用 `write()`，不存在时创建产品；目前按 `default_code` 查找，未将 owner 纳入查找。 | 当前 API07 没有 DELETE 动作分支或订单状态字段；不能套用订单 `cancel` 语义。 | UPDATE 复用现有产品写入/upsert 流程，并按已确认的 `owner + productCode` 键修订定位。除非 Ginlong 后续契约明确产品删除/停用规则，本 CC 不实现 API07 DELETE，不物理删除或擅自归档产品。 |

**DELETE 幂等规则：**对 API01/03/05，找到的记录若已处于 `cancel`，重复 DELETE 返回成功结果且不再改动数据；未找到或查找结果歧义仍按现有接口错误处理，不伪造已取消记录。首次 DELETE 仅修改目标订单/任务状态，不调用物理 `unlink()`。UPDATE 使用已批准契约字段并复用对应模型既有 `write()`；不自行补造字段映射或额外业务校验。

完全相同请求的判定还需内容指纹：API code、上述业务键、规范化请求内容。相同业务键但内容不同必须进入接口动作处理；幂等层不得直接返回旧结果或拒绝合法更新。UPDATE 复用对应模型现有修改逻辑；API01/03/05 DELETE 按 §2.4 保留原业务记录并只取消对应订单/任务状态。API03 其他操作限制及 API01/03/05 的字段更新映射按已批准契约执行；API07 按产品档案新增/修改契约处理，其 DELETE 不在当前确认范围。此段不补造各动作的外部响应及冲突语义。

### 2.5 源码现状核对

本版修订时，API01/03/05/07 的幂等、ORM 限流与订单动作代码已在实施；运行证据及未完成的 CC-TEST-010/017/019 子项见 ATR/IHR。本 v1.1 不重开或放宽这些入站验收。五个回传按钮与出站客户端按本版授权继续实施；共享认证、日志沿用 `worlddepot`。API10 模型缺口按 §2.7 在 `worlddepot` 最小扩展。

具体实现/运行证据见 [`ginlong_controller.py`](../../mymodules/ginlong_apis/controllers/ginlong_controller.py)、[`services.py`](../../mymodules/ginlong_apis/services.py)、[`callback_wizard.py`](../../mymodules/ginlong_apis/models/callback_wizard.py)、[`stocktake.py`](../../mymodules/worlddepot/models/stocktake.py)、[`idempotency.py`](../../mymodules/ginlong_apis/idempotency.py)、[`rate_limiter.py`](../../mymodules/ginlong_apis/rate_limiter.py) 及 ATR/IHR。本版未修改 WMS 已有唯一性规则、`auditlog`、认证算法或库存作业逻辑。

### 2.6 回传 Endpoint、Wizard 与执行方式

1. API02/04/06/08/10 的 Endpoint URL（含 `{objectid}`）和 HTTP Method 使用 Odoo 后台配置；不写死在代码中。CC-003 负责轻量 ORM 配置模型及读取能力，CC-004 提供管理员菜单/表单。任一接口缺少有效配置时禁止发送并显示明确错误。
2. 用户点击相应业务 Order 上的「回传锦浪」按钮后打开 Odoo 标准 Wizard。Wizard 展示订单号、回传业务事件、关联作业单及关键业务数据：API02/08 展示对应 Order 的业务确认状态；API04/06 展示实际产品、SN、数量、托盘等相关信息；API10 展示仓库实盘结果。多张 picking 时允许选择本次实际作业记录。
3. 仅对现有记录中确实缺失且 Ginlong 已确认必填的字段提供补充输入；不新增其他业务录入要求，不重复录入已有数据，不把回传用户或按钮时间填作现场操作人/时间。业务用户不查看、不编辑也无需理解 JSON。
4. 用户确认后，后台根据现有业务记录及允许补充的字段生成符合 Ginlong 协议的 JSON，由标准 Odoo 按钮方法同步发送一次 HTTP 请求，设置合理超时且不自动重试。复用 `worlddepot` 现有 API logger 保存请求 JSON、响应及错误信息，供管理员和技术人员查看；向业务用户显示成功或失败结果。
5. Ginlong V3.2 未明确的 action、撤销、多 picking、增量/累计及数值类型等 Open Items 保持待决。已确认且存在数据来源的字段可以开发和测试；单个未决字段/场景只阻塞直接依赖它的部分。
6. 项目范围内允许修改 `worlddepot` 既有对象以完成数据提取、API 调用或必要字段扩展；也可按 §2.2 移除经确认的无关代码。须保留项目使用的 WMS 行为并执行对应回归。

### 2.7 盘点模型源码与 ORM 核查

项目盘点由两个业务模型组成：`worlddepot` 客户盘点订单及其关联的仓库实盘结果。API10 必须从实盘结果读取实际采集的 SN、产品和数量，并关联客户订单；不得使用 `stock.quant` 或订单计划数据代替实盘，也不得在 `ginlong_apis` 建平行业务模型。

本轮检查了 `odoo.conf` 的 addon 路径、`worlddepot` 的 manifest/import 链及完整模型源码，并通过既有 `odoo shell -c odoo.conf --no-http` 对 `odooce_karlrapp` 的 ORM registry 和 `ir.model.fields` 只读核对。源码及 registry 均未发现 `worlddepot` 盘点订单/实盘结果模型；旧 `ginlong.stocktake.task`/`.line` 仅保存 API05 计划指令。ORM 确认两个旧模型记录数均为 0；源码引用仅包括旧 API05 服务、测试及 ACL。依据本 CC 授权，已开始在 `worlddepot` 增加两个最小模型，将计划范围存于客户订单，将实际结果逐条关联保存，并移除 Ginlong 平行模型及 ACL。升级和自动化验收结果另记 ATR/IHR；验收通过前 API10 仍为 BLOCKED。API10 的模型与测试不阻塞 API02/04/06/08。

## 3. 已确认行为与外部依赖

### 3.1 已确认行为

1. 每个回传由用户点击对应 Odoo 业务 Order 上的「回传锦浪」按钮触发，打开 Odoo 标准 Wizard 作为业务确认界面；用户确认后后台生成 JSON 并同步调用对应接口。
2. Endpoint URL/objectid 和 HTTP Method 从管理员配置读取；配置缺失或不完整时禁止发送并显示明确提示。
3. Wizard 自动读取现有 `worlddepot` Order 业务状态、适用的 `stock.picking`/`stock.move.line` 实际作业记录或 `worlddepot` 盘点实盘结果，展示订单号、回传业务事件、关联作业单和关键业务数据；仅对确实缺失且已确认必填的数据提供输入。业务用户不查看或编辑 JSON。
4. 调用设置合理超时；本 CC 不自动重试。失败后只能由用户再次点击发起重试。
5. 发送后使用 `worlddepot` 现有 API 日志能力保存请求 JSON、响应及错误信息，供管理员和技术人员查看；向业务用户显示成功或失败结果。
6. 本期仅进行权限、安全、数据完整性及格式校验。不得擅自添加订单状态门禁、重复回传规则、业务审批或其他业务检查。
7. 使用现有 Odoo WMS 用户组、认证/权限、配置入口及 API 日志；日志中不记录 Secret、Token 等凭据。业务 Payload 不整体脱敏。
8. API02 和 API08 分别使用 `worlddepot` 对应入库/出库 Order 的现有业务状态、字段和方法；不从 picking 状态或库存过账推断订单业务状态。
9. API04/06 使用 Odoo `stock.picking`、`stock.move.line` 的实际作业记录。API06 从实际 picking/move line 提取作业数据；现有 `set_status_to_pick_finished` 是 Hoymiles 外部回调标记，不代表 KR/Ginlong 备货完成事件，不用于门禁或 Payload。不得新增状态门禁、审批或业务限制。API10 只从 `worlddepot` 仓库实盘结果读取并关联客户盘点指令，不修改库存。

用户提供的 Ginlong 资料给出测试环境基础地址 `http://10.0.3.182:8003/API/WMS_JSON/{objectid}`、正式环境基础地址 `http://10.0.3.182:8001/API/WMS_JSON/{objectid}`，并说明当前接口无鉴权/Key。V3.2 对照核对记录见[参数核对记录](../ginlong_apis/V3.2参数核对记录.md)及[原始工作簿](../ginlong_apis/海外WMS与第三方系统集成V3.2.xlsx)：请求/返回字段表与 V3.1 未见字段变更，但每个 API 的 `objectid`、方法/报文格式、完整响应与错误语义及各事件字段仍须逐项补齐/确认；不在本 Draft 中猜定，也未进行网络调用。

新增的幂等/限流需求依据本次项目用户明确决定：API01/03/05/07 分别以 `inboundOrderNo`、`outboundOrderNo`、`countOrderNo`、`owner + productCode` 为 Ginlong 接口业务键；完全重复的已成功请求复用原结果，失败可重试，差异内容按该 API 动作处理。接口业务键用于集成幂等，不等同于 WMS 模型全局唯一约束，本 CC 不改变现有 WMS 业务唯一性规则。限流按认证后的 API user 和 API 分别计数，阈值独立配置：API01/03/05 默认每秒 10 次，API07 默认每秒 100 次；状态须由 PostgreSQL 持久化并通过 Odoo ORM 并发原子更新，超限返回 HTTP 429 和 `Retry-After`。窗口采用 UTC 固定一秒，不使用滚动窗口或令牌桶。上述要求需要纳入适用的 SRS/TDD 变更基线；本稿不修改冻结 SRS/TDD。

### 3.2 待外部确认或待基线评估

| 事项 | 当前状态及处置 |
|---|---|
| 五个接口各自的 objectid、字段/类型/必填性、操作枚举及响应/错误格式 | 对照 Ginlong 最新 V3.2 资料逐接口核对；未确认的细节不得推定。SRS 已明确字段仍须覆盖；受缺失契约阻塞的接口/场景单独 BLOCKED。 |
| API03 方向 | 仍为 SRS A-003 开发假设，Ginlong 尚未正式确认；不作为已确认外部契约。本 CC 不更改 API03 方向。 |
| API04 多批次/多张 picking 的范围与聚合 | API04 按实际 `stock.picking`/`stock.move.line` 作业记录及确认的接口契约处理；Order 与 picking 松耦合。规则未确认时只阻塞依赖场景，不擅自聚合或设唯一关系。 |
| API02/API08 对应 Order 状态与回传时点 | 分别读取 `worlddepot` 入库/出库 Order 的既有业务状态及方法；如当前状态到接口事件的对应关系在代码中不明确，核实后记录具体缺口，不以 picking 或库存状态替代，也不新增状态机。 |
| API06 备货完成信息的数据来源 | 从现有 `stock.picking`、`stock.move.line` 及 WMS 已有备货完成信息识别和组装回传数据；picking 创建、确认或库存过账不能冒充备货完成。不新增状态门禁、审批或业务限制；若当前实现没有可用的备货完成信息，记录具体数据缺口，不自行新增状态或规则。 |
| API10 部分盘点、重复回传、结果未知、撤销及采集完成语义 | 遵循已确认契约；不自行制定幂等/重复规则、库存差异处理或完成门禁。仅影响 API10。 |
| 货主解绑、托盘生命周期 | 项目必需需求，但不属于 CC-GIN-002；需由独立 CC/后续阶段建立批准基线。受其直接影响的回传场景单独列为依赖。 |
| API10 两个盘点模型 | 源码及 ORM 已确认 `worlddepot` 原先都缺少；批准在 `worlddepot` 内最小新增客户盘点订单和实盘结果两个模型。实现/ORM 集成测试通过前，仅 API10 实盘回传保持 BLOCKED；不得以计划值或 `stock.quant` 代替。 |
| TDD 基线 | 已另存并修订 [TDD v0.4](../ginlong_apis/TDD-v0.4.md)，覆盖本 CC 的数据来源、Wizard、配置与 `worlddepot` 最小盘点扩展；历史冻结 TDD v0.3 不覆盖。 |
| 本地开发环境 URL/实际网络联调 | 仅在明确批准联调和环境可用后执行。当前地址信息不等于已执行 HTTP E2E。 |
| 项目 CC 模板同步 | BLOCKED；沿用已批准的模板缺失流程例外准备本稿，检查仍为 BLOCKED。 |

## 4. 技术边界

- Odoo 标准按钮打开 Wizard 业务确认界面；Wizard 展示现有订单状态、作业记录和关键业务数据。用户确认后后台生成 JSON 并同步执行一次 HTTP 调用；请求 JSON、响应和错误写入既有 API 日志，供管理员和技术人员查看，不向业务用户提供 JSON 查看/编辑工具。
- 五个手动回传按钮不增加事务调度或独立游标设计，遵循普通 Odoo 按钮调用及现有事务行为；入站限流的短 ORM 事务按 §4.2 处理。
- 复用既有 HTTP/配置/认证能力（出站是否无需认证以用户提供的 Ginlong 资料为准）、权限和日志能力；仅在证明现有能力不足且经批准后作最小扩展。
- 不新增平行业务订单、回传 attempt 或 API 日志模型；本次仅按批准在 `worlddepot` 增加缺失的客户盘点订单与实盘结果两个模型。不新增技术状态机和监控体系。复用现有设置存储 Endpoint 配置、使用临时回传 Wizard、入站幂等记录及限流计数模型；不扩展为通用集成平台。
- 不使用 `stock_barcode`。数据库检查只通过现有 Odoo Shell 与 ORM，禁止 SQL/直接 PostgreSQL；使用现有 `odoo.conf`、`venv` 和 `odooce_karlrapp`。
- API10 使用 `worlddepot` 的客户盘点订单与仓库实盘结果两个模型，不触碰库存账；在新模型安装和 ORM 验收前仅阻塞 API10 实绩取数。

### 4.1 拟议幂等事务与并发方案（待 TDD 评审）

**幂等键与指纹：**以 `(api_code, business_key, request_fingerprint)` 建数据库唯一约束。业务键严格按 §2.3 生成；API07 使用无歧义的规范化二元组 `(owner, productCode)`，不拼接可能冲突的分隔符。指纹对解析后的业务 JSON 做确定性序列化：对象键排序、移除无意义空白、保留数组顺序、拒绝 NaN/Infinity 后计算 SHA-256。动作字段和业务字段均纳入指纹；Authorization/Token 等传输凭据不进入指纹或幂等记录。数字表示、大小写、Unicode 等不自行折叠，若 Ginlong 语义要求归一化，需有契约依据。无需再增加单独的秒级 debounce 窗口：相同内容在处理中由唯一约束防并发执行，成功后重放原响应；不同内容不会被时间窗误拦。

**轻量记录与事务边界：**候选 `ginlong.api.idempotency` 只保存 API code、Ginlong 业务键、SHA-256 指纹、成功响应 JSON 和 ORM 标准时间戳；不保存原始请求正文、凭据或完整业务副本。业务服务产生的所有 Odoo 数据库变更与幂等成功记录/响应必须处于同一 Odoo HTTP 请求事务，不能分别提交，也不增加 PROCESSING 状态。只有该请求事务最终成功提交后，幂等成功结果才可用于重放。失败时业务变更和幂等记录一起回滚，允许原请求重试。保留期/清理策略尚未由项目确定；建议本 CC 不自动清理成功记录，避免重放期间丢失原结果，并在 TDD 明确后续保留期决策。

**并发执行与提交结果：**在 Odoo ORM savepoint 内先创建幂等行并 flush 目标约束，再调用现有业务服务；业务成功后写入成功响应并 flush 业务变更与响应，随后退出 savepoint。若创建幂等行发生目标唯一约束冲突，则回滚该 savepoint；Odoo 使用 `REPEATABLE READ`，原 cursor 可能看不到并发事务刚提交的行，因此必须用新 ORM cursor 读取已提交的成功结果并原样重放，不再次调用业务服务。若先行事务回滚，等待请求可继续创建幂等行并执行。只捕获目标唯一约束冲突，其他错误不冒充重复请求。Odoo `SerializationFailure`/deadlock 按 HTTP 事务层既有机制重试。

**失败回滚与成功提交：**业务服务抛错或返回 `success=false` 时，必须回滚包含业务变更和幂等行的整个 savepoint，不保存失败结果为成功幂等项；把失败响应交给现有 `api_logger` 记录，且不得让业务异常穿透其会回滚整个 request cursor 的异常分支。此时完整业务事务未提交，同一请求再次到达时可重新执行。成功路径须将业务记录、成功响应与幂等行作为同一 HTTP 请求事务原子提交；不能在 handler 仅生成成功响应时提前认定已完成。若业务提交失败，所有数据库变更和幂等行一并回滚，Odoo 按既有事务重试处理，任何重试都不得观察到半成品。

现有 `api_logger` 通过独立事务写日志；该日志是请求/响应审计记录，不是业务事务已提交的凭证。TDD 应明确其成功响应记录不得用于证明业务单据或幂等结果已提交；不因此新增日志状态机或日志模型。

**响应丢失与结果未知：**若业务事务已经提交、但成功 HTTP 响应在网络中丢失，调用方重发相同 API、业务键和内容时，命中已提交的幂等记录并取得原成功响应，不重复业务副作用。若原请求仍在处理中，唯一约束使相同请求等待数据库仲裁：原事务提交后重放结果，原事务回滚后由等待请求执行。若调用方无法判断提交结果，执行相同请求重发即可由持久幂等记录消歧；不得仅因客户端超时就生成不同指纹或另行执行。超过 Odoo 既有请求/worker 时限时，未提交事务最终回滚并释放数据库连接，不留下永久处理中行。沿用现有 Odoo/PostgreSQL 锁等待与 worker 时限，不新增任意常量；测试须分别覆盖回滚、提交、提交后响应丢失和提交前异常。

同业务键但不同指纹是不同操作，必须进入该接口动作规则，不得返回旧结果。不同指纹的并发操作不属于相同请求去重；如 Ginlong 契约要求按到达顺序串行更新，先确认顺序语义，再评审最小业务键级串行措施，不能默默让幂等唯一约束替代它。

### 4.2 拟议多 Worker 限流方案（待 TDD 评审）

在 `validate_token` 成功后，用 `request.api_user.id` 作为可信调用方身份；按 API 分开计数，不使用 `remote_addr`、`X-Forwarded-For` 或其他客户端可伪造请求头。配额分别为 API01=10 次/秒、API03=10 次/秒、API05=10 次/秒、API07=100 次/秒，均为默认值且在 Odoo 后台独立配置。不同 API 的请求不消耗彼此配额。

优先复用现有系统配置入口，在 Odoo 后台提供可编辑的四个 API 限流设置项，并以 `ir.config_parameter` 保存各自的正整数阈值；默认值如上表述。若现有设置页不适合承载这些参数，只新增最小的 `res.config.settings` 字段/视图，不另建配置业务模型。运行时读取配置应通过 ORM 直接读取参数记录，避免依赖 `get_param` 的进程级 ORM 缓存；非法或非正整数配置按对应 API 默认值处理并记录配置错误。某 API 的配置变更在该 API 下一秒窗口生效，不在当前窗口中途改变额度。

候选轻量模型 `ginlong.api.rate.counter` 每个已认证 API user/API 组合保留一行：`(api_user_id, api_code)` 数据库唯一约束、当前 UTC 秒窗口起点 `window_start`、当前窗口计数 `request_count`、该窗口阈值快照 `window_limit`。窗口固定为 UTC Unix 时间对齐的一秒区间；不采用滚动窗口、令牌桶或其他限流算法。第一次请求创建 `count=1`，同一调用方、同一 API、同一秒窗口且未达该 API 限额时递增，超额则拒绝；进入新窗口时重置计数为 1 并保存该 API 当时的阈值。该固定窗口让表保持每调用方/API 组合一行且无需清理任务。

并发原子性由同一调用方/API 计数行上的数据库写冲突仲裁，而不是“先读后写”检查。每个请求在业务处理前用短独立 ORM cursor 事务读取并更新计数；同一 user/API 组合的竞争更新在 Odoo `REPEATABLE READ` 下可能触发 serialization failure，或首次建行时触发唯一约束冲突。失败事务必须完整回滚，再用新 cursor 读取最新行并重新判断/申请；必须有受请求/worker 时限约束的有界重试，不能在冲突后沿用旧快照继续放行。重试耗尽时失败关闭并返回服务暂不可用错误，不得错误返回 429，也不得放行未能原子计数的请求。计数事务单独提交，使后续业务失败/回滚仍计入请求速率。不得使用 Python 全局变量、进程内缓存、Odoo 本地 Cache 作为共享限流状态；不使用 Redis 或直接 SQL。HTTP 请求生命周期内可保留一个请求级“已预留”标记，避免 Odoo 内部事务重跑将同一外部请求重复计数；该标记不承载共享配额状态。

超过当前 API 窗口阈值时返回真正的 HTTP 429、JSON 错误及 `Retry-After`，值为距离下一 UTC 秒窗口起点的剩余秒数向上取整（至少 1 秒）。路由顺序建议为认证 → 现有 `api_logger` → Ginlong 限流 → 业务入口，以便拒绝结果也记日志。当前 `api_logger` 仅按 dict 的 `success/code` 记录，无法正确识别 HTTP Response；TDD 应要求对共享 logger 作最小兼容扩展：复用现有 `world.depot.api.log` 及字段，根据 Response status/body 记录 429、`success=false`、`code=429`，并原样返回 HTTP 状态和 `Retry-After`。不改认证算法、不建日志模型/框架。

## 5. TDD v0.4 变更追踪

为落实本 CC v1.1，保留历史冻结的 TDD v0.3 原文件 `docs/ginlong_apis/TDD.md` 不变，另形成当前实施基线 [TDD v0.4](../ginlong_apis/TDD-v0.4.md)。TDD v0.4 已纳入三系统职责、五个回传接口的数据来源、API06 不增加状态门禁、业务数据确认 Wizard（不展示或编辑 JSON）、Endpoint 配置，以及 `worlddepot` 盘点双模型最小扩展。API10 只从实盘结果读取，并与客户盘点指令关联；不读写 `stock.quant`。

TDD v0.4 同时保留 API01/03/05/07 幂等与限流设计、HTTP 事务回滚/提交/响应丢失标准及 CC-TEST-010/017/019 的原验收条件。Ginlong objectid、HTTP method、action/状态 wire 值、撤销/部分回传语义和真实实绩字段缺失仍按接口隔离为 Open Items。项目模板同步继续 BLOCKED，按已批准的模板缺失流程例外记录，不标记为通过。

实施与测试结论按 CC 本身和 ATR/IHR 记录；外部协议未决、未执行项目及本地 Mock 结果不得写成真实 Ginlong 验收通过。

## 6. 候选自动化/组件验收

本 CC 如获批准，验收以现有 Odoo 标准自动化与 ORM/组件集成为主，所有出站 HTTP 均使用测试替身，不访问 Ginlong 网络。完整人工 WMS 操作和三系统 E2E 留最终集成 CC。

### 6.1 五个手动回传接口

下表只记录 API02/04/06/08/10 手动回传验收。其状态、缺陷、证据和结论须在 ATR/IHR 的回传验收分区独立记录，不与入站幂等/限流验收合并判定。

| 测试 ID | 接口/边界 | 验收条件 |
|---|---|---|
| CC-TEST-001 | API02 | Wizard 展示订单号、收货确认事件及 `worlddepot` 入库 Order 现有业务确认状态；不得从 picking 状态推断；缺少配置时不发送；用户确认后一次 Mock HTTP；请求/响应写入现有日志；不改变库存。V3.2 未决动作只阻塞相应动作场景。 |
| CC-TEST-002 | API04 | 从所选实际入库 `stock.picking`/`stock.move.line` 读取产品、SN、数量及托盘等数据，并在 Wizard 展示订单号、事件和关联作业单；覆盖 Order/picking 松耦合；不要求业务用户查看或编辑 JSON。多 picking 未决范围只阻塞依赖场景；不执行库存操作。 |
| CC-TEST-003 | API06 | 从 `stock.picking`、`stock.move.line` 读取备货实际作业结果，并识别已有备货完成信息；不得以 picking 创建、确认或库存过账替代该信息。Wizard 展示实际业务数据，不展示 JSON；不得把计划量/重量冒充实绩，也不得新增状态门禁、审批或业务限制。当前实现缺少某个必需的既有备货信息时，仅将相应数据映射标为 BLOCKED 并记录缺口。 |
| CC-TEST-004 | API08 | Wizard 展示订单号、发货完成事件及 `worlddepot` 出库 Order 现有业务确认状态；不以 picking 创建、状态或库存过账替代；不新增 Order/picking 强关联或状态机；未决 action 只阻塞相关场景；不执行库存扣减。 |
| CC-TEST-005 | API10 | Wizard 展示 `worlddepot` 仓库实盘结果；后台从该结果读取实际 SN、产品、数量并关联 `worlddepot` 客户盘点指令；不使用 `stock.quant`、客户指令计划值或平行模型。两模型源码已补齐，ORM 安装/实盘读取测试完成前此测试保持 BLOCKED，不影响 CC-TEST-001–004/006/007。 |
| CC-TEST-006 | 共用按钮/Wizard/HTTP | 五接口均按业务 Order → 回传按钮 → Wizard 业务数据确认界面 → 必要时补充缺失字段 → 用户确认 → 后台生成 JSON 并发送 HTTP；用户不查看或编辑 JSON。无有效配置不发送；单据状态变化、cron、安装升级和重启不触发；超时/错误不自动重试并向用户反馈。不得新增 JSON 编辑器、技术调试页面、平行业务模型或状态机；API10 模型问题不阻塞其他接口测试。 |
| CC-TEST-007 | 权限、配置、日志与基线 | Endpoint URL/objectid 与 HTTP method 按 API 管理配置；缺项时明确提示且不发送。复用既有权限及 API 日志；无权限不得发送；凭据不入日志；指定开发环境升级及适用自动化/ORM 组件套件通过。 |

**按接口隔离的验收原则：**API10 两模型尚未完成 ORM 安装/读取验收只使 CC-TEST-005 及 API10 专属场景保持 BLOCKED；不得扩大为 API02/04/06/08 的总体验收前置条件。API02/04/06/08 已具备来源、字段契约和 endpoint 配置的功能可独立实施和测试；未确认的某个字段/action/多 picking 语义只阻塞直接依赖场景，不得伪造字段或把部分验证写成完整 PASS。

### 6.2 四个入站接口幂等与限流

下表只记录 API01/03/05/07 入站幂等与限流验收。其运行编号、并发性能数据、缺陷、证据和结论须在 ATR/IHR 的入站验收分区独立记录；回传接口 PASS 不构成本组 PASS，反之亦然。本组不开发、不修改、不专项测试 `audit_log`/`auditlog`。

| 测试 ID | 接口/边界 | 验收条件 |
|---|---|---|
| CC-TEST-008 | 入站业务键 | API01/03/05 分别使用单号键；API07 同时使用 owner 和 productCode；缺键/格式错误不创建业务记录或成功幂等记录。 |
| CC-TEST-009 | 完全相同请求 | 相同 API+业务键+规范化指纹首次执行业务；重放返回原成功结果且不重复副作用；JSON 对象键顺序/空白变化指纹相同，数组顺序保留。 |
| CC-TEST-010 | 并发完全重复 | 多 Odoo worker 并发提交相同请求只产生一次业务副作用；另一请求返回原结果；首个事务失败回滚时等待请求可接手执行。 |
| CC-TEST-011 | 失败与异常恢复 | 业务抛错或 `success=false` 时不留部分业务记录/成功幂等项；同请求可安全重试；锁等待、事务超时/serialization retry 不遗留永久处理中记录。 |
| CC-TEST-012 | 同键不同内容 | 指纹不同请求不被幂等层拦截，进入对应 API 动作规则；API07 同产品编码不同货主为不同 Ginlong 业务键；验收只核对接口幂等行为，不推导或修改 WMS 模型全局唯一约束。未获确认的动作语义场景为 BLOCKED。 |
| CC-TEST-013 | 各 API 限流窗口与配置 | 验证 Odoo 后台可分别修改并保存四个 API 阈值；在单一 UTC 秒窗口中，同一调用方的 API01/03/05 各自前 10 次通过、第 11 次 429，API07 前 100 次通过、第 101 次 429；均返回 `Retry-After`。修改阈值后在对应 API 下一秒窗口生效，跨秒后该 API 计数重置。 |
| CC-TEST-014 | 四 API 多 Worker 原子性与隔离 | 在实际 Odoo 多 Worker HTTP 环境竞争各 API 的计数行，许可数不超过相应阈值；API01/03/05/07 计数相互独立；记录唯一冲突、serialization failure、重试及错误；不得依赖进程内状态/缓存或 Redis。 |
| CC-TEST-015 | 调用方身份与日志 | 按认证后的 `request.api_user.id` 与 API 代码分别限流，不受伪造 IP 头影响；429 HTTP 状态、`Retry-After` 与既有日志 code/status 一致。 |
| CC-TEST-016 | API07 100 次/秒多 Worker 并发性能 | 通过实际 Odoo HTTP API、多个 Worker 和单一认证调用方，在同一 UTC 秒窗口同时并发提交 101 个不同且有效的 API07 产品请求；验证恰有 100 个获得许可、其余 1 个返回 429。记录 Worker 数、并发数、实际窗口、吞吐/响应时延、事务冲突、serialization failure、重试次数及错误。使用可清理的测试数据并通过 ORM 清理。若 101 个请求未落入同一窗口、成功许可数不为 100、发生意外 5xx/重试耗尽/重复副作用或超限放行，标记 BLOCKED/FAIL；不得宣称通过。未批准时延 SLA，不以时延数值单独判 PASS/FAIL。 |
| CC-TEST-017 | 成功事务原子提交 | 验证业务记录、成功响应及幂等记录同属一个 Odoo 请求事务；事务提交后可查询到三者，事务提交失败时三者均不可见；提交前不得宣称成功。 |
| CC-TEST-018 | 业务失败回滚及重试 | 注入业务异常和 `success=false`，验证业务写入及幂等成功行一并回滚、错误由现有日志记录；随后重发相同请求可完整执行并提交，不残留半成品或处理中状态。 |
| CC-TEST-019 | 提交后响应丢失 | 在业务与幂等数据提交成功后丢弃/模拟丢失 HTTP 响应，再重发完全相同请求；验证返回已保存原响应且业务副作用仅发生一次。另覆盖原事务尚未完成时重复请求等待仲裁：原事务提交则重放，回滚则等待请求接手。 |
| CC-TEST-020 | API01 UPDATE/DELETE | UPDATE 使用现有入库订单模型写入逻辑；DELETE 仅把目标订单状态改为 `cancel`，订单及相关原始记录均保留，不调用 `unlink()` 或触发 picking 删除；再次 DELETE 返回成功且不产生额外副作用。 |
| CC-TEST-021 | API03 UPDATE/DELETE | UPDATE 使用现有出库订单 `write()` 逻辑；DELETE 仅把目标订单状态改为 `cancel`，订单及相关原始记录均保留，不调用 `unlink()` 或触发 picking 删除；再次 DELETE 返回成功且不产生额外副作用。 |
| CC-TEST-022 | API05 UPDATE/DELETE | UPDATE 复用现有盘点任务模型；DELETE 将任务状态设为 `cancel`，保留任务和明细记录；再次 DELETE 返回成功且不产生额外副作用。验证状态字段位于现有任务模型，不新建盘点模型。 |
| CC-TEST-023 | API07 UPDATE | UPDATE 复用现有 `product.product` upsert/写入路径并按 `owner + productCode` 定位；不物理删除产品、不擅自归档产品。API07 DELETE 未经契约确认不纳入本 CC，也不阻塞已确认的新增/修改验收。 |

每个接口必须覆盖其批准的全部必需字段和核心行为；若字段/行为缺失或未实际验证，状态为 BLOCKED/NOT RUN，不用局部映射或 Mock 结果声称真实外部契约通过。API07 性能验收必须使用真实 Odoo 多 Worker HTTP 路径，单 Worker 或 ORM 单元测试不能代替。ATR/IHR 应分别维护“手动回传”和“入站幂等/限流”结果分区，并记录各自执行命令、环境、Worker 数、测试运行编号、代码指纹及原始结果。CC-TEST-016 未完整执行或其并发/错误指标不符合上述条件时，入站限流项不得标记 PASS。此 Draft 本身不授权执行这些测试。

本次修订不改变 CC-TEST-010、CC-TEST-017、CC-TEST-019 的原始事务边界和验收要求；其剩余测试继续按本节原标准完成并如实记录 PARTIAL/BLOCKED，不能因回传提案或 API10 模型未定位而延期或降级。

### 6.3 `worlddepot` 保留功能回归与删除影响记录

| 测试 ID | 范围 | 验收条件 |
|---|---|---|
| CC-TEST-024 | 项目相关 `worlddepot` 修改/精简/删除 | 每项删除前核对 manifest 依赖、import/XML 引用、模型/字段关系、菜单/动作/视图、路由和实际调用路径，并将核查结论记入 IHR。对本项目保留并受改动影响的 Order、客户盘点指令/实盘结果、API User/Token、入库/出库处理、Odoo `stock.picking`/`stock.move.line` 交接、共享 API 认证/日志和相关界面执行自动化回归；只在这些保留路径回归通过后判定通过。记录重要删除项及影响；已明确移除的项目外功能作为范围移除，不伪记为 PASS/FAIL。不得扩大为无关重构。 |

CC-TEST-024 与各 API 功能验收分别记录；删除未使用代码的静态引用检查不能替代受影响保留 WMS 路径的自动化回归。

## 7. 停止条件

1. 如实现需要自行确定字段含义、objectid、错误处理、重复/幂等规则、分批语义或额外业务状态检查，先暂停该接口并取得确认/需求变更。
2. 如现有 WMS 记录无法支持某个按钮的批准字段，记录具体字段和依赖；只阻塞直接受影响接口/场景，不静默丢字段、不造映射模型。
3. 如果发现 SRS/TDD 与本稿冲突，先处理上游变更；本 CC 不覆盖或更改冻结 SRS/TDD。
4. 若场景依赖货主解绑或托盘生命周期，按项目必需后续需求管理，不把依赖标成完成，也不因此宣称整个项目闭环已完成。
5. Ginlong 外部测试/正式接口未经授权与环境确认不得调用；外部资料和模板同步状态不得伪记为 PASS。
6. 若 Odoo ORM 唯一冲突、Repeatable Read 快照、Worker 超时或计数行并发更新异常不能按 TDD 方案恢复，暂停受影响实现；不得改用直接 SQL、进程内锁/缓存或客户端 IP 头规避。
7. API10 两个模型尚未完成 ORM 安装/读取验收时，仅暂停 API10 实绩读取和回传；不得阻塞 API02/04/06/08 已具备条件的实现及测试。

## 8. 冻结与完成条件

CC-GIN-003 v1.1 经李建强 Human Review `APPROVED` 后于 2026-11-17 冻结为 `Frozen with Open Items`，并授权本 CC 剩余实施与自动化测试。实施范围限本地开发、Odoo ORM/测试及 Mock HTTP；不访问真实 Ginlong 或生产环境。API10 专属阻塞不扩散到 API02/04/06/08。项目模板源同步仍为 `BLOCKED`；沿用已批准流程例外，不将其标记为 Passed。

CC 完成需分别形成五个手动回传接口、四个入站接口及 `worlddepot` 保留功能回归的测试结果分区，并覆盖 §6.1–§6.3。API07 100 次/秒真实多 Worker HTTP 并发性能测试未完成或未满足标准时，限流验收不得标记 Passed。CC-TEST-010/017/019 的剩余事务子项必须继续按原标准完成；涉及 `worlddepot` 的重要删除及影响须记入 IHR。外部协议、API03 正式方向、API07 DELETE 契约及 API10 实盘模型映射等 Open Items 按接口/场景隔离管理，不因 CC 冻结而伪记解决。

## 附录：版本记录

| 版本 | 日期 | 状态 | 说明 |
|---|---|---|---|
| v0.1 | 2026-11-17 | Draft | 按 Implementation Plan 阶段 2 准备五个手动回传接口的契约草稿；不冻结、不授权编码。 |
| v0.2 | 2026-11-17 | Draft | 根据用户确认 API01/03/05/07 业务键，扩展范围包含四个入站接口幂等与多 Worker 限流；记录 ORM 原子事务/唯一约束、Odoo Repeatable Read 冲突恢复、429/Retry-After 与现有日志适配方案和 TDD 变更建议。未修改业务代码、未重跑测试、未冻结、未授权编码。 |
| v0.3 | 2026-11-17 | Draft | 按新增限流约束改为每调用方一行的 PostgreSQL ORM 计数器，默认 10 次/秒且可配置；明确固定 UTC 秒窗口、跨 worker 并发冲突的新 cursor 有界重试、429/Retry-After 及并发/窗口切换/恢复测试。模板状态仍 BLOCKED；未修改代码、未运行测试、未冻结、未授权编码。 |
| v0.4 | 2026-11-17 | Draft | 按用户确认改为每个 API 独立限流与配置：API01/03/05 默认 10 次/秒、API07 默认 100 次/秒；计数器唯一键改为调用方/API 复合键，更新并发隔离及测试条件。模板状态仍 BLOCKED；未修改代码、未运行测试、未冻结、未授权编码。 |
| v0.5 | 2026-11-17 | Draft | 按评审补充幂等与业务写入的原子事务、失败回滚/成功提交/提交后响应丢失处理及测试；明确接口业务键不改变 WMS 全局唯一规则；确认 UTC 固定一秒限流窗口；增加 API07 100 次/秒真实多 Worker HTTP 并发验证和冲突/重试/错误记录；将手动回传与入站验收分区记录。仅修改文档，未编码、未测试、未冻结。 |
| v0.6 | 2026-11-17 | Draft | 明确 UPDATE 复用现有 WMS 写入逻辑，DELETE 对 API01/03/05 仅置 `cancel`、不物理删除并覆盖重复删除幂等；逐接口记录当前模型/服务支持差异，API05 状态仅建议扩展现有任务模型；排除 `audit_log` 开发、修改和专项测试；补充对应验收项。仅修改文档，未编码、未测试、未冻结。 |
| v1.0 | 2026-11-17 | Frozen with Open Items | Human Review APPROVED；冻结 v0.6 Draft 全部技术方案、测试标准和 Open Items，并授权编码与自动化/集成测试。项目模板源同步仍 BLOCKED，依据既有用户批准例外冻结，不记为通过。 |
| v1.1 | 2026-11-17 | Frozen with Open Items | Human Review `APPROVED`；按评审条件修订并冻结。明确三系统职责及 API02/08、API04/06、API10 数据来源；API06 不增加状态门禁、审批或业务限制。API10 不得使用 `stock.quant`，经源码及 ORM 确认 `worlddepot` 缺少两种盘点模型，授权在 WDepot 内最小扩展，不建 Ginlong 平行模型。Wizard 仅显示业务数据，JSON 后台生成；用户不查看/编辑 JSON。记录项目范围内 worlddepot 改动及保留功能回归；新增 CC-TEST-024，保留 CC-TEST-010/017/019 原标准。模板同步继续 BLOCKED；外部协议未决及未执行测试不标 PASS。授权本地及 Mock HTTP 实施，不访问真实 Ginlong/生产。 |
