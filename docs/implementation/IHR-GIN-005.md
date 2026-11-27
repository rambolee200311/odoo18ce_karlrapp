# 实施历史记录：IHR-GIN-005

| 字段 | 值 |
|---|---|
| IHR 版本 | v0.22 |
| CC 基线 | [CC-GIN-005 v1.1 Frozen with Open Items](CC-GIN-005-v1.1.md) |
| 上游基线 | SRS v1.1；TDD v1.0；Implementation Plan v1.8 |
| 当前状态 | CC-GIN-005 In Progress；API07 HVR 已 Closed；完整项目状态及权限边界仍按原记录跟踪 |
| 环境 | Odoo 18；既有 `venv`、`odoo.conf`、数据库 `odooce_karlrapp` |
| 执行者 | Codex |

## 0. 授权与边界

项目负责人批准全部冻结基线并授权进入 CC-GIN-005 实施。本记录仅覆盖本地开发数据库、Odoo 自动化、ORM 核验和 localhost Mock HTTP。没有访问生产环境、真实 Ginlong、Karl Rapp WMS、Gateway、VPN 或 FTP。数据库读写均通过 Odoo ORM；没有直接 SQL、`psql` 或数据库驱动访问。没有新增、安装或使用 `stock_barcode`。

业务边界继续按冻结基线执行：Ginlong 下达指令，Odoo 管理 Order 并交换数据；Karl Rapp 执行现场作业；Odoo 的实际执行记录使用标准 `stock.picking`、`stock.move.line` 和原生库存台账。API01/03 收单不代表仓库执行，不增加库存。盘点指令与仓库实盘结果分离；API10 读取 `worlddepot` 实盘结果，不读写 `stock.quant`。

## IHR-001 — 产品模板/变体和现有数据迁移

- **实现：** 一个 Ginlong 原始 `productCode` 对应一个 `product.template`；每个 `owner` 在该模板下建立原生 `product.product` 变体。模板保存共享产品属性和 `productForm` / SN tracking；变体保存 owner、原始 `ginlong_product_code` 及内部唯一 `default_code`。内部编码使用无歧义编码函数 `ginlong_internal_code(owner, raw_code)`，API payload 和 API09 响应继续使用原始编码。
- **API07：** 仅接受“原材料”“半成品”“成品”；原材料对应 `tracking='none'`，半成品/成品对应 `tracking='serial'`。同一 `productCode` 的共享产品属性冲突拒绝且不改旧模板。无效值拒绝。
- **API01/API03：** 入库和出库明细按 `(owner, productCode)` 找原生产品变体；API01 对货主编码执行复用/不存在时创建，API03 不自动创建货主或产品。请求处理不建立/过账 Picking，不产生库存变化。
- **WMS 查找：** `worlddepot` 共享产品查询优先按 Ginlong 原始 productCode + owner code 消歧；唯一的 legacy `default_code` / barcode 查询仍保持旧路径；多条 raw code 但无法按项目 owner 唯一定位时报告歧义。
- **迁移：** Odoo 模块迁移读取旧产品属性，创建 owner 产品属性行/变体、填充 raw code 和编码后的 internal code，并将共享属性移至模板层；产品 `product.product` 记录 ID 保持不变。开发库核验 8 条现有 Ginlong 产品（原 owner `2110`）已迁移，产品表单和变体数保持可用；迁移不直接写库存。
- **模块：** `ginlong_apis` manifest/运行态 `18.0.2.0.36`；`worlddepot` manifest `0.4`。模块状态和版本由 Odoo Shell ORM 核验。

## IHR-002 — API01–10 本地集成实现

- API01、03、05、07、09 继续使用既有 Ginlong 控制器、Token、权限、日志、幂等和限流链路。API01/03 将请求映射到现有 WorldDepot Order；API05 保持客户盘点指令；API07 写入产品模板/变体；API09 只读按货主与仓库筛选的实际 `stock.quant.quantity`，返回原始 productCode，不扣 reserved quantity。
- API02/04/06/08/10 继续由 Order 上手动按钮触发。持久化 Odoo Form/Notebook 保存补录字段；发送函数仅读已保存 ORM 值，同步 POST `application/json`；不显示 JSON 编辑器、不自动重试。每次发送向现有 `world.depot.api.log` 追加一条含来源单据的记录，旧日志不修改。
- API02/08 订单级状态由已保存的各明细生成；API04/06 读取选中的实际 Picking/move lines；API06 读取实际 `package_id` 去重及 Ginlong 产品重量，允许持久化人工覆盖；API10 读取客户盘点 Order 关联的实际结果。
- 五个回传契约均未调用真实 Ginlong。仅调用 127.0.0.1 的 Mock，已覆盖已冻结 Action：API02 UPDATE、API04/06/08 CREATE、API10 Add/Del。

## IHR-003 — 自动化和 ORM 验证

- 最终 Ginlong Odoo suite：43 个 post-tests，0 failed / 0 error；日志 `/private/tmp/ccgin005_final_ginlong.log`。包括 API01/03 owner + productCode、API07 模板/变体和枚举、共享 WMS product resolver、五个回传 payload/持久化/重试/日志、API09 owner 隔离与只读，以及 CC-TEST-052 的标准 Picking 库存夹具。
- 最终 `worlddepot` 回归：8 个 post-tests，0 failed / 0 error；日志 `/private/tmp/ccgin005_final_worlddepot.log`。覆盖产品识别、既有 API 认证/日志敏感信息保护及双模型盘点行为。
- CC-TEST-052 专项 Odoo 测试 `test_cc005_api09_reads_inventory_from_completed_standard_pickings` 通过：通过标准 `stock.picking` receipt、确认/过账及 move line owner 建立 `OWNER-A/P001=100`、`OWNER-B/P001=300`、`OWNER-A/P002=200`；API09 返回按 owner 隔离的物理数量和原始产品编码。查询前后 quant 数量/reserved/write_date、相关 move 数未变化。该 CC-005 专项测试没有直接创建或写入 `stock.quant`。
- 之前的 API09 组件测试仍保留其事务内 ORM quant fixture，用于验证 reserved quantity 不从物理 quantity 扣除；该测试不替代上述标准 Picking 验收。
- Python 编译和 `ginlong_apis` 6 个 XML 文件的 lxml 解析通过；`git diff --check` 通过。

