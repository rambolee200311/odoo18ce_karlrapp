# Ginlong 多货主产品变体与 API07 productForm/SN 规则技术验证报告

| 项目 | 内容 |
| --- | --- |
| 文档编号 | TV-GINLONG-PRODUCT-001 |
| 项目 | `ginlong_apis` / `worlddepot` |
| 版本 | 0.4 |
| 状态 | Review Draft，等待 Human Review；未授权实施 |
| 验证日期 | 2026-11-19 |
| 技术环境 | Odoo 18 CE；现有 `venv`、`odoo.conf`、开发库 `odooce_karlrapp` |
| 总体结论 | 原生变体方案与产品主数据规则一致：同一 productCode 的 owner 变体必须有相同 productForm；模板级 tracking 据此确定且不发生跨 owner 冲突。Odoo picking 的 tracking 行为已有 v0.3 ORM 证据；API07 一致性校验、`ginlong_product_form` 模板级权威存储迁移与 KR 实际结果导入仍待 CC-GIN-005 实施验证 |

## 修订记录

| 版本 | 状态 | 修订内容 |
| --- | --- | --- |
| 0.1 | Review Draft | 验证原生产品变体、API01/03/07/09 与暂定 `snTrackingRequired` 字段。 |
| 0.2 | Review Draft | 根据项目负责人 2026-11-19 决策，改由 API07 已有 `productForm` 决定 SN 要求；明确本地三种允许值及未知值拒绝；不新增 `snTrackingRequired`。 |
| 0.3 | Review Draft | 纠正 KR、Gateway、Odoo 的仓库作业职责；用 Odoo ORM 实测模板级 tracking 及显式 Lot 关联行为。 |
| 0.4 | Review Draft | 纳入项目负责人正式规则：同一 `productCode` 跨 owner 的 `productForm` 必须一致；首次创建模板时确定模板 tracking；冲突请求拒绝且不修改已有产品。更新技术结论、API07 校验方案、Open Items 和 CC-GIN-005 验收建议。 |

## 1. 目的与边界

验证以 Odoo 原生 `product.template` 为基础档案、以 `product.product` 变体区分 Ginlong 货主的技术可行性；核对 API01/03/04/06/07/08/09 和现有 WMS 的实际字段与代码路径；核对 API07 `productForm` 与 KR 实际执行结果中 SN 的验证和库存记录路径。

系统职责及数据链为：Ginlong 下达指令 → Odoo 管理业务 Order 并转发作业指令 → Karl Rapp WMS 执行实际收货、上架、拣货、SN 扫描及发货并输出 XML → Gateway 接收 KR XML，进行安全解析及 XML→JSON 转换，不处理业务逻辑 → Odoo 接收 KR 实际作业结果，校验并创建/完成 `stock.picking`、`stock.move.line`，记录库存及 SN → Odoo 向 Ginlong 回传结果。Odoo 不执行 KR 现场作业，也不开发额外的 SN 扫描流程；SN 来源是 KR 作业结果。

本次只做源码检查及本地 Odoo ORM 技术验证。未修改 Python、XML、manifest 或业务数据；临时产品、属性、货主、Picking、Lot 及库存均通过 ORM 创建，并在 shell 事务结束前显式回滚。未访问真实 Ginlong、Karl Rapp 或 Gateway 环境，未执行 Gateway 集成测试；未使用 SQL、`stock_barcode` 或官方 Odoo 源码修改。

## 2. 结论摘要

1. **原生变体方案可行。** Odoo 按 `product.attribute` 的变体属性可以为一个 `product.template` 生成多个 `product.product`。试验中两个货主变体分别保存 `ginlong_owner_code`、`ginlong_unit`、`ginlong_weight`，并在同一内部库位形成不同产品的库存数量；查询没有跨产品合并。
2. **产品规则消除了模板跟踪冲突。** Odoo 的 `tracking` 定义在 `product.template`，同模板变体共享。项目负责人现已确认同一 `productCode` 的 `productForm` 跨 owner 必须一致，因此首次建立模板时可按 productForm 确定 tracking，后续同码变体复用模板且保持该值，不会出现同模板原材料与半成品/成品混用的合法场景。
3. **现有 API 使用原始 `productCode` 作为 `default_code`。** API01/03/API07 按 `default_code + ginlong_owner_code` 查找；API09 和 API04/06/08 回传代码也从 `default_code` 取值。改为组合内部编码后，必须在产品变体保存原始 Ginlong `productCode`，并调整这些查找与回传点。ORM 探针证明当前 API01/03 查找器无法用原始编码找到 `default_code` 已改为组合值的产品。
4. **API07 已有 `productForm` 持久化，但 API 规则未落地。** 现有 API07 已把 `productForm` 保存到变体字段 `ginlong_product_form`；临时 ORM 探针确认“原材料”“半成品”“成品”均可保存且可更新。当前 API07 仍接受其它非空值，三值白名单尚未实现。
5. **`ginlong_product_form` 当前存储层级与新业务语义不同。** 当前字段定义在 `product.product`，但正式规则将同一 `productCode` 的形态作为模板共享属性；需在实施设计中将该字段的权威值放到 `product.template`，并核对/迁移历史变体字段值。此处为模型映射变化，不代表本次已修改代码。
6. **开发库不代表实际库存迁移状态。** 当前库有 13 个模板、13 个变体、8 个产品带货主码 `2110`，但找不到对应货主联系人；没有已登记变体属性、库存量或 move line，只有仓库 `KRWH / KarlRapp-WH`。临时 ORM 测试只能证明 Odoo 机制，不证明 KR 实际库存已同步。
7. **Odoo 标准 Picking 的 SN 行为已用 ORM 验证。** 原材料模板使用 `tracking='none'` 时可在无 SN 情况下完成；半成品/成品模板使用 `tracking='serial'` 时，KR 返回 SN 可用于完成 Picking 并形成 Lot 关联。v0.3 另验证了混合 tracking 情景的技术边界，但该情景现被同码 productForm 一致性规则排除，不作为本项目处理路径。真实 KR/Gateway 数据映射仍未验证。

