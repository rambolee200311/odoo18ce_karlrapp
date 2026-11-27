# ATR-GIN-009 — 验收测试记录

依据 [CC-GIN-009 v1.0 Frozen](CC-GIN-009-v1.0.md) 与当前冻结上游 SRS v1.6、TDD v1.9、Implementation Plan v2.4。

## 1. 测试环境

| 项目 | 实际值 |
|---|---|
| Odoo 数据库 | odooce_karlrapp |
| Python 环境 | 仓库现有 venv |
| Odoo 配置 | 仓库现有 odoo.conf |
| Ginlong 模块 | ORM 核实 installed/latest_version 18.0.2.0.44 |
| Ginlong 测试日志 | /private/tmp/cc-gin-009-ginlong-20261124-final5.log |
| WorldDepot 回归日志 | /private/tmp/cc-gin-009-worlddepot-20261124-final2.log |
| 外部网络 | 仅本地 Mock；未访问真实 Ginlong/生产/KR Gateway |

## 2. 验收矩阵

| 测试 | 状态 | 断言与证据 |
|---|---|---|
| CC-TEST-084 API02 映射及 lifecycle state | PASS | Ginlong suite：planning→N、arrive/inbound→Y；收货操作只改变业务 status，state 不变 |
| CC-TEST-085 API02 订单状态回传 | PASS | 从真实业务按钮发送本地 HTTP POST；不依赖 Picking、move line、旧收货明细；核对请求、响应及日志 |
| CC-TEST-086 收货确认操作日志 | PASS | 操作将 status 写为 arrive；现有 Chatter/字段跟踪保留变更，state 保持原值 |
| CC-TEST-087 API02 Event 与重复操作 | PASS | 状态映射、已保存业务状态读取及现有成功事件规则通过自动化断言 |
| CC-TEST-088 API04 Picking 筛选 | PASS | 当前订单 Done/Incoming 进入处理；当前订单非 Done、其他订单 Done/Incoming、Outgoing Picking 被排除 |
| CC-TEST-089 API04 实际数据来源 | PASS | 本地 Mock HTTP 断言产品、Lot/SN、数量和托盘来自 move line；operator 是 Picking 实际确认人；时间取 date_done |
| CC-TEST-090 API04 每 Picking Event/跳过/重试 | PASS | 两张 Picking 分别 POST；重复点击成功批次不重发；失败事件保留并可手动重试 |
| CC-TEST-091 不合格 Picking/无作业 | PASS | 非合格 Picking 不发送；无合格 Picking 时没有 HTTP 请求并追加失败 API Log，库存/状态无副作用 |
| CC-TEST-092 失败后重试和历史日志 | PASS | Mock 首次返回 503、用户再次点击后返回成功；两次 POST、旧日志不变、新日志追加、事件身份稳定 |
| CC-TEST-093 页面只读结果核对 | **PASS（补充运行）** | 登录后的 Codex in-app browser 实际打开既有 Inbound Order Ginlong APIs Notebook；可见 API02/API04 按钮、只读反馈区域及关联 Picking 列表。未触发业务或回传动作。截图：[CC-GIN-009-CC-TEST-093.png](CC-GIN-009-CC-TEST-093.png) |
| CC-TEST-094 历史及共享字段回归 | PASS | API02 旧明细模型与历史行保留但不再展示/读取；API06 所需共享字段和功能回归通过 Ginlong suite |
| Ginlong 全量回归 | PASS | 76 post-tests，0 failed，0 error(s)，14,484 queries；最终日志 final5 |
| WorldDepot 必要回归 | PASS | 8 post-tests，0 failed，0 error(s)，112 queries；最终日志 final2 |
| 独立人工 HVR | N/A（本 CC） | Human Review 明确本 CC 不组织独立 HVR；未标记 PASS，CC 关闭后回到原项目 API02/API04 HVR |
| 真实 Ginlong 分批协议 | OPEN / NOT RUN | 同订单多 Picking 分别 CREATE 留真实联调确认；不影响本地 Mock 验收 |
| 8099 live Registry | **PASS（重启后核验）** | 受控重启后 HTTP 200；Odoo Shell ORM 核实 `ginlong_apis` installed/latest 均为 `18.0.2.0.44`，新进程启动日志记录 `odooce_karlrapp` Registry loaded |
| 模板同步 | BLOCKED（批准例外） | 模板源未提供；沿用批准流程例外，不伪记 PASS |

## 3. 执行记录及历史失败

- 最终 Ginlong 命令：

~~~bash
./venv/bin/python odoo-bin -c odoo.conf -d odooce_karlrapp -u worlddepot,ginlong_apis --test-enable --test-tags /ginlong_apis --stop-after-init --http-port=0 --gevent-port=0 --log-level=info --log-handler=odoo.tests:INFO --logfile=/private/tmp/cc-gin-009-ginlong-20261124-final5.log
~~~

- WorldDepot 回归命令：

