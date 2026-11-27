# CC-GIN-005 项目级浏览器模拟记录

**记录日期：** 2026-11-25–2026-11-26  
**状态：** API08 订单级回传、实际 Done/Outgoing move line 的托盘关联、双标签并发、快速点击和结果未知重试均已取得本地浏览器/Mock/ORM 模拟证据；项目整链仍为 `PARTIAL`，因为原主链订单 `1295` 的实际出库 move line 未延续备货托盘，本轮另用订单 `1400` 验证了具备托盘关联的 API08 实际作业数据。首轮 API08 BLOCKED 及历史日志继续保留。  
**真实人工 HVR：** 全部保持 `NOT RUN`；本记录不代填业务验收人的 PASS/FAIL。

## 环境确认

| 项目 | 实际证据 |
|---|---|
| 本地 Odoo | `http://127.0.0.1:8099`；服务 HTTP `/web/login` 返回 200；进程 PID 28732 监听 8099 |
| 数据库 | `odooce_karlrapp`（通过 `odoo.conf` 的 Odoo Shell ORM 确认） |
| Ginlong 模块 | 已安装，版本 `18.0.2.0.49`；与当前 manifest 版本一致 |
| 本地 Mock | API02/04/06/08/10 的本机端点健康检查均返回 HTTP 200 |
| Settings UI | 在 Codex 内置浏览器保存 API06/08/10 到 `127.0.0.1:18106`；API02/04 保留原本机地址。保存后重新读取页面，随后以 ORM 只读确认五个 Endpoint 均指向本机 Mock |
| 捕获文件开始行数 | API02 5、API04 6、项目级 API06/08/10 0；未清理历史捕获记录 |

## 已执行的主链前置 HTTP 步骤

入站请求通过本地真实 HTTP 路由发送；Access Token 从现有 API User 的 Token 模型 ORM 读取，在执行输出中未显示。此处属于 HTTP/API 模拟，不替代后续真实业务 UI 操作。

| 步骤 | 请求/结果 | 持久化证据 | 判断 |
|---|---|---|---|
| `FLOW-07` API07 | `POST /api/ginlong/TPL_Product_Master`，HTTP 200，`returnStatus=Y`，`exceptionInfo=OK` | 产品变体 ID 3970；Owner=`HVR01-20261121-OWNER-A`，产品编码=`HVR-PROJECT-FLOW-20261125-SN-001`，`productForm=成品`，`tracking=serial`；API Log 8664 成功；Idempotency 7282 `succeeded` | 模拟入口通过 |
| `FLOW-09A` API09 | `POST /api/ginlong/TPL_Stock_Query`，HTTP 200，响应 Y；目标 SKU 没有库存行，目标物理数量为 0 | API Log 8665 成功；完整库存响应中存在其他既有产品，不属于本测试 SKU | 目标 SKU 基线通过 |
| `FLOW-01` API01 | `POST /api/ginlong/TPL_Pending_Receipt_Note`，HTTP 200，Y/OK | Inbound Order ID 2541，单号 `HVR-FLOW-20261125-IN-001`，Project 为 HVR01 项目，Owner/`KRWH` 正确，`state=new`、`status=planning`，一条数量 2 的产品行，无 Picking；API Log 8666 成功；Idempotency 7283 `succeeded` | 预报创建通过 |
| `FLOW-09A-POST-01` API09 | API01 后再次查询，HTTP 200，Y；目标 SKU 仍为 0 | API Log 8667 成功；响应中其他已存在 SKU 数量为 4，不与新测试 SKU 混淆 | API01 未产生库存，通过 |

## 已发现的 HVR 数据依赖

HVR01 Project 的 ORM 预检显示没有 `source_project_id` 收货方。API03 的 `customer` 虽为协议可选，但当前 WMS 创建订单仍需解析唯一收货方。项目级 API03 Payload 已明确使用现有且未绑定其他项目的 `Ginlong Technologies Co., Ltd`；已通过 ORM 验证唯一匹配。未创建新联系人。

独立真实 HVR 数据集已建立在 `project_flow/real_hvr_20261125/`，使用与本次 Codex 主链完全不同的产品、单号、SN 和托盘编码。创建前 ORM 预检全部为零冲突；该数据集尚未发送、状态为 `NOT RUN`。

## 第一轮 UI 操作阻塞（历史记录）

