<!-- CC-GIN-003 v1.0 Frozen with Open Items：Human Review APPROVED；已授权编码与自动化测试。项目 CC 模板同步仍 BLOCKED，沿用已批准的流程例外但不记为 Passed。 -->

# Coding Contract：CC-GIN-003

## 文档状态

| 项目 | 内容 |
|---|---|
| CC ID | CC-GIN-003 |
| 版本 | v1.0 Frozen with Open Items |
| 当前状态 | Frozen with Open Items；Human Review APPROVED |
| 本 CC 候选范围 | API01/03/05/07 入站幂等与限流；API02/04/06/08/10 手动回传 |
| 上游基线 | SRS v1.0 Frozen；TDD v0.3 Frozen with Open Items（需提出变更）；Implementation Plan v1.0 Frozen |
| 前序 CC | CC-GIN-002 v1.0 Closed；ATR-RUN-009 为最终有效测试基线 |
| 项目架构认知 | [PROJECT_COGNITION.md](../context/cognition/PROJECT_COGNITION.md) v1.6 |
| Human Review | 李建强；2026-11-17；APPROVED（用户明确指示） |
| 模板同步 | BLOCKED：项目模板来源缺失；沿用用户批准的流程例外作评审准备，不代表同步通过 |
| 授权 | 已授权依本 CC 实施业务代码及执行规定的自动化/集成测试 |

本文件是 CC-GIN-003 v1.0 Frozen with Open Items。Human Review 已批准 v0.6 Draft，现按批准内容冻结；用户同时授权进入代码实施和测试。本 CC 将四个入站 API 的幂等、限流及 UPDATE/DELETE 处理与五个回传接口合入同一范围，但两组功能的依赖、验收及结果记录分别列明。外部协议、API03 正式方向、API07 DELETE 契约及模板同步等 Open Items 保留原状态。

## 1. 目标与三系统职责

本 CC 候选范围涵盖四个 Ginlong 入站接口的幂等/限流，以及五个由 Odoo 用户手动触发的回传接口。完整数据流保持：Ginlong 下达业务指令 → Odoo 接收订单并转发给 Karl Rapp → Karl Rapp 执行实际仓库作业 → Odoo 根据 Karl Rapp 返回的实际执行结果，使用现有 `stock.picking` 记录执行与库存变化 → 用户从相应 Odoo 业务订单按钮将结果回传 Ginlong。

Odoo 是业务记录及数据交换枢纽，不重新开发 WMS。Order 记录业务指令，`stock.picking` 记录实际执行；两者不建立强制关联，按订单标识及实际业务数据核对。回传来源使用现有 WMS 订单/执行记录，不将下达指令视为仓库执行完成。

## 2. 范围

### 2.1 候选接口与数据来源

| 接口 | 业务事件 | Odoo 按钮所在单据 | Payload 数据来源 | 边界 |
|---|---|---|---|---|
| API02 | 收货确认 | 入库 `order` | 入库订单（`inbound.order`）收货数据 | 只回传订单已有的收货业务数据；不将按钮点击解释为额外的实际库存记账 |
| API04 | 入库完成 | 入库 `order` | 实际入库完成的 `stock.picking` 数据 | 依据现有 WMS 执行记录；不假设一张订单只对应一个 picking |
| API06 | 备货完成 | 出库 `order` | 出库订单（`outbound.order`）备货完成数据 | 备货完成与实际发货是不同事件，不据此表示货物已离仓 |
| API08 | 发货完成 | 出库 `order` | 实际离仓的 `stock.picking` 数据 | 依据 Karl Rapp 返回并由现有 WMS 记录的实际执行数据 |
| API10 | 盘点完成 | `count.order` 盘点业务单据 | 独立盘点任务及其采集结果 | 盘点采集结果不等于库存调整；遵循已冻结 TDD 的盘点隔离边界 |

五个按钮都在对应 Odoo 订单表单上：API02/04 在入库订单，API06/08 在出库订单，API10 在 `count.order`。Payload 的接口字段须覆盖 SRS v1.0 已批准字段及后续确认的 Ginlong 契约；不得因外部资料未齐而静默省略 SRS 已明确字段。若所需的核心字段、事件数据或接口契约确实无法实现，该受影响接口标记 BLOCKED，不以部分字段或 Mock PASS 代替完整验收。

### 2.2 明确排除