**建议：** API07 以 `productCode` 找到/创建共享模板；首次创建时记录 `productForm` 并按该值设置模板 tracking：原材料=`none`，半成品/成品=`serial`。现有 `ginlong_product_form` 位于 `product.product`，建议后续技术设计将同名字段迁移到 `product.template` 作为唯一权威值，不增加平行字段；迁移前核对现有变体值。不同 owner 后续复用模板并建立各自变体；form 不一致则拒绝且不修改已有产品。Odoo 消费 KR 实绩时读取 KR SN 并写入原生 Lot/move line，不开发本地扫码流程。三值枚举仍是项目负责人规则，Ginlong V3.2 未正式列举这些枚举。

## 3. 方法与数据库基线

| 验证方法 | 实际结果 |
| --- | --- |
| 源码阅读 | 检查 Odoo 原生产品模板、变体、库存跟踪代码；`ginlong_apis` API 服务/扩展字段；`worlddepot` 产品查找、入库/出库模型与拣货流程。 |
| Ginlong 文档核对 | V3.2 API07 0709 字段为必填 `VARCHAR(40)` 且无枚举；请求示例含自由文本；物料信息表 8 行有 4 个“原材料”、4 个“成品”，未出现“半成品”。旧 `.xls` 只读转换到 `/private/tmp` 后扫描，未修改原文件。 |
| ORM 只读检查 | `ginlong_apis`、`worlddepot`、`product`、`stock` 均为 installed；`product.template` 13 条、`product.product` 13 条、`res.partner` 7 条、`stock.quant` 0 条、`stock.move.line` 0 条；仓库 1 个：`KRWH`。 |
| 产品数据检查 | 有 8 个产品带 `ginlong_owner_code='2110'`；没有 `res.partner.ginlong_owner_code='2110'` 的联系人；当前 13 个有内部编码的产品没有重复 `default_code`；13 个模板均没有属性行。上述均为查询当时开发库事实。 |
| 模板同步检查 | `check_template_sync.py --repo-root <项目根目录> --template technical-verification` 返回 `BLOCKED：找不到项目模板来源`；仓库缺少 `docs/context/cognition/template/Designing/Technical_Verification_Guide.md` 来源文件。按既有批准的流程例外记录为 BLOCKED，未将模板同步标为 PASS。 |
| 变体/库存 ORM 探针 | 临时建一个有两个货主属性值的模板和两个变体，分别写入货主码、Ginlong 单位和重量；通过 Odoo `stock.quant._update_available_quantity` 建立 12/7 数量并给其中一项预留 3，调用 API09，随后显式回滚。 |
| API07 ORM 探针 | 临时建测试货主、项目、API 用户，直接调用当前 `api07()` 服务创建/更新三种 `productForm`，并验证缺失/未列值行为；随后显式回滚。该探针验证的是现有实现，不是新增代码。 |
| 产品查找探针 | 临时产品的 `default_code` 使用组合码，调用现有 `_find_product()` 按 Ginlong 原始产品码及货主码查询，得到“未找到”；随后显式回滚。 |
| Picking / SN ORM 探针 | 在回滚事务中创建临时模板、原材料/半成品变体及入库 Picking，分别验证模板 tracking=serial 与 none、KR SN 对应 lot_name 文本及显式 `stock.lot`/`lot_id` 写入，调用标准 `button_validate()`，并检查 move line、quant 的 lot 归属；所有记录均显式回滚。 |
| v0.4 新增 ORM 尝试 | 本轮只读 Odoo shell 在启动阶段遇到 sandbox 对 psutil 系统进程枚举的 `PermissionError`，未得到可引用的新 ORM 输出；未创建或写入记录。v0.4 沿用 v0.3 已完成的 ORM 证据；同码多 owner API07 一致性逻辑尚未实现，交由 CC-GIN-005 测试。 |

## 4. 技术验证事项

### TV-001 — Odoo 原生变体生成及字段隔离

**Question**  一个产品模板能否按货主生成多个原生变体，并保存不同货主的产品属性？

**Method** 阅读 `addons/product/models/product_attribute.py` 的 `create_variant`、`addons/product/models/product_template.py` 的 `_create_variant_ids()`，并用 Odoo ORM 创建一个 `create_variant='always'` 属性、两个属性值和一个模板。

**Result — VERIFIED** 试验生成了两个 `product.product`，关联同一 `product.template`；两个变体可分别保存不同的 `ginlong_owner_code`、`ginlong_unit` 和 `ginlong_weight`。该方式使用原生属性组合，不需要独立货主产品映射模型。

