# CC-GIN-005 模拟 HVR 最终验收报告

**运行编号：** CC005-FINAL-20261127-01  
**运行日期：** 2026-11-27  
**最终代码：** ginlong_apis 18.0.2.0.56  
**数据库 / 服务：** odooce_karlrapp / 本地 Odoo 8099  
**模拟结论：** **PASS**  
**项目负责人真实人工 HVR：** **NOT RUN**  
**真实 Ginlong、生产及 Karl Rapp Gateway 联调：** **NOT RUN**

## 1. 验收范围及业务基线

本次使用 Codex 内置浏览器执行 WMS 页面操作，入站 API 通过本地 HTTP 真实路由调用，出站回传由业务单据按钮发送至本地 Mock，业务数据用 Odoo Shell ORM 只读核验。没有通过 ORM/Shell 创建、确认或完成入库、出库、盘点业务，没有直接修改 stock.quant，没有连接真实外部系统。

执行基线为一步入库、一步出库：入库订单只完成一张 Incoming Picking；出库订单只完成一张 Delivery Orders Picking。API06 读取该唯一 Done/outgoing Picking 上的实际备货作业记录；API08 在此后只改变订单离仓状态并发送 Ginlong V3.2 的三个字段，不创建 Picking 或再移动库存。API01 的 SN/托盘是客户预报；API05 是客户盘点指令；API10 读取 UI 已保存的仓库实盘结果。

执行中没有修改业务代码、模块、Endpoint、库存 Route 或权限配置。遇到的表单操作问题通过已有页面允许的输入解决，没有改配置或规则。

## 2. 环境与自动化前置证据

| 项目 | 实际结果 |
|---|---|
| Odoo | 本地 8099，开始时 GET /web/login 返回 200 |
| 模块 | Odoo ORM 读取 installed/latest 均为 18.0.2.0.56 |
| 自动化回归 | 96 post-tests / 100 test methods，0 failed、0 error；日志 /private/tmp/ginlong_full_regression_20261127_v056.log |
| Mock | API02 18102、API04 18104、API06/08/10 18106；全部为本地 Mock |
| 业务 UI 用户 | hvr.ginlong.operator，Odoo Internal User、Inventory / User、Project / User；非 Stock Manager、非 Administrator |
| 仓库 Route | KRWH 一步入库 / 一步出库；操作类型为 Receipts 和 Delivery Orders |
| 主链 owner / project | HVR-GIN005-OWNER / HVR-GIN005 project |
| 捕获范围 | API02/04/06/08/10 的正式请求以运行开始时记录的 Mock 捕获基线之后新增行计数 |

自动化结果是运行前的技术证据；最终 PASS 另基于本次的实际 HTTP、实际 UI 操作、Mock 请求和响应、API Log、幂等记录与 ORM 库存断言。

## 3. 同一业务主链

| 对象 | 实际记录 |
|---|---|
| 成品 / 半成品 / 原材料 | HVR-FINAL-20261127-FG（变体 4643，Serial）；HVR-FINAL-20261127-SF（变体 4644，Serial）；HVR-FINAL-20261127-RAW（变体 4645，非 SN） |
| 入库订单 | HVR-FINAL-20261127-IN-01，world.depot.inbound.order ID 3077 |
| 实际入库 | KRWH/KRIN/01310，stock.picking ID 2156，唯一 Done/Incoming Picking |
| 出库订单 | HVR-FINAL-20261127-OUT-01，world.depot.outbound.order ID 1578 |
| 实际出库 | KRWH/KROUT/00832，stock.picking ID 2157，唯一 Done/Outgoing Picking |
| 盘点订单 | HVR-FINAL-20261127-COUNT-01，world.depot.stocktake.order ID 1070 |
| 实盘结果 | world.depot.stocktake.result IDs 412–417，共六条实际结果，由业务 UI 保存并勾选回传 |

入库作业把成品 4、半成品 2、原材料 12 放入三个托盘。每个托盘都有原材料和 SN 产品；同产品跨托盘。出库从 PALLET-002 整托发出成品 1、原材料 4，并从 PALLET-001 拆出成品 1。拆出成品的作业行保留来源托盘记录，剩余成品仍在 PALLET-001；拆托后已拣出的产品不要求继续绑定原托盘。

## 4. API01–API10 主链判定

