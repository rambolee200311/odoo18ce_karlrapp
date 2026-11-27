# 自动化测试记录：ATR-GIN-005

## 0. 文档治理

本 ATR 记录 [CC-GIN-005 v1.1 Frozen with Open Items](CC-GIN-005-v1.1.md) 的实施、Odoo 自动化、ORM 核验及本地 Mock 浏览器证据。冻结 SRS v1.1、TDD v1.0、Implementation Plan v1.8、CC-GIN-005 v1.1 均保留，不覆盖历史版本。本 ATR 不授权真实 Ginlong、生产或 KR/Gateway 联调。

## 1. 执行元数据

| 字段 | 值 |
|---|---|
| ATR | ATR-GIN-005 v0.20 |
| IHR | [IHR-GIN-005](IHR-GIN-005.md) |
| HVR | [HVR-GIN-005](../context/report/HVR-GIN-005.md) |
| CC | [CC-GIN-005 v1.1](CC-GIN-005-v1.1.md) |
| Module | `ginlong_apis` `18.0.2.0.39`（Odoo Shell ORM 确认）；`worlddepot` `0.4` |
| Database | 既有 `odooce_karlrapp` |
| Test runner | Odoo 标准 test runner / `TransactionCase`；Odoo Shell ORM；Playwright 浏览器与 localhost Mock |
| 生产/真实外部服务 | NOT ACCESSED |

数据库读取、fixture 建立、模块升级、ORM 验证均通过 Odoo。没有直接 PostgreSQL 访问或 SQL。没有 `stock_barcode`。

## 2. 冻结测试矩阵

