# API04 入库完成人工 HVR 测试计划

## 1. 目的与边界

本指南供 CC-GIN-009 关闭后，按原项目验收流程由业务负责人进行 API04 人工验证。实际入库作业由现有 Odoo WMS 记录到 stock.picking / stock.move.line；Codex 不模拟或代替人工仓库操作。所有回传经 Odoo 订单按钮发送至本机 Mock，不访问真实 Ginlong。

API04 只读取当前 inbound.order 关联且 state=done、picking_type_id.code=incoming 的 Picking。系统自动查找，不让用户选择 Picking。每张 Picking 是独立发送批次和 API Event；同 Payload 已成功时由通用确认窗口决定重发或取消。明确收到 `returnStatus=N` 的失败可直接人工重试；发送后超时、无明确 `N` 的 HTTP 错误及无效/不完整响应属于结果未知，须显式确认风险。若另一用户/标签页正在发送同一 Picking 事件，本次不发送且不弹历史成功确认。

## 2. 固定参数

| 项目 | 值 |
|---|---|
| Method / Content-Type | POST / application/json |
| Ginlong Object ID | TPL_Inbound_Completion |
| 本地 Mock Path | /API/WMS_JSON/TPL_Inbound_Completion |
| 默认本地 Mock URL | http://127.0.0.1:18104/API/WMS_JSON/TPL_Inbound_Completion |
| API 来源 | 当前 inbound.order 关联的 Done/Incoming Picking 和实际 move lines |
| Action | CREATE |
| 外部协议 | Ginlong 是否接受同订单多张 Picking 分别 CREATE，仍待 CC-GIN-006 真实联调 |

## 3. 执行前条件

1. 使用未被旧 HVR 占用的 API01 入库订单号，通过 API01 创建订单；订单和产品明细须由 API01 创建，不要 Backend New 手工建单。
2. 按 WMS 现有流程确认订单、建立收货作业，并由验收人/仓库业务人员完成实际 Incoming Picking，使其状态为 Done。完成动作将实际确认人记录在 Picking 级字段；时间使用 date_done。
3. 至少准备一张 Done/Incoming Picking。多批次测试需同一订单有两张不同的 Done/Incoming Picking。
4. 管理员启动本地 Mock，并使用 API04 的 ORM Endpoint 配置脚本设置临时地址。配置前备份当前 Endpoint；若备份文件已存在，不得覆盖。
5. 人工确认人登录 Odoo Backend；Codex 不触发回传按钮、不填验收结果。

## 4. 覆盖矩阵

| 顺序 | HVR | 操作概要 | 主要断言 |
|---|---|---|---|
| 1 | HVR-API04-01 | 一张符合条件的 Picking，订单页点击 API04 | 一次 POST；Payload 取该 Picking 实绩 |
| 2 | HVR-API04-02 | 同订单两张符合条件的 Picking | 每张 Picking 一个请求和 Event；各自 SN 行不串批 |
| 3 | HVR-API04-03 | 成功后再次点击，并分别确认全量重发/取消 | 决策前无 HTTP；确认全量才实际重发，取消零发送 |
| 4 | HVR-API04-04 | 临时 Mock 首次返回明确 N，之后成功 | 明确失败可直接再次点击；首次日志保留并追加成功日志。若无明确 N 的 503/异常，则需先确认 unknown 风险 |
| 5 | HVR-API04-05 | 当前订单无 Done/Incoming Picking | 不发 HTTP；订单、Picking、库存不变化；记录明确失败日志 |
| 6 | HVR-API04-06 | 当前订单存在未完成/Outgoing，或其他订单有 Done/Incoming | 非合格 Picking 不进入 Payload |

所有场景初始 NOT RUN。执行时记录订单、Picking、Mock 行和 API Log ID；不要直接用 curl 向 API04 Mock 发送业务 JSON。
