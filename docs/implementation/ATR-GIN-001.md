<!-- ATR-GIN-001：记录 CC-GIN-001 v1.0 的自动化及运行时验证。项目 ATR 模板源同步检查 BLOCKED；未将其记为通过。 -->

# 自动化测试记录：ATR-GIN-001

## 0. 文档治理

本 ATR 记录 CC-GIN-001 v1.0 / IHR-GIN-001 的自动化验证证据，不作 CC 完成或发布判定。项目 ATR 模板源 `docs/context/cognition/template/Coding/ATR模板.md` 缺失，模板同步状态为 `BLOCKED`；本记录沿用技能内置 ATR 模板结构，例外不代表同步通过。

## 1. 执行元数据

| 字段 | 值 |
|---|---|
| Intent ID | `GINLONG-FOUNDATION-LOG-SECURITY-OWNER-PALLET` |
| IHR | [IHR-GIN-001](IHR-GIN-001.md) |
| CC Version | CC-GIN-001 v1.0 Frozen |
| Module | `worlddepot` / `ginlong_apis` |
| Environment | 项目 `venv`、`odoo.conf`、目标数据库 `odooce_karlrapp`；Odoo Shell 可连接；`worlddepot` / `ginlong_apis` 已安装 |
| Test Framework | 项目 `venv` Python 3；Odoo Shell ORM；Odoo 标准 `odoo.tests.shell.run_tests` |
| Code Baseline（当前） | `main@63c25840` + 当前未提交工作树；无 Git commit |
| 工作树指纹 | `main@63c25840 + CC-GIN-001 current implementation tree`；当前文件 SHA-256 见 E-018 |
| Branch | `main` |
| 执行时间 | 2026-11-17 10:36–12:00 Asia/Shanghai |
| 执行者 | Codex |

## 2. 测试契约基线

| 来源 | ID | ATR 覆盖 |
|---|---|---|
| CC Test Contract | CC-TEST-001 | 实际认证控制器与现有 logger；认证请求/响应日志遮蔽，调用方响应不变 |
| CC Test Contract | CC-TEST-002 | 无效及过期 Token 的 validator 应用日志不含 Token 原文，401 行为不变 |
| CC Test Contract | CC-TEST-003 | 实际认证控制器遇到日志写入失败时，fallback 不输出 `api_secret` 明文 |
| CC Test Contract | CC-TEST-004 | 最小 addon 安装、现有组件集成及 WMS 行为保持 |
| CC-PRESERVE | CC-PRESERVE-001–005 | 认证、API 响应、API 日志及 WMS / 库存行为保持情况；见 §6 |

## 3. 当前自动化测试状态

| 指标 | 值 |
|---|---:|
| Required Automated Test Contracts | 4 |
| Odoo Runner Tests | 7 PASS；0 FAIL；0 ERROR；0 SKIPPED（ATR-RUN-004、005 重复确认） |
| CC-TEST-001–004 | 4 PASS；含真实 Odoo ORM/controller 认证、7 项组件测试、模块安装及只读 WMS ORM 冒烟检查 |
| Additional Runtime Authentication Check | PASS：现有 venv 已安装独立 requirements 中的 bcrypt 4.0.1；真实 ORM Secret 哈希、正反验证及认证控制器检查通过 |
| WMS Regression | PASS（本 CC 范围）：模块/依赖、订单与 `stock.picking` 模型注册及只读 ORM 查询通过；未执行库存或业务单据写入流程 |
| Overall ATR Status | PASS（本 CC 范围）；模板同步仍 BLOCKED，不属于运行测试结果 |
| Latest Run | ATR-RUN-005 |
| Current Code Baseline | `main@63c25840 + 当前工作树` |
| Evidence Baseline Match | Yes（ATR-RUN-005 针对 E-025 当前工作树执行；ATR-RUN-001 的 fake ORM 结果仅作历史组件证据） |

**历史与当前结果：** ATR-RUN-001–004 的历史阻塞保持原样。ATR-RUN-005 安装 bcrypt 后，通过 Odoo Shell ORM 对真实 `world.depot.api.user` Secret 哈希生成/校验，并调用既有认证控制器验证正确与错误 Secret、Token 发放及日志凭据保护；直接控制器调用使用模拟 request envelope，不等同 HTTP 网络 E2E。Odoo 标准运行器仍为 7/7 通过。WMS 执行只读 ORM 模型/查询冒烟及变更影响检查，没有执行订单或库存写入流程，也未改变业务数据。

