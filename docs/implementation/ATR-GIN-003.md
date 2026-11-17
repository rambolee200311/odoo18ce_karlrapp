# 自动化测试记录：ATR-GIN-003

## 0. 文档治理

本记录执行 [CC-GIN-003 v1.0 Frozen with Open Items](CC-GIN-003.md)，不改变其技术方案、验收标准或 Open Items。五个人工回传接口与四个入站接口分区记录。项目模板同步保持 `BLOCKED`，沿用已批准的流程例外，不记为通过。

## 1. 执行元数据

| 字段 | 值 |
|---|---|
| Intent ID | `GINLONG-API-IDEMPOTENCY-RATELIMIT-001` |
| IHR | [IHR-GIN-003](IHR-GIN-003.md) |
| CC | CC-GIN-003 v1.0 Frozen with Open Items |
| Module | `ginlong_apis` |
| Environment | Odoo 18；既有 `venv`、`odoo.conf`、数据库 `odooce_karlrapp` |
| Test Framework | Odoo 标准 `TransactionCase` / test runner；另有真实本机 HTTP 单进程验证 |
| 当前 addon 指纹 | `GINLONG-WT-0ce7e607aad78a0791719bf08bf700a768bc47ae43e4e1d9bd262af65c06377b`（15 个 addon 文件） |
| 执行者 | Codex |

所有数据库数据核验、临时记录创建和清理均通过 Odoo Shell ORM；未直接访问 PostgreSQL或执行 SQL。未安装或使用 `stock_barcode`。没有访问 Ginlong 外部端点。

## 2. 测试契约基线

引用 [CC-GIN-003 §6](CC-GIN-003.md)：手动回传 CC-TEST-001–007；入站幂等、限流及 UPDATE/DELETE CC-TEST-008–023。`audit_log`/`auditlog` 不开发、不修改、不专项测试。

## 3. 当前验收状态

| 指标 | 值 |
|---|---|
| Required Tests | 23 |
| PASS | 8（组件/ORM 范围内） |
| PARTIAL | 3 |
| FAIL（当前最新基线） | 0 |
| BLOCKED | 10（回传 7 项及真实多 Worker 3 项） |
| NOT RUN | 2 |
| 最新有效自动化运行 | ATR-RUN-008；15 项 Odoo 测试，0 failed / 0 error |
| 最新有效代码基线 | 上列 addon 指纹 |
| CC-GIN-003 整体状态 | In Progress；不得关闭 |

历史 ATR-RUN-004 曾有 1 项失败，修复并保留记录；之后运行通过。Worker 启动阻塞、模板同步阻塞及未执行项均保留，不以组件测试或单进程 HTTP 结果替代。

## 4. 覆盖矩阵

| CC / TEST | 当前结果 | 实际证据及边界 |
|---|---|---|
| CC-TEST-001–007 | BLOCKED / NOT RUN | 五个回传按钮及出站调用未实现；Ginlong `objectid`、完整报文和响应规则未获确认，不用部分 Payload 或 Mock PASS 代替。 |
| CC-TEST-008 | PASS（组件/ORM） | 覆盖 API01/03/05 单号键、API07 `owner + productCode` 组合键，以及缺键不创建成功幂等项。 |
| CC-TEST-009 | PASS（组件/ORM） | 同 API/业务键/规范化指纹只调用一次业务函数并重放原结果；对象键顺序无关、数组顺序保留。 |
| CC-TEST-010 | BLOCKED | 无真实多 Worker 并发重复请求和首事务回滚接管证据；TransactionCase 不满足本项。 |
| CC-TEST-011 | PASS（组件/ORM） | 注入异常和 `success=false` 后业务写入及成功幂等记录回滚；同一异常请求可再次执行。真实 Worker 锁等待/超时恢复未覆盖。 |
| CC-TEST-012 | PASS（幂等组件范围） | 同一 API 业务键但不同内容进入操作函数；API07 不同 owner 形成不同幂等键。WMS 全局产品编码约束未改变；动作契约未确认场景仍保留 Open。 |
| CC-TEST-013 | PARTIAL | Odoo Settings 阈值默认值 10/10/10/100、配置读取及 429 响应组件测试通过；单进程 HTTP 只以临时阈值 1 验证窗口内 200/429。未按正式阈值实测每秒 10/100 次和跨秒复位。 |
| CC-TEST-014 | BLOCKED | 未能启动真实多 Worker，四 API 共享计数行并发原子性及隔离未验。 |
| CC-TEST-015 | PARTIAL | 路由沿用 `worlddepot` Token/API logger 装饰器；实际 HTTP 429 与既有日志状态已核验。多调用方身份隔离及伪造 IP 头场景未完成真实 HTTP 验证。 |
| CC-TEST-016 | BLOCKED | 未执行 API07 真实 HTTP 多 Worker、同一 UTC 秒 101 请求压测；吞吐、时延、冲突、重试、错误指标无数据。 |
| CC-TEST-017 | NOT RUN | 没有独立验证提交成功后业务数据、响应和幂等结果同时可见，或提交失败时均不可见。 |
| CC-TEST-018 | PASS（组件/ORM） | Odoo TransactionCase 注入业务异常和失败响应，确认请求内 ORM 写入及幂等项回滚，并验证失败请求可重试；不是多 Worker HTTP 证据。 |
| CC-TEST-019 | NOT RUN | 未模拟数据库提交成功后的 HTTP 响应丢失和重发，也未验证并发原事务提交/回滚的等待仲裁。 |
| CC-TEST-020 | PASS（ORM） | API01 UPDATE 写入既有订单；DELETE 将状态改为 `cancel`，订单和明细保留，重复 DELETE 成功；测试确认未生成实际 `stock.picking`。 |
| CC-TEST-021 | PASS（ORM） | API03 UPDATE 写入既有订单；DELETE 将状态改为 `cancel`，订单和明细保留，重复 DELETE 成功；未生成实际 `stock.picking`。API03 仍是 A-003 本地假设。 |
| CC-TEST-022 | PASS（ORM） | API05 更新既有任务；DELETE 将任务状态改为 `cancel` 并保留任务/明细；未访问库存模型，不触碰 `stock.quant`。 |
| CC-TEST-023 | PARTIAL | API07 原生 `product.product` 创建及同货主/编码更新通过；不同 owner、相同全局 `default_code` 受现有 WMS 编码约束，动作处理不作为已确认契约，不改 WMS 唯一性规则。 |

