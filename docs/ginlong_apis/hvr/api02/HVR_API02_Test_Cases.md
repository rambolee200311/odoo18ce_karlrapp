# API02 收货确认人工测试实例（历史版，已被 CC-GIN-009 取代）

> 当前步骤请使用 [HVR_API02_Current_Operation_Guide.md](HVR_API02_Current_Operation_Guide.md)。本文件只作历史追溯；逐行 move line 状态、混合 Y/N 阻止及无明细校验均不再作为现行规则。

> 项目级业务链请使用[统一仓库业务流程 HVR](../HVR_Project_Business_Flow_Guide.md)中的同一 API01 单据；本文件的旧 API01 订单不能作为 API03/05/09 的前序业务数据。

## 统一前置：通过 API01 建入库订单

API02 测试订单不是手工 New 的。先按每个场景指定的文件调用 API01：

| API02 场景 | API01 报文文件 | 新建 Reference |
| --- | --- | --- |
| 01、02、04 | [api01_order_01.json](test_data/payloads/api01_order_01.json) | HVR-API02-20261124-01 |
| 03 | [api01_order_03.json](test_data/payloads/api01_order_03.json) | HVR-API02-20261124-02 |
| 05 | [api01_order_05.json](test_data/payloads/api01_order_05.json) | HVR-API02-20261124-03 |

地址为 `http://127.0.0.1:8099/api/ginlong/TPL_Pending_Receipt_Note`，方法 POST，Content-Type application/json，Authorization 使用 API01 HVR 的本地 API User Token。可在本机终端设置 GINLONG_HVR_BASE_URL 和 GINLONG_HVR_TOKEN，再运行：

~~~bash
bash docs/ginlong_apis/hvr/api02/test_data/curl/api01_add_order.sh docs/ginlong_apis/hvr/api02/test_data/payloads/api01_order_01.json
~~~

先在 **WorldDepot → Inbound → Orders** 按 Reference 搜索，确认该编号尚未存在，再只调用一次 Add。收到 API01 成功响应后，搜索并打开对应单据。若响应不确定，先查 Reference 和 API 日志，不要盲目重发 Add；编号已存在时，改用新的未使用编号。三个请求均是已确认的 API01 STANDARD 非 SN 业务，产品为 HVR01 Owner A 的非 SN 产品。

API01 创建订单表头及产品明细；它不创建 Picking、不代表仓库已收货、不更新库存。订单的 Project、Owner、Warehouse、Picking Type 和产品明细应从 API01 及现有配置带入，不要手工 New 订单或再次添加产品行。

## WMS 收货作业准备（适用于 01、02、03）

1. 在 API01 创建的单据上核对 Reference、Owner、Project、Warehouse、Picking Type 和产品明细。若订单或产品数据缺失/不符，停止并记录。
2. 订单仍为 New 时，填写 Create Receipt 要求但 API01 不提供的 Container No；Arrival Date 若为空也补齐。不要改订单号、Owner 或产品明细。
3. 点击单据顶部 **Confirm**，再点击 **Create Receipt**。检查该订单关联一个新的未完成 Picking 及 move line。不要点击 Picking **Validate/Done**。
4. 在该 Inbound Order 的 **Ginlong 回传数据 → API02 收货确认**页添加一行，选择刚创建且属于该订单的 move line，将收货状态设为指定值并保存。离开后重新打开订单，确认数据已保存。

Create Receipt 是从 API01 创建的指令进入现有 WMS 流程；不会因为生成未完成 Picking 而完成收货或过账库存。API02 操作只回传已保存的订单级收货确认结果。

## HVR-API02-01：API01 建单后回传 Y

### 目的

验证 Ginlong API01 请求创建的入库订单可以进入现有 WMS 收货流程；从已保存的收货明细状态生成 API02，并由真实按钮发送到本机 Mock。

### 执行

