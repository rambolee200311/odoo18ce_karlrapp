# Ginlong 项目级仓库业务流程 HVR 指南

**状态：** 新建项目主线；全部用例初始为 `NOT RUN`。人工操作和 PASS/FAIL 由业务验收人完成。

## 1. 验收原则

本指南是 API01–API10 本地项目 HVR 的主入口。测试按一条连续仓库业务链执行：产品主数据 → 客户入库指令 → 收货确认 → 实际入库 → 库存查询 → 客户出库指令 → 实际备货 → 实际发货 → 再次查库存 → 客户盘点指令 → 仓库实盘结果 → 盘点回传。

后续步骤只能使用前序 Odoo/WMS 操作真实产生的数据。API01/03/05 是客户指令，不产生库存；API02 是订单级收货确认，不表示实际收货；只有通过现有 WMS 完成的 Incoming/Outgoing `stock.picking` 才改变库存；API05 是盘点指令，API10 只读取仓库实际盘点结果。禁止用手工建 `stock.quant`、直接改库存、计划数量或 API01 预报代替实际业务结果。

本地模拟 Picking 和盘点结果是由验收人在 Odoo 现有业务界面逐步操作形成的测试事实，不是通过 ORM、SQL 或库存调整补造的数据。Mock 只接收 Odoo 真正的回传 HTTP 请求。不得调用真实 Ginlong、生产环境或 KR Gateway。

API01 已关闭 HVR、API07 已关闭 HVR及其他单接口记录继续保留为历史证据；它们不是本项目主链的完成证据。本指南的主链使用新的共享数据集，旧单接口专项只作为主链之后的补充异常场景。

## 2. 共享数据集

| 对象 | 唯一测试值 | 来源及约束 |
|---|---|---|
| Odoo Project | `HVR01-20261121 API01 HVR Project` | 使用现有项目，不另建项目 |
| API User | `hvr_api01_manual` | 五个入站 API 使用同一个已配置该项目的 API User；API02/04/06/08/10 是同一项目单据上的按钮回传 |
| Owner 编码 | `HVR01-20261121-OWNER-A` | 复用现有货主；不得因接口方向切换 API User |
| API03 收货方 | `Ginlong Technologies Co., Ltd` | 复用现有未绑定其他项目的 Ginlong 联系人。该项目当前没有 `source_project_id` 收货方；API03 Payload 显式传此名称，避免依赖不存在的项目默认收货方 |
| Odoo 仓库 | `KarlRapp-WH` | 由项目配置关联；报文仓库编码 `KRWH` |
| Ginlong 产品编码 | `HVR-PROJECT-FLOW-20261125-SN-001` | 由 API07 首次 Add 创建，需通过第 3 节的无冲突预检 |
| 产品 | `HVR 项目级连续流程成品` | `productForm=成品`，模板 tracking 应为 serial；单位 `台`，单件重量 `1.25` |
| 批次 / 序列身份 | `HVR-FLOW-SN-001`、`HVR-FLOW-SN-002` | 本产品为序列号管理，实际作业中的 Odoo `stock.lot` 身份就是各自 SN；不另造一个没有业务来源的批次号 |
| 实际入库序列号 | `HVR-FLOW-SN-001`、`HVR-FLOW-SN-002` | 仅在实际 Incoming Picking 操作中建立/选择；每件数量 1。API01 STANDARD 预报不传 SN |
| 实际托盘/包裹 | `HVR-FLOW-PALLET-001` | 在收货作业中通过现有 WMS 录入/建立并关联；API04/API05/API06/API10 使用界面实际保存的名称，并沿用到出库及实盘（若实际作业保持同一包裹） |
| 入库单号 | `HVR-FLOW-20261125-IN-001` | API01；数量 2；`businessType=STANDARD`，不传 `snList` |
| 出库单号 | `HVR-FLOW-20261125-OUT-001` | API03；同一 owner、warehouse、productCode；数量 1 |
| 盘点单号 | `HVR-FLOW-20261125-COUNT-001` | API05；实际盘点范围根据出库后的现场实盘结果填写 |