**Evidence** ORM 结果为两个变体；其 Ginlong 字段分别读回 `TV-A… / PCS / 1.25` 与 `TV-B… / BOX / 2.5`。字段定义见 `mymodules/ginlong_apis/models/wms_extensions.py` 的 `ProductProduct` 扩展。当前实际数据库没有产品属性行，因此目标结构尚未用于现有业务数据。

**TDD Impact** 原生变体可作为实现基础。若用属性值表示 owner，必须限定一个产品模板的 owner 维度，并考虑现有/未来其他属性与变体组合的乘积；同一 owner 与原始产品码仍需在 API 层唯一定位。

### TV-002 — 原生库存按变体隔离及 API09 查询

**Question**  不同 owner 的同一原始产品码能否分别形成 Odoo 库存，并由 API09 按货主取数？

**Method** 在上述两个变体对应同一内部库位，分别通过 Odoo 库存 ORM API 记录 owner A 的 12 件（预留 3 件）与 owner B 的 7 件；调用当前 `services.api09()`，检查结果、请求货主及数量。

**Result — VERIFIED（隔离与实物数量口径） / NOT VERIFIED（目标产品编码响应）**

- 原生库存记录分别按 `product_id` 和 `owner_id` 保存，试验中 A 查询只返回 A 变体数量 12，B 查询只返回 B 变体数量 7；API09 用 `quantity:sum`，没有减去 `reserved_quantity`，故返回的是物理在手数量。
- 当前 API09 的响应从 `product.default_code` 填 `productCode`。试验中它返回了内部组合码（`TV-P001-A-…`、`TV-P001-B-…`），而不是 Ginlong 原始 `P001`。目标响应必须改用变体上的原始 Ginlong 产品码字段。
- 试验把 stock owner 和产品变体 owner 设置为同一联系人。现有入库拣货创建代码以 `record.owner.id` 作为 stock owner；API01 同时写入 Ginlong 扩展字段 `ginlong_owner_id`。应在实现测试中确认这两个货主来源一致，不能只凭变体货主码推断库存 owner。

**Evidence** `mymodules/ginlong_apis/services.py` `api09()` 按 owner 联系人匹配 `res.partner.ginlong_owner_code`，按 warehouse 的 `stock.warehouse.code` 找库位范围，查询 `stock.quant.owner_id`，按 `product_id` 汇总 `quantity`，并读取 `product.default_code` 输出。ORM 探针结果 A=`12.0`（reserved=`3.0`），B=`7.0`；临时库存全部回滚。当前开发库本身没有 stock quant，不能用其证明真实库存数据已到达 Odoo。

**TDD Impact** 保留当前按联系人及仓库过滤的边界，并加入产品变体 owner 及原始产品编码条件，确保三个维度 `owner + warehouse + productCode` 一致；回传外部码使用原始码字段。确认 stock move 的 owner 来源与订单 Ginlong owner 一致后再编写集成测试。

### TV-003 — productForm 一致性与模板级 tracking 的技术关系

**Question**  Odoo 的模板级 `tracking` 能否与“同一 `productCode` 跨 owner 的 `productForm` 必须一致”规则配合，正确处理 KR 返回的 SN？

**Method** 使用 v0.3 已完成的 Odoo 18 CE 源码检查及 ORM Picking 探针证据：确认 `product.template.tracking` 的共享范围；验证 `tracking='none'` 的原材料无 Lot 入库，以及 `tracking='serial'` 的跟踪产品在 move line 有 KR SN 时通过标准 `button_validate()` 并形成 Lot 关联；同时保留 v0.3 混合形态探针作为反例。v0.4 新增的只读 Shell 尝试未能通过 sandbox 的 psutil 进程枚举阶段，未产生可引用的新 ORM 输出。

**Result — VERIFIED（字段范围及标准 Picking 行为）；NOT VERIFIED（新 API07 一致性逻辑）**

- `tracking` 定义在 `product.template`，所有货主变体共享。同一 `productCode` 的 `productForm` 若按负责人规则保持一致，则同模板变体需要相同 SN 策略，消除了“同模板原材料与成品使用不同 tracking”的合法业务冲突。正式规则将其定义为模板共享属性；当前 `ginlong_product_form` 仍在变体模型，权威值应在实现时迁移/承载于模板。
- 已有 ORM 探针验证：原材料模板 `tracking='none'` 可在无 SN 情况下完成标准入库 Picking；模板 `tracking='serial'` 且 KR SN 已映射到 move line 时，标准 Picking 可完成并形成 Lot 关联。该证据验证 Odoo 原生机制，不代表现有 API07 已实现新业务校验。
- v0.3 曾验证混合 productForm 时 `tracking='serial'` 会阻止无 SN 的原材料行；`tracking='none'` 配显式 lot 关联可绕开该冲突。该技术事实保留，但混合形态现在违反项目规则，因此此路径不再是本项目的建议实现。
- 当前 API07 还没有跨 owner 复用模板或同码 productForm 比对；冲突拒绝、明确错误及“不修改已有产品”行为均待 CC-GIN-005 实现和自动化验证。