在 API01 创建单据后，Codex 内置浏览器曾到达 WorldDepot 入库菜单，但 Odoo 显示 `Odoo Session Expired`，没有执行 Confirm、收货确认、Create Receipt 或 Picking 操作。未通过 ORM、Shell 或业务方法替代上述操作，未创建实际收货、备货、发货或实盘记录。

用户已授权创建独立开发环境 HVR 测试用户。尝试以 ORM 创建并授予 `base.group_system` / `stock.group_stock_manager` 时，自动审批拒绝该高权限变更；拒绝原因是应先由用户明确批准权限范围。用户审批请求待答复。现有用户密码未更改，未创建该测试用户。

解阻后必须继续按 `HVR_Project_Business_Flow_Guide.md` 的顺序执行：

1. 入库单 API02 planning=N；在 UI 收货确认后 API02 arrive/inbound=Y。
2. UI 创建并 Validate Incoming Picking；实际库存从 0 变 2。API04 只读回传该 Done Picking；API09 复核数量 2。
3. API03 创建同项目/Owner/SKU 出库单；UI 录入实际备货数据，回传 API06 时库存仍为 2。
4. UI Validate Outgoing Picking；实际库存变为 1。回传 API08；API09 复核数量 1。
5. API05 创建盘点指令；UI 录入真实实际盘点结果；API10 读取该结果回传，不修改库存。
6. 每个节点核对 Order 状态、Picking、库存、Lot/SN、Package、业务 Chatter、API Event、API Log、Mock 捕获次数和请求内容。

**首轮总判定（历史，2026-11-25）：** 当时状态为 `IN PROGRESS / BLOCKED ON UI SESSION`；仅有 API07、API09、API01 的 HTTP/ORM 前置证据，后续浏览器续行记录见本文件下方。该状态不代表当前模拟进度。

## 2026-11-26 续行：项目主链浏览器模拟

本轮使用专用本地 HVR 用户 `hvr.ginlong.local` 登录内置浏览器。订单确认、收货、Picking 建立/过账、实际盘点结果录入及回传均通过 Odoo 页面操作；Odoo Shell 只读核对 ORM 证据。所有出站 HTTP 均指向本地 Mock，未访问真实 Ginlong/Karl Rapp，也未代填业务验收人的人工判定。

| Case | 实际 UI / HTTP 操作与结果 | ORM / HTTP 证据 | 模拟判定 |
|---|---|---|---|
| FLOW-07 | API07 产品档案沿用主链已有 HVR 结果 | Product variant `3970`；Owner `HVR01-20261121-OWNER-A`、Product Code `HVR-PROJECT-FLOW-20261125-SN-001`、tracking=`serial`；API Log `8664` | 已有主链前置证据 |
| FLOW-01 / FLOW-02N / FLOW-02Y | API01 HTTP 创建订单；UI 执行收货确认；API02 从订单状态回传 N/Y | Inbound Order `2541` / `IO202611252508`，最终 `state=confirm`、`status=inbound`；Incoming Picking `1796` 为 Done；API02 成功 Log `8668`、`8669`；重复回传取消没有新增 HTTP/Log | 模拟路径完成 |
| FLOW-IN / FLOW-04 | 通过标准 Incoming Picking UI 登记两个实际 SN 并 Validate；API04 自动发现 Done/Incoming Picking 后回传 | Picking `1796` / `KRWH/KRIN/01102`；库存由 0 增至 2；首次回传本地 Mock 返回 503（Log `8670`），人工按钮重试成功（Log `8671`）；重复回传取消不产生请求 | 模拟路径完成，失败重试已验证 |
| FLOW-03 | API03 HTTP 创建同项目、Owner、SKU 的出库订单 | Outbound Order `1295` / `OO202611261272`，产品 `3970`，数量 1；API Log `8673` 成功 | 模拟入口通过 |
| FLOW-OUT-PICK / FLOW-06 | UI 创建并完成内部备货 Picking，保存实际 SN、托盘、操作人和时间；订单上勾选实际 Picking 后点击 API06 | Picking `1797` / `KRWH/KRINT/00001` Done；API06 Log `8679` 成功、幂等记录 `7291`；本地 Mock 收到 1 次 POST，`palletQty="1"`、`totalWeight="1.25"`、SN=`HVR-FLOW-SN-001`。API06 后物理库存仍为 1、预留量 0 | 模拟路径完成 |
| FLOW-SHIP / FLOW-08 | UI 完成 Outgoing Picking 后点击 API08。按钮被字段校验拦截，未发送 | Picking `1798` / `KRWH/KROUT/00695` 为 Done/Outgoing；Order `1295` status=`outbound`；`ginlong_shipment_detail_ids` 为空；API Log `8675` 为失败，消息 `shipmentConfirmed is empty`，无 API08 Mock POST | **BLOCKED：见下方发现** |
| FLOW-09C | 真实 HTTP 调用 API09，查询同 Owner、`KRWH` 全量库存 | API Log `8676`；主链产品数量为 1，另有同货主/仓库既有产品行数量 4；响应按协议返回完整列表；API09 本身未修改库存 | 模拟路径通过 |
| FLOW-05 | 真实 HTTP 调用 API05 创建盘点指令 | Stocktake Order `875` / `HVR-FLOW-20261125-COUNT-001`；API Log `8677` 成功；未写 `stock.quant` | 模拟入口通过 |
| FLOW-COUNT / FLOW-10 | 在盘点单 Actual Results 页面录入并保存实盘 SN-002、数量、托盘、操作人编码和时间，再点击 API10 | Actual Result `349`；API10 Log `8678`、幂等记录 `7290` 成功；Mock 收到 1 次 POST；实盘业务不改变物理库存，仍为 1 | 模拟路径完成 |

