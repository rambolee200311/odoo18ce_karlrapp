<!-- CC-GIN-001 v1.0：2026-11-17 Frozen；经 Human Review 批准后 Closed。模板源同步仍 BLOCKED，不记为 Passed；Owner/托盘模型工作不在本 CC 实施范围内。 -->

# Coding Contract：CC-GIN-001

## 0. 文档治理

| 字段 | 值 |
|---|---|
| CC ID | `CC-GIN-001`（CC-01） |
| 版本 | v1.0 |
| 状态 | Closed（Frozen v1.0；Human Review APPROVED） |
| Intent ID | `GINLONG-FOUNDATION-LOG-SECURITY-OWNER-PALLET` |
| 模块 | `ginlong_apis` / `worlddepot` 共享日志安全修复 |
| SRS 基线（现行） | [ginlong_apis SRS v1.0 Frozen](../requirement/SRS_ginlong_apis.md) |
| TDD 基线（现行） | [ginlong_apis TDD v0.3 Frozen with Open Items](../ginlong_apis/TDD.md) |
| Implementation Plan 基线（现行） | [ginlong_apis Implementation Plan v1.0 Frozen](IMPLEMENTATION_PLAN_ginlong_apis.md) |
| 冻结日期 | 2026-11-17 |
| 批准记录 | 李建强（项目用户明确指令“冻结cc-01，进入实施”）；2026-11-17；批准 CC-GIN-001 v1.0 并授权其阶段0范围实施 |
| 模板同步 | BLOCKED：项目 CC 模板来源缺失；本次按用户明确指令冻结并实施，未将同步检查记为通过 |
| 实施授权 | 有；仅限本 CC v1.0 §3/§4 阶段0范围 |
| 关闭批准 | 李建强（项目用户明确 Human Review 决定）；2026-11-17；依据 FR-GIN-001 v1.0 批准关闭 CC-GIN-001 v1.0 |

本稿将阶段 0 的日志凭据修复限定为源码已证实的泄露路径，并把“订单货主不再强制继承项目货主”及“记录托盘生命周期”列为必须保留的后续模型调整。后两项未进入当前 SRS/TDD 的批准设计基线；不得据本稿直接实施，须先按 §2.6 更新上游基线并重新确认 CC/Plan 分工。

## 1. 变更概述

| 字段 | 值 |
|---|---|
| 工作类型 | 安全修复、addon 基础结构 |
| 变更类型 | 最小 addon 基础 + 现有 API 日志泄露修复 + 上游模型调整项追踪 |
| 目标 | 在现有 API 日志路径上修复已证实的 Secret/Token 泄露，不建立新日志机制；明确多货主与托盘生命周期是必须完成的业务模型调整，并在批准基线更新前阻止相关编码。 |
| 背景 | `world.depot.api.log` 已承担 HTTP 请求/响应日志，但认证 API 的请求体含 `api_secret`、成功响应含 `access_token`，Token validator 也会记录无效/过期 Token 原文。现有 `auditlog` 主要记录配置模型的 ORM 操作变化，不替代 API 报文日志或凭据过滤。 |

## 2. 上游基线与追溯

### 2.1 当前批准的 SRS 基线与缺口

| SRS ID | 标题 / 内容 | 与本次 CC 的相关性 |
|---|---|---|
| NFR-GIN-SEC-001/002 | 复用现有身份认证、权限和凭据安全要求 | 仅修复已证实会记录认证凭据的路径；不改认证语义 |
| NFR-GIN-AUD-001 | 复用现有 API 日志记录请求、响应 / 错误和结果 | 在原有 `world.depot.api.log` 中保留业务排障数据，只遮蔽本 CC 证实的凭据 |
| 货主与项目关系 | SRS v1.0 未要求订单货主独立于项目货主，未规定拆除强制绑定 | 新要求：订单货主不得仅因所属项目而被强制设为该项目唯一货主；具体字段方案待上游基线确认 |
| 托盘生命周期 | SRS v1.0 未定义贯穿入库、库内移动/拆装和出库的托盘生命周期要求 | 新要求：必须能按稳定托盘标识追踪生命周期；验收事件按 Implementation Plan v1.0 的记录先行，SRS/TDD 需正式纳入 |

### 2.2 DDD

N/A。TDD v0.3 §0.2 记录本项目 DDD 不适用及其依据。

### 2.3 当前批准的 TDD 基线与缺口

