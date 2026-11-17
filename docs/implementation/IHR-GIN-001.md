<!-- IHR-GIN-001：依 CC-GIN-001 v1.0 建立。项目 IHR 模板同步为 BLOCKED；按用户明确实施指令记录例外，不将检查记为通过。 -->

# 实施历史记录：IHR-GIN-001

## 0. 文档治理

本 IHR 仅记录 CC-GIN-001 v1.0 实施事实。模板来源同步检查 `BLOCKED`：仓库缺少 `docs/context/cognition/template/Coding/IHR模板.md`。项目用户明确要求冻结 CC 并进入实施；本记录沿用技能内模板，例外不记为同步通过。

## 1. 执行元数据

| 字段 | 值 |
|---|---|
| IHR 文档 | `IHR-GIN-001.md` |
| Intent ID | `GINLONG-FOUNDATION-LOG-SECURITY-OWNER-PALLET` |
| CC 引用 | [CC-GIN-001 v1.0](CC-GIN-001.md)，Closed（冻结基线） |
| 模块 | `ginlong_apis` / `worlddepot` |
| 工作类型 | 安全修复、addon 基础结构 |
| 实施负责人 | Codex；授权人：李建强 |
| 开始时间 | 2026-11-17 10:32 Asia/Shanghai |
| 最后更新 | 2026-11-17 12:00 Asia/Shanghai |
| 当前实施状态 | Installed；真实 Secret/认证及 Odoo 组件测试通过；WMS 只读 ORM 冒烟通过；Human Review APPROVED，CC-GIN-001 v1.0 Closed |
| Branch | `main` |
| Base Commit | `63c25840cf8aba8c4f3a252c6f97177ee610cde2` |

## 2. Coding Contract 基线

| 项 | 引用 |
|---|---|
| Scope | CC-GIN-001 v1.0 §3 |
| 允许/禁止边界 | CC-GIN-001 v1.0 §4 |
| 必需变更 | CC-CHANGE-001/002/003 |
| 保留行为 | CC-PRESERVE-001–005 |
| TDD 防护栏 | T-SEC-001、T-LOG-001、T-WMS-001 |
| 测试契约 | CC-TEST-001–004 |
| 停止条件与完成标准 | CC-GIN-001 v1.0 §12–13 |
| 上游基线 | SRS v1.0 Frozen、TDD v0.3 Frozen with Open Items、Implementation Plan v1.0 Frozen |

Owner 与托盘生命周期工作不属于本 CC；依赖上游文档更新和后续 CC。

## 3. 当前实施状态摘要

| 项 | 状态 |
|---|---|
| CC-CHANGE 落实进度 | 3 / 3 已实施 |
| Preservation Impact | 认证、Token、日志脱敏及 7 项 Odoo 测试通过；WMS 模型/只读 ORM 冒烟与变更影响检查通过，未执行业务写入流程，见 ATR-GIN-001 |
| Deviation | Approved process exception：按用户指令在模板同步 BLOCKED 时冻结 CC 并实施 |
| Stop Condition 触发 | 否 |
| Open Issues | 项目模板来源同步仍 BLOCKED；WMS 操作流程没有独立自动化套件，本 CC 未做业务单据/库存写入测试。Owner/托盘上游事项为后续阶段门禁 |
| Revert 发生 | 否 |
| 当前状态 | CC-GIN-001 v1.0 已经 Human Review APPROVED 并关闭；后续阶段独立推进 |

## 4. 实施历史条目（仅追加）

### IHR-001

| 字段 | 值 |
|---|---|
| 时间 | 2026-11-17 10:32 Asia/Shanghai |
| 阶段 | Implementation / Governance |
| Action | 按李建强明确指令将 CC-GIN-001 冻结为 v1.0，并开始阶段 0 实施；将 Plan 阶段 0 映射回填为实际 CC |
| Reason | 执行“冻结cc-01，进入实施” |
| Files / Components | `docs/implementation/CC-GIN-001.md`；`docs/implementation/IMPLEMENTATION_PLAN_ginlong_apis.md` |
| Contract Reference | CC-GIN-001 v1.0；CC-CHANGE-001–003 |
| Upstream Reference | SRS v1.0；TDD v0.3；Implementation Plan v1.0 |
| Result | Completed |
| Deviation | Approved；模板来源同步为 BLOCKED，未伪记为通过 |
| Follow-up | 实际编码、ATR 验证和 FR 尚未完成 |

