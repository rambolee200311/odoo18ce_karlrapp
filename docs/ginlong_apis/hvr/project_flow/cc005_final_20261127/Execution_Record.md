# CC-GIN-005 Final Simulation HVR — Execution Record

- Run ID: `CC005-FINAL-20261127-01`
- 候选代码：`ginlong_apis 18.0.2.0.56`
- 数据库：`odooce_karlrapp`（仅 Odoo ORM）
- 正式业务链状态：**COMPLETE；API07→API10 同一主链全部完成**
- 真实 Ginlong、生产、KR Gateway 未连接。

## Run 前已核实

| 项目 | 结果 | 证据 |
|---|---|---|
| Odoo 在线 | PASS，`GET /web/login` 返回 200；本地 Odoo 进程监听 8099 | `/private/tmp/odoo_8099_hvr_20261127_final.log`；本轮 HTTP 检查 |
| 模块版本 | PASS，ORM：installed/latest `18.0.2.0.56`；Manifest 同版 | Odoo Shell ORM，只读 |
| 自动化回归 | PASS，96 post-tests / 100 test methods；0 fail、0 error | `/private/tmp/ginlong_full_regression_20261127_v056.log` |
| 严格 Mock 契约预检 | PASS，3 项测试 | 本轮既有 Mock contract test 记录 |
| Mock HTTP | PASS，18102/18104/18106 均 `GET /__mock__/health` 返回 `{{"status":"ok"}}` | 本机 HTTP；健康检查不写业务捕获文件 |
| HVR operator UI | PASS，浏览器页面 `http://127.0.0.1:8099/odoo/action-537/new`，WorldDepot 已登录并可见 | Codex 内置浏览器快照 |
| Owner / Project / Warehouse | PASS：owner id 423 `HVR-GIN005-OWNER`；Project 106 `HVR-GIN005 project`；KRWH id 1 | Odoo ORM |
| Route / Picking Types | PASS：KRWH `one_step`/`ship_only`；Receipts id 1 / `incoming`，Delivery Orders id 2 / `outgoing`，Internal Transfers id 7 / `internal`（禁止选） | Odoo ORM |
| 测试账号 | PASS：`hvr.ginlong.operator` active，stock/project 基础权限有效 | Odoo ORM；不记录密码 |
| 新业务唯一键 | PASS：入库 reference `HVR-FINAL-20261127-IN-01`、出库 reference `HVR-FINAL-20261127-OUT-01`、盘点 count_order_no `HVR-FINAL-20261127-COUNT-01` 均无冲突；三组 productCode 在 `product.product.ginlong_product_code`、`default_code` 均无记录；对应模板名称无冲突 | Odoo ORM，只读 |
| 单位 | PASS：`台` 已存在，Ginlong 单位类别 | Odoo ORM |
| Mock 捕获基线 | API02 `13` 行；API04 `12` 行；API06/08/10 `21` 行。正式 Run 只计基线后新增行；捕获不含 Authorization | `wc -l` 与 Mock 代码 |
| Endpoint | PASS：API02→18102，API04→18104，API06→18106，API08→18106，API10→18106 | `ir.config_parameter` ORM；均为本地 Mock |

## API01–API10 连续主链验收