**Evidence** `addons/stock/models/product.py:721-726` 定义模板级 `tracking`；`addons/stock/models/stock_picking.py:1340-1385` 对 tracked move line 校验 Lot/Serial Number；`addons/stock/models/stock_move_line.py:47-50, 596-663, 719-729` 定义 Lot 字段并在过账时按 move line Lot 记录库存。v0.3 ORM 记录见本报告历史版本及其中 Picking/SN 探针结论；所有临时业务记录均回滚。

**TDD / CC Impact** 同一 `productCode` 首次创建模板时记录共享 `productForm` 并决定模板 tracking：原材料=`none`，半成品/成品=`serial`。当前 `ginlong_product_form` 在 `product.product`；TDD 应将同名字段的权威值调整到 `product.template`，或定义等效的模板级存储与兼容迁移，不增加平行字段。后续 owner 变体复用同一模板。API07 在写入任何产品前完成跨 owner 一致性比较；不一致返回能指出产品码和不一致原因的错误，拒绝请求，不改变已有产品字段或变体。KR 采集并返回 SN，Odoo 只校验和记录到标准 `stock.lot`/`stock.move.line.lot_id`，不开发现场扫描。

### TV-004 — 组合内部编码对现有 Ginlong/WMS 查找的影响

**Question**  把 `default_code` 变为 owner 与产品码的无歧义组合后，现有 API 和 WMS 是否仍按原始产品码工作？

**Method** 检查 API01/03/07/09、Hoymiles 通用产品查找和回传 Payload 的代码；ORM 临时建立 `default_code` 为组合值的产品，以原始产品码调用 `_find_product()`。

**Result — NOT VERIFIED（现状与新编码兼容）；必须改造查找与对外编码路径。** `_find_product()` 当前以 `default_code=productCode AND ginlong_owner_code=owner` 查询；组合码不等于 Ginlong 原始 `productCode`，实际探针报产品不存在。API07 当前也以原始 `default_code` 定位并把它写回 `default_code`。API09 与 API04/06/08 回传也使用 `default_code`，会将内部组合值发给 Ginlong。`worlddepot/controllers/hoymiles/product_lookup.py` 也先按 `default_code` 查找，复用产品的跨系统调用需回归。

**Evidence** `mymodules/ginlong_apis/services.py:120-136, 435-485, 488-540`；`mymodules/ginlong_apis/models/ginlong_callbacks.py:53-84`；`mymodules/worlddepot/controllers/hoymiles/product_lookup.py:17-44`。开发库的 `product.product.default_code` 原生字段仅有索引，没有 SQL 唯一约束；当前 `product.product._sql_constraints` 为空。

**TDD Impact** 在 `product.product` 保留 `ginlong_product_code` 原始码以及 owner 标识；`default_code` 使用可逆、无歧义的组合码。API01/03/07 以 `(owner, ginlong_product_code)` 定位；API09 与 Ginlong 回传使用原始码；既有其他 WMS API 的 raw-code/barcode 查找要保持兼容或有明确迁移测试。组合编码格式、分隔/转义和唯一约束应在 TDD 冻结前定案。

### TV-005 — API07 `productForm` 存储与业务规则实现差距

**Question** 现有 API07 是否具备按同一 `productCode` 复用模板、创建 owner 变体并执行 form 一致性规则的能力？

**Method** 核对 V3.2 API07 字段、物料表样例、`ginlong_product_form` 字段与 `api07()` 服务实现；引用 v0.3 的 ORM 验证结果，并对照项目负责人最新决策检查现有代码覆盖范围。

**Result — VERIFIED（现存字段/基础写入行为）；NOT VERIFIED（新业务规则实现）** 现有 API07 必填 `productForm` 并将其保存到变体级 `product.product.ginlong_product_form`；之前 ORM 探针确认三种项目允许值可存取，缺失字段会拒绝，未知非空值目前会被接受。正式规则要求该属性对模板/`productCode` 共享。现有 API07 仍按 owner 与 raw `default_code` 查找产品，未按 `productCode` 跨 owner 复用模板，也未检查一致性、模板级存储或冲突请求下产品不变。

**Evidence** V3.2 API07 字段 0709 为必填 `VARCHAR(40)` 且未列举枚举；请求样例含自由文本；物料表样例含“原材料”“成品”但没有“半成品”。字段定义在 `mymodules/ginlong_apis/models/wms_extensions.py`，服务实现见 `mymodules/ginlong_apis/services.py:435-485`。字段及基础 API07 行为的 ORM 证据记录在 v0.3，临时记录均回滚。

**TDD / CC Impact** API07 必须拒绝三类之外的值，并按原始 `productCode` 找到同码共享模板、在 owner 维度创建变体。用共享模板的 `ginlong_product_form` 比较新请求；不一致时在任何产品写入前返回明确错误。冲突拒绝及已有产品不变应由 CC-GIN-005 自动化测试证明。V3.2 没有正式确认三值枚举；这是项目负责人决策，不能记为 Ginlong 已确认。

### TV-006 — 原生 WMS 关系兼容性

**Question**  原生变体能否作为现有 WMS 订单和库存移动的产品引用？

**Method** 检查已注册 ORM 关系及订单/库存代码。

**Result — VERIFIED（模型引用层）；PARTIAL（业务流程层）** 入库产品托盘、出库产品、`stock.move`、`stock.move.line` 的 `product_id` 均指向 `product.product`，原生变体可被现有订单和库存模型引用。当前开发库没有 stock moves/quants；未执行完整入库、出库、分配及过账流程，故未声称 WMS E2E 已通过。实际 owner 分配和 KR XML 中 SN 到 `stock.move.line` 的映射也需按目标字段/流程回归。