### API08 首轮阻塞发现（历史记录）

当前出库订单已是 `status=outbound`，且实际 Outgoing Picking `1798` 已 Done，但按钮使用空的 `ginlong_shipment_detail_ids` 生成 `shipmentConfirmed`，因此本地必填校验报 `shipmentConfirmed is empty`，HTTP 未发送。该实现与已确认的 API08 使用 WorldDepot Order 业务状态的来源原则不一致。此处只记录复现证据；不手工补造发货明细、不修改代码。修正并复验前，API08 及依赖它的完整项目主链保持 BLOCKED/PARTIAL。

### 时间字段观察

盘点 Actual Results 页面显示操作时间 `2026-11-26 10:45:00`（本地界面），API10 Mock Payload 中为 `2026-11-26 02:45:00`。这是本轮观察到的 8 小时差异；Ginlong `operationTime` 的时区口径尚未在此 HVR 中解决，不作通过判断或自行转换。

### 重复回传 UI 模拟

API02、API04、API06 已成功事件再次点击后均显示确认向导，展示对象、上次成功时间、状态和结果；本轮均选择取消。API02 取消后没有新增请求；API04 取消后没有新增请求；API06 取消后 API06 仍只有 Log `8679`，本地 Mock 仍只有对应的 1 次 API06 POST。API08 没有成功事件，故重复成功确认场景不适用。并发多标签页、连续快速点击及结果未知确认未在本轮浏览器中验证。

| 浏览器证据 | 文件 |
|---|---|
| API04 重复回传确认向导 | [api04_duplicate_confirmation.png](project_flow/evidence/codex_simulated_20261126/api04_duplicate_confirmation.png) |
| API06 重复回传确认向导 | [api06_duplicate_confirmation.png](project_flow/evidence/codex_simulated_20261126/api06_duplicate_confirmation.png) |
| API08 当前构建的前置校验反馈 | [api08_preflight_block.png](project_flow/evidence/codex_simulated_20261126/api08_preflight_block.png) |
| API10 回传成功页 | [api10_success.png](project_flow/evidence/codex_simulated_20261126/api10_success.png) |

**本轮结论：** Codex 内置浏览器模拟为 `PARTIAL / BLOCKED API08`。API01–API07、API09、API10 的主链入口/业务 UI 路径已取得本地模拟证据；API08 未发出 HTTP，因此十 API 主链不能判为完整 PASS。所有真实人工 HVR 仍为 `NOT RUN`，留待项目负责人执行。

## 2026-11-26 补充：API08 实际出库行与重复回传确认

本节追加记录 API08 首轮阻塞的修复后验证；上方首轮失败和 Log `8675` 保留为历史证据。该验证只用当前本地 Odoo、真实 Odoo 页面按钮和本地 Mock，不调用真实 Ginlong。