### IHR-002

| 字段 | 值 |
|---|---|
| 时间 | 2026-11-17 10:36 Asia/Shanghai |
| 阶段 | Implementation |
| Action | 完成 CC-CHANGE-001–003：只对认证端点的 API 日志副本遮蔽 `api_secret` / `access_token`，移除 validator 的原始 Token 日志，建立最小 `ginlong_apis` addon；新增组件测试 |
| Reason | 落实 CC-GIN-001 v1.0；保留 API 响应、现有日志模型及非凭据业务 Payload |
| Files / Components | `mymodules/worlddepot/controllers/api_logs.py`；`mymodules/worlddepot/controllers/validator_token.py`；`mymodules/worlddepot/__manifest__.py`；`mymodules/worlddepot/tests/`；`mymodules/ginlong_apis/` |
| Contract Reference | CC-CHANGE-001–003；CC-PRESERVE-001–005 |
| Upstream Reference | SRS v1.0；TDD v0.3；Implementation Plan v1.0 |
| Result | 代码变更完成；`py_compile` 通过；组件验证结果见 ATR-GIN-001 / ATR-RUN-001 |
| Deviation | 无范围偏移；未改动 `auditlog`、WMS 订单、货主关系、Package、库存或盘点模型 |
| Follow-up | 目标数据库恢复后执行 Odoo 安装/升级与集成回归；本条不表示 CC 已关闭 |

### IHR-003

| 字段 | 值 |
|---|---|
| 时间 | 2026-11-17 10:43 Asia/Shanghai |
| 阶段 | Verification / Evidence |
| Action | 直接执行新增 Odoo 测试类的 7 个组件测试方法（绕过 DB setUp）、运行 Python 语法检查；探测目标数据库与依赖 addon |
| Reason | 按 CC 测试契约建立可复核证据并判定 Odoo Runtime 验收条件 |
| Files / Components | [ATR-GIN-001](ATR-GIN-001.md)；`venv/bin/python`；`odoo.conf` |
| Contract Reference | CC-TEST-001–004；CC-PRESERVE-001–005 |
| Upstream Reference | SRS v1.0；TDD v0.3；Implementation Plan v1.0 |
| Result | 当时沙箱环境未能建立真实 Odoo 验证；该状态由后续 IHR-004 的 Odoo Shell ORM 结果更新，原 Run 记录保留 |
| Deviation | 未新建数据库或虚拟环境；未声称完整 Odoo / WMS 集成通过 |
| Follow-up | PostgreSQL 服务及项目运行依赖恢复后，追加 ATR Run 执行 CC-TEST-004 和真实 Odoo 回归 |

### IHR-004

