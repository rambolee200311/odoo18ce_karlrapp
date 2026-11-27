# API02 收货确认人工 HVR 测试计划（历史版，已被 CC-GIN-009 取代）

> 当前步骤请使用 [HVR_API02_Current_Operation_Guide.md](HVR_API02_Current_Operation_Guide.md)。本文件保留历史，不再执行逐 move line 收货状态及混合 Y/N 场景。

> 项目级主线请改用[统一仓库业务流程 HVR](../HVR_Project_Business_Flow_Guide.md)：同一 API01 Order 先验证 Planning=N，再通过业务收货确认后验证 Y。不要从本历史计划另建项目主线订单。

## 1. 目的和范围

本 HVR 从真实 API01 入站调用开始，验证 Ginlong 创建的 Inbound Order 经现有 WMS 收货作业准备后，能否由业务用户保存 API02 收货确认状态、点击 Odoo 回传按钮，通过 HTTP POST 将系统生成的 JSON 发送给本地 Mock，并在 Odoo 日志中留下结果。

验收人亲自调用 API01、执行 WMS 单据操作、保存收货状态、点击 API02 按钮、查看 Mock 和 Odoo 日志并判定 PASS/FAIL。API02 回传 JSON 只用于结果对照，不可用 curl/Postman 手工发送。

## 2. 已核实的接口及数据来源

| 项目 | 核实结果 |
| --- | --- |
| API01 | POST /api/ginlong/TPL_Pending_Receipt_Note；从 Ginlong 请求创建 WorldDepot 入库 Order 和订单产品明细 |
| API02 Object ID | TPL_Receipt_Confirmation |
| API02 HTTP Method / Content-Type | POST / application/json |
| API02 来源 | 已保存的 world.depot.inbound.order 与其 ginlong_receipt_detail_ids 收货状态；每条状态关联同一 Order 的 stock.move.line |
| API02 Payload | inboundOrderNo、action=UPDATE、receiptConfirmed=Y/N；不包含订单明细、SN 或库存数量 |
| API02 成功 Mock 响应 | returnStatus=Y、exceptionInfo=OK、operationTime=yyyy-MM-dd HH:mm:ss |
| API02 回传按钮 | 入库单“Ginlong 回传数据”Notebook → API02 收货确认 → “回传锦浪：收货确认” |
| API02 收货状态页面 | 入库单 Notebook“Ginlong 回传数据”→“API02 收货确认” |
| 状态汇总 | 全部明细 Y 得 Y；全部 N 得 N；混合 Y/N 本地阻止；无明细时校验阻止 |
| 不过账边界 | WMS Create Receipt 生成 Picking / move / move line 后，不点击 Validate/Done；本 HVR 不过账库存 |

## 3. API01 与 WMS 前置流程

本 HVR 不通过 Backend 的 New 手工创建业务订单。使用以下 API01 Add Payload 创建干净订单：

| 场景 | API01 Payload | Order Reference | 后续操作 |
| --- | --- | --- | --- |
| HVR-API02-01、02、04 | test_data/payloads/api01_order_01.json | HVR-API02-20261124-01 | 创建一次 WMS Receipt，01/02/04 共用 |
| HVR-API02-03 | test_data/payloads/api01_order_03.json | HVR-API02-20261124-02 | 创建两条收货作业行，用于 Y/N 混合状态 |
| HVR-API02-05 | test_data/payloads/api01_order_05.json | HVR-API02-20261124-03 | 不创建 Picking，不新增 API02 收货明细 |

三个 API01 报文均为 STANDARD 入库，只含必需表头和非 SN 产品明细，不提供 snList。它们通过 API01 建订单，不是 API02 的回传报文。只调用各自一次；API01 Add 成功后不要重发同一单号。响应不确定时，先按 Reference 查订单和 API 日志。

API01 HTTP 请求脚本 `test_data/curl/api01_add_order.sh` 只允许访问本机 Odoo。设置 GINLONG_HVR_BASE_URL 和 GINLONG_HVR_TOKEN 后，按场景调用相应文件：

~~~bash
export GINLONG_HVR_BASE_URL='http://127.0.0.1:8099'
read -rsp '本地 API User Token: ' GINLONG_HVR_TOKEN; export GINLONG_HVR_TOKEN; echo
bash docs/ginlong_apis/hvr/api02/test_data/curl/api01_add_order.sh docs/ginlong_apis/hvr/api02/test_data/payloads/api01_order_01.json
~~~

API01 使用现有项目 API User Token；当前项目调用格式为 `Authorization: <access_token>`，不加 `Bearer`。不要将 Token 写入报文文件或执行记录。

API01 创建的订单使用 API User 配置的 WMS Project；Owner、Warehouse、Picking Type 和产品明细从 API01 请求及现有 Project/Product 配置生成。API01 不创建实际 Picking、不完成仓库作业、不做库存过账。

订单出现在 **WorldDepot → Inbound → Orders** 后，按下面步骤处理：

1. 按 Reference 搜索并打开 API01 刚创建的订单。核对 Owner、Project、Warehouse、Picking Type 和产品明细；异常时停止，不要手工重建订单或产品行。
2. 在订单仍为 New 时，只补填 API01 不提供但现有 Create Receipt 操作要求的 Container No；Arrival Date 如为空也补填。不要重新录入订单号、货主或产品明细。
3. 对 01/02/03 场景点击订单顶部 Confirm，再点击 Create Receipt。确认这张订单关联了新 Picking 和 move line；不要点击 Picking Validate/Done。
4. 对 01/02/03 场景进入“Ginlong 回传数据”→“API02 收货确认”，选择刚生成且属于该 Order 的 move line，填写 Y 或 N 并保存。离开页面再打开确认数据仍在。
5. 对 05 场景不 Confirm、不 Create Receipt、不新增 API02 收货明细。

WMS Create Receipt 是从 API01 订单进入现有仓库业务流程，不是人工另建订单。它建立未完成收货作业行，不代表已完成收货；不点击 Validate/Done，因此不产生库存过账。

## 4. 测试矩阵与顺序

| 顺序 | 实例 | 前置订单 | 状态/动作 | 预期 |
| ---: | --- | --- | --- | --- |
| 1 | HVR-API02-01 | API01 Reference ...-01 | 一条明细 Y，保存后点击回传 | Mock 捕获一条 POST，receiptConfirmed=Y |
| 2 | HVR-API02-02 | 同一 ...-01 | 将同一条状态改 N 并保存后点击 | Mock 捕获新 POST，receiptConfirmed=N |
| 3 | HVR-API02-03 | API01 Reference ...-02 | 两条不同 move line 分别 Y/N 后点击 | 本地阻止发送，Mock 无新 POST |
| 4 | HVR-API02-04 | 同一 ...-01 | 不改已成功的 N 状态，再点击 | 按现有幂等结果不重复 POST；检查本次日志 |
| 5 | HVR-API02-05 | API01 Reference ...-03 | 不建 Picking/API02 明细，点击按钮 | 必填校验阻止发送，Mock 无新 POST |

## 5. 验收证据

Mock 捕获文件为 `test_data/received.jsonl`，每行是一条 Odoo 按钮发出的真实 HTTP POST。检查 **WorldDepot → Ginlong APIs → API 日志**中的请求、响应及错误。API01 成功、订单出现在界面或 Mock 健康检查都不等于 API02 HVR 通过。

所有实例起始状态均为 NOT RUN。完成后由验收人在 [执行记录](HVR_API02_Execution_Record.md) 写入实际 Reference、Picking、Mock 捕获行、API 日志 ID、操作时间和 PASS/FAIL/BLOCKED；Codex 不代填验收结果。