## 5. 运行历史（仅追加）

| Run | 执行结果 | 日志 / 说明 |
|---|---|---|
| ATR-RUN-001 | 初次命令在受限环境连接本地 PostgreSQL 端口时被系统拒绝，未完成测试。之后在批准的本机运行权限下重跑；无数据库或环境变更。 | `/tmp/atr-ginlong-003-run-001b.log` 保存失败；`run-001.log` 为空。 |
| ATR-RUN-002 | Odoo 标准测试 12 项，0 failed / 0 error。 | `/tmp/atr-ginlong-003-run-002.log`；日志时间 09:48:59。 |
| ATR-RUN-003 | Odoo 标准测试 13 项，0 failed / 0 error。另一次 workers=4 启动尝试失败，子 Worker 报 `DistributionNotFound: zope.interface`；CC-TEST-016 未运行。 | `/tmp/atr-ginlong-003-run-003.log`；运行时间 09:55:49。Worker 启动诊断详见 IHR-006。 |
| ATR-RUN-004 | 14 项中 1 项失败：发现共享 `api_logger` 捕获并回滚了 Odoo 可重试的并发异常，妨碍标准重试。失败保留，随后修复。 | `/tmp/atr-ginlong-003-run-004.log`；日志时间 10:04:45。 |
| ATR-RUN-005 | 修复后 14 项，0 failed / 0 error。 | `/tmp/atr-ginlong-003-run-005.log`；日志时间 10:06:34。 |
| ATR-RUN-006 | 15 项，0 failed / 0 error。 | `/tmp/atr-ginlong-003-run-006.log`；日志时间 10:11:09。 |
| ATR-RUN-007 | 在既有 Odoo 单进程 HTTP 服务上执行实际请求：同一 UTC 秒内两个 API07 请求得到一个 HTTP 200、一个 HTTP 429（含 `Retry-After: 1`）；既有 API 日志 ORM 记录 200/429。下一秒完全相同请求重放原响应和产品 ID。临时阈值为 1，故不满足 API07 100/s 验收。随后用 Odoo Shell ORM 清理临时用户、Token、产品、日志和计数记录并恢复阈值 100。 | HTTP 时间 10:08:43–10:08:44；数据库状态及清理经 `odoo shell -c odoo.conf` ORM 检查。单进程结果，不代表多 Worker。 |
| ATR-RUN-008 | 最新代码基线执行 Odoo 标准测试 15 项，0 failed / 0 error。 | `/tmp/atr-ginlong-003-run-007.log`；日志时间 10:13:37；addon 指纹见 §1。 |

ATR-RUN-008 命令（使用既有 venv/config/database）：

```text
venv/bin/python odoo-bin -c odoo.conf -d odooce_karlrapp --test-enable --test-tags /ginlong_apis --stop-after-init --http-port=0 --gevent-port=0 -u ginlong_apis --log-level=info --log-handler=odoo.tests:INFO --logfile=/tmp/atr-ginlong-003-run-007.log
```

