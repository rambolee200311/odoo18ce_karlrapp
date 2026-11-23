# CC-GIN-007 人工执行记录 v0.1 Draft

**人工 HVR 当前状态：HVR-API01-01–06 PASS（预期拒绝及失败尝试均保留）；HVR-API01-07 为补充 API04 出站核对，NOT RUN，不阻塞 CC-GIN-007 关闭。** 下方 Codex 本地模拟结果单独记录，不替代人工 HVR。

## 环境记录

| 项目 | 实际记录 |
|---|---|
| 执行日期/时区 | HVR-API01-01：10:04:52 / 11:01:26；HVR-API01-02：11:07:06 / 11:07:30；HVR-API01-03：11:09:03；HVR-API01-04：11:12:54；HVR-API01-05：11:14:39；HVR-API01-06：11:16:03（API 日志时间；时区未另行确认） |
| 执行人 | 项目负责人提供的人工 HVR 响应；姓名未记录 |
| Odoo 数据库 | 执行时核实既有 odooce_karlrapp |
| 活动服务加载版本 | 复测前重启本地 8099；Odoo ORM 核实数据库模块 `ginlong_apis` installed_version=`18.0.2.0.40`。API 日志未记录请求端口，未将该版本断言为请求进程内版本 |
| API01 本地 URL | NOT RUN（人工 HVR）；Codex 模拟请求使用 `http://127.0.0.1:8089` |
| API User 名称（不记录 Token） | NOT RUN |
| API04 Mock URL（如执行） | NOT RUN |
| 证据目录 | 人工 HVR-API01-01–06：响应由项目负责人提供，ORM 与 API 日志核验；HVR-API01-07 NOT RUN。Codex 模拟：[evidence/codex_simulated_20261123](evidence/codex_simulated_20261123/API01_HTTP_ORM.md) |

## API01 HVR

| 用例 | 执行时间 | HTTP | returnStatus / exceptionInfo / operationTime | Order / ORM 证据 | API 日志/幂等证据 | 判定 |
|---|---|---|---|---|---|---|
| HVR-API01-01 | 首次 10:04:52；复测 11:01:26（ORM/API 日志时间） | 未提供 | 复测 `Y / OK / 2026-11-23 11:01:26`；首次 `N / BUS01: SN清单缺失: ...` 保留 | ORM：Order 1042，业务类型 STANDARD、明细数量 1；无 SN 预报行、无关联 Picking | 首次错误日志 3331 保留；复测成功日志 3332；幂等记录 2629 `succeeded`，attempt_count=1 | **PASS（复测）**；首次旧实例失败作为历史问题保留 |
| HVR-API01-02 | 11:07:06 首次；11:07:30 重试（API 日志时间） | 未提供 | 首次 `N / AUTH01: API认证失败`；刷新 Token 后 `Y / OK / 2026-11-23 11:07:30` | ORM：Order 1043，业务类型 STANDARD、明细数量 1；snList 未写入 JSON/预报行；无关联 Picking | 日志 3333 记录 Token 过期；日志 3335 成功且保留原始畸形 snList 对象；幂等 2630 `succeeded`，attempt_count=1 | **PASS（刷新 Token 后重试）** |
| HVR-API01-03 | 11:09:03（API 日志时间） | 未提供 | `Y / OK / 2026-11-23 11:09:03` | ORM：Order 1044；成品/半成品/原材料数量 4/2/12；9 条预报行按三托盘保存；无关联 Picking | 日志 3336 success；幂等 2631 `succeeded`，attempt_count=1 | **PASS** |
| HVR-API01-04 | 11:12:54（API 日志时间） | 未提供 | `Y / OK / 2026-11-23 11:12:54` | ORM：Order 1045，原材料数量 12；无 SN 预报行、无关联 Picking、无虚拟托盘记录 | 日志 3337 success；幂等 2632 `succeeded`，attempt_count=1 | **PASS** |
| HVR-API01-05 | 11:14:39（API 日志时间） | 未提供 | `Y / OK / 2026-11-23 11:14:39` | ORM：Order 1046；原材料 12（托盘 1/2 为 5/7），成品 1；3 条预报行；成品与原材料共托；无关联 Picking | 日志 3338 success；幂等 2633 `succeeded`，attempt_count=1 | **PASS** |
| HVR-API01-06 | 11:16:03（API 日志时间） | 未提供 | `N / BUS01: SN数量≠1 P=…PROD-SERIAL T=…ALLET001 / 2026-11-23 11:16:03` | ORM：无对应 Inbound Order；无部分明细、Picking 或库存变更 | 错误日志 3339 完整记录 `quantity=3`、产品编码、SN 和托盘；无对应幂等记录 | **PASS（预期拒绝）** |

