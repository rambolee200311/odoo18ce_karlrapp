# 实施历史记录：IHR-GIN-005

| 字段 | 值 |
|---|---|
| IHR 版本 | v0.1 |
| CC 基线 | [CC-GIN-005 v1.1 Frozen with Open Items](CC-GIN-005-v1.1.md) |
| 上游基线 | SRS v1.1；TDD v1.0；Implementation Plan v1.8 |
| 当前状态 | In Progress；完成本地实现与自动化/Mock 浏览器验收，仍有权限边界待确认 |
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
- **模块：** `ginlong_apis` 最终 manifest `18.0.2.0.11`；`worlddepot` manifest `0.4`，运行态版本通过 ORM 核验。

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

## 变更文件

| 文件/组件 | 修改 | 验收 |
|---|---|---|
| `mymodules/ginlong_apis/product_identity.py` | 统一的 owner + raw productCode 内部编码函数 | CC-TEST-047/048 |
| `mymodules/ginlong_apis/data/product_attribute.xml` | 原生产品变体 Owner 属性 | CC-TEST-047 |
| `mymodules/ginlong_apis/migrations/18.0.2.0.10/post-product-variant-migration.py` | 既有 Ginlong 产品迁移至模板共享属性与 owner 变体 | CC-TEST-047 |
| `mymodules/ginlong_apis/models/wms_extensions.py`、`services.py` | 产品字段层级、API01/03/07/09 映射和查找 | CC-TEST-045–048、052 |
| `mymodules/ginlong_apis/views/product_template_views.xml` | 模板共享物料字段及变体身份 Form | CC-TEST-047、HVR |
| `mymodules/worlddepot/controllers/hoymiles/product_lookup.py` | WMS Ginlong 产品复合键 resolver | CC-TEST-048、CC-TEST-055 |
| `mymodules/ginlong_apis/tests/test_ginlong_api.py` | 增加标准 Picking 驱动 API09 库存隔离/只读测试 | CC-TEST-052 |
| `docs/context/report/HVR-GIN-005*.png` | 浏览器记录截图 | CC-TEST-053/054 |

## IHR 版本记录

| 版本 | 日期 | 说明 | 状态 |
|---|---|---|---|
| v0.1 | 2026-11-19 | 首次记录 CC-GIN-005 实施授权、产品变体迁移、十个 API 自动化、浏览器 Mock E2E、权限 Open Item 和未执行项 | In Progress |