| TDD ID / 章节 | 标题 / 内容 | 相关性 |
|---|---|---|
| T-SEC-001 | 复用现有权限和认证；凭据不得进入数据库日志、应用日志或用户提示 | 本 CC 的安全边界；修复范围限定在已证实的 API logger / token validator 路径 |
| T-LOG-001 | 复用现有 API 日志 | 不新建日志模型、日志框架或 ORM 拦截 |
| §1.2、§2、§3.2.3 | `worlddepot` 依赖、最小 addon、API 日志字段复用 | addon 结构和现有日志入口 |
| §0.2、§3、§18 | 当前 TDD 未设计订单脱离项目货主绑定；DDD 说明明确不覆盖跨聚合生命周期 | 与用户确认的两项业务模型要求有缺口/冲突，必须先更新 TDD |

### 2.4 源码检查证据（本轮只读）

| 发现 | 实际证据 | 修复边界 |
|---|---|---|
| 认证请求凭据进入 API 数据库日志 | `api_logger` 原样记录请求体到 `request_data`；`generate_token` 从请求体读取 `api_secret` | 只保护该现有日志记录路径中的认证凭据；保留其余业务字段 |
| Token 成功响应进入 API 数据库日志 | `generate_token` 返回 `access_token`；`api_logger` 将完整响应写入 `response_data`，并将 `data` 再写入 `data` 字段 | 仅日志副本中的凭据值须被遮蔽；客户端认证响应保持原样 |
| 无效/过期 Token 进入应用日志 | `validator_token.py` 分别以 warning/info 记录 Token 原文 | 日志只保留事件类别和非敏感诊断信息；401 响应保持原样 |
| API 数据库日志写入失败时回退输出原请求体 | `api_logger` 的 fallback debug 记录 `request_data` | 对 fallback 路径应用与同一实际认证调用相同的最小凭据保护 |
| `auditlog` 模块能力边界 | 源码模块为 `mymodules/auditlog`，技术名 `auditlog`；`auditlog.log` 记录受规则控制的模型 CRUD 字段变更，HTTP Request 模型记录路径/会话上下文，不记录 API 请求/响应正文 | 不作为 `world.depot.api.log` 的替代品；不新增依赖、审计规则或脱敏扩展。本轮未查询目标数据库中的模块安装状态 |
| 订单货主强制绑定 | 入库及出库模型的 `owner` 字段为 `related='project.owner'`；Plan v1.0 已记录用户决定，但仍要求阶段 1 前更新上游基线 | 必须保留为后续现有订单模型调整；本 CC v0.2 不直接授权改模型 |
| 托盘生命周期 | `worlddepot` 入库流程会创建/关联 `stock.quant.package`，标准 `stock.move.line` 已有来源/目标 Package、产品、数量、库位、时间等字段；但批准的 TDD 未定义从收货至出库的生命周期验收 | 必须保留生命周期要求；先在 TDD 评估现有 package/move 记录能否覆盖，不默认新建台账模型，也不修改盘点库存隔离要求 |

代码依据：[api_logs.py](../../mymodules/worlddepot/controllers/api_logs.py)、[validator_token.py](../../mymodules/worlddepot/controllers/validator_token.py)、[auth_controller.py](../../mymodules/worlddepot/controllers/auth_controller.py)、[`auditlog` manifest](../../mymodules/auditlog/__manifest__.py)、[`auditlog` 模型日志](../../mymodules/auditlog/models/log.py)、[入库单模型](../../mymodules/worlddepot/models/inbound_order.py)、[出库单模型](../../mymodules/worlddepot/models/outbound_order.py)、[标准库存移动行](../../addons/stock/models/stock_move_line.py)。

### 2.5 追溯规则

本 CC 不自行决定两项模型调整的字段实现，不改变 API 契约。若需要修改认证语义、客户端响应、日志权限，或发现必须新增通用日志机制，必须停止并升级至 TDD / SRS 变更流程。

### 2.6 上游基线调整建议（本次只提出，不修改）

