# API07 产品档案 HVR 测试实例

> 本实例集属于已 Frozen / Closed 的 API07 HVR 包；记录的 PASS/判定及证据见 [执行记录](HVR_API07_Execution_Record.md)。

## 通用执行说明

- URL：`http://127.0.0.1:8099/api/ginlong/TPL_Product_Master`
- Method：`POST`
- Header：`Content-Type: application/json`、`Authorization: <测试 Token>`
- 每个 `test_data/payloads/*.json` 都是完整请求体；对应 `test_data/curl/*.sh` 是可执行 curl 请求，脚本会使用被忽略的 `.api07_hvr.env` 载入 Token。
- API07 对外响应严格使用 V3.2 响应结构，仅返回 `returnStatus`、`exceptionInfo`、`operationTime`；成功为 `returnStatus=Y`，业务失败为 `returnStatus=N`。Odoo 的 `success`、`data`、`error` 等通用字段不得出现在 API07 HTTP 响应中。
- Token 无效仍返回 HTTP 401，但响应体同样仅包含上述三个 Ginlong 字段。内部产品 ID 不由响应体提供，须通过 `owner + productCode` 在 Odoo 产品中核对。
- 后台产品路径：**WorldDepot → Ginlong APIs → 产品**。搜索产品名或 `Internal Reference`，打开 `product.product` 表单；用 `Ginlong Owner Code`、`Ginlong Product Code` 核对变体，再检查产品模板的 `Ginlong 物料属性` 页。显示 Ginlong 自定义字段需要 `Inventory / Administrator`（`stock.group_stock_manager`）权限。
- 后台日志路径：**WorldDepot → Ginlong APIs → API 日志**。打开每条日志，在“请求”“响应”页签核对请求及 Ginlong 协议响应。产品 API 日志目前没有自动填写 `source_record`，通过原始产品编码回查产品。
- 幂等记录模型没有业务菜单入口。执行 `test_data/verify_api07_hvr.py` 可用 Odoo ORM 只读打印产品、API 日志与 `ginlong.api.idempotency` 记录；不得直接 SQL 查询。
- 每例最终 HVR 状态依据项目负责人实际人工执行及明确判定记录；Codex 不代替人工操作或推翻负责人的验收判定。

## HVR07-01：新增货主 A 原材料

- **目的 / 前置**：新增首次出现的 Owner A + `productCode`。该编码应不存在。测试数据已准备 Owner A 联系人和 API Project。
- **完整 Payload**：[hvr07_01.json](test_data/payloads/hvr07_01.json)。**HTTP 执行**：[hvr07_01.sh](test_data/curl/hvr07_01.sh)。
- **预期响应**：HTTP 200；JSON 键仅为 `returnStatus`、`exceptionInfo`、`operationTime`，且 `returnStatus=Y`、`exceptionInfo=OK`。通过 Odoo 的 `owner + productCode` 核对新档案，不依赖响应内的 Odoo ID。
- **Odoo 检查**：在上述产品菜单按 `HVR07 原材料产品` 搜索；确认新建 1 个 `product.template` 和 Owner A 的 1 个变体。模板名、规格、`ginlong_unit=台`、可选字段按报文保存；`ginlong_product_form=原材料`、`tracking=none`。变体 `ginlong_owner_code=HVR07-20261119-OWNER-A`、原始编码和复合 `default_code` 与报文一致。
- **日志 / 幂等**：API 日志 1 条，响应仅含三个 Ginlong 协议字段。ORM 幂等键为 Owner A + RAW-A，`action=Add`、`state=succeeded`、`attempt_count=1`。
- **记录**：HVR07-01 人工状态 ____；证据链接/截图 ____。

## HVR07-02：重复 Add（相同及不同 Payload）