| CC-TEST | 内容 | 结果 | 证据和边界 |
|---|---|---|---|
| 044 | 使用既有 Odoo/venv/odoo.conf/DB，模块和迁移状态 | PASS（ORM） | 运行态版本 `ginlong_apis 18.0.2.0.11`、`worlddepot 0.4`；无新环境/数据库 |
| 045 | API01 入库请求映射、货主编码创建/复用和订单不造成库存变化 | PASS（自动化） | Ginlong suite；未将 API01 收单当作实际收货 |
| 046 | API03 出库按 owner + productCode 定位、无效组合拒绝且事务完整 | PASS（自动化） | Ginlong suite；未将 API03 收单当作备货、发货或库存变化 |
| 047 | `productCode` 模板、owner 原生变体、raw/internal code、共享属性、productForm 与 tracking | PASS（迁移 ORM + 自动化 + 浏览器） | 开发库 8 条既有 Ginlong 产品 ID 保持；不同 owner 同码变体；非法枚举/共享属性冲突测试通过；产品 Form 截图 |
| 048 | WorldDepot 产品查找复合键兼容 | PASS（自动化） | Ginlong 与 WorldDepot 回归覆盖 raw code + owner 定位及 legacy lookup |
| 049 | API02/04 入库收货确认与入库完成来源分离、持久化字段、失败重试 | PASS（自动化 + Mock 浏览器） | API02/04 读取保存的入库明细/Picking；API02 Mock 500 后修改、重开、重试；API04 从已完成 move line 回传 |
| 050 | API06 备货与 API08 发货事件及记录来源分离 | PASS（自动化 + Mock 浏览器） | API06 使用选中实际备货行、托盘与重量；API08 使用出库 Order 已保存状态及 Picking；各自单独发送 |
| 051 | API05 客户盘点指令与 API10 实盘结果独立 | PASS（自动化 + Mock 浏览器） | API10 使用现有 `worlddepot` 实盘 result；不访问/调整库存 |
| 052 | API09 `KRWH` owner/product 隔离、实际物理数量及严格只读 | PASS（标准 Picking 自动化） | 标准 receipt Picking 过账生成 A/P001=100、B/P001=300、A/P002=200；owner 隔离、raw code 返回；查询前后 quant 和 move 未改变。既有单元测试另验证 reserved quantity 不扣减 |
| 053 | 五个持久化业务 Form 保存、重开、读取已保存 ORM 数据并手动发送 | PASS（浏览器组件 E2E） | API02 状态、API04 操作人、API06 毛重、API08 状态、API10 Action 分别保存并重开；最终真实角色 ACL 另见 055 |
| 054 | 失败后修正、人工重试、每次尝试日志追加 | PASS（Mock 浏览器 + ORM 日志） | API02 首次 HTTP 500 (`Y`)；保存改为 `N` 并重开；重试成功，日志分别记录失败和成功，历史行未被覆写 |
| 055 | 必要 WMS/UI 回归、真实用户权限和业务数据入口 | PARTIAL | Ginlong 43/43 与 WorldDepot 8/8 自动化通过；浏览器用临时测试 ACL 验证页面/按钮。普通库存用户打开入库 Order 被现有 ACL 拒绝；实际操作组待项目负责人确认，未写入永久授权 |
| 056 | Karl Rapp Gateway/XML | OUT OF SCOPE / NOT RUN | 独立项目；CC-GIN-005 明确不是 Done Gate，不伪称模拟或真实 Gateway 通过 |
| IHR-010 | API01/API05 按 `product.tracking` 执行 SN 清单完整性、产品匹配、数量汇总及同产品重复 SN 检查 | PASS（定向自动化）；人工 HVR NOT RUN | 真实 Odoo HTTP 路由 + ORM 断言；新增 HVR01-21–28 与 HVR05-01–09 待负责人执行 |
| IHR-012 | API01/API05 单件 SN、产品维度身份键、跨托盘/跨产品/跨单据规则及 HVR 报文完善 | PASS（定向 4 post-tests）；完整模块回归 PARTIAL（70 post-tests，1 个历史数据 FAIL） | 真实 HTTP/ORM 自动化；人工 HVR01-29–33、HVR05-10–12 NOT RUN；详情见 RUN-030–032 |
| IHR-015 | 原材料伪 SN 按托盘保存数量、与 details 汇总对账；重建 HVR v2 和授权清理 | PASS（API01/API05 定向 2 post-tests）；v2 人工 HVR NOT RUN | 真实 HTTP/ORM；首轮限流 FAIL 保留于 RUN-036，复验 RUN-037；清理由 ORM 新会话复核 |
| IHR-016 | 将 API01 人工 HVR 收敛为 29–33 五个必测场景，确认现有产品前置并删除无用未执行文件 | PASS（包预检）；初始五项 NOT RUN，后续结果见 IHR-017 | 活动目录 5 JSON + 5 curl；ORM 确认三种产品变体；未执行的 v2 其他报文已删除 |
| IHR-017 | API01 HVR01-31–33：跨托盘重复 SN 拒绝、跨产品相同 SN 放行、跨订单引用已有 SN | **PASS（3/3）** | Odoo Shell ORM：API 日志 3341–3344；失败请求无订单/幂等副作用；订单 1047/1048、幂等 2636/2637 与来源订单 1044 均已核实 |

## 3. 最终运行结果