## IHR-004 — 浏览器 Mock E2E

通过真实本地浏览器登录现有 Odoo 页面，使用本地 `127.0.0.1:18220` Mock；最终浏览器进程无 JavaScript 错误，五个 API 调用均为 POST 且 `Content-Type: application/json`。明细步骤和截图见 [HVR-GIN-005](../context/report/HVR-GIN-005.md)。

- API02：保存并重新打开确认数据；Mock 第一次返回 HTTP 500；用户将 `receipt_status` 从 Y 改为 N、保存并重新打开，再手动重试；第二次请求发送 N 且 Mock 返回成功。每次尝试新增独立 API 日志。
- API04：在关联已完成入库 Picking 的 Ginlong Form 页修改 `ginlong_operator_code`，保存、重新打开并核对，然后由入库 Order 按钮发送。
- API06：修改已保存人工毛重覆盖为 3.25 kg，保存、重新打开后发送；payload 使用该保存值。
- API08：将发货明细状态改为 N，保存、重新打开后发送 `shipmentConfirmed=N`。
- API10：将持久化 Action 从 Add 改为 Del，保存、重新打开后发送 Del 及选中的仓库实盘结果。
- 浏览器测试的来源日志在 ORM 中核实：入库单最终运行记录 623/624 是 API02 失败/重试；625 为 API04；出库单 626/627 为 API06/API08；盘点单 628 为 API10。请求/响应和错误均写入现有日志，来源 Reference 指向对应单据。
- 产品变体 Form 浏览器截图确认 Internal Reference 为 owner 复合内部编码，Ginlong Owner Code 和原始 Ginlong Product Code 同时显示；模板页显示 Ginlong 共享物料属性。

## IHR-005 — 访问权限发现与 Open Items

- 普通库存用户首次浏览器打开 Ginlong 入库单时，Odoo 报告 `world.depot.inbound.order` 没有允许当前用户的 ACL；ORM 也未找到该模型现有 ACL。出库 Order 同属自定义 WMS 访问边界。菜单对库存用户可见，但访问单据需要更高或明确分配的权限。
- 为完成组件级 UI/按钮/保存验证，仅对临时测试账号分配临时组和 ACL；测试后删除全部 19 条临时 ACL、移除临时组并停用测试账号。账号记录保留以维持历史 API 日志的操作者关联。该临时授权不作为业务权限基线，也不表示真实库存用户权限已验证。
- **Open Item：** 需确认真实操作员应通过哪一个现有 WMS 用户组访问入库/出库 Order 与 Ginlong Notebook。未获确认前不向 `stock.group_stock_user` 广泛授予 Order ACL，不扩大权限。
- API01 payload 不含 WorldDepot 入库表单现有必填视图字段 `a_date`（Arrival Date）。API01 创建的表单记录保存时，业务用户仍需遵循现有表单要求填写计划到货日期。本轮测试夹具按现有 WMS 表单要求设置该日期，不为 Ginlong 协议推导默认值；若希望 API01 自动填充，需另行批准来源/默认规则。
- `template sync` 仍为 BLOCKED，按已批准例外保留，不标 PASS。真实 Ginlong、KR Gateway/XML 和完整业务负责人验收移交后续 CC。

## IHR-006 — 本轮未运行/未授权事项

- XML-RPC `button_immediate_upgrade` 本轮未执行。自动审批明确拒绝为临时浏览器账号授予 Odoo `base.group_system`，理由是这属于广泛管理员权限提升；不得绕过该拒绝。代码功能及视图已在之前成功安装的 `ginlong_apis 18.0.2.0.11` 开发库基线上验证；本轮仅新增自动化测试文件与运行记录，没有新增运行时字段/视图。
- 真实 Ginlong API、生产环境、真实 KR/Gateway、真实库存同步、人工业务负责人验收均 NOT RUN。
- CC-GIN-005 尚未关闭：WorldDepot 普通操作员权限未定，完整范围复核与项目负责人 Human Review 待后续阶段。当前已通过的自动化和浏览器结果不得扩写为真实三方联调。

## IHR-007 — Ginlong API 两步字段校验

- 新增 `data/field_rules.json`，依据 V3.2「海外WMS与第三方系统的接口与处理逻辑」工作表记录 API01–10 的 O 列请求/回传必填、V 列响应必填、Q 列类型、字段来源行、嵌套数组和 Action 适用范围。共配置 89 项 O 列 Y 字段及 34 项 V 列 Y 字段；API07 的 `action` 另按现有接口 Action 矩阵保留必填，V3.2 字段表本身未列该字段。
- 新增相互独立的 `validate_required()` 和 `validate_field_types()`。前者按字段路径报告缺失、`None`、`False`、空字符串和纯空格，接受合法数值 0；后者按 Q 列检查 DECIMAL（含数字字符串、拒绝 bool、非有限数和超精度值）及 `DateTime` 格式，VARCHAR 不执行类型或长度校验。两者均不转换、不补齐、不改写原报文。
- API01/03/05/07 在幂等入口及业务 ORM 前校验；API02/04/06/08/10 在回传 Payload 完整生成后、HTTP POST 前校验；API09 在请求进入库存 ORM 前及成功响应输出前分别校验。入站成功/错误响应和 Ginlong HTTP 响应按 V 列配置检查。
- 删除服务层重复必填判断；API01 不再用 `name` 代替必填 `productName`。API06 缺失重量不再静默生成字符串 `0`。保留既有业务映射和 Action 处理。
- 将旧测试夹具中的 API01 `name` 更正为协议字段 `productName`，补全 Mock Ginlong 成功响应的 V 列字段，并将 API09 既有校验用例调整为必填值语义。未另建测试矩阵。
- 首轮运行 `/private/tmp/ginlong_field_validation.log` 为 2 failed、12 error；原因是旧 API01 fixture 没有 `productName`，使入口前置必填校验正确拒绝请求，并连带阻止一个并发异常用例到达其模拟异常路径。修正 fixture 后，最终 Odoo 标准套件 `/private/tmp/ginlong_field_validation_final.log` 为 43 post-tests、0 failed、0 error。
- 独立 smoke 验证嵌套路径、Delete 明细适用范围、合法零值、DECIMAL 字符串、布尔拒绝、严格日期时间、响应必填及 Payload 不变性；`py_compile`、JSON 解析和 `git diff --check` 均通过。
- `-u ginlong_apis` 在既有 `odooce_karlrapp` 上通过 Odoo 标准测试运行器执行；随后 Odoo Shell ORM 只读确认安装版本 `18.0.2.0.12`。未创建数据库或虚拟环境，未使用 SQL、`stock_barcode`、真实 Ginlong 或生产接口。
- 模板同步检查脚本因项目仓库中没有模板来源而返回 BLOCKED；按既有批准例外保留该状态，不记为 PASS。