- **目的 / 前置**：HVR07-01 首次 Add 成功后，分别再次发送完全相同的报文和内容已变更的报文；两次请求的 `owner + productCode` 均与 01 相同。
- **完整 Payload**：[hvr07_02.json](test_data/payloads/hvr07_02.json) 与 01 逐字相同；变更报文见 [hvr07_02_changed.json](test_data/payloads/hvr07_02_changed.json)。执行脚本：[相同报文](test_data/curl/hvr07_02.sh)、[变更报文](test_data/curl/hvr07_02_changed.sh)。
- **预期响应**：两次均 HTTP 200；响应只包含三个 Ginlong 协议字段，`returnStatus=N`，`exceptionInfo` 明确提示 Duplicate API07 Add。重复 Add 不返回首次成功结果。
- **Odoo 检查**：产品菜单仍只有同一模板及 Owner A 变体各 1 个；变更报文中的名称、重量不得覆盖已保存档案。
- **日志 / 幂等**：三次 HTTP 请求各有独立 API 日志。仅首次 Add 建立成功幂等记录，重复 Add 在幂等重放前被拒绝，因此记录仍为 `state=succeeded`、`attempt_count=1`。通过 ORM 核对，不应出现第二个同 owner + productCode 变体。
- **记录**：HVR07-02 人工状态 ____；证据链接/截图 ____。

## HVR07-03：第二货主使用相同 productCode

- **目的 / 前置**：01 成功。Owner B 用相同 `RAW-A`、相同产品共享字段新增产品。
- **完整 Payload**：[hvr07_03.json](test_data/payloads/hvr07_03.json)。**HTTP 执行**：[hvr07_03.sh](test_data/curl/hvr07_03.sh)。
- **预期响应**：HTTP 200；仅返回三个 Ginlong 协议字段且 `returnStatus=Y`。在 Odoo 中确认 Owner B 变体新建，并与 Owner A 变体不同。
- **Odoo 检查**：产品菜单打开 Owner A / B 变体；两个 `product.product` 的 `ginlong_product_code` 相同、`ginlong_owner_code` 不同、`default_code` 不同，并关联同一个 `product.template`。模板不得重复创建或被覆盖。
- **日志 / 幂等**：新 Owner B 组合产生自己的 Add 幂等成功记录；日志请求/响应包含 Owner B 和 RAW-A。
- **记录**：HVR07-03 人工状态 ____；A 变体 ID ____；B 变体 ID ____；模板 ID ____。

## HVR07-04：相同编码跨货主 Edit 但 productForm 冲突

- **目的 / 前置**：03 成功，Owner B 已有相同 productCode 的独立变体，当前共享模板为原材料 / `tracking=none`。Owner B 以 `action=Edit` 和相同 productCode 发送 `productForm=成品`。
- **完整 Payload**：[hvr07_04.json](test_data/payloads/hvr07_04.json)。**HTTP 执行**：[hvr07_04.sh](test_data/curl/hvr07_04.sh)。
- **预期响应**：HTTP 200；仅返回三个 Ginlong 协议字段，`returnStatus=N`，`exceptionInfo` 指示共享字段冲突。使用 Edit 以区分共享属性冲突与重复 Add 拒绝。
- **Odoo 检查**：产品菜单确认模板仍只有一个，`productForm` 仍为原材料、tracking 仍为 none；A/B 变体、内部编码及模板字段均与发送前一致。
- **日志 / 幂等**：请求和失败响应留在 API 日志；失败业务事务回滚，不应留下成功幂等结果。日志状态列如显示成功，按测试计划中的已知日志问题记录，不以此替代响应体核对。
- **记录**：HVR07-04 人工状态 ____；证据链接/截图 ____。

## HVR07-05：半成品 tracking

- **目的 / 前置**：新增 Owner A 的独立半成品 productCode。
- **完整 Payload**：[hvr07_05.json](test_data/payloads/hvr07_05.json)。**HTTP 执行**：[hvr07_05.sh](test_data/curl/hvr07_05.sh)。
- **预期响应**：HTTP 200 成功。
- **Odoo 检查**：产品菜单确认 1 个模板及 1 个 Owner A 变体；`ginlong_product_form=半成品`、`tracking=serial`，规格、单位及可选字段与报文对应。
- **日志 / 幂等**：一条成功 API 日志；该 Owner + Product Code 有一条 `Add/succeeded` 幂等记录，尝试次数 1。
- **记录**：HVR07-05 人工状态 ____；变体 ID ____；模板 ID ____。

## HVR07-06：成品 tracking