**数据冲突处理：** 执行前在 Odoo 产品和单据中只读搜索上表产品编码及三个业务单号。若产品编码、单号或 SN 已存在，停止本轮并为整个数据集统一换一组新后缀；不可只改单个 API 的编码，也不可删除旧业务/幂等记录。若 Owner、Project、仓库或 API User 不匹配，停止并报告，不通过切换 API User 或手工建库存绕过。

## 3. 前置检查

1. 确认本地开发环境、数据库和模块正常；API01/03/05/07/09 共享同一个项目范围 API User，调用 Header 为 `Authorization: <access_token>`，不加 `Bearer`。不要把 key、secret 或 token 放入 Payload、文件或截图。
2. 五个入站 API 的 Object ID 为 API07=`TPL_Product_Master`、API09=`TPL_Stock_Query`、API01=`TPL_Pending_Receipt_Note`、API03=`TPL_Pending_Delivery_Note`、API05=`TPL_Stocktake_Order`。从项目根目录使用统一脚本发送：

   ```bash
   export GINLONG_HVR_BASE_URL='http://127.0.0.1:8099'
   read -rsp '本地 API User access token: ' GINLONG_HVR_TOKEN; export GINLONG_HVR_TOKEN; echo
   bash docs/ginlong_apis/hvr/project_flow/test_data/send_inbound_payload.sh TPL_Product_Master docs/ginlong_apis/hvr/project_flow/test_data/payloads/api07_add_shared_product.json
   ```

   后续请求仅替换 Object ID 和 Payload 路径。脚本只发入站 API；API02/04/06/08/10 必须使用 Odoo 页面按钮。
3. 管理员确认 API02/04/06/08/10 的 Endpoint 均指向本机 Mock；检查每个接收端健康状态和捕获文件当前行数。现有 API02/04 Mock 可沿用其接口专用脚本。API06/08/10 若没有可用本地接收端，先配置本地 Mock 再开始出站场景；不得临时改为真实 Ginlong URL。
4. 对 API09 做基线查询并保存完整响应。只比较新产品编码这一行；API09 返回的是 owner+warehouse 的完整库存列表，其他既有库存行不构成失败。
5. 记录基线时新产品不存在正库存；若已存在正库存，不能用库存调整清零，应换一个从未使用的新 `productCode` 并重做 API07 Payload。
6. 健康检查、无冲突预检、自动化/旧 HVR PASS 都不计为本轮项目级人工 HVR PASS。

### 本地 Mock Endpoint

- API02：`http://127.0.0.1:18102/API/WMS_JSON/TPL_Receipt_Confirmation`，使用 `api02/test_data/mock_api02_receiver.py`。
- API04：`http://127.0.0.1:18104/API/WMS_JSON/TPL_Inbound_Completion`，使用 `api04/test_data/mock_api04_receiver.py`。若要覆盖明确失败重试，可用 `--fail-first 1` 在 API04 首次回传前启动。
- API06、08、10：从项目根目录运行 `python3 docs/ginlong_apis/hvr/project_flow/test_data/mock_outbound_callbacks.py --host 127.0.0.1 --port 18106`；健康检查：`curl --fail --silent http://127.0.0.1:18106/__mock__/health`。在 Odoo Ginlong API Settings 中分别配置：
  - API06：`http://127.0.0.1:18106/API/WMS_JSON/TPL_Picking_Completed`
  - API08：`http://127.0.0.1:18106/API/WMS_JSON/TPL_Shipment_Completed`
  - API10：`http://127.0.0.1:18106/API/WMS_JSON/TPL_Stocktaking_Completed`

该 Mock 只追加保存三个接口由 Odoo 按钮发送的 JSON，不保存认证 Header；捕获文件为 `project_flow/test_data/outbound_received.jsonl`。配置前记录原 Endpoint，整轮 HVR 后在 Settings 恢复。不得把真实 Ginlong 地址改为 Mock，也不得将请求发给真实系统。Mock 不可达或 Endpoint 无法核实时，对应出站用例保持 `BLOCKED`。