| 字段 | 值 |
|---|---|
| 时间 | 2026-11-17 11:14 Asia/Shanghai |
| 阶段 | Verification / Environment and Module Dependencies |
| Action | 按用户限制使用现有 `venv`、`odoo.conf` 和 Odoo Shell；通过 ORM 检查并刷新模块清单，在新 Shell 会话复核模块状态、依赖状态和模型注册 |
| Reason | 继续完成 CC-GIN-001 真实 Odoo 验证；按用户澄清的数据流，Odoo 使用标准 `stock.picking` 记录 KR 实际作业结果；不安装扫码模块、不新建数据库或环境 |
| Files / Components | [ATR-GIN-001](ATR-GIN-001.md)；[Implementation Plan](IMPLEMENTATION_PLAN_ginlong_apis.md)；Odoo ORM `ir.module.module` |
| Contract Reference | CC-TEST-001–004；CC-PRESERVE-001–005 |
| Upstream Reference | SRS v1.0；TDD v0.3；Implementation Plan v1.0 |
| Result | Shell 成功连接 `odooce_karlrapp`。ORM 确认 `ginlong_apis=uninstalled`、`worlddepot=to install`、`stock_barcode=uninstallable`；WorldDepot 依赖中只有该扫码依赖不可安装，认证/Token/API log 模型未注册，标准 `stock.picking` 已注册。真实 Odoo 测试和 WMS 回归仍 BLOCKED |
| Deviation | 仅以 ORM 执行 module list refresh 并提交模块目录元数据；未安装/启用任何模块、未创建业务记录、未直接访问 PostgreSQL、未改动代码或 WMS / stock.picking |
| Follow-up | 按用户要求停止范围外修复；不通过安装 `stock_barcode` 或拆改现有扫码控制器来解除依赖。待取得批准的无扫码依赖运行基线后执行 ATR-RUN-003 |

### IHR-006

| 字段 | 值 |
|---|---|
| 时间 | 2026-11-17 11:23–11:26 Asia/Shanghai |
| 阶段 | Implementation Deviation / Odoo Runtime Verification |
| Action | 按 IHR-005 已获批准的范围，仅从 WorldDepot manifest 移除 `stock_barcode` 依赖声明；通过 Odoo Shell ORM 刷新模块清单并调用 Ginlong 的标准立即安装方法，随后在新会话复核结果 |
| Reason | 满足项目不使用仓库扫码且不得安装 / 启用 `stock_barcode` 的约束，继续验证 CC-GIN-001 |
| Files / Components | `mymodules/worlddepot/__manifest__.py`；`ir.module.module` ORM；[ATR-GIN-001](ATR-GIN-001.md)；[Implementation Plan](IMPLEMENTATION_PLAN_ginlong_apis.md) |
| Contract Reference | CC-GIN-001 v1.0；用户 2026-11-17 对 manifest 依赖修改的明确授权 |
| Upstream Reference | SRS v1.0；TDD v0.3；Implementation Plan v1.0 |
| Result | ORM 确认 WorldDepot 依赖列表不再含 `stock_barcode`。Ginlong 安装失败并回滚：WorldDepot `models/__init__.py` 仍导入 `my_package_barcode.py`，运行时报 `ModuleNotFoundError: No module named 'odoo.addons.stock_barcode'`。新 Shell 确认 Ginlong / WorldDepot 均未安装、扫码模块未启用、`stock.picking` 仍已注册 |
| Deviation | 仅实施用户明确授权的 manifest 依赖声明变更；未改扫码控制器导入、订单、`stock.picking`、库存或业务数据 |
| Follow-up | 等待用户对移除 `my_package_barcode` 导入的授权答复；若不批准，该 blocker 按范围保持 BLOCKED。不得安装扫码模块 |

### IHR-008

| 字段 | 值 |
|---|---|
| 时间 | 2026-11-17 11:34–11:37 Asia/Shanghai（用户授权后、安装验证前实施） |
| 阶段 | Approved Scope Adjustment / Implementation |
| Action | 从 `mymodules/worlddepot/models/__init__.py` 移除 `from . import my_package_barcode`；保留 `my_package_barcode.py` 文件和其余模型导入 |
| Reason | 用户明确说明项目不使用仓库扫码，并授权禁用扫码扩展导入，以解除该扩展对不可安装 `stock_barcode` 的运行依赖 |
| Files / Components | `mymodules/worlddepot/models/__init__.py`；扫码模块仍未安装 / 启用 |
| Contract Reference | CC-GIN-001 v1.0；用户 2026-11-17 明确授权答复 |
| Result | 变更文件 `py_compile` 通过；后续 WorldDepot 与 Ginlong 安装 / 升级成功，详见 IHR-009 / ATR-RUN-004 |
| Deviation | 这是对 CC §4.1 原允许修改文件清单的用户授权调整；仅停用扫码扩展入口，不修改 `stock.picking`、订单、库存、Package 或其他 WMS 代码 |
| Follow-up | 确认业务端不依赖扫码路由及 `pallet_name` 扩展；该项目明确不使用仓库扫码。源码文件留存但不加载 |

