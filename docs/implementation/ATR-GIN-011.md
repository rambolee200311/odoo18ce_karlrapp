# ATR-GIN-011 — CC-GIN-011 自动化测试报告

| 项目 | 内容 |
|---|---|
| CC | [CC-GIN-011 v1.0 Frozen](CC-GIN-011-v1.0.md) |
| 数据库 | 本地开发库 `odooce_karlrapp` |
| 模块版本 | `ginlong_apis 18.0.2.0.49` |
| 测试范围 | API01/03/05/07/09 入站处理、八项通用组件适用性及响应契约 |
| 真实 Ginlong/生产 | 未访问 |
| 独立人工 HVR | N/A；按冻结 CC 回到项目原 HVR |
| 模板同步 | BLOCKED；沿用已批准流程例外，不记 PASS |

## 1. 执行记录

| RUN | 执行方式 | 实际结果 | 证据 |
|---|---|---|---|
| ATR-RUN-001 | Odoo 模块升级与 Ginlong 全量自动化 | **FAIL（保留）**；旧断言仍期待未预期系统异常使用 HTTP 200；实际实现按批准状态映射返回 500。此为测试预期过时，不是产品代码缺陷 | `/private/tmp/cc-gin-011-ginlong-20261125-run1.log`；失败断言 `AssertionError: 500 != 200` |
| ATR-RUN-002 | 修正系统异常状态断言后的 Odoo Ginlong 全量运行 | **PASS**；89 post-tests，0 failed，0 error；Odoo 模块统计 93 tests | `/private/tmp/cc-gin-011-ginlong-20261125-run2.log` |
| ATR-RUN-003 | 补强五接口 Token/API User 前置条件 HTTP 行为后，模块升级并执行完整 Ginlong 自动化 | **PASS**；91 post-tests，0 failed，0 error；模块统计 95 tests，17,314 queries | `/private/tmp/cc-gin-011-ginlong-20261125-final2.log` |
| ATR-RUN-004 | `py_compile`、JSON 配置校验；Odoo 模块升级加载 Settings XML | **PASS**；Python/JSON 检查成功，XML 实际由模块升级加载 | 命令输出及 RUN-003 模块升级日志 |
| ATR-RUN-005 | 重启后的本机 HTTP 与 Odoo Shell ORM 只读核验 | **PASS**；`127.0.0.1:8099/web/login` 返回 HTTP 200；模块 `installed_version=latest_version=18.0.2.0.49`；API09 限流值为 10 | ORM 输出；8099 PID 15997 正在监听 |

最终全量执行命令：

```text
./venv/bin/python odoo-bin -c odoo.conf -d odooce_karlrapp -u ginlong_apis --test-enable --test-tags /ginlong_apis --stop-after-init --http-port=0 --gevent-port=0 --log-level=info --log-handler=odoo.tests:INFO --logfile=/private/tmp/cc-gin-011-ginlong-20261125-final2.log
```

## 2. CC-TEST-121～139 证据映射

下列方法均位于 `mymodules/ginlong_apis/tests/test_ginlong_api.py` 并由 ATR-RUN-003 实际执行。单一行为测试可支持多个验收项；PASS 代表本地 Odoo HTTP/ORM 与 Mock 行为证据，不表示真实 Ginlong 联调或人工 HVR。