## HVR-API01-07 — API04 实际数据来源（有条件）

本用例是 Odoo → Ginlong 出站回传，不要求测试者提交 JSON。已新增[预期出站报文样例](test_data/expected/hvr_api01_07_api04_body.json)供与 Mock 收到的 HTTP body 比对；样例基于候选 Picking 的 ORM 字段，不代表本次已经发送或验收。

| 项目 | 实际记录 |
|---|---|
| 前置 Picking / inbound Order | NOT RUN |
| API04 Endpoint 原值是否留存 | NOT RUN |
| Mock 是否收到 HTTP POST | NOT RUN |
| 请求是否对应所选 Move Line | NOT RUN |
| Odoo API 日志记录 | NOT RUN |
| API04 Endpoint 是否恢复 | NOT RUN |
| 判定（PASS / FAIL / BLOCKED / NOT RUN） | NOT RUN；补充项，不作为 CC-GIN-007 关闭门槛 |

## 问题和证据

| 编号 | 现象/差异 | 原始证据路径 | 后续处理 |
|---|---|---|---|
| — | 尚未执行 | — | — |
| HVR-API01-01 首次请求及复测 | 首次请求 `businessType=STANDARD`、SN 管理产品、无 `snList`，错误日志 3331 要求 SN，且未创建 Order/幂等记录；重启 8099 后项目负责人复测成功。ORM：Order 1042 只有产品/数量明细，无 SN 预报行或 Picking；幂等 2629 succeeded | API 日志 3331（首次错误）和 3332（成功复测）；Odoo ORM 只读核对；项目负责人提供成功响应 | 首次错误响应保留；复测证明当前进程按“非保税不处理 snList”工作。HVR-API01-01 以复测结果判 PASS |
| HVR-API01-02 Token 过期 | 首次请求因 Token 过期返回 `N / AUTH01`（日志 3333）；刷新 Token 后同一报文成功（日志 3335）。订单 1043 已保存，但畸形 `snList` 未形成 Order JSON 或 SN 预报行；原始对象仍在请求日志中 | API 日志 3333、3335；Odoo ORM 只读核对；项目负责人提供成功响应 | 认证失败尝试保留；成功重试后 HVR-API01-02 判 PASS |
| HVR-API01-03 三托盘混装 | 成品 4 件、半成品 2 件、原材料 12 件；9 条预报记录汇总均匹配 details。原材料按 5/4/3 跨三托盘，同托盘与 SN 产品混装；无实际 Picking 被创建 | API 日志 3336；ORM Order 1044、SN 预报 JSON、幂等记录 2631 | 已按产品数量、SN 数量和托盘分布核对；HVR-API01-03 判 PASS |
| HVR-API01-04 保税原材料无 SN 清单 | 保税业务类型下原材料数量 12，未发送 `snList`；Order 保存总量，不生成预报 SN 行或虚拟托盘 | API 日志 3337；ORM Order 1045、幂等记录 2632 | 与已确认规则一致；HVR-API01-04 判 PASS |
| HVR-API01-05 原材料分托与 SN 共托 | 原材料数量 12 按两个托盘分为 5/7；一件成品 SN 与第一托盘原材料共托。ORM 保存 3 条预报行，按产品汇总与 details 一致；未创建 Picking | API 日志 3338；ORM Order 1046、预报 JSON、幂等记录 2633 | 与已确认规则一致；HVR-API01-05 判 PASS |
| HVR-API01-06 SN 单条数量非法 | 成品 SN 行 `quantity=3`，响应拒绝并显示产品及托盘定位片段；ORM 无 Order/幂等记录，日志 3339 保留完整产品、SN、托盘和错误原因 | API 日志 3339；Odoo ORM 只读核对；项目负责人提供的响应 | 整单拒绝且无业务副作用；HVR-API01-06 判 PASS（预期拒绝） |

