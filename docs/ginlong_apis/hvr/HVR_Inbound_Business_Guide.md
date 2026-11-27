# API01 → API02 → API04 入库业务人工 HVR 指南

> **项目主线数据集已更新：** 本文件原来使用的 `HVR-GIN010-MANUAL-IN-20261125-01` 和 `HVR01-20261122-PROD-SERIAL` 只保留为旧入库专项参考，不能并接 API03/API05/API09。项目级统一数据、API01 Order、实际出入库和盘点顺序以[《Ginlong 项目级仓库业务流程 HVR 指南》](HVR_Project_Business_Flow_Guide.md)为准。不要混合两个数据集的单据、库存、Picking 或 Mock 行。

## 1. 目的与执行门槛

本指南把 API02、API04 原有独立操作说明合并为一条完整入库业务流程。它验证 API01 创建的实际入库订单、订单级收货确认、分批实际入库 Picking，以及 Odoo 回传到本机 Mock 的结果。

**执行门槛：** CC-GIN-009、CC-GIN-010 已按各自关闭记录完成；本指南现在供项目级本地 Mock HVR 使用。真实 Ginlong 联调仍需后续单独授权。

执行人亲自发送 API01、操作入库单和 Picking、点击 API02/API04 回传按钮、检查 Mock 与 Odoo 记录，并填写 PASS / FAIL。Codex 不代做业务操作，不代填人工结论。

本地测试只访问 `127.0.0.1`，不访问真实 Ginlong、生产环境或 Karl Rapp Gateway。

## 2. 当前准备状态

| 项目 | 准备结果 |
|---|---|
| Odoo Backend | `http://127.0.0.1:8099/odoo`；本次受控重启后 `/web/login` 返回 HTTP 200 |
| Odoo 数据库 | `odooce_karlrapp` |
| ginlong_apis / worlddepot | 本次升级后 Odoo Shell ORM 核实 `18.0.2.0.48` / `18.0.0.5`，installed_version 与 latest_version 一致 |
| API02 Mock | `http://127.0.0.1:18102/API/WMS_JSON/TPL_Receipt_Confirmation`；仅监听 loopback；捕获文件已有 5 行，测试比较增量 |
| API04 Mock | `http://127.0.0.1:18104/API/WMS_JSON/TPL_Inbound_Completion`；仅监听 loopback；捕获文件已有 6 行；当前进程已重新启用首个 POST HTTP 503、后续成功，测试比较增量 |
| API02 Endpoint | 现有配置已指向本机 API02 Mock；原未配置状态保存在权限受限的备份文件 |
| API04 Endpoint | 已通过 Odoo Shell ORM 备份原值并临时指向本机 API04 Mock |
| Codex 模拟单据 | `SIM-GIN010-IN-20261125-01`，仅作 Codex 模拟；不得用于人工 HVR |
| 独立人工 HVR 单据 | Reference `HVR-GIN010-MANUAL-IN-20261125-01`；Order ID `2011`；Bill No `IO202611251978`；由本机 API01 创建，尚无 Picking |
| HVR 判定 | 所有场景初始 `NOT RUN`；不得把 Mock 健康检查或本指南准备工作记作 HVR PASS |

API01 认证用户应关联现有 `HVR01-20261121 API01 HVR Project` 项目。执行前使用当前有效的本地 API Token；按当前接口实现将 Token 原样放在 `Authorization` Header，**不要加 `Bearer` 前缀**。不要把 Token 写入 Payload、文档或执行记录。

若需要重新获取本地 Token，可向现有认证入口提交当前 API User 的 key/secret（在本机安全填写占位符，不要把密钥保存到本指南）：

```bash
curl --request POST \
  --url http://127.0.0.1:8099/world_depot/api/auth/token \
  --header 'Content-Type: application/json' \
  --data '{"api_key":"<本地 API Key>","api_secret":"<本地 API Secret>"}'
```