| CC-TEST | 冻结验收内容 | 实际测试方法 / 断言 | RUN | 结果 |
|---|---|---|---|---|
| 121 | 五个路由有效、无效及过期 Token | `test_http_all_inbound_apis_reject_invalid_and_expired_tokens`; `test_api01_decorated_route_authenticates_and_logs_with_existing_logger`；五路由无效/过期均为 401、三字段响应及 AUTH01 日志 | 003 | PASS |
| 122 | 五个路由要求有效 API User，拒绝无关联用户且无业务权限扩展 | `test_http_all_inbound_apis_require_an_api_user_before_business_processing`; `test_http_api09_queries_by_codes_and_never_persists_idempotency`；五路由均 403/AUTH02、业务模型和幂等行数不变、错误日志存在；API09 拒绝时不查库存 | 003 | PASS |
| 123 | Required、Type、幂等、业务、系统错误共用 Error/Log 且不泄露内部异常 | `test_outer_error_wrapper_preserves_business_reason`; `test_ginlong_api_logger_exception_fallback_uses_protocol_response`; `test_http_api07_unexpected_system_error_is_sanitized_and_logged`; `test_http_api01_rate_rejection_and_storage_failure_are_distinct` | 003 | PASS |
| 124 | API01/03/05/07 必填字段和嵌套输入校验、失败无业务写入 | `test_http_api01_add_duplicate_error_delete_authentication_and_validation`; `test_http_api03_valid_owner_product_add_edit_delete_and_rejection`; `test_http_api05_add_repeatable_edit_and_delete`; `test_http_api07_add_duplicate_rejection_and_repeatable_edit`; `test_api09_validates_required_fields` | 003 | PASS |
| 125 | DECIMAL、DateTime、BOOLEAN 类型、错误路径和原始 Payload 不变 | `test_required_nested_datetime_and_generic_optional_non_text_types`; `test_optional_configured_decimal_skips_only_missing_null_and_empty`; API07 真实 HTTP 类型校验 | 003 | PASS |
| 126 | API09 请求/响应契约、库存项字段和只读 | `test_api09_route_uses_existing_token_and_api_logger`; `test_http_api09_queries_by_codes_and_never_persists_idempotency`; `test_http_api09_rate_limit_uses_own_config_and_protocol_error` | 003 | PASS |
| 127 | API01/03/05/07 幂等策略不变；API09 不持久化幂等 | `test_http_api01_add_duplicate_error_delete_authentication_and_validation`; `test_http_api03_valid_owner_product_add_edit_delete_and_rejection`; `test_http_api05_add_repeatable_edit_and_delete`; `test_http_api07_first_add_commits_product_and_idempotency_before_duplicate_conflict`; `test_http_api09_queries_by_codes_and_never_persists_idempotency` | 003 | PASS |
| 128 | 写 API 并发/事务防重；API09 不进入写幂等 | `test_concurrent_duplicate_waiter_replays_committed_transaction`; `test_concurrent_duplicate_waiter_takes_over_after_rollback`; `test_concurrent_effective_add_conflict_is_mapped_by_fresh_orm_state`; `test_concurrent_outbound_duplicate_posts_only_once`; API09 查询前后幂等计数相同 | 003 | PASS |
| 129 | 原限流阈值不变；API09 独立默认 10/秒、配置和超限 | `test_api_rate_defaults_and_configuration`; `test_http_api01_rate_rejection_and_storage_failure_are_distinct`; `test_http_api09_rate_limit_uses_own_config_and_protocol_error`；核对设置、429、Retry-After、RATE01 日志 | 003 | PASS |
| 130 | API01 成功响应严格为 V3.2 三字段 | `test_api01_decorated_route_authenticates_and_logs_with_existing_logger`; `test_http_api01_add_duplicate_error_delete_authentication_and_validation`；真实 HTTP 字段集合断言 | 003 | PASS |
| 131 | API03 成功及失败响应裁剪，业务结果保持 | `test_http_api03_valid_owner_product_add_edit_delete_and_rejection`; `test_api03_rejected_owner_product_pair_returns_and_logs_business_error`；HTTP 字段与订单 ORM 结果断言 | 003 | PASS |
| 132 | API05 成功及失败响应裁剪，盘点指令行为保持 | `test_http_api05_add_repeatable_edit_and_delete`; `test_http_api05_sn_consistency_by_product_tracking`；协议字段与盘点 ORM 结果断言 | 003 | PASS |
| 133 | API07 三字段响应不暴露内部产品 ID | `test_api07_http_response_exposes_only_ginlong_protocol_fields`; `test_http_api07_first_add_commits_product_and_idempotency_before_duplicate_conflict` | 003 | PASS |
| 134 | API09 V3.2 成功字段白名单、库存行白名单及只读 | `test_api09_route_uses_existing_token_and_api_logger`; `test_http_api09_queries_by_codes_and_never_persists_idempotency`; `test_api09_returns_owner_scoped_physical_stock_read_only` | 003 | PASS |
| 135 | ErrorCode、错误体、长度、日志完整诊断 | `test_ginlong_error_catalog_uses_stable_configured_codes`; `test_http_api07_unexpected_system_error_is_sanitized_and_logged`; `test_ginlong_api_logger_exception_fallback_uses_protocol_response`; 限流错误响应/日志测试 | 003 | PASS |
| 136 | 200/Y、200/N、401、403、429、500 状态矩阵 | API01 成功/错误 HTTP 测试；`test_http_all_inbound_apis_reject_invalid_and_expired_tokens`; `test_http_all_inbound_apis_require_an_api_user_before_business_processing`; `test_http_api01_rate_rejection_and_storage_failure_are_distinct`; `test_http_api09_rate_limit_uses_own_config_and_protocol_error`; API07 SYS01 测试 | 003 | PASS |
| 137 | 失败日志、事务边界与历史记录 | `test_commit_failure_rolls_back_business_and_idempotency_records`; `test_idempotency_failure_rolls_back_and_allows_retry`; API01/03/05/07 错误及 API09 Error Log 断言 | 003 | PASS |
| 138 | API09 认证/API User 拒绝先于查询且留日志 | `test_api09_route_uses_existing_token_and_api_logger` 中断言查询服务未调用；`test_http_api09_queries_by_codes_and_never_persists_idempotency`; 五路由 API User HTTP 拒绝用例 | 003 | PASS |
| 139 | 五个真实 HTTP 入口及适用通用组件整体回归 | `TestGinlongHttpAPI` 全部 API01/03/05/07/09 HTTP、ORM、副作用、日志、认证与限流场景 | 003 | PASS |

## 3. 结论与边界

- 最终运行通过：**91 post-tests，0 failed，0 error；模块统计 95 tests**。早期旧断言失败留在 ATR-RUN-001，不覆盖历史。
- 本地 8099 正在监听并返回 HTTP 200；ORM 安装版本为 `18.0.2.0.49`，API09 阈值为 10。
- 未访问真实 Ginlong、生产环境或 Karl Rapp Gateway。真实 Ginlong 是否接受本项目 HTTP 401/403/429/500 映射仍 Deferred。
- CC 不组织独立人工 HVR；模板同步 BLOCKED 继续沿用批准例外，均不伪记 PASS。

**CC-TEST-121～139 自动化证据结论：PASS。**