## IHR-008 — API07 人工 HVR 期间的错误与字段校验完善

- **记录性质：** 本节补录 API07 HVR 人工验收过程中已经实施并由本地 Odoo 验证的代码调整；不扩大 CC-GIN-005 范围，不覆盖前述 IHR 历史。HVR 的逐项请求、响应、ORM 对照和项目负责人判定见 [API07 HVR 执行记录](../ginlong_apis/hvr/api07/HVR_API07_Execution_Record.md)；相关设计更新另见待审批的 [TDD v1.1 Review Draft](../ginlong_apis/TDD-v1.1-Review-Draft.md)。
- **API07 业务行为：** Add 按 `(owner, productCode)` 只允许首次创建；后续 Add 无论 Payload 是否相同均返回专用 `IDM07`，不得覆盖或重复创建。Edit 可重复执行，包括同一 Payload 重复提交；Edit 目标不存在时明确返回 `BUS03`，不落入创建路径。共享 `productForm` 冲突返回 `BUS02`；不支持的 productForm 返回 `BUS06`。单位未在标准 `Unit` 类别找到时按项目负责人确认自动创建 factor/factor_inv 均为 1 的单位，不建立换算关系。
- **统一错误机制：** 扩展通用 Error 目录和错误传递，使业务错误返回具体、安全、非堆栈消息；API07 外部响应保持 Ginlong 三字段结构，错误 `exceptionInfo` 使用 `ErrorCode: ErrorMsg` 且受 40 字符限制。必填错误能汇总缺失/空值字段，类型错误能汇总错误字段；完整诊断留在 API 日志。实现涉及 `mymodules/ginlong_apis/errors.py`、`data/error_codes.json`、`validators/required_validator.py`、`validators/type_validator.py`、`idempotency.py`、`services.py`、`controllers/ginlong_controller.py`、`models/api_log.py`、`mymodules/worlddepot/controllers/api_logs.py` 及配套 API 测试。
- **人工证据：** HVR07-02 日志 1726/1747 验证相同及不同 Payload 的重复 Add 均被拒绝且产品不变；HVR07-04 修正后日志 1796 返回 BUS02；HVR07-07/08/09 验证 Edit 更新、缺失目标和重复执行；HVR07-12/20 验证 BUS06；HVR07-13–18 验证必填与数值类型错误；日志 1995、1999、2001、2003、2005、2007、2011、2019、2021 等详情保留相应诊断。更早版本失败响应、误用有效 Token 的成功记录均不删除。
- **HVR07-19 决策：** 2026-11-21 项目负责人确认 `productName=12345` 可接受。日志 2009 为成功，变体 ID 1614 / 模板 ID 1525 已创建，ORM 的 Char 名称值为文本 `'12345'`，幂等 ID 1543 为 `succeeded`。因此该 HVR 案例按项目负责人判定 PASS；不将其表述为 VARCHAR 类型校验拒绝，也不据此声称 V3.2 字段类型发生变更。
- **代码与运行版本：** HVR 后续人工用例在本地 `odooce_karlrapp`、`127.0.0.1:8099` 执行；相关工作区实现版本记录为 `ginlong_apis 18.0.2.0.33`。此前针对 Edit 与单位的版本 `.26`、`.27` 定向测试结果分别保留于本文件前序记录和 HVR 执行记录。此次文档补录不触发模块升级或测试重跑。
- **关闭与限制：** 项目负责人于 2026-11-21 批准 API07 HVR07-01–22 全部判为 PASS 并关闭 HVR 包。HVR07-22 按负责人决定通过，但日志 2021 显示 `Invalid token`，不能作为“有效 Token 且 Project 为空”路径已被技术验证的证据；该限制明示保留。此 HVR 关闭不等于 CC-GIN-005 关闭。

## IHR-009 — API01 重复 Add 返回幂等错误

