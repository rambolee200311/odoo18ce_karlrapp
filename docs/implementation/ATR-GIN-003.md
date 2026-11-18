# 自动化测试记录：ATR-GIN-003

## 0. 文档治理

本记录保留 [CC-GIN-003 v1.1 Frozen with Open Items](CC-GIN-003-v1.1.md) 及 v1.2/v1.3 历史结果，并追加 [CC-GIN-003 v1.4](CC-GIN-003-v1.4.md) 的实施证据及 [v1.5 关闭记录](CC-GIN-003-v1.5.md)。五个人工回传接口与四个入站接口分区记录。项目模板同步保持 `BLOCKED`，沿用已批准的流程例外，不记为通过。

## 1. 执行元数据

| 字段 | 值 |
|---|---|
| Intent ID | `GINLONG-API-IDEMPOTENCY-RATELIMIT-001` |
| ATR 版本 | v1.3 |
| IHR | [IHR-GIN-003](IHR-GIN-003.md) |
| CC | [CC-GIN-003 v1.4](CC-GIN-003-v1.4.md) 实施增补；[v1.5 Closed](CC-GIN-003-v1.5.md)；v1.1 冻结基线及后续历史版本保留 |
| Module | `ginlong_apis`、`worlddepot` 受影响代码 |
| Environment | Odoo 18；既有 `venv`、`odoo.conf`、数据库 `odooce_karlrapp` |
| Test Framework | Odoo 标准 `TransactionCase` / test runner；真实四 Worker 本机 HTTP/ORM 验证；本机响应丢失代理 |
| 入站历史 addon 指纹 | `GINLONG-WT-0ce7e607aad78a0791719bf08bf700a768bc47ae43e4e1d9bd262af65c06377b`（ATR-RUN-017 使用；非本轮回传代码指纹） |
| 当前源文件核对 | 持久化回传 Form、API05、盘点模型、owner resolver 和 API01/03 货主处理见工作树；Ginlong addon 版本 `18.0.2.0.9`；ATR-RUN-049–055 为关闭后的项目负责人决策补充证据 |
| 执行者 | Codex |

所有数据库数据核验、临时记录创建和清理均通过 Odoo Shell ORM；未直接访问 PostgreSQL或执行 SQL。未安装或使用 `stock_barcode`。没有访问 Ginlong 外部端点。

## 2. 测试契约基线

现行测试标准引用 [CC-GIN-003 v1.4 §6](CC-GIN-003-v1.4.md)；CC-GIN-003 v1.1 为冻结验收基线。手动回传 CC-TEST-001–007；入站幂等、限流及 UPDATE/DELETE CC-TEST-008–023；`worlddepot` 影响回归 CC-TEST-024。`audit_log`/`auditlog` 不开发、不修改、不专项测试。

## 3. 当前验收状态

| 指标 | 值 |
|---|---|
| Required Tests | 24 |
| PASS | 24（CC-TEST-001–024；CC-TEST-010/017/019 沿用已批准的历史证据） |
| PARTIAL | 0 |
| FAIL（当前最新有效基线） | 0；失败/无效历史运行保留在下方 |
| BLOCKED | 本地冻结验收无剩余 BLOCKED；Ginlong 撤销/部分执行等外部语义保留为隔离 Open Items，不阻塞已确认场景 |
| NOT RUN | Ginlong 真实环境、完整浏览器人工回传与完整 WMS 人工 E2E；后两项留最终集成 CC |
| 最新有效自动化运行 | ATR-RUN-048 Ginlong 最终全量 31 项、ATR-RUN-044 worlddepot 全量 8 项，均 0 failed / 0 error；ATR-RUN-046 三项最终规则定向测试亦通过；首次失败 ATR-RUN-041 保留 |
| 最新 ORM 基线 | 2026-11-18 Odoo Shell ORM 只读确认收/发货明细模型、API06 汇总字段、owner/weight 与 move-line 来源字段注册，callback Wizard 未注册；Ginlong module installed |
| CC-GIN-003 整体状态 | Closed；FR-GIN-003 v1.0 Closure SATISFIED、Human Review APPROVED |

历史 ATR-RUN-004 及 CC-TEST-010/017/019 的失败/修复和多 Worker 证据均保留。原先 Wizard 方案与运行记录是历史实现；当前 v1.2 使用持久化 Form/Notebook。API04 仅发送已保存选中的 picking；API10 仅发送已保存选中的实盘结果。API06 的既有备货事件仍为出库 Order `status='picking'`、`picking_PICK` 和 `picking_PICK_date`，没有新增状态门禁。回传本地 Mock 自动化与外部协议 Open Items 分开统计。

本轮回传验收：API02/08 的持久化明细状态及 API06 实际备货数据已按用户最终规则组装并通过 Mock；同状态可发送，混合 Y/N 阻止发送并追加日志。API06 托盘取选中实际 `stock.move.line.package_id` 去重；重量取 V3.2 API07 `weight` 对应的 `product.ginlong_weight` × 实际数量，毛重默认净重且可手工覆盖；DECIMAL(18,6) 值按用户最终确认和 V3.2 样例序列化为最多六位小数的 JSON string。API07 跨 owner 同码创建/更新、项目 owner 消歧、API01/03 产品定位及受影响 WMS 自动化通过。未访问真实 Ginlong；完整浏览器操作及完整 WMS 人工 E2E 留最终集成 CC。

## 4. 覆盖矩阵