| Run | 执行 | 结果 | 日志 |
|---|---|---|---|
| ATR-RUN-001 | Ginlong 全量标准 Odoo 测试 | PASS；43 post-tests，0 failed、0 error | `/private/tmp/ccgin005_final_ginlong.log` |
| ATR-RUN-002 | `worlddepot` 受影响回归 | PASS；8 post-tests，0 failed、0 error | `/private/tmp/ccgin005_final_worlddepot.log` |
| ATR-RUN-003 | API09 标准 Picking 定向测试 | PASS；1 test，0 failed、0 error | `/private/tmp/ccgin005_api09_standard_picking.log`；最终全量 RUN-001 亦包含该用例 |
| ATR-RUN-004 | 产品变体迁移 Odoo ORM 核验 | PASS | 既有 8 个 Ginlong 产品迁移且产品 variant IDs 保留；模板共享 `productForm`/tracking、owner variant 编码及 owner 属性行符合基线 |
| ATR-RUN-005 | 五个持久化回传 Form 浏览器 E2E | PASS（临时 ACL） | [HVR-GIN-005](../context/report/HVR-GIN-005.md)，localhost Mock 请求计数 API02×2、API04/06/08/10 各 1；所有 HTTP 均 POST JSON |
| ATR-RUN-006 | Python/XML/工作区检查 | PASS | 7 个 Python 文件 `py_compile`；6 个 Ginlong XML 由 lxml 解析；`git diff --check` |
| ATR-RUN-011 | 两步字段校验器首次 Ginlong 套件运行 | FAIL；2 failed、12 error | `/private/tmp/ginlong_field_validation.log`；旧 API01 测试夹具仍使用 `name`，与 V3.2 必填 `productName` 不符，阻止相关用例及一个并发异常用例进入目标路径；随后只修正夹具并保留本失败记录 |
| ATR-RUN-012 | 两步字段校验器最终 Ginlong 套件及基本验证 | PASS；43 post-tests，0 failed、0 error | `/private/tmp/ginlong_field_validation_final.log`；另通过独立校验器 smoke、Python 编译、JSON 解析、`git diff --check`；Odoo Shell ORM 核验模块版本 `18.0.2.0.12` |
| ATR-RUN-013 | API01 重复 Add 定向自动化及 HTTP/ORM 验收 | PASS；4 post-tests，0 failed、0 error。同报文、变更 Payload、Del 后再次 Add 均返回 IDM02；订单和原成功幂等记录不变，失败响应/日志为三字段和 IDM02 | `/private/tmp/api01_duplicate_add_idempotency_targeted_final.log` |
| ATR-RUN-014 | ginlong_apis 完整自动化回归（升级 .35 后） | FAIL；66 post-tests，1 failed、0 error。唯一失败为既有产品身份测试检查数据库产品 ID 1619 时未找到 Owner 属性行 | `/private/tmp/api01_duplicate_add_idempotency_final.log`；Shell ORM 确认 ID 1619 是既有 HVR01-AUTO 产品记录，未修改 |
| ATR-RUN-015 | Odoo Shell ORM 检查模块和 HVR01-02 历史记录 | PASS（只读）；模块 installed/latest=`18.0.2.0.35`；日志 2056/2057 都是旧 `Y/OK`；幂等 ID 1559 仍是唯一成功 Add 记录 | Odoo Shell ORM 输出；无 SQL/直接 PostgreSQL 操作 |
| ATR-RUN-016 | 人工 HVR01-02 复测及 HVR01-03 不同 Payload 重复 Add | PASS（逐项人工响应 + ORM）；日志 2233/2234 均为 IDM02/error；Order 713 仍唯一、数量 3、备注原值；幂等 ID 1559 仍唯一且 `attempt_count=1`。HVR01-02 首次 FAIL 记录保留 | 项目负责人提供响应；Odoo Shell ORM 只读输出；无 SQL/直接 PostgreSQL 操作 |
| ATR-RUN-017 | 人工 HVR01-04 货主自动建档及订单关联 | PASS；Partner 1143 唯一，Order 756 关联该 Partner；按三级 ORM 关系，其子层产品行关联预置 Variant 1619；成功日志 2238、幂等 ID 1692 为 API01/Add/succeeded | 项目负责人提供响应；Odoo Shell ORM 只读输出；无 SQL/直接 PostgreSQL 操作 |
| ATR-RUN-018 | 人工 HVR01-05 已有货主复用 | PASS；Owner A Partner 1080 数量仍为 1，Order 757 关联 Partner 1080；三级结构子层产品行关联 Owner A Variant 1617；成功日志 2239、幂等 ID 1693 为 API01/Add/succeeded | 项目负责人提供响应；Odoo Shell ORM 只读输出；无 SQL/直接 PostgreSQL 操作 |
| ATR-RUN-019 | 人工 HVR01-06 相同 productCode 跨货主变体隔离 | PASS；同码 Owner A/B Variant 分别为 1617/1618；Order 758 的 owner 为 B，三级结构子层产品行关联 Variant 1618，未误连 A；成功日志 2240、幂等 ID 1694 为 API01/Add/succeeded | 项目负责人提供响应；Odoo Shell ORM 只读输出；无 SQL/直接 PostgreSQL 操作 |
| ATR-RUN-020 | 人工 HVR01-07 quantity=0 与原材料 SN 跟踪 | PASS；Order 759 子层数量为 `0.0`；Owner A Variant 1617 的 `ginlong_product_form=原材料`、`tracking=none`；成功日志 2241、幂等 ID 1695 为 API01/Add/succeeded | 项目负责人提供响应；Odoo Shell ORM 只读输出；无 SQL/直接 PostgreSQL 操作 |
| ATR-RUN-021 | HVR01-07 二次提交：省略 `snList`，并验证相同单号重放拒绝 | PASS（新单场景）；原单号 `IN-ZERO` 重发返回 IDM02（日志 2242）；新单号 `IN-ZERO1` 返回 success（日志 2243），Order 760 数量 `0.0`、SN 数 0、`ginlong_sn_list_json=[]`，Owner A 产品 `tracking=none`；幂等 ID 1696 succeeded。HVR01-08 独立 quantity=3 用例仍 NOT RUN | 项目负责人提供响应/报文；Odoo Shell ORM 只读输出；无 SQL/直接 PostgreSQL 操作 |
| ATR-RUN-022 | 人工 HVR01-08 quantity=3、省略 `snList` | PASS；Order 761 的子层产品 Variant 1617 数量 3，SN 数 0；日志 ID 2244 的 request_data 确认无 `snList`，响应成功；幂等 ID 1697 为 API01/Add/succeeded | 项目负责人提供响应；Odoo Shell ORM 只读输出；无 SQL/直接 PostgreSQL 操作 |
| ATR-RUN-023 | 人工 HVR01-09 一次汇总多个缺失必填字段 | PASS；响应 `REQ01: 缺失字段: owner, businessType`；日志 ID 2245 的 `exception_details` 同时包含两个字段；无对应订单或幂等记录 | 项目负责人提供响应；Odoo Shell ORM 只读输出；无 SQL/直接 PostgreSQL 操作 |
| ATR-RUN-024 | API01/API05 SN 一致性首轮定向 HTTP/ORM 测试 | FAIL；2 个用例的日志断言将用户短消息错误地查在 `exception_details`，实际共享日志把短消息存入 `msg`、详细诊断存入 `exception_details`；业务 HTTP 断言此前均已到达 | `/private/tmp/ginlong_sn_consistency_targeted.log`；修正测试断言字段，不改业务规则 |
| ATR-RUN-025 | API01 业务类回归 + API01/API05 SN HTTP 用例 | FAIL；58 post-tests，57 通过、1 失败。唯一失败为既有产品身份测试的数据库 product ID 1619 缺 Owner 属性行；与本次 SN 代码无关，保留失败且不修饰既有产品数据 | `/private/tmp/ginlong_sn_consistency_regression.log`；该历史问题也见 ATR-RUN-014 |
| ATR-RUN-026 | API01/API05 SN 一致性最终定向 HTTP/ORM 自动化，含部分 SN 与错误摘要截断 | PASS；2 post-tests，0 failed、0 error。真实 POST、正反用例、ORM 无副作用、API 日志和幂等状态均断言 | `/private/tmp/ginlong_sn_consistency_targeted_final.log` |
| ATR-RUN-027 | Ginlong 模块升级版本 ORM 核验 | PASS；`ginlong_apis` state=`installed`，`latest_version=installed_version=18.0.2.0.36` | Odoo Shell ORM；使用既有 `odoo.conf`/数据库，没有 SQL |
| ATR-RUN-028 | API01/API05 SN 一致性定向复验；API01 不完整 SN 字段路径断言及 HVR shell 语法修正 | PASS；2 post-tests，0 failed、0 error。实际 HTTP + ORM 覆盖保留；所有新增 API01/API05 curl 脚本通过 `bash -n`，JSON/manifest 解析通过 | `/private/tmp/ginlong_sn_consistency_targeted_final2.log`；`git diff --check` 仅发现既有 WorldDepot 改动中的 CRLF 行尾空白，Ginlong 本次文件通过定向检查 |
| ATR-RUN-029 | 重启 8099 并准备 API01/API05 人工 HVR 前置产品 | PASS；旧 PID 9358 停止，新 Odoo PID 14462 从项目工作目录启动并监听 8099；`/web/login` 返回 200；Odoo Shell ORM 核实模块 installed/latest 与 manifest 均为 `18.0.2.0.36`。两条本地 API07 setup 均返回 `Y/OK`；ORM 产品 Variant 1754（成品/serial）、1755（半成品/serial），日志 2352/2353、幂等 1811/1812 succeeded。未执行 API01/API05 验收请求，人工 HVR 仍 NOT RUN | Odoo Shell ORM、`lsof`/本地 HTTP、`debug_logs/odoo_181.log`；无 SQL、无真实外部请求 |
| ATR-RUN-030 | API01/API05 SN 身份与数量规则定向 HTTP/ORM 测试 | PASS；4 post-tests，0 failed、0 error。API01/API05 tracking 规则测试、请求内 `(productCode, productSN)` 判重、不同产品同 SN、跨 API01 订单引用、API05 已存在/未入库引用均通过 | `/private/tmp/ginlong_api01_api05_sn_identity_r2.log`；实际调用 Odoo HTTP 测试入口并核对 ORM 结果 |
| ATR-RUN-031 | ginlong_apis 全量回归首次运行 | FAIL；70 post-tests，1 failed、1 error。API05 旧 fixture 使用单条 SN quantity=2，与单件规则冲突；既有产品 ID 1619 Owner 属性行缺失 | `/private/tmp/ginlong_apis_full_sn_identity_r2_regression.log`；fixture 随后改为两条 quantity=1，历史失败保留 |
| ATR-RUN-032 | 修正 fixture 后的 ginlong_apis 全量回归 | PARTIAL；70 post-tests，1 failed、0 error。唯一失败是既有数据库产品 ID 1619 缺 Owner 属性行；ORM 确认记录存在但属性行数为 0，未改业务数据或放宽断言 | `/private/tmp/ginlong_apis_full_sn_identity_r2_regression_final.log`；Odoo Shell ORM 只读核验模块 .37 及产品 1619 状态 |
| ATR-RUN-033 | HVR JSON、manifest、curl shell 语法及丰富报文组合检查 | PASS；API01/API05 清单及全部 HVR JSON 可解析，curl 通过 `bash -n`；HVR01-29 为 3 产品、3 托盘、9 个不同 SN，逐条 quantity=1，产品明细汇总为 5/4/4 | 本地静态预检命令；未发送任何人工 HVR HTTP 请求 |
| ATR-RUN-034 | 修正并复验新增 API01/API05 HVR curl payload 路径 | PASS；修正 8 个重复 `.json` 后缀；API01 38 项、API05 12 项 manifest 引用均存在，全部 JSON 解析通过，所有 curl 脚本通过 `bash -n`；HVR01-29 的三产品/三托盘/九个单件 SN 分布及序列号产品数量汇总断言通过 | 本地静态验证；未发送任何人工 HVR HTTP 请求 |
| ATR-RUN-035 | 诊断 API01-R1 的 Y/OK 响应并恢复 8099 运行代码 | PARTIAL；ORM 证明产品 ID 1617 是原材料、`tracking=none`；订单 842、成功 API 日志 2610 和幂等记录 2016 与用户响应吻合。该响应来自早于 `.37` 源码修改的旧进程 PID 14462，不能作为当前基线验收。已重启为 PID 22584，启动晚于源码修改，`GET /web/login` 为 HTTP 200；未由 Codex 重发 API01 HVR | ORM 只读查询、进程启动时间与文件修改时间、localhost GET；保留旧请求数据，无删除/SQL/真实 Ginlong 请求 |
| ATR-RUN-036 | API01/API05 三托盘混合 SN/原材料数量行首次定向测试 | FAIL；2 个测试中 1 项因连续 HTTP 请求触发既有固定窗口限流而收到 429；保留失败证据，未修改限流实现或阈值 | `/private/tmp/ginlong_api01_api05_pallet_split_20261123.log` |
| ATR-RUN-037 | 降低定向测试请求速率后的 API01/API05 三托盘混合场景复验 | PASS；2 个真实 HTTP/ORM post-tests，0 failed、0 error。逐产品汇总原材料/成品/半成品为 9/6/6；核对 3 个托盘各自数量及 15 行记录持久化 | `/private/tmp/ginlong_api01_api05_pallet_split_final_20261123.log`；请求节奏辅助改动仅服务测试，不改变限流业务规则 |
| ATR-RUN-038 | API01 HVR v3 执行包预检 | PASS（包完整性检查）；仅检查 5 个 JSON/curl、5 项 manifest 和 HVR01-29 逐托盘/逐产品数量；未发送 HTTP | `python3 docs/ginlong_apis/hvr/api01/test_data/generate_payloads.py` 后进行 JSON/manifest 及 `bash -n` 检查；Odoo Shell ORM 确认 3 个 Owner A 产品变体存在，随后删除未执行且不需要的 v2 其他报文 |
| ATR-RUN-039 | API01 HVR01-31–33 人工结果 ORM 核验 | **PASS（3/3）** | 只读 ORM 核对日志 3341–3344、订单 1047/1048、幂等 2636/2637；HVR01-31 无订单/幂等记录，HVR01-32 跨产品同 SN 成功，HVR01-33 跨单据复用成功且重复 Add 被 IDM02 拒绝 |