## 4. 执行顺序与真实依赖

| 顺序 / HVR | API / 操作 | 使用的实际输入 | 关键预期与停止条件 |
|---|---|---|---|
| 01 `FLOW-07` | API07 Add 共享产品 | `payloads/api07_add_shared_product.json` | 成功后 Odoo 产品模板/owner 变体存在，`tracking=serial`。失败或产品已有时停止，不继续 API01。 |
| 02 `FLOW-09A` | API09 入库前库存基线 | `payloads/api09_owner_warehouse_query.json` | 新产品无正库存；查询只读。响应按产品编码定位，不要求整个 inventoryList 只有该产品。 |
| 03 `FLOW-01` | API01 Add 入库指令 | `payloads/api01_add_inbound.json` | 一个数量 2 的入库明细；STANDARD 场景省略 `snList`。只产生 Order 预报，不产生 Picking、Lot、托盘或库存。 |
| 04 `FLOW-02N` | API02 未确认收货回传 | 该 API01 入库 Order 当前 `status=planning` | 真按钮发送 `receiptConfirmed=N`。不创建 Picking，不改变库存。 |
| 05 `FLOW-02Y` | 业务收货确认后 API02 回传 | 同一入库 Order，实际业务操作后 `status=arrive/inbound` | 真正执行收货确认并检查业务日志后，按钮应发送 `receiptConfirmed=Y`；仍不等同入库过账。 |
| 06 `FLOW-IN` | 现有 WMS 收货操作 | API01 Order → 关联 Incoming Picking | 录入/扫描两个实际 SN，各 1 件，同一实际托盘；Validate 完成 Picking。库存 +2 仅由此 Picking 过账。 |
| 07 `FLOW-04` | API04 入库完成回传 | 当前订单关联的 Done/Incoming Picking、实际 move lines | 按 Picking 自动发送；核对两个实际 SN、数量、托盘、实际确认人和 `date_done`。不读 API01 预报替代实绩。 |
| 08 `FLOW-09B` | API09 入库后查询 | 同一 Owner + `KRWH` | 新产品实际物理数量为 2；不扣预留量。该库存只依赖 FLOW-IN 的 Done Picking；API04 回传失败不改变已过账事实，也不阻止查询，但 API04 自身仍记失败/阻塞。 |
| 09 `FLOW-03` | API03 Add 出库指令 | `payloads/api03_add_outbound.json` | owner/productCode 与 API07/API01 完全相同；API03 不创建 Picking、不预留、不改变库存。产品必须按 owner+productCode 匹配。 |
| 10 `FLOW-OUT-PICK` | 创建并完成备货作业行 | API03 Order → 现有出库 Picking | 从实际已入库两件中选择 `HVR-FLOW-SN-001`，数量 1；使用当前实际托盘/包裹和真实作业人/时间。不得任选一个别的 SKU。 |
| 11 `FLOW-06` | API06 备货完成回传 | 已保存的实际出库 move line / Picking | 从出库单 Ginlong 回传页操作；一张订单事件，托盘按实际 package 去重，重量来源为 API07 产品重量×实际数量，按保存后的数据核对。 |
| 12 `FLOW-SHIP` | Validate 出库 Picking | 上一步同一 Picking 和实际备货记录 | 完成真实 WMS 出库过账，库存 −1；不得直接写库存。留下的实际在库 SN 应为 SN-002。API06 回传异常不撤销实际备货或库存业务事实，单独记录回传结果。 |
| 13 `FLOW-08` | API08 发货完成回传 | 当前出库 Order 已保存的 `ginlong_shipment_detail_ids`，每条关联真实 Done/Outgoing `stock.move.line` | 在出库 Order 的 Ginlong 回传数据页，添加并保存实际发货作业行及 Y/N 发货状态，再点击按钮。系统只接受当前 Order 的实际 Outgoing 行（包括 `picking_Out` 关系）；内部备货行不能作为实际发货行。按已保存状态生成订单级 `shipmentConfirmed`；不得用 API06 回传代替实际发货。 |
| 14 `FLOW-09C` | API09 出库后查询 | 同一 Owner + `KRWH` | 新产品实际物理数量为 1；SN-002 是尚存实物。该查询依赖 FLOW-SHIP，不依赖 API08 回传成功；若与实际 Picking 不符，停止，不用调整库存修正。 |
| 15 `FLOW-05` | API05 客户盘点指令 | `payloads/api05_count_remaining_stock.json` | 盘点单使用相同 Owner、仓库、产品；计划 SN/托盘按前序出库和实际剩余作业范围填写。API05 只建客户指令，不产生实盘结果。 |
| 16 `FLOW-COUNT` | 仓库实际盘点 | 同一盘点单的 Actual Results | 由验收人执行现有盘点采集，录入真实观察到的产品、SN、数量、托盘、实盘操作人和时间。不得复制计划值冒充实盘，也不得读 stock.quant 推导实盘结果。 |
| 17 `FLOW-10` | API10 盘点完成回传 | 同一盘点单下已保存并勾选的实盘结果行 | 按真实按钮发送；Payload 只能来自 Actual Results。缺少需要的实盘操作人员外部编码时暂停该回传并记录 BLOCKED，不拿回传用户替代。 |

