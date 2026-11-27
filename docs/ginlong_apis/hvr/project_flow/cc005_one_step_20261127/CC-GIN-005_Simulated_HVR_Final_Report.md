# CC-GIN-005 模拟 HVR 最终报告

**运行编号：** `R8239A3`  
**执行日期：** 2026-11-27  
**环境：** 本地 Odoo `odooce_karlrapp`，`ginlong_apis 18.0.2.0.54`，本地 Mock HTTP   
**性质：** Codex 内置浏览器模拟 HVR；不代表业务负责人真实人工 HVR，也不代表真实 Ginlong/Karl Rapp 联调。

## 总体结论

**整体：PARTIAL。** 当前连续主链已完成 API01–07、API09、API10 的浏览器模拟及本地 Mock 验收。API04、API06、API10 对非 SN 原材料均使用 `productSN=productCode`，数量取实际 Picking 或实盘结果；通过 Odoo ORM 只读确认回传前后库存未因回传改变。唯一未完成项为 API08：当前出库单仍为 `Planning`，实际离仓业务状态未产生，且当前 API08 代码从空的持久化发货明细生成 Payload。不得为完成 HVR 而手工复制明细或虚构离仓状态。

API04 的旧日志 9499 保留为修复前失败证据；修复后同一主链经真实订单按钮和本地 Mock 重新发送，日志 9533 为 `success / HTTP 200 / returnStatus=Y`，因此当前 API04 判为 PASS。

| API | 当前模拟 HVR 状态 | 证据 |
|---|---|---|
| API01 | PASS | Log 9496，入库单 2751 |
| API02 | PASS | Logs 9497（N）、9498（Y） |
| API03 | PASS | Log 9503，出库单 1403；首次类型错误 Log 9502 保留 |
| API04 | PASS | 修复后 Log 9533；RAW `productSN=productCode`，实际数量为 3/4/5 |
| API05 | PASS | Log 9511，盘点单 953 |
| API06 | PASS | 修复后重发 Log 9535；RAW `productSN=productCode`、实际数量 3 |
| API07 | PASS | Logs 9492–9494，主链三个产品 |
| API08 | BLOCKED | 订单 `status=planning`、`actual_outbound_datetime` 为空；现有 API08 依赖空发货明细 |
| API09 | PASS | Logs 9495、9501、9509；出库后 FG/SF/RAW=2/2/9 |
| API10 | PASS | Log 9534；RAW `productSN=productCode`，实盘数量 5/4 |

本轮定向 Odoo 自动化运行 3 个 API04/06/10 测试方法，结果 **3 passed, 0 failed, 0 error**。测试命令和运行结果见 `evidence/callback_retest_automation_20261127.json`。最新 ORM 与回传证据见 `evidence/api04_api06_api10_nonserial_orm_evidence_20261127.json`。

## 本轮唯一主链数据

| 对象 | 编号 / 记录 |
|---|---|
| 货主 | `HVR01-20261121-OWNER-A` |
| 仓库 | `KRWH` / `KarlRapp-WH` |
| 项目 | `HVR01-20261121 API01 HVR Project` |
| 入库单 | `HVR005-20261127-R8239A3-IN-001`，ORM ID 2751 |
| 出库单 | `HVR005-20261127-R8239A3-OUT-001`，ORM ID 1403 |
| 盘点单 | `HVR005-20261127-R8239A3-COUNT-001`，ORM ID 953；API05 Log 9511 |
| 产品 | `...-FG`（ID 4216，serial）、`...-SF`（ID 4217，serial）、`...-RAW`（ID 4218，非 SN） |
| 托盘 | `...-PALLET-001`、`...-PALLET-002`、`...-PALLET-003` |

三个产品由 API07 建立，均对应同一货主、项目和仓库。入库预报及实际入库分布为：

| 托盘 | 成品 FG | 半成品 SF | 原材料 RAW |
|---|---:|---:|---:|
| PALLET-001 | 2（FG-SN-001/002） | 1（SF-SN-001） | 5 |
| PALLET-002 | 1（FG-SN-003） | 1（SF-SN-002） | 4 |
| PALLET-003 | — | 1（SF-SN-003） | 3 |
| 合计 | 3 | 3 | 12 |

因此，入库已覆盖三个托盘均含多种产品、同产品跨托盘及一个托盘多件/SN。实际出库从 PALLET-001 拆出 FG 1 件，并从 PALLET-003 整托出 SF 1 件及 RAW 3 件。出库后实测库存为 FG 2、SF 2、RAW 9。

## 首轮运行结果（保留历史记录；后续结论见追加记录）