## 4. 核心测试契约覆盖矩阵

| CC / TEST 来源 | 自动化验证 | Run | 结果 | 证据 / 限定 |
|---|---|---|---|---|
| CC-TEST-001 | Odoo 标准运行器执行 controller/logger 组件测试；Odoo ORM Secret 与认证 controller 核验 | ATR-RUN-005 | PASS | 7 项组件测试通过；真实 API User Secret 哈希正反验证、既有认证 controller 正确/错误凭据响应、Token 发放及日志凭据遮蔽通过。controller 使用模拟 request envelope，非 HTTP 网络 E2E |
| CC-TEST-002 | Odoo 标准运行器执行 Token validator 组件测试；真实 Token 模型 ORM 与 validator 检查 | ATR-RUN-005 | PASS | 无效/过期 Token 的脱敏与 401 组件断言通过；真实 Token ORM 有效/无效/过期校验通过，临时用户与 Token 已回滚 |
| CC-TEST-003 | Odoo 标准运行器执行 logger fallback 组件测试；现有 API log ORM 写入 / 读取 | ATR-RUN-005 | PASS | fallback 故障注入不泄露 Secret；真实 logger 记录的 Secret/Token 均遮蔽；临时日志已清理，未对数据库连接做破坏性故障注入 |
| CC-TEST-004 | Ginlong / WorldDepot 安装、依赖、日志 / 认证集成及 WMS 行为保持 | ATR-RUN-005 | PASS（本 CC 范围） | 两模块 installed；`stock_barcode` 仍 uninstallable 且非依赖；API、订单与 `stock.picking` 模型注册及只读查询成功。7 项 Odoo 组件测试通过；订单/库存写入流程未执行，WMS 业务逻辑未改，项目不使用扫码 |

## 5. Test Run History（仅追加）

### ATR-RUN-001

| 字段 | 值 |
|---|---|
| Run ID | ATR-RUN-001 |
| 时间 | 2026-11-17 10:36–10:43 Asia/Shanghai |
| Code Baseline | `main@63c25840` + 当前工作树（未提交） |
| Environment | 项目现有 `venv`；目标 DB `odooce_karlrapp` 未连接 |
| Invocation | `venv/bin/python` 加载变更的 Odoo 控制器 / 测试模块，直接调用 7 个测试方法（不执行 `TransactionCase` 生命周期）；`venv/bin/python -m py_compile` 编译变更 Python 文件 |
| Scope | CC-TEST-001–004；组件模拟与语法检查，不是完整 Odoo 集成套件 |
| Expected Tests | 4 项 CC 测试契约 |
| Executed | 7 个组件测试方法覆盖 3 项 CC 契约；1 项 CC 契约因目标运行环境不可用而 BLOCKED |
| PASS / FAIL / SKIPPED / BLOCKED | 3 / 0 / 0 / 1 |
| Result | BLOCKED（组件验证通过；完整 addon 安装及 WMS 回归仍待目标 Odoo Runtime） |
| Evidence | E-001–E-004 |
| Follow-up | IHR-GIN-001；目标 PostgreSQL 与缺失的 `stock_barcode` 运行依赖恢复后，重跑 CC-TEST-004 |

### ATR-RUN-002

| 字段 | 值 |
|---|---|
| Run ID | ATR-RUN-002 |
| 时间 | 2026-11-17 11:10–11:14 Asia/Shanghai |
| Code Baseline | `main@63c25840` + 与 ATR-RUN-001 相同的代码工作树 |
| Environment | `venv/bin/python odoo-bin shell -c odoo.conf --no-http`；数据库 `odooce_karlrapp` |
| Invocation | Odoo Shell 中经 ORM 执行 `ir.module.module.update_list()` 并提交模块目录元数据；在新 Shell 会话只读复核模块、依赖及模型注册状态 |
| Scope | Odoo Runtime / ORM 状态核验；未执行模块安装或标准自动化测试 |
| Expected Tests | CC-TEST-001–004（真实 Odoo 标准测试） |
| Executed | 0 项 CC 测试；完成 ORM 环境和模块状态核验 |
| PASS / FAIL / SKIPPED / BLOCKED | 0 / 0 / 0 / 4 |
| Result | BLOCKED |
| Evidence | E-006–E-008 |
| Follow-up | 不安装扫码模块。WorldDepot 安装依赖的处置超出当前 CC 范围；获得批准的无扫码依赖运行基线后再执行 Odoo 测试 |

