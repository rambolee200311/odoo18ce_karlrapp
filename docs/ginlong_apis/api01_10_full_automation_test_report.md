# Ginlong API01–API10 自动化验收报告

| 项目 | 结果 |
| --- | --- |
| 项目 / 模块 | `odoo18ce_karlrapp` / `ginlong_apis` |
| 测试数据库 | `odooce_karlrapp`（通过现有 `odoo.conf` 和 Odoo ORM 测试框架） |
| 测试日期 | 2026-11-19 |
| 模块版本 | `18.0.2.0.13` |
| 最终结论 | **PASS（本地自动化与 Mock HTTP 范围）** |

## 1. 执行摘要

完成了现有 `ginlong.api.idempotency` 双向幂等处理器、静态策略及五个出站回调的接入，并对 Ginlong 模块执行完整 Odoo 自动化套件。最终运行结果为 **61 项模块测试、57 项 post-install 测试、0 failed、0 error**。测试包括真实 Odoo HTTP 入站路由、ORM 持久化和回滚断言，以及发往本机 Mock HTTP 接收端的真实 POST。

测试期间的唯一约束冲突日志来自并发测试中两个事务争抢同一幂等唯一键；竞争事务在数据库唯一约束处被序列化，测试断言确认只有一个业务执行/外发请求，Odoo 套件最终结果为通过。该日志是测试覆盖的并发竞争路径，不是未处理测试失败。

## 2. 本次实现与复用

- 复用 `ginlong.api.idempotency`，没有新建第二张幂等表。记录包含 API、方向、Action、业务键、事件键、Payload 指纹、状态、尝试次数和结果。
- 新增 `data/idempotency_rules.json`，按 API01–10 声明方向、业务键、Action 策略、事件及版本来源；API09 明确不使用持久化幂等。
- 入站 Add/Delete 采用相同业务键和请求指纹去重；Edit 按 repeatable 策略每次执行。业务失败时回滚本次幂等占位和同事务业务变更，使相同请求可重试。
- 出站 API02/04/06/08/10 用来源记录、业务事件、Action、版本上下文及 Payload 指纹生成稳定本地事件键。成功结果复用；失败允许重试；超时记录为 `unknown`，同一事件可再次发送。每次实际发送继续追加现有 API 日志。
- 字段必填与类型校验器保持独立。本轮完整模块回归覆盖其现有测试，没有把字段校验逻辑并入幂等器。
- 为保持 API03 重复 Edit 的事务完整性，替换明细时先在同一事务内删除旧明细再创建新明细，避免对必填订单外键写入空值。

主要相关文件：

- `mymodules/ginlong_apis/idempotency.py`
- `mymodules/ginlong_apis/data/idempotency_rules.json`
- `mymodules/ginlong_apis/models/api_control.py`
- `mymodules/ginlong_apis/models/ginlong_callbacks.py`
- `mymodules/ginlong_apis/services.py`
- `mymodules/ginlong_apis/tests/test_ginlong_api.py`
- `mymodules/ginlong_apis/__manifest__.py`

## 3. 执行环境与命令

执行完整模块升级及测试的命令：

```bash
./venv/bin/python odoo-bin -c odoo.conf -d odooce_karlrapp -u ginlong_apis \
  --test-enable --test-tags /ginlong_apis --stop-after-init \
  --http-port=0 --gevent-port=0 --log-level=test \
  --logfile=/tmp/ginlong_apis_test_20261119_5.log
```

最终日志：`/tmp/ginlong_apis_test_20261119_5.log`

关键执行摘要：

```text
57 post-tests in 8.68s, 7364 queries
ginlong_apis: 61 tests 7.70s 7097 queries
0 failed, 0 error(s) of 57 tests
```

执行前对本次涉及的 Python 文件运行了 `py_compile`，并运行 `git diff --check`；两项均通过。Odoo 命令退出码为 `0`。

