# 实施历史记录：IHR-GIN-003

## 0. 文档治理

| 字段 | 值 |
|---|---|
| CC | [CC-GIN-003 v1.4 最终规则实施与验证增补](CC-GIN-003-v1.4.md)；v1.1 冻结基线及 v1.2/v1.3 历史保留 |
| IHR 版本 | v1.1 |
| TDD 基线 | [TDD v0.7 实施验证修订](../ginlong_apis/TDD-v0.7.md)；v0.4–v0.6 历史保留 |
| 模块 | `ginlong_apis`、`worlddepot` 盘点业务模型与回传界面 |
| 工作类型 | API 幂等/限流、持久化手动回传 Form、盘点双模型及定向自动化测试 |
| 实施负责人 | Codex |
| 开始 / 最后更新 | 2026-11-17 / 2026-11-18 |
| 最新 addon 基线 | ginlong_apis 18.0.2.0.6；ATR-RUN-041–048 记录本轮最终规则、全量 Odoo 自动化及 ORM registry 核验 |
| 当前实施状态 | 本地 CC-TEST-001–024 自动化验收满足，提交 Human Review 关闭评估；五个人工回传使用标准 Form/Notebook，无回传 Wizard |
| 模板同步 | BLOCKED：项目模板来源缺失；沿用已批准例外，不记为通过 |

## 1. CC 基线

本记录执行 [CC-GIN-003 v1.4](CC-GIN-003-v1.4.md) 的当前实施增补，并沿用 [CC-GIN-003 v1.1 Frozen with Open Items](CC-GIN-003-v1.1.md) 冻结验收基线；v1.2/v1.3 作为过程历史保留。手动回传与四个入站接口分别核验，结果见 [ATR-GIN-003](ATR-GIN-003.md)。本 CC 不实施或专项测试 `audit_log`/`auditlog`。

| 范围 | 当前状态 |
|---|---|
| API01/03/05/07 幂等与限流 | 已实施；ATR-RUN-017 的 15 项 Odoo 自动化通过；API01/03/05 默认 10+1、API07 100+1、配置切换、窗口恢复和调用方隔离均经真实四 Worker HTTP 验证 |
| API01/03/05 UPDATE/DELETE；API07 owner+productCode | API07 跨 owner 同码创建、查询和更新通过；受影响 WMS Controller 使用项目 owner 消歧，无法唯一定位时明确报错；API01/03 产品定位通过 |
| 五个人工回传 | 五个业务 Form/Notebook 按钮、Endpoint 配置及现有日志已接入；API02/08 状态、API06 实际托盘/重量和手工覆盖、失败后修改重发、独立追加日志均有 Mock 自动化；混合状态按用户决策阻止发送 |
| API05/10 盘点 | `worlddepot` 内客户盘点订单与实盘结果两个模型已安装；API05 计划写入、API10 实盘读数/关联展示测试通过；不访问 `stock.quant` |
| CC-TEST-024 受影响 WMS 自动回归 | ATR-RUN-043/044/048 自动化通过；完整 WMS 人工 E2E 留最终集成 CC |
| 外部 Ginlong 联调 / 完整 WMS 人工 E2E | 未执行，留最终集成 CC |

## 2. 当前实施状态摘要

| 项 | 状态 |
|---|---|
| 实施进度 | 本地实施和自动化完成；入站保护、UPDATE/DELETE 和多 Worker 限流沿用既有验证；五个人工回传持久化 Form/Notebook 已完成本地 Mock 验收 |
| Preservation Impact | `worlddepot` 的客户盘点订单与实盘结果双模型继续复用；本轮只在既有模型/记录增加必要持久化字段；API05/10 不访问库存账。CC-TEST-024 自动化回归已通过；完整人工 WMS E2E 留最终集成 CC |
| 偏离 | 不新增外部基础设施；五个按钮同步执行设计保留，但协议未决时不触发 HTTP；未改 `stock.picking` 库存流程或 Gateway |
| Stop Condition | 未触发额外业务规则；事务自动化已完成。完整 WMS 人工 E2E 不属于本 CC，留最终集成 CC |
| Open Issues | Ginlong 外部撤销/部分执行语义及真实联调；模板同步 BLOCKED（已批准流程例外）；逐项见 ATR §7 |
| 当前状态 | Ready for Human Review；不自行关闭 |

## 3. 实施历史条目（仅追加）

### IHR-001 — CC 基线与现有实现核对

- 阶段：Implementation
- Action：核对 `ginlong_apis` 的 API01/03/05/07 服务、Token/logger 装饰器、盘点模型、配置 `workers=0`；确认当前没有通用幂等/限流或五个手动回传按钮。
- Files / Components：`mymodules/ginlong_apis/`、`mymodules/worlddepot/controllers/api_logs.py`、`odoo.conf`
- Contract Reference：CC-GIN-003 §§2、6
- Result：Completed；模板同步和 Odoo Engineering 指南来源同步均 BLOCKED，未将 BLOCKED 改写为 PASS。
- Deviation：None
- Follow-up：五个回传 API objectid/字段及共享 TDD 变更依赖继续开放。

### IHR-002 — 幂等、限流及动作实现（进行中）

- 阶段：Implementation
- Action：新增轻量 ORM 幂等结果及固定 UTC 秒窗口计数模型；新增每 API 可配置的 Settings 字段；入站路由按 Token 认证出的 API 用户限流并执行请求指纹幂等。API01/03 UPDATE 使用现有订单 `write()`；DELETE 只写 `state=cancel`；API05 在现有任务模型增加取消状态；API07 以 owner+productCode 定位原生产品。共享 `api_logger` 增加 HTTP Response 最小记录兼容。
- Files / Components：`models/api_control.py`、`models/ginlong_models.py`、`services.py`、`idempotency.py`、`rate_limiter.py`、`controllers/ginlong_controller.py`、`views/res_config_settings_views.xml`、`worlddepot/controllers/api_logs.py`
- Contract Reference：CC-TEST-008–015、017–023
- Upstream Reference：CC-GIN-003 §5（TDD 变更建议尚未合并到冻结 TDD）
- Result：Partial；最新 15 项 Odoo 自动化通过；单进程 HTTP 429/重放通过；真实多 Worker 100/s 和事务提交后响应丢失仍未验收。
- Deviation：None；未修改 `stock.quant`、`stock.move`、`stock_barcode` 或 `auditlog`。
- Follow-up：核对并发事务、API07 多 Worker 100/s，确认 logger 的真实 HTTP 429 行为；依 CC 范围分区记录。

