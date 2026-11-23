# CC-GIN-007 API01 Codex 本地模拟证据

**日期：** 2026-11-23
**范围：** API01 六个 HVR 请求；仅本机 Odoo HTTP 与 ORM。
**状态语义：** 以下是 Codex 模拟结果，不是业务负责人签署的人工 HVR。

## 环境与升级

- HTTP URL：`http://127.0.0.1:8089/api/ginlong/TPL_Pending_Receipt_Note`
- 数据库：`odooce_karlrapp`
- 项目现有 `venv`、`odoo.conf`
- 服务 PID：43875，启动参数将 `http_port` 覆盖为 8089，`max_cron_threads=0`。
- 8089 启动时原端口空闲；8089 服务保持运行。既有 8099 服务未停止。
- Odoo Shell ORM 升级前后核实：`ginlong_apis` 为 `installed`，`installed_version=latest_version=18.0.2.0.40`；调用了 `button_immediate_upgrade()`。
- Owner A 命中 1 条；原材料变体 `HVR01-20261121-PROD-COMMON` 为 `tracking=none`；成品 `HVR01-20261122-PROD-SERIAL` 和半成品 `HVR01-20261122-PROD-SEMIFINISHED` 均为 `tracking=serial`。

## 实际 HTTP 响应

实际请求通过包内 `test_data/curl/hvr_api01_01.sh` 至 `hvr_api01_06.sh` 顺序执行。Token 从本机隐藏环境文件加载，未打印或写入本证据；`Set-Cookie` Session Cookie 已排除。

| 用例 | `inboundOrderNo` | HTTP | 实际响应 Body |
|---|---|---:|---|
| 01 | `HVR07-20261123-NONBONDED-01` | 200 | `{"returnStatus":"Y","exceptionInfo":"OK","operationTime":"2026-11-23 09:28:09"}` |
| 02 | `HVR07-20261123-NONBONDED-02` | 200 | `{"returnStatus":"Y","exceptionInfo":"OK","operationTime":"2026-11-23 09:28:24"}` |
| 03 | `HVR07-20261123-BONDED-MIX-03` | 200 | `{"returnStatus":"Y","exceptionInfo":"OK","operationTime":"2026-11-23 09:28:36"}` |
| 04 | `HVR07-20261123-BONDED-RAW-NOSN-04` | 200 | `{"returnStatus":"Y","exceptionInfo":"OK","operationTime":"2026-11-23 09:28:44"}` |
| 05 | `HVR07-20261123-BONDED-RAW-SPLIT-05` | 200 | `{"returnStatus":"Y","exceptionInfo":"OK","operationTime":"2026-11-23 09:28:54"}` |
| 06 | `HVR07-20261123-BONDED-INVALID-SN-QTY-06` | 200 | `{"returnStatus":"N","exceptionInfo":"BUS01: SN数量≠1 P=…PROD-SERIAL T=…ALLET001","operationTime":"2026-11-23 09:29:07"}` |

Odoo 服务日志 `/private/tmp/ginlong_8089.log` 中 09:28:09 至 09:29:07 有六条对应的本机 `POST /api/ginlong/TPL_Pending_Receipt_Note` 记录，HTTP 状态均为 200。

## ORM 持久化断言

| 用例 | Order ID | Details | SN 预报行 | Picking | 幂等 ID/状态 | API Log ID/状态 |
|---|---:|---|---:|---|---|---|
| 01 | 1037 | 成品 1 | 0 | 无 | 2622 / `succeeded` | 3323 / success |
| 02 | 1038 | 成品 1 | 0；非保税畸形 `snList` 未保存为业务预报 | 无 | 2623 / `succeeded` | 3324 / success |
| 03 | 1039 | 成品 4、半成品 2、原材料 12 | 9 | 无 | 2624 / `succeeded` | 3325 / success |
| 04 | 1040 | 原材料 12 | 0 | 无 | 2625 / `succeeded` | 3326 / success |
| 05 | 1041 | 原材料 12、成品 1 | 3 | 无 | 2626 / `succeeded` | 3327 / success |
| 06 | 不存在 | 未创建 | 0 | 无 | 无记录 | 3328 / error |

API01-03 九条预报行：

| 托盘 | 成品 SN | 半成品 SN | 原材料数量 |
|---|---|---|---:|
| `HVR07-B03-PALLET001` | `FG-001`、`FG-002`，各 1 | `SF-001`，1 | 5 |
| `HVR07-B03-PALLET002` | `FG-003`，1 | — | 4 |
| `HVR07-B03-PALLET003` | `FG-004`，1 | `SF-002`，1 | 3 |

API01-05 三条预报行：原材料 `PALLET001=5`、`PALLET002=7`；成品一条数量 1，与原材料共用 `PALLET001`。

API01-06 完整日志诊断：`Business processing rejected: APIAPI01 snList[0].quantity=3; each SN row must equal 1; productCode=HVR01-20261122-PROD-SERIAL, productSN=HVR07-B06-FG-INVALID-001, palletCode=HVR07-B06-PALLET001`。

额外 ORM 断言：API01-02 的 API 日志原始请求仍包含 `snList={"unexpected":"not an snList array"}`；以六个 HVR 单号查询 `stock.picking.origin`、`stock.move.origin` 和对应 move lines 均为 0；订单没有关联 Picking。

## API04 条件场景预检

只读 ORM 发现一个候选 Picking：

- Picking `KRWH/KRIN/00168`，ID 300，`state=done`，incoming。
- 关联 Order `HVR-GIN005-IN-001`。
- Move Line：产品 `HVR-GIN005-P001`、数量 1、SN `HVR-GIN005-SN-001`、托盘 `HVR-GIN005-PALLET-001`、操作人 `KR-OP-BROWSER`、操作时间 `2026-11-19 07:32:31`。
- API04 Endpoint 当前为空。
- 尚未通过 UI 配置本机 Mock、发送或恢复设置。浏览器当前会话过期，故 API04 HVR 未执行。

## 限制

- 未访问真实 Ginlong、Karl Rapp 或 Gateway。
- 未创建、修改或删除 API01 外的业务单据；未进行库存过账。
- 本地 API01 请求创建的五张 Order、对应日志和幂等记录保留在开发数据库中，不做清理。
- UI 页面确认、Administrator 身份核实和 API04 Mock 回传仍未完成；不得把后端 HTTP/ORM 证据冒充为浏览器 HVR。