| CC / TEST | 当前结果 | 实际证据及边界 |
|---|---|---|
| CC-TEST-001–006 | PASS（已确认场景的 Odoo/Mock 范围） | ATR-RUN-042/043 覆盖 Form 持久化、重新打开、明细状态/实绩 payload、API06 覆盖、失败修改重试与日志追加；无真实 Ginlong。 |
| CC-TEST-007 | PASS | API02/08 混合 Y/N 明细按用户最终确认阻止发送并追加错误日志；API06 DECIMAL 字段按确认以 JSON string 发送。撤销/部分执行等外部契约仍隔离记录。 |
| CC-TEST-008 | PASS（组件/ORM） | 覆盖 API01/03/05 单号键、API07 `owner + productCode` 组合键，以及缺键不创建成功幂等项。 |
| CC-TEST-009 | PASS（组件/ORM） | 同 API/业务键/规范化指纹只调用一次业务函数并重放原结果；对象键顺序无关、数组顺序保留。 |
| CC-TEST-010 | PASS（HTTP 并发提交 + ORM 事务回滚接管） | ATR-RUN-014 的真实四 Worker HTTP 并发相同 API07 请求均 200 且返回同一产品 ID；ATR-RUN-026 的两个独立 ORM cursor 自动化覆盖竞争请求在首事务提交时重放、首事务回滚时等待请求接手，最终各仅一条业务副作用和一条幂等记录。回滚接管子场景是数据库/ORM 并发自动化，不冒称为 HTTP Worker 回滚故障注入。 |
| CC-TEST-011 | PASS（组件/ORM） | 注入异常和 `success=false` 后业务写入及成功幂等记录回滚；同一异常请求可再次执行。真实 Worker 锁等待/超时恢复未覆盖。 |
| CC-TEST-012 | PASS（幂等组件范围） | 同一 API 业务键但不同内容进入操作函数；API07 不同 owner 形成不同幂等键。WMS 全局产品编码约束未改变；动作契约未确认场景仍保留 Open。 |
| CC-TEST-013 | PASS | 四 Worker HTTP 同秒 API01/03/05 各 10×200、1×429；API07 同秒 100×200、1×429，全部 429 `Retry-After: 1`。Settings API01 改为 2 后下个 UTC 秒为 2×200/1×429；恢复默认后四 API 后续窗口均返回 200。旧 worker 缓存阈值的无效运行已保留。 |
| CC-TEST-014 | PASS | 四 Worker 下 API01/03/05/07 竞争独立计数行；早期临时阈值 2 的隔离运行，以及默认 10/10/10、API07 100/s 均核对到对应调用方/API窗口。调用方隔离见 CC-TEST-015。 |
| CC-TEST-015 | PASS | 两个认证 API user 同一 UTC 秒分别计数 2 与 1；同一 user 更换伪造 XFF 仍共用同一 api_user 计数行；日志来源均为 `127.0.0.1`，未记录伪造地址或 Token。 |
| CC-TEST-016 | PASS | 四 Worker、16 个 HTTP 客户端、101 个请求均始于 `2026-11-17T10:53:11Z`：100×200、1×429。全程约 623 ms；min/p50/p95/max 67.323/87.390/141.700/168.068 ms。ORM：100 产品、100 幂等行、计数 100、101 日志。77 个捕获的限流竞争重试事件（3 UniqueViolation、74 SerializationFailure；第 1/2/3 次分别 51/22/4），无 retry exhaustion、5xx 或客户端错误。 |
| CC-TEST-017 | PASS（Odoo ORM 请求事务边界） | ATR-RUN-026 在 `Cursor.commit()` 前注入故障；独立新 ORM 事务确认业务记录和成功幂等记录都不可见。成功提交后，新 ORM 事务可读取业务记录及已保存响应；Odoo HTTP 框架源码确认请求成功响应在事务 commit 后返回。故障注入在真实 Odoo Cursor/ORM 事务上运行，未修改生产路由加入故障钩子。 |
| CC-TEST-018 | PASS（组件/ORM） | Odoo TransactionCase 注入业务异常和失败响应，确认请求内 ORM 写入及幂等项回滚，并验证失败请求可重试；不是多 Worker HTTP 证据。 |
| CC-TEST-019 | PASS（HTTP 响应丢失 + ORM 并发仲裁） | ATR-RUN-016 的本机代理在上游 HTTP 200 后丢弃客户端响应；相同 HTTP 请求重放得到已保存结果且无第二次副作用。ATR-RUN-026 再验证两个 ORM 事务在原事务提交时重放、回滚时由等待事务接手。响应丢失使用本地 Odoo HTTP 和代理，不访问 Ginlong。 |
| CC-TEST-020 | PASS（ORM） | API01 UPDATE 写入既有订单；DELETE 将状态改为 `cancel`，订单和明细保留，重复 DELETE 成功；测试确认未生成实际 `stock.picking`。 |
| CC-TEST-021 | PASS（ORM） | API03 UPDATE 写入既有订单；DELETE 将状态改为 `cancel`，订单和明细保留，重复 DELETE 成功；未生成实际 `stock.picking`。API03 的 Ginlong→Odoo 方向已由后续接口矩阵确认；早期 A-003 假设仅保留为历史。 |
| CC-TEST-022 | PASS（ORM） | API05 更新既有任务；DELETE 将任务状态改为 `cancel` 并保留任务/明细；未访问库存模型，不触碰 `stock.quant`。 |
| CC-TEST-023 | PASS（Odoo 自动化） | ATR-RUN-043/047/048 覆盖同 `default_code` 跨 owner 创建、同 owner 查询/更新及 API01/03 的 owner+productCode 产品定位；受影响 Hoymiles/OFoundation Controller 共用 resolver，按项目 owner 消歧，重复编码无 owner 依据时明确报歧义。 |
| CC-TEST-024 | PASS（本 CC 自动化范围） | ATR-RUN-043/044/048 覆盖受影响 Ginlong/worlddepot 模块、owner resolver、API01/03 订单与实际 Picking 关系保留、盘点双模型、API User/Token/日志及回传明细关联。完整人工 WMS E2E 不属于本 CC，留最终集成 CC。 |

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
| ATR-RUN-009 | 初次四 Worker API07 突发客户端运行无效：101 个并发客户端中仅 36 个 HTTP 200，65 个连接重置；无 429，服务端仅记录 36 个请求。另保留两次 API01/03/05 旧 worker 使用临时阈值 2 的无效结果（2×200、9×429）。 | API07 客户端失败记录与 10:57:46、10:58:34 的旧阈值运行；仅保留，不作为验收证据。 |
| ATR-RUN-010 | 四 Worker、16 个独立 HTTP 客户端同一 UTC 秒提交 101 个 API07 请求：100×200、1×429，`Retry-After: 1`；请求约 623 ms 完成；ORM 核验 100 产品、100 幂等行、窗口计数 100、101 日志。77 次并发冲突恢复事件（3 UniqueViolation、74 SerializationFailure），无重试耗尽、5xx 或客户端错误。 | `/tmp/ccgin003_api07_101_results.json`；窗口 `2026-11-17T10:53:11Z`。 |
| ATR-RUN-011 | 保留 API01/03/05 两次无效默认限流运行：旧 Worker 进程持有阈值 2，分别观察到每路 2×200、9×429；重启 Worker 并恢复配置缓存后另行有效验证。 | 10:57:46、10:58:34 UTC；不得覆盖 ATR-RUN-012。 |
| ATR-RUN-012 | 四 Worker 同一窗口验证 API01/03/05 默认额度，各 API 10×200、1×429，均有 `Retry-After: 1`；无客户端错误。 | `/tmp/ccgin003_default_limits_10_10_10_r3.json`；窗口 `2026-11-17T10:59:57Z`。 |
| ATR-RUN-013 | 两个认证 API user 的 API07 计数按用户隔离；同一用户使用不同伪造 XFF 仍共享其计数身份。日志仅出现连接来源 `127.0.0.1`，未记录伪造头或 Token。 | `/tmp/ccgin003_caller_identity.json`；窗口 `2026-11-17T11:01:09Z`。 |
| ATR-RUN-014 | 四 Worker 同请求并发及跨窗口恢复：并发 API07 请求均 HTTP 200 并返回同一产品 ID，ORM 仅一产品/一幂等结果；API01/03/05/07 完全相同请求在下一 UTC 窗口成功重放。 | `/tmp/ccgin003_idem_concurrent_commit.json`、`/tmp/ccgin003_window_recovery.json`。 |
| ATR-RUN-015 | 通过 Odoo Settings/ORM 将 API01 阈值改为 2，下一个 UTC 秒窗口观察到 2×200、1×429；随后按 ORM 备份恢复原配置状态。 | `/tmp/ccgin003_settings_change.json`；配置恢复后四 API 下一窗口请求正常。 |
| ATR-RUN-016 | 本机代理接收 Odoo 完整 HTTP 200 后丢弃客户端响应；客户端确认连接中断。独立 Odoo Shell ORM 在重放前确认业务记录及幂等结果已提交；完全相同请求重放后返回相同结果，业务记录仍仅一份。另以 ORM 两 cursor 验证首事务回滚后等待事务可接手。 | `/tmp/ccgin003_response_lost.json`；后半为 ORM cursor 验证，不冒充真实 HTTP Worker 回滚接管。 |
| ATR-RUN-017 | 最新 addon 基线执行 Odoo 标准测试 15 项，0 failed / 0 error。 | `/tmp/atr-ginlong-003-run-009.log`；2026-11-17 11:07:59 UTC。 |
| ATR-RUN-018 | `worlddepot`/`ginlong_apis` 模块升级并运行 7 项定向测试，0 failed / 0 error；覆盖盘点订单/实盘结果 ORM、API05 存储/更新/取消、API10 实盘数据 Wizard、API02 状态来源、API06 不加备货门禁、协议未确认时不发 HTTP、Mock HTTP helper 一次调用及 15 秒超时。 | `debug_logs/odoo_181.log`，2026-11-17 13:15:29 UTC，PID 41123；7 tests / 344 queries。 |
| ATR-RUN-019 | API04 与 API06 使用实际创建的 `stock.picking`、`stock.move`、`stock.move.line`、lot 及 package 数据验证 Wizard 展示产品、SN、数量、托盘；API06 不检查 picking 状态作为额外门禁。2 项通过。 | `debug_logs/odoo_181.log`，2026-11-17 15:36:55 UTC，PID 41686；2 tests / 294 queries。 |
| ATR-RUN-020 | API08 Order 状态来源、API02 未决协议阻塞日志、Endpoint URL userinfo/凭据查询参数不进入 API 日志的测试通过；3 项通过。 | `debug_logs/odoo_181.log`，2026-11-17 16:27:08 UTC，PID 41931；3 tests / 216 queries。 |
| ATR-RUN-021 | 通过既有 `odoo shell -c odoo.conf --no-http` ORM 核对安装状态/版本、两盘点模型字段、五个按钮方法、盘点/Wizard 视图、旧 Ginlong 盘点模型已从 registry 移除。计数模型为零仅表示测试事务回滚后没有遗留数据；未访问 `stock.quant`。 | 2026-11-18 CST，ATR-RUN-020 后的只读 shell 核查；控制台结果摘要记录于 IHR-013。 |
| ATR-RUN-022 | 凭据 URL 日志遮蔽与未配置 Endpoint 时不发送/记录清楚提示，2 项 Odoo 自动化通过。 | `debug_logs/odoo_181.log`，2026-11-18 01:02:51 UTC，PID 44540；2 tests / 177 queries。 |
| ATR-RUN-023 | 回归 URL 凭据遮蔽、未配置 Endpoint 阻断及 Wizard 复用 `stock.group_stock_user` ACL，3 项通过。 | `debug_logs/odoo_181.log`，2026-11-18 01:03:49 UTC，PID 44638；3 tests / 183 queries。 |
| ATR-RUN-024 | 回归 Endpoint URL userinfo 和敏感查询值同时出现在模拟响应/错误时，现有 API 日志会遮蔽请求路径、响应、错误与摘要中的凭据；1 项通过。 | `debug_logs/odoo_181.log`，2026-11-18 01:06:24 UTC，PID 44731；1 test / 138 queries。 |
| ATR-RUN-025 | 使用既有 venv/config/database 执行 `ginlong_apis` 全套 Odoo 标准自动化；29 post-tests 中 2 项失败：并发回滚测试断言过严，缺少业务键测试错误假设全表为空。失败记录保留，不作为通过证据。 | `/tmp/ccgin003_transaction_completion.log`；2026-11-18 01:49 UTC。 |
| ATR-RUN-026 | 修正测试断言后重跑同一 Odoo 标准套件：29 post-tests，0 failed / 0 error；覆盖 CC-TEST-010/017/019 事务自动化、API06 既有备货完成状态/时间展示及 Ginlong 模块回归。临时探针由测试 finally 清理，随后 Odoo Shell ORM 确认无残留。 | `/tmp/ccgin003_transaction_completion_r2.log`；2026-11-18 01:52 UTC；模块升级 `ginlong_apis` 到 `18.0.2.0.1`。 |
| ATR-RUN-027 | 持久化回传视图首次模块升级失败：Odoo 拒绝无 `for` 属性的 `<label>`。失败保留；修正为标准 Form 标签结构后再运行。 | `/private/tmp/ginlong_callbacks_test.log`；2026-11-18 03:17 UTC；未有测试通过。 |
| ATR-RUN-028 | 三次早期测试筛选命令均为 0 post-tests，未验证功能，不计 PASS；随后修正精确测试选择器。 | `/private/tmp/ginlong_callbacks_test_r2.log`、`r3.log`、`r4.log`；2026-11-18 03:19–03:21 UTC。 |
| ATR-RUN-029 | 六项回传测试中 1 项断言失败、1 项异常：响应 JSON 字符串空白断言过严，且测试向 Odoo Selection 写入小写值。保留失败，修正断言和测试数据。 | `/private/tmp/ginlong_callbacks_test_r5.log`；2026-11-18 03:22 UTC。 |
| ATR-RUN-030 | 修正后六项定向 Odoo post-tests，0 failed / 0 error；覆盖 Form/无 Wizard、API04、API10、API02/06/08 Open Item 隔离及凭据保护。 | `/private/tmp/ginlong_callbacks_test_r6.log`；2026-11-18 03:22 UTC。 |
| ATR-RUN-031 | 七项定向 Odoo post-tests，0 failed / 0 error；增加 API06/API08 各自阻塞范围验证。 | `/private/tmp/ginlong_callbacks_test_r7.log`；2026-11-18 03:24 UTC。 |
| ATR-RUN-032 | 最新七项定向 Odoo post-tests，0 failed / 0 error；在 API04 多 picking 选择持久化后重跑，确认只发送已保存选中的实际作业单数据。 | `/private/tmp/ginlong_callbacks_test_r8.log`；2026-11-18 03:28 UTC；9 项运行统计中含 7 项 post-tests。 |
| ATR-RUN-033 | 通过既有 `odoo.conf` 和数据库 `odooce_karlrapp` 执行只读 Odoo Shell ORM 核查：Ginlong 模块为 installed `18.0.2.0.6`；`stock.picking`、`stock.move.line`、两个 `world.depot.stocktake.*` 模型均包含已批准的最小持久化字段；回传 Wizard 不在 ORM registry；包含「Ginlong 回传数据」的四个 Form 视图已注册。 | 2026-11-18；ORM 控制台结果；未写数据库、未执行 SQL。 |
| ATR-RUN-034 | 首次 `odoo-bin` 测试运行器连接既有数据库时，被受限执行环境拦截，测试未启动。保留为环境阻塞记录，不计测试结果。 | 命令输出：连接 `127.0.0.1:5555` 返回 `Operation not permitted`；未使用 SQL/数据库驱动。 |
| ATR-RUN-035 | 组合测试命令在既有配置 `log_level=error` 下退出码为 0，但没有可核验的测试数量/结果摘要；不作为 PASS 证据。 | `debug_logs/odoo_181.log`；随后改用显式测试日志和定向命令。 |
| ATR-RUN-036 | 既有数据库上升级/测试 `worlddepot`，8 个 post-tests、0 failed / 0 error；覆盖 API Token/认证与凭据日志，以及客户盘点指令和实盘结果独立关联。 | `/private/tmp/ccgin003_run034_worlddepot.log`；2026-11-18 03:56 UTC。 |
| ATR-RUN-037 | Ginlong 定向自动化 8 项、0 failed / 0 error；覆盖 API07 当前创建/同 owner 更新及冲突行为、API01/03 更新、API05 订单、持久化回传 Form、API04 保存后读取/失败重发/日志追加、API10 实盘结果和 API02/06/08 Open Item 隔离。 | `/private/tmp/ccgin003_run034_ginlong.log`；2026-11-18 03:56 UTC。 |
| ATR-RUN-038 | 扩展 API01/03 更新回归：订单已有实际 Picking 和 move line 时，API 更新后关联关系、作业行和数量均保留；1 个 post-test、0 failed / 0 error。 | `/private/tmp/ccgin003_run038_order_picking.log`；2026-11-18 03:58 UTC。 |
| ATR-RUN-039 | Odoo Shell ORM 事务探针创建两个不同产品、相同 `default_code`，ORM 接受并读到 2 条；显式回滚后新 Shell 查询为 0 条。未留下产品数据。 | Odoo Shell 输出；仅 ORM；未访问 PostgreSQL/SQL。 |
| ATR-RUN-040 | 更新回传 Form 以只读展示已存在业务来源：API02/08 的 Order `state/status`；API06 的 Order `state/status`、`picking_PICK` 与 `picking_PICK_date`。3 个 Odoo post-tests、0 failed / 0 error；同时验证 API02/06/08 未决字段仍分别阻止发送。未建立 `receiptConfirmed`、`shipmentConfirmed` 或托盘/重量的 wire 映射。 | `/private/tmp/ccgin003_run040_callback_sources.log`；2026-11-18 06:13 UTC。 |
| ATR-RUN-041 | 首次执行 7 个业务规则定向 post-tests，1 failure、4 errors、2 pass。错误发现明细子表 package 关系缺 ORM comodel 声明，产品编码测试未同步更新 SN 行字段；修复前结果保留，不计 PASS。 | `/private/tmp/ccgin003_business_rules_r1.log`；2026-11-18 06:52 UTC。 |
| ATR-RUN-042 | 修复后同范围 7 个定向 post-tests，0 failed / 0 error。覆盖 API07 跨 owner 同码、API02/08 持久化明细、API06 package 去重/重量/覆盖及 Mock Payload。 | `/private/tmp/ccgin003_business_rules_r2.log`；2026-11-18 06:53 UTC。 |
| ATR-RUN-043 | `ginlong_apis` 全量标准 Odoo post-tests：30 项，0 failed / 0 error。包含 API07 复合键与 WMS owner resolver、API02/08 明细及状态 Payload、API06 实际汇总与发送、入站幂等/限流、失败重试和日志追加。日志中并发幂等用例触发预期唯一键冲突并由实现处理；最终测试结果为通过。 | `/private/tmp/ccgin003_ginlong_full_r1.log`；2026-11-18 06:58 UTC。 |
| ATR-RUN-044 | `worlddepot` 全量标准 Odoo post-tests：8 项，0 failed / 0 error。覆盖现有 API Token/认证凭据日志、非认证业务日志及客户盘点指令与实盘结果独立关联。 | `/private/tmp/ccgin003_worlddepot_regression_r1.log`；2026-11-18 06:58 UTC。 |
| ATR-RUN-045 | Odoo Shell 对既有 `odoo.conf` / `odooce_karlrapp` 执行 ORM registry 只读核对：收/发货明细模型与关联字段、产品 owner/weight、API06 汇总字段及 move line 字段均存在；Ginlong callback Wizard 未注册；模块为 installed。未创建或修改业务记录，显式 rollback 退出。 | `/private/tmp/ccgin003_orm_registry_r1.log`；2026-11-18 07:05 UTC。 |
| ATR-RUN-046 | 按用户最终确认追加 3 个定向 post-tests：API02/08 混合 Y/N 阻止 HTTP 并记录独立失败日志；API06 DECIMAL 字段序列化为 JSON string；重量来源及手工覆盖保持正确。3 项、0 failed / 0 error。 | `/private/tmp/ccgin003_final_rules_r1.log`；2026-11-18 07:11 UTC。 |
| ATR-RUN-047 | 最终代码状态下重跑 `ginlong_apis` 全量 Odoo post-tests：31 项、0 failed / 0 error。日志包含幂等并发测试预期唯一键冲突，由实现正确处理；runner 汇总未报告失败或错误。 | `/private/tmp/ccgin003_ginlong_final_r1.log`；2026-11-18 07:13 UTC。 |
| ATR-RUN-048 | 在 API06 DECIMAL 格式化断言补齐后，再次运行 `ginlong_apis` 全量 Odoo post-tests：31 项、0 failed / 0 error。包含六位小数舍入及尾零清理检查；并发幂等用例中的唯一键冲突为预期竞争结果，runner 汇总无测试失败/错误。 | `/private/tmp/ccgin003_ginlong_final_r2.log`；2026-11-18 07:18 UTC。 |
| ATR-RUN-049 | 项目负责人批准 API01/03 货主规则后的首次定向运行：6 个 post-tests，1 failed / 0 error。唯一失败为跨 owner 产品消歧测试在刻意清空货主编码后未恢复测试夹具；其他 API01/03 新规则测试通过。失败保留，不作为通过证据。 | `/private/tmp/ccgin_api01_api03_targeted.log`；2026-11-18 10:41:40 Odoo log time。 |
| ATR-RUN-050 | 恢复测试夹具后重跑定向套件：6 个 post-tests，0 failed / 0 error；覆盖 API01 已有货主关联、缺失货主自动建档及不同订单复用、API03 已有货主与产品组合校验、API07 跨 owner 同码和既有订单更新。 | `/private/tmp/ccgin_api01_api03_targeted_r2.log`；2026-11-18 10:42:28 Odoo log time。 |
| ATR-RUN-051 | 加入 API03 路由失败日志用例后的定向回归：7 个 post-tests，0 failed / 0 error；确认缺失 owner+productCode 时不创建订单/产品，返回 HTTP 400 JSON 业务错误，现有 API logger 记录 `status=error`、`success=false`。 | `/private/tmp/ccgin_api01_api03_targeted_r3.log`；2026-11-18 10:45:15 Odoo log time。 |
| ATR-RUN-052 | `ginlong_apis` 全量 Odoo 自动化回归：40 个 post-tests，0 failed / 0 error。覆盖 API01/API03 货主新规则及既有 API07、API09、回传、幂等/限流测试。 | `/private/tmp/ccgin_api01_api03_full_r2.log`；2026-11-18 10:45:45 Odoo log time。 |
| ATR-RUN-053 | 通过既有 `odoo shell -c odoo.conf --no-http` 做只读 ORM registry 核验：模块 `installed 18.0.2.0.9`；入库/出库订单上的 `ginlong_owner_id` 均为 `res.partner` Many2one；`res.partner.ginlong_owner_code` 唯一约束已注册；当前开发库 0 条 Ginlong owner 编码记录、无重复；未留下测试 owner。 | `/private/tmp/ccgin_api01_api03_orm_final_r2.log`；2026-11-18。 |
| ATR-RUN-054 | API03 表头更新货主一致性定向回归：4 个 post-tests，0 failed / 0 error；不带 `details` 把出库订单货主改为没有对应产品的 owner 时拒绝更新，原 owner 及产品行不变；合法同 owner 更新和 API01 复用规则继续通过。 | `/private/tmp/ccgin_api01_api03_targeted_r4.log`；2026-11-18 11:06:45 Odoo log time。 |
| ATR-RUN-055 | 加入表头更新现有产品行核验后的最终 Ginlong 全量 Odoo 自动化回归：40 个 post-tests，0 failed / 0 error。 | `/private/tmp/ccgin_api01_api03_full_r3.log`；2026-11-18 11:07:15 Odoo log time。 |

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
| API07 复用 Odoo 产品 | PASS（自动化） | 不同 owner 同码创建、按复合键更新及现有 WMS 按项目 owner 消歧通过；不改变 Odoo 原生编码唯一性规则。 |
| API Token、权限、日志、凭据 | PASS（本 CC 自动化范围） | 复用现有 Token/认证/日志测试通过；完整浏览器角色矩阵留最终集成 CC。 |
| 完整 WMS 人工 E2E | NOT RUN（本 CC 不要求） | 按用户指示留最终集成 CC；不作为当前 CC-TEST-010/017/019 的前置条件。 |