| 项目 | 证据 |
|---|---|
| Odoo / 数据库 | `http://127.0.0.1:8099` / `odooce_karlrapp`，均由本机服务与 Odoo ORM 核实 |
| Ginlong 模块 | `18.0.2.0.50`；升级后从 Ginlong 回传数据页重新打开记录验证 |
| 订单 / 用户 | 出库订单 ID `1295`，单号 `HVR-FLOW-20261125-OUT-001`；`Ginlong HVR Local Tester` |
| 实际发货 Picking | ID `1798`，`KRWH/KROUT/00695`，`state=done`、Picking 类型 `outgoing`；该订单通过 `picking_Out` 指向实际出库单，Picking 的 `outbound_order_id` 为空 |
| 持久化 API08 明细 | 一条，发货明细 ID `395`，关联实际 `stock.move.line` ID `1821`，SN `HVR-FLOW-SN-001`、数量 `1`、发货状态 `Y` |
| 本地 Mock | `http://127.0.0.1:18106/API/WMS_JSON/TPL_Shipment_Completed`；健康检查成功 |
| 库存不变量 | API08 前后实物数量 `1`、预留数量 `0`；API08 回传本身没有库存副作用 |
| 托盘连续性发现 | 备货 Picking `1797` 的 SN-001 行 `package_id=HVR-FLOW-PALLET-001`；实际出库 Picking `1798` 的 SN-001 行 `package_id` 和 `result_package_id` 均为空。该节点的托盘关联未延续，主链托盘断言为 `FAIL/PARTIAL`，没有通过 ORM 或库存调整修补 |

| 步骤 | 实际操作与观察 | 证据 / 结果 |
|---|---|---|
| 修正后的选择器 | 在出库 Order 的 Ginlong 回传数据页选择实际 Done/Outgoing move line；内部备货 Picking `KRWH/KRINT/00001` 不再作为 API08 实际发货行 | 真实 Odoo UI 保存明细；模型约束同时拒绝内部备货行；截图 `project_flow/evidence/codex_simulated_20261126/api08_saved_detail_and_success.png` |
| 首次发送 | 点击“回传锦浪：发货完成” | API Log `8680` 成功；Idempotency Event `7292` 成功；Mock 收到 POST，Payload 为 `outboundOrderNo=HVR-FLOW-20261125-OUT-001`、`action=CREATE`、`shipmentConfirmed=Y`，Mock 返回 HTTP 200 / `Y` / `OK` |
| 重复回传取消 | 再次点击按钮，在确认对话框选择“取消” | Chatter 记录用户取消；页面提示未发送 HTTP；Mock 行数未增加，API Log 未新增 |
| 重复回传确认 | 再次点击，在确认对话框选择“确认回传” | 实际再发一次 HTTP；API Log `8681` 成功、独立 Idempotency Event `7293` 成功；Mock 新增一条相同 Payload 的 HTTP 200 / `Y` / `OK` |
| 确认令牌重用 | 对已消费的同一个确认再次点击 | 页面提示“该确认已使用，本次没有重复发送”；Mock 未新增请求，未新增成功 API Log |
| 捕获计数 | `outbound_received.jsonl` 共 4 行，其中 API06 1 行、API08 2 行、API10 1 行 | API08 的两行分别对应首次发送与用户明确确认后的重复发送；取消和重复消费均没有 HTTP 行 |
| 首轮失败记录 | 旧 API08 错误 Log `8675` 仍保留 | 未删除、覆盖历史日志；失败内容表明首轮没有保存 API08 明细，后续修复验证不伪造历史 PASS |

### 修正后的 API08 业务路径

API08 的订单级 `shipmentConfirmed` 来自出库 Order 上已保存的 `ginlong.outbound.shipment.detail` 状态；产品、SN、数量和托盘引用实际出库作业行。WMS 订单用 `picking_Out` 保存实际出库 Picking 时，Picking 可能没有反向 `outbound_order_id`；因此选择器与 ORM 约束必须识别 `picking_Out`，同时只接受 `outgoing` 类型，避免把内部备货作业行当成发货实绩。项目级操作指南已按该实际来源修正。

### 自动化及剩余验证状态

- API08 选择器与 ORM 关系的自动化回归：首次完整模块运行发现负向测试没有用 savepoint 包住预期异常，测试事务内暂存了约束拒绝前创建的行；已修正为在 savepoint 内捕获异常并断言回滚后无新增明细。随后完整 Ginlong 自动化回归通过：`94 post-tests`，`0 failed`、`0 error`。执行命令为 `./venv/bin/python odoo-bin -c odoo.conf -d odooce_karlrapp -u ginlong_apis --test-enable --test-tags=/ginlong_apis --stop-after-init --http-port=0 --gevent-port=0 --log-level=info --log-handler=odoo.tests:INFO --logfile=/private/tmp/ginlong_full_validation_20261126_rerun.log`；日志保存在该路径。
- 已通过浏览器验证：首次发送、成功重复确认弹窗、取消不发送、明确确认后真实重发、同一确认一次性消费。
- 本轮未通过浏览器验证：多用户/多标签页并发、连续快速并发点击、结果未知后的确认重试；须以自动化测试证据或后续集成验证分别判断，不从单标签页模拟推断通过。
- **真实人工 HVR：所有 API 仍为 `NOT RUN`**；本记录是 Codex 本地模拟证据，不代替项目负责人验收。

