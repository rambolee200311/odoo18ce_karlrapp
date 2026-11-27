# FR-GIN-009 — CC 关闭评估报告

| 字段 | 值 |
|---|---|
| FR | FR-GIN-009 v0.2 |
| CC | [CC-GIN-009 v1.0 Frozen](CC-GIN-009-v1.0.md) |
| 上游冻结基线 | [SRS v1.6](../requirement/SRS_ginlong_apis-v1.6.md)、[TDD v1.9](../ginlong_apis/TDD-v1.9.md)、[Implementation Plan v2.4](IMPLEMENTATION_PLAN_ginlong_apis-v2.4.md) |
| IHR / ATR | [IHR-GIN-009](IHR-GIN-009.md) / [ATR-GIN-009](ATR-GIN-009.md) |
| 数据库 | `odooce_karlrapp`（本地开发） |
| 在线模块版本 | `ginlong_apis 18.0.2.0.44`（Odoo Shell ORM 核实） |
| 当前结论 | **Closure SATISFIED: YES — Closure Review Submitted; Human Review Pending** |
| CC 状态 | **Closure Review Pending；尚未 Closed** |
| 人工 HVR | N/A（CC-GIN-009）；CC 正式关闭并获项目负责人确认后，进入项目级入库 HVR |

> 更正说明（2026-11-25）：本 FR 原始 v0.2 页面描述误记 API02/API04 回传按钮当时已位于 Notebook。后续核实发现按钮仍在标准表头；现已在 `18.0.2.0.45` 移入 Notebook 并用登录浏览器复核。原始自动化测试版本 `.44` 及其测试结果仍按历史记录保留；按钮当前布局证据以 IHR-007、ATR §7 和本文件“补充 UI 入口核验”为准。

## 1. 当前评估

CC-GIN-009 的自动化、Mock HTTP/ORM 组件集成及必要 WorldDepot 回归满足冻结关闭条件。Ginlong 测试为 76 post-tests、0 failed、0 error；WorldDepot 回归为 8 post-tests、0 failed、0 error。CC-TEST-093 的已登录浏览器只读检查现已完成，实际页面显示 Inbound Order 的 Ginlong APIs Notebook、API02/API04 按钮、只读结果区域及关联 Picking 列表。检查没有触发业务操作或回传。

本地 8099 已受控重启；在线进程 PID 84612 返回 HTTP 200，使用数据库 `odooce_karlrapp`。Odoo Shell ORM 核实模块状态为 installed，`installed_version=latest_version=18.0.2.0.44`。在线 Registry 启动日志见 `/private/tmp/ginlong_8099_hr_del_20261124.log`。

基于以上证据，实施方提交本 FR 供 Human Review。**这不是正式关闭记录**：在项目负责人批准前，CC-GIN-009 状态保持 Closure Review Pending。

## 2. 关闭条件矩阵

| 条件 | 结果 | 证据 |
|---|---|---|
| API02 从 `inbound.order.status` 生成状态并写入收货确认业务操作记录；不改 lifecycle state | SATISFIED | ATR-GIN-009 CC-TEST-084–087；Ginlong 最终自动化日志 |
| API04 自动筛选当前订单关联的 Done/Incoming Picking 并读取实际 move line | SATISFIED | ATR-GIN-009 CC-TEST-088/089/091；Mock HTTP 与 ORM 断言 |
| 每 Picking Event、成功跳过、失败人工重试及追加日志 | SATISFIED | ATR-GIN-009 CC-TEST-090/092；本地 Mock 接收记录和 ORM 断言 |
| WorldDepot 必要回归 | SATISFIED | 8 post-tests，0 failed、0 error |
| CC-TEST-093 登录后浏览器页面只读检查 | SATISFIED | [实际浏览器截图](CC-GIN-009-CC-TEST-093.png)；见 IHR-005 |
| 8099 在线 Registry 版本 | SATISFIED | PID 84612；HTTP 200；ORM 显示 `18.0.2.0.44` |
| 独立人工 HVR | N/A（本 CC） | 冻结 CC 与 Human Review 决定；本 CC 不组织 HVR |
| Ginlong 同单多 Picking `CREATE` 协议 | OPEN / NOT RUN | 留待真实外部联调；本地 Mock 不构成 Ginlong 确认 |
| 模板同步 | BLOCKED（批准例外） | 模板来源未提供；沿用已批准流程例外，不记 PASS |

