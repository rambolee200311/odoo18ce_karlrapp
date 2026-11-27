# ATR-GIN-010 — 自动化测试报告

| 项目 | 内容 |
|---|---|
| CC | [CC-GIN-010 v1.0 Frozen](CC-GIN-010-v1.0.md) |
| 数据库 | `odooce_karlrapp`（本地开发） |
| 模块版本 | `18.0.2.0.47` |
| 真实 Ginlong/生产 | 未访问 |
| 人工 HVR | N/A（本 CC 不组织独立 HVR） |

## 1. 执行记录

| RUN | 执行命令/方法 | 结果 | 日志 |
|---|---|---|---|
| ATR-RUN-001 | 首次全量：`./venv/bin/python odoo-bin -c odoo.conf -d odooce_karlrapp -u ginlong_apis --test-enable --test-tags /ginlong_apis --stop-after-init ...` | **FAIL（保留）**；80 post-tests，4 failed，5 error；捕捉到初版行为与并发/回传断言问题 | `/private/tmp/cc-gin-010-ginlong-20261125-run1.log` |
| ATR-RUN-002 | 第二次全量，同一模块升级和测试命令 | **FAIL（保留）**；82 post-tests，3 failed，0 error；发现真实按钮/Mock 期望与稳定事件等待状态处理需修正 | `/private/tmp/cc-gin-010-ginlong-20261125-run2.log` |
| ATR-RUN-003 | `TestGinlongAPI.test_stable_callback_event_serializes_different_confirmation_tokens`、`test_all_five_callbacks_send_real_http_and_keep_api10_unchanged`、`test_api04_mixed_success_and_failed_pickings_defaults_to_only_unsuccessful` 定向运行 | **PASS**；3 post-tests，0 failed，0 error | `/private/tmp/cc-gin-010-ginlong-20261125-targeted4.log` |
| ATR-RUN-004 | 最终全量：`./venv/bin/python odoo-bin -c odoo.conf -d odooce_karlrapp -u ginlong_apis --test-enable --test-tags /ginlong_apis --stop-after-init --http-port=0 --gevent-port=0 --log-level=info --log-handler=odoo.tests:INFO --logfile=/private/tmp/cc-gin-010-ginlong-20261125-final.log` | **PASS**；82 post-tests，0 failed，0 error；Odoo 模块统计 86 tests | `/private/tmp/cc-gin-010-ginlong-20261125-final.log` |
| ATR-RUN-005 | 对修改 Python 执行 `py_compile`；对回传视图 XML 执行 lxml parse | **PASS**；全部通过 | 本报告记录；无独立运行日志 |
| ATR-RUN-006 | `odoo-bin shell -c odoo.conf -d odooce_karlrapp --no-http`，通过 ORM 只读 `ir.module.module` | **PASS**；state=`installed`，installed/latest 均为 `18.0.2.0.47` | 命令输出记于 IHR；未写数据库 |
| ATR-RUN-007 | 检查本地 TCP 8099 监听 | **PASS**；本项目服务已监听 8099 | Odoo 启动日志 `/private/tmp/cc-gin-010-odoo-8099.log` |
| ATR-RUN-008 | 修正 API04 视图说明后重新执行完整模块升级与回归，同 ATR-RUN-004 命令，日志文件改为 `...-final2.log` | **PASS**；82 post-tests，0 failed，0 error；Odoo 模块统计 86 tests；视图在升级阶段实际加载 | `/private/tmp/cc-gin-010-ginlong-20261125-final2.log` |
| ATR-RUN-009 | 重启 8099 后分别以本机 HTTP GET 与 Odoo Shell ORM 只读核查 | **PASS**；`/web/login?db=odooce_karlrapp` 返回 HTTP 200；模块安装版本和 latest version 均为 `18.0.2.0.47` | `/private/tmp/cc-gin-010-odoo-8099.log`；ORM 输出记于 IHR |
| ATR-RUN-010 | 第一轮补齐矩阵缺口的定向运行 | **PASS**；3 post-tests，0 failed，0 error | `/private/tmp/cc-gin-010-gap-tests-20261125.log` |
| ATR-RUN-011 | 扩充历史成功兼容用例后的第一次定向运行 | **FAIL（保留）**；5 post-tests，1 failed，0 error；失败为新增断言取历史结果索引错误，非业务行为失败 | `/private/tmp/cc-gin-010-gap-tests-final2-20261125.log` |
| ATR-RUN-012 | 修正测试断言后的定向重跑 | **PASS**；5 post-tests，0 failed，0 error | `/private/tmp/cc-gin-010-gap-tests-final3-20261125.log` |
| ATR-RUN-013 | 最终补充场景定向运行 | **PASS**；7 post-tests，0 failed，0 error；覆盖 API04 过滤/多 Picking/unknown、API06 聚合、当前 Payload 重读、unknown 分类、write_date 不影响指纹及旧成功日志兼容 | `/private/tmp/cc-gin-010-gap-tests-final4-20261125.log` |