- **目的 / 前置**：新增 Owner A 的独立成品 productCode。
- **完整 Payload**：[hvr07_06.json](test_data/payloads/hvr07_06.json)。**HTTP 执行**：[hvr07_06.sh](test_data/curl/hvr07_06.sh)。
- **预期响应**：HTTP 200 成功。
- **Odoo 检查**：产品菜单确认 `ginlong_product_form=成品`、`tracking=serial`，其他字段按报文保存。
- **日志 / 幂等**：一条成功 API 日志和一条 `Add/succeeded` 幂等记录。
- **记录**：HVR07-06 人工状态 ____；变体 ID ____；模板 ID ____。

## HVR07-07：Edit 第一次修改名称和规格型号

- **目的 / 前置**：准备脚本已建立 Owner A 的 EDIT-NAME 基准产品；这是该产品的第一次 Edit，修改 `productName` 和 `specificationModel`。
- **完整 Payload**：[hvr07_07.json](test_data/payloads/hvr07_07.json)。**HTTP 执行**：[hvr07_07.sh](test_data/curl/hvr07_07.sh)。
- **契约预期**：HTTP 200 成功，原变体 ID 不变；模板名称及规格更新为报文值，tracking/其他未变字段保持原值。
- **当前代码状态**：模块 `18.0.2.0.26` 已修复 Edit 对既有产品共享字段的更新；不存在的 owner/productCode 目标返回 `BUS03`，不得创建新产品。项目负责人复测前，确认 Odoo 中已存在目标变体且名称/规格为基准值。
- **Odoo 检查**：当前复测基准为变体 ID 1544 / 模板 ID 1471；基准名称“HVR07 名称修改旧值”、规格型号“HVR07-NAME-OLD”。响应成功后应仍为原 ID，名称和规格改为请求值。
- **日志 / 幂等**：Edit 按 repeatable 规则，每次都实际处理，不应生成 Add 的成功重放记录；每次 HTTP 调用各留一条日志。缺少目标的 BUS03 请求不得创建部分产品或模板。
- **记录**：HVR07-07 已于 2026-11-20 复测通过；API 日志 ID 1828，变体 ID 1544 / 模板 ID 1471 保持不变，详见 `HVR_API07_Execution_Record.md`。

## HVR07-08：同一产品第二次 Edit 修改单位及可选属性

- **目的 / 前置**：HVR07-07 已成功后，对同一 OWNER-A + EDIT-NAME 再执行第二次 Edit。保留 07 更新后的名称、规格，把 `unit` 从“台”改为临时同类别测试单位 `HVR07-20261119-UNIT-ALT`，并修改 `power`、重量/尺寸。
- **完整 Payload**：[hvr07_08.json](test_data/payloads/hvr07_08.json)。**HTTP 执行**：[hvr07_08.sh](test_data/curl/hvr07_08.sh)。
- **契约预期**：HTTP 200 成功，变体 ID、模板 ID 不变；单位及请求中变更的可选模板属性更新。
- **当前代码状态**：API07 Edit 已允许更新既有产品的共享模板字段；HVR07-07 已通过，可按顺序执行本例。产品形态冲突仍按 BUS02 拒绝。
- **Odoo 检查**：产品菜单搜索 EDIT-NAME；修复后检查 HVR07-07 的名称/规格仍保留，`ginlong_unit=HVR07-20261119-UNIT-ALT`、Odoo UoM 指向该同类别单位、重量/尺寸更新，owner/productCode 和 ID 不变。
- **日志 / 幂等**：同一 Edit 按 repeatable 策略；每个实际请求独立日志，成功 Edit 不要求持久幂等结果。成功时确认既有模板/变体 ID 不变并核对请求字段更新。
- **记录**：HVR07-08 已于 2026-11-20 复测通过；API 日志 ID 1830，变体 ID 1544 / 模板 ID 1471 保持不变，UoM 更新至 ID 35，详见 `HVR_API07_Execution_Record.md`。

## HVR07-09：相同 Payload 多次 Edit