### IHR-003 — 手动回传能力待决

- 阶段：Implementation review
- Action：代码检索未发现 API02/04/06/08/10 按钮或出站客户端；Ginlong `objectid` 与完整调用/响应契约仍未在本地批准资料中确定。本轮未以猜测字段新增回传按钮。
- Files / Components：Ginlong addon 搜索结果、Ginlong V3.2 参数核对记录
- Contract Reference：CC-TEST-001–007、CC §3.2、§7
- Result：BLOCKED（仅此回传范围）
- Deviation：None
- Follow-up：在契约确认后继续，不将部分 Payload/Mock 结果记为通过。

### IHR-004 — 共享日志并发异常传播修复

- 阶段：Implementation / defect correction
- Action：ATR-RUN-004 的 14 项自动化中发现 1 项失败：`worlddepot` 既有 `api_logger` 包装器回滚并吞掉 Odoo 可重试的 PostgreSQL 并发异常。修复仅限共享 logger 对 Odoo 并发重试异常的传播，不改变 API 认证、日志模型或普通错误处理。修复后 ATR-RUN-005 的 14 项测试通过。
- Files / Components：`mymodules/worlddepot/controllers/api_logs.py`、`mymodules/ginlong_apis/tests/test_ginlong_api.py`
- Contract Reference：CC-TEST-011、014、017–019
- Result：修复完成；原失败记录保留；当前 Odoo 自动化基线通过。
- Deviation：未新增日志框架或认证算法。
- Follow-up：真实并发/事务恢复仍需多 Worker HTTP 验证。

### IHR-005 — Odoo 模块升级及 ORM 基线确认

- 阶段：Implementation verification
- Action：在既有 `odoo.conf` 和 `odooce_karlrapp` 上完成模块升级；Odoo Shell ORM 确认 addon 为 installed、模块版本 `18.0.1.2.0`、幂等/限流模型及配置字段注册、阈值 10/10/10/100、普通用户对内部控制模型无 CRUD ACL。ORM 同时确认 `stock_barcode` 状态为 `uninstallable`。
- Files / Components：`ginlong_apis` addon、Odoo module registry / ORM
- Contract Reference：CC-TEST-007、013、020–023
- Result：模块升级和 ORM 检查通过。
- Deviation：未安装或使用 `stock_barcode`；未直接访问 PostgreSQL；未新建数据库/虚拟环境。
- Follow-up：真实调用方权限矩阵及多 Worker 环境仍待验。

### IHR-006 — 多 Worker 启动阻塞

- 阶段：Runtime verification
- Action：使用既有 Odoo 配置/venv/数据库尝试启动 4 个 Worker。子进程在 gevent 启动期间因 `pkg_resources.DistributionNotFound: zope.interface` 退出；检查发现 pip metadata 可见 `zope.interface 8.7`，但 Worker 子进程仍无法解析。未安装或调整依赖，也未修改 `odoo.conf`。
- Files / Components：`odoo.conf`、现有 `venv`、Odoo/gevent Worker 启动路径
- Contract Reference：CC-TEST-010、014、016
- Result：BLOCKED；API07 100/s 验收未执行。
- Deviation：无环境修复，避免超出 CC 范围。
- Follow-up：先在既有环境解决 Worker 对 distribution 的解析问题，再按 CC-TEST-016 原标准测试；不得将单进程 HTTP 结果代替。

### IHR-007 — 单进程真实 HTTP 限流与幂等重放

- 阶段：Runtime verification
- Action：复用现有 Odoo 单进程服务，临时将 API07 阈值设为 1，通过真实 HTTP 在同一 UTC 秒并发提交两个请求，观测一条 HTTP 200 和一条 HTTP 429，429 带 `Retry-After: 1`；既有 API logger 的 ORM 记录对应结果。下一秒提交完全相同请求，返回已保存响应和同一产品 ID。随后通过 Odoo Shell ORM 删除临时 API 用户、Token、产品、日志、幂等及限流记录，并恢复原 API07 阈值 100。
- Files / Components：Ginlong HTTP controller、`worlddepot` Token/logger、`ginlong.api.rate.counter`、`ginlong.api.idempotency`
- Contract Reference：CC-TEST-009、013、015、019（仅实际覆盖部分）
- Result：单进程实际 HTTP 场景通过；不得视为真实多 Worker、API07 100/s 或响应丢失测试通过。
- Deviation：临时测试数据在完成后全部通过 ORM 清理。
- Follow-up：仍需执行 CC-TEST-014/016；另行实现并验证五个回传接口。

### IHR-008 — 多 Worker 启动修复与限流压测

- 阶段：Runtime verification / environment compatibility
- Action：复核失败根因是现有 Python 3.11 环境的 `setuptools 65.5.0` 中 `pkg_resources` 无法按发行包名称解析已安装的 `zope.interface 8.7`；将既有 venv 调整至已验证的 `setuptools 81.0.0` 后，`pkg_resources.get_distribution('zope.interface')` 成功，Odoo 启动 4 个 `WorkerHTTP`。依赖根目录当前被 Git 忽略的 `requirements.txt` 加入本地 pin，未更换 venv、数据库或 Odoo 配置。
- Files / Components：现有 `venv`、`requirements.txt`、`odoo.conf`、gevent `22.10.2`
- Contract Reference：CC-TEST-010、014、016
- Result：四 Worker 启动通过。CC-TEST-016 有效运行在 2026-11-17 10:53:11 UTC：16 个 HTTP 客户端在同一固定秒提交 101 个有效 API07 请求；100 个 HTTP 200、1 个 HTTP 429（`Retry-After: 1`），所有请求始于同一秒，客户端用时约 623 ms，时延 min/p50/p95/max 为 67.323/87.390/141.700/168.068 ms。ORM 核验 100 产品、100 成功幂等行、同一窗口计数 100、101 日志（100 success/200、1 error/429），凭据未进入日志。
- Concurrency evidence：限流器记录 77 个捕获并重试的竞争事件（3 个 `UniqueViolation`、74 个 `SerializationFailure`；retry attempt 1/2/3 分别 51/22/4 次）；无重试耗尽、HTTP 5xx 或客户端错误。数据库日志中的唯一冲突/serialization 是此并发仲裁路径的预期竞争证据，不是未处理请求失败。
- Deviation：首次 101 线程突发运行保留为失败（36×200、65×连接重置、无 429，服务端只接收到 36 个）；改用 16 个独立持久客户端复测，未删除失败记录。另有两次阈值为 2 的无效默认阈值尝试，保留在 ATR-RUN-011。
- Follow-up：按 CC-TEST-016 通过；CC-TEST-010 的真实 HTTP 回滚接管子场景仍需完成。

