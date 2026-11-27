# ATR-GIN-012 — CC-GIN-012 自动化与组件集成验收报告

| 项目 | 内容 |
|---|---|
| CC | [CC-GIN-012 v1.0 Frozen](CC-GIN-012-v1.0.md) |
| 数据库 | 本地开发库 `odooce_karlrapp` |
| Ginlong 模块 | `18.0.2.0.49` |
| WorldDepot 模块 | `18.0.0.6` |
| 外部服务 | 仅本机 HTTP Mock；真实 Ginlong/生产/KR Gateway 未访问 |
| 独立人工 HVR | N/A（CC-012）；项目 HVR 归 CC-005 |
| 模板同步 | BLOCKED；批准例外，未记 PASS |
| 总结 | 自动化/组件集成 PASS；请求关闭评审，不自行关闭 CC |

## 1. 执行记录

| RUN | 方法 | 实际结果 | 证据 |
|---|---|---|---|
| ATR-RUN-001 | 最初运行主链 | **FAIL，保留**。Outgoing reservation 行没有 Lot；不能把未扫描 SN 当作作业实绩。 | `/private/tmp/cc_gin_012_targeted_run1.log` |
| ATR-RUN-002 | 加入 ORM 诊断后重跑 | **FAIL，保留**。move line 与 reservation quant 的 `lot_id=False`，测试需模拟实际扫描步骤。 | `/private/tmp/cc_gin_012_targeted_run2.log` |
| ATR-RUN-003 | 主链推进至日志汇总 | **FAIL，保留**。测试对日志数量/owner 标记的查询范围有误；修正测试域，不改变业务规则。 | `/private/tmp/cc_gin_012_targeted_run3.log` |
| ATR-RUN-004 | 首次重跑修正后查询域 | **ERROR，保留**。Odoo Domain 语法不正确，修正测试代码。 | `/private/tmp/cc_gin_012_targeted_final1.log` |
| ATR-RUN-005 | 一版隔离/主链测试 | **PASS**。2 post-tests，0 failed，0 error；后续补强断言发现收货确认 Chatter 缺口，不作为最终验收。 | `/private/tmp/cc_gin_012_targeted_final2.log` |
| ATR-RUN-006 | 加强 CC-TEST-144 后主链 | **FAIL，保留**。状态改变但没有可核对的收货确认 Chatter 消息。 | `/private/tmp/cc_gin_012_targeted_final3.log` |
| ATR-RUN-007 | 检查 Chatter tracking values | **FAIL，保留**。只有 state、确认人、时间等字段，没有 `status` 前后变化。 | `/private/tmp/cc_gin_012_targeted_final4.log` |
| ATR-RUN-008 | Chatter 断言重试 | **FAIL，保留**。同一实际缺口，未降低断言。 | `/private/tmp/cc_gin_012_targeted_final5.log` |
| ATR-RUN-009 | Chatter 断言重试 | **FAIL，保留**。同一实际缺口，未降低断言。 | `/private/tmp/cc_gin_012_targeted_final6.log` |
| ATR-RUN-010 | Chatter 断言重试 | **FAIL，保留**。同一实际缺口，未降低断言。 | `/private/tmp/cc_gin_012_targeted_final7.log` |
| ATR-RUN-011 | 收货操作日志最小修复后主链 | **PASS**。1 post-test，0 failed，0 error。 | `/private/tmp/cc_gin_012_targeted_final8.log` |
| ATR-RUN-012 | 修正盘点数据来源后主链 | **PASS**。1 post-test，0 failed，0 error，1,631 queries；SN/托盘取自 Done Incoming Picking move line。 | `/private/tmp/cc_gin_012_targeted_final9.log` |
| ATR-RUN-013 | Ginlong 全量回归 | **FAIL，保留**。旧断言期待自动字段跟踪值；更新为实际用户可见的状态操作日志断言。 | `/private/tmp/cc_gin_012_ginlong_final2.log` |
| ATR-RUN-014 | 更新断言后的 Ginlong 全量回归 | **PASS**。93 post-tests，0 failed，0 error；模块统计 97 tests，18,067 queries。 | `/private/tmp/cc_gin_012_ginlong_final4.log` |
| ATR-RUN-015 | WorldDepot 受影响模块回归 | **PASS**。8 post-tests，0 failed，0 error；模块统计 12 tests，112 queries。 | `/private/tmp/cc_gin_012_worlddepot_final2.log` |
| ATR-RUN-016 | Odoo Shell ORM 版本与残留检查 | **PASS**。模块版本确认；测试标记业务/日志数据残留均为 0。 | 本次 Odoo Shell ORM 输出 |
| ATR-RUN-017 | Python 编译与差异空白检查 | **PASS**。`py_compile` 成功；Git 检查使用 `core.whitespace=cr-at-eol` 兼容原 CRLF 文件。 | 本地命令输出 |