- **目的 / 前置**：Owner A 的 EDIT-REPEAT 基准产品必须存在，且字段与 Payload 相同。当前已通过现有 API07 业务服务准备变体 ID 1562 / 模板 ID 1486。项目负责人此前在基准不存在时提交过一次请求并收到 BUS03（日志 ID 1832）；该请求只证明缺少目标时不会误创建产品，不计为重复 Edit 验收。现在对同一 JSON 连续执行两次。
- **完整 Payload**：[hvr07_09.json](test_data/payloads/hvr07_09.json)。**HTTP 执行**：[hvr07_09.sh](test_data/curl/hvr07_09.sh)，执行两次。
- **预期响应**：两次均 HTTP 200 成功并返回相同变体 ID。
- **Odoo 检查**：产品菜单确认模板和变体数量不增加，原有字段和值不变。
- **日志 / 幂等**：两次 HTTP 请求各有一条 API 日志；Edit 为 repeatable，不应因同 Payload 短路，也不应写入 Add 的持久化成功幂等记录。通过 ORM 确认处理结果。
- **记录**：HVR07-09 PASS；有效重复 Edit 两次日志 ID 1834 / 1836。首次缺前置数据的 BUS03 日志 ID 1832 保留，详见执行记录。

## HVR07-10：未配置单位自动加入 Unit 类别

- **目的 / 前置**：V3.2 将 `unit` 定义为 VARCHAR(40)，未规定枚举；使用当前 Odoo 尚不存在的单位名，验证 API07 自动在标准 `Unit` 类别创建单位，换算因子为 1，再创建产品。
- **完整 Payload**：[hvr07_10.json](test_data/payloads/hvr07_10.json)。**HTTP 执行**：[hvr07_10.sh](test_data/curl/hvr07_10.sh)。
- **预期响应**：HTTP 200；仅返回三个 Ginlong 协议字段，`returnStatus=Y`、`exceptionInfo=OK`。
- **Odoo 检查**：在 `uom.category` 的标准 `Unit` 类别内找到同名单位，因子/倒数均为 1，产品使用该单位；产品列表有且仅有一个 RETRY 产品变体，属性与报文一致。
- **日志 / 幂等**：成功 API 日志；API07 Add 有一条成功幂等记录，重复 Add 不得再次创建或改写产品。
- **本地代码预检**：模块 `18.0.2.0.27` 已升级；定向自动化测试 3 PASS、0 FAIL、0 ERROR。原人工请求于 10:14:28 返回 BUS01（旧行为）；项目负责人于 10:30:26 重发成功，见执行记录。
- **记录**：HVR07-10 PASS；API 日志 ID 1850；单位 ID 40；产品变体 ID 1570 / 模板 ID 1492；自动化和 ORM 复核见执行记录。

## HVR07-11：同键不同单位的重复 Add 拒绝

- **目的 / 前置**：HVR07-10 已成功；保持相同 `owner + productCode`，使用 `unit=台` 的不同 Payload 再执行 Add，验证首次成功后的重复新增策略优先拒绝请求。
- **完整 Payload**：[hvr07_11.json](test_data/payloads/hvr07_11.json)。**HTTP 执行**：[hvr07_11.sh](test_data/curl/hvr07_11.sh)。
- **预期响应**：HTTP 200；`returnStatus=N`，`exceptionInfo=IDM07: 重复新增，冲突键(owner, productCode)`。
- **Odoo 检查**：仍只有 HVR07-10 创建的一个 RETRY 变体；单位仍为 HVR07-NO-SUCH-UOM，不被改为“台”，无第二个模板/变体。
- **日志 / 幂等**：HVR07-10 成功日志和 HVR07-11 IDM07 失败日志各一条；幂等记录仍为唯一一条成功 Add、尝试次数 1。
- **记录**：HVR07-11 PASS；`unit=台` 的人工请求日志 ID 1854 返回 IDM07，产品仍使用 HVR07-10 建立的 UoM ID 40；日志 1852 是更早的相同 Payload 重复请求。

## HVR07-12：拒绝未支持的 productForm

- **目的 / 前置**：用 V3.2 外的形态值“包装物”验证业务规则拒绝。
- **完整 Payload**：[hvr07_12.json](test_data/payloads/hvr07_12.json)。**HTTP 执行**：[hvr07_12.sh](test_data/curl/hvr07_12.sh)。
- **预期响应**：HTTP 200；仅返回三个 Ginlong 协议字段，`returnStatus=N`，`exceptionInfo=BUS06: productForm仅支持原材料/半成品/成品`。
- **Odoo 检查**：产品菜单搜索 BAD-FORM，不应有模板或变体；其他已有产品模板不变化。
- **日志 / 幂等**：请求和错误响应有日志；无成功幂等行。
- **历史执行**：2026-11-20 10:40:09 首次返回 `BUS01: 业务处理失败`（API 日志 ID 1856），实际诊断为 `productForm=包装物` 不在允许枚举内；这是旧响应映射过于笼统，不能记为通过。
- **复测结果**：2026-11-20 14:38:46 返回预期 `BUS06: productForm仅支持原材料/半成品/成品`。此前 14:38:40 的过期 Token 请求记录为独立认证失败，不计入本用例。
- **ORM 证据**：API 日志 ID 1923，`success=False`、错误码 `BUS06`，诊断列出非法值及允许枚举；按 owner + productCode 查询不到产品变体或模板，也没有对应成功幂等记录。
- **记录**：HVR07-12 PASS；首次 BUS01 失败记录（日志 ID 1856）保留。

