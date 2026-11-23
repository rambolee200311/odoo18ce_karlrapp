# 自动化测试记录：ATR-GIN-007

## 0. 文档治理与环境

| 字段 | 值 |
|---|---|
| ATR 版本 | v0.4 |
| IHR | [IHR-GIN-007](IHR-GIN-007.md) |
| CC | [CC-GIN-007 v1.0](CC-GIN-007-v1.0.md) |
| 上游基线 | SRS v1.2；TDD v1.5；Implementation Plan v1.9 |
| Module | `ginlong_apis` `18.0.2.0.40`（manifest；Odoo 测试运行器执行模块升级） |
| Database | 既有 `odooce_karlrapp` |
| 执行方式 | Odoo 标准测试运行器、真实本地 HTTP 路由、ORM 断言 |
| 真实外部系统 | NOT ACCESSED |

自动化测试仅通过 Odoo 测试运行器和 ORM；无直接 SQL / PostgreSQL 访问。其后项目负责人完成并报告 HVR-API01-01–06，HVR-API01-07 尚未执行。模板同步维持 BLOCKED，采用已批准流程例外，不伪记 PASS。

## 1. CC 测试覆盖状态

| CC-TEST | 场景 | 状态 | 证据 |
|---|---|---|---|
| 057/058 | 非保税 API01 Add：`snList` 缺失、null、错误类型或错误行被忽略；Order 不保存；日志保留收到的原始报文 | PASS（自动化） | ATR-RUN-005；`test_http_api01_non_bonded_ignores_sn_list_and_logs_original_request` |
| 059–067 | 保税 API01 SN 完整性、单件数量、SN 身份、原材料跨托盘分布、多产品混托与数量汇总 | PASS（定向自动化） | ATR-RUN-005；`test_http_api01_sn_consistency_by_product_tracking`、`test_http_api01_sn_identity_is_product_scoped_and_orders_can_reference_it` |
| 064 | 保税 API01 原材料可省略 `snList`；也可在混合订单中仅提交 SN 产品行 | PASS（自动化） | ATR-RUN-005；同上，ORM 检查数量及无原材料 SN 子记录 |
| API05 回归 | API05 继续按原规则拒绝缺失 SN/托盘行，不受 API01 可选参数影响 | PASS（定向自动化） | ATR-RUN-005；`test_http_api05_sn_consistency_by_product_tracking`、`test_http_api05_accepts_existing_and_unreceived_serial_references` |
| 068 | API01/API05 新增 SN 拒绝路径的整单原子性与无库存副作用 | PASS（自动化） | ATR-RUN-010；每个拒绝用例前后经 ORM 比较单据、成功幂等记录及库存对象快照 |
| 069 | API04 从实际 Picking / Move Line 取数，且来源独立于 API01 预报 | PASS（来源回归） | ATR-RUN-005；API04 测试构造与 API01 预报不同的已选实际 Picking/Move Line，并断言外发数据来自实绩；未实现预报/实收比较 |
| 070 | 其他 API、认证、错误/日志、幂等的完整回归 | PASS（自动化） | ATR-RUN-012；删除经批准的历史 HVR 夹具后，Ginlong 全量 71 个 post-tests 为 0 失败、0 错误；删除前失败记录仍保留于 ATR-RUN-006/008/011 |
| HVR-API01-01–06 | 本地人工 API01 验收 | PASS（项目负责人执行并报告；ORM/API 日志证据已记录） | HVR 执行记录 § API01 HVR；API 日志 3332、3335–3339；旧进程及 Token 首次失败保留 |
| HVR-API01-07 | API04 实际 Picking 出站来源人工核验 | NOT RUN | 预期出站报文已补入测试包；实际 Mock POST、UI 操作和日志证据尚未产生 |

## 2. 运行记录