**Evidence** ORM 字段元数据显示上述 `product_id` 均关联 `product.product`；入库拣货代码 `mymodules/worlddepot/models/inbound_order_create_piking.py:35-43` 把 `record.owner` 写入 picking owner；出库拣货从托盘/库存 quant 获取 owner，并写入 move line。现有出库分配路径会使用 `product_id.tracking` 和库存产品/owner 数据。

**TDD Impact** 复用原生产品和库存移动模型，不新增库存台账。需在实现阶段分别验证 owner A/B 变体的订单行、Picking、Lot/SN、stock quant 归属与 API09 输出链路。

## 5. API01/03/04/06/07/08/09 改造影响分析

| API | 目标处理与数据来源 | 当前实现及影响 |
| --- | --- | --- |
| API01 | 接收 Ginlong 入库指令；货主不存在则按已批准规则创建/复用 Contact；按 `(owner, productCode)` 定位产品变体。订单接收不代表 KR 已收货，不更新实际库存。 | 当前按 raw `default_code + ginlong_owner_code` 查找，并关联三层入库订单。变体实施需改用原始 Ginlong 产品码字段，并核实 `ginlong_owner_id`、基础 `owner` 与后续 Picking 的 `stock owner` 一致。 |
| API03 | 接收 Ginlong 出库指令；按 `(owner, productCode)` 校验已有产品变体，缺失货主或任一组合时拒绝整单，不自动创建产品/货主。订单接收不代表 KR 已拣货或发货。 | 当前按 `default_code + ginlong_owner_code` 查找。变体实施需改用原始码字段并保留整单事务完整性；后续仓库执行及库存结果来自 KR XML。 |
| API04 | 从 Odoo 根据 KR 实际收货结果生成/完成的 `stock.picking`、`stock.move.line` 回传入库完成；SN（适用时）读取已记录的 Lot/序列号。 | 现有回传使用 `product_id.default_code` 输出产品编码。切换内部组合码后必须回传原始 Ginlong `productCode`；本次已验证标准 Lot/`lot_id` 的 Odoo 入账路径，但未验证 KR XML 到 move line 的实际映射。 |
| API06 | 以 KR 实际备货结果对应的 `stock.picking`、`stock.move.line` 回传备货完成；不得以 Order 计划量或 Picking 创建动作冒充实际备货。 | 使用的产品引用为 `product.product`。需要按实际变体及 move line 读取产品、数量、托盘和已记录 SN；本次只评估变体与 SN 记录兼容性，不验证 API06 字段口径或回传协议。 |
| API07 | 按 `productCode` 定位/创建共享产品模板，按 owner 创建/复用变体；货主不存在按已批准规则创建/复用 Contact。productForm 仅允许“原材料”“半成品”“成品”，且同码跨 owner 必须一致；不一致拒绝且不修改已有产品。 | 当前 API07 以 owner+raw `default_code` 单独查找/创建产品，未复用跨 owner 模板；虽然写入变体级 `ginlong_product_form`，但未执行三值白名单或同码跨 owner 一致性检查，也未把该值作为模板级权威属性保存。`productName`、UoM 是共享模板字段，需继续评估 owner 间差异。 |
| API08 | 从 KR 实际发货结果对应的 Order 状态及 `stock.picking`、`stock.move.line` 回传发货完成；SN 读取 KR 实绩关联的 Lot。 | 回传产品编码当前取 `product_id.default_code`，组合内部编码实施后要输出原始 Ginlong `productCode`。不在本 TV 推断发货确认状态或新增现场操作流程。 |
| API09 | 只读查询 Odoo 已有的物理库存，按 `owner + warehouse + productCode` 隔离，返回原始 Ginlong 产品编码，不扣预留量。 | 当前按 `res.partner.ginlong_owner_code`、`stock.warehouse.code`、`stock.quant.owner_id` 查询并汇总 `quantity`，临时 ORM 结果不扣 reserved quantity；需增加变体 owner/raw productCode 条件。当前开发库没有库存数据或双仓样本，未验证真实 KR 同步数据。 |

**跨接口影响：**当前 API04/06/08 回传及 API09 响应读取 `product_id.default_code`。若实施组合内部编码，相关 Ginlong 请求匹配和响应字段均需使用单独保存的原始 `ginlong_product_code`，并回归其他仍按 `default_code` 查询的 WMS 路径。KR 现场作业完成后，Gateway 仅做安全解析及 XML→JSON 转换；业务字段到 Odoo 订单/Picking/move line 的映射由 Odoo 侧完成。

## 6. API07 `productForm` 规则与 Odoo tracking

### 6.1 字段契约及项目负责人规则