## 7. Open Issues 与回传阻塞

### 7.1 回传接口逐字段阻塞矩阵

本节保留早期依据 Ginlong V3.2 工作簿第 21–32、67–80、96–104 行和旧代码核查形成的字段分析历史。协议/本地来源/映射类别说明适用于当时分析；当前实施、最终用户决策和验收结果以 §7.4 为准。

#### v1.2 历史实施状态（已由 §7.4 后续结果更新）

| 接口 | 当前实现及验收 | 当前仍阻塞的范围 |
|---|---|---|
| API02 | `UPDATE`、POST、JSON 已固定；现有 inbound Order 状态字段及时间字段已核查；缺失映射时写现有 API 日志且不发 HTTP | `state` 是订单确认/取消，`status` 的 `inbound` 来自实际入库完成；V3.2 未定义哪个状态对应 `receiptConfirmed` 的 Y/N，也有确认/撤销与 DELETE 的冲突。阻塞 API02 完整 Payload |
| API04 | `CREATE`、POST、JSON；从已保存选中的 `stock.picking` / `stock.move.line` 生成 Payload；逐 SN 操作人/时间字段持久化；Mock 成功、失败编辑重试和独立追加日志通过 | 多 picking/部分范围及逐 SN operationTime 格式/时区等外部语义仍待确认；不影响已验证的本地正常场景 |
| API06 | `CREATE`、POST、JSON；识别既有备货完成事件并读取已选实际 Picking/move line，不增加状态门禁；数据源存在 | `palletQty` 的实际托盘计数口径、`totalWeight` 净/毛重与聚合范围不清；DECIMAL 字段与 JSON 字符串样例冲突。阻塞 API06 完整 Payload |
| API08 | `CREATE`、POST、JSON；已核查现有 outbound Order 状态与发运日期 | V3.2 正常样例为 shipmentConfirmed=N，触发描述为确认且撤销用删除；没有 Order 状态到该字段的可确认映射。阻塞 API08 完整 Payload |
| API10 | `Add` / `Del` 大小写不敏感；从已保存选中的客户盘点单实盘结果生成 JSON；本地 Mock 回传通过 | V3.2 对撤销与部分采集的精确范围语义仍待确认；不读 `stock.quant`，不以计划数据代替实盘 |