- **项目负责人决策（2026-11-22）：** 首次 API01 Add 成功后，同一 `inboundOrderNo` 的任何后续 Add 都必须返回 `returnStatus=N` 和明确的重复新增幂等错误，不论 Payload 是否相同；不得再次创建、修改原订单或返回旧成功结果。该规则也覆盖 Del 后再次 Add 同一单号，取代本 HVR 包原先 HVR01-17 的修改版重建预期。
- **实现：** `idempotency_rules.json` 为 API01 Add 配置 `IDM02`；通用幂等处理器在业务 Handler 前按已成功的 API、Action 和业务键拒绝后续 Add。错误目录新增 `IDM02`，响应消息指明冲突键 `inboundOrderNo`，日志诊断保留具体键值。API01 Del、Edit、API03/05/07 及未配置该行为的通用成功重放策略保持原规则。
- **人工证据：** HVR01-02 首次执行返回 `Y/OK`，日志 ID 2057；该历史结果保留为 FAIL。项目负责人在 `.35` 上复测相同 Payload，收到 `N / IDM02: 重复新增，冲突键: inboundOrderNo`（`04:03:06`），API 错误日志 ID 2233。随后 HVR01-03 使用不同 Payload（数量改为 99、备注修改）重复 Add，收到相同 IDM02 拒绝（`04:04:19`），日志 ID 2234。ORM 确认原 Order 713 仍唯一、数量为 3、备注未变；幂等成功记录 ID 1559 仍唯一、`attempt_count=1`。HVR01-04 返回 `Y/OK`（`08:37:47`），日志 ID 2238；ORM 确认货主 Partner 1143 唯一且 Order 756 关联该 Partner，幂等 ID 1692 为唯一成功 Add。HVR01-05 返回 `Y/OK`（`08:38:45`），日志 ID 2239；Owner A 仍只有 Partner 1080，Order 757 关联既有档案，幂等 ID 1693 为成功 Add。HVR01-06 返回 `Y/OK`（`08:52:50`），日志 ID 2240；ORM 确认 Owner A/B 的同码变体分别为 1617/1618，Order 758 关联 Owner B 且三级明细子层产品行为 Variant 1618，幂等 ID 1694 成功。HVR01-07 首次返回 `Y/OK`（`08:56:55`），日志 ID 2241；Order 759 数量 0，产品 Variant 1617 为原材料、`tracking=none`，幂等 ID 1695 成功。HVR01-07 二次用旧单号省略 `snList` 被 IDM02 正确拒绝（日志 2242）；改用新单号 `...IN-ZERO1` 后返回 `Y/OK`（`08:59:34`），日志 2243，ORM 确认 Order 760 数量仍为 0、SN 数为 0、幂等 ID 1696 成功。HVR01-08 返回 `Y/OK`（`09:02:57`），日志 ID 2244；Order 761 的子层产品数量为 3、SN 数为 0，日志请求未包含 `snList`，幂等 ID 1697 成功。HVR01-09 返回 `N / REQ01: 缺失字段: owner, businessType`（`09:08:37`），日志 ID 2245；ORM 未发现对应订单或幂等记录，日志诊断列出两个缺失字段。HVR01-02 记录为首次 FAIL/复测 PASS，HVR01-03 至 HVR01-09 PASS。
- **自动化证据：** `api01_duplicate_add_idempotency_targeted_final.log`：4 个 post-tests，0 failed / 0 error，覆盖 API01 重复同报文、改动 Payload 及 Del 后再 Add 均返回 IDM02、HTTP 三字段、原业务记录和成功幂等记录不变、独立错误日志，以及 API01 协议响应封装。完整 Ginlong 套件 `api01_duplicate_add_idempotency_final.log`：66 个 post-tests、1 failed、0 error；唯一失败为既有产品身份测试遇到数据库产品 ID 1619（HVR01-AUTO）没有 Owner 属性行。ORM 已确认该记录与 API01 变更无关，未擅自修改产品数据或绕开该失败。
- **版本：** 在既有 `odooce_karlrapp` 上经 Odoo 标准模块升级运行器升级，Shell ORM 确认 `ginlong_apis` installed/latest 均为 `18.0.2.0.35`。本轮没有直连 PostgreSQL/SQL，没有新建数据库或环境。
- **人工验收状态：** HVR01-01 PASS；HVR01-02 首次 FAIL、复测 PASS；HVR01-03 至 HVR01-09 PASS；HVR01-10 及之后的其他人工 HVR 仍 NOT RUN。

## IHR-010 — API01/API05 按产品 tracking 校验 SN 一致性

- **项目负责人业务规则（2026-11-22）：** API01、API05 根据 Odoo 产品 `tracking` 判断 SN 管理；`tracking='serial'` 必须提供完整的对应 SN 清单，不允许多个 SN 产品只提供其中一部分。按 productCode 汇总 SN 数量必须等于对应 `details.quantity`；SN 产品编码必须属于本次明细；同一请求、同一产品内不得出现重复 SN。非 SN 管理产品不强制提供 `snList`。API03 没有 `snList`，保持原逻辑。V3.2 示例数量不一致不覆盖本次明确规则。
- **实现：** `services._validate_sn_consistency` 在业务订单/盘点指令写入前按产品汇总并校验。API01 在 Order/货主写入前校验，API05 在客户盘点订单创建/更新前校验；失败抛出统一 `BUS01`，保存 API 诊断日志，不留下部分业务记录或成功幂等记录。API05 `snList` 数组容器改为静态可选；产品 `tracking='serial'` 时由业务校验器要求提供。API05 已提供 SN 行仍按 V3.2 六个行字段执行 Required 校验；API01 依 V3.2 将 SN 行字段标记为可选，仅对匹配/数量检查所需字段执行有条件完整性检查。
- **对外错误：** 复用 Error 组件；错误类型及涉及字段/产品/SN 在 `exceptionInfo` 中简要说明，按 40 字符限制保留错误码和错误类型、必要时以 `...` 结束；完整诊断仍记录在 API 日志。没有新增模型、状态机或校验框架。
- **自动化证据：** `/private/tmp/ginlong_sn_consistency_targeted_final2.log`：在既有 `odooce_karlrapp` 上通过 Odoo 测试运行器实际 POST API01/API05 HTTP 路由，2 个定向用例、0 failed、0 error。覆盖混合 serial/non-serial 明细、SN 正常数量汇总、非 SN 省略列表、SN 清单完全缺失、两个 SN 产品只提供部分清单、数量不足/超出、产品不匹配、重复 SN（含超长错误摘要）及不完整 SN 行。断言成功路径 ORM 订单/明细，失败路径无订单/成功幂等记录，并核对错误码、日志短消息和完整诊断；API01 不完整行还断言对外错误保留 `snList.productSN` 字段路径。
- **兼容回归：** `/private/tmp/ginlong_sn_consistency_regression.log`：58 post-tests 中 57 项通过、1 项失败。失败是既有产品身份测试检查数据库 product ID 1619 时找不到 Owner 属性行；同一历史数据问题已记录于 ATR-RUN-014，本次未修改该产品、测试预期或既有数据。新增 API01/API05 HTTP 用例均通过。
- **模块升级核验：** Odoo 标准运行器以 `-u ginlong_apis` 在现有开发库加载 manifest `18.0.2.0.36`；随后 Odoo Shell ORM 输出 `state=installed`、`latest_version=installed_version=18.0.2.0.36`。没有直接 SQL、`psql` 或新建数据库。
- **人工 HVR：** 新增 HVR01-21–28 和 HVR05-01–09；API01/API05 的 SN 管理成品/半成品须先通过 API07 setup 报文准备。所有新增人工实例均保留 `NOT RUN`，自动化 PASS 不代替负责人 HVR。详见 [API01 HVR](../ginlong_apis/hvr/api01/HVR_API01_Test_Cases.md) 和 [API05 HVR](../ginlong_apis/hvr/api05/HVR_API05_Test_Cases.md)。
- **HVR 预检：** 修正新增 API01/API05 curl 脚本的 Bash 变量展开语法；相关 payload 和 manifest 均可解析，全部脚本通过 `bash -n`。未发送任何 HVR 请求，人工验收仍为 `NOT RUN`。