| 上游文档 | 当前状态 | 必要调整 | 影响的 CC 范围 |
|---|---|---|---|
| SRS v1.0 | Frozen；未规定订单货主脱离项目货主，也未列出托盘生命周期需求 | 修订为新版本：明确项目关联不再强制决定订单货主；明确稳定托盘标识及须追溯的入库、库内移动/拆装、出库事件和必要验收数据。保留不增加货主-产品归属校验的既有决定 | 将订单模型调整纳入阶段 1 的 CC；将生命周期实现及端到端验收纳入适当阶段 CC |
| TDD v0.3 | Frozen with Open Items；§0.2称不覆盖跨聚合生命周期，§3仍假设现有 order/project 关系 | 修订技术设计：订单货主与项目关联解耦；检查标准 Package/Stock Move 是否足以满足生命周期追踪，只在有证据证明不足时最小扩展。不得增加未要求的校验/通用机制；API05/10 仍不操作 `stock.quant` / `stock.move` 或执行库存调整 | 更新 ORM、流程边界、组件集成测试和回归约束；不默认为新增托盘台账或出库三级模型 |
| Implementation Plan v1.0 | Frozen；将两项要求列作门禁，但风险项说明 CC-GIN-001 不触及订单货主及托盘操作 | 上游文档批准后修订计划：将货主关系改造映射到 CC-GIN-002；将托盘生命周期实现/验证分配至受影响阶段的 CC（必要时新增 CC），并更新阶段验收及追溯表 | CC-GIN-001 保持阶段 0 日志修复；模型工作不得被误认为已包含或已授权 |

在以上上游调整经批准前，本稿的两个业务模型项是必须保留的范围要求和开工阻塞项，不是可直接执行的实现指令。修订后的 SRS/TDD/Plan 基线确定后，再更新本 CC 的版本/追溯范围并评审。

## 3. 范围界定

### 3.1 在范围内

- 阶段 0 可执行范围：建立依赖 `worlddepot` 的最小 `ginlong_apis` addon 骨架；不添加 Ginlong 路由、业务模型或访问控制扩展。
- 只修复源码已证实的泄露路径：认证 API 的 `api_secret` 请求日志、认证成功响应中的 `access_token` 日志、Token validator 对无效/过期 Token 的应用日志，以及 API 日志失败时回退输出的认证请求体。
- 继续使用 `world.depot.api.log`、现有 `api_logger` 和 Token validator；在现有记录点对日志副本作最小凭据保护，业务响应仍原样返回。
- 保留订单货主与项目强制绑定解除、托盘生命周期管理两项必要业务模型调整为本项目后续必须完成的范围；它们在当前批准基线中未定义，实施归属和验收见 §2.6，更新上游文档前不得编码。
- 以自动化组件测试和组件集成测试验证认证端点、共享 API 日志、Token validator 及日志失败回退路径。

### 3.2 超出范围

- Ginlong API01–10 路由、Payload 映射、订单按钮及 API09 查询。
- 在本 CC-001 阶段直接实现订单货主关系解除或托盘生命周期模型；两项必须保留并转入完成上游更新后的适当 CC，不得删除或视为可选。
- 新增货主与产品归属校验、删除现有订单 project 关联、或默认新增出库“订单-托盘-产品”三级模型。
- 为 API05/10 修改盘点与库存记账流程；不得直接操作 `stock.quant`、`stock.move` 或执行库存调整。
- 改造 `auditlog` 通用模块、增加 ORM 拦截、配置额外 `auditlog.rule`，或以 auditlog 代替 API 报文日志。
- 新建日志框架、日志模型、Secret 管理器、Endpoint 配置模型、监控框架、队列或重试器。

### 3.3 非目标

- 不改变现有认证 / Token 校验语义、客户端响应字段、HTTP 状态或成功返回的 `access_token`。
- 不遮蔽或删除非凭据业务 Payload；不对所有模型字段作全局脱敏。
- 本 CC 不证明 Ginlong 外部协议已确定，也不进行真实 Ginlong 联调。
- 本 CC 不实现 Ginlong 业务接口、事务调度或后台重试。

### 3.4 范围内追溯

阶段 0 可执行要求须落到 §5 的 CC-CHANGE-001–003。货主关系解耦和托盘生命周期是已确认但尚未进入 SRS/TDD 批准基线的后续模型要求；本 CC 仅在 §2.6 和 §5 留置追踪，不构成本 CC 阶段 0 的编码授权。

## 4. 变更边界

### 4.1 允许修改