### IHR-009

| 字段 | 值 |
|---|---|
| 时间 | 2026-11-17 11:37–11:40 Asia/Shanghai |
| 阶段 | Verification / Odoo Installation, Tests and ORM |
| Action | 在现有 `odooce_karlrapp` 上通过 Odoo Shell ORM 安装 / 升级 `ginlong_apis` / `worlddepot`；使用 Odoo 标准 Shell test runner 执行 WorldDepot 测试；以 ORM 验证 Token / API log 并检查最终状态 |
| Reason | 继续完成 CC-GIN-001 真实 Odoo 验证；遵守不直接访问 PostgreSQL、不安装扫码模块、复用现有环境并保护业务数据的约束 |
| Files / Components | [ATR-GIN-001](ATR-GIN-001.md)；[Implementation Plan](IMPLEMENTATION_PLAN_ginlong_apis.md)；`ir.module.module`、`world.depot.api.user`、`world.depot.api.token`、`world.depot.api.log`、WMS / `stock.picking` 模型 |
| Contract Reference | CC-TEST-001–004；CC-PRESERVE-001–005；CC-GIN-001 v1.0 |
| Upstream Reference | SRS v1.0；TDD v0.3；Implementation Plan v1.0 |
| Result | `worlddepot=installed`、`ginlong_apis=installed`、`stock_barcode=uninstallable`；WorldDepot 依赖不含扫码模块；Odoo 标准运行器 7 项，0 错误 / 0 失败 / 0 跳过。Token / API log ORM 写读通过并回滚。Secret 哈希曾因缺 bcrypt backend 阻塞，由后续 IHR-010 / ATR-RUN-005 解锁并复验。WMS 模型注册成功；未执行业务写入流程 |
| Deviation | 所有数据库交互仅由 Odoo Shell ORM / Odoo 测试框架执行；未用 SQL/psycopg2/psql，未新建环境 / 数据库，未安装或启用 `stock_barcode`，未写业务订单、库存、Package 或 picking 数据。临时 ORM 测试记录在事务内回滚，后续会话查询为 0 |
| Evidence | ATR-RUN-004，E-012–E-017 |
| Follow-up | 由于真实 Secret 哈希认证 BLOCKED、HTTP E2E 和 WMS 行为回归未运行，不生成 FR、不申请关闭 CC。是否补齐项目现有 venv 的 bcrypt backend 后复测，由项目负责人决定；不在本次擅自安装依赖 |


### IHR-010