## 3. 测试与证据摘要

- Ginlong 自动化及组件集成：76 post-tests，0 failed、0 error(s)，14,484 queries；日志 `/private/tmp/cc-gin-009-ginlong-20261124-final5.log`。
- WorldDepot 必要回归：8 post-tests，0 failed、0 error(s)，112 queries；日志 `/private/tmp/cc-gin-009-worlddepot-20261124-final2.log`。
- 首轮 final4 中一项测试因对 JSON 空格格式作字符串比较而失败；改为解析 JSON 后断言，final5 全量通过。final4 失败历史保留。
- CC-TEST-093 的浏览器检查为实际登录会话下的只读页面核对；没有触发 API 按钮。截图及操作证据记录于 IHR/ATR。
- 未调用真实 Ginlong，未访问生产或 KR Gateway。未执行项目级人工 HVR。

## 4. 项目级 HVR 交接

完整入库人工 HVR 已合并于 [HVR_Inbound_Business_Guide.md](../ginlong_apis/hvr/HVR_Inbound_Business_Guide.md)，覆盖 API01 创建订单、API02 收货确认及 API04 分批实际入库回传。所有人工场景仍为 `NOT RUN`，不由本 FR 代填结果。

本机 Mock 已准备：API02 `127.0.0.1:18102`；API04 `127.0.0.1:18104`（首次 POST 返回 503，之后成功）。API02/API04 Endpoint 当前临时指向本地 Mock；指南内含 ORM 恢复脚本。Mock 健康检查不等于业务 HVR；尚未创建业务订单或发送业务 Payload。执行 HVR 前须先取得 CC-GIN-009 正式关闭及项目负责人确认。

API04 的真实 Ginlong 同单分批 `CREATE` 语义仍待外部确认。此 Open Item 不影响本地 CC 关闭评估，但不允许将 Mock 结果描述为真实 Ginlong 联调通过。

### 补充 UI 入口核验（2026-11-25）