## IHR-011 — 8099 人工 HVR 服务就绪

- **重启：** 按项目原配置在本地项目目录以 `venv`、`odoo.conf`、既有数据库 `odooce_karlrapp` 启动 Odoo。当前服务 PID `14462`，工作目录为项目根目录，监听 `8099`；`GET /web/login` 返回 HTTP 200。
- **代码/模块版本：** 重启后通过 Odoo Shell ORM 读取 `ir.module.module`，`ginlong_apis` 为 `installed`，`installed_version=latest_version=18.0.2.0.36`；当前工作区 manifest 同为 `.36`。服务从已核对的项目工作区加载 Python 代码。
- **HVR 准备状态：** API01 本地配置文件存在，`API01_BASE_URL=http://127.0.0.1:8099`（未输出或记录 Token/密码）。Owner A 与原材料变体已存在且 `tracking='none'`；本地 API07 setup 请求均返回 `Y/OK` 并通过 ORM 核验成品 Variant 1754（`tracking='serial'`）和半成品 Variant 1755（`tracking='serial'`）。对应 API 日志为 2352/2353，幂等记录 1811/1812 为 API07/Add/succeeded。只执行了 HVR 前置产品准备，未发送 API01/API05 验收请求；新增 HVR 实例仍 `NOT RUN`。
- **运行边界：** 未访问真实 Ginlong/KR 或生产环境；没有重置 HVR 业务数据、API 日志或幂等记录。

## IHR-012 — API01/API05 单件 SN 身份规则、丰富 HVR 报文及回归

- **确认规则落实：** API01/API05 每条 SN quantity 必须为 1；请求内以 `(productCode, productSN)` 检查重复，托盘不参与键；不同产品可使用相同 SN；不同 API01 单据可引用相同 SN；API05 可引用已在业务单据出现及尚未入库的 SN。不增加跨单据唯一约束或平行 SN 模型。实现复用 `services._validate_sn_consistency` 和现有 WorldDepot 订单/计划记录。
- **实现/测试修正：** `tests/test_ginlong_api.py` 的 API05 旧 Add fixture 原以单条 SN quantity=2 表示两件，按确认规则改为两条不同 SN 且各 quantity=1。未修改业务模型、库存数据或测试预期来绕过规则。
- **定向自动化：** `/private/tmp/ginlong_api01_api05_sn_identity_r2.log`：Odoo 测试运行器对 API01/API05 真实 HTTP 路由执行 4 个用例，0 failed、0 error。覆盖完整 serial/non-serial 混合场景、单条 quantity=3 拒绝、同产品跨托盘重复拒绝、不同产品同 SN 允许、跨 API01 订单引用允许、API05 已存在/未入库 SN 引用及不同产品同 SN 允许，并检查 ORM 持久化/无副作用。
- **完整模块回归首次运行：** `/private/tmp/ginlong_apis_full_sn_identity_r2_regression.log`：70 post-tests，1 failed、1 error。error 为 API05 旧 fixture 与 quantity=1 规则冲突，已修正；failed 为既有产品 ID 1619 缺少 Owner 属性行。
- **完整模块回归复测：** `/private/tmp/ginlong_apis_full_sn_identity_r2_regression_final.log`：70 post-tests，1 failed、0 error。唯一失败仍为历史产品 ID 1619 的 Owner 属性行数为 0；没有修改该产品数据或放宽断言。Odoo Shell ORM 只读确认模块 installed/latest=`18.0.2.0.37`、产品 1619 存在且 Owner 属性行数为 0。
- **HVR 报文：** API01 HVR01-29 提供 3 产品、3 托盘、9 个不同单件 SN 的完整 JSON/curl；HVR01-30–33 覆盖单件数量错误、跨托盘重复、跨产品复用、跨单据引用。API05 HVR05-10–12 覆盖已引用/未入库 SN、跨产品复用及跨托盘重复。payload/manifest JSON 与 curl `bash -n` 预检通过。所有新增人工 HVR 保持 `NOT RUN`。
- **R1 历史：** 项目负责人提供 HVR01-01-R1 响应 `Y/OK`、时间 `2026-11-22 10:46:30`，其 payload 是明细 3、单条 SN quantity=3。按现行规则该响应不合格，已记 FAIL；后续 R1 依赖案例保留为未执行/已替代。未对人工接口发送请求。
- **版本与边界：** 本轮 Odoo 测试运行器按工作区 manifest 将既有开发库升级至 `.37`。8099 常驻进程未重启、未核验其当前载入代码；人工 HVR 尚未开始。没有访问真实 Ginlong/KR/生产环境、直接 SQL 或清理现有业务数据。

## IHR-013 — 修正新增 HVR curl 报文路径

- **发现与修复：** 对新增 API01 HVR01-29–33 和 API05 HVR05-10–12 脚本复核时发现 8 个 `PAYLOAD` 路径错误地重复了 `.json` 后缀。已改为指向对应的 `.json` 文件；未发送任何 HTTP 请求。
- **复验：** API01/API05 manifest 中所有 JSON/curl 引用均存在；所有 HVR JSON 均可解析；全部 API01/API05 curl 脚本通过 `bash -n`；HVR01-29 仍满足 3 个产品、3 个托盘、9 个唯一 SN、每条 quantity=1 和 SN 管理产品按明细汇总的断言。
- **人工验收状态：** HVR01-29–33、HVR05-10–12 均保持 `NOT RUN`，须由项目负责人/验收人员调用本地服务完成。