| 字段 | 值 |
|---|---|
| 时间 | 2026-11-17 11:40–12:00 Asia/Shanghai |
| 阶段 | Dependency Repair / Verification / Handoff |
| Action | 按用户明确授权，在既有项目 venv 安装独立 `mymodules/worlddepot/requirements.txt` 中的 `passlib==1.7.4` 与 `bcrypt==4.0.1`；通过现有 Odoo Shell ORM 验证真实 API User Secret 哈希/校验、既有认证 controller、Token validator 和日志凭据保护；重跑 CC 组件测试并执行只读 WMS ORM 冒烟；更新 ATR、计划进度并生成 FR |
| Reason | 解除 ATR-RUN-004 已确认的 bcrypt backend 缺失阻塞，完成用户要求的 CC-GIN-001 复验和关闭评审申请 |
| Files / Components | `mymodules/worlddepot/requirements.txt`；`.gitignore`；[ATR-GIN-001](ATR-GIN-001.md)；[Implementation Plan](IMPLEMENTATION_PLAN_ginlong_apis.md)；[FR-GIN-001](FR-GIN-001.md)；现有 `world.depot.api.user`、认证 controller、Token validator、API log 和 WMS ORM 模型 |
| Contract Reference | CC-GIN-001 v1.0；CC-TEST-001–004；CC-PRESERVE-001–005；CC §13 Done Criteria |
| Upstream Reference | SRS v1.0；TDD v0.3；Implementation Plan v1.0（Frozen） |
| Result | bcrypt 4.0.1 安装成功，`pip check` 无 broken requirements；passlib backend=`bcrypt`，真实 ORM 生成 `$2b$14$` Secret hash，正确 Secret 验证为 True、错误 Secret 为 False。真实认证 controller 正确/错误凭据及 Token 发放、validator 有效/无效/过期 Token 检查通过。Odoo runner 7 项 0 fail/error/skip。现有日志不含临时 Secret/Token；临时 API 用户 / Token / 日志均回滚或 ORM 清理。模块依赖与安装、WMS 相关模型注册和只读查询通过。FR-GIN-001 v0.1 提交 Human Review |
| Deviation | 只安装用户授权的兼容依赖；未修改 WorldDepot 原有认证算法或业务代码。数据库仅通过 Odoo Shell ORM / 标准测试运行器访问；未新建数据库或虚拟环境、未安装/启用 `stock_barcode`、未写业务订单或库存数据。依赖文件由 `.gitignore` 精确例外纳入版本控制 |
| Evidence | ATR-RUN-005，E-019–E-024 |
| Follow-up | Human Reviewer 决定是否关闭 CC；FR 不代表已关闭、合并或发布。模板同步继续 BLOCKED；真实 HTTP 网络/Ginlong 联调及 WMS 写入流程未作为本 CC 验证执行 |


### IHR-011

| 字段 | 值 |
|---|---|
| 时间 | 2026-11-17 |
| 阶段 | Human Review / Contract Closure |
| Action | 按李建强的 Human Review 决定，将 CC-GIN-001 v1.0 状态更新为 Closed；将 FR-GIN-001 更新为 v1.0 并记录 Human Review APPROVED；更新 Implementation Plan 阶段状态；创建 CC-GIN-002 v0.1 Draft |
| Reason | 用户明确批准依据 FR-GIN-001 v0.1、IHR-GIN-001 v0.6、ATR-GIN-001 v0.5 关闭 CC-GIN-001，并要求起草下一 Coding Contract |
| Files / Components | [CC-GIN-001](CC-GIN-001.md)；[FR-GIN-001](FR-GIN-001.md)；[Implementation Plan](IMPLEMENTATION_PLAN_ginlong_apis.md)；[CC-GIN-002 Draft](CC-GIN-002.md) |
| Contract Reference | CC-GIN-001 v1.0 §13–15；拟议 CC-GIN-002 v0.1（Draft） |
| Result | Human Review：APPROVED；CC-GIN-001 v1.0：Closed；FR-GIN-001 v1.0：正式关闭。阶段 1 可进入 CC-GIN-002 起草/评审；多货主与托盘生命周期依然保留，且须先更新并批准上游基线后才能冻结/实施受影响内容 |
| Deviation / Limits | 本条不把 HTTP E2E、WMS 流程写入验证或模板同步状态改为 PASS；CC-GIN-001 范围仍只限阶段 0。CC-GIN-002 仍为 Draft，不代表实施授权 |
| Evidence | 用户 2026-11-17 Human Review 决定；FR-GIN-001 v1.0；Plan v1.0 当前进度记录 |

## 5. 实际变更清单（当前快照）