| 顺序 | 步骤 | 状态 | 实际证据 / 说明 |
|---:|---|---|---|
| 1 | API07 创建三个产品变体 | PASS | 实际 HTTP POST，API Log 9492–9494 均 `Y/OK`。同码/归属与主链货主一致。 |
| 2 | API09 期初库存 | PASS | API Log 9495，`Y/OK`；本轮三个 SKU 不在返回清单中，期初为 0。响应另含既有非本轮 SKU，未将其计入主链。 |
| 3 | API01 创建入库单 | PASS | 实际 HTTP POST，API Log 9496 `Y/OK`；入库单 ID 2751。 |
| 4 | API02 未收货状态 | PASS | API Log 9497，Payload `receiptConfirmed=N`，本地 Mock HTTP 200。 |
| 5 | API02 收货确认后 | PASS | 浏览器执行订单“收货确认”，状态改为 `arrive` 并记录 Chatter；API Log 9498，Payload `receiptConfirmed=Y`，本地 Mock HTTP 200。 |
| 6 | 入库实际作业 | PASS | 浏览器通过 Receipts 创建、录入明细并 Validate；唯一 Picking ID 1937 `KRWH/KRIN/01180`，类型 incoming，状态 Done。共 9 个产品/托盘 move line。未使用 ORM 创建业务记录。 |
| 7 | API04 入库完成 | **FAIL（契约）** | 浏览器实际回传按钮产生 API Log 9499，POST 至本地 Mock，Mock 回 `Y/OK`。日志中的三条 RAW 行 `productSN=false`；V3.2 API04 `snList[].productSN`（`field_rules.json` O 列第 27 行）为必填。Mock 未做字段契约校验，故不能认定 API04 通过。 |
| 8 | API09 入库后库存 | PASS | API Log 9501，实际 HTTP 200 `Y/OK`；FG=3、SF=3、RAW=12，未扣预留。ORM 实盘量与三个托盘分布一致。 |
| 9 | API03 出库订单 | PASS（数据输入） | 首次报文 `total_vol=0.30000000000000004` 被 TYP01 拒绝（Log 9502）；修正测试 JSON 为精确十进制 `0.3` 后，Log 9503 `Y/OK`。API03 订单 ID 1403 与主链使用相同项目、货主和三个产品。随后在浏览器确认订单，state=`confirm`。本测试把 `customer` 映射到现有货主 Contact；未验证与货主不同的收货方场景。 |
| 10 | 一张实际出库 Picking | **BLOCKED** | 订单表单 Picking Type 下拉仅提供 `KarlRapp-WH: Internal Transfers`，项目默认 outbound picking type 为空。该 Order 的“Create Picking”路径按 `pick_type` 创建，不能使用，因为会引入被禁止的内部调拨。标准 Deliveries 页面虽为 outgoing，但 `stock.picking.outbound_order_id` 在现有界面只读，无法形成 API06 所需的订单关联。仅建立过未保存草稿并已 Discard；没有新 Picking、库存移动或副作用。 |
| 11 | API06 备货完成 | BLOCKED | 无关联的已完成实际出库 Picking，不能生成符合主链的实际备货报文。未点击回传按钮，未向 Mock 发送。 |
| 12 | 实际离仓确认 | NOT RUN | 未出库，不能进行离仓确认。 |
| 13 | API08 发货完成 | BLOCKED | 无实际出库记录/已保存发货明细，未发送 API08。API08 的 V3.2 Payload 仍仅为 `outboundOrderNo`、`action`、`shipmentConfirmed`；本轮未增加托盘字段。 |
| 14 | API09 出库后库存 | NOT RUN | 没有实际出库，不能把入库后库存冒充出库后库存。当前库存仍 FG=3、SF=3、RAW=12。 |
| 15 | API05 盘点指令 | NOT RUN | 盘点应对应出库后的真实剩余库存；出库未完成，未提交。 |
| 16 | 实盘结果及 API10 | NOT RUN | 未创建/录入实盘结果，也未回传 API10；未使用 `stock.quant` 推算实盘结果。 |

## 实际库存与订单复核

通过 Odoo ORM 只读核验：入库后且 API03 订单确认后，KRWH/KRStock 的货主实物量为 FG 3、SF 3、RAW 12，预留量均为 0。托盘分布分别为：FG PALLET-001 两件、PALLET-002 一件；SF 三个托盘各一件；RAW PALLET-001/002/003 分别为 5/4/3。出库订单为 `confirm/planning`，`pick_type`、`picking_PICK`、`picking_Out` 均为空；没有关联出库 Picking。

API03 首次 `TYP01` 是测试 JSON 的浮点序列化尾差，不是业务处理缺陷；调整 Payload 后成功，第一次失败记录保留。入库后拆托需求尚未执行，不能用预期拆托数据判定托盘连续性。

## 已发现问题与影响