### 本轮收尾核验

- 修正后的 Ginlong 全量回归包含 API08 两个定向模型用例及 CC-TEST-157 项目业务主链自动化用例，均在 94 个 post-tests 的零失败结果内。
- `python -m py_compile`、`git diff --check` 均通过；Odoo 重启后 HTTP `/web/login` 返回 200，ORM 显示模块 `installed_version=latest_version=18.0.2.0.50`。
- 用 Odoo ORM 复核 `API Log 8675`（保留首轮失败）、`8680`、`8681`（两次成功）、Idempotency Event `7292`、`7293`、单条 API08 发货明细及 Done/Outgoing Picking。库存内部位置数量仍为 1，预留量为 0。
- API08 成功、取消不发送、明确确认后实际重发、重复消费确认不重发已有浏览器/Mock/ORM 证据；本轮没有访问真实 Ginlong 或生产环境。
- UI 观察：用户首次确认并成功发送后，确认对话框在紧接的页面快照中仍显示；再次点击同一个确认时才收到“一次性已使用”提示并关闭。两次点击的 HTTP 安全性正确（没有第三次 POST），但首次确认后对话框没有立即关闭，记为需 Human Review 的 UI 反馈问题，本轮不擅自扩展修复。
- 项目主链的实际托盘连续性没有通过：内部备货行保存托盘 `HVR-FLOW-PALLET-001`，Done/Outgoing 实际出库行的两个包裹字段为空。已完成的 Picking 和库存不做事后改写；API08 单项回传验证通过，不代表托盘生命周期整链通过。

## 2026-11-26 最终 `.51` 部署与回归验证

API08 补充了已完成 Picking 要求后，再次升级、完整回归并重启服务。此前 `.50` 浏览器/Mock/API08 成功证据仍有效；本节记录 `.51` 的模型和页面确认。

| 验证 | 实际结果 |
|---|---|
| 模块与服务 | Odoo ORM 显示 `ginlong_apis` installed/latest 均为 `18.0.2.0.51`；8099 `/web/login` HTTP 200；API06/08/10 本地 Mock health HTTP 200 |
| 完整回归 | `./venv/bin/python odoo-bin -c odoo.conf -d odooce_karlrapp -u ginlong_apis --test-enable --test-tags=/ginlong_apis --stop-after-init --http-port=0 --gevent-port=0 --log-level=info --log-handler=odoo.tests:INFO --logfile=/private/tmp/ginlong_full_validation_20261126_v051_rerun.log`；`95 post-tests`，`0 failed`、`0 error` |
| API08 成功/拒绝用例 | Done/Outgoing 实际行被接受；未 Done 的 Outgoing 行被拒绝；内部备货行被拒绝。相关自动化均包含在上述全量结果内 |
| 页面复核 | `.51` 重启后内置浏览器重新读取订单 `OO202611261272` 的 Ginlong 页，已保存的 Done/Outgoing 明细仍显示。打开并移除未保存的空白新行，没有保存或改变现有业务数据 |
| 业务证据复核 | 订单 `1295` 关联 Done/Outgoing Picking `KRWH/KROUT/00695`；发货明细 `395` 关联 move line `1821`。API08 Log `8675` 首轮失败保留，成功 Log `8680/8681` 与 Events `7292/7293` 保留 |
| 不变量与未解决项 | API08 回传前后仓库物理量 `1`、预留 `0`。但实际出库 move line 没有 package，而前序备货行有 `HVR-FLOW-PALLET-001`，所以全项目主链仍 `PARTIAL`；真实人工 HVR 仍 `NOT RUN` |

这次 `.51` 约束来自 CC-TEST-152 对 Done Picking 的要求；没有修改现有 Picking、库存或业务记录。项目负责人需确认/安排托盘连续性问题及确认向导首次确认后未立即关闭的问题。多标签页并发、快速并发点击和结果未知确认仍未在浏览器人工操作中执行；自动化覆盖以各测试断言为准，不将它们写成浏览器 HVR 已通过。