1. 按统一前置发送 `api01_order_01.json` 一次，Reference 为 `HVR-API02-20261124-01`；确认 API01 返回成功。
2. 在 Backend 搜索并打开该 API01 创建的 Order。按 WMS 收货作业准备流程执行 Confirm → Create Receipt，不 Validate/Done。
3. 在 Ginlong 回传数据页选择本次新建的一条 move line，设收货状态 Y，保存并重新打开核实。
4. 点击订单顶部 **回传锦浪：收货确认**。

### 预期

Mock 新增一条由 Odoo 按钮发送的 POST，Path 为 `/API/WMS_JSON/TPL_Receipt_Confirmation`，Content-Type 为 `application/json`：

~~~json
{
  "inboundOrderNo": "HVR-API02-20261124-01",
  "action": "UPDATE",
  "receiptConfirmed": "Y"
}
~~~

Mock 返回 V3.2 三字段成功响应；Odoo 显示成功通知并在 API 日志新增记录。Picking 仍未过账，库存没有因 API02 回传改变。

人工记录：判定 ____；API01 响应 ____；Order ID/Reference ____；Picking ____；Mock 行 ____；API 日志 ID ____；证据 ____。

## HVR-API02-02：同一订单修改为 N 后回传

### 前置

HVR-API02-01 已完成；仍使用 API01 创建的 `HVR-API02-20261124-01` 订单和原 move line。

### 执行及预期

将已保存的收货状态从 Y 改成 N，保存并重新打开核实，然后再次点击 **回传锦浪：收货确认**。预期 Mock 捕获新的真实 POST，内容的 inboundOrderNo 不变、action 为 UPDATE、receiptConfirmed 为 N；Odoo 新增一次 API 日志。不要再次调用 API01 Add。

人工记录：判定 ____；Mock 行 ____；API 日志 ID ____；证据 ____。

## HVR-API02-03：混合 Y/N 状态被阻止

### 前置订单

调用 `api01_order_03.json` 一次创建 Reference `HVR-API02-20261124-02`。这个 API01 报文包含同一非 SN 产品的两条数量为 1 的订单明细；这使现有 WMS Create Receipt 为两条作业行分别生成托盘/ move line。不要手工另建订单或产品。

### 执行

在新订单执行 Confirm → Create Receipt，不 Validate/Done。确认产生两条属于该订单的不同 move line。在 API02 收货确认页分别选择两条 move line，保存一条 Y、一条 N，重新打开核实后点击回传按钮。

### 预期

Odoo 提示订单明细状态不一致；Mock 捕获文件不增加行；没有 API02 HTTP POST。API 日志按现有实现记录本地失败。人工记录：判定 ____；API01 响应 ____；Order/两条 move line ____；提示 ____；Mock 行数前/后 ____；日志 ID ____；证据 ____。

## HVR-API02-04：同一成功事件重复点击

### 前置

HVR-API02-02 已成功，`HVR-API02-20261124-01` 当前保存状态为 N。

### 执行及预期

不修改任何已保存字段，直接再次点击 **回传锦浪：收货确认**。按现有出站幂等设计，Mock 不应收到重复 POST；检查 Odoo 页面结果以及这次点击是否仍追加 API 日志。不要用成功通知代替 Mock 捕获证据。

人工记录：判定 ____；Mock 行数前/后 ____；API 日志 ID ____；证据 ____。

## HVR-API02-05：没有 API02 收货明细时阻止发送

### 前置

调用 `api01_order_05.json` 一次创建 Reference `HVR-API02-20261124-03`。这是 API01 创建的有效订单，含一条产品指令；但本例特意不进行 WMS 收货作业，不点击 Confirm/Create Receipt，也不添加 Ginlong 收货确认行。

### 执行及预期

打开该订单，确认 Ginlong 回传数据页的 API02 明细为空，点击订单顶部 **回传锦浪：收货确认**。预期 Odoo 的必填校验阻止发送并指出缺少订单级收货确认值；Mock 不新增捕获行；API 日志按现有实现记录失败。

人工记录：判定 ____；API01 响应 ____；Order ID/Reference ____；Odoo 提示 ____；Mock 行数前/后 ____；API 日志 ID ____；证据 ____。
