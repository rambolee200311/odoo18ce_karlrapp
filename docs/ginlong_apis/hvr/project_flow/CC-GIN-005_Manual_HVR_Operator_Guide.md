# CC-GIN-005 项目级真实人工 HVR 操作指南

**当前 Codex 模拟 HVR：** PASS，Run CC005-FINAL-20261127-01。  
**本指南对应的项目负责人真实人工 HVR：** NOT RUN。  
**本地范围：** Odoo 8099 + 本地 Ginlong Mock；不连接真实 Ginlong、生产或 KR Gateway。

本指南只使用 real_hvr_20261128 目录的独立数据，不复用 CC005-FINAL-20261127 模拟订单。实际 HVR 前重新检查产品、Lot/SN、Package、订单号及幂等键无冲突。若有冲突，统一调整整套数据后缀，不清理历史记录。

## 1. 固定业务基线

- 一步入库：一个入库订单，一张 Incoming Picking，只有该 Picking Done 改变库存。
- 一步出库：一个出库订单，一张 Delivery Orders Picking。完成 Picking 时同时形成备货实绩；API06 读取该实绩。API08 只改变订单离仓状态并回传，不创建 Picking、不移动库存。
- API01 的 SN/托盘行只是客户预报；API04 只读取实际 Done Picking。
- API05 是客户盘点指令；API10 只读取已保存的实盘结果。
- API02/04/06/08/10 只通过 Odoo 真实业务单据按钮发到本地 Mock。不得手工构造外发 JSON。
- API08 请求严格只有 outboundOrderNo、action、shipmentConfirmed 三个字段。

## 2. 环境和登录

1. 打开 http://127.0.0.1:8099/odoo，使用 hvr.ginlong.operator 登录。该账号有 Inventory / User、Project / User，不是 Administrator 或 Stock Manager。
2. 确认 Ginlong API Endpoint 仍指向本地 Mock：API02 18102、API04 18104、API06/08/10 18106。
3. 查看 outbound_received.jsonl 当前行数，记为本次人工 HVR 的 Mock 起始行号。不要删除旧捕获记录。
4. 通过项目 API User 的现有凭据取得有效 Token。Authorization Header 直接放 Token，不加 Bearer。不要把 Token、Secret、Cookie 放入 HVR 记录。
5. 进入 real_hvr_20261128/，先查看 README.md，再只执行 payloads 目录列出的七份 JSON。

## 3. 入站 HTTP 报文

从该数据集目录执行：

- API07：api07_01_fg.json → api07_02_sf.json → api07_03_raw.json。三次均预期 Y/OK；验证 owner 变体、模板共享属性及 tracking：FG/SF 为 Serial，RAW 为 none。此时库存仍为 0。
- API09：api09_opening.json。目标三个 SKU 的库存必须均为 0；列表可包含其他历史 SKU。
- API01：api01_inbound.json。预期创建 HVR-REAL-20261128-IN-01。打开 WorldDepot → Inbound → Orders，确认 owner、project、warehouse、产品和数量正确；此时不得出现实际 Picking/Lot/Package/库存。
- API09：API04 完成后再次发送同一 api09_opening.json，目标库存应 FG4、SF2、RAW12。
- API03：api03_outbound.json。预期创建 HVR-REAL-20261128-OUT-01，且使用同一 owner、warehouse、三种产品；创建指令不应创建 Picking/预留或减少库存。
- API09：API08 操作完成后再次发送，目标库存应 FG2、SF2、RAW8。
- API05：api05_count_after_outbound.json。盘点指令应匹配出库后的剩余产品、数量与计划 SN；不得创建实盘结果或调整库存。

报文只由以下脚本发送；脚本不包含凭据：
./send_payload.sh API07 payloads/api07_01_fg.json
./send_payload.sh API07 payloads/api07_02_sf.json
./send_payload.sh API07 payloads/api07_03_raw.json
./send_payload.sh API09 payloads/api09_opening.json
./send_payload.sh API01 payloads/api01_inbound.json
./send_payload.sh API03 payloads/api03_outbound.json
./send_payload.sh API05 payloads/api05_count_after_outbound.json

## 4. 单一完整业务主链：逐步操作