早期失败 RUN 作为实际过程证据保留，不被最终通过记录覆盖。

## 2. CC-TEST-140～157 证据映射

主链由 `TestGinlongHttpAPI.test_cc012_full_api01_to_api10_business_mainline_and_stock_invariants` 实际执行。测试使用真实 Ginlong HTTP 路由、ORM、业务按钮、标准 Picking 和本机 Mock；不以结构检查或直接调用 Payload builder 代替集成断言。下表对应最终主链 RUN-012 及完整回归 RUN-014。

| CC-TEST | 场景与断言 | 实际方法 / 证据 | 结果 |
|---|---|---|---|
| 140 | 运行级唯一数据；同 owner/project/warehouse/product；起始物理量、预留量为 0；teardown 核验测试日志和限流清零。 | 主链快照、HttpCase fixture/teardown | PASS |
| 141 | API07 HTTP Add；owner+productCode 唯一变体和模板 serial tracking；无库存副作用。 | HTTP `/TPL_Product_Master`、product ORM、快照 | PASS |
| 142 | API09 入库前真实 HTTP 返回空库存；同 owner/warehouse；无 API09 幂等记录或库存写入。 | HTTP `/TPL_Stock_Query`、ORM 计数及快照 | PASS |
| 143 | API01 HTTP Add 引用 API07 变体；只建预报订单，不建 Picking、Move、Move Line、Lot、Package 或库存。 | HTTP `/TPL_Pending_Receipt_Note`、ORM 和快照 | PASS |
| 144 | API02 planning/arrive 真实按钮回传 N/Y；Chatter 记状态前后值和操作人；生命周期/库存不变。 | API02 按钮、`action_mark_arrived()`、Mock、Chatter ORM | PASS |
| 145 | 标准 Incoming Picking 两个 SN 完成收货；Done move line/Lot/托盘/货主正确；物理量唯一增加 2。 | WMS Picking 工作流、ORM 作业行、快照 | PASS |
| 146 | API04 从订单关联的 Done/Incoming Picking 回传实际 SN/产品/数量/托盘/人员/时间；库存不变。 | API04 业务按钮、Mock HTTP、move line | PASS |
| 147 | API09 入库后返回该 owner/warehouse/product quantity=2；只读。 | HTTP `/TPL_Stock_Query`、前后快照 | PASS |
| 148 | API03 HTTP 创建同 owner/project/product 出库指令并映射相同变体；不建 Picking/库存移动、不预留。 | HTTP `/TPL_Pending_Delivery_Note`、ORM 计数/快照 | PASS |
| 149 | 标准 WMS 备货建立实际作业行，选此前入库形成的 SN；物理量仍 2。 | Outbound preparation、move line ORM、库存/预留快照 | PASS |
| 150 | API06 业务按钮向 Mock 发送已保存备货数据；SN/托盘/重量一致；物理量保持 2。 | API06 按钮、Mock HTTP、快照 | PASS |
| 151 | 仅标准 Outgoing Picking Done 将物理量 2 减至 1，预留归零；发货 SN 与 move line 一致。 | WMS `button_validate()`、ORM 与快照 | PASS |
| 152 | API08 从已保存发货明细及 Done Picking 实绩回传；无二次扣库存。 | API08 按钮、Mock HTTP、发货明细、快照 | PASS |
| 153 | API09 出库后返回物理 quantity=1；查询只读。 | HTTP `/TPL_Stock_Query`、前后快照 | PASS |
| 154 | API05 HTTP 创建同 owner/product 客户盘点指令；无实盘结果、无库存副作用。 | HTTP `/TPL_Stocktake_Order`、盘点 ORM、快照 | PASS |
| 155 | 保存独立实盘结果并关联 API05；SN/托盘来自 Done Incoming Picking move line，不使用计划或 quant 推导。 | `world.depot.stocktake.result` ORM 和来源行断言 | PASS |
| 156 | API10 业务按钮只发送保存的实盘结果；Mock 与结果行一致，库存不变。 | API10 按钮、Mock HTTP、快照 | PASS |
| 157 | 十 API 主链顺序、六个 callback POST、日志/Event 与库存归因均断言；库存仅由两个标准 Done Picking 改变。 | 主链终态 HTTP/Mock/Event/Log/快照断言 | PASS |