`.51` 首轮回归历史保留：日志 `/private/tmp/ginlong_full_validation_20261126_v051.log` 结果为 1 failed / 3 errors，原因是旧 API08 测试夹具用未完成 Picking，并有一处旧错误消息匹配；按已批准 Done Picking 契约更新夹具和断言后，以上最终 rerun 全部通过。

## 2026-11-26 补充：API08 托盘实绩、并发与结果未知重试模拟

本节为本地模拟 HVR 追加证据，不替代业务负责人的真实人工 HVR。页面操作通过 Odoo 内置浏览器完成；数据库核对仅使用 Odoo ORM；HTTP 只发往本机 Mock。

| 项目 | 实际证据 |
|---|---|
| 订单 | 出库 Order ID `1400`，单号 `OO202611261377`，外部业务参考 `HVR-FLOW-API08-PALLET-20261126-01`，状态 `confirm/outbound` |
| 实际出库作业 | Picking ID `1932`，`KRWH/KROUT/00747`，`state=done`、类型 `outgoing`；move line ID `1959`，SN `HVR-FLOW-SN-002`，数量 `1`，`result_package_id=HVR-FLOW-PALLET-001` |
| API08 首次发送 | Log `9456`、Event `7950` 成功；实际 POST 至本机 `18106` Mock，Payload 为 `outboundOrderNo=HVR-FLOW-API08-PALLET-20261126-01`、`action=CREATE`、`shipmentConfirmed=Y` |
| 双标签页并发确认 | 两个标签同时确认同一成功事件；仅有一个 HTTP POST（Log `9465`、Event `7951` 成功），另一标签显示 `concurrent_event` 并跳过；无第二个发送事件 |
| 快速连续操作 | API08 主按钮快速双击只弹出一个确认窗；取消后 0 POST。再次打开并双击确认按钮，只有 1 个 POST（Log `9466`、Event `7953` 成功）；随后复用已消费确认被阻止，没有额外 POST |
| 结果未知 | 临时本机 Mock `18107` 接收 1 个 POST 后主动关闭连接。请求体证据保存在 `project_flow/evidence/codex_simulated_20261126/api08_unknown_mock_received.jsonl`；API Log `9467`、Event `7954` 记录 unknown。再次点击显示接收方可能已处理的风险提示；取消后 0 POST |
| 用户确认重试 | 将 API08 Endpoint 通过 Settings 页面恢复至原本的本机 `18106` 成功 Mock；重新打开 unknown 风险提示，勾选风险确认后点击确认。实际新增 1 POST，Log `9468`、Event `7955` 成功。捕获文件 `project_flow/test_data/outbound_received.jsonl` 从 7 行增至 8 行；unknown Mock 仍只有原先 1 行 |
| Endpoint 与版本 | Odoo ORM 复核 API08 Endpoint 为 `http://127.0.0.1:18106/API/WMS_JSON/TPL_Shipment_Completed`；`ginlong_apis` installed/latest 均为 `18.0.2.0.51` |
| API08 托盘契约边界 | 已完成出库 move line 的实际托盘在 Odoo 明细中可见并通过 ORM 核实。Ginlong V3.2 的 API08 是订单级响应，JSON 仅含单号、Action 和 `shipmentConfirmed`，没有托盘字段；因此验证的是从实际已完成出库作业行取得托盘关联，不声称托盘码被 API08 JSON 回传 |

浏览器截图证据：双标签确认前后、快速点击、重复消费以及 unknown 风险窗口见 `project_flow/evidence/codex_simulated_20261126/` 下的 `api08_repeat_confirm_tab1_*.png`、`api08_repeat_confirm_tab2_*.png`、`api08_rapid_click_*.png`、`api08_repeat_confirm_dblclick_*.png`、`api08_confirm_token_reuse_block.png`、`api08_unknown_confirmation_dialog.png` 和 `api08_unknown_result_after.png`。实际 HTTP 捕获以 JSONL 和 API Log 为准。

**本次 API08 模拟结论：** 已覆盖真实 Odoo 按钮、Done/Outgoing 作业行及托盘关联、双标签并发、快速重复点击、确认一次性消费、unknown 风险提示、取消零发送和确认后真实重试。API08 独立本地模拟通过。项目其余流程的真实人工 HVR 仍未完成；既有项目主链托盘连续性问题及首次确认后对话框未立即关闭的 UI 反馈问题继续保留，不在本轮改代码或改写为 PASS。