- 不重写 API01/03/05/07 已有字段映射及 WMS 主业务流程；本 CC 只按 Ginlong 契约补齐 UPDATE/DELETE 操作接入既有模型能力，并增加幂等/限流保护。API09 库存查询不属于本 CC。
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
| API05 | `countOrderNo` | 当前映射到独立 `ginlong.stocktake.task`；服务按项目和盘点单号查找删除目标；模型字段仅 `index=True`，未声明唯一约束 |
| API07 | `owner + productCode` | 当前 `services.api07` 只按 `default_code=productCode` 查找产品，未将 owner 纳入识别条件；需按确认的复合键修订 TDD 设计，复用 `product.product` 扩展字段，不默认新建产品映射模型 |

表中业务键是 Ginlong 接口幂等判定使用的外部业务标识，不代表对应 Odoo/WMS 模型必须对该字段或字段组合施加全局唯一约束。幂等记录自身仅对 `(api_code, business_key, request_fingerprint)` 建立防重复约束；本 CC 不增删或改变 `inbound.order`、`outbound.order`、盘点、`product.product` 等 WMS 模型现有唯一性规则，也不以接口幂等需求为由新增业务唯一校验。

### 2.4 UPDATE/DELETE 与现有模型支持情况

以下结论来自当前 `services.py`、控制器及对应 WMS 模型源码。Ginlong 接口操作语义与模型能力分别判断；本 CC 不据接口业务键新增模型全局唯一规则。

| API | 当前 UPDATE 支持 | 当前 DELETE/取消支持 | 本 CC 处理要求 |
|---|---|---|---|
| API01 入库单 | `services.api01` 当前没有 UPDATE 分支，只支持 CREATE/DELETE；现有 `world.depot.inbound.order` 可通过 ORM `write` 修改，但未发现 Ginlong 专用更新服务。 | 当前服务调用 `order.unlink()`；模型有 `cancel` 状态和 `action_cancel()`，但该方法对已取消单据报错，并可能删除关联的未完成 `stock.picking`；模型还允许特定状态下物理删除订单。 | UPDATE 按已批准字段映射使用现有入库模型修改逻辑；DELETE 只把订单状态写为 `cancel`，保留订单及相关原始记录，不调用 `unlink()` 或带有删除拣货副作用的 `action_cancel()`。已取消记录再次 DELETE 返回幂等成功。 |
| API03 出库单 | `services.api03` 当前没有 UPDATE 分支，只支持 CREATE/DELETE；现有 `world.depot.outbound.order.write()` 可用于修改，并保留其现有日期换算逻辑。 | 当前服务调用 `order.unlink()`；模型有 `cancel` 状态和 `action_cancel()`，但该方法对已取消单据报错，并可能删除关联的未完成 `stock.picking`；模型还允许特定状态下物理删除订单。 | UPDATE 复用现有出库模型 `write()`；DELETE 只把订单状态写为 `cancel`，保留订单及相关原始记录，不调用 `unlink()` 或带有删除拣货副作用的 `action_cancel()`。已取消记录再次 DELETE 返回幂等成功。 |
| API05 盘点单 | `services.api05` 当前没有 UPDATE 分支；现有 `ginlong.stocktake.task` 可通过 ORM `write` 修改其任务字段，没有专用更新方法。 | 当前服务调用任务 `unlink()`；模型没有状态字段或取消方法，物理删除还会级联删除明细。 | UPDATE 复用同一现有任务模型的 ORM 修改；为保留盘点任务，最小扩展该模型的状态字段以支持 `cancel`，DELETE 仅改状态、不删任务或明细；已取消任务再次 DELETE 返回幂等成功。不新增第二套盘点模型。 |
| API07 产品档案 | 当前 `services.api07` 已执行原生产品 upsert：存在产品时对 `product.template`/`product.product` 调用 `write()`，不存在时创建产品；目前按 `default_code` 查找，未将 owner 纳入查找。 | 当前 API07 没有 DELETE 动作分支或订单状态字段；不能套用订单 `cancel` 语义。 | UPDATE 复用现有产品写入/upsert 流程，并按已确认的 `owner + productCode` 键修订定位。除非 Ginlong 后续契约明确产品删除/停用规则，本 CC 不实现 API07 DELETE，不物理删除或擅自归档产品。 |

**DELETE 幂等规则：**对 API01/03/05，找到的记录若已处于 `cancel`，重复 DELETE 返回成功结果且不再改动数据；未找到或查找结果歧义仍按现有接口错误处理，不伪造已取消记录。首次 DELETE 仅修改目标订单/任务状态，不调用物理 `unlink()`。UPDATE 使用已批准契约字段并复用对应模型既有 `write()`；不自行补造字段映射或额外业务校验。