### IHR-009 — 默认额度、窗口切换与调用方隔离

- 阶段：Runtime verification
- Action：在 4 Worker 服务用单一 API 用户并发测试 API01/03/05 默认阈值；随后通过 `res.config.settings.execute()` 设置 API01=2、在下一 UTC 秒观察生效，再通过原先未设置参数的 ORM 备份恢复并清除缓存。跨秒重放 API01/03/05/07 请求验证新窗口可用。另以两个不同认证 API user、不同伪造 `X-Forwarded-For` 请求 API07。
- Contract Reference：CC-TEST-013–015
- Result：API01/03/05 各同秒 10×200、1×429（`Retry-After: 1`）；API07 的 100×200/1×429 见 IHR-008。设置 API01=2 后下一 UTC 秒为 2×200/1×429；恢复默认后四 API 下一窗口均正常返回 200。两个调用方同秒分别产生计数 2 与 1；同一调用方改变伪造 XFF 后仍共用一行，日志来源均为实际连接地址 `127.0.0.1`，不记录伪造地址或 Token。
- Deviation：早期两个 10+1 尝试仍使用旧 worker 进程缓存的阈值 2；重启四 Worker 后以 10 默认值重测通过。两个错误尝试保留，不覆盖。
- Follow-up：无额外基础设施；限流的固定 UTC 秒窗和认证调用方隔离已按冻结标准验证。

### IHR-010 — 幂等并发、事务及响应丢失

- 阶段：Runtime verification / ORM concurrency
- Action：真实四 Worker 同时提交两份相同 API07 请求；以本机代理接收完整上游 HTTP 响应后丢弃客户端连接，再通过完全相同请求重放；另用两个 Odoo ORM cursor 事务验证首个业务副作用写入后回滚时第二个等待事务接手。
- Contract Reference：CC-TEST-010、017–019
- Result：真实并发提交场景两请求均 HTTP 200 且返回同一产品 ID；ORM 仅一产品、一幂等记录、两次限流计数。响应丢失代理已读取上游 HTTP 200 后关闭客户端连接；丢失响应后、重放前由独立 ORM shell 确认产品与幂等结果已提交；重放再得相同响应/ID，仍仅一产品。首事务回滚/第二事务接手组件验证 PASS，并清理临时记录。
- Deviation / residual：目前没有对真实 HTTP dispatcher 最终 `commit()` 失败做故障注入；也没有在真实多个 HTTP worker 中强制第一请求回滚、让第二请求等待接管。故 CC-TEST-017、019 维持 PARTIAL；CC-TEST-010 维持 PARTIAL，不能将 ORM cursor 结果等同真实 worker HTTP。
- Follow-up：不增加生产故障钩子；评估使用 Odoo 标准测试设施完成无生产路由的 HTTP 事务故障测试。

### IHR-011 — 五个回传接口字段来源核验

- 阶段：Contract/source review
- Action：逐项对照 V3.2 字段行、触发说明、JSON 样例及当前 WMS ORM 字段；未向 Ginlong 地址发请求。没有在缺失的 objectid/method 或必填数据来源上新增按钮/发送代码。
- Files / Components：`docs/ginlong_apis/海外WMS与第三方系统集成V3.2.xlsx`、`V3.2参数核对记录.md`、`world.depot.inbound.order`、`world.depot.outbound.order`、`stock.picking`、`stock.move.line`、`ginlong.stocktake.task`
- Contract Reference：CC-TEST-001–007
- Result：待确认问题限定为：(1) API02/04/06/08/10 各自 objectid、HTTP 方法；(2) API02/08 字段表/示例 action 与确认标记冲突，以及 API04/06/10 删除 action 的精确字面值；(3) API04/06/10 每条 SN 必填 operator/operationTime 的实际仓库来源；(4) API04/06/08 多 picking/部分结果范围及 API06 palletQty/totalWeight 取计划订单还是实际执行、JSON number/string；(5) API10 结果采集存储位置、count.order 按钮宿主与当前仅有 `ginlong.stocktake.task` 的模型差异、部分采集/撤销请求范围。详细依据和阻塞映射见 ATR-GIN-003 §7。
- Deviation：没有用 `picking.user_id`（它是 Responsible/负责人）、`create_uid/write_uid`（记录创建/修改者）冒充 KR 实际操作人；没有将订单输入 `sn_list_json` 冒充 API10 的实际采集结果。未为待确认字段伪造时间、托盘或重量规则。
- Follow-up：用户已收到精简问题清单；收到确认后，只实现/测试不受未决项阻塞的字段与行为。

### IHR-012 — 回传修订提案与盘点实盘模型核查

- 阶段：Contract review / Odoo ORM source verification
- Action：根据用户确认的回传方案，起草 [CC-GIN-003 v1.1 回传方案修订提案](CC-GIN-003-v1.1-回传修订提案.md)，包含管理员 endpoint URL/objectid 与 HTTP method 配置、Order 上的手动 Wizard、实际执行数据读取、多 picking 范围选择、Payload 预览、仅补充真正缺失的回传必填字段、确认后同步发送一次及现有 API 日志复用。提案待 Human Review；未实施回传按钮或客户端。
- Files / Components：`docs/implementation/CC-GIN-003-v1.1-回传修订提案.md`；`mymodules/ginlong_apis/models/ginlong_models.py`；既有数据库 `odooce_karlrapp` 的 Odoo ORM registry / `ir.model.fields`
- Contract Reference：拟议 CC-GIN-003 v1.1 §4、§6；现行 CC-TEST-001–007 仍按 v1.0 冻结条件记录
- Result：项目业务边界确认为两个对象——客户盘点订单及仓库实盘结果。用户要求 API10 从实盘结果读取实际 SN、产品、数量并关联客户订单；不得读取 `stock.quant` 推算，也不得以计划值冒充实盘。当前 checkout 中只找到 `ginlong.stocktake.task` 和其计划产品明细 `ginlong.stocktake.task.line`；ORM registry 的 `world.depot.*` 模型/字段检查未定位独立仓库实盘结果模型或其到客户盘点单的关系。API10 实际取数与完整回传保持 BLOCKED，等待模型映射证据。
- Deviation：未假设 `ginlong.stocktake.task.line` 为实盘记录；未访问 `stock.quant`；未创建平行模型；没有直接数据库访问或 SQL。
- Follow-up：提案评审通过后再修订受控 CC 并实施。API10 仅复用查明的现有客户订单/实盘结果模型；若当前 checkout/数据库确无该结果模型，则保持阻塞，须由现有 WMS/Gateway 实际交付后继续，不得在本提案下自行新增平行盘点模型。