| 项目 | 规则 / 依据 |
| --- | --- |
| Ginlong V3.2 字段 | `productForm` 必填，`VARCHAR(40)`；V3.2 未列举枚举，样例含 `Three-phase Asynchronous Motor`。 |
| 项目允许值 | “原材料”“半成品”“成品”；其它值拒绝。该枚举是项目负责人规则，不表示 Ginlong 已确认。 |
| 唯一性范围 | 同一 `productCode` 的 `productForm` 必须一致，不受 `owner` 变化影响。 |
| 原生模板 | 首次创建产品模板时记录该码的 `productForm`，并据此确定模板级 `tracking`。不同 owner 的同码物料复用模板，建立/更新各自变体。 |
| SN / tracking 对应 | 原材料不要求 SN，对应 `tracking='none'`；半成品、成品要求 KR 实绩 SN，对应 `tracking='serial'`。同码跨 owner 一致性确保共享模板的 tracking 不冲突。 |
| SN 来源与职责 | KR WMS 现场采集并在 XML 实绩中返回 SN；Gateway 安全解析并转换 XML→JSON；Odoo 校验并关联 Odoo 标准 Lot/SN 记录，不执行扫描。 |
| Odoo 字段 | 复用现有字段名 `ginlong_product_form`，但当前定义在 `product.product`；正式语义为共享模板属性。TDD/CC 应将其权威值放到 `product.template`（或提供等效模板级存储），并迁移/核对历史值；不新增平行字段、产品模型或 `snTrackingRequired`。 |

### 6.2 API07 请求校验与测试矩阵

API07 首次收到某个 `productCode` 时，以请求 `productForm` 建立模板的产品形态基线并设置 `tracking`；随后不同 owner 的同码请求先对照该码已有产品形态。匹配则复用模板并处理该 owner 变体；不匹配则返回明确错误，拒绝请求且不修改任何已有产品。缺少 `productForm` 或取值不在允许列表时也拒绝。

| 场景 | 预期行为 | 当前证据 / 后续验证 |
| --- | --- | --- |
| 首次 Add：原材料 | 创建模板和首个 owner 变体；模板保存 form；tracking=`none` | 当前变体字段基础保存及 Odoo none tracking 行为 **VERIFIED**；模板级字段迁移及新 upsert **NOT IMPLEMENTED** |
| 首次 Add：半成品/成品 | 创建模板和首个 owner 变体；模板保存 form；tracking=`serial` | 当前变体字段基础保存及 Odoo serial Picking/SN 行为 **VERIFIED**；模板级字段迁移及新 upsert **NOT IMPLEMENTED** |
| 不同 owner、同码、同 form | 复用既有模板，创建对应 owner 变体；不改变模板 tracking | Odoo 原生变体机制已有 TV-001 证据；API07 共模处理 **NOT IMPLEMENTED** |
| 不同 owner、同码、不同 form | 拒绝并返回明确错误；已有模板、变体及字段保持不变 | 项目负责人已确认规则；当前 API07 未实现，CC-GIN-005 必须验证拒绝与不变性 |
| 同 owner 更新，form 保持一致 | 更新允许的产品资料，不改变共享模板 tracking | 现有字段更新已在 v0.3 ORM 验证；一致性路径待测试 |
| 同 owner 更新，form 与已建同码产品不一致 | 拒绝；不修改已有产品 | 新规则覆盖，当前未实现，CC-GIN-005 验证 |
| 缺失或非法 productForm | 拒绝且不创建/更新产品 | 缺失字段当前已验证拒绝；非法值当前会被接受，白名单待实现 |
| KR 实绩：原材料无 SN | Odoo 标准 Picking 可按 tracking none 记录实际入库 | v0.3 ORM 标准 Picking 证据 **VERIFIED**；Gateway 数据映射未验证 |
| KR 实绩：半成品/成品带 SN | Odoo 标准 serial tracking 根据 KR SN 完成 Picking 并记录 Lot | v0.3 ORM 标准 Picking 证据 **VERIFIED**；真实 KR/Gateway 映射未验证 |

**实施边界** 产品形态一致性是 API07 的业务校验，不应作为不同货主间可变的 owner 属性。检测到冲突时应先校验、后写入，避免产品部分更新。Odoo 端只消费 KR 提供的 SN 并按产品 tracking 写入实际 `stock.move.line`；不重复采集、不建立 Odoo 扫码功能。模板 `tracking` 不应由后续同码 owner 请求重设。

## 7. 数据迁移与兼容性风险