| API / 作业 | 权威数据来源 | 库存预期 | 状态 |
|---|---|---|---|
| 07 | HTTP Add 三个 owner 产品变体：FG/SF/RAW | 不变 | PASS；变体 4643–4645，FG/SF serial、RAW none；stock.quant=0；API Log 10745–10747，幂等 9028–9030；HTTP 200/Y/OK，响应证据在 `evidence/api07_01_finished.json`、`api07_02_semifinished.json`、`api07_03_raw.json` |
| 09 期初 | HTTP 查询本轮 owner + KRWH 物理数量 | FG/SF/RAW = 0/0/0；只读 | PASS；HTTP 200/Y/OK；响应列出其他历史 SKU，本轮三 SKU 缺席；`evidence/api09_opening.json` |
| 01 | HTTP 建入库订单与客户预报 | 不建 Picking/Lot/Package/quant | PASS；本轮订单 id 3077，reference `HVR-FINAL-20261127-IN-01`；请求/响应 `evidence/api01_bonded_inbound.json`；API Log 10749、Idempotency 9031。 |
| 02 | 入库 Order 状态 `planning→N`、确认后 `arrive→Y` | 不变 | PASS；Order 3077；Mock API02 追加 2 次真实按钮请求；日志 10750/10751、幂等事件 9032/9033；Mock HTTP 均 200/Y/OK。 |
| 入库作业 | UI 建立并 Validate 一张 Receipts Picking | 仅此时增至 FG4/SF2/RAW12 | PASS；Picking 2156 `KRWH/KRIN/01310`，唯一一张 Incoming、Done；9 条操作行，3 托盘；ORM 验证 FG4/SF2/RAW12、货主423、无预留；库存仅由该次 Done 增加。截图 `evidence/inbound_picking_done_2156.png`。 |
| 04 | 入库订单自动读取 Done/Incoming Picking | 不变 | PASS；从订单 3077 按钮实际 POST 至 Mock，发送 Picking 2156 的 9 条实际明细；HTTP 200/Y/OK；API Log 10752、Event/Idempotency 9034 succeeded；请求证据 `evidence/api04_inbound_callback.json`。 |
| 09 入库后 | HTTP 查询实际物理数量 | FG4/SF2/RAW12 | PASS；真实 HTTP 200/Y/OK，返回本轮 FG4/SF2/RAW12，且历史 SKU 独立显示；API Log 10753、无持久化幂等。 |
| 03 | HTTP 建出库订单，复用相同 owner/project/product variants | 不创建 Picking/预留 | PASS；订单 id 1578，reference `HVR-FINAL-20261127-OUT-01`，owner 423/project 106；复用成品变体 4643 两行及原材料变体 4645 一行；创建时未关联 Picking，未预留、未改变 09 入库后库存；API Log 10754，HTTP 200/Y/OK；证据 `evidence/api03_outbound_order.json`。 |
| 出库作业 | UI 建立并 Validate 一张 Delivery Orders Picking；Pallet-002 整托、Pallet-001 拆托 | 仅此时降至 FG2/SF2/RAW8 | PASS；唯一 Picking 2157 `KRWH/KROUT/00832` Done/outgoing；证据 `evidence/outbound_picking_done_2157.png` |
| 06 | 出库订单回传同一 Done/Outgoing Picking 实绩 | 不变 | PASS；按钮实际 POST，Mock 200/Y/OK；API Log 10755、Idempotency 9036；`evidence/api06_mock_request_response.json` |
| 08 | 同一出库订单离仓操作 | 仅状态与三字段回传；无第二张 Picking | PASS；状态更新并实际 POST 仅三字段；API Log 10756、Idempotency 9037；`evidence/api08_mock_request_response.json`、`evidence/api08_outbound_status_success.png` |
| 09 出库后 | HTTP 查询剩余实际库存 | FG2/SF2/RAW8 | PASS；API Log 10757 返回本轮 FG2/SF2/RAW8，HTTP 200/Y/OK，只读 |
| 05 | HTTP 建同 owner/product/warehouse 盘点指令 | 不变 | PASS；盘点单 ID 1070；API Log 10759、幂等记录 9038 succeeded；未变更库存 |
| 实盘 + 10 | UI 保存剩余实盘结果并从记录回传 | 不从 stock.quant 推算；库存不变 | PASS；六条 Actual Results 经 UI 保存并选中；API Log 10760、Mock 200/Y/OK；库存未变；`evidence/api10_mock_request_response.json`、`evidence/api10_callback_success.png` |

## 实际执行日志

仅在完成真实 HTTP / 浏览器作业后更新对应状态，并附请求/响应、页面截图、ORM 只读快照、Mock 追加行号及 API Log/Event 证据。自动化和独立历史单据不能替代本 Run 的业务主链步骤。

| 顺序 | 实际步骤 | 状态 | 证据 |
|---:|---|---|---|
| 1 | API07 三产品 | PASS | 三次真实 HTTP 200/Y/OK；ORM IDs 4643/4644/4645；Log 10745/10746/10747；Idempotency 9028/9029/9030；无库存。 |
| 2 | API09 入库前查询 | PASS | HTTP 200/Y/OK；本轮三个 SKU 不在响应；响应完整保存在 `evidence/api09_opening.json`。 |
| 3 | API01 创建预报 | PASS | 真实 HTTP 返回 200/Y/OK；ORM 订单 id 3077、project 106、owner 423、warehouse KRWH；3 个产品变体映射及 9 条预报 SN/托盘分布已核对；Log 10749、幂等 9031。无 Picking、Lot、Package、stock.move、quant；请求/响应见 `evidence/api01_bonded_inbound.json`。UI 已打开该订单卡片，见浏览器步骤继续记录。 |
| 4 | API02 N→收货确认→Y | PASS | 订单 3077；Planning 按钮回传 N、UI 收货确认操作写入状态/Chatter、Arrive 按钮回传 Y；两次实际 Mock 请求及 API Log/Idempotency 9032/9033；本地接收记录第14–15行。 |
| 5 | 唯一 Incoming Picking 及实际入库 | PASS | UI 创建、分配单件 SN、三个托盘及原材料 5/4/3 分托，Validate 一张 `KRWH/KRIN/01310`；Done 后 ORM 只读核对 9 条 move line、库存/货主/Package；无第二 Picking。 |
| 6 | API04 入库结果回传 | PASS | 订单 Ginlong Tab 按钮触发真实 HTTP POST；Payload 来自 Done Picking，9 条 SN/产品/数量/托盘，operator 为实际确认用户，operationTime 取 date_done；Mock 响应 200/Y/OK；Log 10752，Event 9034。 |
| 7 | API09 入库后查询 | PASS | 使用短时本地 API Token 走真实 HTTP 入口，完成后立即 ORM 撤销；HTTP 200/Y/OK，目标物理数量 4/2/12；API Log 10753；无持久化幂等。 |
| 8 | API03 出库指令 | PASS | 真实 HTTP POST；复用本 Run 的 owner、project、产品变体及 customer；ORM 订单 id 1578，三条明细（FG 1+1、RAW 4），没有创建 Picking/预留；API Log 10754；请求/响应 `evidence/api03_outbound_order.json`。 |
| 9 | 唯一 Outgoing Picking（整托+拆托） | PASS | Picking 2157 `KRWH/KROUT/00832`，订单 1578；Done/outgoing；整托 PALLET-002 + 拆出 PALLET-001 一件；ORM 最终库存 FG2/SF2/RAW8。 |
| 10 | API06 实际备货回传 | PASS | 订单 1578 UI 按钮；API Log 10755 / Idempotency 9036；Mock 第 22 行；`evidence/api06_callback_success_2157.png`、`api06_mock_request_response.json`。 |
| 11 | API08 离仓状态及三字段回传 | PASS | API Log 10756 / Idempotency 9037；Payload `outboundOrderNo/action/shipmentConfirmed`；Mock 第 23 行；`evidence/api08_outbound_status_success.png`。 |
| 12 | API09 出库后查询 | PASS | API Log 10757；`inventoryList` 显示 FG2/SF2/RAW8；只读。 |
| 13 | API05 盘点指令 | PASS | API Log 10759；订单 1070；Idempotency 9038 succeeded；Mock 入站日志及 ORM 确认实盘前库存不变。 |
| 14 | UI 实盘及 API10 回传 | PASS | UI 保存/重开核验六条实盘行并勾选，按钮实际 POST；API Log 10760、Mock 第 24 行；最终库存不变。 |