## HVR07-13：缺少 owner

- **目的 / 前置**：删除必填 `owner`，其余字段保留；Payload 使用已有 RAW-A 编码，用于验证校验先于幂等/业务查询。
- **完整 Payload**：[hvr07_13.json](test_data/payloads/hvr07_13.json)。**HTTP 执行**：[hvr07_13.sh](test_data/curl/hvr07_13.sh)。
- **预期响应**：HTTP 200；仅返回三个 Ginlong 协议字段，`returnStatus=N`，`exceptionInfo=REQ01: 缺失字段: owner`。
- **Odoo 检查**：产品菜单核对原有 Owner A RAW-A 模板/变体 ID 和字段均未改变。
- **日志 / 幂等**：日志请求保留缺失字段报文和错误响应；校验失败不产生幂等行。
- **历史结果**：2026-11-20 14:40:15 首次请求返回 `REQ01: 必填字段校验失败`，日志 ID 1925；日志诊断已指出 `owner is missing`，旧版对外响应未展示该原因。
- **复测结果**：模块 `.31` 升级后，2026-11-20 14:59:30 返回 `REQ01: 必填字段错误: owner is missing`，日志 ID 1947；HVR07-13 已通过。`.32` 将提示压缩为完整字段名列表格式。
- **额外请求**：14:59:46 的日志 ID 1949 中 `owner` 被填为“原材料”，而 `productForm` 缺失；系统据实提示 `productForm is missing`。该请求不是本用例的缺失 owner 场景，不改变 HVR07-13 结果。
- **多字段补充验证**：项目负责人于 2026-11-20 15:31:27 重发同时缺少 `owner`、`productForm` 的请求，返回 `REQ01: 缺失字段: owner, productForm`。API 日志 ID 1995 的完整诊断为 `Required fields: owner is missing; productForm is missing`，确认两项均被收集。
- **ORM 证据**：日志 ID 1995 的请求数据确实缺少 `owner` 和 `productForm`；该时段 API07 幂等新增数为 0。ORM 查询仍只有原有 RAW-A 两个货主变体 ID 1513、1519，共享模板 ID 1451；名称、`productForm=原材料`、`tracking=none` 保持原值。
- **记录**：HVR07-13 单字段及多字段必填校验均 PASS；旧版通用提示和截断响应记录（日志 ID 1925、1951）保留。

## HVR07-14：owner 为 null

- **目的 / 前置**：必填 owner 明确传 null，产品编码独立。
- **完整 Payload**：[hvr07_14.json](test_data/payloads/hvr07_14.json)。**HTTP 执行**：[hvr07_14.sh](test_data/curl/hvr07_14.sh)。
- **预期响应**：HTTP 200，失败响应指出 `owner` 空值。
- **Odoo 检查**：产品菜单搜索 NULL-OWNER，不应产生记录。
- **日志 / 幂等**：请求/响应可查；必填校验失败，不留幂等记录。
- **实际结果**：2026-11-21 01:15:55 返回 `REQ01: 空值字段: owner`；API 日志 ID 1999，诊断为 `owner is empty`。
- **ORM 证据**：请求中 `owner=null`；编码 `HVR07-20261119-NULL-OWNER` 无产品变体、无幂等记录。
- **记录**：HVR07-14 PASS；用户未提供 HTTP 状态码，原始响应及日志 ID 1999 为证据。

## HVR07-15：productCode 为空字符串