## 2. 验收覆盖摘要

| 验收主题 | 状态 | 实际行为断言 |
|---|---|---|
| API02/04/06/08 首发及业务数据 | PASS | 通过 Odoo 按钮入口构造业务 Payload，实际 POST 到本机 Mock，检查响应、Event 与 Log |
| API02 | PASS | `test_api02_uses_order_status_and_logs_retry_without_picking`、`test_api02_status_mapping_preserves_order_lifecycle` 覆盖订单状态映射、真实 Mock POST 与既有业务状态来源 |
| API04 | PASS | `test_api04_auto_scans_done_incoming_and_uses_picking_actuals`、`test_api04_mixed_success_and_failed_pickings_defaults_to_only_unsuccessful` 覆盖筛选、Picking 粒度、混合状态与真实 HTTP |
| API06 / API08 | PASS | `test_api06_and_api08_send_saved_operation_data` 覆盖现有备货/发货业务数据来源与真实 Mock HTTP；API06 保持订单聚合事件 |
| 成功相同 Payload 重复、确认与取消 | PASS | 取消请求数不增加；确认重新真实 POST，新增 Event/Log 并保留历史 |
| 明确失败与结果未知 | PASS | 明确 N 可人工重试；HTTP 后不确定异常/无 N 的错误及无效响应归 unknown，须风险确认 |
| Payload 指纹 | PASS | 字段顺序、空白/序列化紧凑度、等值 1/1.0 和 API04/06 无序 snList 排列不影响指纹；数字字符串与数值仍有区别；原 Payload 未改 |
| API04 混合 Picking | PASS | 默认仅处理未成功项；成功批次仅在选全量且确认后重发；每 Picking 独立 Event |
| 多用户/标签/令牌同事件并发 | PASS | `test_stable_callback_event_serializes_different_confirmation_tokens` 使用独立用户及 ORM 事务，并在首个 HTTP 挂起时模拟第二标签页；本机 Mock 仅收到一次并发重发，第二调用未发 HTTP、未弹历史成功确认；令牌只消费一次 |
| API10 保持原状 | PASS | 完整模块测试核对 API10 实际 HTTP 发送既有行为；本次未接入新确认机制 |
| Python/XML 语法 | PASS | py_compile 与 lxml parse 全部通过 |
| 完整人工 HVR/真实 Ginlong | N/A / Deferred | 按批准范围不属于 CC-GIN-010 验收；后续按项目 HVR / 联调授权执行 |

## 3. CC-TEST-101～120 证据映射

以下映射明确区分全量 RUN 与后续定向补测；没有把定向运行计入 ATR-RUN-008 的 82 项全量结果。标为 `PASS` 的测试有实际 Odoo 测试执行和断言，测试方法均位于 `mymodules/ginlong_apis/tests/test_ginlong_api.py`。