### 单据操作要点

- API01 Add 后，打开 **WorldDepot → Inbound → Orders** 找到新单。按现有 WMS 要求补充仅限 Odoo 必填的订单字段并保存；之后按页面已有业务入口 Confirm、收货确认、Create Receipt。API01 请求本身不产生这些操作。
- Incoming Picking 中每个序列号数量为 1。通过 Picking 的实际 Operations/详细作业行登记两个 SN 和实际 Package；Validate 后确认 Picking 为 Done，订单关联无误。若界面不支持形成两条实际 SN 行或托盘绑定，停止 HVR，不直接调用 ORM。
- API03 Add 必须在 API01 产品已创建且收货 Picking 已过账后执行。创建的出库单应与实际库存 SKU 一致。API03 接收成功不表示已预留/拣货。
- Outgoing Picking 实际选择 SN-001，保留 SN-002。先保存备货 move line 的来源包裹、实际操作人和时间，再点击 API06；之后完成实际出库 Validate，再维护 API08 发货明细并回传。若当前 WMS 页面顺序不同，按真实业务动作执行并记录页面事实，不为了通过 API 调换/伪造阶段。
- 拆托出库时分开核对**来源托盘追溯**与**当前托盘绑定**：备货 move line 的 `package_id` 记录被拣产品来自哪个托盘；`result_package_id` 记录是否进入另一个托盘。拆出的产品可以不再绑定原托盘，除非业务明确要求重新组托。验收应确认来源托盘可从作业记录追溯、留在原托盘的产品仍有正确绑定；不得因出库 move line 没有当前 `package_id`/`result_package_id` 就单独判失败。
- API08 从出库 Order 上已保存的发货明细及状态生成 Payload。实际 Outgoing Picking Done 后，在出库 Order 的 **Ginlong 回传数据**页添加实际发货作业行，选择该 Done/Outgoing Picking 对应的 move line，设置发货状态并保存；确认行显示正确产品、SN、数量和托盘后，点击“回传锦浪：发货完成”。实际 outbound picking 可能只通过 Order 的 `picking_Out` 关联，不能只按 Picking 的反向 `outbound_order_id` 查找；选择器不得把 Done 的内部备货 Picking 当成实际发货。该接口不要求重复录入产品、SN、数量或托盘事实。
- 完成 API09C 后再发 API05。API05 计划中的数量/范围是客户指令；发送前把 `api05_count_remaining_stock.json` 的 `palletCode` 与实际剩余序列号在 Odoo 中显示的包裹核对；若不同，只能按已观察到的实际包裹值修订客户盘点请求并保存实际发送版本，不能借 Payload 建立/改变包裹事实。仓库实际盘点必须单独执行并保存在 **WorldDepot → Stocktake → Customer Orders → Actual Results**，再由 API10 读取。Actual Results 必须来自实际盘点操作，不得复制计划 JSON 或根据 `stock.quant` 推算。API10 不写库存。