### ATR-RUN-003

| 字段 | 值 |
|---|---|
| Run ID | ATR-RUN-003 |
| 时间 | 2026-11-17 11:23–11:26 Asia/Shanghai |
| Code Baseline | `main@63c25840` + manifest 依赖声明调整后的工作树 |
| Environment | 现有 `venv` / `odoo.conf` / 数据库 `odooce_karlrapp` |
| Invocation | Odoo Shell ORM 刷新 `ir.module.module`；使用 ORM 调用 `ginlong_apis.button_immediate_install()`；异常时 `env.cr.rollback()`；在新的 Shell 会话只读复核状态 |
| Scope | 验证获批 manifest 修改后的依赖发现、模块安装可行性和回滚结果；未安装或启用 `stock_barcode` |
| Expected Tests | CC-TEST-001–004（真实 Odoo 标准测试） |
| Executed | 0 项 CC 测试；尝试安装 Ginlong 后在 WorldDepot Python 导入阶段失败 |
| PASS / FAIL / SKIPPED / BLOCKED | 0 / 0 / 0 / 4 |
| Result | BLOCKED |
| Evidence | E-009–E-011 |
| Follow-up | `worlddepot/models/__init__.py` 仍导入 `my_package_barcode.py`，其直接导入缺失的 `odoo.addons.stock_barcode`；等待该扫码导入点的授权处置 |

### ATR-RUN-004

| 字段 | 值 |
|---|---|
| Run ID | ATR-RUN-004 |
| 时间 | 2026-11-17 11:37–11:40 Asia/Shanghai |
| Code Baseline | `main@63c25840` + 当前工作树；WorldDepot manifest 依赖移除及扫码导入停用后的代码 |
| Environment | 项目现有 `venv` / `odoo.conf` / `odooce_karlrapp`；仅通过 Odoo Shell ORM / 标准测试运行器访问数据库 |
| Invocation | `venv/bin/python odoo-bin shell -c odoo.conf --no-http`；Shell 内调用 `odoo.tests.shell.run_tests(env, '/worlddepot', modules=['worlddepot'], reload_tests=True)`；另以 Shell ORM 调用 `button_immediate_upgrade()`，并执行临时 Token/API log ORM 创建、读取后 `env.cr.rollback()` |
| Scope | CC-TEST-001–004；API Secret / Token / API log 运行时核验；WorldDepot / Ginlong 安装和 WMS 模型注册 |
| Automated Tests | Odoo 标准测试运行器发现 7 项；7 PASS，0 FAIL，0 ERROR，0 SKIPPED |
| Result | BLOCKED（自动化组件与安装验证通过；真实 API Secret 哈希认证缺少 bcrypt backend；独立 WMS 业务回归未运行） |
| Evidence | E-012–E-017 |
| Log Review | 检查 `debug_logs/odoo_181.log`。保留此前 ATR-RUN-003 的扫码导入失败历史；该失败之后未发现新的 ERROR / CRITICAL / Traceback。当前运行时仍输出既有 Odoo create-batch deprecation warnings |
| Data Safety | Secret 创建尝试因缺 backend 失败并回滚；Token / API log 临时记录在 Shell 事务内创建、读取并回滚。临时记录复核计数均为 0。未修改订单、库存、Package 或 `stock.picking` 数据 |
| Follow-up | 按授权移除扫码模型导入后重装成功；不安装 `stock_barcode`。不擅自安装 bcrypt；由授权方决定补齐环境依赖后是否复测真实 API User Secret。独立 WMS 行为没有现成测试，须在能定义安全、无生产数据副作用的验收场景后再测。此 Run 不关闭 CC |

### ATR-RUN-005