1. **订单与单步出库 Picking 的关联入口冲突（主链阻塞）**：已核实 KRWH 有一步出库 Route 和 `Delivery Orders` outgoing operation type，仓库 Route 不缺失。问题在 API03 出库订单的 `pick_type` 域限定 `code=internal`（`mymodules/worlddepot/models/outbound_order.py`），`action_create_picking_PICK` 依该字段建 Picking（`outbound_order_create_picking.py`）；本轮项目默认类型为空。另一方面，标准 `Delivery Orders` 创建表单的 `stock.picking.outbound_order_id` 在视图中只读（`mymodules/worlddepot/views/inbound_order.xml`），不能把 outgoing Picking 关联至订单供 API06 使用。不得点击订单的“Create Picking”制造内部调拨，也不得创建独立 outgoing Picking 后声称已关联订单。仅建立过未保存草稿并已 Discard；没有新 Picking、库存移动或副作用。核对截图见 [一步出库 Route](evidence/one_step_delivery_route_ui.png)，ORM 只读详情见 [证据 JSON](evidence/orm_readonly_evidence.json)。
2. **API04 非 SN 产品映射（协议失败）**：实际 move line 中 RAW 没有 Lot/SN，生成的 API04 行将 `productSN` 序列化为 `false`。不能编造 SN，也不能把 Mock 的宽松成功当作 Ginlong 契约成功。需要确认非 SN 产品在 API04 `snList` 中的协议表达方式或调整实现方案；本轮不擅自决定。

以上为现有代码/界面和协议适配问题，不是拆托业务规则问题，也不是本轮操作者遗漏。没有修改代码、Route、仓库配置或业务记录；本地已按计划创建的 API07、API01、API03 和入库 Picking 保留。

## 证据索引

- 本轮输入报文：[`payloads/`](payloads/)
- API01 响应：[`api01_http_result.json`](api01_http_result.json)
- API03 首次类型错误及成功重试：[`api03_http_attempts.jsonl`](api03_http_attempts.jsonl)、[`api03_http_result.json`](api03_http_result.json)
- API02/API07/API09 响应记录：[`inbound_http_results.jsonl`](inbound_http_results.jsonl)
- 入库 Picking UI 证据：[`evidence/api02_order_status_and_picking_created.png`](evidence/api02_order_status_and_picking_created.png)
- Picking 操作前截图：[`evidence/inbound_picking_before_validate.png`](evidence/inbound_picking_before_validate.png)
- 单步出库选择器证据：[`evidence/outbound_order_pick_type_options.png`](evidence/outbound_order_pick_type_options.png)
- API Log：9492–9503（敏感凭据未纳入本报告）；API04 请求报文为 Log 9499。
- 数据库复核使用现有 Odoo Shell ORM 只读查询；未使用 SQL。

## 人工验收状态

本报告只记录 Codex 的本地模拟 HVR，不能代替项目负责人真实人工 HVR。真实人工 HVR 未在本次由 Codex 代填。API04 契约问题和出库 Picking 关联问题解决并经评审后，应从清洁的连续测试数据重新执行受影响的主链步骤；已通过且不受影响的 API07/API01/API02/入库事实可保留作为历史证据，但最终整条主链仍需按冻结验收要求重新确认。

## 后续记录：一步出库 Picking 与 API06（2026-11-27）

本节追加后续实际证据，不覆盖上文当时的 BLOCKED 记录。API03 订单的出库类型现已为 `KarlRapp-WH: Delivery Orders`；订单 `OO202611271380` 关联唯一 Done/outgoing Picking `KRWH/KROUT/00749`（ORM ID 1938）。由于该 Picking 已完成并已过账库存，未删除或冲销；API06 原失败没有发送 HTTP，直接复用这张实际 Picking 完成回传。

API06 代码修正后按订单关联的 `outbound_order_id` 自动读取 Done/outgoing Picking，不再要求用户勾选作业单。非 SN 管理原材料依已确认的 Ginlong 表达规则，以 `productSN=productCode` 发送，数量为实际数量。SN 产品仍发送真实 Lot/SN。

Codex 通过真实订单 Form 的“回传锦浪：备货完成”按钮执行一次回传。界面反馈“本次实际发送 1 个事件，未发送/跳过 0 个”。本地 Mock 收到 1 次 POST：`/API/WMS_JSON/TPL_Picking_Completed`，返回 `returnStatus=Y`、`exceptionInfo=OK`。API Log 9508 成功（HTTP 200），对应幂等记录 7981 为 succeeded；旧失败日志 9504 保留。请求及响应见 `../test_data/outbound_received.jsonl` 最后一条，按钮结果截图见 `evidence/api06_success_order_button_20261127.png`。