| 顺序 | 页面和操作 | 预期结果 |
|---:|---|---|
| 1 | API01 创建入库订单后，在 WorldDepot → Inbound → Orders 打开该订单。检查业务指令和 SN/托盘预报。 | 状态仍为未完成仓库作业；没有 Picking、Lot、实际 Package 或库存变化。 |
| 2 | 进入订单 Ginlong 回传数据页，点击“回传锦浪：收货确认”。 | 订单 status=planning 时 Mock 收到 API02 receiptConfirmed=N，返回 Y/OK；库存不变。 |
| 3 | 在同一订单执行现有“收货确认”操作，核对状态及 Chatter 操作日志；随后再次进入 Ginlong 回传数据页并点击 API02 按钮。 | status 为 arrive/inbound；Mock 收到 receiptConfirmed=Y；仍没有已过账库存。 |
| 4 | 在订单 Main 页将 Arrival Date 设为 Order Date（允许相同），Container No 可以留空；保存、确认订单。Picking Type 选择 Receipts，只点击一次 Create Receipt。 | 只生成该入库订单的一张 Incoming Picking。 |
| 5 | 在 Incoming Picking 实际 Operations 中录入三托盘作业：PALLET-001：FG SN-001/002 各1、SF SN-001 数量1、RAW 5；PALLET-002：FG SN-003 数量1、RAW 4；PALLET-003：FG SN-004 数量1、SF SN-002 数量1、RAW 3。保存后核对实际数量、Lot/SN、owner 与 Package，再 Validate 这一张 Picking。 | 唯一 Incoming Picking Done；库存首次改变为 FG4/SF2/RAW12。API01 预报不创建这些实际库存对象。 |
| 6 | 回到入库订单 Ginlong 回传数据页，点击“回传锦浪：入库完成”。 | 系统自动按订单找到 Done/Incoming Picking；Mock 收到实际 SN、非 SN productCode 和托盘数量；API04 不改库存。 |
| 7 | 发送 API09 入库后查询。 | 目标库存仍为 FG4/SF2/RAW12。 |
| 8 | 发送 API03 出库指令。进入 WorldDepot → Outbound → Orders 打开出库订单。为两个成品明细分别保存来源托盘前缀：SN-003 对应 HVR28-PALLET-002，SN-001 对应 HVR28-PALLET-001；原材料 4 对应 HVR28-PALLET-002。 | 出库订单使用同一 owner、warehouse、product variants 与项目；API03 本身不创建 Picking、reserve 或库存变化。 |
| 9 | 选择 KarlRapp-WH: Delivery Orders，确认订单，只点击一次 Create Picking。在这一张 Outgoing Picking 中核对两个来源托盘和实际 Lot/SN/产品/数量。PALLET-002 整托出 FG-SN-003 与 RAW 4；PALLET-001 拆出 FG-SN-001 一件。记录真实作业人和时间，保存后 Validate。 | 只完成一张 Done/outgoing Picking；库存由 FG4/SF2/RAW12 变为 FG2/SF2/RAW8。FG-SN-002 留在 PALLET-001；被拣出的 FG-SN-001 可离开原 Package，但其来源作业行可追溯。 |
| 10 | 在 Done Picking / 出库订单的 Ginlong 回传数据页，按现有 Form 填/确认必要的实际操作人员和时间并保存。确认托盘数为2、总重量为4.50 kg，点击“回传锦浪：备货完成”。 | API06 来自唯一 Done/outgoing Picking。Mock 收到真实备货结果；回传不再扣库存、不创建另一张 Picking。 |
| 11 | 在同一出库订单点击“确认离仓并回传锦浪：发货完成”。 | 订单离仓业务状态更新并记录操作；Mock Payload 只有 outboundOrderNo、action=CREATE、shipmentConfirmed=Y。无第二 Picking、无额外库存移动。 |
| 12 | 发送 API09 出库后查询。 | FG2/SF2/RAW8，预留量不扣减。 |
| 13 | 发送 API05 盘点指令后，进入 WorldDepot → Stocktake → Customer Orders，打开 HVR-REAL-20261128-COUNT-01。Actual Results 页按实际库存记录：FG-SN-002/PALLET-001；FG-SN-004/PALLET-003；SF-SN-001/PALLET-001；SF-SN-002/PALLET-003；RAW 5/PALLET-001；RAW 3/PALLET-003。按页面记录实际盘点人及时间，保存。 | 六条实际结果持久化；不读取计划数量代替实盘，不改 stock.quant。 |
| 14 | 在该盘点单 Ginlong 回传数据页将六条本次实盘结果纳入回传并保存，点击“回传锦浪：盘点完成”。 | API10 从已保存实盘数据生成请求，Mock 返回 Y/OK；不改变库存。 |

## 5. 预期库存节点

| 节点 | FG | SF | RAW |
|---|---:|---:|---:|
| API09 入库前 | 0 | 0 | 0 |
| 唯一 Incoming Picking Done | 4 | 2 | 12 |
| API03 / API04 / API06 / API08 / API10 后（除 Picking 外） | 不改变当前值 | 不改变当前值 | 不改变当前值 |
| 唯一 Outgoing Picking Done | 2 | 2 | 8 |

Stocktake/实盘数量不是库存调整。若 API09 数量或 Odoo Picking 实际结果不符，应停止依赖该数据的步骤，保存证据，不要通过人工改 quant 掩盖。

## 6. 结果记录

在 HVR_Project_Business_Flow_Execution_Record.md 中，由负责人填写每个 API 请求响应、单据/Picking/实盘 ID、Mock 新增捕获行、API Log/Event、库存快照及人工 PASS/FAIL。Codex 的模拟报告位于 CC-GIN-005_Final_Simulation_HVR_Report.md；它只证明模拟 HVR，不作为负责人真实人工验收。