| 字段 | 值 |
|---|---|
| Run ID | ATR-RUN-005 |
| 时间 | 2026-11-17 11:40–12:00 Asia/Shanghai |
| Code Baseline | `main@63c25840` + 当前未提交工作树；新增 WorldDepot 独立依赖清单 |
| Environment | 项目现有 `venv`、`odoo.conf`、数据库 `odooce_karlrapp`；Python 3.11.9；所有数据库交互只经 Odoo Shell ORM / Odoo 测试运行器 |
| Dependency | `mymodules/worlddepot/requirements.txt`：`passlib==1.7.4`、`bcrypt==4.0.1`；`pip check` 无损坏依赖 |
| Invocation | 在现有 venv 安装独立 requirements；Odoo Shell ORM 创建临时 API User 并验证 Secret；调用现有 `/token`、`/getToken` 对应认证 controller 与 `validator_token.validate_token`；调用 `run_tests(env, '/worlddepot', modules=['worlddepot'], reload_tests=True)`；只读 ORM 查询安装状态、模型和数据；所有临时 ORM 记录回滚 / 清理 |
| Scope | 修复依赖后真实 Secret 哈希/校验、认证 controller、Token validator、日志脱敏、CC-TEST-001–004 复验和 WMS 只读冒烟 |
| Runtime Authentication | PASS：Passlib bcrypt backend 正常；正确 Secret 验证通过，错误 Secret 拒绝；controller 的成功/失败结果及 Token 发放行为符合既有响应；有效 Token 关联用户，无效 / 过期 Token 返回既有 401 结果 |
| Automated Tests | Odoo 标准运行器 7 项；7 PASS，0 FAIL，0 ERROR，0 SKIPPED |
| Result | PASS（本 CC 范围） |
| Log Review | 扫描 `debug_logs/odoo_181.log` 的全部 ERROR / CRITICAL / Traceback；仅存在 2026-11-17 03:24 前的历史模块依赖与扫码导入失败，之后无新的 ERROR / CRITICAL / Traceback。测试运行中的既有 Odoo deprecation warnings 不属于本次失败 |
| Data Safety | API User / Token 临时 ORM 记录回滚；logger 独立游标写入的临时日志通过 ORM 清理并复查为 0；未新增订单、产品、库存、Package 或 `stock.picking` 数据，无业务数据变化 |
| WMS Regression | 模块依赖与安装状态、API/订单/`stock.picking` 模型注册、只读 `search_count` 冒烟成功；未执行业务单据或库存写入流程。WMS 业务源文件未改；扫码扩展停用是用户明确授权且项目不使用扫码 |
| Limitations | 使用真实 Odoo registry/ORM/model/controller，但 request envelope 为模拟对象；未发起真实 HTTP 网络请求或 Ginlong 外部请求。无既有独立 WMS 流程自动化套件 |
| Evidence | E-019–E-024 |
| Follow-up | 生成 FR-GIN-001 v0.1，提交 Human Review 申请关闭 CC；不自行关闭、合并或发布 |

## 6. 回归验证（映射 CC-PRESERVE）

| CC-PRESERVE | 验证 | Run | 结果 | 限定 |
|---|---|---|---|---|
| CC-PRESERVE-001 | Secret 哈希认证、Token 发放 / 校验及 401 行为 | ATR-RUN-005 | PASS | 真实 Odoo ORM Secret 哈希正反校验、认证 controller 成功 / 错误响应及实际 validator 有效 / 无效 / 过期 Token 行为通过；临时记录已回滚 |
| CC-PRESERVE-002 | `/getToken` 与 `/token` 客户端响应 | ATR-RUN-005 | PASS（controller 响应） | 真实既有 controller 直接调用确认两种成功响应结构及错误响应；未执行 HTTP socket/network E2E |
| CC-PRESERVE-003 | 既有 API log ORM 字段及非认证业务 Payload | ATR-RUN-005 | PASS | API log ORM 创建 / 读取及 Secret/Token 脱敏通过；非凭据业务字段组件测试保持；临时日志已清理 |
| CC-PRESERVE-004 | 项目、订单与现有 WMS 收发货流程 | ATR-RUN-005 | PASS（影响范围检查 + 只读 ORM） | 订单/WMS 业务模型源码未改，相关模型和查询成功；本次未执行创建/过账业务单据流程，也未改业务数据 |
| CC-PRESERVE-005 | `stock.picking` 执行结果记录及库存行为 | ATR-RUN-005 | PASS（影响范围检查 + 只读 ORM） | 标准 `stock.picking` 注册及只读查询通过，相关库存/拣货业务代码未改；没有执行库存操作或修改 picking 数据 |