## 4. 通用组件结果

| 组件 | 状态 | 实际行为证据 |
| --- | --- | --- |
| 必填字段校验器 | IMPLEMENTED / PASS | 回归测试覆盖缺失、null、空白、合法 `0`、嵌套字段路径及不修改原 Payload。 |
| 字段类型校验器 | IMPLEMENTED / PASS | 回归测试覆盖非必填 Decimal 的缺失/null/空字符串跳过、数值零、合法日期时间及非法类型。 |
| 双向幂等处理器 | IMPLEMENTED / PASS | 测试验证入站一次性/可重复策略、事务回滚与响应丢失重放；出站成功重放、失败/超时重试、不同 Payload 分事件及并发单次 POST。 |

## 5. API01–API10 逐接口验收

| API | 状态 | 入口/数据来源及实际断言 |
| --- | --- | --- |
| API01 入库单 | **PASS** | `TestGinlongHttpAPI.test_http_api01_add_replay_delete_authentication_and_validation` 经真实 HTTP 路由验证 Bearer Token、Add 重放返回同一单据、Del 重放不重复取消、必填错误无单据副作用、无效 Token 返回 401。ORM 断言订单、货主和幂等记录；`test_api01_creates_owner_by_code_and_reuses_it_for_later_orders` 验证新货主按编码创建及后续复用。 |
| API02 收货确认 | **PASS** | `test_all_five_callbacks_send_real_http_and_replay_successful_events` 和 `test_api02_uses_saved_receipt_details_and_logs_each_retry` 验证从已保存 `inbound.order` 收货明细生成 JSON、真实 POST、重复触发不再发送、每次按钮触发留日志；混合明细状态按已确认规则阻止发送。失败 503 和超时场景另见出站失败/超时用例。 |
| API03 出库单 | **PASS** | `test_http_api03_valid_owner_product_add_edit_delete_and_rejection` 经真实 HTTP 验证 Add 去重、Edit 可重复执行、Del 仅取消、货主与产品组合定位、无效组合返回业务错误且无部分订单/货主写入；在补齐有效货主产品后，相同拒绝请求可重试成功。 |
| API04 入库完成 | **PASS** | 本地 Mock 接收端收到由已完成入库 `stock.picking` / `stock.move.line` 生成的 POST；断言 SN、托盘及响应记录；`test_api04_failure_can_be_edited_and_retried_with_separate_logs` 验证失败后修改并重试、日志逐次追加。未将 API02 收货确认当作入库完成。 |
| API05 盘点单 | **PASS** | `test_http_api05_add_repeatable_edit_and_delete` 经真实 HTTP 验证 Add、Edit 重复执行、Del 的订单状态结果及 ORM 数据。盘点指令维持 `worlddepot` 盘点订单，不触碰库存账。 |
| API06 备货完成 | **PASS** | 本地 Mock 实际收到 API06 POST；Payload 来源为已保存 `outbound.order` 备货实际数据，断言托盘去重、人工托盘数、净/毛重及 SN 数据。相同成功事件只发送一次；两个独立 ORM 事务并发竞争时 Mock 仅收到一次 POST。未将备货完成与发货完成混淆。 |
| API07 物料档案 | **PASS** | `test_http_api07_add_and_repeatable_edit_use_same_owner_product_variant` 经真实 HTTP 验证 Add 重放、Edit 可重复执行及 `(owner, productCode)` 对应产品变体；产品服务测试覆盖产品创建/更新、`productForm` 与 tracking 规则及非法值拒绝。V3.2 未定义的 Delete 未作为 API07 操作测试。 |
| API08 发货完成 | **PASS** | 本地 Mock 实际收到 API08 POST，Payload 来源于已保存的实际离仓 Picking/发货明细，断言业务状态、发送内容、成功重放及日志；未将 API06 备货完成当作实际发货。 |
| API09 库存查询 | **PASS** | `test_http_api09_queries_by_codes_and_never_persists_idempotency` 经真实 HTTP 查询并按 owner/warehouse 编码隔离；配合交叉货主库存矩阵、未知 owner/warehouse、空库存和库存只读 ORM 断言。重复查询不创建持久幂等行，不执行库存调整。 |
| API10 盘点完成 | **PASS** | 五回调 HTTP 测试和 `test_api10_persists_action_scope_and_uses_only_saved_actual_results` 验证从 `worlddepot` `count.order` 的已保存实盘结果生成 POST；断言仅使用实际结果，不以计划数或 `stock.quant` 推算，重复成功事件复用结果。 |