~~~bash
./venv/bin/python odoo-bin -c odoo.conf -d odooce_karlrapp -u worlddepot --test-enable --test-tags /worlddepot --stop-after-init --http-port=0 --gevent-port=0 --log-level=info --log-handler=odoo.tests:INFO --logfile=/private/tmp/cc-gin-009-worlddepot-20261124-final2.log
~~~

- final4 Ginlong 首轮真实 HTTP 组件测试有 1 项测试断言失败：测试按无空格字符串匹配 API response，但现有 API Log 存的是有空格的合法 JSON；修正测试为 JSON 解析断言后，final5 全量为 0 fail/0 error。final4 记录保留，没有隐藏。
- 沙箱内直接连接现有 PostgreSQL 端口曾被隔离策略拒绝；随后在授权的 Odoo 测试运行器/ORM 下使用同一配置和数据库完成最终运行。没有使用 psql、psycopg2 直连或直接 SQL。

## 4. 总体结果

代码、自动化/组件集成验收、CC-TEST-093 登录后只读页面检查及 `.44` 在线 Registry 核对均通过。人工 HVR仍未开始，且本 CC 不要求独立人工 HVR。真实 Ginlong API04 分批协议仍为 OPEN；模板同步 BLOCKED 继续沿用已批准例外。FR-GIN-009 v0.2 将关闭条件评为 SATISFIED 并提交 Human Review；在 Human Review 批准前，CC 不标记为 Closed。

## 5. 补充运行历史（2026-11-24）

此前 ATR/IHR 记录的 CC-TEST-093 `PARTIAL / BLOCKED` 和 8099 `NOT VERIFIED` 保留为历史，不覆盖。新的浏览器截图与 ORM/HTTP 证据见 IHR-GIN-009 IHR-005；当前状态以本节及验收矩阵的补充运行结果为准。

## 6. HVR 环境准备核验（2026-11-24；不属于人工业务验收）

| 检查项 | 结果 | 证据 |
|---|---|---|
| 测试订单状态 | READY / NOT CREATED | 通过 `world.depot.inbound.order` ORM 搜索参考号 `HVR-GIN009-IN-20261124-01`，未找到记录；API01 报文已准备但未发送 |
| 主数据前置 | READY | ORM 找到指定 owner 编码及唯一匹配的 SN 产品变体 |
| API02/API04 Endpoint | READY — LOCAL MOCK | ORM 值分别指向 `127.0.0.1:18102` 和 `127.0.0.1:18104` |
| Mock 健康状态 | PASS（仅环境检查） | 2026-11-24 对两个 `__mock__/health` 执行 GET，均 HTTP 200；该项不是业务 HVR |
| 捕获记录 | EMPTY / NO BUSINESS REQUESTS | API02/API04 `received.jsonl` 均尚无本轮业务记录；没有手工构造或发送 API02/API04 Payload |
| 人工场景 | NOT RUN | HVR-IN-01–06 全部留空，由项目负责人执行后判定；须等待 CC-GIN-009 正式关闭和开始授权 |

预检仅覆盖 JSON、Shell、Python 助手脚本语法和本地 Mock 存活；没有运行完整人工业务流程、没有写入测试订单/库存、没有访问真实 Ginlong 或生产。

## 7. 回传按钮 Notebook 位置修正（2026-11-25）

| 检查项 | 结果 | 证据 |
|---|---|---|
| 清除订单标准表头中的 Ginlong 回传入口 | PASS | 浏览器实际检查入库单、出库单和客户盘点订单，三个表头均无 API02/API04/API06/API08/API10 回传按钮；原 WMS 操作保留 |
| 所有 Ginlong 回传按钮位于专用 Notebook | PASS | 入库页显示 API02/API04，出库页显示 API06/API08，盘点页显示 API10；页面证据见 [IHR-007 截图](Ginlong_Callback_Buttons_Notebook_20261125.png)、[出库](Ginlong_Callback_Buttons_Outbound_Notebook_20261125.png)、[盘点](Ginlong_Callback_Buttons_Stocktake_Notebook_20261125.png) |
| 8099 在线模块升级 | PASS | 新进程 PID `89829`；现有数据库 `odooce_karlrapp`；Odoo Apps 升级请求 HTTP 200；启动日志显示 `ginlong_apis` 加载，Registry loaded。当前代码 Manifest 为 `18.0.2.0.45` |
| 回传业务行为 / 人工 HVR | NOT RUN | 没有点击回传按钮、没有发送回传请求；此轮只验证界面入口位置，不替代人工 HVR |
| 自动化回归 | NOT RUN | 本轮只涉及 Form View XML 与入口位置；未执行自动化套件 |

历史测试在 `.44` 版本运行的结果继续保留；本节只记录 `.45` 的 UI 入口修正和现场页面证据，不把旧回归结果描述为 `.45` 的重新运行结果。

本节同时更正 §2 中 CC-TEST-093 对 `.44` 按钮位置的旧描述；旧描述不作为当前 Notebook 按钮位置的证据。浏览器分别检查了入库单 `IO202611190301`、出库单 `OO202611190186`、盘点订单 `HVR-GIN005-COUNT-001`；没有触发任何回传。