## 5. 本轮 Payload 清单

只把 `project_flow/test_data/payloads/` 内的 API07、01、03、05、09 文件用于本主链。回传 API02、04、06、08、10 没有外部请求 Payload 文件：必须点击 Odoo 真正业务按钮，由系统从持久化订单/作业/实盘数据生成并发送。`expected/` 是人工核对模板，绝不能用 curl 手工发送。

| 文件 | 用途 | 可执行时点 |
|---|---|---|
| [api07_add_shared_product.json](project_flow/test_data/payloads/api07_add_shared_product.json) | 创建主链唯一成品 | 第 01 步 |
| [api01_add_inbound.json](project_flow/test_data/payloads/api01_add_inbound.json) | API01 客户入库指令 | 第 03 步 |
| [api03_add_outbound.json](project_flow/test_data/payloads/api03_add_outbound.json) | API03 客户出库指令 | 第 09 步；不得提前用于另一货主/项目 |
| [api05_count_remaining_stock.json](project_flow/test_data/payloads/api05_count_remaining_stock.json) | API05 客户盘点范围 | 第 15 步；先核对实际剩余 SN/托盘 |
| [api09_owner_warehouse_query.json](project_flow/test_data/payloads/api09_owner_warehouse_query.json) | 同一 owner+warehouse 的库存快照请求 | 第 02、08、14 步 |
| [expected/](project_flow/test_data/expected/) | API02/04/06/08/10 按钮生成结果的核对模板 | 对应按钮发送后核对；不发送这些文件 |

API01、API03、API05、API07、API09 五个入站 HTTP API 沿用同一项目 API User，入口为本地 `POST /api/ginlong/{objectid}`。API02、04、06、08、10 是 Odoo 按钮发起的出站回传，不使用入站 API User Token。Token 不写入本指南；入站请求使用当前有效 Token，Header 不加 Bearer。

## 6. API09 数量连续性判定

API09 返回指定 Owner+仓库的完整产品清单。三个查询必须在相同 Owner=`HVR01-20261121-OWNER-A`、Warehouse=`KRWH` 下完成，并以唯一 SKU `HVR-PROJECT-FLOW-20261125-SN-001` 比较：

| 查询点 | 唯一 SKU 预期物理在库 | 产生该数量的实际业务 |
|---|---:|---|
| 入库前 | 0 或不返回该 SKU | 尚无此产品库存；若已有正数则换全套新 SKU |
| Incoming Picking Done 后 | 2 | 两个 SN 实际收货并 Validate |
| Outgoing Picking Done 后 | 1 | SN-001 实际发出，SN-002 留在仓库 |

库存变化应只发生在对应 Picking Validate。API01/02/03/04/05/06/07/08/09/10 的接收、回传或查询本身不得造成库存变化。API09 不减 `reserved_quantity`；若有预留，仍按协议读取物理 `quantity`。

## 7. 专项异常 HVR 的隔离

API01 bonded `snList`、API03 生命周期/跨货主/错误字段、API05 SN 错误输入、API07 22 项产品校验、API09 未知 owner/warehouse 隔离以及 API02/04/06/08 重复确认，可作为专项 HVR。它们可以使用专门单号或独立产品，但不得：

1. 删除、取消或修改主链 Owner、Project、SKU、入库单、已完成 Picking、剩余 SN/托盘或盘点结果。
2. 在主链完成前对主链 SKU 执行其他收发货、调整、预留或归档。
3. 清理 API Log、Event、幂等记录来“重置”一个已执行场景。
4. 使用旧 API05-10 对 API01-HVR-29 的依赖；本指南中的项目级数据源是新主链实际 Incoming Picking。