| Run | 执行 | 结果 | 证据 |
|---|---|---|---|
| ATR-RUN-001 | Python 编译、manifest 语法检查 | PASS | `py_compile` 覆盖 `services.py`、`ginlong_controller.py`、`test_ginlong_api.py`；manifest AST literal 校验成功 |
| ATR-RUN-002 | 首次 API01 HTTP/ORM 定向运行 | FAIL；3 post-tests，1 failed、0 error。保税原材料省略分托行进入新增分支时触发未初始化错误；未调整业务规则 | `/private/tmp/ccgin007_api01_targeted.log`；完整 Odoo traceback 保留 |
| ATR-RUN-003 | 初次 API01/API05 七用例回归 | FAIL；7 post-tests，0 failed、1 error。货主自动建档测试沿用序列号产品夹具，但实际产品为非 SN 跟踪，违反新契约 | `/private/tmp/ccgin007_api01_regression.log`；随后仅修正测试夹具，使该用例不提交虚构 SN |
| ATR-RUN-004 | API01/API05 七用例定向复验 | PASS；7 post-tests，0 failed、0 error，2,429 queries。包含真实 HTTP/ORM 非保税畸形 snList 忽略、保税 SN 规则、产品维度 SN 引用及 API05 回归 | `/private/tmp/ccgin007_api01_regression_retry1.log` |
| ATR-RUN-005 | API01/API05 与 API04 来源独立性最终定向复验 | PASS；8 post-tests，0 failed、0 error，2,637 queries。包括非保税忽略、保税原材料省略/混合订单、SN 校验、跨产品/订单引用、API05 回归及 API04 实际 Picking 数据来源 | `/private/tmp/ccgin007_api01_api04_regression_final.log` |
| ATR-RUN-006 | `ginlong_apis` 全量回归 | PARTIAL；71 post-tests，1 failed、1 error。失败为数据库既有产品 ID 1619 缺 Owner 属性行；错误为既有 API05 Add 测试以 tracking=none 原材料搭配真实 SN 行，业务按契约拒绝后测试仍索引 `success` 字段。API05 业务代码未修改 | `/private/tmp/ccgin007_full_ginlong.log`；完整 traceback 已保留 |
| ATR-RUN-007 | Odoo Shell ORM 模块状态核验 | PASS；`ginlong_apis` state=`installed`，`latest_version=18.0.2.0.40` | 既有 `odoo.conf` 和数据库 `odooce_karlrapp`；只读 ORM 查询 |
| ATR-RUN-008 | 修正 API05 有效测试夹具后的 Ginlong 全量回归 | PARTIAL；71 post-tests，1 failed、0 error。唯一失败为既有数据库产品 ID 1619 缺 Owner 属性行；API01/05/04 定向测试均通过。API05 测试夹具调整未改业务规则 | `/private/tmp/ccgin007_full_ginlong_final.log`；既有产品数据未修改 |
| ATR-RUN-009 | 产品 ID 1619 失败根因只读调查 | PASS（调查完成） | Odoo Shell ORM：ID 1619/模板 1529 创建于 `2026-11-21 08:33:54`，由 OdooBot 创建；字段 `(owner, productCode)` 与组合 `default_code` 正确，但模板无 Owner 属性行、产品无 PTAV。来源为 [prepare_api01_hvr.py](../ginlong_apis/hvr/api01/test_data/prepare_api01_hvr.py) 的 `_seed_ownerless_product()`：为 HVR01-04 特意直接创建“货主联系人尚不存在”的产品夹具，未创建模板变体属性。它是持久化 HVR 测试夹具，不是本轮测试临时夹具，也无证据指向当前 API01/API07 业务代码缺陷；没有修改数据库记录 |
| ATR-RUN-010 | CC-TEST-068 API01/API05 定向 HTTP/ORM 验收 | PASS；2 post-tests，0 failed、0 error，2,299 queries | `/private/tmp/ccgin007_api01_cc068_targeted.log`；每个 API01/API05 SN 业务拒绝路径均断言整单不存在、无成功幂等记录、失败日志存在，并对库存量、Lot、Package、Picking、Move、Move Line 进行请求前后 ORM 快照比较 |
| ATR-RUN-011 | Ginlong 全量回归（加入 CC-TEST-068 快照后） | PARTIAL；71 post-tests，1 failed、0 error，11,047 queries。所有新快照断言通过；唯一失败仍为产品身份全局断言命中 ID 1619 缺 Owner 属性行 | `/private/tmp/ccgin007_full_ginlong_cc068.log`；数据库记录未修改 |
| ATR-RUN-012 | 经用户授权删除产品 1619 后的 Ginlong 全量回归 | PASS；71 post-tests，0 failed、0 error，11,046 queries。产品身份全局断言通过，CC-TEST-068 库存快照断言通过 | 删除前 ORM 检查确认无 quant、lot、move、move line、product/template 引用；Odoo ORM unlink 删除产品 1619 及其唯一模板 1529 并提交。全量日志：`/private/tmp/ccgin007_full_ginlong_after_1619_delete.log` |
| ATR-RUN-013 | 项目负责人完成 HVR-API01-01–06 并报告结果 | PASS（六项符合预期；01 首次旧进程错误后重启复测成功，02 刷新 Token 后重试成功，06 为预期拒绝） | [人工执行记录](../ginlong_apis/hvr/cc_gin_007_v0.1_draft/HVR_GIN_007_Execution_Record.md)；对应 API 日志 3331–3339。HVR-API01-07 仍 NOT RUN，不纳入此 PASS |