从响应读取 `access_token`，有效期为 3600 秒。随后仅在本机 shell 设置 `GINLONG_HVR_TOKEN`，API01 请求直接发送 `Authorization: <access_token>`，不加 `Bearer`。不要将 Token 粘贴到共享截图、Mock Payload 或执行记录。

## 3. 测试数据

### 3.1 固定入库订单

| 字段 | 测试值 |
|---|---|
| inboundOrderNo | `HVR-GIN010-MANUAL-IN-20261125-01` |
| owner | `HVR01-20261121-OWNER-A` |
| warehouse | `KRWH` |
| businessType | `STANDARD` |
| API User 项目 | `HVR01-20261121 API01 HVR Project`（当前 API User 关联项目） |
| productCode | `HVR01-20261122-PROD-SERIAL` |
| 产品 | `HVR01 成品序列号验收产品`，现有变体为 SN 管理，`tracking=serial` |
| specificationModel | `HVR01-SERIAL-MODEL` |
| 订单数量 | 2 台，后续分为两个各 1 台的实际批次 |
| Container No | `HVR-GIN010-MANUAL-CN-01` |
| 实际序列号 | `HVR-GIN010-MANUAL-SN-001`、`HVR-GIN010-MANUAL-SN-002` |

该订单由 Codex 使用本机 API01 入口创建，仅用于项目级人工 HVR。ORM 已核实：`state=new`、`status=planning`、一条数量 2 的 `tracking=serial` 产品行、无 SN 预报明细及无 Picking。不要再次发送该 Add。`SIM-GIN010-IN-20261125-01` 是独立 Codex 模拟单，不供人工验收。

`Container No` 为可选字段。本次人工数据保留示例值，但可清空后继续；订单确认及创建 Picking 不再要求填写。没有柜号时，系统用订单编号生成可追溯的托盘/批次命名段。

### 3.2 API01 请求报文

创建该人工 HVR 订单所用的请求文件：[独立 API01 Payload](test_data/api01_gin010_manual_inbound.json)。此报文已通过本机 API01 成功提交；后续人工步骤使用现有订单，不要再次 Add。

请求正文：

```json
{
  "owner": "HVR01-20261121-OWNER-A",
  "action": "Add",
  "inboundOrderNo": "HVR-GIN010-MANUAL-IN-20261125-01",
  "warehouse": "KRWH",
  "businessType": "STANDARD",
  "remark": "CC-GIN-010 项目级人工 HVR 专用订单；与 Codex 浏览器模拟数据隔离",
  "details": [
    {
      "productCode": "HVR01-20261122-PROD-SERIAL",
      "productName": "HVR01 成品序列号验收产品",
      "specificationModel": "HVR01-SERIAL-MODEL",
      "quantity": 2
    }
  ]
}
```

此例为 `STANDARD`，不提供 `snList`。API01 只创建客户入库指令，不创建 Picking、Lot、托盘或库存。序列号和托盘只在后续实际 Picking 中记录。

API01 已返回 HTTP 200、`returnStatus=Y`、`exceptionInfo=OK`。人工验收人在 **WorldDepot → Inbound → Orders** 搜索此 Reference，打开 Bill No `IO202611251978`；确认明细 2 台、`state=New`、`status=Planning`、无关联 Picking。若列表暂时没有该单，先查看 API 日志，不要重发同订单号 Add。

## 4. 本地 Mock 查看方式

Mock 只接收 Odoo 实际回传按钮发出的 HTTP POST，不手工向 API02/API04 Mock POST 业务 Payload。

开始 HVR 前，在终端分别检查接收器；健康检查只发 GET，不会生成业务记录：

```bash
curl --fail --silent http://127.0.0.1:18102/__mock__/health
curl --fail --silent http://127.0.0.1:18104/__mock__/health
```

截至 2026-11-25 检查时，两个 Mock 均在 loopback 监听，捕获 JSONL 文件各有 2 条历史行。开始前运行健康检查并记录行数；不要清空文件或重启正在运行的 API04 接收器，否则会重置 fail-first 计数：