#### 2026-11-18 本地字段与产品编码复核

| 项目 | 源码/ORM 证据 | 当前结论与阻塞 |
|---|---|---|
| API02 `receiptConfirmed` | `world.depot.inbound.order.state` 是 `new/confirm/cancel`，其中 `confirm` 由 `action_confirm()` 设置为业务订单确认；`status` 是 `planning/arrive/inbound`，现有 `cron_update_inbound_date()` 仅在关联 Picking `date_done` 后将其设为 `inbound`。另有 `confirm_time_server`（订单确认时间）和 `i_datetime`（实际入库时间），没有独立收货确认字段/事件时间。 | V3.2 定义必填 VARCHAR，正常样例为 `Y`，但没有值域/状态映射，且文字描述撤销使用删除；用户已确认正常 Action=`UPDATE`。本地代码未实现映射；不能把订单确认、到货或入库完成状态擅自等同 `receiptConfirmed`。仅阻塞 API02 完整 Payload。 |
| API06 `palletQty` | 已选实际 `stock.picking` 与 `stock.move.line` 可读实际数量及 `result_package_id`/`package_id`；没有直接表示 Ginlong“实际托盘总数”的现成 API 字段。订单计划托盘数不是本次实际作业实绩。 | V3.2 要求 DECIMAL(18,6)，样例却将 `"3"` 作为 JSON 字符串；未定义是按本次选中行的不同包裹、托盘主数据或其他口径计数。数据来源候选存在，具体聚合映射未实现，不能把包裹数直接冒充托盘数。阻塞 API06 完整 Payload。 |
| API06 `totalWeight` | 已选 move line 有实际 `quantity` 和产品重量；`stock.picking.shipping_weight` 可读；WorldDepot packing info 有 gross/net 字段但不是本次选中 Picking 的直接实绩字段。 | V3.2 要求 DECIMAL(18,6)，样例用 JSON 字符串 `"4"`；未定义净重/毛重、是否含包装及按所选 Picking 还是订单范围聚合。候选来源存在，映射未实现；不以订单计划重量代替。阻塞 API06 完整 Payload。 |
| API08 `shipmentConfirmed` | `world.depot.outbound.order.state` 是 `new/confirm/cancel` 的订单生命周期；`status` 是 `planning/picking/outbound`。现有 `cron_update_outbound_date()` 在关联出库 Picking 有 `date_done` 后设置订单 `status='outbound'` 并写 `picking_Out_date`。 | V3.2 字段表称确认/取消、触发说明称撤销用删除，唯一样例却是 `shipmentConfirmed: "N"`；用户已确认正常 Action=`CREATE`。来源字段存在但语义并非 `Y/N`，映射未实现。不能由订单确认、picking 状态或样例单独推定是否应发 `Y`。仅阻塞 API08 完整 Payload。 |
| API07 相同编码跨 owner | Odoo 原生 `product.product.default_code` 是索引字段；核心 `_onchange_default_code()` 只给 UI warning，没有全局唯一 ORM/SQL 约束。ORM 临时创建两个同码产品成功并回滚。`services.api07()` 则额外在复合键未命中时拒绝任何全局同码产品。既有 Hoymiles inbound/outbound 等控制器按 `default_code` 单字段搜索并 `limit=1`。 | API07 冻结键为 `owner + productCode`，但放开跨 owner 同码会使既有 WMS 单字段查找歧义；继续拒绝则无法为第二 owner 建立独立复合键产品。未改唯一性规则、服务逻辑或测试预期，等待 Human Review 定边界。 |

当前 UI 为标准持久化 Form/Notebook；没有 Ginlong 回传 `TransientModel` Wizard。用户补录字段先保存，再由按钮读取 ORM；API04 的 picking 选择及 API10 的实盘结果选择均持久化。每次 HTTP 尝试新增现有 API 日志行，不改写旧日志。用户已明确统一 `POST` 与 `Content-Type: application/json`，因此下方更早关于 method/header 未确认的描述只保留资料历史，不再代表当前实施 Open Item。真实 Ginlong 与完整浏览器人工验收未运行。