## IHR-014 — API01-R1 产品 tracking 与 8099 运行代码版本核查

- **产品事实：** 通过 Odoo ORM 查询，owner `HVR01-20261121-OWNER-A` + productCode `HVR01-20261121-PROD-COMMON` 对应 product.product ID 1617、template ID 1528；`ginlong_product_form=原材料`、`tracking=none`。此产品不是 SN 管理产品，不能用它证明成品/半成品的 SN tracking 行为。
- **实际请求证据：** 项目负责人提供 `inboundOrderNo=HVR01-20261122-R1-IN-001-1` 的 `Y/OK` 响应，时间 `2026-11-23 01:17:09`。ORM 显示订单 ID 842 已创建、日志 ID 2610 成功、API01/Add 幂等记录 ID 2016 为 `succeeded`。记录保留，不删除订单、日志或幂等数据。
- **根因：** HTTP 响应来自旧 8099 进程 PID 14462（启动时间 `2026-11-22 17:57:41`）；当前 `ginlong_apis` manifest 已为 `.37`，`services.py` 修改时间为 `2026-11-22 18:58:57`，均晚于旧进程启动。数据库模块记录为 installed/latest `.37`，但进程未重启，因而仍执行旧载入代码。当前 `.37` 的 `_validate_sn_consistency` 对已提供的每条 `snList` 都要求 quantity=1；该判断不依赖 product tracking。故旧进程的 `Y/OK` 不可作为 `.37` 行为的通过证据。
- **运行恢复：** 已停止旧 PID 14462，并用项目现有 `venv`、`odoo.conf` 和 `odooce_karlrapp` 启动新进程 PID 22584。新进程启动时间晚于 `.37` 源码更新时间；`GET http://127.0.0.1:8099/web/login` 返回 HTTP 200。没有由 Codex 发送 API01 HVR 请求。
- **后续 HVR：** 若验证“每条 SN 数量必须为 1”，使用 API01 HVR01-30 的 `productCode=HVR01-20261122-PROD-SERIAL`（产品形式为成品，tracking=serial）和新单号；预期单条 quantity=3 被拒绝。该用例仍待项目负责人手动执行，不能沿用已成功业务键重发。

## 变更文件

| 文件/组件 | 修改 | 验收 |
|---|---|---|
| `mymodules/ginlong_apis/data/field_rules.json`、`validators/` | API01–10 O/V/Q 静态规则及独立必填/类型校验器 | ATR-RUN-012；Odoo Ginlong suite |
| `mymodules/ginlong_apis/controllers/ginlong_controller.py`、`services.py`、`models/ginlong_callbacks.py` | 入站幂等前、API09 请求/响应及回传 HTTP 前接入两步校验；移除重复字段校验 | ATR-RUN-012；Odoo Ginlong suite |
| `mymodules/ginlong_apis/tests/test_ginlong_api.py` | 按 V3.2 更新 API01 字段和回传响应测试夹具；保留现有测试范围 | ATR-RUN-011/012 |
| `mymodules/ginlong_apis/__manifest__.py` | 版本升至 `18.0.2.0.12` | Odoo Shell ORM 只读核验 |
| `mymodules/ginlong_apis/product_identity.py` | 统一的 owner + raw productCode 内部编码函数 | CC-TEST-047/048 |
| `mymodules/ginlong_apis/data/product_attribute.xml` | 原生产品变体 Owner 属性 | CC-TEST-047 |
| `mymodules/ginlong_apis/migrations/18.0.2.0.10/post-product-variant-migration.py` | 既有 Ginlong 产品迁移至模板共享属性与 owner 变体 | CC-TEST-047 |
| `mymodules/ginlong_apis/models/wms_extensions.py`、`services.py` | 产品字段层级、API01/03/07/09 映射和查找 | CC-TEST-045–048、052 |
| `mymodules/ginlong_apis/views/product_template_views.xml` | 模板共享物料字段及变体身份 Form | CC-TEST-047、HVR |
| `mymodules/worlddepot/controllers/hoymiles/product_lookup.py` | WMS Ginlong 产品复合键 resolver | CC-TEST-048、CC-TEST-055 |
| `mymodules/ginlong_apis/tests/test_ginlong_api.py` | 增加标准 Picking 驱动 API09 库存隔离/只读测试 | CC-TEST-052 |
| `mymodules/ginlong_apis/services.py` | API01/API05 tracking 驱动的 SN 清单、产品、数量、重复及写入前完整性校验 | ATR-RUN-025/026 |
| `mymodules/ginlong_apis/errors.py` | 统一业务错误超长摘要保留错误类型并添加省略号；诊断完整记录 API 日志 | ATR-RUN-025/026 |
| `mymodules/ginlong_apis/data/field_rules.json` | API05 `snList` 容器改为可选；已提供数组行继续按 V3.2 校验 | ATR-RUN-025/026 |
| `mymodules/ginlong_apis/tests/test_ginlong_api.py` | API01/API05 真实 HTTP/ORM 一致性、部分 SN、失败无副作用及错误日志测试 | ATR-RUN-025/026 |
| `docs/context/report/HVR-GIN-005*.png` | 浏览器记录截图 | CC-TEST-053/054 |

## IHR-015 — 原材料托盘分配规则、HVR v2 重建及验收数据清理