### 2.1 物理库存与来源核查

`stock.quant` 仅通过 ORM 只读获取 `quantity`、`reserved_quantity` 和位置/货主/Lot/Package。测试代码不对 quant 执行 `create/write/unlink`。入库前 0；API07/01/02、API04、API09、API03、备货、API06 前后不改变物理数；标准 Incoming Done 唯一产生 `0→2`；标准 Outgoing Done 唯一产生 `2→1`；API08、API05、实盘结果保存、API10 前后为 1。

盘点请求和实盘记录的 SN/托盘来自此前已完成 Incoming Picking 的 move line；API10 Payload 来自持久化 `world.depot.stocktake.result`。`stock.quant` 不用于合成盘点事实。

## 3. 环境与执行命令

Ginlong 全量回归实际命令：`venv/bin/python odoo-bin -c odoo.conf -d odooce_karlrapp -u worlddepot,ginlong_apis --test-enable --test-tags '/ginlong_apis' --stop-after-init --http-port=0 --gevent-port=0 --log-level=info --log-handler=odoo.tests:INFO --logfile=/private/tmp/cc_gin_012_ginlong_final4.log`。

WorldDepot 回归实际命令：`venv/bin/python odoo-bin -c odoo.conf -d odooce_karlrapp -u worlddepot --test-enable --test-tags '/worlddepot' --stop-after-init --http-port=0 --gevent-port=0 --log-level=info --log-handler=odoo.tests:INFO --logfile=/private/tmp/cc_gin_012_worlddepot_final2.log`。

Python 编译与空白检查：`python3 -m py_compile mymodules/ginlong_apis/tests/test_ginlong_api.py mymodules/worlddepot/models/inbound_order.py`；`git -c core.whitespace=cr-at-eol diff --check`。

Odoo Shell ORM 只读核实 Ginlong installed/latest 均为 `18.0.2.0.49`，WorldDepot 均为 `18.0.0.6`；`GINLONG-HTTP-`、`GINLONG-CC012-LOG-` 标记的 API Log、幂等、入库/出库/盘点订单、产品、Picking 均为 0。没有执行 SQL。

最终摘要：Ginlong 93 post-tests/0 failed/0 error（97 tests、18,067 queries）；WorldDepot 8 post-tests/0 failed/0 error（12 tests、112 queries）；主链 target 1 post-test/0 failed/0 error（1,631 queries）。并发/幂等用例的唯一约束冲突日志是其预期竞争测试路径，最终摘要无测试错误。

## 4. 非 PASS 项

| 项目 | 状态 | 说明 |
|---|---|---|
| CC-005 浏览器模拟主链 | Deferred / Not Run | 本 CC 不执行；关闭评审后回到项目 HVR。 |
| 项目负责人真实人工 HVR | Not Run | 由负责人亲自操作并填写；本报告不代填。 |
| 真实 Ginlong/生产/KR Gateway | Deferred / Not Run | 本地 Mock 不是外部联调。 |
| 模板同步 | BLOCKED | 沿用已批准例外，不记 PASS。 |
| 8099 live service 重启/页面验证 | Not Run | 测试命令使用 `--stop-after-init --http-port=0`；既有 PID 20853 仍监听 8099，本次未重启。 |

## 5. 结论

CC-TEST-140～157 自动化与组件集成均 **PASS**；Ginlong 全量及 WorldDepot 受影响回归通过。CC-GIN-012 可提交关闭评审；项目负责人批准前仍为 In Progress/Closure Review Pending。本结论不关闭 CC-GIN-005，也不表示人工 HVR 通过。