Ginlong 测试/正式 Base URL 和无鉴权/Key 事实沿用 TDD v0.4.1。用户已补充本 CC 五个回传 API 的 objectid，并明确统一 HTTP POST、`Content-Type: application/json`。后台配置完整 Endpoint URL；这些调用设置用于本地 Mock，真实 Ginlong 请求未执行。API04/API10 已完成已确定正常场景的 Payload 组装和 Mock 验收；API02/06/08 在各自字段缺项处阻止发送，不省略必填字段冒充接口通过。

#### 共用协议字段

下表保留最初逐字段核对时的资料状态，不能单独视为当前实施阻塞清单；后续用户确认及当前代码/测试结果以 §7.4 为准，仍未解决的事项汇总于 §7.3。尤其是 HTTP 方法和 Content-Type 已由后续接口矩阵确认。

| 字段 | V3.2 事实 | 缺口归属 | 影响 |
|---|---|---|---|
| 每个 API 的 `{objectid}` | 用户于 2026-11-18 提供 API02=`TPL_Receipt_Confirmation`、API04=`TPL_Inbound_Completion`、API06=`TPL_Picking_Completed`、API08=`TPL_Shipment_Completed`、API10=`TPL_Stocktaking_Completed`。API01/03/05/07 的 objectid 也已在 [V3.2 参数核对记录](../ginlong_apis/V3.2参数核对记录.md) 登记；API09 未提供 | 对本 CC 五个回传接口而言，objectid 已确认；后台完整 URL 配置能力已实现 | 不再阻塞 API02/04/06/08/10 的 Endpoint 配置。管理员仍须将确认值配置到相应环境；API09 objectid 不在本 CC 范围 |
| 每个 API 的 HTTP Method | V3.2 未定义 | Ginlong 协议资料缺失；后台配置能力已实现 | 仅阻塞真实接口配置；不能从 REST 习惯推定 POST/PUT |
| `Content-Type` / 字符编码 | V3.2 提供 JSON 示例，未明确 HTTP Header、字符编码或是否有外层封装 | Ginlong HTTP 协议资料缺失 | 阻塞最终 HTTP 请求封装确认；不会阻塞本地字段来源和 Mock 组件测试 |
| 响应 `returnStatus` | 五个接口样例均为 `Y`；无失败响应样例或枚举解释 | Ginlong 响应协议缺失 | 阻塞 HTTP 2xx 后的业务成功/失败判定，不阻塞请求字段映射 |
| 响应 `exceptionInfo` | 字段存在，样例值为 `OK` 或成功描述；无完整错误码/失败语义 | Ginlong 响应协议缺失 | 阻塞错误分类及回传结果的业务状态解释 |
| 响应 `operationTime` | 为响应字段；样例格式 `yyyy-MM-dd HH:mm:ss`，字段类型说明写 `DateTime(yyyy-MM-dd 00:00:00)` | Ginlong 协议格式有冲突/精度不清 | 阻塞严格响应解析；API02/08 的 `operationTime` **不是请求字段** |
| 请求时间字段格式 | API04/06/10 的 SN 行有必填 `operationTime`；类型说明写 `DateTime(yyyy-MM-dd 00:00:00)`，样例精确到秒 | Ginlong 协议格式/时区未说明；本地来源见逐字段行 | 阻塞严格时间序列化，不阻塞读取现有 Odoo 时间 |

#### API02 收货确认（请求字段）

| 字段 | V3.2 / 本地事实 | 类别与精确阻塞范围 |
|---|---|---|
| `inboundOrderNo` | 必填；`world.depot.inbound.order.reference` 是现有 Ginlong 入库单号 | 来源可映射；本地 Payload 映射未实现。字段本身不需 Ginlong 补充 |
| `action` | 字段写“确认/取消”；触发说明说撤销用“删除”；唯一请求样例却为 `UPDATE` | Ginlong 协议冲突，确认/撤销的精确 wire 值未定；阻塞 API02 请求 action |
| `receiptConfirmed` | 必填 VARCHAR；样例为 `Y`，没有取消样例；本地 `state/status` 可读但不是 `Y/N` | 数据源存在，映射未实现；Ginlong 未给状态枚举/撤销值及 Odoo 状态到值的映射。阻塞完整请求 |

#### API04 入库完成（请求字段）

| 字段 | V3.2 / 本地事实 | 类别与精确阻塞范围 |
|---|---|---|
| `owner` | 必填；来源 `inbound.order.ginlong_owner_code` | 来源可映射；Payload 映射未实现，不需新增货主映射模型 |
| `action` | 表格写“创建/删除”，样例有 `CREATE`；撤销说明要求删除对应撤回 SN 清单，无 DELETE 请求样例 | CREATE 值已由样例确认；删除的 wire 字面值/撤回报文未确认，只阻塞删除/撤销场景 |
| `inboundOrderNo` | 必填；来源 `inbound.order.reference` | 来源可映射；Payload 映射未实现 |
| `snList[].productSN` | 必填；实际来源 `stock.move.line.lot_id.name` | 有 `lot_id` 的行可映射；未编码。若实际行无 Lot/SN，属于该单据本地数据缺失，不能造值 |
| `snList[].quantity` | 必填；实际来源 `stock.move.line.quantity` | 来源可映射；Payload 映射未实现 |
| `snList[].palletCode` | 必填；实际来源 `stock.move.line.result_package_id.name`，空时可读取 `package_id.name` | 已分包的行可映射；Payload 映射未实现。无包裹记录的行是本地数据缺失，不能由计划托盘补造 |
| `snList[].productCode` | 必填；实际来源 `stock.move.line.product_id.default_code`；API07 将 Ginlong `productCode` 保存到该 Odoo 字段 | 来源可映射；Payload 映射未实现 |
| `snList[].operator` | 必填；`stock.move.line` 没有实际作业人字段；`stock.picking.user_id` 是负责人，`create_uid/write_uid` 是记录维护人 | 本地实际数据缺失；不得改用负责人、创建人或回传用户。若由业务方提供实际作业记录或 Wizard 允许补充，才可解除该字段阻塞；补充输入目前未实现 |
| `snList[].operationTime` | 必填；实际 `stock.picking.date_done` / `inbound.order.i_datetime` 可提供实际完成时间，但粒度为 picking/订单，不是独立 SN 操作时刻 | 本地来源有较粗粒度时间，Payload 映射未实现；Ginlong 需确认该完成时间是否可作为每条 SN 的 operationTime，以及时间格式/时区 |
| 本次 `snList` 范围 | V3.2 描述支持部分过账；触发说明又写第三方整单确认完成时调用 | Ginlong 语义冲突；阻塞部分 picking/部分 SN 何时及以何范围发送。不是 API04 的订单/作业数据源缺失 |

#### API06 备货完成（请求字段）

| 字段 | V3.2 / 本地事实 | 类别与精确阻塞范围 |
|---|---|---|
| `owner` | 必填；来源 `outbound.order.ginlong_owner_code` | 来源可映射；Payload 映射未实现 |
| `action` | 表格写“创建/删除”，样例有 `CREATE`；撤销说明要求删除对应撤回 SN 清单，无 DELETE 请求样例 | CREATE 值已由样例确认；删除 wire 字面值/撤回请求范围未确认，只阻塞删除/撤销 |
| `outboundOrderNo` | 必填；来源 `outbound.order.reference` | 来源可映射；Payload 映射未实现 |
| 备货完成事件 | 现有 WMS 在内部出库作业完成后记录 `outbound.order.status='picking'`、`picking_PICK` 和 `picking_PICK_date`；相关 `stock.picking`/move line 可展示实际作业 | 本地来源已查明并由 ATR-RUN-026 组件测试覆盖。Wizard 显示该状态/作业时间；按钮仍可手动打开，不增加状态门禁。此项不再是 Open Item |
| `snList[].productSN` | 必填；来源 `stock.move.line.lot_id.name` | 有 Lot/SN 行可映射；未编码；缺 Lot 的单据是本地数据缺失 |
| `snList[].quantity` | 必填；来源 `stock.move.line.quantity` | 来源可映射；Payload 映射未实现 |
| `snList[].palletCode` | 必填；来源 `result_package_id.name` / `package_id.name` | 已分包行可映射；未编码；Odoo package 是否等于 Ginlong pallet 需要按实际数据口径核实 |
| `snList[].productCode` | 必填；来源 `stock.move.line.product_id.default_code`，API07 使用此字段保存 Ginlong 编码 | 来源可映射；Payload 映射未实现 |
| `snList[].operator` | 必填；move line/picking 无实际操作人字段；负责人或记录创建人不代表 KR 现场操作人 | 本地实际数据缺失；不能以订单负责人、`user_id`、`create_uid` 或回传用户代替。人工补充输入尚未实现 |
| `snList[].operationTime` | 必填；关联 picking 的 `date_done`/`picking_PICK_date` 可提供拣选完成时间，但不是每条 SN 的单独操作时刻 | 本地来源有 picking 粒度时间，映射未实现；需确认 Ginlong 接受该实际完成时间作为各 SN 操作时间，并确认格式/时区 |
| `palletQty` | 必填 DECIMAL；实际 move line 有 package 关系，picking 有 package levels；订单 `pallets_of_pick/packed`、`pack.info` 也存在，但不是与本次所选 picking 明确绑定的实绩数 | 本地数据映射/实绩口径未完成；包裹数不自动等于托盘数。需要按实际 picking 记录确定本次托盘数，不用订单计划数 |
| `totalWeight` | 必填 DECIMAL；`stock.picking.shipping_weight` 可读取（按实际 picking 包装/产品重量计算），订单 pack info 另有 gross/net weight | 本地候选来源存在，但映射未实现；Ginlong 未说明 totalWeight 是净重/毛重/是否含包装；V3.2 DECIMAL 声明与样例字符串值 `"4"` 冲突 |
| 本次 picking/SN 范围 | V3.2 写支持部分过账，触发说明写整单出库下架完成时调用；现有 wizard 可选择关联 picking | Ginlong 触发范围互相矛盾；本地选择 UI 已有，序列化范围未实现。只阻塞部分/整单 Payload，不阻塞 API06 的既有事件读取 |