Payload 实际包含 3 条作业行：成品 SN `...FG-SN-001` 数量 1、半成品 SN `...SF-SN-003` 数量 1、非 SN 原材料以 `productSN=HVR005-20261127-R8239A3-RAW` 数量 3；托盘数为 2，总重量为 5.25。三条记录的操作人均为 `HVR-LOCAL-TEST-OPERATOR`，操作时间取实际 Picking 完成时间 `2026-11-27 02:22:07`。

回传前后 ORM 只读库存一致：FG 2、SF 2、RAW 9，预留量均为 0。API06 只发送实际备货数据，没有创建或删除 Picking，也没有改变库存。

**本次后续结果：API06 PASS（本地 Mock/浏览器按钮）；该时点 API04、API08、出库后 API09、API05 实盘及 API10 尚未完成。该历史状态由下方 2026-11-27 最新复验记录更新。真实人工 HVR 未执行。**

## 最新记录：非 SN 回传修正与主链续验（2026-11-27）

### 已确认规则及实现

非 SN 管理产品不产生单件 SN。API04、API06、API10 的非 SN 明细统一使用原始 `productCode` 填充协议字段 `productSN`；`quantity` 分别来自已完成 Picking 的 `stock.move.line.quantity` 或已保存实盘结果的 `quantity`。SN 管理产品仍使用实际 SN。没有修改产品追踪方式，没有创建虚假 SN，没有写入或调整库存。

### 当前实际回传证据

- **API04：PASS。** 从入库单 2751 的 Done/incoming Picking `KRWH/KRIN/01180`（ID 1937）通过 Form 按钮回传。修复后 API Log 9533、幂等记录 8004，本地 Mock HTTP 200，响应 `Y/OK`。RAW 三个托盘行分别为 `productSN=HVR005-20261127-R8239A3-RAW`，数量 3、4、5；其他 SN 产品仍发送 Picking 中真实 Lot/SN。旧 Log 9499 的 RAW `productSN=false` 作为修复前证据保留，不再代表当前行为。
- **API06：PASS。** 出库单 1403 关联唯一 Done/outgoing Picking `KRWH/KROUT/00749`（ID 1938）。通过出库单 Form 按钮实际发送；在已有成功记录后确认重复回传，产生新 HTTP 请求。最新 API Log 9535、幂等记录 8006，本地 Mock HTTP 200，响应 `Y/OK`。Payload 中 RAW 使用 `productSN=productCode`，数量 3；SN 产品使用实际 SN。重复确认界面已取消关闭，取消动作没有另发 HTTP。
- **API09 出库后：PASS。** 已有真实 HTTP 查询结果及 API Log 9509，指定 owner/warehouse 返回 FG=2、SF=2、RAW=9；与出库后库存一致。
- **API05：PASS。** API Log 9511，盘点单 953 按同一主链 owner、warehouse、产品及剩余数据创建。
- **API10：PASS。** 在盘点单 Form 中保存并重新打开核对实盘结果，再从订单按钮发送。API Log 9534，本地 Mock HTTP 200，响应 `Y/OK`。SN 管理行发送实际 SN；RAW 两托盘分别以 `productSN=productCode`、数量 5 和 4 回传。API10 读取实盘结果，没有查询 `stock.quant` 推算实盘。

### 库存与 API08 剩余项

Odoo Shell ORM 只读复核结果：FG=2、SF=2、RAW=9，预留量均为 0；API04、API06、API10 回传没有改变这些数量。证据见 `evidence/api04_api06_api10_nonserial_orm_evidence_20261127.json`。

API08 当前仍为 **BLOCKED**，不是因为报文需要托盘字段（Ginlong V3.2 仍只有 `outboundOrderNo`、`action`、`shipmentConfirmed` 三项），而是当前业务界面/代码不符合已确认的“一步出库、实际离仓仅改订单状态并回传”操作：订单 ORM 状态仍为 `planning`，`actual_outbound_datetime` 为空，UI 没有可执行的实际离仓状态按钮；API08 构造器要求 `ginlong_shipment_detail_ids` 中存在已保存明细，而该表单明细为空。为遵循“不重复维护已有数据、不伪造业务状态”，本轮未手工补行，也未点击造成失败日志的回传。当前页面截图见 `evidence/api08_current_business_state_20261127.png`。此项需要按已批准业务设计补齐实际离仓状态入口/API08 状态映射后，才能续跑受影响步骤。

### 自动化定向验证

数据库 `odooce_karlrapp` 当前安装模块版本为 `ginlong_apis 18.0.2.0.54`。在现有环境执行 API04、API06、API10 三个定向 Odoo 测试方法，输出 `3 post-tests`、`0 failed`、`0 error(s)`；没有运行完整全量回归。报告证据文件列出实际命令和方法。

**最新模拟 HVR 结论：API01–07、API09、API10 PASS；API08 BLOCKED；CC-GIN-005 模拟 HVR 整体仍为 PARTIAL。真实人工 HVR 未执行。**