### ATR-RUN-005 实际执行命令

```sh
./venv/bin/python odoo-bin -c odoo.conf -d odooce_karlrapp -u ginlong_apis --test-enable --test-tags /ginlong_apis:TestGinlongAPI.test_api01_maps_order_pallet_product_and_serial_without_execution,/ginlong_apis:TestGinlongAPI.test_api01_creates_owner_by_code_and_reuses_it_for_later_orders,/ginlong_apis:TestGinlongAPI.test_api04_sends_saved_move_line_data_and_logs_response,/ginlong_apis:TestGinlongHttpAPI.test_http_api01_non_bonded_ignores_sn_list_and_logs_original_request,/ginlong_apis:TestGinlongHttpAPI.test_http_api01_sn_consistency_by_product_tracking,/ginlong_apis:TestGinlongHttpAPI.test_http_api01_sn_identity_is_product_scoped_and_orders_can_reference_it,/ginlong_apis:TestGinlongHttpAPI.test_http_api05_sn_consistency_by_product_tracking,/ginlong_apis:TestGinlongHttpAPI.test_http_api05_accepts_existing_and_unreceived_serial_references --stop-after-init --http-port=0 --gevent-port=0 --log-level=info --log-handler=odoo.tests:INFO --logfile=/private/tmp/ccgin007_api01_api04_regression_final.log
```

### ATR-RUN-010 实际执行命令

```sh
./venv/bin/python odoo-bin -c odoo.conf -d odooce_karlrapp -u ginlong_apis --test-enable --test-tags /ginlong_apis:TestGinlongHttpAPI.test_http_api01_sn_consistency_by_product_tracking,/ginlong_apis:TestGinlongHttpAPI.test_http_api05_sn_consistency_by_product_tracking --stop-after-init --http-port=0 --gevent-port=0 --log-level=info --log-handler=odoo.tests:INFO --logfile=/private/tmp/ccgin007_api01_cc068_targeted.log
```

ATR-RUN-011 全量回归命令：

```sh
./venv/bin/python odoo-bin -c odoo.conf -d odooce_karlrapp -u ginlong_apis --test-enable --test-tags /ginlong_apis --stop-after-init --http-port=0 --gevent-port=0 --log-level=info --log-handler=odoo.tests:INFO --logfile=/private/tmp/ccgin007_full_ginlong_cc068.log
```

ATR-RUN-012 全量回归命令：

```sh
./venv/bin/python odoo-bin -c odoo.conf -d odooce_karlrapp -u ginlong_apis --test-enable --test-tags /ginlong_apis --stop-after-init --http-port=0 --gevent-port=0 --log-level=info --log-handler=odoo.tests:INFO --logfile=/private/tmp/ccgin007_full_ginlong_after_1619_delete.log
```

## 3. 后续验收

- `CC-TEST-068` API01/API05 新增 SN 拒绝路径的单据原子性与库存无副作用断言已通过。产品 ID 1619 根因确认为持久化 HVR 测试夹具；项目负责人随后明确授权删除。通过 Odoo ORM 删除该产品及唯一模板后，ATR-RUN-012 全量回归通过。ATR-RUN-006/008/011 中删除前的失败证据保留不变。
- HVR-API01-01–06 已由项目负责人执行并记录。HVR-API01-07 是 API04 出站核验，没有应由测试者提交给 Odoo 的输入 JSON；候选实际数据对应的预期 body 见 HVR 包 `test_data/expected/hvr_api01_07_api04_body.json`。在本机 Mock 收到实报文并由负责人核验前，该项保持 NOT RUN。
- 8099 服务已按项目负责人此前要求重启用于人工 HVR；旧进程首次 API01-01 错误及重启后成功复测均保留在执行记录中。

## 4. 修订记录

| 版本 | 日期 | 修订内容 |
|---|---|---|
| v0.1 | 2026-11-23 | 原始 CC-GIN-007 自动化执行记录，历史失败结果保留。 |
| v0.2 | 2026-11-23 | 完成 ID 1619 只读根因调查；CC-TEST-068 增加 API01/API05 拒绝路径的整单原子性和库存对象快照；追加 ATR-RUN-009–011。 |
| v0.3 | 2026-11-23 | 按用户授权通过 ORM 删除 HVR 夹具产品 1619 和唯一模板 1529；追加全量回归 ATR-RUN-012（71 项全部通过），不覆盖删除前失败记录。 |
| v0.4 | 2026-11-23 | 记录项目负责人报告的 HVR-API01-01–06；明确 HVR-API01-07 是 API04 出站报文比对而非入站 JSON，并补充预期 body 文件引用。 |