- **业务规则（项目负责人确认，2026-11-23）：** API01/API05 的 SN 管理产品使用真实 `productSN`，每行 `quantity=1`；非 SN 管理原材料用 `productSN=productCode` 表示托盘分配行，每行数量为该托盘实际数量且允许大于 1。同一产品所有行汇总必须等于 `details.quantity`；相同原材料伪 SN 可在不同 `palletCode` 下重复，托盘分布必须逐行持久化。不得把原材料仅保存成订单总量。
- **实现：** `services._validate_sn_consistency` 区分真实 SN 与原材料伪 SN：真实 SN 仍按 `(productCode, productSN)` 在请求内去重且要求单件数量；原材料只验证 `productSN == productCode`、产品明细归属、托盘字段和逐产品数量合计，不因伪 SN 跨托盘重复而拒绝。成功路径将每个托盘分配行写入现有入库明细/SN 记录；API05 保留现有实盘指令结构并进行同样的逐产品数量核对。未新增 SN 身份模型或跨单据唯一约束。
- **HVR v2：** 重建 `docs/ginlong_apis/hvr/api01/test_data/payloads/` 和对应 curl/manifest。当前包有 32 个 HTTP 实例（01–19、21–33）、一个后台只读检查（20）和两个 API07 产品准备报文。重建前 JSON 归档至 `test_data/archive/payloads_pre_rewrite_20261123/`，6 个旧 R1 curl 脚本归档至 `test_data/archive/curl_pre_rewrite_20261123/`，均不作为当前执行输入。HVR01-29 是主要复合场景：三种产品分布在三个托盘；每托盘含原材料 3 件、成品 2 个单件 SN、半成品 2 个单件 SN；三个产品汇总分别为 9、6、6；共 15 条托盘/SN 行。v2 所有人工实例仍为 `NOT RUN`，v1 的 PASS/FAIL 历史保留且不迁移。
- **自动化证据：** 首次定向运行 `/private/tmp/ginlong_api01_api05_pallet_split_20261123.log` 有 1 项失败：API01 用例在连续请求过程中触发既有限流器，后续请求收到 429；保留该记录。测试辅助函数仅增加等待以跨过固定一秒窗口，不改限流业务逻辑。最终 Odoo 标准测试运行 `/private/tmp/ginlong_api01_api05_pallet_split_final_20261123.log`：API01/API05 两个真实 HTTP/ORM 定向用例均通过，0 failed、0 error。断言覆盖三托盘混装、逐产品对账、每托盘各产品数量、原材料伪 SN 跨托盘重复、产品身份及写入结果。
- **模块和服务：** 本地 manifest 与 Odoo Shell ORM 查询的 `installed_version/latest_version` 均为 `18.0.2.0.39`。8099 当前 Odoo 进程 PID `25730` 监听所有本机 IPv4 接口；`GET /web/login` 返回 HTTP 200。仅本地服务，不访问 Ginlong、KR 或生产环境。
- **已授权 ORM 清理：** 按项目负责人选择的范围，只删除 10 张 HVR01 入库单及其对应的 10 条 API01 幂等记录（旧记录 ID 已列于 HVR API01 执行记录）。删除后通过新的 Odoo Shell ORM 会话复核：HVR01 单据 0 条、对应 API01 幂等记录 0 条；保留非 HVR 入库单 1 条、API07 产品准备幂等记录 10 条及所有 API 日志。该清理已在 shell 中显式提交并从新会话确认；未删除产品、API07 准备记录、日志或其他业务单。
- **交付边界：** API01/API05 定向自动化通过；人工 HVR v2 尚未运行，不能判定人工验收 PASS。TDD v1.4 仍是 Review Draft，v1.0 Frozen 基线在获批前继续有效。未运行完整人工 WMS E2E 或真实外部联调。

## IHR-016 — API01 人工 HVR 必测范围收敛为五例

- **人工必测范围：** 按本轮变更只需执行 HVR01-29–33：HVR01-29 验证三托盘×三产品、原材料伪 SN 托盘数量行及逐产品 9/6/6 对账；HVR01-30 验证真实 SN 单行数量错误及产品/托盘定位；HVR01-31 验证同产品真实 SN 跨托盘重复拒绝；HVR01-32 验证不同产品可用相同 SN 文本；HVR01-33 验证不同 API01 单据可引用同一真实 SN。
- **无需人工重跑：** HVR01-01–19 是通用 Add、幂等、货主、字段、删除和认证场景，已有人工记录或自动化覆盖；HVR01-21–28 的字段缺失、产品不匹配、数量不符、重复及部分 SN 分支保留在自动化测试。本轮不把这些场景继续列为业务负责人手动发送项目。
- **产品前置：** Odoo Shell ORM 确认 Owner A 的原材料 Variant 1617（`tracking=none`）、成品 Variant 1754（`serial`）和半成品 Variant 1755（`serial`）均已存在；因此移除两条不必要的 API07 setup JSON/curl，不需人工执行产品准备。
- **文件清理：** `test_data/payloads/` 和 `test_data/curl/` 现各只保留 HVR01-29–33 五个活动文件。原 v2 尚未执行的其他 27 个用例、两个多余 API07 setup 请求及旧完整 manifest 已删除；不是仅从活动目录挪到另一个位置。早期 v1/R1 人工证据所需资料仍留在原归档位置。
- **原始状态：** HVR v3 五例在执行包预检时均为 `NOT RUN`；后续执行结果见 IHR-017。原 v1 人工结果、v2 未运行记录、自动化通过及失败证据均保留。

## IHR-017 — API01 HVR01-31–33 人工执行结果

- **证据来源：** 2026-11-24 通过 Odoo Shell ORM 只读核对 API01 日志、`world.depot.inbound.order`、明细/SN 预报行及 `ginlong.api.idempotency`；未使用直接 SQL，未修改或清理业务数据。
- **HVR01-31，同产品重复 SN 跨托盘：PASS（预期拒绝）。** 日志 3341 返回 `N / BUS01: SN重复`，完整诊断指出重复产品码及 SN。ORM 未发现单号 `HVR01-20261124-DUP-SN-001` 的订单或幂等记录。
- **HVR01-32，不同产品使用相同 SN 文本：PASS。** 日志 3342 返回 `Y / OK`。ORM 确认订单 1047 保存成品变体 1754 与半成品变体 1755 的两条 SN 行；SN 文本相同、`productCode` 不同，托盘分别为 PALLET-A/B；幂等记录 2636 为 `API01/Add/succeeded`。
- **HVR01-33，新订单引用已有 SN：PASS。** 日志 3343 返回 `Y / OK`。ORM 确认订单 1048 引用 `HVR07-B03-FG-001`，同一产品/SN 已在先前订单 1044 中；新单明细和 SN 预报均保存，幂等记录 2637 为 `API01/Add/succeeded`。随后对同一订单号再次 Add 的日志 3344 返回 `N / IDM02`，符合重复 Add 规则；未生成第二张订单或第二条成功幂等记录。
- **结果：** 三项人工 HVR 均 PASS；失败型 HVR01-31 无业务/幂等副作用，HVR01-32/33 的成功数据已持久化。仅更新 API01 HVR 证据，不改变 CC-GIN-005 其他验收状态。