## 6. 幂等、异常与事务测试证据

- 入站策略：`test_inbound_add_delete_once_and_edit_always_reexecutes` 验证 Add/Delete 首次执行后重放不重复执行，Edit 包含相同 Payload 也每次执行；`test_idempotency_business_keys_and_different_content_reach_operation` 验证不同内容交由业务层处理。
- 失败恢复：`test_idempotency_failure_rolls_back_and_allows_retry` 验证失败回滚后重试可完成；API03 HTTP 测试验证无效货主/产品组合无部分业务记录，之后补齐档案后同一请求可成功。
- 并发与事务：`test_concurrent_duplicate_waiter_replays_committed_transaction`、`test_concurrent_duplicate_waiter_takes_over_after_rollback`、`test_commit_failure_rolls_back_business_and_idempotency_records` 验证竞争事务、接管与提交失败回滚。
- 响应丢失：`test_response_discard_after_commit_replays_saved_result` 验证业务提交后客户端丢失响应，重试读取原成功结果。
- 出站失败/未知：`test_outbound_http_failure_retries_same_event_then_caches_success` 对本机 HTTP 接收端先返回 503 后返回 200，断言 2 次实际发送、稳定事件指纹、状态/尝试次数及 3 条发送日志；`test_outbound_timeout_is_unknown_then_retried_over_http_and_cached` 验证 Mock 已接收但延迟响应导致超时，状态为 `unknown`，随后同事件重试并缓存成功。
- 出站并发：`test_concurrent_outbound_duplicate_posts_only_once` 使用两个独立 ORM 事务和真实本地 HTTP 接收端竞争相同 API06 事件，接收端仅记录一次 POST，获胜事务及等待事务得到同一成功结果。
- 五个回传按钮：`test_all_five_callbacks_send_real_http_and_replay_successful_events` 对 API02/04/06/08/10 分别触发两次，断言接收端每个事件只收到一次、每个触发均有日志、幂等状态为 succeeded 且一次尝试。

## 7. 未执行项目与限制

以下项目不属于本地自动化 PASS 范围，未执行且未伪记为通过：

1. 未访问真实 Ginlong、生产环境或真实 Karl Rapp Gateway；报告只证明 Odoo 本地行为及 Mock HTTP 交互。
2. 并发幂等使用同一 Odoo 测试进程中的线程和独立数据库事务/游标验证，没有启动多个 Odoo OS Worker 做部署级压力测试。
3. 超时后本地状态记为 `unknown` 并允许同一事件重试；Ginlong 是否按订单号/Action 对远端重复业务结果去重，需真实协议/联调确认。Odoo 无法单方面保证远端 exactly-once。
4. API07 Delete 不在 V3.2 已确认的 Add/Edit 契约内，未实现或验收该操作。

上述事项不阻塞“本地 Odoo 自动化 + Mock HTTP”验收；真实 Ginlong/KR 互操作及多 OS Worker 压测应分别在相应后续集成/部署验收中完成。

## 8. 最终结论

**本地自动化验收：PASS。** 统一字段校验、双向幂等及 API01–API10 的适用本地业务路径均通过当前 Odoo 模块测试。真实外部服务联调和多 OS Worker 压测状态为 **NOT RUN**，不计入本报告的 PASS 范围。
