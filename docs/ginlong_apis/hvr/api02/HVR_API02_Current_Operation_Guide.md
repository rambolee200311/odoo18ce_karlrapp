# API02 收货确认 — 当前人工操作指南

> **项目级主线：** 实际项目 HVR 订单必须按[项目级仓库业务流程 HVR](../HVR_Project_Business_Flow_Guide.md)由 API01 创建，并在同一订单依次测试未收货 N、业务收货确认后 Y。不要按本目录旧的独立 Payload 另造订单、Picking 明细或收货结果。API02 出站请求必须由订单“Ginlong 回传数据”页的真实按钮触发。

> 本单接口指南已并入[《API01→API02→API04 入库业务人工 HVR 指南》](../HVR_Inbound_Business_Guide.md)。项目级 HVR 只按合并指南执行；本文件保留作历史参考，不单独起一个 API02 HVR。

本指南依据 CC-GIN-009 v1.0 冻结基线。API02 回传订单级收货确认状态；不读取 Picking、move line 或旧的收货明细子表。API02 当前回传按钮位于订单的“Ginlong 回传数据”Notebook 页，不在订单标准表头。旧版 API02 Test Plan/Cases 中关于选择 move line、逐行填写 Y/N、混合状态阻止、无收货明细报错及表头回传按钮位置的步骤已经过时，保留作历史，不再执行。

## 操作结果

| 操作/当前订单业务状态 | API02 receiptConfirmed |
|---|---|
| planning | N |
| arrive | Y |
| inbound | Y |

收货确认按钮只将业务字段 status 写为 arrive，并保留现有操作跟踪；不改变订单生命周期 state。API02 回传按钮仅读取已保存 status，不触发收货确认，也不要求先创建 Picking。

## 重复回传及并发提示

- 当前状态对应的 Payload 已有成功回传时，再次点击会提示上次时间、状态和结果；用户确认才会真实重发，取消则不发送。
- Ginlong 明确返回 `returnStatus=N`，或本地确认请求尚未发送的错误，可再次点击直接重试。
- 请求发出后出现超时、连接异常、无明确 `N` 的 HTTP 错误或无效/不完整响应，属于结果未知；须在风险提示中明确确认后才能重试。
- 若另一用户/标签页正在发送同一订单事件，或本次点击等待时该事件刚完成，本次不会再发 HTTP，也不弹出重复成功确认框；提示本次未发送。
- 发送中的按钮应显示 Odoo 标准 loading/disabled 状态；跨标签页的实际请求数仍以 Mock 捕获为准，前端状态不替代后端并发保护。
- 完整人工执行步骤（成功确认/取消、明确失败、unknown 风险确认、事件日志及 HTTP 计数）见[通用重复回传执行记录](../HVR_Callback_Repeat_Confirmation_Execution_Record.md)。所有场景初始 NOT RUN。

## 环境准备

- 本机 Odoo：`http://127.0.0.1:8099/odoo`；数据库 `odooce_karlrapp`。执行前由管理员确认本地服务当前可用。
- API02 Mock：`http://127.0.0.1:18102/API/WMS_JSON/TPL_Receipt_Confirmation`。
- Mock 接收器：`test_data/mock_api02_receiver.py`。健康检查为 GET，不会创建 API 业务记录：

~~~bash
python3 docs/ginlong_apis/hvr/api02/test_data/mock_api02_receiver.py --host 127.0.0.1 --port 18102
curl --fail --silent http://127.0.0.1:18102/__mock__/health
~~~

管理员把 ginlong_apis.api02_callback_url 配置为上述本地 Mock URL。配置应通过 Odoo Settings 或现有 ORM 配置流程完成；若 test_data/.api02_endpoint_backup 已存在，勿覆盖备份，先查明当前 HVR 是否仍在进行以及应恢复哪个配置。不要将真实地址或凭据写进执行记录。

## 准备一张干净订单