- **目的 / 前置**：必填产品编码传空字符串。
- **完整 Payload**：[hvr07_15.json](test_data/payloads/hvr07_15.json)。**HTTP 执行**：[hvr07_15.sh](test_data/curl/hvr07_15.sh)。
- **预期响应**：HTTP 200，错误路径指出 `productCode` 为空。
- **Odoo 检查**：产品菜单搜索 HVR07 标记的新产品；不应有空编码创建或其他副作用。
- **日志 / 幂等**：请求/响应留日志；校验失败不留幂等行。
- **实际结果**：2026-11-21 01:17:55 返回 `REQ01: 空值字段: productCode`；API 日志 ID 2001，诊断为 `productCode is empty`。
- **ORM 证据**：请求 `productCode=""`；货主 A 下无空编码产品变体，测试业务键无幂等记录。
- **记录**：HVR07-15 PASS；用户未提供 HTTP 状态码，原始响应及日志 ID 2001 为证据。

## HVR07-16：productName 纯空格

- **目的 / 前置**：必填产品名称仅包含空格，编码独立。
- **完整 Payload**：[hvr07_16.json](test_data/payloads/hvr07_16.json)。**HTTP 执行**：[hvr07_16.sh](test_data/curl/hvr07_16.sh)。
- **预期响应**：HTTP 200，错误路径指出 `productName` 为空。
- **Odoo 检查**：产品菜单搜索 BLANK-NAME 编码，不应创建模板/变体。
- **日志 / 幂等**：检查完整响应 JSON；字段校验失败不留幂等行。
- **实际结果**：2026-11-21 01:18:56 返回 `REQ01: 空值字段: productName`；API 日志 ID 2003，诊断为 `productName is empty`。
- **ORM 证据**：请求名称为三个空格；编码 `HVR07-20261119-BLANK-NAME` 无产品变体、无幂等记录。
- **记录**：HVR07-16 PASS；用户未提供 HTTP 状态码，原始响应及日志 ID 2003 为证据。

## HVR07-17：productForm 为 null

- **目的 / 前置**：产品形态必填字段传 null。
- **完整 Payload**：[hvr07_17.json](test_data/payloads/hvr07_17.json)。**HTTP 执行**：[hvr07_17.sh](test_data/curl/hvr07_17.sh)。
- **预期响应**：HTTP 200，错误路径指出 `productForm` 空值。
- **Odoo 检查**：产品菜单搜索 NULL-FORM，不应创建模板/变体。
- **日志 / 幂等**：检查请求与 `returnStatus=N` 响应；无幂等行。
- **实际结果**：2026-11-21 01:19:50 返回 `REQ01: 空值字段: productForm`；API 日志 ID 2005，诊断为 `productForm is empty`。
- **ORM 证据**：请求 `productForm=null`；编码 `HVR07-20261119-NULL-FORM` 无产品变体、无幂等记录。
- **记录**：HVR07-17 PASS；用户未提供 HTTP 状态码，原始响应及日志 ID 2005 为证据。

## HVR07-18：DECIMAL weight 非法文本

- **目的 / 前置**：可选 DECIMAL 字段传 `"abc"`，确认非空非法值不被当作缺省值或 0。
- **完整 Payload**：[hvr07_18.json](test_data/payloads/hvr07_18.json)。**HTTP 执行**：[hvr07_18.sh](test_data/curl/hvr07_18.sh)。
- **预期响应**：HTTP 200、失败 JSON，错误路径指向 `weight` 类型；不得创建产品或把重量保存成 0。
- **Odoo 检查**：产品菜单搜索 BAD-WEIGHT，不应有模板/变体。
- **日志 / 幂等**：错误 JSON 和报文留日志；字段类型校验在业务处理前失败，无幂等行。
- **实际结果**：2026-11-21 01:20:18 返回 `TYP01: 类型错误字段: weight`；API 日志 ID 2007，详细原因为 `weight must be a decimal number or numeric string`。
- **ORM 证据**：请求 `weight="abc"`；编码 `HVR07-20261119-BAD-WEIGHT` 无产品变体、无幂等记录。
- **记录**：HVR07-18 PASS；用户未提供 HTTP 状态码，原始响应及日志 ID 2007 为证据。

## HVR07-19：VARCHAR productName 传数字（已执行，项目负责人判定 PASS）