### IHR-013 — CC-GIN-003 v1.1 冻结后的回传与盘点实施

- 阶段：Implementation / Odoo ORM verification
- Action：依据 Human Review APPROVED 的 CC-GIN-003 v1.1 和 TDD v0.4，在对应 inbound/outbound/stocktake Order 表单加入五个人工回传按钮及业务确认 Wizard；在 Settings 配置各回传 API 的完整 Endpoint URL 和 HTTP method。Wizard 从 inbound/outbound Order、关联实际 picking/move line、或 `worlddepot` 实盘结果读取业务数据，不显示 JSON。`_build_payload()` 在 Ginlong wire action/撤销/部分范围/必填操作字段等未确认时明确阻止发送；不猜协议、不发真实 Ginlong 请求。现有 API 日志保存阻塞结果；Endpoint URL userinfo 及敏感查询值在日志中遮蔽。
- API06 证据：检查 `worlddepot/models/outbound_order_status.py`，`set_status_to_pick_finished` 仅在 Hoymiles 的专属流程下回传 Hoymiles 并记录该回传结果。没有把它当作 Karl Rapp 备货事件，也未新增状态门禁、审批或业务限制。
- API10 盘点：此前源码/ORM 已确认缺少客户盘点单与仓库实盘结果模型；在 `worlddepot` 中最小增加 `world.depot.stocktake.order` 与 `world.depot.stocktake.result` 两个模型。API05 写订单指令和计划范围；API10 从关联 `result_ids` 展示实盘 SN/产品/数量/托盘/可用的真实操作人及时间。删除旧 `ginlong.stocktake.task`、`.line` 模型及 ACL 前，核对旧模型 ORM 记录为 0，源码引用仅在旧 API05 服务、测试和 ACL；不创建 Ginlong 平行盘点模型，不访问 `stock.quant`。
- Files / Components：`mymodules/ginlong_apis/models/callback_wizard.py`、`models/api_control.py`、相关 view/settings/ACL/tests、API05 service；`mymodules/worlddepot/models/stocktake.py`、import/manifest/ACL/view/test；[TDD v0.4 冻结原件](../ginlong_apis/TDD-v0.4.md)、[TDD v0.4.1 地址/鉴权事实补充](../ginlong_apis/TDD-v0.4.1.md)、[CC-GIN-003 v1.1](CC-GIN-003-v1.1.md)、[Implementation Plan v1.1 执行补充](IMPLEMENTATION_PLAN_ginlong_apis-v1.1.md)。
- Contract Reference：CC-TEST-001–007、CC-TEST-024；API05/10 的 `worlddepot` 模型边界。
- Result：既有配置的 `odooce_karlrapp` 中 `worlddepot` 18.0.0.3 与 `ginlong_apis` 18.0.2.0.0 均 installed；ORM registry 确认两个盘点模型字段、五个按钮方法、相关 views 已注册，旧 Ginlong 盘点模型不再注册。定向 Odoo 运行：ATR-RUN-018 7 项、ATR-RUN-019 2 项、ATR-RUN-020 3 项、ATR-RUN-022 2 项、ATR-RUN-023 3 项、ATR-RUN-024 1 项，均为 0 failed / 0 error。测试实际创建 picking/move/move line/lot/package 来确认 API04/06 展示字段；API10 测试确认显示实盘数据而不显示计划 SN。Wizard ACL 使用现有 `stock.group_stock_user`，并通过定向测试确认；无 Endpoint 时不发送且给出管理员配置提示。日志测试确认 Endpoint 用户名/密码及敏感 query 值即使被模拟响应/异常原样回显，也会在日志各字段遮蔽。
- Deviation / residual：没有完成完整按钮到成功 Mock HTTP，因为任何一组未决 action/响应/撤销/现场 operator/time 映射都不能用猜测补齐。Endpoint helper 的独立单次 Mock 调用测试不是完整回传验收。CC-TEST-001–007 的组件子项为 PARTIAL；完整 HTTP 和外部联调仍 BLOCKED/NOT RUN。完整 WMS 人工 E2E 留最终集成 CC。CC-TEST-010/017/019 未重跑且保留原 PARTIAL，不降级标准。
- Follow-up：请求 Ginlong 明确各回传 endpoint objectid/HTTP method（管理员配置可先放置值，但真实接口契约仍需确认）、wire action/状态、撤销及分批范围、逐 SN 操作人/时间来源、API06 备货实际事件与实际数量/重量序列化。每项确认后仅解锁依赖该契约的 API 场景；继续本地 Mock，未经新授权不访问 Ginlong/生产。

### IHR-014 — 回传阻塞逐字段核对、objectid 补充及事务自动化完成