正式 Run 开始后禁止变更代码、模块、数据库、业务配置、权限与 Mock Endpoint。遇到实际缺陷时，保留本轮失败证据并停止；不得将本 Run 修补成 PASS。


## 正式 Run 开始

- 开始时间（Asia/Shanghai）：`2026-11-27T16:15:53+08:00`。
- 冻结起点：代码/Manifest `.56`、数据库 `odooce_karlrapp`、权限、API Endpoint 和三个本地 Mock。正式业务请求从 API07 开始；后续只允许执行本指南顺序，不调整业务配置。
- 捕获基线：API02 13 行，API04 12 行，API06/API08/API10 21 行。
- Run 状态：**COMPLETE — 模拟 HVR PASS**。


## 正式 Run 完成结果（2026-11-27）

**Codex 本地模拟 HVR：PASS。** 使用 `ginlong_apis 18.0.2.0.56`、本地数据库 `odooce_karlrapp`、本机 Odoo 8099 和本地 Mock 完成 API01–API10 同一业务主链；执行期间未修改代码、模块版本、Endpoint、仓库 Route 或权限配置。前置全量自动化为 96 post-tests / 100 methods，0 fail、0 error；该结果是准备证据，本次 PASS 还依赖下列真实 HTTP、浏览器 UI、Mock 与 ORM 断言。

| 节点 | 实际最终业务结果 | 证据摘要 |
|---|---|---|
| 入库 | API01 建入库客户指令；API02 先 N 后 Y；UI 只完成一张 Incoming Picking 2156 | Logs 10749–10752；Idempotency 9031–9034；入库后实物 FG4/SF2/RAW12 |
| 出库 | API03 建出库指令；UI 只完成一张 Delivery Orders Picking 2157；包含 PALLET-002 整托与 PALLET-001 拆托 | Log 10754、10755；Picking 2157 是唯一关联 Done/outgoing；API06 POST 实绩，不另外扣库存 |
| 离仓 | API08 在同一出库订单确认离仓；仅改变业务状态并发送 V3.2 三字段 | Log 10756 / Idempotency 9037；无第二张 Picking、无第二次库存移动 |
| 盘点 | API05 创建客户盘点指令；UI 保存六条实际盘点结果；API10 从已保存实盘记录回传 | API05 Log 10759 / Idempotency 9038；API10 Log 10760；Mock 实收成功 |
| 最终库存 | 成品 2、半成品 2、原材料 8；reserved 均为 0；托盘与 SN 留存符合整托/拆托实际作业 | ORM 只读快照 `evidence/final_orm_snapshot.json`；API09 Log 10757 与 Mock/API Log 输出相符 |

API06、API08、API10 的真实按钮请求与 Mock 响应分别保存在 `evidence/api06_mock_request_response.json`、`api08_mock_request_response.json`、`api10_mock_request_response.json`。实际 API10 回传页面截图为 `evidence/api10_callback_success.png`。Mock 捕获对应本 Run 正式请求分别为第 23、24、25 行（历史捕获未删除）。

API05 成功幂等记录为 9038；API10 的成功 HTTP Log 为 10760。API10 在 CC-GIN-010 中明确保持原有行为，本 Run 不扩展其重复回传确认机制。API09 不使用持久化幂等。

**判定区分：** 本 Run 的 Codex 内置浏览器模拟 HVR 为 PASS；项目负责人亲自操作的真实人工 HVR 仍为 NOT RUN；真实 Ginlong/Karl Rapp/KR Gateway 联调也未执行。