| CC-TEST | 实际测试方法 / 验证方式 | RUN | 结果与证据摘要 |
|---|---|---|---|
| 101 首次真实发送 | `test_all_five_callbacks_send_real_http_and_keep_api10_unchanged`; `test_api02_uses_order_status_and_logs_retry_without_picking`; `test_api04_auto_scans_done_incoming_and_uses_picking_actuals`; `test_api06_and_api08_send_saved_operation_data` | 008、013 | PASS；真实按钮业务方法向 loopback Mock POST，核对 Payload、Event、API Log 和 ORM 来源 |
| 102 成功同 Payload 再点 | `test_all_five_callbacks_send_real_http_and_keep_api10_unchanged`; `test_legacy_success_log_opens_confirmation_and_repeat_adds_new_http_event` | 008、013 | PASS；确认弹窗出现前无额外 HTTP；含历史成功日志兼容 |
| 103 确认后重发 | 同上；`test_outbound_timeout_requires_risk_confirmation_then_success_requires_repeat_confirmation` | 008、013 | PASS；确认后真实 POST，新增 Event/Log 并保留父记录 |
| 104 取消 | `test_successful_callback_cancel_does_not_send_or_append_http_log`; `test_all_five_callbacks_send_real_http_and_keep_api10_unchanged` | 008 | PASS；取消无 HTTP/HTTP Log，验证来源 Chatter 和事件状态 |
| 105 明确失败重试 | `test_api04_failed_picking_can_be_retried_without_changing_history`; `test_outbound_http_failure_retries_then_requires_explicit_repeat_send` | 008、013 | PASS；明确 N 失败可重试，历史请求和日志保留 |
| 106 网络结果未知 | `test_outbound_timeout_requires_risk_confirmation_then_success_requires_repeat_confirmation` | 008 | PASS；超时先归 unknown，风险确认前无第二次 POST |
| 107 无 N 的 5xx / 无效 2xx | `test_callback_unknown_http_responses_require_risk_confirmation` | 013 | PASS；实际 API02 按钮对两类响应均先显示风险确认，再发送并记录结果 |
| 108 业务 Payload 改变 | `test_outbound_failed_unknown_success_and_changed_payload_are_separate_events`; `test_callback_confirmation_uses_current_payload_after_business_change` | 008、013 | PASS；新业务 Payload 形成独立版本，历史不覆盖 |
| 109 无关字段 / write_date 改变 | `test_callback_write_date_change_does_not_change_repeat_confirmation` | 013 | PASS；变更无关字段及模拟 write_date 后，相同业务指纹仍要求重复发送确认 |
| 110 Payload 规范化 | `test_callback_fingerprint_ignores_json_format_and_unordered_sn_lines`; `test_api06_multiple_pickings_are_one_order_level_event` | 008、013 | PASS；字段序、空白、数值等价及配置明细排列规则不改变指纹，外发 JSON 不被改写 |
| 111 确认期间 Payload 改变 | `test_callback_confirmation_uses_current_payload_after_business_change` | 013 | PASS；确认时重读 ORM，发送最新 `receiptConfirmed=Y`，不发送旧 `N` 快照 |
| 112 确认令牌一次消费 | `test_outbound_timeout_requires_risk_confirmation_then_success_requires_repeat_confirmation`; `test_all_five_callbacks_send_real_http_and_keep_api10_unchanged` | 008 | PASS；重复调用同一向导确认不增加 HTTP 请求 |
| 113 多用户/标签页并发 | `test_stable_callback_event_serializes_different_confirmation_tokens`; `test_concurrent_outbound_duplicate_posts_only_once` | 008 | PASS；独立 ORM 事务竞争同稳定事件，loopback Mock 只收到一次请求 |
| 114 连续按钮/确认点击 | `test_stable_callback_event_serializes_different_confirmation_tokens`; `test_outbound_timeout_requires_risk_confirmation_then_success_requires_repeat_confirmation` | 008 | PASS（后端执行门闩、令牌及 HTTP 次数）；浏览器按钮视觉 loading/disabled 属项目 UI 模拟 HVR，当前仍 NOT RUN，详见项目 HVR 记录，不作为独立 CC HVR |
| 115 API04 多 Picking 混合状态 | `test_api04_mixed_success_and_failed_pickings_defaults_to_only_unsuccessful`; `test_api04_multi_picking_unknown_requires_risk_confirmation`; `test_api04_auto_scans_done_incoming_and_uses_picking_actuals` | 008、013 | PASS；默认未成功项、全量确认、取消及 unknown 风险分支均核对实际 HTTP 数 |
| 116 API04 Picking 事件粒度 | `test_api04_auto_scans_done_incoming_and_uses_picking_actuals`; `test_api04_multi_picking_unknown_requires_risk_confirmation` | 008、013 | PASS；每张符合条件的 Picking 独立 Event/Log，错误 Picking 被排除 |
| 117 API06 多 Picking 聚合 | `test_api06_multiple_pickings_are_one_order_level_event` | 013 | PASS；多个已选 Picking 形成一个订单级 Payload、单一事件及一次 HTTP 请求 |
| 118 旧成功日志兼容 | `test_legacy_success_log_opens_confirmation_and_repeat_adds_new_http_event` | 013 | PASS；多条历史成功日志仍显示最早成功时间，确认重发增加新事件和日志 |
| 119 API10 不变 | `test_all_five_callbacks_send_real_http_and_keep_api10_unchanged`; `test_api10_persists_action_scope_and_uses_only_saved_actual_results` | 008 | PASS；API10 既有按钮与实际数据发送路径保持原行为 |
| 120 Event/Log/Chatter 关系 | `test_successful_callback_cancel_does_not_send_or_append_http_log`; `test_legacy_success_log_opens_confirmation_and_repeat_adds_new_http_event`; `test_all_five_callbacks_send_real_http_and_keep_api10_unchanged` | 008、013 | PASS；只对真实 HTTP 产生 HTTP Log；取消决定及重发父子 Event 可追溯，历史行不覆盖 |