| 类型 | 详情 |
|---|---|
| 新增文件 | `mymodules/ginlong_apis/__init__.py` |
| 新增文件 | `mymodules/ginlong_apis/__manifest__.py` |
| 新增文件（仅用于最小包结构时） | `mymodules/ginlong_apis/controllers/__init__.py`、`mymodules/ginlong_apis/models/__init__.py` |
| World Depot 版本记录 | `mymodules/worlddepot/__manifest__.py`，仅更新模块版本号 |
| 现有 API logger | `mymodules/worlddepot/controllers/api_logs.py`，仅修复已证实的认证请求/响应及 fallback 日志泄露 |
| Token validator | `mymodules/worlddepot/controllers/validator_token.py`，只移除无效/过期 Token 的原文日志值 |
| 新增测试 | `mymodules/worlddepot/tests/` 中覆盖现有认证/日志组件的自动化测试；只在 Odoo 测试发现需要时添加初始化文件 |

`auth_controller.py` 作为现有端点的被测组件，不预先授权修改。若测试证明仅在该文件内作最小修复不可避免，先修订 CC 文件清单。

### 4.2 禁止修改

| 类型 | 禁止事项 |
|---|---|
| WMS 订单 / 库存 | 本 CC-001 阶段不修改订单货主字段、项目关联、库存数量、Package 或 stock move 行为；后续订单/托盘要求不得从项目总范围删除 |
| 盘点 | 不修改 API05/10 独立盘点设计，不读取 / 写入 `stock.quant` 或执行调整 |
| API 合约 | 不新增 Ginlong 路由、字段、状态码、业务状态或自动触发行为 |
| 权限 | 不扩大 `world.depot.api.log`、Token 或 API user 的访问权限 |
| 认证 | 不改变 API key / Secret 校验、Token 发放 / 有效期或 Token 接受规则 |
| 日志 / 审计 | 不新增 ORM `create`/`write` 拦截，不配置额外 auditlog 规则，不改造 `auditlog` 模块 |
| 架构 | 不新增通用脱敏框架、Adapter、Secret Provider、队列、重试器或独立监控框架 |
| 项目边界 | 本 CC 阶段不执行订单 Owner 解耦或托盘生命周期改造；须按 §2.6 更新上游并落实到后续获批 CC |

## 5. 必需的行为变更

| 当前行为 | 期望行为 | CC-CHANGE ID |
|---|---|---|
| token 获取 API 的 request_data、response_data/data 和日志失败 fallback 原样记录请求/响应，已证实包含 `api_secret` / `access_token` | 只在现有 API 日志与 fallback 的日志副本中遮蔽这些凭据；其余字段和客户端响应保持不变 | CC-CHANGE-001 |
| Token validator 对无效/过期 Token 的应用日志输出 Token 原文 | 日志保留事件类别，不包含 Token/Authorization 原文；401 响应不变 | CC-CHANGE-002 |
| 新 Ginlong addon 尚无基础结构 | 提供只依赖现有 `worlddepot` 的最小可安装骨架，不加载业务路由/模型 | CC-CHANGE-003 |

项目还必须完成两项后续业务调整，但它们不属于本 CC 的 `CC-CHANGE`，也不由本次实施完成：

| 后续要求 | 追踪位置 | 解锁条件 |
|---|---|---|
| 订单 Owner 不再强制继承 `project.owner`；项目关联的保留方式和 Owner 字段行为按批准设计确定，不增加 Owner-产品归属校验 | Plan `OPEN-GIN-MULTI-OWNER` | SRS、TDD、Implementation Plan 更新批准后，纳入后续 CC |
| 按稳定托盘标识追踪收货、库内移动/拆装和出库生命周期；优先验证标准 Package/Stock Move 是否满足 | Plan `OPEN-GIN-PALLET-LIFECYCLE` | SRS、TDD、Implementation Plan 更新批准后，纳入后续 CC |

## 6. 既有行为保留（回归边界）

| 行为 / 契约 | 保留原因 | CC-PRESERVE ID |
|---|---|---|
| 现有认证检查、Token 发放和过期策略 | 被现有 API 客户端依赖；本次只防止凭据泄漏 | CC-PRESERVE-001 |
| 现有 API 路由响应字段、HTTP 状态与业务结果 | 本 CC 不改变 API 契约 | CC-PRESERVE-002 |
| 现有日志字段、状态及非凭据业务 Payload 的可读性 | NFR-GIN-AUD-001 要求复用现有日志；不整体脱敏 | CC-PRESERVE-003 |
| 项目字段及订单流程，除经批准的 Owner 关系调整外 | 保持项目关联、收发货流程和现有作业行为；不增加新校验 | CC-PRESERVE-004 |
| 标准库存包裹和移动记账；API05/10 盘点隔离 | 仅在批准的托盘生命周期设计中复用标准库存作业；不把生命周期追踪扩展成盘点库存调整 | CC-PRESERVE-005 |