## 7. Issues（当前快照）

| ID | 测试 | Run | 类型 | 原因 | 状态 | 后续 |
|---|---|---|---|---|---|---|
| ATR-ISSUE-001 | CC-TEST-004 安装阻塞 | ATR-RUN-003/004 | 已解决（经授权） | 用户授权移除 `my_package_barcode` 导入；Ginlong / WorldDepot 安装及升级现已成功 | Closed | 保留扫码文件但不导入、不安装或启用 `stock_barcode` |
| ATR-ISSUE-002 | 文档模板同步 | ATR-RUN-001 | BLOCKED | 项目模板源目录不存在 | Open | 恢复模板源后按流程检查；不将其写成 Passed |
| ATR-ISSUE-003 | 真实 API Secret 哈希认证 | ATR-RUN-004/005 | Closed | venv 安装独立 bcrypt 依赖后，真实 Odoo ORM Secret 哈希、验证及认证 controller 检查通过 | Closed | 依赖约束记录在 `mymodules/worlddepot/requirements.txt` |
| ATR-ISSUE-004 | WorldDepot 业务回归范围 | ATR-RUN-005 | Non-Blocking limitation | 无独立 WMS 操作回归套件；本次完成安装 / 模型 / 只读 ORM 冒烟和源变更影响检查，未进行单据/库存写入 | Open | 后续涉及 WMS 业务逻辑变更时，另按对应 CC 定义流程级回归；本 CC 未改这些业务代码 |

## 8. 专项验证

- **真实 ORM / 认证：**ATR-RUN-005 在现有数据库创建临时 `world.depot.api.user` 并真实运行 Secret 哈希、正确/错误 Secret 验证、Token 发放和 validator 检查；所有临时 API 用户及 Token 均回滚。
- **日志安全：**真实认证 controller 调用通过现有 logger 记录；复核日志及 fallback 中不含测试 Secret/Token 明文。Odoo 7 项组件测试全部通过，覆盖控制器日志、validator 和 logger fallback。
- **层级限定：**controller 使用模拟 request envelope；不是 HTTP socket/network E2E，也没有连接 Ginlong。WMS 使用只读 ORM / 影响范围检查，没有创建或过账 WMS 单据、没有操作库存。
- **Coverage：**不适用；CC 未要求覆盖率门槛。

## 9. Evidence Inventory

