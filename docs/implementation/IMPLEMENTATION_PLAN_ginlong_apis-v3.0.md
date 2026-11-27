# Ginlong API 实施计划 v3.0 — CC-GIN-005 最终业务主链模拟验收

| 项目 | 内容 |
|---|---|
| 版本 | v3.0（基线对齐及最终模拟 HVR 执行计划） |
| 日期 | 2026-11-27 |
| 状态 | 经项目负责人授权的连续对齐与 CC-GIN-005 最终模拟 HVR 执行状态；不新增 CC |
| 前一计划 | [Implementation Plan v2.9](IMPLEMENTATION_PLAN_ginlong_apis-v2.9.md)；历史版本保留 |
| CC-GIN-012 | [v1.0 Closed](CC-GIN-012-v1.0.md)；Closure SATISFIED；Human Review APPROVED |
| CC-GIN-005 | v1.1 Frozen；当前执行解释见 [同一 CC 执行对齐补充](CC-GIN-005-Execution-Alignment-20261127.md)；项目级模拟 HVR 进行中 |

## 1. 执行状态

| 阶段 | 范围 | 状态 | 后续动作 |
|---|---|---|---|
| 阶段 4F / CC-GIN-012 | API01–API10 连续本地业务主链自动化、库存断言、组件集成及必要缺陷修复 | **Closed；Closure SATISFIED** | 不重复已通过的自动化；真实 Ginlong/KR 集成仍按后续 CC 门禁。 |
| 阶段 4 / CC-GIN-005 | 本地浏览器 UI/WMS E2E 及项目级人工 HVR | **In Progress** | Codex 内置浏览器模拟完整业务主链；更新人工指南；随后由项目负责人执行真实人工 HVR。 |
| 阶段 5 / CC-GIN-006 | 真实 Ginlong 环境联调 | **Deferred** | 按原授权门禁另行安排，不属于本轮。 |

## 2. CC-GIN-012 关闭依据

- CC-TEST-140～157 自动化/组件集成结果及早期失败记录见 [ATR-GIN-012](ATR-GIN-012.md)。
- 实施记录见 [IHR-GIN-012](IHR-GIN-012.md)；正式关闭决定见 [FR-GIN-012 v1.0](FR-GIN-012.md)。
- Human Review 于 2026-11-25 批准 Closure SATISFIED；CC-GIN-012 已正式 Closed。
- 模板同步 `BLOCKED` 继续沿用已批准例外，不伪记 PASS；自动化结果不替代 CC-GIN-005 人工 HVR。

## 3. CC-GIN-005 本轮执行边界

按 CC-GIN-005 v1.1 和 [项目级业务流程 HVR 指南](../ginlong_apis/hvr/HVR_Project_Business_Flow_Guide.md) 使用同一 owner、warehouse、productCode、SN 与实际托盘串联十个 API。API01/03/05/07/09 使用真实本地 HTTP 入口；API02/04/06/08/10 使用真实 Odoo 单据按钮和本地 Mock。实际入库、备货、出库及盘点均经 Odoo 浏览器界面操作，不使用 ORM、Shell、直接业务方法或库存调整代替。每项操作保存实际页面、业务记录、API Event/Log、Mock 请求和库存证据；不访问真实 Ginlong或生产。

模拟浏览器验证全部完成后，再修订 HVR 操作指南并准备与模拟数据完全隔离的新一组负责人真实 HVR 数据。Codex 不代填真实人工 HVR 的 PASS/FAIL。

## 4. 2026-11-27 CC-GIN-005 同一范围执行状态与基线对齐

- 当前 SRS：[`SRS v2.1`](../requirement/SRS_ginlong_apis-v2.1.md)；当前 TDD：[`TDD v2.4`](../ginlong_apis/TDD-v2.4.md)。两者继承 v2.0/v2.3 已批准内容，并补齐十个 API 的权威事实来源、UI/HTTP 触发及库存不变量。
- 当前 CC-GIN-005 执行解释：[`同一 CC 执行对齐补充`](CC-GIN-005-Execution-Alignment-20261127.md)。这是对已批准 CC 的增补，不另开 CC、不改变冻结范围。
- 本轮候选服务由 Odoo ORM 确认为数据库 `odooce_karlrapp`、`ginlong_apis` installed/latest `18.0.2.0.56`；仓库 Manifest 同版本。8099 本地服务返回 `/web/login` HTTP 200。
- 全量自动化既有证据：96 post-tests、100 test methods、0 failed / 0 error，日志 `/private/tmp/ginlong_full_regression_20261127_v056.log`。不因本次纯基线对齐重跑未受影响代码。
- 业务主链只用 KRWH `one_step` inbound、`ship_only` outbound；唯一 Receipts Picking 增库存，唯一 Delivery Orders Picking 扣库存；API06 读该出库实绩，API08 只转订单状态并送三字段，不产生第二次库存移动。
- 模拟 HVR 使用唯一 Run Manifest、零冲突新业务键、冻结 Endpoint/权限和严格本地 Mock，在内置浏览器连续执行一条 API01–10 主链。真实负责人 HVR 与真实 Ginlong/KR 集成仍独立判定。
- 模板同步继续沿用已批准 `BLOCKED` 例外，不标 PASS。

| Gate | 当前事实 | 状态 |
|---|---|---|
| 基线与代码 | SRS v2.1 / TDD v2.4 / CC 补充、安装代码 `.56` 对齐 | PASS |
| 全量自动化 | `.56` 全量运行 96 post-tests、100 methods，0 fail/error | PASS |
| 本地环境 | 8099 HTTP 200；API02/04/06/08/10 Mock health OK | PASS |
| 角色与页面 | 专用 HVR operator 登录；WorldDepot 页面已读取 | PASS |
| 新数据冲突 | API01/03 reference、API05 count_order_no、API07 owner+productCode 经 ORM 检查均为 0；库存 SKU 为零历史 | PASS |
| 正式模拟 HVR | 单一新订单的 10 API 连续业务主链 | IN PROGRESS；Run `CC005-FINAL-20261127-01` |