## 7. 适用的 TDD 防护栏

| TDD 防护栏 | 适用性 | 本次落实位置 | 验证方式 |
|---|---|---|---|
| T-SEC-001 | 适用 | 认证 API 日志副本、Token validator 应用日志 | TEST-GIN-009、CC-TEST-001/002 |
| T-LOG-001 | 适用 | 继续使用 `world.depot.api.log` 原有字段和 `api_logger` | TEST-GIN-012、CC-TEST-001/003 |
| T-WMS-001 | 适用 | 阶段 0 不更改 WMS 业务行为；Owner/托盘工作须先更新基线 | 后续模型 CC 的组件集成测试（待分配） |
| T-COUNT-001 | 本 CC 不适用 | — | API05/10 不在本 CC 范围；后续 CC 继续适用 |

## 8. 数据 / 迁移影响

| 字段 | 值 |
|---|---|
| 本 CC-001 阶段迁移 | 否；不新增业务模型或数据库字段 |
| 后续模型 CC 的迁移 | 未定；Owner related 字段替换及托盘记录差异须在更新后的 TDD 中评估，不由本稿预设 |
| 历史日志清理 | 不在范围内；不删除或改写历史记录 |
| 验证 | 新写入的日志不含凭据；历史数据不纳入本 CC 证明范围 |

## 9. API / 集成影响

| 字段 | 值 |
|---|---|
| 修改的端点 | 不改端点契约；只保护认证端点的现有日志副本和 Token validator 应用日志 |
| 向后兼容 | 是；认证、HTTP 状态和客户端响应保持不变 |
| Adapter 变更 | N/A；不创建 Adapter |
| Ginlong 外部联调 | 不适用；真实联调属于后续计划阶段 |

## 10. 安全 / 权限影响

| 字段 | 值 |
|---|---|
| 新权限 | 无 |
| ACL 变更 | 无 |
| 本次已证实的凭据 | token 获取 API 请求体中的 `api_secret`、成功响应中的 `access_token`，以及 Authorization header 中无效/过期 Token 的应用日志输出 |
| 保护位置 | `world.depot.api.log` 的相关请求/响应副本、其写入失败时的同一路径 fallback、validator 的两条应用日志 |
| 保持原样 | 客户端认证响应、401 错误响应、认证校验、业务 Payload、日志模型/字段与权限 |
| 新凭据种类 | 签名等凭据只有在源码或正式接口契约证明现有路径会记录时才另行修订 CC；本稿不扩展为通用日志脱敏机制 |

## 11. 测试契约

| 测试 ID | 对应变更 | 上游来源 | 测试类型 | 预期结果 | 人工验证 | 原因 |
|---|---|---|---|---|---|---|
| CC-TEST-001 | CC-CHANGE-001 | T-SEC-001、T-LOG-001、TEST-GIN-009/012 | 自动化组件测试 | 调用实际 token 获取 controller/logger 组件；日志 `request_data`、`response_data`、`data` 中不含 `api_secret` / `access_token` 原文，非凭据字段保留；客户端响应仍含协议要求的 access_token | 否 | 覆盖源码已确认的数据库日志泄露 |
| CC-TEST-002 | CC-CHANGE-002 | T-SEC-001、TEST-GIN-009 | 自动化组件测试（caplog） | 对无效与过期 Token 调用 validator；应用日志不含 Token/Authorization 原值，401 状态和响应体保持既有结果 | 否 | 覆盖两条源码已确认的应用日志泄露 |
| CC-TEST-003 | CC-CHANGE-001 | T-LOG-001、TEST-GIN-012 | 自动化组件集成测试 | 模拟现有 API 日志写入失败；fallback 可记录非敏感诊断信息，但请求体中的 `api_secret` 不以明文输出 | 否 | 覆盖日志失败时的实际 fallback 泄露 |
| CC-TEST-004 | CC-CHANGE-003、CC-PRESERVE-001/002/003/004 | T-WMS-001、现有 addon manifest | 自动化模块安装/组件集成测试 | 最小 addon 依赖可解析；现有认证、API 日志字段/状态、业务响应和 WMS 行为保持不变；不新增 auditlog 规则或日志模型 | 否 | 验证阶段 0 集成及既有行为 |