**覆盖边界：** 本地自动化和 Mock 组件集成均通过。CC-TEST-114 的实际 Backend 按钮 loading/disabled 视觉反馈另列项目级浏览器模拟记录；本 CC 不设独立人工 HVR，不能把该项目模拟 HVR 记成自动化测试或 CC 人工 PASS。

## 4. 当前结论

CC-TEST-101～120 已逐项映射到实际测试方法及运行记录。自动化缺口补测 ATR-RUN-013 通过；全量回归仍以 ATR-RUN-008 的 82 post-tests 为证据。早期失败与后续测试断言失败均保留在 RUN-001/002/011 中。模板同步 BLOCKED 按批准例外保留，真实 Ginlong 为 Deferred；CC 独立人工 HVR 为 N/A。

## 3. 失败与预期竞争证据

最终全量运行 Odoo 汇总为 0 failed、0 error。日志中出现的数据库唯一冲突/序列化冲突来自并发竞态用例，测试断言其由协调层捕获且未发第二个 HTTP；API01/03/05/07 业务唯一键并发测试也在同一 Ginlong 套件运行。错误路径测试会记录其模拟异常 traceback（例如用于验证内部异常不泄露给 API 调用方）；这些日志属于测试输入，最终断言确认受保护响应与 API 结果，不是未捕获测试错误。RUN-001/002 失败记录保持原样，修正后 RUN-004 复验通过。

## 4. 结论

CC-GIN-010 的自动化及本地组件集成验收为 **PASS**。模板同步保留 **BLOCKED** 批准例外；外部 Ginlong 响应语义与真实 HTTP 交互 Deferred 至最终联调。CC 关闭仍待 Human Review，不将 N/A、Deferred 或 BLOCKED 伪记为 PASS。