1. **默认编码迁移。** 现有 Ginlong 产品把原始 `productCode` 存在 `default_code`；新方案要保存原始码并把内部码改成无歧义组合。必须先生成旧 `default_code`、owner code、新原始码、新组合码的迁移清单；核对碰撞、长度及已有引用。Odoo 原生产品未提供 default_code 全局唯一 SQL 约束，不能仅凭默认编码假设唯一。
2. **模板合并/变体重构。** 当前 API07 对同一 raw productCode 的不同 owner 建不同模板/单变体；新方案要求同一基础产品模板下形成不同 owner 变体。合并模板可能影响模板级名称、分类、UoM、tracking、销售/采购属性、供应商、历史单据关联及库存估值。开发库当前没有重复编码、属性行或库存，不能代表目标环境安全迁移。
3. **共享字段覆盖。** Odoo `name`、`uom_id` 和 `tracking` 是模板级；现有 API07 把 `productName` 和 UoM 写入模板。同一模板多个 owner 的值若不同，会互相覆盖。Ginlong 名称是否允许按 owner 不同，Odoo 库存基础单位是否必须一致，需要确定；Ginlong `unit` 文本字段可独立存储，但不能因此推断 Odoo 库存单位也可逐变体不同。
4. **库存 owner 与产品 owner 是两个关系。** 变体 `ginlong_owner_code` 和 `stock.quant.owner_id` 分别标记产品归属与库存所有者。现有 Picking 路径会从 Order、pallet 或 quant 取得 owner。迁移/回归须验证二者一致，避免 API09 查询漏库存或跨货主泄漏。
5. **其他 WMS 调用。** `product_lookup.py`、订单查询/报表及 Ginlong 回传目前读取 `default_code`。修改内部编码需一并处理原始码查询和展示，不可将组合码暴露给旧 API 或 Ginlong。
6. **API07 一致性与 tracking 落地。** `ginlong_product_form` 已是变体字段；API07 三值白名单、同码跨 owner 一致性拒绝及“拒绝前不修改”尚未实现。同一 productCode 统一 productForm 后，模板级 tracking 可以按该 form 设置；原材料为 none，半成品/成品为 serial。Odoo 标准 Picking 和 SN 行为已有 ORM 证据，但完整 KR 实绩导入及变体关联未验证。
7. **开发库基线有限。** 当前 8 个 Ginlong 产品 owner code 均为 `2110`，但没有匹配联系人；库存、move line 为空。API01/API07 的 owner Contact 创建/关联和真实库存流转需在实施测试数据库中覆盖，不能从当前产品快照推定已完成。
8. **模板 tracking 与现有 WMS 行为。** v0.3 验证 tracking none 配显式 lot 关联只是混合形态下的技术探针，不再作为本项目方案。当前规则下原材料模板为 none、半成品/成品模板为 serial；完整 `worlddepot` 订单、分配和出库回归尚未执行，CC-GIN-005 需验证 KR 结果导入对这些既有路径的影响。

## 8. 最小技术方案建议（供 Human Review）

1. 复用原生 `product.template` / `product.product`。按 Ginlong 原始 `productCode` 找共享模板，按 owner 建立/复用 `product.product` 变体；不建立货主产品映射模型。保留原始 `ginlong_product_code` 与内部 `default_code` 的区别，并评估现有数据迁移。
2. 复用 `ginlong_product_form` 字段名，建议把现有变体级字段迁移为 `product.template` 上的模板级权威字段，先核对并迁移现有变体值，不增加平行字段。模板首次建立时记录 productForm，并设置模板 tracking：原材料=`none`，半成品/成品=`serial`。后续 owner 变体在写入前与该码现存形态比对；一致才复用模板，不一致拒绝且不修改已存在产品。无需新增 productForm 字段或状态机。
3. API07 只接受“原材料”“半成品”“成品”。当 productCode 已存在时，即使 owner 不同，也必须校验 form 与该码基准一致。对同 owner 的更新采用同一校验；错误响应说明 productCode 已有的形态与本次收到的形态。错误文案可由实现确定，但必须明确且不得把外部未确认规则伪装为 Ginlong 协议。
4. API01 保持已批准的货主自动创建/复用及 owner+productCode 产品变体校验；API03 按 owner+productCode 校验并在缺少任一组合时拒绝整单；API07 根据 productCode 共享模板；API09 只读使用 owner、warehouse、原始产品码筛选实际物理库存。API04/06/08 继续从 KR 实际结果对应的 Picking/move line 回传，不让 Ginlong 订单创建动作代表仓库实际执行。
5. KR 在现场采集 SN 并随 XML 返回实际作业结果；Gateway 仅作安全解析及 XML→JSON 转换。Odoo 消费转换结果并创建/完成 Picking：原材料无 SN，半成品/成品使用 KR 返回 SN 写入 Odoo 标准 Lot/move line。不得开发 Odoo 扫描流程或将 v0.3 的混合 tracking 技术路径作为常规方案。
6. 在适用 SRS/TDD 与 CC 基线完成修订和批准后，CC-GIN-005 应测试 API07 首次创建三类 productForm 对应 tracking、跨 owner 同码一致时复用模板并创建变体、跨 owner 或同 owner 的冲突 form 请求明确拒绝且已有产品完全不变；同时覆盖 API01/03/07/09 多货主产品识别及 API04/06/08 按 KR 实绩读取产品码/SN。使用 Mock Gateway JSON，不宣称已验证 Gateway/KR 真实联调。
7. 先对目标库按原始 `productCode` 扫描多模板、重复 owner 和不一致 productForm；在测试环境验证合并/迁移及回滚。API07 不应静默自动合并历史重复模板，也不应在收到冲突请求时改写其 form 或 tracking。

## 9. Open Items