| 文件 | 动作 | 实际变更 | CC 来源 | IHR |
|---|---|---|---|---|
| `mymodules/worlddepot/controllers/api_logs.py` | 修改 | 在现有 API logger 中仅对两个已确认认证端点的日志副本遮蔽请求 `api_secret` 及响应 `access_token`；日志字段 `data` 同步使用遮蔽结果；认证请求无法解析时不保留原始请求体 | CC-CHANGE-001 | IHR-002 |
| `mymodules/worlddepot/controllers/validator_token.py` | 修改 | 无效与过期 Token 的应用日志不再写出 Token 原文；响应与校验流程不变 | CC-CHANGE-002 | IHR-002 |
| `mymodules/worlddepot/__manifest__.py` | 修改 | 模块版本 `0.1` → `0.2`；按用户明确授权移除 `stock_barcode` 依赖声明（见 IHR-005/006） | CC-CHANGE-001–003；IHR-005 deviation | IHR-002/006 |
| `mymodules/worlddepot/models/__init__.py` | 修改 | 按用户授权移除扫码扩展 `my_package_barcode` 的导入；保留源文件，禁用该扫码扩展入口，不改变其他 WMS / `stock.picking` 逻辑 | 经授权的运行依赖处置 | IHR-008 |
| `mymodules/worlddepot/tests/` | 新增 | 添加认证日志、非认证业务报文、Token validator 与 logger fallback 自动化组件测试 | CC-TEST-001–004 | IHR-002 |
| `mymodules/ginlong_apis/` | 新增 | 只依赖 `worlddepot` 的最小可安装 addon 骨架，无 Ginlong 路由或业务模型 | CC-CHANGE-003 | IHR-002 |
| `docs/implementation/ATR-GIN-001.md` | 修改 | 保留 ATR-RUN-001–004 历史，追加 ATR-RUN-005 bcrypt、真实 Odoo 认证、回归及范围限定证据 | CC-TEST-001–004 | IHR-004/006/009/010 |
| `docs/implementation/IMPLEMENTATION_PLAN_ginlong_apis.md` | 修改 | 更新阶段 0 安装 / 测试进度和运行时阻塞；保持 Plan v1.0 基线不变 | 阶段 0 进度快照 | IHR-004/006/009 |
| `mymodules/worlddepot/requirements.txt` | 新增 | 独立运行依赖 `passlib==1.7.4`、`bcrypt==4.0.1`；不改 WorldDepot 认证算法 | 用户 2026-11-17 依赖修复授权 | IHR-010 |
| `.gitignore` | 修改 | 为 `mymodules/worlddepot/requirements.txt` 增加精确例外，避免被通用 requirements 忽略规则排除 | 用户要求交付独立 requirements 文件 | IHR-010 |
| `docs/implementation/FR-GIN-001.md` | 新增/更新 | v0.1 完成评估；依据 Human Review APPROVED 更新为 v1.0 正式关闭 | CC-GIN-001 §13–14 | IHR-010/011 |
| `docs/implementation/CC-GIN-002.md` | 新增 | 阶段 1 候选契约草案；明确 SRS/TDD/Plan 上游门禁，未冻结或授权编码 | Implementation Plan v1.0 阶段 1；用户要求起草 | IHR-011 |
| `docs/implementation/IHR-GIN-001.md` | 修改 | 保留历史阻塞记录，追加依赖授权、安装及 ATR-RUN-005 结果 | CC-GIN-001 §12–13 | IHR-004–010 |

## 6. 偏离与停止条件记录

| 时间 / IHR ID | 事件 | 处理 / 授权 | 状态 |
|---|---|---|---|
| 2026-11-17 / IHR-001 | CC、IHR、ATR 模板来源同步检查均为 BLOCKED；项目模板源目录缺失 | 用户明确要求冻结 CC 并实施；记录为显式流程例外，检查仍为 BLOCKED | 已记录；不影响代码范围边界 |
| 2026-11-17 11:23 / IHR-005 | CC-GIN-001 §4.1 原仅允许修改 WorldDepot manifest 版本字段；拟移除现有 `stock_barcode` 依赖声明 | 用户明确授权“批准修改WorldDepot 的 manifest 声明依赖”；实施限于删除该依赖项，不改 `my_package_barcode.py`、`models/__init__.py` 或其他 WMS 代码；不安装/启用扫码模块 | 已授权并实施；结果见 IHR-006 |
| 2026-11-17 11:34 / IHR-007 | manifest 依赖移除后，WorldDepot 初始化仍加载扫码控制器并失败 | 用户明确授权从 `models/__init__.py` 移除 `my_package_barcode` 导入；只禁用该扫码扩展入口，源码保留，不触碰其他 WMS / `stock.picking` 流程 | 已授权；变更前记录 |
| 2026-11-17 11:34 / IHR-008 | CC §4.1 原文件清单未列 `models/__init__.py` | 用户明确授权移除扫码导入；按最小范围执行并追加记录，不修改扫码源码或其他 WMS 逻辑 | 已授权并实施 |