完全相同请求的判定还需内容指纹：API code、上述业务键、规范化请求内容。相同业务键但内容不同必须进入接口动作处理；幂等层不得直接返回旧结果或拒绝合法更新。UPDATE 复用对应模型现有修改逻辑；API01/03/05 DELETE 按 §2.4 保留原业务记录并只取消对应订单/任务状态。API03 其他操作限制及 API01/03/05 的字段更新映射按已批准契约执行；API07 按产品档案新增/修改契约处理，其 DELETE 不在当前确认范围。此段不补造各动作的外部响应及冲突语义。

### 2.5 源码现状核对

本次只读检查确认当前模块没有通用幂等表、请求指纹、重复请求结果复用或 API 限流实现，也没有请求级防抖。四个入站控制器均使用 `worlddepot` 的 `validate_token` 与 `api_logger`；前者在 Token 验证后提供 `request.api_user`，后者使用既有 `world.depot.api.log` 并通过短独立 cursor 写日志。Odoo HTTP dispatcher 会在主事务出现 serialization/deadlock 时重跑 route；当前 logger 每次 route 执行都会独立新建日志，故并发重试可能造成重复或过早的日志结果。当前没有任何限流计数/锁，且日志中的 `request_source` 是远端地址字段，不能将其当作可信限流身份。

具体代码证据：[`ginlong_controller.py`](../../mymodules/ginlong_apis/controllers/ginlong_controller.py)、[`services.py`](../../mymodules/ginlong_apis/services.py)、[`wms_extensions.py`](../../mymodules/ginlong_apis/models/wms_extensions.py)、[`ginlong_models.py`](../../mymodules/ginlong_apis/models/ginlong_models.py)、[`inbound_order.py`](../../mymodules/worlddepot/models/inbound_order.py)、[`outbound_order.py`](../../mymodules/worlddepot/models/outbound_order.py)、[`validate_token`](../../mymodules/worlddepot/controllers/validator_token.py)、[`api_logger`](../../mymodules/worlddepot/controllers/api_logs.py)、Odoo [`sql_db.py`](../../odoo/sql_db.py)。Odoo 18 cursor 使用 `REPEATABLE READ`；HTTP 层对 serialization/deadlock 等并发异常有既有事务重试。API01 当前 Ginlong 服务只实现 CREATE/DELETE，DELETE 调 `unlink()`；入库模型有 `cancel` 状态及 `action_cancel()`，但取消方法会拒绝重复取消且在特定情况下删除未完成 picking，模型另允许特定状态的订单物理删除。API03 当前服务同样只实现 CREATE/DELETE、DELETE 调 `unlink()`；出库模型有 `cancel` 状态及相同类型的关联未完成 picking 删除副作用。两者现有 ORM `write()` 能力可供 UPDATE 使用，但 Ginlong 服务无专用 UPDATE 分支。API05 当前服务只实现 CREATE/DELETE，DELETE 物理删除任务；`ginlong.stocktake.task` 有通用 ORM `write()`，但没有状态字段/取消方法。API07 当前已对原生产品执行 upsert/`write()`，但按 `default_code` 查找而非 owner+code；没有订单状态或 DELETE 分支。仓库现有字段变更跟踪模块位于 `mymodules/auditlog`；本 CC 不改其规则或实现，不做专项测试。API01 现有约束是在同一 project 内检查非取消单据的 reference，不是数据库唯一约束；API03 模型未找到对应 reference 唯一规则；API05 盘点号未加唯一约束。这些 WMS 现状不因接口业务键而修改。

## 3. 已确认行为与外部依赖

### 3.1 已确认行为

1. 每个回传只能由用户点击对应 Odoo 订单上的按钮触发；按钮一次同步调用一个对应接口。
2. 调用设置合理超时；本 CC 不自动重试。失败后只能由用户再次点击发起重试。
3. 点击后读取当前业务订单及适用的实际执行/盘点结果，按已批准字段组装 JSON，调用 Ginlong API，使用 `worlddepot` 现有 API 日志能力记录操作、请求、响应或错误，并向用户显示结果。
4. 本期仅进行权限、安全、数据完整性及格式校验。不得擅自添加订单状态门禁、重复回传规则、业务审批或其他业务检查。
5. 使用现有 Odoo WMS 用户组、认证/权限、配置入口及 API 日志；日志中不记录 Secret、Token 等凭据。业务 Payload 不整体脱敏。
6. API04/08 表达实际执行结果，数据以 Odoo `stock.picking` 中记录的实际结果为准。Order 与 picking 松耦合，按业务数据核对。
7. API06 仅表达备货完成，不得当作实际发货完成。API10 只回传独立盘点任务和采集结果，不修改库存。