| API / WMS 节点 | 判定 | 实际行为和证据 |
|---|---|---|
| API07 产品档案 | PASS | 真实 HTTP 创建同一 owner 的成品、半成品、原材料档案；模板/变体和 tracking 正确，无库存变化。Logs 10745–10747，Idempotency 9028–9030。 |
| API09 入库前 | PASS | 真实 HTTP 查询 owner + KRWH；本轮三个 SKU 的初始物理数量为 0。只读。 |
| API01 入库指令 | PASS | 真实 HTTP 创建订单 3077 和客户预报明细；未创建 Picking、Lot、实际 Package 或库存。Log 10749，Idempotency 9031。 |
| API02 收货确认 | PASS | 订单 Planning 时按钮向 Mock 回传 N；用户执行现有收货确认后，按钮回传 Y。Logs 10750/10751；Mock 新增两条真实 HTTP 请求；业务状态和 Chatter 操作记录已核对。 |
| 实际入库 Picking | PASS | 通过 UI 创建并完成唯一 Incoming Picking 2156；九条作业行、三个托盘。只在 Done 时库存从 0/0/0 增至成品 4、半成品 2、原材料 12。 |
| API04 入库完成 | PASS | 从订单按钮自动读取当前订单的 Done/Incoming Picking 2156 和实际作业数据回传。Mock HTTP 200、Y/OK；Log 10752、幂等记录 9034。回传不改变库存。 |
| API09 入库后 | PASS | 真实 HTTP 查询返回本轮成品 4、半成品 2、原材料 12；不扣预留量，查询不改变库存。Log 10753。 |
| API03 出库指令 | PASS | 真实 HTTP 创建订单 1578；使用同一 owner/project/warehouse 和 API07 产品变体。未创建 Picking、未预留或扣减库存。Log 10754。 |
| 实际出库 Picking | PASS | 通过 UI 只创建并完成唯一 Delivery Orders Picking 2157；包含整托 PALLET-002 和 PALLET-001 拆托。Done 后库存变为成品 2、半成品 2、原材料 8。来源托盘记录和剩余绑定均与拆托实际结果相符。 |
| API06 备货完成 | PASS | 在订单 1578 页面按钮从 Done/outgoing Picking 实际数据回传；托盘数 2、重量 4.5，SN 产品使用真实 SN，非 SN 原材料用 productCode 表达且数量为 4。Mock HTTP 200、Y/OK；Log 10755、幂等 9036。库存不变。 |
| API08 发货完成 | PASS | 在同一订单按钮确认离仓并回传；只改订单业务状态，不创建第二张 Picking。Mock Payload 仅 outboundOrderNo、action、shipmentConfirmed；Log 10756、幂等 9037；HTTP 200、Y/OK。库存不变。 |
| API09 出库后 | PASS | 真实 HTTP 查询本轮成品 2、半成品 2、原材料 8；只读。Log 10757。 |
| API05 盘点指令 | PASS | 真实 HTTP 创建盘点订单 1070，计划数量对应出库后的剩余商品；不创建实盘结果、不改库存。Log 10759；独立 Idempotency 9038 succeeded。 |
| 实盘与 API10 | PASS | 业务 UI 保存并重新核对六条 Actual Results，再从盘点单按钮回传。Payload 使用 SN 产品实际 SN；非 SN 原材料按托盘分别以 productCode 和数量 5/3 表达。Mock HTTP 200、Y/OK；Log 10760。未读 stock.quant 推算实盘，也未改库存。 |

## 5. 库存、SN 与托盘连续性

| 检查点 | 成品 | 半成品 | 原材料 | 变化来源 |
|---|---:|---:|---:|---|
| API09 入库前 | 0 | 0 | 0 | 无 |
| Incoming Picking 2156 Done 后 | 4 | 2 | 12 | 唯一入库 Picking |
| API03 / API04 / API06 / API08 / API10 后 | 保持对应数量 | 保持对应数量 | 保持对应数量 | API/状态确认不记账 |
| Outgoing Picking 2157 Done 后 | 2 | 2 | 8 | 唯一出库 Picking |

最终 Odoo ORM 只读核验：三个 SKU 的 reserved_quantity 均为 0；包装分布中成品 SN-002 留在 PALLET-001、SN-004 留在 PALLET-003，半成品 SN-001 留在 PALLET-001、SN-002 留在 PALLET-003，原材料分别为 5 和 3；出库的整托及拆托数量与 Mock 回传一致。API10 六条实盘结果与出库后的实际剩余库存、SN 和托盘一致，盘点及回传未产生库存移动。

## 6. 日志和证据

- ORM 只读快照：cc005_final_20261127/evidence/final_orm_snapshot.json
- API06 Mock 请求/响应：cc005_final_20261127/evidence/api06_mock_request_response.json
- API08 Mock 请求/响应：cc005_final_20261127/evidence/api08_mock_request_response.json
- API10 Mock 请求/响应：cc005_final_20261127/evidence/api10_mock_request_response.json
- API10 页面成功截图：cc005_final_20261127/evidence/api10_callback_success.png
- Picking 2156 / 2157 页面证据：cc005_final_20261127/evidence/inbound_picking_done_2156.png、outbound_picking_done_2157.png
- 完整步骤记录：cc005_final_20261127/Execution_Record.md
- 正式出站 Mock 捕获文件：project_flow/test_data/outbound_received.jsonl（本 Run 请求追加在正式捕获基线之后；没有删除历史行）
- API Log IDs：10745–10757、10759–10760。Token 签发日志 10758 不作为业务 HVR 证据引用。
- 关键 Idempotency：API07 9028–9030；API01 9031；API02 9032/9033；API04 9034；API06 9036；API08 9037；API05 9038。
- API09 不使用持久化幂等。API10 在 CC-GIN-010 中保持原有行为，本次只验实际回传和 API Log，不扩展 API10 重复确认机制。

## 7. 最终状态

**CC-GIN-005 Codex 内置浏览器模拟 HVR：PASS。** 一个最终代码版本、一套全新业务单号、一条连续业务链完成 API01–API10；一步入库、一步出库和同一盘点链均有实际证据。此前运行遗留的 BLOCKED/PARTIAL 属于旧运行记录；本报告结论只针对 Run CC005-FINAL-20261127-01，不覆盖或删除其历史证据。

**项目负责人真实人工 HVR：NOT RUN。** 负责人尚未亲自执行并签署验收；本报告不替负责人填写 PASS。

**真实 Ginlong、生产及 Karl Rapp Gateway 联调：NOT RUN。** 本次出站只到本机 Mock。下一步真实人工 HVR 使用独立数据目录 real_hvr_20261128，不复用已经完成的 FINAL Run 单据。

