# API02 / API04 Codex 浏览器模拟记录

> 本记录只记录 Codex 在 Codex 内置浏览器中完成的本地业务模拟，不能替代项目负责人真实人工 HVR。不得访问真实 Ginlong。

## 模拟基线

| 项目 | 值 |
|---|---|
| Odoo URL | `http://127.0.0.1:8099/odoo` |
| 数据库 | `odooce_karlrapp` |
| 模块版本 | `ginlong_apis 18.0.2.0.48`、`worlddepot 18.0.0.5`；本次升级后 Odoo Shell ORM 核实 installed/latest 一致 |
| API02 Mock | `127.0.0.1:18102`；执行前已有捕获 2 行，保留历史 |
| API04 Mock | `127.0.0.1:18104`；执行前已有捕获 2 行，保留历史 |
| 模拟订单 | API01 本地 HTTP 已创建 `SIM-GIN010-IN-20261125-01`，ORM ID 2002；专供 Codex 模拟，不供人工 HVR |
| 认证信息 | 不写入本记录；需由用户在浏览器自行完成登录 |

## 浏览器会话状态

| 检查 | 结果 |
|---|---|
| 内置浏览器 Tab | 当前 IAB tab 3 为 `/web/login` 的 invalid CSRF 提示；tab 5 保留模拟订单页 |
| 首次页面快照 | 原 Tab 3 为 Odoo `Session expired (invalid CSRF token)`；未输入凭据 |
| 用户接管 | 用户确认已登录；Codex 通过 Odoo 应用菜单进入 WorldDepot → Inbound → Orders，确认列表可见；查找模拟订单时页面弹出 `Odoo Session Expired` |
| 订单列表证据 | 搜索/列表快照出现 `SIM-GIN010-IN-20261125-01`（模拟单），之后建立的人工订单单独使用 ID 2011；未打开或修改订单记录 |
| 回传页检查 | 已通过 UI 打开模拟订单的 Ginlong 回传数据页；看到 API02/API04 按钮和只读结果字段。订单 `state=New`、`status=Planning`，无关联 Picking |
| Container No 可选修正 | 经批准移除订单确认及 Picking 创建入口的 Container No 拦截；柜号缺失时以订单编号保持托盘/批次命名可追溯。Odoo Ginlong 套件验证覆盖无柜号确认及建 Picking，0 failed、0 error |
| API02 首次按钮尝试 | 点击“回传锦浪：收货确认”时 Odoo 表单校验返回 `Invalid fields: Arrival Date`；按钮 RPC 被表单校验拦截，没有 Mock HTTP 请求，也没有生成回传成功结果 |
| 补齐测试单字段 | 在模拟单 Main 页通过 UI 填写 `Arrival Date=2026-11-25` 并按 Enter 提交控件；两次点击“Save manually”均弹出 `Session expired`。随后通过 Odoo ORM 核实 `a_date=False`，`write_date` 仍为创建时值；该日期没有持久化。当前浏览器保留未保存输入，但服务端业务数据未改变 |
| API02/API04 回传与 WMS 操作 | 未收到 API02 Mock 请求；未点击重复回传确认/取消、收货确认、Create Receipt 或 Validate。API02 Payload/向导和 API04 实际 Picking 回传均未验证 |
| 当前会话 | 保存失败截图证据为 [CC-GIN-010-session-expired-arrival-date-20261125.jpg](../../implementation/CC-GIN-010-session-expired-arrival-date-20261125.jpg)。服务重启后旧 Cookie 在 `/web/login` 返回 invalid CSRF；重新进入 `/odoo` 后现为有效登录表单，tab 3 已交还用户认证。未读取或输入凭据；没有修改 Administrator 或普通用户密码 |
| 模拟结论 | **BLOCKED / NOT RUN**，原因是页面操作中会话失效；不得视为失败或 PASS |

## 第一轮中断时未完成的浏览器场景（历史记录）

会话恢复后，仅用模拟订单完成以下动作，并在每项记录前后 Mock 捕获行数及 Odoo Event/Log：