1. 从 API01 已通过的入库 Add 测试报文复制业务字段，改为未使用的 inboundOrderNo；使用已存在的货主、产品及本地 API User Token，通过 API01 创建订单。不要用 Backend 的 New 手工创建，也不要重复提交已成功的订单号。
2. 在 WorldDepot → Inbound → Orders 按该 inboundOrderNo 搜索并打开 API01 创建的单据。记录单号及订单 ID。
3. API01 报文没有 Odoo WMS 的 `Arrival Date`，但当前 Inbound Order Form 将其设为必填。先在 Main 页填写并保存该日期，保存后重新打开/刷新单据确认日期仍显示，再检查订单 status 为 planning、state 保持原生命周期值。若出现 `Session expired` 或日期未持久化，先恢复登录并重新保存；不要继续点回传按钮。不要执行 Confirm/Create Receipt，也不要创建 Picking 或 move line。

## HVR 场景

### HVR-API02-C01：planning 回传 N

1. 确认重新打开单据后 `Arrival Date` 仍已保存且订单 status=planning；若日期缺失，Odoo 的表单校验会在按钮 RPC 之前阻止操作，Mock 不会收到请求。Codex 模拟期间曾遇到保存请求因 `Session expired` 未持久化，因此必须检查保存结果。
2. 打开订单的“Ginlong 回传数据”Notebook 页，点击“回传锦浪：收货确认”。
3. 在 Mock 捕获文件 test_data/received.jsonl 确认由 Odoo 按钮实际发送一条 POST；不使用 curl/Postman 手工发送 API02。

预期 Payload：

~~~json
{
  "inboundOrderNo": "替换为本次 API01 创建的订单号",
  "action": "UPDATE",
  "receiptConfirmed": "N"
}
~~~

Mock 返回 returnStatus=Y、exceptionInfo=OK、operationTime；Odoo 显示成功结果并记录 API Log。业务 status/state 均未因回传按钮变化。

### HVR-API02-C02：收货确认后回传 Y

1. 在同一入库订单点击“收货确认”。
2. 确认订单 status 更新为 arrive，Chatter/字段跟踪记录操作人、时间和状态；订单生命周期 state 不变。
3. 点击“回传锦浪：收货确认”。
4. 核对 Mock 捕获的新 POST 中同一 inboundOrderNo、action=UPDATE、receiptConfirmed=Y；核对对应 Odoo API Log。

该步骤只确认订单级业务状态；不要填写 move line 状态，不要把 API04 的实际入库完成当成 API02 收货确认。

### HVR-API02-C03：现有 WMS 状态 inbound 仍映射 Y（可选）

如果现有业务流程已经把另一张测试订单的 status 更新为 inbound，直接检查该值并点击 API02 按钮，Mock 应捕获 receiptConfirmed=Y。不得为了本场景手工写数据库或伪造库存状态；若 WMS 流程未产生 inbound，可记录 BLOCKED/NOT RUN，不必额外改变业务流程。

### HVR-API02-C04：同状态重复点击（可选）

对已成功回传且 status 未变化的订单再次点击按钮，预期打开“确认 Ginlong 回传”窗口，并显示订单、上次状态、时间和安全的响应摘要。此时 Mock 请求数不变：

- 选择“取消”：关闭窗口且不发送 HTTP；订单 Chatter 记录取消决定，API Event/API Log 不新增。
- 选择“确认回传”：系统重新读取已保存状态并真实 POST 相同 Payload；Mock 新增一条请求，API Event 新增一条关联原成功 Event 的记录，API Log 追加本次 HTTP 结果。

若收货状态已变化，生成的 Payload 指纹也变化，则不弹成功重复确认窗口，直接发送新状态。不得通过修改无关字段来改变判重结果。

## 核对与记录

- Mock 每条记录包含由 Odoo 实际按钮发送的 HTTP POST、Payload 和模拟响应；路径为 `/API/WMS_JSON/TPL_Receipt_Confirmation`，Content-Type 为 application/json。
- 在 WorldDepot → Ginlong APIs → API 日志中按接口及订单来源核对请求、响应、结果和时间。
- API02 请求只包含订单号、UPDATE 和 receiptConfirmed；没有订单明细、SN、托盘、数量或 Picking 数据。
- 人工执行记录填写 `HVR_API02_Execution_Record.md` 及上述通用执行记录。历史 CC-GIN-009 行保持原值，新增加的项目 HVR 场景初始 NOT RUN；Codex 不代填 PASS/FAIL。
- 本地 Mock 验证不代表真实 Ginlong 分批协议或真实环境联调。CC-GIN-009/010 均不设独立人工 HVR；项目级 HVR 单独验收。