| Evidence ID | 类型 | 位置 / 内容 | 对应 Run |
|---|---|---|---|
| E-001 | Python 语法检查 | `venv/bin/python -m py_compile` 对 logger、validator、新测试及 addon Python / manifest 文件执行，退出码 0 | ATR-RUN-001 |
| E-002 | 组件测试 | `mymodules/worlddepot/tests/test_api_log_credentials.py` 的 7 个测试方法均直接执行并通过；fake ORM / request；未执行 Odoo `TransactionCase` setUp 或真实数据库 | ATR-RUN-001 |
| E-003 | 故障注入 | `test_api_log_failure_fallback_does_not_print_auth_secret` 调用实际认证控制器；API log 写入失败时 fallback 不含测试 Secret，成功响应保持 | ATR-RUN-001 |
| E-004 | 环境探测 | `pg_isready -h 127.0.0.1 -p 5555` 返回 no response；在配置 addon 路径中查找 `stock_barcode` 无结果 | ATR-RUN-001 |
| E-005 | 当前代码指纹 | `api_logs.py` `10c947f2…d4caddedd8`；`validator_token.py` `7dbbde81…b8bb61ff`；WorldDepot manifest `885dfe9d…ee593fa`；测试 `b7a909bb…0913423`；Ginlong manifest `bd2f0dab…d1af3d42`；Ginlong init `8b5c97ca…a4eacce06` | ATR-RUN-001 |
| E-006 | Odoo Shell ORM | 模块清单刷新后，`ginlong_apis=uninstalled`、`worlddepot=to install`、`stock_barcode=uninstallable`；Ginlong 依赖 WorldDepot，WorldDepot 依赖项中包含 `stock_barcode` | ATR-RUN-002 |
| E-007 | Odoo Shell ORM | 新 Shell 会话确认 `world.depot.api.log`、`world.depot.api.user`、`world.depot.api.token` 未注册；标准 `stock.picking` 已注册；WorldDepot 其他依赖状态为 installed | ATR-RUN-002 |
| E-008 | 源码依赖追踪 | WorldDepot manifest 声明 `stock_barcode`；`models/__init__.py` 导入 `my_package_barcode.py`，该文件继承扫码控制器并注册 `/stock_barcode/*` 路由 | ATR-RUN-002 |
| E-009 | Odoo Shell ORM | 移除 manifest 声明并刷新模块清单后，WorldDepot ORM 依赖列表不再含 `stock_barcode`；Ginlong 显示 `uninstalled`，扫码模块仍为 `uninstallable` | ATR-RUN-003 |
| E-010 | Odoo Shell ORM 安装尝试 | `ginlong_apis.button_immediate_install()` 失败：`ModuleNotFoundError: No module named 'odoo.addons.stock_barcode'`；异常后执行 ORM transaction rollback | ATR-RUN-003 |
| E-011 | Odoo Shell ORM | 新会话确认 Ginlong / WorldDepot 均未安装，`stock_barcode` 未启用；WorldDepot API 模型仍未注册，`stock.picking` 仍注册 | ATR-RUN-003 |
| E-012 | Odoo 标准测试运行器 | `run_tests(env, '/worlddepot', modules=['worlddepot'], reload_tests=True)`：7 tests run，0 errors，0 failures，0 skipped | ATR-RUN-004 |
| E-013 | Odoo Shell ORM | Secret 哈希验证尝试在 passlib bcrypt 后端加载处失败：`MissingBackendError: bcrypt: no backends available`；异常经 Shell 外层 transaction rollback；数据库中 API User 原有记录数为 0 | ATR-RUN-004 |
| E-014 | Odoo Shell ORM | 临时 Token ORM create/search 与 `world.depot.api.log` create/read 均通过；结束时 `env.cr.rollback()`；新 Shell 中对应临时记录计数为 0 | ATR-RUN-004 |
| E-015 | Odoo Shell ORM | 最终状态：`worlddepot=installed`、`ginlong_apis=installed`、`stock_barcode=uninstallable`；WorldDepot 依赖不含 `stock_barcode`；API log/user/token、入库单、出库单及 `stock.picking` 均注册 | ATR-RUN-004 |
| E-016 | Odoo Shell ORM | `worlddepot.button_immediate_upgrade()` 返回 Odoo 标准 `ir.actions.act_url`；新 Shell 复核模块仍为 installed | ATR-RUN-004 |
| E-017 | 日志检查 / Python 语法检查 | 检查 `debug_logs/odoo_181.log`；后续安装 / 升级后无新 ERROR/CRITICAL/Traceback，较早扫码导入失败保留为历史。变更 Python 文件 `py_compile` 退出码 0 | ATR-RUN-004 |
| E-018 | 当前工作树 SHA-256 | `api_logs.py` `10c947f2…d4caddedd8`；`validator_token.py` `7dbbde81…b8bb61ff`；WorldDepot manifest `d49c0b6d…4a427b98`；models init `4f113c34…86722d7`；组件测试 `b7a909bb…0913423`；Ginlong manifest `bd2f0dab…d1af3d42`；Ginlong init `8b5c97ca…4eacce06` | ATR-RUN-004 |
| E-019 | 依赖检查 | `mymodules/worlddepot/requirements.txt` pin `passlib==1.7.4`、`bcrypt==4.0.1`；现有 venv Python 3.11.9；`pip check` 返回 `No broken requirements found` | ATR-RUN-005 |
| E-020 | bcrypt backend 自检 | 现有 venv `CryptContext(schemes=['bcrypt'], bcrypt__rounds=14)` 生成 `$2b$14$` hash；backend=`bcrypt`；正确 secret=True、错误 secret=False | ATR-RUN-005 |
| E-021 | 真实 Odoo ORM / controller 认证 | 临时 API User ORM 创建生成 bcrypt Secret hash；真实既有 `/token` 与 `/getToken` controller 正确凭据发 token、错误凭据拒绝；API 日志未含测试 Secret / access_token 明文 | ATR-RUN-005 |
| E-022 | 真实 Odoo Token validator | 真实 ORM Token 通过有效 / 无效 / 过期 validator 场景；invalid / expired 返回既有 401；临时 User / Token 回滚 | ATR-RUN-005 |
| E-023 | Odoo 标准测试与 WMS ORM smoke | 7 tests run，0 errors / failures / skipped；`worlddepot` / `ginlong_apis` installed、`stock_barcode` uninstallable 且不在 WorldDepot 依赖中；相关 WMS / `stock.picking` 模型注册并支持只读 ORM 查询，无业务数据写入 | ATR-RUN-005 |
| E-024 | 日志、清理与工作树检查 | Odoo log 中 03:24 历史依赖错误之后无新 ERROR / CRITICAL / Traceback；临时 API User / Token / API log 复核为 0；`git diff --check` 通过 | ATR-RUN-005 |
| E-025 | 当前实现基线 SHA-256 | `.gitignore` `b059e93fb386952cd038c1743d106e0faad432f7ae7fc68ca7c6b4d39457f044`；requirements `a66fba5f1f47725e726adaf4a2ee6f7e184dae4bd075e8fb44e8ccff97065632`；logger `10c947f210a223061474dd6387f5c0d7abc5b60216e77fe2ceea391d4cadedd8`；validator `7dbbde81c1b8ad6073df5908ec62bbb73d83c8dc1e4dfc468bff4428b3bb61ff`；WorldDepot manifest `d49c0b6dfd4f619355751ccb44788b081094ea3dd7002862c3c2c1514a427b98`；models init `4f113c34a842955fd3f33b587aa4b33eb2229d7414422dfb6bc53b97386722d7`；tests `b7a909bb1b887566831c31c4d3bac757b085501329277c475af4618580913423`；Ginlong manifest `bd2f0dab8221814f6bc0cbdf39c8b92918dbc9ffd8bf299758124394d1af3d42`；Ginlong init `8b5c97ca5b260533fe0442c590074cf45204b5efd1040aaae9358e5a4eacce06` | ATR-RUN-005 |