```bash
python3 docs/ginlong_apis/hvr/api02/test_data/mock_api02_receiver.py --host 127.0.0.1 --port 18102
python3 docs/ginlong_apis/hvr/api04/test_data/mock_api04_receiver.py --host 127.0.0.1 --port 18104 --fail-first 1
```

API04 `--fail-first 1` 只让本地接收器的首个 POST 返回 503，随后返回成功，供 HVR-IN-04 验证用户手动重试。当前接收器已运行时不要再启动第二份。完成 HVR 后按 §8 恢复 Endpoint，再分别在接收器终端按 `Ctrl-C` 停止服务。

推荐在单独终端运行，观察新的请求及模拟响应：

```bash
tail -f docs/ginlong_apis/hvr/api02/test_data/received.jsonl
```

```bash
tail -f docs/ginlong_apis/hvr/api04/test_data/received.jsonl
```

也可在仓库根目录运行格式化查看器，查看两种 Mock 最近收到的请求和响应：

```bash
python3 docs/ginlong_apis/hvr/test_data/view_inbound_mock_captures.py --tail 10
```

API02 与 API04 的 JSONL 文件分别追加记录；查看记录中的 `method`、`path`、`contentType`、`payload`、`httpStatus` 和 `mockResponse`。Mock 不保存 Authorization、Cookie 等认证 Header。

## 5. 统一业务流程与人工操作

### HVR-IN-01：API01 创建订单，API02 未收货回传 N

**前置数据与页面**

- 使用 §3 的 API01 报文，真实 POST 到 `http://127.0.0.1:8099/api/ginlong/TPL_Pending_Receipt_Note`。
- 进入 **WorldDepot → Inbound → Orders**，按 Reference 打开 API01 创建的单据。
- API01 不包含 Odoo WMS 的 `Arrival Date`，但当前 Inbound Order Form 将其设为必填。先在 Main 页填写 `Arrival Date` 并保存，重新打开/刷新单据确认日期仍显示，再确认 `state=New`、`status=Planning`，尚未执行收货确认且未创建 Picking。`Arrival Date` 可以等于 `Order Date`；本流程没有要求到货日期必须晚于订单日期。此处只补齐 Odoo 单据必填字段，不点 Confirm。若保存时出现 `Session expired`，先重新登录并确认日期已持久化，不能继续回传。

**操作**

确认 `Arrival Date` 已保存后，打开订单的 **Ginlong 回传数据** Notebook 页，点击 **回传锦浪：收货确认**。此场景不要先点表头中的 WMS `收货确认`，也不要创建 Picking。若遗漏必填日期，Odoo 会在表单保存阶段阻止按钮 RPC，Mock 不会收到请求。

**Mock 预期**

```json
{
  "inboundOrderNo": "HVR-GIN010-MANUAL-IN-20261125-01",
  "action": "UPDATE",
  "receiptConfirmed": "N"
}
```

预期 Mock 返回 HTTP 200 与 Ginlong 三字段成功响应；Odoo 显示成功通知，并新增 API02 Event/幂等记录和 API Log。订单 `state`、`status` 不因回传动作改变。

**人工记录：** PASS / FAIL ____；API01 响应 ____；Order ID ____；Mock 捕获行 ____；Event ID ____；API Log ID ____；截图/备注 ____。

### HVR-IN-02：业务收货确认，API02 回传 Y

**操作页面与字段**

仍在同一张 Inbound Order：

1. `Container No` 可留空；如果保留示例值，不影响本场景。
2. 填写 `Arrival Date` 为本次测试日期。
3. 将 `Picking Type` 设为 **KarlRapp-WH: Receipts**。
4. 确认 `Scan Serial Number one by one` 已勾选；该字段默认开启。保存。
5. 点击顶部 **Confirm**。这是现有订单生命周期确认，不是收货状态回传。
6. 点击顶部 **收货确认**。该业务操作应将订单 `status` 改为 `Arrived`，订单 `state` 保持 `Confirmed`。
7. 在 Chatter/跟踪记录核对该状态变化的操作人和时间。
8. 打开 **Ginlong 回传数据** Notebook 页，再点击 **回传锦浪：收货确认**。

