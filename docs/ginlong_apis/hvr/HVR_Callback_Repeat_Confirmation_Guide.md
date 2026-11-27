# API02 / API04 / API06 / API08 重复回传确认操作说明

**状态：** 操作说明；人工结论由业务验收人填写。CC-GIN-010 本身不组织 HVR。执行项目级 HVR 时，须遵循对应业务指南及当前已部署版本。

API02/API04 入库业务的干净订单、Mock 和完整操作顺序见[入库业务 HVR 指南](HVR_Inbound_Business_Guide.md)。API06/API08 按下表中的订单事件单位和同一向导交互验收；所有人工结果填写在[通用执行记录](HVR_Callback_Repeat_Confirmation_Execution_Record.md)。

## 共通操作

1. 在对应业务单据的 **Ginlong 回传数据** 页，点击该接口的“回传锦浪”按钮。首次发送仍按现有业务数据来源生成 Payload 并同步发送。
2. 同一业务事件、同一规范化 Payload 已成功回传时，再点击按钮会打开确认窗口，展示业务对象、上次成功时间、状态和安全响应摘要；不显示原始 JSON。
3. 用户选择取消时，不发送 HTTP、不新增 HTTP API Log/Event；来源单据 Chatter 记录用户、时间和决定。
4. 用户确认时，后台重新读取已保存 ORM 数据并生成 Payload；确认成功后必须真实发送一次 HTTP POST，新增子 Event（关联原成功 Event）和本次 HTTP API Log。历史记录不覆盖。
5. Payload 已变化且不存在该版本的成功记录时，直接发送；不使用 `write_date` 单独判断业务内容变化。
6. 明确收到 `returnStatus=N` 的失败，或能证明请求尚未发送的本地拒绝，可再次点击直接重试。HTTP 请求发生后连接/响应异常、没有明确 `returnStatus=N` 的 HTTP 错误、无效/不完整响应均是结果未知；窗口必须显示可能已被处理的风险，用户确认后才发送。取消则零发送。
7. 同一稳定业务事件仍在处理，或本次等待期间已由另一标签页/用户完成时，不得再次发送，也不得打开历史成功确认窗口；页面提示本次未发送，用户之后可重新点击并按最新状态判定。按钮在 RPC 执行期间显示 loading/disabled，但并发安全由服务端幂等协调保证。
8. 多个独立事件同时处理时（目前 API04 每个 Picking 一个事件），默认选择“仅回传未成功项”；可选“回传全部”或“取消”。处理中事件始终跳过，未知事件仍需风险确认。

## 各 API 业务对象

| API | 从哪里点击 / 事件单位 | 重复窗口中的预期范围 |
|---|---|---|
| API02 收货确认 | 入库 Order 的 Ginlong 回传数据页；一张 Order 的订单级状态 Payload | 单事件确认/取消；状态变化生成新 Payload 后直接发送 |
| API04 入库完成 | 入库 Order 的 Ginlong 回传数据页；每张关联的 Done/Incoming `stock.picking` 是独立事件 | 多 Picking 可混合成功、失败、首次和未知；默认仅未成功项；全量或取消由用户选择 |
| API06 备货完成 | 出库 Order 的 Ginlong 回传数据页；已有 Picking/move line 实绩聚合为一个订单级事件 | 多张 Picking 仍是一个聚合 Payload；不可拆成逐 Picking 回传 |
| API08 发货完成 | 出库 Order 的 Ginlong 回传数据页；一张 Order 的订单级状态 Payload | 单事件确认/取消；发货状态变化形成新 Payload 后直接发送 |

## API06 / API08 人工操作准备

以下步骤补足出库回传的实际操作对象与保存位置。只使用已有 WorldDepot 出库单、关联 Picking 和实际 move line；不要手工构造 Payload。

### API06：备货完成

1. 打开 **WorldDepot → Outbound → Orders**，找到已经记录实际备货作业的出库单，进入 **Ginlong 回传数据** 页。
2. 在作业单列表中勾选本次要包含的 Picking 的 **纳入本次 Ginlong 回传**，保存出库单。选择范围是用户本次确认要报告的已保存备货实绩；API06 会把所选 Picking 的实际作业行聚合成一个订单级事件。
3. 打开所选 Picking 的 **Ginlong 回传数据** 页，逐条核对实际 move line 的产品、Lot/Serial、数量和 Package；填写实际 `Ginlong 回传操作人员` 与 `Ginlong 回传操作时间`，保存后重新打开确认值仍在。
4. 返回出库单的 **Ginlong 回传数据** 页，核对 `实际托盘数（自动）`、`实际净重（kg）`、`回传总重量/毛重（kg）`。系统按已选 move line 的 `package_id` 去重计算托盘数；净重按产品档案 `ginlong_weight × 实际数量` 汇总；毛重默认净重。若需使用业务确认过的人工值，先启用相应覆盖项、填写并保存，再发送。
5. 点击 **回传锦浪：备货完成**。Mock 应收到一个订单级 POST，`snList` 来自所选实际 move line，且 `palletQty` / `totalWeight` 使用已保存的订单值。首次成功后再点，分别验证取消不增加请求、确认后实际增加一次请求。
6. 多 Picking 时再次点击仍是一份聚合 Payload 和一个事件。失败或结果未知、重复点击按本指南共通规则执行；不要将 API06 拆成每张 Picking 单独回传。

### API08：发货完成

1. 打开 **WorldDepot → Outbound → Orders**，找到已有实际发货 move line 的出库单，进入 **Ginlong 回传数据** 页。
2. 在 API08 发货明细中添加/选择本订单对应的实际发货 move line；核对产品、SN、数量和托盘显示来自所选 move line，设置并保存该行的 `shipment_status`（按业务实际确认值 Y/N）。离开再打开订单确认明细和状态已持久化。
3. 若有多条明细，逐行维护已确认的业务状态；当前订单级接口只接受能够汇总成一个确认值的记录，Y/N 混合时应显示业务错误并阻止发送。不要为通过接口而改写真实业务状态。
4. 点击 **回传锦浪：发货完成**。Mock 应收到订单级 Payload，包含 `outboundOrderNo`、`action=CREATE` 和按已保存发货状态汇总的 `shipmentConfirmed`。成功后再点，取消应为零新增请求；确认后应实际增加一次 POST，并追加 Event / API Log。
5. 明确失败可直接重试；unknown 必须先确认风险。每次核对 Mock 请求增量与订单来源、API Event、API Log 和 Chatter 决定。

若菜单、字段或当前页面与步骤不符，记录页面可见字段和订单状态并暂停该场景；不要用 ORM、SQL 或手工 HTTP 补造业务事实。

不要因重复确认窗口而改变既有订单状态、Picking 选择、业务数据或 Payload 结构。API10 不适用本机制。

## 验收记录

人工验收人按执行场景记录：API/业务单号、首次及重复点击时间、确认窗口显示内容、选择项、Mock 实际 POST 数量和 Payload、Event/Log 记录 ID、Chatter 决定、PASS/FAIL/BLOCKED。未经实际执行的项目保持 `NOT RUN`；本说明不代填结论。

