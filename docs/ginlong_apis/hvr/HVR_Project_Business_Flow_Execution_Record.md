# CC-GIN-005 项目级真实人工 HVR 执行记录

**本记录用途：** 由项目负责人记录真实人工 HVR。  
**Codex 模拟 HVR：** PASS，Run CC005-FINAL-20261127-01。  
**本记录状态：** 所有负责人判定仍为 NOT RUN；Codex 不代填人工结果。

## 执行环境与主线数据

| 项目 | 执行值 |
|---|---|
| Odoo / 数据库 | http://127.0.0.1:8099/odoo / odooce_karlrapp；开始前由负责人核对 |
| ginlong_apis | 18.0.2.0.56；开始前 ORM 核对 |
| 浏览器用户 | hvr.ginlong.operator；Inventory / User、Project / User |
| API User | 项目 HVR-GIN005 project 下的 hvr.ginlong.operator；使用新 Token，不记录凭据 |
| Owner / Warehouse / Project | HVR-GIN005-OWNER / KRWH / HVR-GIN005 project |
| Customer | HVR-GIN005 recipient |
| 入库 / 出库 / 盘点号 | HVR-REAL-20261128-IN-01 / HVR-REAL-20261128-OUT-01 / HVR-REAL-20261128-COUNT-01 |
| 产品 | HVR-REAL-20261128-FG / HVR-REAL-20261128-SF / HVR-REAL-20261128-RAW |
| Mock | API02 18102；API04 18104；API06/API08/API10 18106 |
| Mock 捕获起始行号 | 执行前填写 |
| 执行人 / 开始时间 | 执行时填写 |

数据文件只使用 project_flow/real_hvr_20261128/payloads。若产品、单号、SN、托盘、API 幂等业务键与现有记录冲突，停止并整体更换数据后缀；不得删除历史数据。

## 验收步骤和记录

| 顺序 | Case | 动作 | 预期关键结果 | 人工判定 | 时间/证据 |
|---:|---|---|---|---|---|
| 1 | API07 | 依次发送 api07_01_fg.json、api07_02_sf.json、api07_03_raw.json | 三个 owner 产品建立；FG/SF serial，RAW none；无库存 | NOT RUN | — |
| 2 | API09-A | 发送 api09_opening.json | 本轮三个 SKU 初始物理库存均为 0；查询只读 | NOT RUN | — |
| 3 | API01 | 发送 api01_inbound.json 并打开新入库订单 | 三产品及预报正确；无 Picking、Lot、实际 Package、库存 | NOT RUN | — |
| 4 | API02-N | 入库单 Ginlong 回传数据页点击收货确认回传 | Planning 对应 receiptConfirmed=N；Mock 收到一次 POST | NOT RUN | — |
| 5 | 收货确认 | 执行同一订单现有收货确认操作，核对业务状态和操作日志 | status=arrive/inbound；无库存变化 | NOT RUN | — |
| 6 | API02-Y | 再点击收货确认回传 | receiptConfirmed=Y；Mock 收到一次新 POST | NOT RUN | — |
| 7 | 一步入库 | 选择 Receipts，只创建一张 Incoming Picking；按三托盘录入 FG4/SF2/RAW12 并 Validate | Picking Done；此处唯一增加库存的操作 | NOT RUN | — |
| 8 | API04 | 入库单 Ginlong 回传数据页点击入库完成 | 从关联 Done/Incoming Picking 取实际数据；不改变库存 | NOT RUN | — |
| 9 | API09-B | 查询相同 owner + KRWH | FG4/SF2/RAW12；查询只读 | NOT RUN | — |
| 10 | API03 | 发送 api03_outbound.json | 使用同一 owner/project/warehouse/产品；不创建 Picking、预留或扣库存 | NOT RUN | — |
| 11 | 一步出库 | 选择 KarlRapp-WH: Delivery Orders，只创建一张 Picking；整托 PALLET-002，并从 PALLET-001 拆出 FG-SN-001 后 Validate | 唯一 Picking Done；库存变为 FG2/SF2/RAW8；拆出品的来源行可追溯，剩余品保留托盘 | NOT RUN | — |
| 12 | API06 | 从出库单/Done Picking Ginlong 回传数据页点击备货完成 | 同一 Done/outgoing Picking 实际作业数据发送；不发生第二次出库 | NOT RUN | — |
| 13 | API08 | 在同一出库单点击确认离仓并回传发货完成 | 订单状态更新；Mock Payload 只有 outboundOrderNo、action、shipmentConfirmed；不建 Picking、不动库存 | NOT RUN | — |
| 14 | API09-C | 查询相同 owner + KRWH | FG2/SF2/RAW8；查询只读 | NOT RUN | — |
| 15 | API05 | 发送 api05_count_after_outbound.json | 建客户盘点指令；与实际结果分离；不动库存 | NOT RUN | — |
| 16 | 实盘 | Actual Results 页面录入实际剩余 FG/SF SN 及 RAW 5/3 托盘行，保存后重新打开核对 | 六条已保存实盘事实与现场结果一致 | NOT RUN | — |
| 17 | API10 | 勾选本次六条实盘结果，在 Ginlong 回传页点击盘点完成 | 只发送已保存实盘结果；不读 stock.quant 推算、不改库存 | NOT RUN | — |

## 每一步证据

每个 Case 至少记录：实际输入/业务点击、HTTP 或 Mock 响应、单据/Picking/实盘结果 ID、库存数、API Log/Event、截图路径、项目负责人 PASS/FAIL。Token、Secret 和 Cookie 不记入证据。

| Case | API Log / Event / 业务 ID | Mock 行号或响应 | UI/ORM 只读证据 | 人工判定 |
|---|---|---|---|---|
| API07 | — | — | — | NOT RUN |
| API09-A | — | — | — | NOT RUN |
| API01 | — | — | — | NOT RUN |
| API02-N / 收货 / API02-Y | — | — | — | NOT RUN |
| 一步入库 / API04 | — | — | — | NOT RUN |
| API09-B / API03 | — | — | — | NOT RUN |
| 一步出库 / API06 / API08 | — | — | — | NOT RUN |
| API09-C / API05 | — | — | — | NOT RUN |
| Actual Results / API10 | — | — | — | NOT RUN |

## 人工验收结论

- 项目负责人真实人工 HVR：NOT RUN
- 项目负责人：—
- 完成时间：—
- 未通过或阻塞项：—
- 最终签署：—

此记录与 Codex 模拟 HVR 分开判定。模拟 HVR 的结果和证据见 CC-GIN-005_Final_Simulation_HVR_Report.md。