| # | 待确认内容 | 影响 |
| --- | --- | --- |
| OI-01 | Ginlong 是否正式确认 `productForm` 只会发送“原材料”“半成品”“成品”？V3.2 未列举枚举，且接口示例含 `Three-phase Asynchronous Motor`；本地已决定拒绝其它值。 | 若真实报文出现其它值，API07 将按项目规则拒绝；这是外部兼容风险，不改变本地规则。 |
| OI-02 | 不同 owner 的同码产品是否可能有不同 `productName` 或 Ginlong unit？如何将 `ginlong_product_form` 从现有变体字段迁移到模板级权威值？ | 前者决定模板共享名称、库存 UoM 与变体 Ginlong 属性的边界；后者需先扫描历史变体并安全迁移，不能静默覆盖冲突值。productForm 跨 owner 一致规则已确定。 |
| OI-03 | 内部 `default_code` 组合码的格式、可逆规则和长度策略。 | 决定查找、迁移及其他 WMS 调用改造方式。 |
| OI-04 | Ginlong 产品 owner 是否继续使用 `ginlong_owner_code` 字符串，或需要与 `res.partner` 强 Many2one 关系？ | 影响产品 owner 完整性、联系人改码及 API09 过滤；不改变 API07 用 owner+productCode 定位变体的业务规则。 |
| OI-05 | API09 对无 `stock.quant.owner_id` 的实际库存应如何处理，以及产品 owner 与库存 owner 不一致时的处置。 | 影响库存隔离及数量是否纳入查询；需结合现有 WMS 来源确认。 |
| OI-06 | 目标库是否存在同一 Ginlong `productCode` 多模板、不同 productForm 或已有库存/单据引用，以及迁移对应关系。 | 当前开发库不足以证明目标库数据可直接合并；迁移前需只读扫描并在测试环境验证。API07 不得自行修复冲突数据。 |
| OI-07 | KR XML 中 SN 字段及其与订单行、产品、实际数量的关联方式；当前没有 KR XML 样例或 Gateway 转换契约。 | 阻塞真实 XML 数据映射；CC-GIN-005 可先用 Mock 转换结果验证 Odoo 业务处理，真实映射待资料到位后确认。 |
| OI-08 | 代表性产品/订单数据下，现有 `worlddepot` 在模板 tracking=`none` 或 `serial` 时的入库、分配及出库回归结果。 | 标准 Odoo Picking 行为已有 v0.3 证据，但完整 WMS 集成回归尚未执行，纳入 CC-GIN-005。 |
| OI-09 | 新确认的 form 一致性规则尚未纳入冻结 SRS v1.0 FR-GIN-007、TDD v0.9 或 CC-GIN-005 v0.2 Draft；如何完成上游基线与计划影响评估？ | 本 TV 记录规则和技术影响，但不修改上游文档。进入实现前须按项目工作流修订/批准适用的 SRS、TDD 及 CC，并评估 IMPLEMENTATION_PLAN v1.0 的基线有效性；未完成前不得把本规则作为已冻结实施基线。 |

## 10. 项目负责人决策记录与 IHR 要求

**2026-11-19 项目负责人决策：**同一 `productCode` 的 `productForm` 必须跨 owner 一致。首个 owner 产品建立共享模板并记录 `productForm`，据此设置 Odoo 模板级 tracking；其他 owner 同码产品复用模板、建立对应变体。匹配则正常处理；不匹配则 API07 返回明确错误并拒绝请求，不修改已有产品。结合此前决定：API07 仅接受“原材料”“半成品”“成品”；原材料不要求 SN，半成品、成品要求 SN；其他值拒绝。tracking 映射为原材料=`none`、半成品/成品=`serial`。KR 负责实际仓库作业及 SN 扫描并输出 XML；Gateway 安全解析并转换 XML→JSON，不处理业务逻辑；Odoo 接收作业结果、验证并生成/完成 `stock.picking`，记录库存和 SN，不开发 Odoo 扫码流程。V3.2 未定义该三值枚举，Ginlong 尚未正式确认。

本记录及 v0.4 新增的一致性规则作为后续实施 IHR 的决策来源。实施时应在对应 CC 的新增 IHR 条目中引用本报告，写明“项目负责人本地决策 / Ginlong 正式确认未完成”，并保留后续 Ginlong 确认的单独证据；不回写或改写已关闭 CC-GIN-001–004 的历史 IHR。

## 11. 证据索引

- Odoo 原生变体：`addons/product/models/product_attribute.py`、`addons/product/models/product_template.py` 的 `_create_variant_ids()`、`addons/product/models/product_product.py`。
- Odoo 原生库存跟踪：`addons/stock/models/product.py:721-726`；Picking 跟踪数据校验：`addons/stock/models/stock_picking.py:1340-1385`；Lot/序列号及库存移动关联：`addons/stock/models/stock_move_line.py:47-50, 596-663, 719-729`。
- Ginlong 产品字段：`mymodules/ginlong_apis/models/wms_extensions.py` 中 `ProductProduct`。
- API01/03 产品定位：`mymodules/ginlong_apis/services.py:120-138, 156-188, 254-285`。
- API07 当前 upsert：`mymodules/ginlong_apis/services.py:435-485`。
- API09 查询及数量映射：`mymodules/ginlong_apis/services.py:488-540`。
- API04 等回传产品编码：`mymodules/ginlong_apis/models/ginlong_callbacks.py:53-84`。
- WMS 共用产品查找：`mymodules/worlddepot/controllers/hoymiles/product_lookup.py:17-44`。
- WMS 产品导入/原生跟踪：`mymodules/worlddepot/models/my_product_template.py:57-70`。
- WMS 入库库存 owner 来源：`mymodules/worlddepot/models/inbound_order_create_piking.py:35-43`；出库分配：`mymodules/worlddepot/models/outbound_order_create_picking.py`。

**代码修改：无。CC-GIN-005 修改：无。业务实现授权：无。** 本报告 v0.4 Review Draft 提交 Human Review。新业务规则尚未纳入冻结 SRS/TDD 基线；须先按 OI-09 完成上游影响评估与批准，再进入实施。本轮未修改 SRS、TDD、Implementation Plan 或 CC。