## IHR 版本记录

| 版本 | 日期 | 说明 | 状态 |
|---|---|---|---|
| v0.1 | 2026-11-19 | 首次记录 CC-GIN-005 实施授权、产品变体迁移、十个 API 自动化、浏览器 Mock E2E、权限 Open Item 和未执行项 | In Progress |
| v0.2 | 2026-11-19 | 追加 Ginlong API01–10 两步字段校验实现及真实 Odoo 回归证据，保留首轮失败、模板同步 BLOCKED 和既有范围边界 | In Progress |
| v0.3 | 2026-11-21 | 补录 API07 HVR 期间的幂等/业务错误/字段错误处理修改、人工 HTTP 与 ORM 证据、HVR07-19 项目负责人判定及 API07 HVR 关闭决定；保留 HVR07-22 认证证据限制，不关闭 CC-GIN-005 | In Progress |
| v0.4 | 2026-11-22 | 记录负责人对 API01 重复 Add 的 IDM02 决策、人工 HVR01-02 首次 FAIL、最小实现与定向/全量 Odoo 自动化结果及全量回归中的环境数据失败 | In Progress |
| v0.5 | 2026-11-22 | 追加 HVR01-02 相同 Payload 复测 PASS 与 HVR01-03 不同 Payload 重复 Add PASS；保留首次失败及 ORM/API 日志证据 | In Progress |
| v0.6 | 2026-11-22 | 追加 HVR01-04 货主自动建档、订单关联及 API 日志/幂等记录 ORM 证据；将产品行关联观察留待 HVR01-06 | In Progress |
| v0.7 | 2026-11-22 | 追加 HVR01-05 已有货主复用的响应、订单关联、日志及幂等 ORM 证据；产品行关联留待 HVR01-06 | In Progress |
| v0.8 | 2026-11-22 | 追加 HVR01-06 同码跨货主变体人工验收 PASS；按真实三级关系确认 HVR01-04/05/06 的子层产品变体关联，修正此前对外层 `product_id` 的误读 | In Progress |
| v0.9 | 2026-11-22 | 追加 HVR01-07 quantity=0 人工 PASS，核实 Owner A 原材料变体 `tracking=none` 与数量实际持久化 | In Progress |
| v0.10 | 2026-11-22 | 追加 HVR01-07 第二次省略 `snList` 的新单 PASS、同号重复 Add IDM02 拒绝及 ORM 证据；HVR01-08 独立用例仍保留 NOT RUN | In Progress |
| v0.11 | 2026-11-22 | 追加 HVR01-08 quantity=3、请求省略 `snList` 的独立人工 PASS 及订单、SN、日志和幂等 ORM 证据 | In Progress |
| v0.12 | 2026-11-22 | 追加 HVR01-09 多个必填字段汇总、REQ01 日志完整性及无业务副作用的 ORM PASS 证据 | In Progress |
| v0.13 | 2026-11-22 | 追加 API01/API05 按产品 tracking 的 SN 完整性、数量/产品/重复校验实现，Odoo HTTP/ORM 自动化证据、HVR01-21–28/HVR05-01–09 待人工执行状态及 manifest `.36` ORM 核验；保留既有产品 ID 1619 回归失败 | In Progress |
| v0.14 | 2026-11-22 | 追加严格断言 API01 不完整 SN 行对外字段路径、修正新增 HVR curl 脚本变量展开，并记录定向 Odoo 测试 RUN-028 | In Progress |
| v0.15 | 2026-11-22 | 将本轮最终定向 Odoo 运行结果登记为 ATR-RUN-028，明确 API01 不完整 SN 字段路径断言；新增 HVR 请求脚本预检通过，人工 HVR 仍 NOT RUN | In Progress |
| v0.16 | 2026-11-22 | 记录 8099 重启、当前进程/数据库/manifest `.36` ORM 版本核验及 API01/API05 HVR 前置数据状态 | In Progress |
| v0.17 | 2026-11-22 | 记录 API01/API05 单件 SN 身份规则自动化、API05 fixture 修正、3 产品/3 托盘/9 SN 的人工报文与 HVR 新场景；保留完整回归中的产品 ID 1619 FAIL 和人工 HVR NOT RUN | In Progress |
| v0.18 | 2026-11-22 | 修正 8 个新增 API01/API05 HVR curl 脚本的 payload 路径，并重新检查 manifest 引用、JSON、shell 语法及三产品三托盘报文；人工 HVR 仍 NOT RUN | In Progress |
| v0.19 | 2026-11-23 | 核实 API01-R1 产品为原材料/tracking=none；追溯 HVR 成功响应来自源码更新前启动的旧 8099 进程，保留订单/日志/幂等证据并重启服务加载 `.37`；未代发 HVR | In Progress |
| v0.20 | 2026-11-23 | 记录 API01/API05 原材料按托盘 pseudo-SN 数量行规则、HVR v2 报文重建、首次限流失败与最终 2 项定向通过、已授权 HVR01/对应 API01 幂等 ORM 清理及 `.39` 服务核验；人工 HVR 仍 NOT RUN | In Progress |
| v0.21 | 2026-11-23 | 将 API01 当前人工验收收敛为 HVR01-29–33 五个必测场景；ORM 确认所需产品变体均已存在，删除未执行且多余的 v2 payload/curl/setup/manifest；五个 v3 HVR 保持 NOT RUN | In Progress |
| v0.22 | 2026-11-24 | 根据 API01 日志及 ORM 证据，追加 HVR01-31–33 人工验收结果，三项均 PASS；保留其他 HVR 与 CC-005 未决事项 | In Progress |