日志末尾记录 `15 post-tests` 及 `0 failed, 0 error(s) of 15 tests`。未创建虚拟环境或数据库，未安装 `stock_barcode`。

## 6. 业务边界与回归结果

| 保护边界 | 结果 | 证据 / 限制 |
|---|---|---|
| API01/03 收单不等于仓库执行 | PASS（ORM 模拟） | 测试断言订单处于待处理状态，未创建/关联实际 picking；不代表完整 WMS 人工流程。 |
| API01/03 DELETE 保留原记录 | PASS（ORM） | 状态为 `cancel`，订单及子记录保留，重复 DELETE 可重复调用；源码不调用 `unlink()`。 |
| API05 不写库存账 | PASS（组件边界） | API05 服务和测试不访问 `stock.quant`；未进行库存过账流程。 |
| API07 复用 Odoo 产品 | PARTIAL | 在 `product.product` 创建及同组合更新通过；不改变现有全局编码唯一性。 |
| API Token、权限、日志、凭据 | PARTIAL | 路由装饰器和 429 日志组件已测；单进程 HTTP 的错误/成功日志已查。调用方隔离及完整安全权限矩阵仍待验。 |
| 其他 WMS / 完整 WMS 流程 | BLOCKED / NOT RUN | 本 CC 自动化不替代最终人工业务流程；按后续集成 CC 验收。 |

## 7. Open Issues 与阻塞

| 项目 | 状态 | 影响 |
|---|---|---|
| API02/04/06/08/10 按钮及完整回传契约 | BLOCKED | CC-TEST-001–007 未通过；所需 objectid、请求/响应契约待确认。 |
| 真实 Odoo 多 Worker | BLOCKED | workers=4 子进程不能导入 `zope.interface` distribution；未改变 Python 环境。CC-TEST-010/014/016 未通过。 |
| 正式阈值窗口与多调用方隔离 | PARTIAL / NOT RUN | 仅以单进程和临时阈值 1 验证真实 429/重放。 |
| 事务提交后响应丢失 | NOT RUN | CC-TEST-017/019 未完成。 |
| Ginlong 外部联调、API03 正式方向 | BLOCKED / 未执行 | 不访问外部地址；A-003 继续作为开发假设。 |
| 模板同步 | BLOCKED | 已批准流程例外继续保留，不标记 PASS。 |
| Odoo Engineering 指南来源同步 | BLOCKED | 项目 canonical 来源缺失；按已批准 CC 继续，不能声称同步通过。 |

## 8. 多 Worker 性能验收要求

CC-TEST-016 必须由真实 Odoo 多 Worker HTTP 路径在同一个 UTC 固定秒窗口发送 101 个不同且有效的 API07 产品请求，观察 100 个获准、1 个 HTTP 429，并记录 worker 数、并发数、吞吐/时延、事务冲突、重试及错误。当前未取得此证据。单进程请求、ORM 自动化、Mock、数据库计数器读数均不能替代。不得宣称 API07 100 次/秒限流验收通过。

## 9. 证据库存

- 最新 Odoo runner 日志：`/tmp/atr-ginlong-003-run-007.log`。
- 保留失败日志：`/tmp/atr-ginlong-003-run-004.log`。
- 已修复后回归日志：`/tmp/atr-ginlong-003-run-005.log`、`run-006.log`、`run-007.log`。
- 多 Worker 启动失败诊断：`/tmp/atr-ginlong-003-run-003.log` 及 IHR-006。
- 单进程 HTTP 与清理：通过现有 Odoo 服务和 Odoo Shell ORM 完成；结果详见 ATR-RUN-007。
- 最新 addon 指纹：§1。

## 10. 移交摘要

当前只完成 CC-GIN-003 的部分实施和组件/ORM 验收。15 项最新自动化通过，但这不代表全部 CC 验收通过。五个人工回传、真实多 Worker 并发、API07 100/s 性能、成功提交与响应丢失恢复仍未完成；模板同步仍 `BLOCKED`。CC 保持 In Progress，不生成关闭 FR。

## 附录：版本记录

| 版本 | 日期 | 说明 | 状态 |
|---|---|---|---|
| v0.1 | 2026-11-17 | 建立 CC-GIN-003 实施和测试证据台账。 | In Progress |
| v0.2 | 2026-11-17 | 追加 ATR-RUN-001–008、逐项验收矩阵、真实单进程 HTTP 429 结果、多 Worker 阻塞及遗留 Open Items；保留失败运行。 | In Progress |