以上均为计划测试，本次尚未运行。Owner/托盘后续 CC 应另行定义自动化组件集成测试；本 CC 的测试不得替代这两项业务验收。执行结果须记录到对应 ATR/IHR，不得将计划状态记为通过。

## 12. 停止条件 / 升级闸门

出现以下任一情形时，停止受影响工作并修订相应基线或 CC：

| 触发条件 | 升级路径 |
|---|---|
| 凭据保护需要改变认证方式、响应字段或 API 业务语义 | 停止；更新 TDD / SRS 并重新批准 |
| 发现通用日志框架、ORM 拦截或 auditlog 扩展被认为是必要条件 | 停止；先提供实际需求证据并修订 TDD/CC，不得默认增加 |
| 发现凭据通过本稿未列明的真实路径泄露 | 暂停该路径；提供源码/复现证据并修订 CC，不作全局拦截 |
| addon 依赖与 TDD / 现有模块依赖冲突 | 停止；更新 TDD，不得临时增加依赖 |
| 开始实施 Owner 解耦或托盘生命周期 | 停止相关模型工作；先批准 SRS/TDD 更新、修订 Plan 阶段/CC 映射，再由对应 CC 授权 |
| 托盘生命周期被要求新增台账模型或改变库存处理 | 先核对标准 Package/Stock Move 与批准验收要求；只有证明现有模型不足并经 TDD 批准，才纳入最小变更 CC |
| 凭据保护导致业务 Payload 丢失或客户端认证响应变化 | 停止；保留失败证据并修订设计 |

## 13. 完成定义 / 关闭标准

| ID | 标准 | 闸门类型 |
|---|---|---|
| 1 | CC-GIN-001 范围为阶段 0：最小 addon 与已证实日志泄露修复；Owner/托盘要求仍是未完成项目事项，不纳入本 CC 或宣称已完成 | 硬闸门 |
| 2 | `api_secret`、`access_token` 与 validator 无效/过期 Token 不出现在对应数据库日志、应用日志或 fallback 中 | 硬闸门 |
| 3 | CC-TEST-001–004 执行并记录 ATR/IHR；Owner/托盘测试由后续 CC 执行 | 硬闸门 |
| 4 | 客户端响应、既有认证行为、非凭据业务数据及 WMS 作业行为保持不变 | 硬闸门 |
| 5 | addon 在现有 `odooce_karlrapp` 开发环境安装/升级通过；复用现有 `venv`，不新建隔离数据库或虚拟环境 | 硬闸门 |
| 6 | CC-GIN-001 不得宣称完成 Owner/托盘要求；这些事项在受影响阶段开工前须完成上游基线更新与 CC 分配 | 硬闸门 |
| 7 | 无未授权文件变更；测试失败按流程处理，不得静默豁免 | 硬闸门 |

## 14. 追溯矩阵

### 14.1 正向：In-Scope 上游 → CC

| 上游 ID | CC-CHANGE ID | 备注 |
|---|---|---|
| NFR-GIN-SEC-001/002、T-SEC-001 | CC-CHANGE-001/002 | 只修复源码确认的认证日志泄露；客户端行为不变 |
| NFR-GIN-AUD-001、T-LOG-001 | CC-CHANGE-001/003 | 复用 `world.depot.api.log` / `api_logger` 及现有 addon 依赖 |
| T-WMS-001 | CC-PRESERVE-004/005 | 保持既有 WMS 作业；Owner/托盘功能待上游更新后进入后续 CC |
| Plan OPEN-GIN-MULTI-OWNER | 不属于本 CC | 用户已确认的后续需求；SRS/TDD/Plan 更新并批准后另分配 CC |
| Plan OPEN-GIN-PALLET-LIFECYCLE | 不属于本 CC | 用户已确认的后续需求；SRS/TDD/Plan 更新并批准后另分配 CC |

### 14.2 反向：CC → 上游

| CC ID | 上游 ID | 类型 |
|---|---|---|
| CC-CHANGE-001/002 | NFR-GIN-SEC-001/002、NFR-GIN-AUD-001、T-SEC-001、T-LOG-001 | SRS / TDD |
| CC-CHANGE-003 | T-WMS-001、TDD §1.2/§2 | TDD |