主链全部结束后，专项异常测试应使用单独的业务键，并优先使用独立 SKU/owner；若异常用例只验证请求拒绝，可复用有效编码作为输入，但不得执行会改动主链单据的 Edit/Del。

## 8. 未满足条件与判定

- 产品/订单/SN 唯一性预检未完成、Mock Endpoint 未指向本机、实际收货/出库 Picking 未 Done、API06 操作人/时间缺失、API10 实盘外部操作人编码缺失，均应把受影响场景标为 `BLOCKED`，不可用准备脚本或手工库存替代。
- 发生输入错误或响应错误时，先停下并记录该步请求/响应、业务单据和日志证据；不继续依赖该结果的后续步骤。
- 2026-11-26 Codex 模拟记录发现：出库单 `HVR-FLOW-20261125-OUT-001` 的内部备货 move line 有 `package_id=HVR-FLOW-PALLET-001`，但 Done/Outgoing Picking `KRWH/KROUT/00695` 对应 SN-001 的 `package_id` 与 `result_package_id` 均为空。API08 的回传功能已单独通过，但项目主链的托盘连续性断言未通过；不得把项目级整链标为 PASS，需由项目负责人确认后续 WMS 处理。
- 每个 API 的 PASS 必须同时具备真实 HTTP/按钮请求证据及对应业务结果证据。自动化、Mock 健康检查、静态 JSON 校验和单接口历史 HVR 均不能替代项目主链 HVR。
- 不覆盖历史执行记录，不由 Codex 代填人工 PASS/FAIL。

出站回传失败不会回滚已经完成的 WMS 收货、备货、发货或实盘业务事实。对应回传用例按重复回传指南修复/重试并记录；只有缺少实际业务前置数据时，依赖该事实的后续主线步骤才停止。不得把 Mock HTTP 成功当作 Picking 完成，也不得把 Picking 完成当作回传成功。

## 9. API01–API10 主线覆盖与依赖

| API | 主线操作 | 业务输入来源 | 前序条件 | 主线 Payload / 结果核验 |
|---|---|---|---|---|
| API01 | 创建入库指令 | Ginlong HTTP → `inbound.order` | API07 产品已建立；API09 基线确认无该 SKU 正库存 | `payloads/api01_add_inbound.json`；只建预报单，不产生托盘、Lot 或库存 |
| API02 | 回传收货确认 N/Y | 同一 `inbound.order.status` | API01 建单；先 N，再执行现有收货确认操作后 Y | Odoo 入库单按钮；对照 `expected/api02_*.json`；不依赖 Picking/move line |
| API03 | 创建出库指令 | Ginlong HTTP → `outbound.order` | 同一产品已真实入库，API09B 显示 quantity=2 | `payloads/api03_add_outbound.json`；无 Picking、预留或库存变化 |
| API04 | 回传入库完成 | API01 订单关联的 Done/Incoming `stock.picking` 和 move lines | FLOW-IN 实际收货过账 | 入库单按钮；逐 Picking Event；对照 `expected/api04_inbound.json` |
| API05 | 创建客户盘点指令 | Ginlong HTTP → `world.depot.stocktake.order` | 实际出库后 API09C 显示 quantity=1 | `payloads/api05_count_remaining_stock.json`；只写盘点计划 |
| API06 | 回传备货完成 | 出库订单选定的实际 Picking/move lines | FLOW-OUT-PICK 已保存实际备货数据；真实人员/时间可用 | 出库单按钮；订单级事件；对照 `expected/api06_picking.json` |
| API07 | 创建共享产品 | Ginlong HTTP → `product.template` / owner 变体 | 主线数据集预检通过 | `payloads/api07_add_shared_product.json`；其产品编码/Owner 后续各 API 共用 |
| API08 | 回传发货完成 | 出库 Order 已保存的发货明细状态；实际产品、SN、数量、托盘来自关联的 Done/Outgoing `stock.move.line` | FLOW-SHIP 完成并保存实际发货明细 | 出库单 Ginlong 回传数据页添加并保存实际 Outgoing 作业行及 Y/N 状态，再点击按钮；核对订单级 `shipmentConfirmed` 与 `expected/api08_shipment.json`。不得选择内部备货行 |
| API09 | 查询物理库存 | 同一 Owner + Warehouse 的 Odoo 库存记录 | 基线、FLOW-IN Done、FLOW-SHIP Done 三个检查点 | 同一个 `payloads/api09_owner_warehouse_query.json`；目标 SKU 数量 0→2→1 |
| API10 | 回传盘点完成 | 同一盘点单已保存、已选择的 `world.depot.stocktake.result` | API05 指令后，验收人真实完成实际盘点 | 盘点单按钮；对照 `expected/api10_actual_stocktake.json`；不写库存 |