| 顺序 | 动作 | 必须记录的行为证据 | 状态 |
|---|---|---|---|
| 1 | 打开订单的 Ginlong 回传数据页 | API02/API04 按钮位置、可用/禁用状态、显示字段 | 第一轮 NOT RUN；第二轮已模拟 |
| 2 | 点击 API02 首次回传 | 是否直接发送、页面成功反馈、Mock 新增行、Payload、API Event/Log | 第一轮 NOT RUN；第二轮已模拟 |
| 3 | 再点 API02，先取消后重新打开并确认 | 向导历史摘要、取消零发送、确认后单次真实 POST、最新状态重读 | 第一轮 NOT RUN；第二轮已模拟 |
| 4 | 按现有 WMS UI 建立并完成实际 Incoming Picking | Order/Picking 关联、Done 状态、实际 SN/托盘/数量；不直接写 ORM 数据 | 第一轮 NOT RUN；第二轮已模拟 |
| 5 | 点击 API04 首次回传 | 自动扫描合格 Picking、真实 Mock POST、Payload 来源和页面反馈 | 第一轮 NOT RUN；第二轮已模拟 |
| 6 | 同一 Picking 再点，分别取消和确认 | 取消无发送；确认真实再次 POST；Event/Log 追加 | 第一轮 NOT RUN；第二轮已模拟 |
| 7 | 连续点击/另开标签页同时点击同一事件 | UI loading/disabled；服务端不并发发送；Mock 请求次数 | NOT RUN |
| 8 | 如果可控地遇到明确失败或 unknown | 明确失败直接重试；unknown 风险确认前零新增发送，确认后恰一次 | NOT RUN |

## 执行记录

| 时间 | 页面/动作 | Mock 行数前→后 | API Event / Log | 实际反馈 | 结果 |
|---|---|---|---|---|---|
| 第一轮中断 |  | 2 / 2 |  | 到货日期保存遇 Session expired，保留原 BLOCKED 证据 | BLOCKED（历史） |

## 第二轮浏览器模拟（2026-11-25）

本轮在用户完成浏览器登录后继续执行。`Arrival Date` 设为与 `Order Date` 相同的 `2026-11-25`，保存成功并通过 ORM 复核；该日期组合可正常确认和收货。所有请求均由 Odoo 页面按钮发送到本机 Mock，不是人工 HVR，也不访问真实 Ginlong。

| 项目 | 实际结果 |
|---|---|
| 模拟订单 | `SIM-GIN010-IN-20261125-01`，Inbound Order ID `2002`；开始时 `state=new`、`status=planning`、无 Container No、无 Picking |
| 回传页 | 通过浏览器打开“Ginlong 回传数据”页；API02、API04 按钮和只读结果区可见 |
| API02 planning 首发 | Mock 行数 `2→3`；真实 POST `UPDATE`、`receiptConfirmed=N`；API Log `6859`，Event `5721`，Mock 返回 Y/OK |
| 标准收货流程 | 选择 `KarlRapp-WH: Receipts` 并保存；订单 Confirm；从订单点击 Create Receipt；通过标准 Picking 页面 Mark as Todo、生成 SN、分配目标托盘并 Validate。未直接写 ORM 或库存模型 |
| API02 收货状态更新 | 收货确认后订单 `state=confirm`、`status=inbound`；点击 API02 真实 POST `receiptConfirmed=Y`。Mock 行数 `3→4`；API Log `6860`、Event `5722`，成功 |
| API04 实际来源 | Picking `KRWH/KRIN/00926`，ID `1508`，`state=done`、Incoming、`date_done=2026-11-25 06:45:28`；两条 SN 各数量 1，均属于产品 `HVR01-20261122-PROD-SERIAL` 和托盘 `SIM-GIN010-IN-20261125-01-0001`。货主为 HVR 测试货主，实际确认人为 Administrator |
| API04 首发 | 点击订单上的 API04 按钮后自动扫描该 Done/Incoming Picking 并实际 POST。Mock 行数 `2→3`；API Log `6861`、Event `5723`，Mock 返回 Y/OK |
| API04 重复取消 | 再次点击显示成功时间、结果及 Picking 名称；选择取消后提示“已取消，本次没有发送 HTTP 请求”。Mock 行数保持 `3`；Chatter 记录 `16731` |
| API04 重复确认 | 重新打开后确认回传，Mock 行数 `3→4`，真实 POST 第二次相同业务 Payload；API Log `6862`、Event `5724`（关联 Event `5723`），Chatter 记录 `16732` |
| API02 重复确认 | 对已成功的 Y Payload 打开确认；取消分支无 POST，之后确认分支实际 POST。Mock 行数 `4→5`；API Log `6863`、Event `5725`，Chatter 分别记录取消 `16733`、确认 `16734` |
| 一次性消费 | 确认按钮第二次点击提示“该确认已使用，本次没有重复发送”；API04、API02 Mock 行数均未增加，未产生第三次重复请求 |
| API04 明确失败 | 重启本机 Mock 并启用 `--fail-first 1` 后，经成功事件确认窗口再发送；Mock 行数 `4→5`，HTTP 503 / `returnStatus=N` / `MOCK01: temporary failure`；API Log `6864`、失败 Event `5726` |
| API04 失败重试 | 关闭失败尝试留下的向导后再次点击 API04，失败状态允许直接重试；无重复确认窗口，实际 POST 成功。Mock 行数 `5→6`；API Log `6865`、成功 Event `5727`（关联失败 Event `5726`） |
| 最终业务状态 | ORM 核实 `date=a_date=2026-11-25`、`state=confirm`、`status=inbound`、只关联 Picking `1508`。库存记录来自标准 Picking Validate |
| Container No | 模拟订单 Container No 为空；订单 Confirm、Create Receipt、Picking Validate 均通过，托盘/批次名使用订单编号保持可追溯 |
| 本地 Mock 增量 | API02 `2→5`（3 次 POST：N、Y、用户确认重发 Y）；API04 `2→6`（4 次 POST：首次、确认重发、明确失败、失败后重试）。历史 JSONL 行保留 |
| 人工 HVR 环境交接 | API02 捕获文件当前 5 行；API04 捕获文件当前 6 行，历史和模拟记录均保留。API04 Mock 已重新启动并重置仅进程内的 `fail-first=1`，所以真实人工 HVR 的下一次 API04 POST 将收到一次性 503，之后重试返回成功 |
| 浏览器证据 | [第二轮模拟结束页面](../../implementation/CC-GIN-010-browser-api02-api04-simulation-20261125.png) |