#### API08 发货完成（请求字段）

| 字段 | V3.2 / 本地事实 | 类别与精确阻塞范围 |
|---|---|---|
| `outboundOrderNo` | 必填；来源 `outbound.order.reference` | 来源可映射；Payload 映射未实现 |
| `action` | 字段写“确认/取消”；触发说明说撤销用“删除”；JSON 样例却为 `CREATE` | Ginlong 协议冲突，确认/撤销精确 wire 值未定；阻塞 API08 action |
| `shipmentConfirmed` | 必填 VARCHAR；确认事件的样例值却是 `N`；本地 `state/status` 可读 | 数据源存在，映射未实现；Ginlong 未说明 `Y/N` 与 `CREATE/UPDATE/DELETE` 的组合关系，阻塞完整请求 |
| `operationTime` | V3.2 将其列在响应字段，不在 API08 请求参数中 | 不构成 API08 请求字段阻塞；无需从 picking 生成请求 operationTime |
| 作业单/picking 范围 | API08 请求没有 picking/SN 字段；项目边界规定来源是出库 Order 状态 | 不属于本接口字段阻塞；不再把部分/多 picking 列为 API08 Open Item |

#### API10 盘点完成（请求字段）

| 字段 | V3.2 / 本地事实 | 类别与精确阻塞范围 |
|---|---|---|
| `owner` | 必填；来源 `world.depot.stocktake.order.owner_code` | 来源可映射；Payload 映射未实现 |
| `action` | 表格写“创建/删除”，样例有 `CREATE`；撤销说明要求删除要撤回的 SN 清单，无 DELETE 样例 | CREATE 值已由样例确认；删除 wire 字面值/撤销范围未确认，只阻塞撤销场景 |
| `countOrderNo` | 必填；来源 `world.depot.stocktake.order.count_order_no` | 来源可映射；Payload 映射未实现 |
| `snList[].productSN` | 必填；来源 `world.depot.stocktake.result.serial_number` | 实盘字段已存在；Payload 映射未实现 |
| `snList[].quantity` | 必填；来源 `world.depot.stocktake.result.quantity` | 实盘字段已存在；Payload 映射未实现 |
| `snList[].palletCode` | 必填；来源 `world.depot.stocktake.result.pallet_code` | 实盘字段已存在；Payload 映射未实现；不使用计划托盘补值 |
| `snList[].productCode` | 必填；来源 `world.depot.stocktake.result.product_code` | 实盘字段已存在；Payload 映射未实现 |
| `snList[].operator` | 必填 VARCHAR；来源 `result.operator_id`，是真实仓库操作人关系 | 操作人来源存在；映射未实现。Ginlong 只定义字符串类型，未定义应发送 `login`、显示名或其他人员编码 |
| `snList[].operationTime` | 必填；来源 `result.operation_time`，是实际结果时间 | 实盘时间来源存在；映射未实现；Ginlong 日期格式/时区说明与样例精度不一致 |
| 本次结果范围 | V3.2 一处说明支持部分采集，触发说明又说整单采集完成后调用；当前 Wizard 读该订单全部 `result_ids`，没有选取部分结果的输入 | Ginlong 发送范围语义未定 + 本地部分结果选择未实现；仅阻塞部分/累计/撤销场景。完整结果字段来源可继续映射；严禁用计划范围或 `stock.quant` 代替 |

### 7.2 盘点模型核查与实施记录

实施前源码与既有 ORM registry 核查发现：`worlddepot` 中没有客户盘点订单/仓库实盘结果两个模型；旧 `ginlong.stocktake.task` / `.line` 是 Ginlong 独立盘点实现，ORM 记录均为 0，源码调用范围仅为旧 API05 服务、测试及 ACL。批准后将其改为 `worlddepot` 内的 `world.depot.stocktake.order` 和 `world.depot.stocktake.result`，API05 只写客户指令/计划范围，API10 从关联实盘结果读数。旧 Ginlong 模型和 ACL 已移除。通过当前 ORM shell 核对，两个新模型、字段和视图已注册，旧模型不再注册。实际 ORM 自动化已确认实盘 SN 显示而计划 SN 不显示；全程未读取 `stock.quant`、未执行 SQL。

### 7.3 其他未决项

| 项目 | 状态 | 影响 |
|---|---|---|
| CC-GIN-003 v1.1 | Frozen with Open Items / Human Review APPROVED | 本地与 Mock HTTP 实施获授权；本 ATR 记录执行结果 |
| Ginlong 外部联调 | BLOCKED / 未执行 | 本 CC 不访问真实端点，实际网络联调留最终集成 CC |
| API03 接口方向 | 已确认 | 后续 Ginlong 接口矩阵明确为 Ginlong→Odoo；旧 A-003 本地假设已被新资料取代，V3.2 初始核对记录保留为历史 |
| CC-TEST-010/017/019 | PASS（自动化） | CC-TEST-010 结合 ATR-RUN-014 四 Worker 同请求 HTTP 证据及 ATR-RUN-026 双 ORM cursor 提交重放/回滚接管；CC-TEST-017 有实际 Cursor commit 失败原子性注入；CC-TEST-019 有 ATR-RUN-016 HTTP 响应丢失代理及 ATR-RUN-026 数据库并发重放。未执行完整人工 WMS E2E，按范围留最终集成 CC |
| CC-TEST-023 API07 owner 复合映射 | PASS（当前，详见 §7.4） | 早期冲突已由本轮 owner resolver 和自动化解决；旧分析及运行保留于 IHR-016/ATR-RUN-039 |
| CC-TEST-024 受影响 WMS 自动回归 | PASS（自动化范围） | 当前最终证据为 ATR-RUN-043/044/047；完整人工 WMS E2E 留最终集成 CC |
| 模板同步 / Engineering canonical 指南同步 | BLOCKED | 保留已批准流程例外，不标记 PASS |

### 7.4 v1.4 最终规则与当前验收状态

| 范围 | 用户最终规则 | 当前代码与验收 |
|---|---|---|
| API02 `receiptConfirmed` | 从持久化收货明细读取；明细状态一致时回传该值，混合 Y/N 不发送；不实现取消控制/回传 | 同状态 Payload、失败修改后重试和每次独立日志通过；混合状态阻止发送及日志追加测试通过 |
| API06 `palletQty` | 对本次选中实际 `stock.move.line.package_id` 去重；已保存人工值优先 | 实际托盘计数与覆盖测试通过 |
| API06 `totalWeight` | 使用 V3.2 API07 `weight` 对应的 `product.ginlong_weight` × 实际数量；毛重默认净重，可保存人工修改 | 重量计算/覆盖通过；DECIMAL(18,6) 按用户最终确认的 V3.2 JSON string 样例规范化输出，并由 Mock 测试验证 |
| API08 `shipmentConfirmed` | 从持久化发货明细读取；明细状态一致时回传该值，混合 Y/N 不发送；不实现取消控制/回传 | 同状态 Payload 及混合状态阻止发送/追加日志测试通过 |
| API07 `owner + productCode` | 允许不同 owner 同码；服务和现有 WMS 查询按货主消歧，无法唯一定位时明确报错 | 跨 owner 创建、查询、更新、API01/03 产品定位及共享 WMS resolver 测试通过 |

ATR-RUN-048 Ginlong 全量 31 post-tests、ATR-RUN-044 `worlddepot` 全量 8 post-tests、ATR-RUN-046 最终规则定向 3 post-tests 均为 0 failed / 0 error。外部撤销/部分执行语义与真实联调仍按最终集成 CC 承接；它们未被伪记通过，也不阻塞本 CC 已确认正常场景。模板同步仍 `BLOCKED`，沿用批准的流程例外。

### 7.5 关闭状态记录

2026-11-18，Human Review 批准 CC-GIN-003 关闭。FR-GIN-003 v1.0 判定 Closure SATISFIED；CC-GIN-003 v1.5 登记 Closed，Implementation Plan v1.5 同步状态。关闭阶段未修改代码、未新增测试运行，也未覆盖任何既有 ATR 结果。真实 Ginlong 联调、完整浏览器/WMS 人工 E2E、外部撤销/部分执行语义和项目后续需求仍按各自 Open Items 管理；模板同步继续 BLOCKED，沿用已批准例外。