- **目的 / 前置**：验证项目负责人接受的 JSON number 名称能否经 API07 写入 Odoo 文本名称字段。
- **完整 Payload**：[hvr07_19.json](test_data/payloads/hvr07_19.json)。**HTTP 执行脚本**：[hvr07_19.sh](test_data/curl/hvr07_19.sh)。
- **验收规则**：项目负责人确认数值 `12345` 可作为该产品名称；依据 V3.2 的 VARCHAR 定义，现有校验器不对该文本字段执行类型检查，Odoo `Char` 字段将其持久化为文本 `12345`。
- **实际结果**：项目负责人于 2026-11-21 01:21:35 执行后收到成功响应；API 日志 ID 2009 记录 `productName=12345`（JSON number）及成功结果。
- **ORM 证据**：创建了变体 ID 1614 / 模板 ID 1525，模板名称存为字符串 `'12345'`；幂等记录 ID 1543 为 `succeeded`、attempt_count=1。
- **记录**：HVR07-19 PASS（项目负责人于 2026-11-21 明确判定该名称有效）。该判定不改变 V3.2 字段类型定义；保留已创建档案和验收证据。

## HVR07-20：productForm 使用数字类型

- **目的 / 前置**：必填 productForm 传 JSON number，而非三种有效文本值。
- **完整 Payload**：[hvr07_20.json](test_data/payloads/hvr07_20.json)。**HTTP 执行**：[hvr07_20.sh](test_data/curl/hvr07_20.sh)。
- **预期响应**：HTTP 200 失败 JSON，错误指出 productForm 必须为允许值；不创建产品。
- **Odoo 检查**：产品菜单搜索 BAD-FORM-TYPE，无模板/变体。
- **日志 / 幂等**：有效 Token 请求有日志，字段业务拒绝没有成功幂等记录。
- **实际结果**：2026-11-21 01:22:06 返回 `BUS06: productForm仅支持原材料/半成品/成品`；日志 ID 2011 的诊断记录非法值 `7`。
- **ORM 证据**：编码 `HVR07-20261119-BAD-FORM-TYPE` 无产品变体、无幂等记录。
- **记录**：HVR07-20 PASS；用户未提供 HTTP 状态码，原始响应及日志 ID 2011 为证据。

## HVR07-21：无效 Token

- **目的 / 前置**：请求体完整，Authorization 使用无效 Token。
- **完整 Payload**：[hvr07_21.json](test_data/payloads/hvr07_21.json)。**HTTP 执行**：[hvr07_21.sh](test_data/curl/hvr07_21.sh)。
- **预期响应**：认证失败，三个 Ginlong 错误字段，`returnStatus=N`、`AUTH01`。
- **初次尝试**：01:22:35 返回成功并产生日志 ID 2013；ORM 显示该次使用关联 Project 146 的有效 API User，创建变体 ID 1615 / 幂等记录 ID 1545，不属于无效 Token 验收。记录保留，不删除。
- **纠正后复测**：01:25:47 返回 `AUTH01: API认证失败`；日志 ID 2019 诊断为 `Invalid token`。该次使用新业务键 `INVALID-TOKEN1`，没有产品或幂等记录。
- **记录**：HVR07-21 PASS（以纠正后的无效 Token 请求为准）；初次误用有效 Token 的副作用作为历史记录保留。

## HVR07-22：Token 有效但 API User 未配置 WMS Project

- **目的 / 前置**：使用有效 Token，Token 对应 API User 但 Project 为空。
- **完整 Payload**：[hvr07_22.json](test_data/payloads/hvr07_22.json)。**HTTP 执行**：[hvr07_22.sh](test_data/curl/hvr07_22.sh)。
- **项目负责人判定**：项目负责人确认最终 `AUTH01` 响应可将 HVR07-22 记为 PASS。
- **历史误用**：01:23:28 返回成功，日志 ID 2015 的 `project_id=146`；该请求使用了有 Project 的 API User，创建变体 ID 1616 / 幂等记录 ID 1546，不属于本用例有效验收，记录保留。
- **复测结果及证据**：01:26:38 返回 `AUTH01: API认证失败`；日志 ID 2021 的诊断为 `Invalid token`。本地未配置 Project 的 API User（ID 111，Project 为空）及其 Token（ID 211）仍存在；但本次响应说明发送的 Token 未被服务识别，未实际证明“有效 Token 且无 Project”的处理路径。
- **记录**：HVR07-22 PASS（项目负责人判定）；同时保留 Token 不匹配的证据限制，不将其表述为已验证业务错误原因。
