# CC-GIN-007 人工 HVR 用例 v0.1 Draft

## 通用步骤

- 使用 README 中的本地 URL 和 Token；不要在 payload、截图或执行记录中公开 Token。
- 一次只运行本用例对应的 curl；成功 Add 不得重放。每例使用独立 inboundOrderNo。
- 成功预期 HTTP 200，响应仅有 returnStatus、exceptionInfo、operationTime，且为 Y/OK。
- 每次请求后先核对订单界面和 API 日志，再运行只读 ORM 脚本。不要清理或删除测试单据。

## HVR-API01-01 — 非保税 STANDARD，不带 snList

**目的：** 确认业务类型不等于保税类型时，即使订单产品为 SN 管理产品，也不要求客户预报 SN。

- 前置：Owner A 成品存在且 tracking=serial；单号未使用。
- 请求：[JSON](test_data/payloads/hvr_api01_01.json)；执行 [curl](test_data/curl/hvr_api01_01.sh)。
- 预期：Y/OK；创建一张入库 Order 和一条产品明细，quantity=1；无 SN 预报 JSON/子行；无实际 Picking、Move、Lot、Package 或库存变化。
- 后台：WorldDepot → Inbound → Orders，按单号搜索，确认业务类型 STANDARD 与产品数量。运行 ORM 检查，确认 forecast_sn_rows 为空、没有关联 Picking。
- 证据：HTTP 响应、订单编号/页面、ORM 输出、Ginlong API 日志。

## HVR-API01-02 — STANDARD 携带畸形 snList

**目的：** 确认非保税分支不处理客户 snList；即使容器格式错误，也不因该字段拒绝其余有效订单；API 日志仍记录收到的原始请求。

- 前置：Owner A 成品 tracking=serial；新单号。
- 请求：[JSON](test_data/payloads/hvr_api01_02.json)；执行 [curl](test_data/curl/hvr_api01_02.sh)。
- 预期：Y/OK；Order 成功，SN 预报 JSON/子行为空；共享 API 日志 request body 保留原始 snList 对象。日志保存原请求不表示业务持久化或接受它。
- 后台：确认订单产品数量；在 Ginlong API 日志按单号检索并确认请求内含原对象；ORM 输出确认 Order 未保存 SN 预报。
- 证据：响应、订单、日志 ID/截图、ORM 输出。

## HVR-API01-03 — 保税业务三产品、三托盘混装

**目的：** 验证 SN 产品和原材料的托盘预报分配、同产品跨托盘、每托盘混装及逐产品数量合计。

- 前置：Owner A 成品、半成品 tracking=serial；原材料 tracking=none；单号未使用。
- 请求：[JSON](test_data/payloads/hvr_api01_03.json)；执行 [curl](test_data/curl/hvr_api01_03.sh)。
- 预期：Y/OK。Order 产品总量为成品 4、半成品 2、原材料 12，结构化预报共 9 行：
  - PALLET001：成品两个不同 SN 各 1、半成品一个 SN 数量 1、原材料 5。
  - PALLET002：成品一个 SN 数量 1、原材料 4。
  - PALLET003：成品一个 SN 数量 1、半成品一个 SN 数量 1、原材料 3。
  - 每条真实 SN quantity=1；原材料 productSN=productCode，数量可以大于 1；逐产品汇总为 4/2/12。
- 后台：在入库 Order Form 确认三条产品明细。ORM 输出逐条列出序列号子行的 ginlong_product_code、serial_number、ginlong_quantity、ginlong_pallet_code。确认没有由 API01 创建的 Picking 或库存对象；不得将既有 pallets=1 当作实际托盘数。
- 证据：响应、订单、9 条预报行 ORM 输出、日志与幂等记录。

## HVR-API01-04 — 保税原材料不提供 snList

**目的：** 验证非 SN 管理原材料可以只提供客户订单总数量，不被要求虚构托盘或 SN 分配。

- 前置：Owner A 原材料 tracking=none；单号未使用。
- 请求：[JSON](test_data/payloads/hvr_api01_04.json)；执行 [curl](test_data/curl/hvr_api01_04.sh)。
- 预期：Y/OK；Order 保存原材料数量 12；不保存 SN 预报子行或虚拟 palletCode，不产生实际库存对象。
- 后台：核对 Order Form 和只读 ORM 输出；日志业务键对应本请求。
- 证据：响应、订单、ORM 输出、日志和幂等记录。

