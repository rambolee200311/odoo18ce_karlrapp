# 实施历史记录：IHR-GIN-003

## 0. 文档治理

| 字段 | 值 |
|---|---|
| CC | [CC-GIN-003 v1.0 Frozen with Open Items](CC-GIN-003.md) |
| IHR 版本 | v0.2 |
| TDD 基线 | v0.3 Frozen with Open Items；CC 已记录需提出 TDD 变更 |
| 模块 | `ginlong_apis`、共享 `worlddepot` API logger 最小兼容 |
| 工作类型 | API 幂等、限流、订单动作与组件测试 |
| 实施负责人 | Codex |
| 开始 / 最后更新 | 2026-11-17 |
| 最新 addon 基线 | `GINLONG-WT-0ce7e607aad78a0791719bf08bf700a768bc47ae43e4e1d9bd262af65c06377b` |
| 当前实施状态 | In Progress；入站代码与 ORM 验收部分完成，人工回传及多 Worker 验收阻塞 |
| 模板同步 | BLOCKED：项目模板来源缺失；沿用已批准例外，不记为通过 |

## 1. CC 基线

本记录执行 [CC-GIN-003 v1.0](CC-GIN-003.md)。手动回传与四个入站接口分别核验，结果见 [ATR-GIN-003](ATR-GIN-003.md)。本 CC 不实施或专项测试 `audit_log`/`auditlog`。

| 范围 | 当前状态 |
|---|---|
| API01/03/05/07 幂等与限流 | 已实施；15 项最新 Odoo 自动化通过，单进程 HTTP 429/重放通过；真实多 Worker 并发与 API07 100/s 仍 BLOCKED |
| API01/03/05 UPDATE/DELETE；API07 owner+productCode | ORM 自动化部分通过；API07 不同 owner/相同产品编码仍受现有 WMS 全局编码规则和未确认操作契约约束 |
| API02/04/06/08/10 手动按钮 | 当前 Ginlong addon 未找到实现；外部 objectid/完整回传报文仍未确认，未实施，CC-TEST-001–007 保持 BLOCKED/NOT RUN |
| 外部联调与完整 WMS 人工流程 | 不在本轮模拟测试证据范围；保留后续联调依赖 |

## 2. 当前实施状态摘要

| 项 | 状态 |
|---|---|
| 实施进度 | 进行中；入站保护与 UPDATE/DELETE 已进入 Odoo 标准测试；回传接口未实施 |
| Preservation Impact | 需要回归确认；DELETE 不调用 `unlink()` / `action_cancel()`，API05 不访问库存模型 |
| 偏离 | 未新增外部基础设施；`api_logger` 仅作 HTTP Response 状态兼容 |
| Stop Condition | 未触发已确认接口的额外业务规则；workers=4 子进程启动异常，未宣称多 Worker 通过 |
| Open Issues | 回传按钮和 Ginlong objectid/报文；TDD 上游变更；模板来源同步；多 Worker 环境；提交后响应丢失测试 |
| 当前状态 | In Progress |

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

## 5. 偏离与停止记录

| 事件 | 处理 | 状态 |
|---|---|---|
| Odoo Engineering 来源副本缺失 | 同步脚本返回 BLOCKED；不使用内置副本充当权威来源，按已批准 CC 的具体方案继续 | BLOCKED 事实保留 |
| API 回传 objectid/报文未确认 | 不新增猜测的 HTTP 调用或按钮；仅阻塞回传实现 | BLOCKED |
| `odoo.conf` 当前 `workers=0` | 不把单进程自动化测试充作多 Worker 性能证据 | CC-TEST-016 待执行 |
| CC 提出的 TDD v0.4 更新 | 本轮未修改冻结 TDD；实现以用户 Human Review 批准的 CC v1.0 明确新增需求为边界，后续仍需按治理流程更新上游追踪 | Open |

## 6. 移交摘要

当前仍在实施。最新 15 项 Odoo 自动化和单进程 HTTP 429/重放已通过各自有限范围；它们不代表整份 CC 完成。多 Worker 100 次/秒、完整五个回传按钮、提交后响应丢失及外部协议联调不得由 ORM/Mock 结果替代。项目模板同步保持 BLOCKED。

## 附录：版本记录

| 版本 | 日期 | 说明 | 状态 |
|---|---|---|---|
| v0.1 | 2026-11-17 | 创建 CC-GIN-003 实施事实台账；代码实施进行中 | In Progress |
| v0.2 | 2026-11-17 | 追加 logger 并发异常修复、Odoo 升级/ORM、单进程 HTTP 429/幂等重放及多 Worker 启动阻塞证据；模板同步继续 BLOCKED | In Progress |