**Mock 预期**

```json
{
  "inboundOrderNo": "HVR-GIN010-MANUAL-IN-20261125-01",
  "action": "UPDATE",
  "receiptConfirmed": "Y"
}
```

预期 Mock 收到新的 POST；Odoo 新增对应 Event/API Log，界面显示成功。此时可以尚未存在 Done Picking：API02 的 Y 表示订单业务收货确认，不表示实际入库完成或库存已经过账。

**人工记录：** PASS / FAIL ____；保存后 state/status ____；Chatter 操作人/时间 ____；Mock 捕获行 ____；Event ID ____；API Log ID ____；截图/备注 ____。

### HVR-IN-03：创建实际收货 Picking 并完成第一批

**操作页面与步骤**

1. 回到该 Inbound Order，点击统计按钮 **Create Receipt**。这是现有 WMS 创建收货作业单的入口；不手工 New 一个无关联 Picking。
2. 打开订单的 `Stock Picking` 关联记录，核对 `Inbound Order` 指向当前订单、Picking Type 为 Receipts。
3. 在 Picking 的 **Operations** / 详细作业行中，为两条序列号作业行填写 Lot/Serial Number：
   - 第一行：`HVR-GIN010-MANUAL-SN-001`
   - 第二行：`HVR-GIN010-MANUAL-SN-002`
4. 核对每条序列号作业数量为 1。记录系统生成的 Destination Package 名称；本次 API04 `palletCode` 应取实际 move line 的包裹记录，不要自行编造或改写包裹名。
5. 第一批只实际完成 SN-001：第一行实收数量 1，第二行本批实收数量 0/未选中。点击 Picking 顶部 **Validate**。
6. Odoo 提示是否创建 Backorder 时，选择 **Create Backorder**，保留未完成的 SN-002 作为第二批。不要选择取消剩余数量。
7. 核对第一张 Picking 状态为 Done，关联订单正确，Done 数量 1、SN 为 SN-001；库存变化来自标准 Picking 过账。

> 如果当前界面没有显示可编辑的 Lot/Serial、数量或包裹字段，或 Validate 不能按部分数量生成 Backorder，先停止并记录 UI 状态，不要用 ORM/SQL 或库存调整绕过 WMS。

### HVR-IN-04：API04 首次失败与人工重试（第一批）

API04 Mock 已设置“第一次 POST 返回 HTTP 503，之后成功”。仅对本地接收端生效。

1. 打开订单的 **Ginlong 回传数据** Notebook 页，点击 **回传锦浪：入库完成**。系统自动发现当前订单的 Done/Incoming Picking，无需选择 Picking。
2. 第一次尝试预期 Mock 返回 HTTP 503，并在 JSON 中明确返回 `returnStatus=N`；这属于明确失败，Odoo 显示失败，API Log 及 API Event 保留失败状态，可由用户直接重试。
3. 验证 Mock 第一条 API04 记录：`action=CREATE`、`inboundOrderNo` 为本测试订单、`snList` 只含第一批 SN-001；`productCode`、数量、托盘、操作人和时间来自 Done Picking/move line。
4. 由验收人在同一订单的 **Ginlong 回传数据** Notebook 页再次点击 **回传锦浪：入库完成**。第二次 POST 预期成功；Mock 新增一条记录，仍是第一批 SN-001；Odoo 新增成功 API Log，第一次失败日志保持不变。

Payload 核对结构（`palletCode`、`operator`、`operationTime` 必须与实际记录一致）：