后续核对发现 `.44` 页面中的 Ginlong 回传按钮仍在订单标准表头。此入口位置已在 `18.0.2.0.45` 修正并通过 8099 登录浏览器复核：入库、出库和盘点订单表头不再显示 Ginlong 回传按钮；API02/API04、API06/API08、API10 分别位于各自“Ginlong 回传数据”Notebook。WMS 表头操作保留。详见 [IHR-007](IHR-GIN-009.md#ihr-007--ginlong-回传按钮入口修正2026-11-25)、[ATR §7](ATR-GIN-009.md#7-回传按钮-notebook-位置修正2026-11-25) 及 [入库](Ginlong_Callback_Buttons_Notebook_20261125.png)、[出库](Ginlong_Callback_Buttons_Outbound_Notebook_20261125.png)、[盘点](Ginlong_Callback_Buttons_Stocktake_Notebook_20261125.png) 截图。本轮未点击按钮、未执行人工 HVR、未运行自动化回归；现有 `.44` 自动化结果仍只代表 `.44`。本补充只更新 UI 位置证据，不构成项目级 HVR 或 Human Review 关闭批准。

## 5. Human Review 请求

请审核 §2 所列关闭证据。批准后由负责人将 CC-GIN-009 正式更新为 Closed；在收到该决定前，不执行项目级人工 HVR。模板同步的已批准流程例外继续保留。

---

## 历史归档：FR-GIN-009 v0.1（保留，不作为当前评估）

以下原始 v0.1 内容完整保留，用于审计历史；其中的 `CC-TEST-093 BLOCKED`、8099 未验证及 `Closure SATISFIED: NO` 是当时状态，已被本 v0.2 新证据取代。

# FR-GIN-009 — CC 关闭评估报告

| 字段 | 值 |
|---|---|
| FR | FR-GIN-009 v0.1 |
| CC | [CC-GIN-009 v1.0 Frozen](CC-GIN-009-v1.0.md) |
| 上游冻结基线 | [SRS v1.6](../requirement/SRS_ginlong_apis-v1.6.md)、[TDD v1.9](../ginlong_apis/TDD-v1.9.md)、[Implementation Plan v2.4](IMPLEMENTATION_PLAN_ginlong_apis-v2.4.md) |
| IHR / ATR | [IHR-GIN-009](IHR-GIN-009.md) / [ATR-GIN-009](ATR-GIN-009.md) |
| 数据库 | odooce_karlrapp（本地开发） |
| 模块版本 | 18.0.2.0.44（Odoo Shell ORM 核实 installed/latest） |
| 结论 | **Closure SATISFIED: NO — Closure Review Pending** |
| 人工 HVR | N/A（本 CC）；关闭后回到原项目 API02/API04 HVR |

## 1. 评估结果

API02/API04 代码实施、Ginlong 自动化、真实本地 HTTP Mock 组件集成及必要 WorldDepot 回归通过：Ginlong 76 post-tests、0 failed/0 error；WorldDepot 8 post-tests、0 failed/0 error。未访问真实 Ginlong、生产或 KR Gateway。

CC-TEST-093 的 Form/View/ORM 自动化部分通过，但登录后的内置浏览器只读页面检查未完成：浏览器会话刷新后到达 Odoo 登录页，未登录、未打开业务单据，也未触发按钮。因此不能将 CC-TEST-093 标为 PASS，CC-009 当前不满足正式关闭条件。

## 2. 关闭条件矩阵

| 条件 | 结果 | 证据 |
|---|---|---|
| API02 读取 inbound.order.status；收货操作写 arrive、不改 lifecycle state | SATISFIED | ATR-GIN-009 CC-TEST-084–087；final5 自动化日志 |
| API04 自动查当前订单 Done/Incoming Picking 并读取实际 move line | SATISFIED | ATR-GIN-009 CC-TEST-088/089/091；Mock HTTP 与 ORM 断言 |
| 每 Picking Event；成功跳过，失败允许人工重试，日志追加 | SATISFIED | ATR-GIN-009 CC-TEST-090/092；final5 真实本机 HTTP receiver 测试 |
| WorldDepot 相关回归 | SATISFIED | final2：8 post-tests、0 fail、0 error |
| Form/View 只读显示字段与按钮 | SATISFIED（自动化部分） | CC-TEST-093 的 View/ORM assertions |
| 登录后浏览器打开订单并检查 UI | NOT SATISFIED / BLOCKED | 浏览器 Session Expired；未完成页面查看 |
| 独立人工 HVR | N/A（本 CC） | Human Review 明确不组织；不得误记 PASS |
| Ginlong 分批 CREATE 真实协议 | OPEN / NOT RUN | CC-GIN-006 真实联调范围；不阻塞本地实现，但不能声称外部通过 |
| 模板同步 | BLOCKED（已批准例外） | 模板源缺失；按既有批准例外，不记 PASS |

## 3. 关闭建议

当前不申请正式关闭，也不将 CC 状态更新为 Closed。补齐 CC-TEST-093 所需的已登录浏览器只读页面检查后，可提交新的 Human Review 关闭决定。该检查不需要触发 API 回传，不属于独立人工 HVR。正式关闭后，再回到原项目 API02/API04 人工 HVR 流程。

## 4. 人工 HVR 与外部联调边界

- CC-GIN-009 不组织独立人工 HVR；未填写或代填任何 HVR PASS。
- CC 关闭后的 API02/API04 人工验收操作指南已更新至 docs/ginlong_apis/hvr/api02 和 docs/ginlong_apis/hvr/api04。
- API04 每 Picking 的本地 Mock 结果不是 Ginlong 对同一订单多次 CREATE 的协议确认。真实请求必须留待另行授权的 CC-GIN-006。
- 8099 持久服务进程未重启，live Registry 版本 NOT VERIFIED；ORM 只读确认安装模块版本为 18.0.2.0.44。