主线业务执行次序仍按第 4 节，不按 API 编号排序。五个入站 API（01/03/05/07/09）共用同一个 API User 和同一项目；五个出站 API（02/04/06/08/10）从该主线上真实生成的单据或结果回传。某个回传接口的结果不得替代前序业务操作，例如 API04 成功不产生库存，API06 成功不代表出库完成，API10 成功不代表库存调整。

## 10. 与单接口 HVR 的关系

各 API 单独 HVR 保留为专项或历史证据。项目主链执行状态统一填写在[项目级执行记录](HVR_Project_Business_Flow_Execution_Record.md)。单接口目录的 README 和案例须引用本指南，标明主链依赖以及专项用例不得破坏主链。API02/API04 的旧独立入库订单 `HVR-GIN010-MANUAL-IN-20261125-01` 不再作为项目主链输入；除非另有专项需要，不要继续把它的操作结果接到本次 API03/05/09 数据上。

## 11. 2026-11-26 模拟收尾与真实人工 HVR 交接

本地 Codex 模拟主链最终结果见 [CC-GIN-005 模拟 HVR 最终验收报告](project_flow/CC-GIN-005_Final_Simulation_HVR_Report.md)。该轮沿 CC5HVR-20261126-* 数据完成入库、备货、拆托出库、库存查询及盘点回传。SN-001 在 Internal Picking 1934 上记录来源托盘，拆出后未重新绑定托盘；SN-002 保留在原托盘。来源托盘追溯判定 **PASS**，不要求拆出的产品继续绑定原托盘。API08 仍严格按 V3.2 三字段发送，托盘关系是独立的 WMS 作业记录核对。

当前模拟整体为 **PARTIAL**：订单 1401 的 API06 已通过真实 Odoo 按钮回传，API Log 9489、幂等记录 7967、本机 Mock 捕获第 12 行均成功。该次补发发生在 API08 和实际出库之后，故没有验证冻结主链要求的“API06 → 实际出库 → API08”顺序及 API06 后发货前库存仍为 2；API06 Payload 来源仍是 Done/Internal Picking 1934 的已保存备货数据。普通库存操作员权限也仍为 PARTIAL。详情见最终报告。

项目负责人真实人工 HVR 仍为 **NOT RUN**，不得使用 Codex 模拟记录代填人工结果。人工执行请使用独立数据集与步骤 [real_hvr_20261125/README.md](project_flow/real_hvr_20261125/README.md)，不要复用本地模拟的 CC5HVR-* 产品、订单、SN 或托盘。启动前按该 README 的 ORM 预检确认业务键可用，确认 API02/04/06/08/10 仅指向本地 Mock；入库、备货、出库和实盘结果均由人工在 Odoo 页面完成。

真实人工验收时，托盘来源追溯必须独立于 API08 报文判断：查看入库包裹、备货内部转移行的来源 `package_id` 与目的 `result_package_id`，以及剩余库存的实际托盘绑定。拆出的出库产品若没有当前托盘绑定，只要来源托盘仍可从作业记录追溯，且没有重新组托要求，就不判失败。API08 仅核对三字段 Payload；不修改 stock.quant 或伪造 Picking。