### 自动化运行命令

```sh
./venv/bin/python odoo-bin -c odoo.conf -d odooce_karlrapp --test-enable --test-tags /ginlong_apis --stop-after-init --http-port=0 --gevent-port=0 --log-level=info --log-handler=odoo.tests:INFO --logfile=/private/tmp/ccgin005_final_ginlong.log
```

```sh
./venv/bin/python odoo-bin -c odoo.conf -d odooce_karlrapp --test-enable --test-tags /worlddepot --stop-after-init --http-port=0 --gevent-port=0 --log-level=info --log-handler=odoo.tests:INFO --logfile=/private/tmp/ccgin005_final_worlddepot.log
```

## 4. 失败/部分记录（保留）

| Run | 实际情况 | 后续处理 |
|---|---|---|
| ATR-RUN-007 | API09 新标准 Picking 用例首次运行在 API07 创建第二个同码 owner 变体时，因为测试 fixture 给同一共享模板使用不同名称而拒绝；0 failed、1 error | 只修正测试数据，使同码模板名称一致；定向复测 RUN-003 PASS，全量 Ginlong RUN-001 PASS。未放宽共享产品一致性规则 |
| ATR-RUN-008 | 首次以仅 stock user/manager 的浏览器账号打开入库单，Odoo ACL 拒绝 | 查实现有自定义 Order 无普通库存用户 ACL；后续仅给临时浏览器用户建立临时 ACL 供 UI 组件 E2E，完成后移除；最终用户权限仍 PARTIAL |
| ATR-RUN-009 | API04 浏览器字段首次保存后重新打开未保持新操作人值，因为列表编辑自动化在保存前没有 blur/commit 行编辑 | 自动化改为 Tab blur 后显式点击 Form Save；最终 HVR 操作人改值可重开读取，API04 payload 读取新值 |
| ATR-RUN-010 | XML-RPC 模块升级提议因无已知应用管理员凭据，尝试临时授予 browser user `base.group_system` 被 auto-review 拒绝；该操作未执行 | 保留拒绝；不绕过、不以 shell 或其他路径变相提权。运行时模块代码已在已安装版本基线上；本轮新增的只是测试代码和报告 |
| ATR-RUN-011 | 字段校验器首次全套运行未通过；旧 API01 测试夹具用 `name` 代替必填 `productName`，共 2 failed、12 error | 将夹具改为协议字段 `productName`，同时保留 O 列前置校验；最终结果单独记录于 RUN-012 |
| ATR-RUN-014 | 完整套件中仍有 1 个产品身份测试失败；记录 ID 1619 的现存 HVR01-AUTO 变体没有对应模板 Owner 属性行 | 不属于 API01 重复 Add 修复；保留 FAIL 证据，不改测试预期、不修改产品数据，另行评估该历史产品数据问题 |