```json
{
  "owner": "HVR01-20261121-OWNER-A",
  "action": "CREATE",
  "inboundOrderNo": "HVR-GIN010-MANUAL-IN-20261125-01",
  "snList": [
    {
      "productSN": "HVR-GIN010-MANUAL-SN-001",
      "quantity": 1,
      "palletCode": "从实际 Done move line 读取",
      "productCode": "HVR01-20261122-PROD-SERIAL",
      "operator": "执行 Validate 的 Odoo 用户 login",
      "operationTime": "该 Picking 的 date_done"
    }
  ]
}
```

**人工记录：** PASS / FAIL ____；Picking ____；第一条 HTTP 状态/Mock 行 ____；失败 API Log ID ____；重试 HTTP 状态/Mock 行 ____；成功 API Log ID ____；Event/尝试次数 ____；截图/备注 ____。

### HVR-IN-05：完成第二批并验证增量发送

**操作页面与步骤**

1. 打开第一张 Picking 生成的 Backorder（从原 Picking 的 Backorder 关联，或在 **Inventory → Operations → Receipts** 按本订单关联记录查找）。
2. 核对它仍关联当前 Inbound Order，剩余作业为 SN-002，数量 1，包裹与实际业务记录一致。
3. 点击 Backorder 顶部 **Validate**，完成第二批实际入库。
4. 回到原 Inbound Order 的 **Ginlong 回传数据** Notebook 页，点击 **回传锦浪：入库完成**。

**Mock 预期**

- API04 对第一张 Picking：原成功批次在向导中列出；默认“仅回传未成功项”跳过该 Picking，只有选择“回传全部”并确认才会重复 POST。
- API04 对第二张 Picking：新增一条 POST，`snList` 只含 SN-002，不包含 SN-001。
- 第二张 Picking 使用自己的 `date_done` 与实际确认人；产品、数量和托盘来自该批实际 move line。
- API Event/幂等记录和 API Log 均能区分 Picking 来源；Odoo 显示本次发送/跳过结果。

**人工记录：** PASS / FAIL ____；第二张 Picking ____；新增 Mock 行 ____；两张 Picking 对应 Event/API Log ID ____；通知 ____；截图/备注 ____。

### HVR-IN-06：成功批次重复回传确认

不修改订单、Picking、SN、托盘或数量，在原 Inbound Order 的 **Ginlong 回传数据** Notebook 页再次点击 **回传锦浪：入库完成**。确认窗口展示每张 Picking 的上次状态、成功时间和响应摘要。

**Codex 浏览器模拟注意事项：** 当前观察到用户确认发送后，页面成功/失败通知已出现，但确认窗口可能仍留在页面。此时不要再次点击“确认回传”，以免造成误解；先关闭该窗口，按 Mock 新行、API Log 和 Event 核对本次是否已经真实发送。一次性确认保护会阻止已消费向导再次发出请求。该 UI 表现尚待项目负责人真实 HVR 核实，不能因此将重复回传场景自动判 PASS。

发送结束通知出现后，若“最近回传成功/时间/错误”只读区域仍显示上一条结果，刷新业务单据并重新打开“Ginlong 回传数据”页，再核对最新 Event、Log 和 Mock 行。Codex 模拟中，API04 明确失败后的重试成功通知即时出现，但只读摘要直到页面刷新才更新为最新成功结果。

选择默认“仅回传未成功项”并确认：两张已成功 Picking 均跳过，Mock 行数不增加。随后重新点击，在窗口选择“回传全部”并确认：Mock 对两张 Picking 分别收到一条真实新 POST；新增两个子 Event 和两条 API Log，原历史记录保留。另开一次窗口选择“取消”：不发送请求，Chatter 记录取消决定。

**人工记录：** PASS / FAIL ____；各次选择 ____；Mock 行数 ____；通知 ____；相关 Event/API Log ID ____；Chatter 决定 ____；截图/备注 ____。

如果另一用户/标签页正在发送某张 Picking，本次点击应不发送且不弹历史成功确认；在用户稍后重新点击后，再按数据库中最新提交的结果显示重复确认或可发送项目。

## 6. API 日志与 Event 检查