- 阶段：Contract/source review / Odoo automated verification
- Action：将用户于 2026-11-18 提供的 Ginlong objectid 登记至 [V3.2 参数核对记录](../ginlong_apis/V3.2参数核对记录.md)：API01 `TPL_Pending_Receipt_Note`、API02 `TPL_Receipt_Confirmation`、API03 `TPL_Pending_Delivery_Note`、API04 `TPL_Inbound_Completion`、API05 `TPL_Stocktake_Order`、API06 `TPL_Picking_Completed`、API07 `TPL_Product_Master`、API08 `TPL_Shipment_Completed`、API10 `TPL_Stocktaking_Completed`。这些值消除 API02/04/06/08/10 的 objectid 缺项；API09 未提供。HTTP method 仍未知。未修改冻结的 SRS/TDD/CC。
- 逐字段结论：API02 `inboundOrderNo`/状态来源已存在但 Payload 映射未实现；`action`、`receiptConfirmed` wire 语义仍有 V3.2 冲突/缺值。API04/06 的 order、product/SN/quantity/package 及 picking 完成时间有本地来源但完整映射未实现；API04/06 的逐 SN 实际 operator 本地数据不存在，点击用户/负责人不能替代；`operationTime` 粒度及格式需确认。API06 的既有备货事件已定位为 `outbound.order.status='picking'`、`picking_PICK`、`picking_PICK_date`，Wizard 已展示并测试，不属于阻塞；`palletQty`/`totalWeight` 的实际选取范围、重量口径和 JSON 表示仍未定。API08 Order 状态来源存在、映射未实现；`action`/`shipmentConfirmed` 的 V3.2 样例/说明冲突。API10 的实盘字段、operator 关系及实际时间均在 `worlddepot.stocktake.result`；Payload 映射、operator 字符串表示及部分结果选择尚未实现/确认。所有接口具体字段与影响见 ATR §7.1。
- 测试证据：保留 ATR-RUN-025 失败原始记录。ATR-RUN-026 使用既有 `odoo.conf`、`venv`、`odooce_karlrapp` 执行 `ginlong_apis` Odoo 标准测试，29 post-tests、0 failed / 0 error。CC-TEST-010 结合 ATR-RUN-014 的四 Worker 相同请求 HTTP 并发提交证据，以及本轮独立 Odoo ORM cursor 的提交重放/首事务回滚接管自动化；CC-TEST-017 注入真实 Odoo `Cursor.commit()` 失败并由新 ORM 事务确认业务与幂等数据均不可见；CC-TEST-019 结合 ATR-RUN-016 本机 HTTP 响应丢失代理、重放结果与本轮 ORM 提交/回滚仲裁自动化。无 Ginlong 外部流量。
- 范围说明：这些是接口/事务自动化及组件集成证据；完整 WMS 人工 E2E 继续留最终集成 CC，不作为本轮阻塞。CC-TEST-024 冻结要求的受影响 WMS 自动回归仍单独跟踪；项目模板同步仍 BLOCKED 并沿用已批准例外。
- Result：CC-TEST-010/017/019 自动化证据已补齐并通过；五个人工回传接口不是一个笼统 BLOCKED，协议缺项、数据来源缺失和本地映射未实现已分列。CC-GIN-003 仍 In Progress，不生成关闭 FR。
- Deviation：没有将 objectid 补充推断成 HTTP 方法或其他 wire 规则；未访问真实 Ginlong；未执行完整 WMS 人工 E2E。
- Follow-up：依 ATR §7.1 分字段处理尚缺的 Ginlong HTTP/状态/撤销/分批及字段表示契约，并实现已有数据来源的本地 Payload 映射及确实缺失字段补充输入；完整人工 E2E 留最终集成 CC。

### IHR-015 — 回传界面切换为持久化 Form/Notebook

- 阶段：Implementation / Odoo automated verification
- Action：依据用户确认的视图交互规范和 CC-GIN-003 v1.2，将五个人工回传界面统一放入现有业务 Form 的「Ginlong 回传数据」Notebook。移除回传 `TransientModel` Wizard；补充字段先写入持久化 ORM 后，按钮才从已保存记录生成 JSON 并同步 POST。API04 的本次 picking 范围保存在 `stock.picking.ginlong_callback_selected`；API04/06 的逐 SN 操作人编码和时间保存在现有 `stock.move.line`；API10 的 Action、实盘结果范围及 Ginlong 操作人编码保存于既有客户盘点单/实盘结果模型。每次发送新增现有 `world.depot.api.log` 记录，失败后可编辑重试，不覆写旧日志。
- 数据边界：API04 只读取已保存选中的实际 picking/move line；API10 只读取已保存选中的 `world.depot.stocktake.result`。没有使用客户盘点计划数据或 `stock.quant` 推算盘点结果，没有创建平行盘点/日志模型。
- 接口状态：API04 的实际入库数据 Mock POST、失败后修改重发及日志独立性通过；API10 的实盘数据 Add/Del Mock 路径通过。API02 仅 `receiptConfirmed` 状态映射未决，API06 仅 `palletQty/totalWeight` 实际聚合口径/类型未决，API08 仅 `shipmentConfirmed` 状态映射未决；分别阻止不完整请求，不互相阻塞。统一 POST 与 `application/json` 来自用户明确指令。未访问真实 Ginlong。
- Files / Components：`mymodules/ginlong_apis/models/ginlong_callbacks.py`、`views/ginlong_callback_views.xml`、`models/__init__.py`、`__manifest__.py`、`tests/test_ginlong_api.py`；`mymodules/worlddepot/models/stocktake.py`；[CC-GIN-003 v1.2](CC-GIN-003-v1.2.md)、[TDD v0.5](../ginlong_apis/TDD-v0.5.md)、[Implementation Plan v1.2](IMPLEMENTATION_PLAN_ginlong_apis-v1.2.md)、[PROJECT_COGNITION v1.7](../context/cognition/PROJECT_COGNITION.md)。
- Test Evidence：ATR-RUN-027–032 保留首次视图失败、零测试筛选、修复前失败及后续通过运行。最新 ATR-RUN-032 为 7 项指定 Odoo post-tests，0 failed / 0 error；ATR-RUN-033 使用 Odoo Shell ORM 只读核对 `ginlong_apis` 18.0.2.0.6、持久化字段、四个 Form 视图和 Wizard 不在 registry。
- Deviation / residual：未完成完整浏览器人工 E2E；API02/06/08 按字段分别 Open；API04/API10 的外部撤销/部分结果等协议语义仍待 Ginlong 确认。CC-TEST-010/017/019 沿用既有证据，本轮未重跑；CC-TEST-024 完整保留 WMS 回归及模板同步状态不改。按仓库脚本检查 ATR/IHR/Implementation Plan 模板来源均返回 BLOCKED（项目模板源缺失）；沿用已批准的流程例外，不记录为 PASS。
- Result：持久化数据保存、重新读取、修改、Mock 发送、失败重试和日志追加由七项自动化覆盖；符合用户 Wizard/Form 项目认知。CC-GIN-003 仍 In Progress，不生成关闭 FR。


### IHR-016 — 剩余验收、字段来源与 API07 唯一性核查