用户提供的 Ginlong 资料给出测试环境基础地址 `http://10.0.3.182:8003/API/WMS_JSON/{objectid}`、正式环境基础地址 `http://10.0.3.182:8001/API/WMS_JSON/{objectid}`，并说明当前接口无鉴权/Key。V3.2 对照核对记录见[参数核对记录](../ginlong_apis/V3.2参数核对记录.md)及[原始工作簿](../ginlong_apis/海外WMS与第三方系统集成V3.2.xlsx)：请求/返回字段表与 V3.1 未见字段变更，但每个 API 的 `objectid`、方法/报文格式、完整响应与错误语义及各事件字段仍须逐项补齐/确认；不在本 Draft 中猜定，也未进行网络调用。

新增的幂等/限流需求依据本次项目用户明确决定：API01/03/05/07 分别以 `inboundOrderNo`、`outboundOrderNo`、`countOrderNo`、`owner + productCode` 为 Ginlong 接口业务键；完全重复的已成功请求复用原结果，失败可重试，差异内容按该 API 动作处理。接口业务键用于集成幂等，不等同于 WMS 模型全局唯一约束，本 CC 不改变现有 WMS 业务唯一性规则。限流按认证后的 API user 和 API 分别计数，阈值独立配置：API01/03/05 默认每秒 10 次，API07 默认每秒 100 次；状态须由 PostgreSQL 持久化并通过 Odoo ORM 并发原子更新，超限返回 HTTP 429 和 `Retry-After`。窗口采用 UTC 固定一秒，不使用滚动窗口或令牌桶。上述要求需要纳入适用的 SRS/TDD 变更基线；本稿不修改冻结 SRS/TDD。

### 3.2 待外部确认或待基线评估

| 事项 | 当前状态及处置 |
|---|---|
| 五个接口各自的 objectid、字段/类型/必填性、操作枚举及响应/错误格式 | 对照 Ginlong 最新 V3.2 资料逐接口核对；未确认的细节不得推定。SRS 已明确字段仍须覆盖；受缺失契约阻塞的接口/场景单独 BLOCKED。 |
| API03 方向 | 仍为 SRS A-003 开发假设，Ginlong 尚未正式确认；不作为已确认外部契约。本 CC 不更改 API03 方向。 |
| API04/API08 分批执行、一次订单多张 picking 的聚合/标识规则 | Order 与 picking 松耦合；按确认的接口契约和业务标识处理。未确认时只阻塞依赖该规则的场景，不擅自聚合或设唯一关系。 |
| API02/API06 订单数据何时代表相应业务事件 | 复用现有 WMS 数据；除权限、安全、完整性和格式外不新增状态门禁。任何需新增的检查须走需求变更。 |
| API10 部分盘点、重复回传、结果未知、撤销及采集完成语义 | 遵循已确认契约；不自行制定幂等/重复规则、库存差异处理或完成门禁。 |
| 货主解绑、托盘生命周期 | 项目必需需求，但不属于 CC-GIN-002；需由独立 CC/后续阶段建立批准基线。受其直接影响的回传场景单独列为依赖。 |
| 本地开发环境 URL/实际网络联调 | 仅在明确批准联调和环境可用后执行。当前地址信息不等于已执行 HTTP E2E。 |
| 项目 CC 模板同步 | BLOCKED；沿用已批准的模板缺失流程例外准备本稿，检查仍为 BLOCKED。 |

## 4. 技术边界

- Odoo 标准按钮方法中同步执行：读取现有单据 → 组装 JSON → 调用对应 Ginlong API → 写入既有 API 日志 → 显示结果。
- 五个手动回传按钮不增加事务调度或独立游标设计，遵循普通 Odoo 按钮调用及现有事务行为；入站限流的短 ORM 事务按 §4.2 处理。
- 复用既有 HTTP/配置/认证能力（出站是否无需认证以用户提供的 Ginlong 资料为准）、权限和日志能力；仅在证明现有能力不足且经批准后作最小扩展。
- 不新增业务订单、库存、盘点、回传 attempt 或 API 日志模型；不新增技术状态机和监控体系。仅评估本次明确要求的轻量幂等记录及限流计数模型，不扩展为通用集成平台。
- 不使用 `stock_barcode`。数据库检查只通过现有 Odoo Shell 与 ORM，禁止 SQL/直接 PostgreSQL；使用现有 `odoo.conf`、`venv` 和 `odooce_karlrapp`。
- API10 复用独立盘点任务与采集结果模型，不触碰库存账。

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