在 Odoo Backend 以有权限的管理员打开：

- **WorldDepot → Ginlong APIs → API 日志**：分别按 API02/API04 和订单业务键筛选，检查请求、响应、状态、时间及来源单据。API04 日志应能定位各自 Picking。
- **WorldDepot → Ginlong APIs → 幂等记录**：检查 API02 各订单状态事件及 API04 各 Picking 事件的方向、业务键、状态和尝试次数。
- Inbound Order 的 Ginlong APIs 页面：核对按钮结果只读区显示的最近成功状态、时间或失败信息。
- Inbound Order Chatter：只用于检查“收货确认”业务操作记录，不能用 API Log/Event 代替业务操作日志。

认证 Token 不应出现在 API 日志、Mock 捕获文件或本指南证据中。

## 7. 人工执行记录

| 场景 | 初始状态 | 人工结果（PASS/FAIL/BLOCKED） | Order / Picking | Mock 行 | API Event / Log | 证据链接/备注 |
|---|---|---|---|---|---|---|
| HVR-IN-01 API01 创建订单及 API02 planning→N | NOT RUN |  |  |  |  |  |
| HVR-IN-02 收货确认及 API02 arrive→Y | NOT RUN |  |  |  |  |  |
| HVR-IN-03 第一批 Done Picking | NOT RUN |  |  |  |  |  |
| HVR-IN-04 API04 HTTP 503 后人工重试成功 | NOT RUN |  |  |  |  |  |
| HVR-IN-05 第二批 API04 增量发送 | NOT RUN |  |  |  |  |  |
| HVR-IN-06 成功批次默认跳过、全量确认重发及取消 | NOT RUN |  |  |  |  |  |

### CC-GIN-010 重复回传确认补充场景

下列为项目级 HVR，不是 CC-GIN-010 独立 HVR。详细步骤及 API02/API04/API06/API08 的独立事件单位、Mock 增量、失败/未知结果和连续点击断言见[重复回传确认 HVR 指南](HVR_Callback_Repeat_Confirmation_Guide.md)及[执行记录](HVR_Callback_Repeat_Confirmation_Execution_Record.md)。

| HVR | 场景 | 状态 | Order / Picking | Mock 行增量 | API Event / Log / Chatter | 人工证据 |
|---|---|---|---|---|---|---|
| HVR-REP-01/02 | API02 首次、相同成功 Payload 取消/确认、明确失败/unknown | NOT RUN |  |  |  |  |
| HVR-REP-03/04 | API04 多 Picking 成功/失败/首次混合、默认/全量/取消及跨标签页并发 | NOT RUN |  |  |  |  |
| HVR-REP-05/06 | API06 多 Picking 聚合、重复确认、失败/unknown 重试 | NOT RUN |  |  |  |  |
| HVR-REP-07/08 | API08 订单级重复确认与多标签连续点击 | NOT RUN |  |  |  |  |

Codex 内置浏览器模拟结果单独记录在 [HVR_Callback_Browser_Simulation_Record.md](HVR_Callback_Browser_Simulation_Record.md)，不填入本表的人工结论。

## 8. 环境恢复

项目级人工 HVR 全部结束后，管理员在仓库根目录分别通过现有 Odoo Shell/ORM 恢复 Endpoint；不得直接操作 PostgreSQL：

```bash
./venv/bin/python odoo-bin shell -c odoo.conf -d odooce_karlrapp --no-http < docs/ginlong_apis/hvr/api02/test_data/restore_api02_endpoint.py
./venv/bin/python odoo-bin shell -c odoo.conf -d odooce_karlrapp --no-http < docs/ginlong_apis/hvr/api04/test_data/restore_api04_endpoint.py
```

确认 API02/API04 Endpoint 已恢复原值后，在各 Mock 所在终端按 `Ctrl-C` 停止接收器。保留 JSONL Mock 证据、API Log、Event 和业务记录；不要清理或覆盖历史 HVR 数据。
