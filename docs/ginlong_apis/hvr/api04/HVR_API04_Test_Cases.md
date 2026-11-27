# API04 入库完成人工 HVR 实例

> **项目级主线：** 完整流程使用[项目级 HVR 指南](../HVR_Project_Business_Flow_Guide.md)中的 API01 入库订单及其实际 Done/Incoming Picking；API04 从实际 move lines 取数，不读取 API01 预报代替实绩。API04 POST 必须由 Odoo 按钮触发。

本包只验证 Odoo 实际回传按钮和本机 Mock；不手工 POST API04 Payload，不操作真实 Ginlong。

## 公共准备

1. 使用 API01 真实 HTTP 入口创建全新 Inbound Order。使用有效 owner、已有 productCode 和未使用 inboundOrderNo；避免重发已成功单号。
2. 在现有 WMS 流程中创建收货作业。由业务验收人实际完成 Incoming Picking；不要用 ORM/SQL 人为改 Picking state，也不要手工写库存台账。
3. 管理员在 Odoo 配置 API04 Callback URL 指向本机 Mock。启动方法见同目录 README。
4. 在订单上打开 Ginlong APIs Tab。系统应只展示 API04 按钮及只读最近结果，不出现 Picking 选择控件或 JSON 编辑器。

## HVR-API04-01：单张 Picking 回传

### 前置数据

API01 创建一个订单，订单已通过现有 WMS 流程完成一张 incoming Picking。Picking state 为 done，日期和实际确认人已存在，至少有一条实际 move line，产品、SN/数量和托盘数据符合 API04 必填契约。

### 操作

1. 在该入库订单页面核对 Reference 与 Picking 关联。
2. 点击表单上的“回传锦浪：入库完成”。
3. 查看 Odoo 通知、API 日志和 Mock 捕获文件。

### 预期

- Mock 收到恰好一条 POST，路径为 /API/WMS_JSON/TPL_Inbound_Completion，Content-Type 为 application/json。
- 请求 action=CREATE，inboundOrderNo 为该订单号。
- snList 的产品、productSN、quantity、palletCode 来自该 Picking 的实际 move lines；operator 来自该 Picking 实际确认人，operationTime 来自 date_done。
- Odoo 有 Picking 来源的成功 Event 和 API Log，页面只读区域显示最近成功与时间。
- API01 预报 snList 不进入本次 Payload；回传不改变 Picking、move line 或库存。

人工记录：Order ID/Reference ____；Picking ____；Mock 行 ____；API Log ID ____；实际响应 ____；结论 ____。

## HVR-API04-02：两张 Picking 按批次回传

### 前置数据

同一入库订单通过现有 WMS 作业形成两张不同的 Done/Incoming Picking，每张均有自己的实际 move lines、实际确认人和 date_done。

### 操作与预期

1. 在订单页点击一次 API04 按钮。
2. Mock 应分别收到两条 POST，每条只含对应单张 Picking 的 SN/作业明细；检查两张来源 Picking 各自有独立 Event 与 API Log。
3. 在原订单页再点击一次。预期打开通用重复回传窗口，默认选择“仅回传未成功项”；由于两张 Picking 均成功，确认该默认范围时不会新增 HTTP。选择“回传全部”并确认，才会对两张已成功 Picking 各真实 POST 一次；选择“取消”则零发送。确认框中应显示 Picking、上次成功时间和安全响应摘要。若已有用户/标签页正在发送同一 Picking 事件，本次点击应被服务端协调拦截，不发第二次 HTTP，也不弹出此历史成功确认窗口。

外部 Ginlong 是否接受同一订单号的多次 CREATE 尚待真实联调；本场景只判定本地项目行为及 Mock 结果，不代表外部协议已通过。确认重发需追加子 Event、关联原成功 Event、追加真实 HTTP API Log，并在订单 Chatter 留下用户决定。

人工记录：Order ____；Picking A/B ____；首次 Mock 行 ____；重按前/后行数 ____；Event/API Log ID ____；结论 ____。

## HVR-API04-03：失败后人工重试

### 前置数据

准备一张新的 Done/Incoming Picking。管理员重启本机 Mock 时可设置 `--fail-first 1`，让 Mock 第一次返回 HTTP 503 且 JSON 明确含 `returnStatus=N`，第二次返回标准三字段成功响应。由于第一次响应明确为 N，属于可直接人工重试的明确失败。

### 操作与预期

1. 点击订单的 API04 回传按钮。预期首条尝试明确失败，Odoo 显示失败，API Log 记录 503 和 `returnStatus=N`。
2. 不修改历史 API Log。用户再次点击时不应弹未知结果风险窗口，而是直接实际发送重试。
3. 第二次点击后 Mock 返回成功；预期追加新的成功 API Log，同一 Picking/Event 身份保持稳定，首次失败日志仍可查询。

人工记录：Order ____；Picking ____；第一次响应/日志 ____；第二次 Mock 行/日志 ____；结论 ____。

## HVR-API04-04：不合格 Picking 排除

准备以下记录：当前订单关联但未 Done 的 Incoming Picking；当前订单关联的 Done/Outgoing Picking；另一个订单的 Done/Incoming Picking。点击当前订单 API04 按钮，Mock 报文不得包含任何上述记录。若当前订单完全没有合格 Picking，则不得发送 HTTP，应显示明确失败且生成 API Log。操作前后核对订单、Picking、库存没有因回传而变化。

人工记录：目标订单 ____；不合格 Picking ____；Mock 行数前/后 ____；API Log ID ____；结论 ____。