### 14.3 无 DDD 路径

现行阶段 0 追溯链为 SRS v1.0 → TDD v0.3 → Implementation Plan v1.0 → CC-GIN-001 v1.0 → IHR/ATR。Owner 与托盘需求目前只有用户确认和 Plan 门禁记录，待 SRS/TDD/Plan 修订批准后再形成完整实施追溯链。

## 附录 A — 变更决策（CC-DEC）

| CC-DEC ID | 决策 | 考虑的替代方案 | 理由 |
|---|---|---|---|
| CC-DEC-001 | 复用 `world.depot.api.log`、现有 `api_logger` 与 Token validator，只修复已证实的凭据输出点 | 新建 Ginlong 专用日志模型/框架或全局 ORM 拦截 | 现有组件已经承担 API 日志；改动限制在实际漏洞路径 |
| CC-DEC-002 | 检查并复用 `auditlog` 的 ORM 审计职责，但不将它用于 API 报文凭据过滤 | 新增 auditlog 规则、依赖或脱敏扩展 | 其模型记录的是 ORM 操作及字段变化，不记录 API 请求/响应正文 |
| CC-DEC-003 | 必须完成订单 Owner 与项目 Owner 解耦及托盘生命周期管理，但先更新上游批准基线并分配后续 CC | 从项目范围中删除这些事项，或现在直接实施 | 保留用户已确认的业务要求，同时遵守 SRS→TDD→Plan→CC 变更顺序 |
| CC-DEC-004 | 托盘生命周期优先验证标准 Package/Stock Move 能否满足；只有证据显示不足才作最小扩展 | 默认新建独立托盘台账或出库三级订单模型 | 降低重复建模，保持既有 WMS 作业行为 |

## 附录 B — 模板使用记录

CC 模板副本同步检查结果为 `BLOCKED`（项目模板来源缺失）。项目用户于 2026-11-17 明确要求“冻结cc-01，进入实施”；据此冻结 CC-GIN-001 v1.0 并授权 §3/§4 阶段0范围。该授权不改变模板检查状态，也不将其标记为 Passed。SRS/TDD 不作修改；Implementation Plan 只回填实际 CC 追溯状态。

## 附录 C — 术语表

| 术语 | 说明 |
|---|---|
| 凭据 | 本次已证实的认证值：`api_secret`、`access_token`、Authorization 中的 Token |
| 共享 API 日志 | `world.depot.api.log` 及现有 `api_logger` 写入路径 |
| ORM 审计 | `auditlog` 对配置规则指定模型的 create/read/write/unlink/export 操作记录 |

## 附录 D — 版本历史

| 版本 | 日期 | 变更说明 | 状态 |
|---|---|---|---|
| v0.1 | 2026-11-17 | 根据 Plan v1.0 起草阶段 0 addon 基础及共享日志凭据保护范围 | Draft |
| v0.2 | 2026-11-17 | 对照 `worlddepot` / `auditlog` 源码收窄到实际泄露点；移除 ORM 拦截和直接 ORM 日志脱敏要求；记录 Owner 解耦及托盘生命周期为必须保留、但待 SRS/TDD/Plan 更新后分配实施的范围 | Draft（评审稿） |
| v1.0 | 2026-11-17 | 按项目用户明确指令冻结阶段0范围并进入实施；Human Review APPROVED 后按 FR-GIN-001 v1.0 关闭；模板同步保持 BLOCKED；Owner/托盘模型工作未纳入本 CC 实施范围 | Closed |


## 15. 关闭记录

| 字段 | 值 |
|---|---|
| Contract | CC-GIN-001 v1.0 Frozen |
| Human Review | **APPROVED** |
| 批准人 | 李建强（项目用户） |
| 批准日期 | 2026-11-17 |
| 关闭依据 | [FR-GIN-001 v1.0](FR-GIN-001.md)；IHR-GIN-001 v0.7；ATR-GIN-001 v0.5 |
| 当前状态 | **Closed** |
| 范围确认 | 仅关闭阶段 0 addon 基础与现有 API 日志敏感信息保护；项目与货主解绑、托盘生命周期管理仍为后续需求，不视为本 CC 完成 |
| 后续 | 阶段 1 可进入 CC-GIN-002 草案 / 评审；其冻结和实施仍须满足更新后的上游基线门禁 |