- 阶段：Implementation / Odoo automated regression / ORM source review
- Action：按 CC-GIN-003 v1.2、TDD v0.5、Ginlong V3.2 和当前 Odoo 源码逐项检查 CC-TEST-023/024 及 API02/06/08。未访问真实 Ginlong，没有改动生产业务逻辑、产品编码规则或 API02/06/08 Payload 映射。
- API02：入库单 state 为 new/confirm/cancel；confirm 是现有订单确认动作。status 为 planning/arrive/inbound；源码仅在关联 Picking date_done 后由 cron 更新为 inbound。confirm_time_server 是订单确认时间，i_datetime 是实际入库时间；没有独立收货确认字段或对应事件时间。V3.2 的 receiptConfirmed 是必填 VARCHAR，样例为 Y，但未定义允许值、Order 状态映射或撤销值；V3.2 文字还称撤销调用删除，用户确认的正常 Action 为 UPDATE。当前实现有状态显示与未决提示，但不组装完整 Payload。
- API06：已选实际 stock.picking / stock.move.line 可读取实际 quantity、产品重量及 package/result_package 关系；已有 outbound Order 的 picking 状态/时间可识别备货事件，未新增状态门禁。V3.2 没说明 palletQty 是否按本次实盘托盘、唯一包裹或其他方式计数；totalWeight 没说明净/毛重、包装和聚合范围；字段声明 DECIMAL(18,6)，样例却用 JSON 字符串。实际数据源候选存在，但聚合和序列化映射未实现，因此完整 API06 Payload 仍阻塞。
- API08：出库单 state 为 new/confirm/cancel；status 为 planning/picking/outbound。现有 cron 在关联出库 Picking date_done 后将 Order status 设为 outbound 并记录 picking_Out_date。V3.2 将 shipmentConfirmed 列为 VARCHAR，唯一请求样例为 N，触发说明却是发货确认；撤销说明调用删除。用户确认正常 Action 为 CREATE。字段来源存在，但不能据此推定 Y/N 或取消语义；当前实现不组装完整 Payload。
- API07/CC-TEST-023：Odoo 原生 product.product.default_code 为索引字段；核心 onchange 仅提示重复，未找到全局唯一 ORM/SQL 约束。通过 Odoo Shell ORM 在同一事务创建两个不同产品、相同 default_code 成功；显式回滚，后续新 Shell 核实探针记录为 0。当前 ginlong services.api07 在 owner+productCode 未命中而全局 default_code 已存在时，额外抛出 ValidationError。既有 Hoymiles inbound/outbound Controller 使用 default_code 单字段查询并 limit=1。若允许跨 owner 重码，旧 WMS 产品定位会有歧义；若维持 Ginlong guard，则 API07 复合键不能为第二 owner 建立同码产品。未修改现有规则或现有测试预期，CC-TEST-023 保持 PARTIAL，提交 Human Review。
- CC-TEST-024 自动化证据：ATR-RUN-036 在既有测试数据库执行 worlddepot 自动化 8 个 post-tests，0 failed / 0 error，覆盖 API User/Token/认证日志和盘点客户指令/实盘结果；ATR-RUN-037 执行 Ginlong 定向回归 8 个 post-tests，0 failed / 0 error，覆盖 API07、API01/03 更新、API05、持久化 Form、API04、API10、API02/06/08 未决隔离；ATR-RUN-038 扩展 API01/03 更新测试，断言已有 inbound/outbound Picking、move line 及数量仍保留，1 个 post-test、0 failed / 0 error。回传测试还验证已保存选中范围在 ORM invalidate/rebrowse 后仍被按钮读取，API04 失败后修改重发并独立追加日志，API10 只发送选中实盘结果。项目外客户 Controller 未修改；共享 Token/日志测试通过。
- 本轮测试使用既有 odoo.conf、venv、odooce_karlrapp 和 Odoo test runner / Shell ORM。ATR-RUN-034 的受限环境连接失败、ATR-RUN-035 无可核验测试摘要均保留且不计 PASS。未运行 CC-TEST-010/017/019，沿用先前通过证据；未使用 stock_barcode、未直接连接 PostgreSQL、未访问 Ginlong。
- 当前判定：CC-TEST-024 的本 CC 自动化范围 PASS；完整 WMS 人工 E2E 留最终集成 CC。CC-TEST-023 未完成，且 API02/06/08 必填字段仍无批准映射，CC-GIN-003 保持 In Progress，不生成关闭 FR。

#### 提交 Human Review 的最小问题

1. API07：是否允许两个 owner 使用相同 productCode，并在 Odoo 建立 default_code 相同的独立 product.product？若允许，是否授权为消除歧义而调整现有按 default_code 单字段查询的 WMS 路径；若不允许，是否接受第二 owner 的同码 API07 请求继续拒绝？
2. API02：在现有入库单 state（订单确认/取消）与 status（planning/arrive/inbound，inbound 来自实际入库完成）中，哪个状态及值应映射至 receiptConfirmed 的 Y/N？正常 Action 已定为 UPDATE；取消仍按 UPDATE 发送 N，还是取消回传暂不实现/沿用 V3.2 删除语义？
3. API06：palletQty 应按本次选中实际作业范围的什么实体计数；totalWeight 应按净重还是毛重、是否含包装、按哪些实际行聚合；两字段 JSON 应为 number 还是 string？
4. API08：正常发货时现有 Order 状态 outbound 是否对应 shipmentConfirmed=Y（其他状态如何处理）？正常 Action 已定为 CREATE；取消是否暂不实现/沿用 V3.2 删除语义？

### IHR-017 — 回传 Form 来源字段展示与 Open Item 回归

- 阶段：Implementation / Odoo automated regression
- Action：将已有 Odoo 业务来源字段加入现有 Ginlong Notebook，只读展示 API02/08 的 Order `state/status`，以及 API06 的 Order `state/status`、`picking_PICK`、`picking_PICK_date`。没有新增业务字段、状态门禁或 Ginlong wire 映射；未决必填字段仍阻止对应 API 发送。
- Test Evidence：ATR-RUN-040 使用既有 `odoo.conf`、`venv`、`odooce_karlrapp` 和 Odoo test runner，对来源字段展示及 API02/06/08 Open Item 隔离执行 3 个 post-tests，0 failed / 0 error。命令及日志见 ATR §9。
- Result：已知本地数据来源可由用户在业务 Form 查看；API02 的 `receiptConfirmed`、API06 的 `palletQty/totalWeight` 口径与类型、API08 的 `shipmentConfirmed` 仍不能在缺少业务/协议依据时映射。API04/API10 持久化数据来源与已保存 ORM 发送回归继续引用 ATR-RUN-037。未访问真实 Ginlong。
- Status：组件回归通过；外部字段决策仍 Open，CC 不满足关闭条件。