## 10. 移交摘要

ATR-RUN-005 安装 `passlib==1.7.4` / `bcrypt==4.0.1` 后，真实 Odoo ORM Secret 哈希、正反校验、既有认证 controller、Token 发放 / 验证均通过；现有 logger 不记录测试凭据。Odoo 标准运行器 7 项测试全部通过，模块安装状态、依赖和 WMS 模型/只读查询通过。未执行真实 HTTP 网络请求、Ginlong 联调或 WMS 写入流程；没有业务数据变更。CC-GIN-001 的实现、测试及保留行为证据足以提交 FR-GIN-001 v0.1 评审并申请关闭；CC 本身仍待 Human Review。

## 附录 A — 基线历史

| 时间 | 旧基线 | 新基线 | 失效 Run | 处理 |
|---|---|---|---|---|
| 首次记录 | — | `main@63c25840 + 当前工作树` | — | ATR-RUN-001 仅绑定本工作树状态 |

## 附录 B — 版本历史

| 版本 | 日期 | 变更 | 状态 |
|---|---|---|---|
| v0.1 | 2026-11-17 | 记录 CC-GIN-001 v1.0 首次组件验证及运行环境阻塞 | Superseded by v0.2 |
| v0.2 | 2026-11-17 | 追加 Odoo Shell ORM 状态；确认 WorldDepot / stock_barcode 依赖阻塞，Mock 不代表真实 Odoo 通过 | Superseded by v0.3 |
| v0.3 | 2026-11-17 | 记录获批的 manifest 依赖移除、真实安装失败点和待授权的扫码导入处理 | Superseded by v0.4 |
| v0.4 | 2026-11-17 | 追加扫码导入获批停用后的安装 / 升级、7 项 Odoo 标准测试及 ORM 证据；保留 bcrypt 与 WMS 行为验证历史阻塞 | Superseded by v0.5 |
| v0.5 | 2026-11-17 | 安装独立 bcrypt 依赖并追加真实 Odoo Secret / controller / Token 验证、回归结果和当前限制；保留旧 BLOCKED 运行记录，生成 FR 评审 | Current |

## 附录 C — 维护规则

后续每次正式测试追加新的 `ATR-RUN-NNN`。失败或阻塞历史保留；任何实质代码变化后，须重新执行受影响测试，不得继承本 Run 的 PASS。