## Codex 本地模拟执行（不替代人工 HVR）

> 本节记录项目负责人要求的 Codex 模拟执行。所有结果均为本机 Odoo HTTP + ORM 证据；不代表业务负责人已完成人工 HVR 或批准关闭。未记录 API Token、密码或 HTTP Session Cookie。

| 项目 | 实际记录 |
|---|---|
| 执行日期 | 2026-11-23 |
| 服务 | `http://127.0.0.1:8089`，PID 43875；本轮启动时端口空闲，实例保持运行 |
| 数据库 | `odooce_karlrapp` |
| Ginlong 模块 | ORM 核实 `installed`，`installed_version=18.0.2.0.40`；本轮通过 Odoo Shell ORM 调用 `button_immediate_upgrade()`，升级后版本仍为 18.0.2.0.40 |
| 前置数据 | Owner A 唯一；原材料 `tracking=none`，成品/半成品 `tracking=serial` |
| 外部系统 | 未访问真实 Ginlong、Karl Rapp 或 Gateway；API01 请求只发往本机 8089 |
| HTTP/ORM 证据 | [本地模拟证据](evidence/codex_simulated_20261123/API01_HTTP_ORM.md) |

### API01 六个请求模拟结果

| 用例 | HTTP/业务响应 | ORM 与幂等结果 | API 日志 | Codex 模拟判定 |
|---|---|---|---|---|
| HVR-API01-01 | HTTP 200，`Y / OK`，09:28:09 | 入库单 1037；1 条明细；无预报行、无 Picking；幂等 2622 `succeeded` | 3323 | 符合预期 |
| HVR-API01-02 | HTTP 200，`Y / OK`，09:28:24 | 入库单 1038；1 条明细；畸形 `snList` 未形成预报行；幂等 2623 `succeeded` | 3324 | 符合预期 |
| HVR-API01-03 | HTTP 200，`Y / OK`，09:28:36 | 入库单 1039；成品/半成品/原材料数量 4/2/12；保存 9 条预报行，三托盘分布正确；无 Picking；幂等 2624 `succeeded` | 3325 | 符合预期 |
| HVR-API01-04 | HTTP 200，`Y / OK`，09:28:44 | 入库单 1040；原材料数量 12；无预报行、无 Picking；幂等 2625 `succeeded` | 3326 | 符合预期 |
| HVR-API01-05 | HTTP 200，`Y / OK`，09:28:54 | 入库单 1041；原材料 5/7 跨托盘，成品 SN 与原材料共托；3 条预报行；无 Picking；幂等 2626 `succeeded` | 3327 | 符合预期 |
| HVR-API01-06 | HTTP 200，`N / BUS01`，09:29:07；指出 SN 单条数量错误、产品和托盘 | 入库单不存在；无幂等记录 | 3328，完整诊断保留产品、SN、托盘和数量 | 符合预期拒绝 |

以上为 Codex 模拟结果，不替代上文项目负责人随后完成的人工 HVR-API01-01–06；模拟运行时的结果与人工结果分开记录。

### API04 条件场景状态

只读 ORM 找到候选：已完成入库 Picking `KRWH/KRIN/00168`（ID 300），关联 Order `HVR-GIN005-IN-001`，实际 Move Line 有产品、数量、SN、托盘、操作人及操作时间。API04 Endpoint 当前未配置。本轮 Browser 会话在模块升级后显示 Odoo Session Expired；已请求用户通过内置浏览器完成认证。因此尚未执行 Mock HTTP 回传、未更改 Endpoint 或订单，HVR-API01-07 保持 NOT RUN，待认证后继续。