### IHR-018 — 最终字段规则、API07 货主消歧与关闭验收

- 阶段：Implementation / Odoo automated regression / ORM registry verification
- 授权：按用户 2026-11-18 最终决策实施并使用现有 venv、`odoo.conf`、`odooce_karlrapp`；仅本地 ORM/test runner 与 Mock HTTP；无真实 Ginlong 或生产访问。
- API07：Ginlong 产品业务键为 `owner + productCode`，同 `default_code` 可跨 owner 建立/更新原生 `product.product`。`services.api07()`、API01/03/05 产品查找复用 owner 代码；新增共享 WMS `product_lookup.resolve_product()`，并更新 Hoymiles/OFoundation 入库、出库、调拨 Controller 的单字段查找调用。无重复编码时沿用旧查找；重复编码时按项目货主 Ginlong owner code 消歧，缺少唯一 owner 依据时返回歧义错误，不用 `limit=1` 任取。没有新增映射模型，也未改变 Odoo 原生编码唯一性规则。
- API02：在现有入库 Order 下增加持久化收货明细，关联实际 move line，产品、Lot/SN、数量、托盘从关联记录读取，行状态保存 Y/N。Payload 从保存后的明细状态生成。状态一致时发送该状态；用户最终确认混合 Y/N 明细阻止发送，记录失败日志；取消控制/回传不在本轮。
- API06：从已选实际 `stock.move.line.package_id` 去重计数，已保存人工托盘数覆盖优先；单件重量采用 API07 字段映射 `product.ginlong_weight`，乘实际备货数量计算净重；毛重默认净重且允许保存覆盖。`palletQty`/`totalWeight` 按用户最终确认和 V3.2 示例作为 JSON string，格式化到最多六位小数。无状态门禁。
- API08：在现有出库 Order 下增加持久化发货明细，关联实际 move line，读取产品、Lot/SN、数量及托盘，保存 Y/N 发货状态。状态一致时生成订单字段；混合 Y/N 阻止发送并记录错误；取消控制/回传不在本轮。
- Tests：ATR-RUN-041 首次运行 1 failure、4 errors，保留；修正后 RUN-042 七项定向通过。RUN-043 Ginlong 全量 30 post-tests、RUN-044 worlddepot 全量 8 post-tests、RUN-045 ORM registry 检查通过。根据用户最后确认增加混合状态和 JSON string 验证，RUN-046 三项通过；最终 Ginlong 全量 RUN-047/048 均为 31 post-tests、0 failed / 0 error，RUN-048 还断言六位小数序列化。RUN-041/042 的原始证据均保留。
- ORM registry：收货/发货明细模型及 order/move_line/product/lot/qty/package/status 字段、API06 汇总字段、产品 Ginlong owner/weight 字段、move line package/operator/time 字段均注册；`ginlong.api.callback.wizard` 不在 registry；模块状态为 installed。只读 ORM 输出见 ATR-RUN-045。
- WMS 回归：`worlddepot` 当前 8 项自动化及 Ginlong 当前全量自动化通过；API07 resolver 和 API01/03 订单及现有 Picking/move line 保留由相应自动化覆盖。完整人工 WMS E2E 留最终集成 CC。
- Result：CC-TEST-001–024 均有 PASS 证据；CC-TEST-010/017/019 沿用既有通过运行，本轮不重跑。Ginlong 撤销/部分执行等外部 Open Items 和真实联调留最终集成 CC，不伪记 PASS。模板同步保持 BLOCKED，沿用批准的流程例外。CC-GIN-003 本地验收具备提交 Human Review 关闭评估的条件；不自行标记 Closed 或生成关闭 FR。

### IHR-019 — API03 方向补充确认

- 阶段：Implementation record correction / interface baseline update
- 来源：用户后续提供的 Ginlong 接口矩阵列明 API03「出库单创建」方向为 Ginlong → Odoo，Object ID 为 `TPL_Pending_Delivery_Note`，路径为 `/api/ginlong/TPL_Pending_Delivery_Note`，Action 为 Add/Del/Edit；矩阵另行确认所有接口使用 POST 与 `application/json`。
- Action：将 API03 方向从当前 Open Item 中移除，明确早期 A-003 是历史开发假设，已由新矩阵取代。未访问真实 Ginlong；未更改 Ginlong 业务逻辑或外部契约。
- Impact：不改变已执行的 API03 本地订单接收、UPDATE/DELETE、幂等和限流测试结果；真实端点联调仍留最终集成 CC。
- Evidence：当前接口资料记录、ATR-GIN-003 v1.1；原 V3.2 对方向资料不足的同期判断保留为历史，不伪记其当时已确认。
- Result：API03 当前方向已确认；真实环境联调 NOT RUN。

## 4. 实际变更清单（当前快照）

| 文件 / 组件 | 当前变更 | 追溯 |
|---|---|---|
| `mymodules/ginlong_apis/models/api_control.py` | 幂等、限流 ORM 模型及可配置 API 阈值 | CC-TEST-008–019、013–016 |
| `mymodules/ginlong_apis/idempotency.py`、`rate_limiter.py` | 请求指纹/结果重放、独立 ORM 计数事务与 429 | CC-TEST-009–019 |
| `mymodules/ginlong_apis/services.py` | UPDATE/取消和 API07 复合键定位 | CC-TEST-020–023 |
| `mymodules/ginlong_apis/controllers/ginlong_controller.py` | 四路由接入幂等/限流 | CC-TEST-008–015 |
| `mymodules/ginlong_apis/views/res_config_settings_views.xml` | 后台独立阈值设置 | CC-TEST-013 |
| `mymodules/worlddepot/controllers/api_logs.py` | 兼容记录 HTTP 429，不改变模型/认证 | CC-TEST-015 |
| `mymodules/ginlong_apis/tests/test_ginlong_api.py` | ORM 组件测试扩展 | CC-TEST-008–023（部分） |
| `mymodules/ginlong_apis/models/ginlong_callbacks.py`、`views/ginlong_callback_views.xml` | 五个持久化 Form/Notebook 按钮、保存后 ORM 读取、POST/JSON、现有 API 日志追加及凭据保护；API04/API10 Mock 场景通过，API02/06/08 分字段阻止不完整发送 | CC-TEST-001–007（本地组件/Mock 范围 PASS；外部 Open Items 保留） |
| `stock.picking`、`stock.move.line`、`world.depot.stocktake.order/result` | 仅增加本次 picking/实盘选择及 Ginlong 必填操作资料的持久化字段；不新建平行业务模型 | CC-TEST-001–006 |
| `mymodules/worlddepot/models/stocktake.py`、相关 ACL/view/import/manifest/tests | 客户盘点订单与仓库实盘结果双模型；API05/10 复用，移除 Ginlong 平行模型 | CC-TEST-005、022、024 |
| `mymodules/worlddepot/controllers/hoymiles/product_lookup.py` 及 5 个 Hoymiles/OFoundation Controller | 共享产品编码 resolver；重复编码按项目 owner 消歧或报告歧义；不任意选择第一条 | CC-TEST-023/024 |
| `mymodules/ginlong_apis/models/wms_extensions.py`、`models/ginlong_callbacks.py`、API 回传视图及测试 | API02/08 持久化实际明细与状态；API06 实际 package 去重、Ginlong 产品重量、JSON string 和可保存覆盖；混合状态阻止；失败重试追加日志 | CC-TEST-001–007、023/024 |