## 7. 遗留问题与后续

| 问题 | 状态 | 后续 |
|---|---|---|
| CC/IHR/ATR 项目模板来源缺失 | BLOCKED | 有模板同步要求的后续修订前恢复来源并重新检查；不标记为 Passed |
| 真实 API Secret 哈希认证 | Closed（ATR-RUN-005） | 按用户授权安装独立 bcrypt requirements；现有 Odoo ORM 的 Secret 哈希、正反校验与认证 controller 测试通过 |
| HTTP 网络 E2E / WMS 写入流程 | 未执行（非阻塞限制） | 真实 controller/ORM、7 项 Odoo 测试和 WMS 只读模型查询已通过；本次未发起 HTTP 网络请求或写入业务单据/库存，也未改 WMS 业务逻辑 |
| `stock_barcode` 运行依赖 | 已解决（经用户授权） | WorldDepot manifest 不声明该依赖；`models/__init__.py` 不再加载扫码扩展；扫码模块仍 `uninstallable`，没有安装 / 启用 |
| Owner 与项目强制绑定解除、托盘生命周期管理未纳入批准 SRS/TDD | Open；不属于 CC-GIN-001 | 在受影响阶段前修订并批准 SRS/TDD/Plan，再分配后续 CC |

## 8. 移交摘要

CC-GIN-001 v1.0 阶段 0 实施及复验完成。按用户授权安装独立 requirements（`passlib==1.7.4`、`bcrypt==4.0.1`），未修改 `worlddepot` 认证算法或业务代码。现有 Odoo 环境中真实 ORM Secret 哈希及认证 controller / Token 校验通过；7 项 Odoo 标准测试全通过，日志凭据保护与模块/依赖状态通过。WMS 只读模型/查询冒烟通过，未执行业务单据或库存写入；没有业务数据变化。未安装/启用 `stock_barcode`。ATR-RUN-001–004 历史阻塞保留，ATR-RUN-005 更新当前状态；FR-GIN-001 v1.0 已经 Human Review APPROVED 并关闭 CC。模板来源同步仍 BLOCKED；该状态未伪记为通过。Owner/托盘模型工作继续等待上游基线更新和后续 CC。

## 附录 B — 版本历史

| 版本 | 日期 | 说明 | 状态 |
|---|---|---|---|
| v0.1 | 2026-11-17 | 建立 CC-GIN-001 v1.0 实施记录 | In Progress |
| v0.2 | 2026-11-17 | 追加 CC-CHANGE-001–003 实施事实、组件验证及 Odoo Runtime 阻塞 | In Progress |
| v0.3 | 2026-11-17 | 追加 ATR-RUN-002 的目标库 ORM 模块状态、扫码依赖来源及真实测试阻塞；未扩大代码范围 | Superseded by v0.4 |
| v0.4 | 2026-11-17 | 记录经授权的 manifest 依赖移除及 Odoo 安装失败于活动扫码控制器导入 | Superseded by v0.5 |
| v0.5 | 2026-11-17 | 记录扫码扩展导入获批停用、Odoo 安装 / 升级及 7 项测试结果，保留 bcrypt 与 WMS 回归历史 | Superseded by v0.6 |
| v0.6 | 2026-11-17 | 记录用户授权安装独立 bcrypt requirements、现有 Odoo 环境真实 Secret/认证复验、ATR-RUN-005 与 FR 评审申请；保留模板同步及 WMS 流程测试限制 | Superseded by v0.7 |
| v0.7 | 2026-11-17 | 记录 Human Review APPROVED、FR-GIN-001 v1.0 正式关闭及 CC-GIN-001 v1.0 Closed；后续需求仍在范围外 | Closed |