并发幂等测试日志中可见 PostgreSQL 唯一约束冲突，这是测试刻意制造的多 Worker/并发路径；Odoo 标准套件最终摘要 0 failed / 0 error，不作为运行失败。

## 5. ORM / Mock 证据

- API09 标准 Picking test 建立所有库存的唯一路径为 `stock.picking` + `stock.move`/`stock.move.line` 的原生确认与过账；专用用例没有 `stock.quant.create()` 或 quant 写入。API09 调用前后快照对比 quant `quantity`、`reserved_quantity`、`write_date` 和相关 `stock.move` 数相同。
- 浏览器 Mock 最终请求顺序：API02 `{receiptConfirmed:Y}` → HTTP 500；API02 `{receiptConfirmed:N}` → HTTP 200；API04 `{action:CREATE, snList.operator:KR-OP-BROWSER}`；API06 `{action:CREATE, totalWeight:"3.25"}`；API08 `{action:CREATE, shipmentConfirmed:N}`；API10 `{action:Del}`。Mock 只监听 `127.0.0.1:18220`。
- 最终 run 的 source-linked log IDs：入库 order 623/624 为 API02 fail/retry，625 为 API04；出库 order 626 为 API06、627 为 API08；stocktake order 628 为 API10。日志 payload、响应、错误均由 Odoo Shell ORM 检查；没有直接 SQL。
- HVR 使用的临时 WMS ACL 只挂在临时浏览器用户组，不是项目永久 ACL。真实普通库存用户访问不通过，故 CC-TEST-055 不得标 PASS。
- E2E 收尾后以新的 Odoo Shell ORM 会话核验：临时 ACL 820–838 均已删除，临时组 65 已移除，五个 localhost Endpoint 配置均不存在。临时账号 30 已停用并保留，以维持历史 API 日志操作者关联；没有给真实 WMS 用户组增加权限。