## 8. 多 Worker 限流性能验收结果

CC-TEST-016 已按冻结标准完成：四个 Odoo HTTP worker、16 个 HTTP 客户端，在同一 UTC 固定秒窗口提交 101 个不同且有效的 API07 产品请求；100 个返回 HTTP 200，1 个返回 HTTP 429 并带 `Retry-After: 1`。完整时延、事务冲突/重试和 ORM 结果见 CC-TEST-016 矩阵与 ATR-RUN-010。首次无效客户端突发失败及旧 worker 阈值缓存运行均保留在 ATR-RUN-009、011，不覆盖有效结果。

## 9. 证据库存

- 既有入站 runner 日志：`/tmp/atr-ginlong-003-run-009.log`（ATR-RUN-017，15 项，0 failed / 0 error）。本轮回传/盘点定向日志见下方 PID 41123、41686、41931。
- API07 101 请求有效结果：`/tmp/ccgin003_api07_101_results.json`；详见 ATR-RUN-010。
- 默认 10/10/10 限流：`/tmp/ccgin003_default_limits_10_10_10_r3.json`；详见 ATR-RUN-012。
- 配置修改/恢复：`/tmp/ccgin003_settings_change.json`；详见 ATR-RUN-015。
- 跨窗口恢复：`/tmp/ccgin003_window_recovery.json`；详见 ATR-RUN-014。
- 调用方/XFF 隔离：`/tmp/ccgin003_caller_identity.json`；详见 ATR-RUN-013。
- 并发同请求与响应丢失：`/tmp/ccgin003_idem_concurrent_commit.json`、`/tmp/ccgin003_response_lost.json`；详见 ATR-RUN-014、016。
- 本轮回传/盘点定向自动化日志：`debug_logs/odoo_181.log` 中 PID 41123、41686、41931、44540、44638、44731（ATR-RUN-018–020、022–024）；每项运行数、时间与边界见 §5。
- 持久化回传自动化运行：`/private/tmp/ginlong_callbacks_test.log` 及 `ginlong_callbacks_test_r2.log`–`r8.log`（ATR-RUN-027–032）；保留失败、零测试筛选和有效重跑原始日志。最新 ORM registry 核验见 ATR-RUN-033。
- CC-TEST-010/017/019 自动化：ATR-RUN-025 首次全套运行失败记录 `/tmp/ccgin003_transaction_completion.log`；修正后有效日志 `/tmp/ccgin003_transaction_completion_r2.log`（ATR-RUN-026，29 post-tests / 0 failed / 0 error）。ATR-RUN-026 通过 Odoo 标准 TransactionCase 使用独立 ORM cursor 覆盖提交重放和回滚接管、真实 `Cursor.commit()` 故障注入、提交后结果重放；HTTP 同请求并发和响应丢失仍引用 ATR-RUN-014/016。完整人工 WMS E2E 留最终集成 CC。
- ATR-RUN-026 可复现命令（使用既有环境）：

```text
venv/bin/python odoo-bin -c odoo.conf -d odooce_karlrapp --test-enable --test-tags /ginlong_apis --stop-after-init --http-port=0 --gevent-port=0 -u ginlong_apis --log-level=info --log-handler=odoo.tests:INFO --logfile=/tmp/ccgin003_transaction_completion_r2.log
```

- 本轮 Odoo Shell ORM 检查：经 `odoo shell -c odoo.conf --no-http` 读取当前 registry；摘要详见 IHR-013，不涉及直接 SQL。
- ATR-RUN-032 可复现命令（使用既有配置、数据库和 venv；七项回传组件测试）：

```text
venv/bin/python odoo-bin -c odoo.conf -d odooce_karlrapp -u ginlong_apis --test-enable --test-tags /ginlong_apis:TestGinlongAPI.test_callback_forms_are_persistent_and_have_no_transient_wizard,/ginlong_apis:TestGinlongAPI.test_api02_open_field_mapping_is_logged_without_blocking_other_apis,/ginlong_apis:TestGinlongAPI.test_api06_and_api08_open_fields_are_isolated_and_logged,/ginlong_apis:TestGinlongAPI.test_api04_sends_saved_move_line_data_and_logs_response,/ginlong_apis:TestGinlongAPI.test_api04_failure_can_be_edited_and_retried_with_separate_logs,/ginlong_apis:TestGinlongAPI.test_api10_persists_action_scope_and_uses_only_saved_actual_results,/ginlong_apis:TestGinlongAPI.test_callback_logs_do_not_expose_endpoint_credentials --stop-after-init --http-port=0 --gevent-port=0 --log-level=info --log-handler=odoo.tests:INFO --logfile=/private/tmp/ginlong_callbacks_test_r8.log
```

- ATR-RUN-036 至 ATR-RUN-038 可复现命令（使用既有配置、数据库和 venv）：

```text
venv/bin/python odoo-bin -c odoo.conf -d odooce_karlrapp -u worlddepot --test-enable --test-tags /worlddepot --stop-after-init --http-port=0 --gevent-port=0 --log-level=info --log-handler=odoo.tests:INFO --logfile=/private/tmp/ccgin003_run034_worlddepot.log
venv/bin/python odoo-bin -c odoo.conf -d odooce_karlrapp -u ginlong_apis --test-enable --test-tags /ginlong_apis:TestGinlongAPI.test_api07_creates_and_updates_native_product,/ginlong_apis:TestGinlongAPI.test_api01_and_api03_update_existing_orders,/ginlong_apis:TestGinlongAPI.test_api05_is_independent_and_preserves_task_scope,/ginlong_apis:TestGinlongAPI.test_callback_forms_are_persistent_and_have_no_transient_wizard,/ginlong_apis:TestGinlongAPI.test_api04_sends_saved_move_line_data_and_logs_response,/ginlong_apis:TestGinlongAPI.test_api04_failure_can_be_edited_and_retried_with_separate_logs,/ginlong_apis:TestGinlongAPI.test_api10_persists_action_scope_and_uses_only_saved_actual_results,/ginlong_apis:TestGinlongAPI.test_api02_open_field_mapping_is_logged_without_blocking_other_apis,/ginlong_apis:TestGinlongAPI.test_api06_and_api08_open_fields_are_isolated_and_logged --stop-after-init --http-port=0 --gevent-port=0 --log-level=info --log-handler=odoo.tests:INFO --logfile=/private/tmp/ccgin003_run034_ginlong.log
venv/bin/python odoo-bin -c odoo.conf -d odooce_karlrapp -u ginlong_apis --test-enable --test-tags /ginlong_apis:TestGinlongAPI.test_api01_and_api03_update_existing_orders --stop-after-init --http-port=0 --gevent-port=0 --log-level=info --log-handler=odoo.tests:INFO --logfile=/private/tmp/ccgin003_run038_order_picking.log
```

- ATR-RUN-040 可复现命令（接口源字段只读展示及 Open Item 隔离）：

```text
venv/bin/python odoo-bin -c odoo.conf -d odooce_karlrapp -u ginlong_apis --test-enable --test-tags /ginlong_apis:TestGinlongAPI.test_callback_forms_expose_existing_order_and_picking_sources,/ginlong_apis:TestGinlongAPI.test_api02_open_field_mapping_is_logged_without_blocking_other_apis,/ginlong_apis:TestGinlongAPI.test_api06_and_api08_open_fields_are_isolated_and_logged --stop-after-init --http-port=0 --gevent-port=0 --log-level=info --log-handler=odoo.tests:INFO --logfile=/private/tmp/ccgin003_run040_callback_sources.log
```

- 保留失败/无效日志：ATR-RUN-004 的自动化失败、ATR-RUN-009 的客户端重置、ATR-RUN-011 的旧 worker 缓存阈值记录及更早运行日志均保留。
- 本轮可复现运行：ATR-RUN-043 使用 `venv/bin/python odoo-bin -c odoo.conf -d odooce_karlrapp -u ginlong_apis --test-enable --test-tags /ginlong_apis --stop-after-init --http-port=0 --gevent-port=0 --log-level=info --log-handler=odoo.tests:INFO --logfile=/private/tmp/ccgin003_ginlong_full_r1.log`；ATR-RUN-044 使用相同环境将模块/筛选改为 `-u worlddepot --test-tags /worlddepot`，日志 `/private/tmp/ccgin003_worlddepot_regression_r1.log`。均使用 Odoo 标准测试运行器，不直接连接数据库。
- ATR-RUN-045 的 Odoo Shell ORM 核验输出保存于 `/private/tmp/ccgin003_orm_registry_r1.log`；未运行 SQL、psql、数据库驱动或 stock_barcode。
- ATR-RUN-046 运行命令：`venv/bin/python odoo-bin -c odoo.conf -d odooce_karlrapp -u ginlong_apis --test-enable --test-tags /ginlong_apis:TestGinlongAPI.test_api02_and_api08_block_mixed_saved_detail_statuses,/ginlong_apis:TestGinlongAPI.test_api06_uses_saved_actual_preparation_for_totals,/ginlong_apis:TestGinlongAPI.test_api06_and_api08_send_saved_operation_data --stop-after-init --http-port=0 --gevent-port=0 --log-level=info --log-handler=odoo.tests:INFO --logfile=/private/tmp/ccgin003_final_rules_r1.log`。
- ATR-RUN-047 最终 Ginlong 全量命令与筛选/环境同 ATR-RUN-043，日志为 `/private/tmp/ccgin003_ginlong_final_r1.log`；ATR-RUN-048 同命令日志为 `/private/tmp/ccgin003_ginlong_final_r2.log`；均汇总 `31 post-tests`、`0 failed, 0 error(s)`。
- ATR-RUN-049/050/051/052/054/055 均使用既有 `venv/bin/python odoo-bin -c odoo.conf -d odooce_karlrapp -u ginlong_apis --test-enable --stop-after-init --http-port=0 --gevent-port=0 --log-level=info --log-handler=odoo.tests:INFO`；049 为 6 个定向测试首次失败，050 为修复夹具后的 6 项定向通过，051 为加入 API03 失败日志后的 7 项定向通过，052 为当时版本的 40 个全量 post-tests，054 为 API03 表头更新 4 个定向 post-tests，055 为包含全部最终改动的 40 个全量 post-tests。对应原始日志见运行表。
- ATR-RUN-053 ORM registry 补充核查使用 `venv/bin/python odoo-bin shell -c odoo.conf -d odooce_karlrapp --no-http`；核对模块状态/版本、owner 关系字段、partner owner-code 唯一约束及无测试残留，未执行 SQL。
- 最新 Ginlong addon 指纹：§1。