## 5. TDD 变更建议（尚未修改冻结 TDD）

冻结的 TDD v0.3 §3.2.1、§3.2.2、§3.3、§4、§8–10、§11、§15、§18–19 与本次确认的接口业务键及幂等/限流要求存在缺口或冲突；其中 §10 仍将重复规则留待外部确认，§4 不新增 WMS 业务唯一约束。建议起草 TDD v0.4 Draft，至少：

1. 固化 API01/03/05/07 的 Ginlong 接口业务键，并明确它们仅供集成幂等使用；不得据此增加、删除或改变 `inbound.order`、`outbound.order`、盘点模型或 `product.product` 的全局唯一约束/现有业务校验。API07 按 `owner + productCode` 映射现有 `product.product`；若现有数据结构无法无歧义支持该映射，记录并阻塞受影响场景，先走需求/设计变更，不擅改 WMS 主数据唯一性。
2. 增加轻量幂等模型的字段、`(api_code, business_key, fingerprint)` 唯一约束、指纹规范化、成功响应重放及失败回滚重试规则；不存原始请求正文或凭据。
3. 明确 UPDATE 复用现有 WMS 业务修改逻辑，不另建一套更新模型/服务。API01/03 当前 Ginlong 服务没有 UPDATE 分支，但现有订单模型支持 `write()`；API05 复用现有 `ginlong.stocktake.task` 的 ORM 修改能力。明确 API01/03 DELETE 只将订单 `state` 写为 `cancel`，不调用物理 `unlink()`，也不调用会删除未完成 picking 的现有 `action_cancel()`；重复 DELETE 已取消记录返回成功。API05 在同一既有任务模型上增加支持 `cancel` 所需的最小状态字段，不删除任务或明细。API07 复用现有产品 upsert/`write()`，不套用订单取消规则；除非外部契约明确，产品 DELETE 不实现。对上述操作不修改其他 WMS 界面/业务既有取消行为。`audit_log` 字段变更跟踪仅复用，不开发、不修改、不专项测试。
4. 明确失败/`success=false` 时业务写入与幂等行在同一 savepoint 回滚且允许重试；成功业务记录、成功响应和幂等行在同一 Odoo HTTP 请求事务原子提交；唯一冲突回滚 savepoint 后用新 ORM cursor 读取已提交结果；提交失败不留下任一半成品；提交后响应丢失时相同请求重放原结果。覆盖 Odoo `REPEATABLE READ`、flush 时点、serialization/deadlock 既有重试，且不建持久处理中状态。
5. 增加以认证 `world.depot.api.user` 为身份、按 API 分开的多 Worker 限流：API01/03/05 默认 10 次/秒，API07 默认 100 次/秒，各自可配置；使用每个调用方/API 组合一行的 PostgreSQL ORM 计数器及复合唯一约束。固定采用 UTC 对齐的一秒窗口，不设计滚动窗口或令牌桶。说明每 API 窗口阈值快照、短 ORM 事务、serialization/首次建行冲突时以新 cursor 有界重试、HTTP 429 与 `Retry-After`。禁止进程内计数器/缓存、Redis、直接 SQL 及伪造 IP 头。
6. 规定 API07 在真实 Odoo HTTP 多 Worker 环境下，以同一认证调用方在一个 UTC 秒窗口并发提交 100 个不同有效产品请求，并额外提交第 101 个请求，验证 100 个在限额内获准、超限请求为 429。记录 worker 数、并发/到达窗口、吞吐与响应时延、数据库唯一冲突/serialization failure、重试次数、HTTP 错误和限流错误；不虚构未批准的延时 SLA。请求未实际落入同一秒窗口、发生非预期 5xx/重试耗尽/数据重复或许可数超限时，标为 BLOCKED/FAIL，不得宣称性能验证通过。
7. 为 HTTP 429 对共享 `api_logger` 提出最小兼容变更，继续复用现有日志模型/权限；明确独立日志记录不代表业务事务提交。检查 Odoo 主事务并发重试时的日志时序，评估用 `request` 生命周期内的日志记录 ID 更新同一条现有日志，避免每次 framework retry 新增重复记录，不新增日志字段/模型/状态。
8. 明确幂等记录保留期及不同内容并发时的顺序语义。SRS v1.0 的重复/幂等 OPEN 项及新增限流需求、Implementation Plan v1.0 的阶段/CC 映射均需通过正式变更/追踪更新；本稿不覆盖冻结 SRS/TDD/Plan。五个手动回传接口与四个入站接口的测试、问题和 PASS/BLOCKED 结论须分区独立记录，不得用一组结果替另一组背书。