## HVR-API01-05 — 原材料跨托盘并与 SN 产品共托

**目的：** 验证原材料以 productSN=productCode 表达托盘分配时可大于 1，且可与 SN 产品共用托盘。

- 前置：Owner A 原材料 tracking=none、成品 tracking=serial；单号未使用。
- 请求：[JSON](test_data/payloads/hvr_api01_05.json)；执行 [curl](test_data/curl/hvr_api01_05.sh)。
- 预期：Y/OK；原材料总量 12，其中 PALLET001=5、PALLET002=7；成品一件为一条真实 SN，quantity=1，位于 PALLET001。原材料的两行合计 12；PALLET001 同时有原材料和成品。
- 后台：确认订单产品行和 ORM 预报子行；没有由 API01 创建的实际托盘或库存对象。
- 证据：响应、订单、预报行 ORM 输出、日志和幂等记录。

## HVR-API01-06 — SN 管理产品单条数量不为 1

**目的：** 验证保税类型下每条真实 SN 代表一件实物，不能用一个 SN 行承载多件。

- 前置：Owner A 成品 tracking=serial；单号未使用。
- 请求：[JSON](test_data/payloads/hvr_api01_06.json)；执行 [curl](test_data/curl/hvr_api01_06.sh)。
- 预期：HTTP 200、returnStatus=N、错误码 BUS01；消息指向单条 SN 数量错误，exceptionInfo 不超过 40 字符。完整 API 日志诊断应包含产品、SN、托盘和 quantity。
- 后台：订单不存在、没有订单明细、没有成功幂等记录、没有新库存对象；有失败 API 日志。
- 证据：响应、只读 ORM 结果、失败日志详情；保留失败记录。

## HVR-API01-07 — API04 从实际 Picking/Move Line 取数（补充项）

**目的：** 核实 API04 入库完成回传从已保存实际作业行读取，不使用 API01 客户预报代替实绩。

**报文说明：** 本用例没有供测试者提交的 Ginlong 请求 Payload，也没有 `curl`。API04 是 Odoo → Ginlong 的出站回传；用户在 Odoo 点击回传按钮后，Odoo 从已保存并选中的 Picking/Move Line 自动生成 JSON。下方的[预期出站报文](test_data/expected/hvr_api01_07_api04_body.json)只用于和本机 Mock 收到的内容逐字段比较，**不要把它作为请求发送给 Odoo，也不要手工录入 JSON**。

- 前置：仅使用现有开发数据中的已完成 Picking，且关联一张入库 Order；Move Line 已有真实产品、数量、Lot/SN、托盘、ginlong_operator_code 和 ginlong_operation_time。没有合格记录则 BLOCKED，不自行新建或过账 Picking。
- 准备：另开终端运行 test_data/mock_api04_receiver.py，记录它输出的本机 URL；先记录当前 API04 Endpoint。
- 操作：
  1. 在 Settings → General Settings → Ginlong APIs 临时把 API04 Endpoint 配为本机 Mock URL 并保存。
  2. 打开 WorldDepot → Inbound → Orders，搜索关联单据；在 Ginlong 回传数据 Notebook 中只勾选该 Picking 并保存 Order。
  3. 打开 Picking 的 Ginlong 回传数据页，核实每条实际 Move Line 已保存现场操作人编码和时间；不能用回传用户或点击时间替代。
  4. 回到 Order，点击“回传锦浪：入库完成”，目标仅为本机 Mock。
  5. 核对 Mock 实际收到的 POST JSON、HTTP 200/Y 响应和 API 日志；报文中的产品、SN、数量、托盘、操作人及操作时间来自所选 Move Line。
  6. 恢复原 API04 Endpoint，停止 Mock。
- 预期：Mock 仅收到所选已保存 Move Line 生成的数据；未选 Picking 不在报文中。候选 Picking 对应的参考 JSON 为 `test_data/expected/hvr_api01_07_api04_body.json`；API 日志记录本次请求和响应。此项不比较 API01 预报与实际收货，也不形成差异结论。
- 证据：Picking/Move Line 实际字段、Mock 接收报文、API 日志 ID、恢复 Endpoint 的记录。
- 判定：完成为 PASS；无合格现存 Picking 为 BLOCKED；不得为通过 HVR 创建库存记录。
- 当前记录：NOT RUN；CC-TEST-069 已通过，且项目负责人决定此补充 UI/Mock 核查不阻塞 CC-GIN-007 关闭。不得将本项改记为 PASS。