### 模拟发现及未覆盖项

- 首次确认重复回传后，HTTP 请求与成功通知已发生，但确认对话框仍短暂留在页面；再次点击同一向导的确认按钮时，一次性消费保护阻止第二次 HTTP，并返回“该确认已使用”后关闭。实际请求次数正确，但第一次确认后立即关闭对话框的 UI 行为未达到预期。按“不擅自修改业务代码”的授权边界，本轮记录为发现项，不自行修复。
- 本轮未执行并发多标签页、连续快速点击和 unknown 风险确认，因此仍为 `NOT RUN`；不得宣称重复回传完整项目 HVR 通过。
- 本轮结论仅为 **Codex 浏览器模拟：API02/API04 的成功、状态变化、取消及确认重发路径已执行；整体验收 PARTIAL**。项目负责人真实人工 HVR 仍待执行，人工记录不得填 PASS。

## API08 并发及 unknown 结果浏览器模拟补充（2026-11-26）

下列是随后补做的本地 Codex 浏览器模拟，更新本文件较早部分的 `NOT RUN` 记录；不更改业务负责人 HVR 表格，真实人工状态仍为 `NOT RUN`。

| 场景 | 页面操作 | 实际 HTTP / 事件证据 | 结果 |
|---|---|---|---|
| 双标签页同时确认 API08 成功事件 | 两个浏览器标签打开同一出库 Order 的 API08 重复回传向导，同时确认 | 仅 1 次 Mock POST；Log `9465`、Event `7951` 成功。另一标签返回 `concurrent_event` 并跳过 | 本地模拟通过 |
| 主按钮快速双击 | 连续双击“回传锦浪：发货完成” | 仅出现一个确认窗；取消后 HTTP 增量为 0 | 本地模拟通过 |
| 确认按钮快速双击及 token 复用 | 确认一个重复回传向导后立即再点同一确认 | 只新增 1 次 POST（Log `9466`、Event `7953`）；同一确认再次使用被拒绝，没有额外 HTTP | 本地模拟通过；首次发送后对话框未立即关闭仍是 UI 反馈问题 |
| unknown 风险取消 | 临时本机 Mock `18107` 接收请求体后关闭连接，不返回响应；再次打开向导后取消 | 请求被记录为 unknown（Log `9467`、Event `7954`）；取消没有发出第二个 POST | 本地模拟通过 |
| unknown 风险确认后重试 | 通过 Odoo Settings 页面将 Endpoint 恢复为 `18106`，在风险对话框勾选确认并发送 | 本机成功 Mock 捕获行从 7 增至 8；Log `9468`、Event `7955` 成功。临时 unknown Mock 仅捕获最初的 1 次请求 | 本地模拟通过 |

测试对象为出库 Order `OO202611261377`（ID `1400`），完成 Picking `KRWH/KROUT/00747`（ID `1932`）。实际 move line `1959` 有 SN `HVR-FLOW-SN-002`、数量 `1`、`result_package_id=HVR-FLOW-PALLET-001`。V3.2 API08 是订单级确认，Payload 只含订单号、`CREATE`、`shipmentConfirmed=Y`，不含托盘字段。ORM 确认 `ginlong_apis` 为 `18.0.2.0.51` 且 API08 Endpoint 已恢复到 `http://127.0.0.1:18106/API/WMS_JSON/TPL_Shipment_Completed`。unknown Mock 接收的请求另存为 `project_flow/evidence/codex_simulated_20261126/api08_unknown_mock_received.jsonl`；捕获和事件细节见 [项目浏览器模拟记录](HVR_Project_Browser_Simulation_Record.md)。

这只补齐 API08 本地重复回传交互模拟，不代表 API02/04/06/08 所有混合多事件场景或 API01–10 整体主链通过；项目负责人真实人工 HVR 仍按原表保持 `NOT RUN`。