以上均是待评审的技术方案，不是已批准实现基线。外部字段映射/响应语义、不同内容并发到达顺序及幂等保留期尚未在本稿中擅自确定。

## 6. 候选自动化/组件验收

本 CC 如获批准，验收以现有 Odoo 标准自动化与 ORM/组件集成为主，所有出站 HTTP 均使用测试替身，不访问 Ginlong 网络。完整人工 WMS 操作和三系统 E2E 留最终集成 CC。

### 6.1 五个手动回传接口

下表只记录 API02/04/06/08/10 手动回传验收。其状态、缺陷、证据和结论须在 ATR/IHR 的回传验收分区独立记录，不与入站幂等/限流验收合并判定。

| 测试 ID | 接口/边界 | 验收条件 |
|---|---|---|
| CC-TEST-001 | API02 | 按入库订单数据组装已批准字段；按钮方法仅在调用时发出一次 Mock HTTP；操作/响应写入现有日志；不改变库存或确认额外实际执行。 |
| CC-TEST-002 | API04 | 从实际入库 `stock.picking` 读取并映射确认字段；覆盖订单与实际 picking 松耦合及必要的多次执行场景（仅在契约已定义时）；不由回传按钮执行库存操作。 |
| CC-TEST-003 | API06 | 从出库订单读取备货完成数据；证明该回传不会被表达/处理成实际发货或库存扣减。 |
| CC-TEST-004 | API08 | 从实际离仓 `stock.picking` 读取并映射数据；不强制 Order/picking 外键或单一 picking；不由集成按钮执行库存扣减。 |
| CC-TEST-005 | API10 | 从独立 `count.order`/盘点任务及采集结果生成字段；不读写 `stock.quant`/`stock.move`，不创建库存调整；操作和结果写现有日志。 |
| CC-TEST-006 | 共用按钮调用 | 五接口均只在显式按钮调用时发出一次 Mock 请求；按钮/单据状态变化、cron、安装升级和重启不触发请求；超时/错误不会自动重试，错误向用户反馈。 |
| CC-TEST-007 | 权限、日志与基线 | 复用既有权限及 API 日志；无权限不得发送请求；凭据不进入日志；模块可在指定开发环境升级，相关 Odoo 自动化/ORM 组件套件通过。 |

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

## 7. 停止条件

1. 如实现需要自行确定字段含义、objectid、错误处理、重复/幂等规则、分批语义或额外业务状态检查，先暂停该接口并取得确认/需求变更。
2. 如现有 WMS 记录无法支持某个按钮的批准字段，记录具体字段和依赖；只阻塞直接受影响接口/场景，不静默丢字段、不造映射模型。
3. 如果发现 SRS/TDD 与本稿冲突，先处理上游变更；本 CC 不覆盖或更改冻结 SRS/TDD。
4. 若场景依赖货主解绑或托盘生命周期，按项目必需后续需求管理，不把依赖标成完成，也不因此宣称整个项目闭环已完成。
5. Ginlong 外部测试/正式接口未经授权与环境确认不得调用；外部资料和模板同步状态不得伪记为 PASS。
6. 若 Odoo ORM 唯一冲突、Repeatable Read 快照、Worker 超时或计数行并发更新异常不能按 TDD 方案恢复，暂停受影响实现；不得改用直接 SQL、进程内锁/缓存或客户端 IP 头规避。

## 8. 冻结与完成条件

本 CC v1.0 于 2026-11-17 经李建强 Human Review `APPROVED` 后冻结，并依用户明确指示授权编码和自动化/集成测试。项目模板源同步仍为 `BLOCKED`；按已批准流程例外冻结，不将其标记为 Passed。

CC 完成需分别形成五个手动回传接口及四个入站接口的测试结果分区，并覆盖 §6.2 CC-TEST-008–023。API07 100 次/秒真实多 Worker HTTP 并发性能测试未完成或未满足标准时，限流验收不得标记 Passed。外部协议、API03 正式方向、API07 DELETE 契约等 Open Items 继续按 §3.2 和停止条件管理，不因 CC 冻结而伪记解决。

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