## 10. 移交摘要

本地 CC-TEST-001–024 自动化验收均有通过证据：Ginlong 最终全量 31 项、worlddepot 全量 8 项、最终规则定向 3 项和 ORM registry 核验通过；CC-TEST-010/017/019 沿用既有通过证据，本轮未重跑。用户已确认 API02/08 混合状态不发送、API06 数值为 JSON string、重量字段取 `product.ginlong_weight`，实现和测试结果见 §7.4。外部撤销/部分执行语义、完整人工 WMS E2E 和真实 Ginlong 联调留最终集成 CC；模板同步仍 BLOCKED 且沿用已批准流程例外。CC-GIN-003 已依据 FR-GIN-003 v1.0（Closure SATISFIED；Human Review APPROVED）关闭；本轮未重跑测试。

以上为 CC-GIN-003 关闭时的移交基线摘要；关闭后的项目负责人决策补充及后续运行结果见 §11，不覆盖或改写关闭时证据。

## 11. CC-GIN-003 关闭后的项目负责人决策补充

本节是按项目负责人明确授权追加的 API01/03 实施记录，不重开或修改 CC-GIN-003 v1.1–v1.5、FR-GIN-003 v1.0 或其关闭证据。

| 决策/测试范围 | 实施与结果 | 证据 |
|---|---|---|
| API01 货主档案 | 将请求 `owner` 按 `res.partner.ginlong_owner_code` 精确匹配；存在则复用，不存在则创建（接口不提供货主名称，显示名使用编码），写入订单上的 `ginlong_owner_id` 直接关系；编码唯一约束防止重复档案。WorldDepot 原有 `owner` 项目关联字段保持不变。 | ATR-RUN-050/051、ATR-RUN-052、Odoo Shell ORM registry 核验 |
| API03 货主及产品 | 要求 `owner` 已存在；每条入站明细按 `ginlong_owner_code + default_code` 查现有产品；无明细的表头更新仍校验订单已有明细与目标 owner 一致；缺货主或缺组合时不创建/修改订单或产品。不同货主同产品编码仍可定位对应产品。 | ATR-RUN-051/054/055 |
| API03 失败日志 | 缺少 owner+productCode 组合时返回 HTTP 400 的 JSON 业务错误，现有 `worlddepot` API logger 将响应记录为 `status=error`、`success=false`。 | ATR-RUN-051 |
| 首次测试失败 | 初次目标运行 6 个 post-tests，1 failed：既有跨 owner 消歧测试在故意清空 owner code 后未恢复夹具，导致 API01 合法地创建新 owner；恢复夹具后重跑。实现/约束不回退，原失败保留。 | ATR-RUN-049，`/private/tmp/ccgin_api01_api03_targeted.log` |
| 目标回归 | 夹具修复后 6 个定向 post-tests 通过；加入 API03 HTTP 业务错误和日志检查后，7 个定向 post-tests 0 failed / 0 error。 | ATR-RUN-050/051，见 §5 |
| 全量 Ginlong 回归 | `ginlong_apis` 最终全量 40 个 post-tests，0 failed / 0 error；包含 API01/03、API07 跨 owner 同码、API09 与回传/幂等限流现有测试。 | ATR-RUN-055 |
| ORM 检查 | 模块 `installed 18.0.2.0.9`；两个现有订单模型上的 `ginlong_owner_id` 均为 `res.partner` Many2one；`res.partner.ginlong_owner_code` 唯一约束已注册；事务测试未留下 owner 记录。 | Odoo Shell ORM，只读检查；详见 IHR-021 |

本补充没有访问真实 Ginlong；不代表完整人工 WMS E2E 或真实联调通过。模板同步仍 `BLOCKED`，保留既有批准例外。

## 附录：版本记录

| 版本 | 日期 | 说明 | 状态 |
|---|---|---|---|
| v0.1 | 2026-11-17 | 建立 CC-GIN-003 实施和测试证据台账。 | In Progress |
| v0.2 | 2026-11-17 | 追加 ATR-RUN-001–008、逐项验收矩阵、真实单进程 HTTP 429 结果、多 Worker 阻塞及遗留 Open Items；保留失败运行。 | In Progress |
| v0.3 | 2026-11-17 | 追加 ATR-RUN-009–017，修正当前真实 Worker/事务验收状态，保留无效/失败运行；记录 API10 双模型业务边界及当前实盘结果模型未定位事实；关联待评审 v1.1 回传修订提案。 | In Progress |
| v0.4 | 2026-11-17 | 更新 v1.1 正式修订稿评审状态，明确 API10 实盘模型缺口只阻塞 API10，API02/04/06/08 按各自条件可独立实施/测试；本轮仍未实施回传代码。 | In Progress |
| v0.6 | 2026-11-18 | 逐字段拆分五个回传 API 的 Ginlong 协议缺失/冲突、本地来源缺失、来源可读但映射未实现和可映射字段；更正 API02/08 请求字段（operationTime 只在响应）、纳入用户补充的 objectid、确认 API06 既有备货事件来源；ATR-RUN-025/026 记录事务测试失败及修复结果，CC-TEST-010/017/019 自动化验收通过；完整人工 WMS E2E 明确留最终集成 CC。 | In Progress |
| v0.7 | 2026-11-18 | 追加持久化 Form/Notebook 回传实现验收，记录 Wizard 移除、API04/10 Mock 成功路径及 API02/06/08 的独立 Open Items；追加 ATR-RUN-027–033，保留视图失败、无效筛选和修复前失败，不覆盖历史记录；模板同步与完整人工 E2E 仍未通过/未执行。 | In Progress |
| v0.8 | 2026-11-18 | 追加 ATR-RUN-034–039：完成 CC-TEST-024 受影响自动回归；验证 API01/03 更新后已有 Picking/move line 不变；用 ORM 澄清 `default_code` 原生不唯一及 Ginlong 层冲突；细化 API02/06/08 的本地字段来源与 V3.2 协议缺项。CC-TEST-023 与回传必填字段映射仍 Open，未关闭。 | In Progress |
| v0.9 | 2026-11-18 | 追加 ATR-RUN-040；更新持久化回传 Form 展示 API02/08 Order 状态及 API06 备货来源字段，并以 3 个 Odoo post-tests 验证展示与未决项隔离。未推导 Ginlong wire 映射，CC-TEST-023 与 API02/06/08 Open Items 保留。 | In Progress |
| v1.0 | 2026-11-18 | 追加 ATR-RUN-041–048：保留首次失败；Ginlong 最终 31 项、worlddepot 8 项、最终规则定向 3 项及 ORM registry 核验通过。API02/08 混合状态阻止及 API06 JSON string 按用户最终确认实现；本地验收通过并提交 Human Review 关闭评估。 | Ready for Human Review |
| v1.1 | 2026-11-18 | 勘误当前记录：依据后续 Ginlong 接口矩阵确认 API03 为 Ginlong→Odoo；将 A-003 降为历史假设，真实外部联调仍未执行。保留所有旧分析与测试记录。 | Ready for Human Review |
| v1.2 | 2026-11-18 | 追加关闭状态记录：依据 FR-GIN-003 v1.0 与 Human Review APPROVED，将 CC-GIN-003 当前状态标记 Closed；不新增测试运行，全部原始测试结果和模板同步 BLOCKED 记录保留 | CC-GIN-003 Closed |
| v1.3 | 2026-11-18 | 追加关闭后项目负责人授权的 API01/03 货主档案及 owner+productCode 校验实施证据；保留首次失败并记录 7 项定向、40 项全量 Odoo 测试及 ORM registry 核验；不改变 CC/FR 关闭历史 | Approved post-closure supplement |