## 6. 全部范围与移交

- API01–API10 本地映射/回传有自动化证据；API09 有标准 Picking 生成库存的组件证据，API02/04/06/08/10 有 localhost Mock 浏览器证据。
- CC-TEST-053/054 的 Form 数据流程在临时测试权限下已验证；真实业务用户权限未通过/未确认，CC-TEST-055 PARTIAL。不得据此建议 CC-GIN-005 已具备关闭条件。
- Arrival Date 是现有入库 Form 的 required 字段，但 V3.2 API01 header 未提供。浏览器 fixture 设置了该现有字段后才能保存 Order Form；没有猜测 Ginlong 值或增加默认规则。
- 模板同步仍 BLOCKED，保留批准的流程例外。
- 完整用户权限决策/人工验收移交本 CC 评审；真实 Ginlong 外部联调交 CC-GIN-006；KR Gateway/XML 另立阶段；以上都未测试。
- 本轮模板同步检查脚本因仓库内未找到项目模板来源而返回 BLOCKED；沿用既有批准的模板同步流程例外，没有将其记为 PASS。

## ATR 版本记录

| 版本 | 日期 | 说明 | 状态 |
|---|---|---|---|
| v0.1 | 2026-11-19 | 首次记录 CC-GIN-005 实施和当前 Odoo/Mock 运行证据；保留缺陷、权限差距及 BLOCKED/NOT RUN 边界 | In Progress |
| v0.2 | 2026-11-19 | 追加 Ginlong 必填/类型校验器实施、首轮失败及最终 43 项回归证据；保留既有历史运行记录和模板同步 BLOCKED | In Progress |
| v0.3 | 2026-11-22 | 追加 API01 重复 Add IDM02 定向验收、完整测试中的现存产品数据失败及 HVR01-02 人工失败记录 | In Progress |
| v0.4 | 2026-11-22 | 追加 HVR01-02 `.35` 复测及 HVR01-03 不同 Payload 重复 Add 的人工与 ORM PASS 证据；保留首次失败和完整回归失败记录 | In Progress |
| v0.5 | 2026-11-22 | 追加 HVR01-04 货主自动建档成功与订单关联 ORM 证据，并保留产品行映射待 HVR01-06 核验的发现 | In Progress |
| v0.6 | 2026-11-22 | 追加 HVR01-05 已存在货主复用及订单关联 ORM 证据；保留 HVR01-06 产品行映射核验项 | In Progress |
| v0.7 | 2026-11-22 | 追加 HVR01-06 同码跨货主变体隔离 PASS；复核 Odoo 入库三级结构并更正 HVR01-04/05/06 子层产品关联结论 | In Progress |
| v0.8 | 2026-11-22 | 追加 HVR01-07 quantity=0 / 原材料非 SN 管理人工 PASS 及 ORM 证据 | In Progress |
| v0.9 | 2026-11-22 | 追加 HVR01-07 第二次无 `snList` 新单验证、同号重复 Add 拒绝及 ORM 证据；独立 HVR01-08 保持 NOT RUN | In Progress |
| v0.10 | 2026-11-22 | 追加 HVR01-08 独立 quantity=3、省略 `snList` 人工 PASS 及 ORM、日志、幂等证据 | In Progress |
| v0.11 | 2026-11-22 | 追加 HVR01-09 多必填字段汇总错误与失败无副作用的人工/ORM PASS 证据 | In Progress |
| v0.12 | 2026-11-22 | 追加 IHR-010 API01/API05 SN 一致性实现与定向自动化记录；保留首轮日志断言失败、既有产品 ID 1619 回归失败以及新增人工 HVR NOT RUN 状态 | In Progress |
| v0.13 | 2026-11-22 | 补充 API01 不完整 SN 字段路径自动化断言、HVR curl 脚本预检及 ATR-RUN-028 结果 | In Progress |
| v0.14 | 2026-11-22 | 重启并核实当时 8099 服务加载工作区 `.36` 代码、数据库模块版本及 HVR 前置数据状态；人工请求仍 NOT RUN | In Progress |
| v0.15 | 2026-11-22 | 追加 API01/API05 SN 身份规则定向自动化、修正旧 API05 fixture、完整回归残余产品数据失败及 3 产品/3 托盘/9 SN 的 HVR 报文预检；人工 HVR 保持 NOT RUN | In Progress |
| v0.16 | 2026-11-22 | 修复 8 个新增 API01/API05 curl 脚本的 payload 文件名，并通过全量 manifest/JSON/curl 静态复验；人工 HVR 保持 NOT RUN | In Progress |
| v0.17 | 2026-11-23 | 记录 API01-R1 的产品 tracking、订单/日志/幂等 ORM 证据及 8099 旧进程代码滞后根因；重启后加载 `.37`，人工复验仍待用户执行 | In Progress |
| v0.18 | 2026-11-23 | 追加 API01/API05 原材料托盘数量行规则和定向自动化证据，保留首轮限流失败；登记人工 HVR v2 仍 NOT RUN 及已授权 ORM 清理的独立证据 | In Progress |
| v0.19 | 2026-11-23 | 更新 API01 HVR 为仅需人工执行 29–33 五例；核实产品前置已具备，删除未执行且多余的活动报文；没有执行人工 API 请求 | In Progress |
| v0.20 | 2026-11-24 | 追加 API01 HVR01-31–33 的日志与 ORM 核验证据，三项人工验收均 PASS；保留其他 API 与 CC-005 未决事项 | In Progress |