## 5. 偏离与停止记录

| 事件 | 处理 | 状态 |
|---|---|---|
| Odoo Engineering 来源副本缺失 | 同步脚本返回 BLOCKED；不使用内置副本充当权威来源，按已批准 CC 的具体方案继续 | BLOCKED 事实保留 |
| API 回传界面与剩余 Open Items | 已切换为持久化 Form/Notebook；API04/API10 本地 Mock 场景通过。API02/06/08 各自字段未决时不发送不完整数据；真实 Ginlong 与完整人工 E2E 未执行 | In Progress（逐接口跟踪） |
| 多 Worker 启动依赖 `zope.interface` distribution 解析 | 现有 venv setuptools 更新至 81.0.0 后四 Worker 可启动；限流性能验收已按原标准完成 | CC-TEST-016 PASS；首次失败与无效客户端运行保留在 ATR |
| TDD v0.4 / v0.4.1 | v0.4 按批准的 CC-GIN-003 v1.1 冻结为设计基线；v0.4.1 单独补记后续确认的 Odoo→Ginlong 回传 Base URL/无鉴权事实，两个原件均保留 | Frozen with Open Items / factual supplement |

## 6. 移交摘要

本地实施和自动化完成。五个人工回传继续使用持久化业务 Form/Notebook；API07 复合键与 WMS owner resolver、API02/08 实际明细状态、API06 实际托盘/重量/覆盖均按用户最终规则实现。ATR-RUN-048 Ginlong 全量 31 项、RUN-044 worlddepot 全量 8 项、RUN-046 最终规则定向 3 项和 RUN-045 ORM registry 核验通过；CC-TEST-010/017/019 沿用既有通过证据，本轮不重跑。真实 Ginlong 和完整人工 WMS E2E 留最终集成 CC；模板同步继续 BLOCKED 并保留批准例外。当前 CC 具备 Human Review 关闭评估条件，未经批准不标记 Closed、不生成关闭 FR。

## 附录：版本记录

| 版本 | 日期 | 说明 | 状态 |
|---|---|---|---|
| v0.1 | 2026-11-17 | 创建 CC-GIN-003 实施事实台账；代码实施进行中 | In Progress |
| v0.2 | 2026-11-17 | 追加 logger 并发异常修复、Odoo 升级/ORM、单进程 HTTP 429/幂等重放及多 Worker 启动阻塞证据；模板同步继续 BLOCKED | In Progress |
| v0.3 | 2026-11-17 | 追加四 Worker 启动修复、API01/03/05/07 默认阈值及 100/s 实测、配置窗口切换、身份隔离、事务回滚接管组件验证、响应丢失重放、V3.2 回传数据来源核对及 CC-TEST-010/017/019 剩余缺口；保留失败运行与模板 BLOCKED | In Progress |
| v0.4 | 2026-11-17 | 追加 CC-GIN-003 v1.1 回传修订提案及 API10 两模型边界；用当前源码和 ORM registry 核查实盘结果模型映射，未定位则明确保持 API10 BLOCKED；回传实施等待 Human Review | In Progress |
| v0.5 | 2026-11-18 | 记录 CC-GIN-003 v1.1 Frozen with Open Items / Human Review APPROVED 后的回传与盘点实施、ATR-RUN-018–021、API06 事件来源核对和日志 URL 凭据保护；明确完整 HTTP/外部联调、CC-TEST-010/017/019 子项及保留 WMS 完整回归仍未完成 | In Progress |
| v0.6 | 2026-11-18 | 追加 IHR-014：登记用户补充的各 API objectid；分离回传协议缺项、Odoo 数据来源缺失及本地映射未实现；记录 ATR-RUN-025 失败及 ATR-RUN-026 通过，完成 CC-TEST-010/017/019 自动化验收；完整人工 WMS E2E 留最终集成 CC | In Progress |
| v0.7 | 2026-11-18 | 追加 IHR-015：按 Wizard/Form 项目认知，将五个人工回传改为持久化 Form/Notebook，记录已保存 ORM 数据、API04 多 picking 与 API10 实盘选择、Mock 重发/追加日志测试及最新 ORM 核查；保留旧 Wizard 记录作为历史，模板同步仍 BLOCKED | In Progress |
| v0.8 | 2026-11-18 | 追加 IHR-016：核验 API02/06/08 的字段与本地状态/作业来源，实测原生 default_code 重复与 Ginlong 服务冲突，完成 CC-TEST-024 受影响自动化回归并列出最小 Human Review；CC-TEST-023 与字段映射仍未解决 | In Progress |
| v0.9 | 2026-11-18 | 追加 IHR-017：在持久化业务 Form 展示 API02/08 Order state/status 及 API06 Order/picking 备货来源字段；3 个 Odoo post-tests 通过；未增加未经确认的 Ginlong 字段映射，CC-TEST-023 与 API02/06/08 Open Items 保留 | In Progress |
| v1.0 | 2026-11-18 | 追加 IHR-018：纳入 API07 owner+productCode 和现有 WMS resolver、API02/08 持久化实际明细及混合状态阻止、API06 JSON string/重量/手工覆盖；记录 ATR-RUN-041–048、ORM registry 及关闭验收评估 | Ready for Human Review |
| v1.1 | 2026-11-18 | 追加 IHR-019：根据后续 Ginlong 接口矩阵确认 API03 Ginlong→Odoo，保留早期 A-003 作为历史假设；真实联调仍未执行 | Ready for Human Review |
