# Ginlong 多货主产品变体与 API07 productForm/SN 规则技术验证报告

| 项目 | 内容 |
| --- | --- |
| 文档编号 | TV-GINLONG-PRODUCT-001 |
| 项目 | `ginlong_apis` / `worlddepot` |
| 版本 | 1.0 |
| 状态 | **Closed with Open Items；Human Review：APPROVED** |
| 验证日期 | 2026-11-19 |
| 技术环境 | Odoo 18 CE；现有 `venv`、`odoo.conf`、开发库 `odooce_karlrapp` |
| Human Review | **APPROVED**；李建强（项目负责人）；2026-11-19；批准关闭 TV-GINLONG-PRODUCT-001 |
| 总体结论 | 产品主数据采用一个 Ginlong `productCode` 对应一个 `product.template`、每个 `owner` 对应一个 `product.product` 变体。模板共享名称、规格、重量、尺寸、productForm 与 tracking；变体保存货主、内部组合码和原始产品编码。Odoo 原生 tracking/Picking 行为已有 v0.3 ORM 证据；模板字段迁移、多货主库存/托盘一致性及 CC-GIN-005 集成仍待实施验证 |

## 修订记录

| 版本 | 状态 | 修订内容 |
| --- | --- | --- |
| 0.1 | Review Draft | 验证原生产品变体、API01/03/07/09 与暂定 `snTrackingRequired` 字段。 |
| 0.2 | Review Draft | 根据项目负责人 2026-11-19 决策，改由 API07 已有 `productForm` 决定 SN 要求；明确本地三种允许值及未知值拒绝；不新增 `snTrackingRequired`。 |
| 0.3 | Review Draft | 纠正 KR、Gateway、Odoo 的仓库作业职责；用 Odoo ORM 实测模板级 tracking 及显式 Lot 关联行为。 |
| 0.4 | Review Draft | 纳入同码跨 owner `productForm` 一致性及模板 tracking 规则。 |
| 0.5 | Review Draft | 明确 Ginlong productCode/owner 与 Odoo template/variant 的字段归属、产品固有属性一致性、货主库存与托盘约束；定义 CC-GIN-005 最小合并范围及明确排除的预分配/Gateway 工作。保留既有验证证据。 |
| 1.0 | Closed with Open Items | 李建强于 2026-11-19 Human Review APPROVED，批准关闭 TV。保留全部 Open Items、既有验证证据及模板同步 BLOCKED，不将其改写为已解决；不修改 SRS/TDD/Implementation Plan/CC，不授权代码实施。 |

## 1. 目的与边界

验证一个 Ginlong `productCode` 对应一个 Odoo `product.template`、不同 `owner` 对应不同 `product.product` 变体的模型；核对 API01/03/04/06/07/08/09、模板/变体字段归属、API07 属性一致性、货主库存及托盘归属要求，并据此提出合并 CC-GIN-005 的最小范围。

系统职责及数据链为：Ginlong 下达指令 → Odoo 管理业务 Order 并转发作业指令 → Karl Rapp WMS 执行实际收货、上架、拣货、SN 扫描及发货并输出 XML → Gateway 接收 KR XML，进行安全解析及 XML→JSON 转换，不处理业务逻辑 → Odoo 接收 KR 实际作业结果，校验并创建/完成 `stock.picking`、`stock.move.line`，记录库存及 SN → Odoo 向 Ginlong 回传结果。Odoo 不执行 KR 现场作业，也不开发额外的 SN 扫描流程；SN 来源是 KR 作业结果。

本次只做源码检查及本地 Odoo ORM 技术验证。未修改 Python、XML、manifest 或业务数据；临时产品、属性、货主、Picking、Lot 及库存均通过 ORM 创建，并在 shell 事务结束前显式回滚。未访问真实 Ginlong、Karl Rapp 或 Gateway 环境，未执行 Gateway 集成测试；未使用 SQL、`stock_barcode` 或官方 Odoo 源码修改。

## 2. 结论摘要

1. **原生产品变体可承载多货主 SKU。** v0.3 的 ORM 证据证明，一个模板可生成多个变体并分别保存货主码及变体字段；沿用该能力可满足一个 `productCode` 一个模板、不同 owner 一个变体的结构，无需建立平行产品模型。
2. **已确认的字段归属。** 模板共享：产品名称、规格、重量、尺寸、`productForm`、`tracking`。变体专属：owner、组合内部编码 `default_code`、原始 Ginlong `productCode`。当前 `ginlong_owner_code`、规格、Ginlong 重量/尺寸、`ginlong_product_form` 都定义在 `product.product`；模板级字段迁移及历史数据整理是实施工作，不是已验证现状。
3. **模板 tracking 与 productForm 规则一致。** 同一 `productCode` 跨 owner 的 `productForm` 必须一致；原材料用 `tracking='none'`，半成品/成品用 `tracking='serial'`。Odoo tracking 是模板级，同码一致性消除了合法业务中的 tracking 冲突。API07 同码 productForm 冲突必须拒绝且不能覆盖原模板。
4. **产品编码仍需变体级双编码。** Odoo `default_code` 是变体字段，适合作为组合内部编码；原始 Ginlong `productCode` 也需保存在变体，供 API01/03/07 查找、API04/06/08/09 对外使用。现有接口按 raw `default_code` 查找/回传，需适配及迁移。
5. **库存所有权与产品变体必须一致。** Odoo `stock.move.line.owner_id` 记录库存货主；`stock.quant.package.owner_id` 是根据包内 quant owner 计算的只读值，包内 owner 不一致时计算结果为空。KR 实绩导入时应验证产品变体 owner、move-line/quant owner 及托盘内容归属一致；当前源码/历史 ORM 证据尚未证明这一整条路径已通过。
6. **真实作业职责保持原架构。** KR 执行仓库作业和 SN 扫描；Gateway 只接收 XML、进行安全解析及 XML→JSON 转换；Odoo 根据 KR 实绩创建/完成 Picking、记录库存/SN 并向 Ginlong 回传。Odoo 不开发现场扫描流程，CC-GIN-005 仅使用 Mock KR 实绩和本地 WMS。

**CC-GIN-005 建议范围：**产品变体及必要迁移；API01/03/04/06/07/08/09 适配；模板共享属性一致性和 API07 冲突拒绝；以模拟 KR 实绩经现有 WMS 流程生成实际 Picking，验证 SN、托盘、库存货主一致性。API03 预留 Picking、Odoo Reserve/托盘库位建议、KR 回传后取消 Picking 1 并创建 Picking 2 的预分配机制，以及 Gateway/真实 XML 联调均排除，预分配另立 CC 并先做 TV/设计。

## 3. 方法与数据库基线

| 验证方法 | 实际结果 |
| --- | --- |
| 源码阅读 | 检查 Odoo 模板/变体字段、tracking、move line owner、package owner 计算；`ginlong_apis` 产品字段/API 服务；`worlddepot` 产品查找、入库拣货及库存路径。 |
| Ginlong 文档核对 | V3.2 API07 0709 字段为必填 `VARCHAR(40)` 且无枚举；请求示例含自由文本；物料信息表 8 行有 4 个“原材料”、4 个“成品”，未出现“半成品”。旧 `.xls` 只读转换到 `/private/tmp` 后扫描，未修改原文件。 |
| ORM 只读检查 | `ginlong_apis`、`worlddepot`、`product`、`stock` 均为 installed；`product.template` 13 条、`product.product` 13 条、`res.partner` 7 条、`stock.quant` 0 条、`stock.move.line` 0 条；仓库 1 个：`KRWH`。 |
| 产品数据检查 | 有 8 个产品带 `ginlong_owner_code='2110'`；没有 `res.partner.ginlong_owner_code='2110'` 的联系人；当前 13 个有内部编码的产品没有重复 `default_code`；13 个模板均没有属性行。上述均为查询当时开发库事实。 |
| 模板同步检查 | `check_template_sync.py --repo-root <项目根目录> --template technical-verification` 返回 `BLOCKED：找不到项目模板来源`；仓库缺少 `docs/context/cognition/template/Designing/Technical_Verification_Guide.md` 来源文件。按既有批准的流程例外记录为 BLOCKED，未将模板同步标为 PASS。 |
| 变体/库存 ORM 探针 | 临时建一个有两个货主属性值的模板和两个变体，分别写入货主码、Ginlong 单位和重量；通过 Odoo `stock.quant._update_available_quantity` 建立 12/7 数量并给其中一项预留 3，调用 API09，随后显式回滚。 |
| API07 ORM 探针 | 临时建测试货主、项目、API 用户，直接调用当前 `api07()` 服务创建/更新三种 `productForm`，并验证缺失/未列值行为；随后显式回滚。该探针验证的是现有实现，不是新增代码。 |
| 产品查找探针 | 临时产品的 `default_code` 使用组合码，调用现有 `_find_product()` 按 Ginlong 原始产品码及货主码查询，得到“未找到”；随后显式回滚。 |
| Picking / SN ORM 探针 | 在回滚事务中创建临时模板、原材料/半成品变体及入库 Picking，分别验证模板 tracking=serial 与 none、KR SN 对应 lot_name 文本及显式 `stock.lot`/`lot_id` 写入，调用标准 `button_validate()`，并检查 move line、quant 的 lot 归属；所有记录均显式回滚。 |
| 后续 ORM 尝试 | v0.4 的只读 Odoo shell 在启动阶段遇到 sandbox 对 psutil 系统进程枚举的 `PermissionError`，未得到可引用的新 ORM 输出；未创建或写入记录。v0.5 沿用此前已有 ORM 证据；本轮不执行数据库测试。 |

## 4. 技术验证事项

### TV-001 — Odoo 原生变体生成及字段隔离

**Question**  一个产品模板能否按货主生成多个原生变体，并保存不同货主的产品属性？

**Method** 阅读 `addons/product/models/product_attribute.py` 的 `create_variant`、`addons/product/models/product_template.py` 的 `_create_variant_ids()`，并用 Odoo ORM 创建一个 `create_variant='always'` 属性、两个属性值和一个模板。

**Result — VERIFIED** 试验生成了两个 `product.product`，关联同一 `product.template`；两个变体可分别保存不同的 `ginlong_owner_code`、`ginlong_unit` 和 `ginlong_weight`。该方式使用原生属性组合，不需要独立货主产品映射模型。

**Evidence** ORM 结果为两个变体；其 Ginlong 字段分别读回 `TV-A… / PCS / 1.25` 与 `TV-B… / BOX / 2.5`。字段定义见 `mymodules/ginlong_apis/models/wms_extensions.py` 的 `ProductProduct` 扩展。当前实际数据库没有产品属性行，因此目标结构尚未用于现有业务数据。

**TDD Impact** 原生变体可作为实现基础。建议用 Odoo 原生产品属性的 owner 维度生成变体，并确保属性值与 `ginlong_owner_code` 对应；`default_code` 保存可区分 owner 的内部组合码，独立字段保存原始 Ginlong `productCode`。需限制该 owner 维度及其与其他变体属性的组合，避免同一 `(owner, productCode)` 产生多个变体。

### TV-002 — 原生库存按变体隔离及 API09 查询

**Question**  不同 owner 的同一原始产品码能否分别形成 Odoo 库存，并由 API09 按货主取数？

**Method** 在上述两个变体对应同一内部库位，分别通过 Odoo 库存 ORM API 记录 owner A 的 12 件（预留 3 件）与 owner B 的 7 件；调用当前 `services.api09()`，检查结果、请求货主及数量。

**Result — VERIFIED（隔离与实物数量口径） / NOT VERIFIED（目标产品编码响应）**

- 原生库存记录分别按 `product_id` 和 `owner_id` 保存，试验中 A 查询只返回 A 变体数量 12，B 查询只返回 B 变体数量 7；API09 用 `quantity:sum`，没有减去 `reserved_quantity`，故返回的是物理在手数量。
- 当前 API09 的响应从 `product.default_code` 填 `productCode`。试验中它返回了内部组合码（`TV-P001-A-…`、`TV-P001-B-…`），而不是 Ginlong 原始 `P001`。目标响应必须改用变体上的原始 Ginlong 产品码字段。
- 试验把 stock owner 和产品变体 owner 设置为同一联系人。现有入库拣货创建代码以 `record.owner.id` 作为 stock owner；API01 同时写入 Ginlong 扩展字段 `ginlong_owner_id`。应在实现测试中确认这两个货主来源一致，不能只凭变体货主码推断库存 owner。

**Evidence** `mymodules/ginlong_apis/services.py` `api09()` 按 owner 联系人匹配 `res.partner.ginlong_owner_code`，按 warehouse 的 `stock.warehouse.code` 找库位范围，查询 `stock.quant.owner_id`，按 `product_id` 汇总 `quantity`，并读取 `product.default_code` 输出。ORM 探针结果 A=`12.0`（reserved=`3.0`），B=`7.0`；临时库存全部回滚。当前开发库本身没有 stock quant，不能用其证明真实库存数据已到达 Odoo。

**TDD Impact** 保留当前按联系人及仓库过滤的边界，并加入产品变体 owner 及原始产品编码条件，确保三个维度 `owner + warehouse + productCode` 一致；回传外部码使用原始码字段。确认 stock move 的 owner 来源与订单 Ginlong owner 一致后再编写集成测试。

### TV-003 — 模板级 tracking 与 KR 实际 SN 入账

**Question**  Odoo 模板级 tracking 是否能按 Ginlong 产品固有 `productForm` 设置，并支持 KR 实绩生成入库 Picking？

**Method** 检查 Odoo `product.template.tracking` 及标准 Picking 校验；沿用 v0.3 ORM 探针中模板 `tracking='none'` 无 SN 入库、`tracking='serial'` move line 有 KR SN 时完成 Picking 并形成 Lot 的结果。v0.3 的混合 productForm 探针保留为旧技术边界，不作为当前合法产品数据情景。

**Result — VERIFIED（tracking 共享层级及标准 Picking 行为）；NOT VERIFIED（KR 实绩端到端生成与货主/托盘匹配）** Odoo `tracking` 定义在模板并由全部货主变体共享。同一 `productCode` 的 `productForm` 被负责人要求跨 owner 一致，因此该共享属性能决定唯一 tracking：原材料=`none`；半成品/成品=`serial`。KR SN 由 Odoo 标准 move line / Lot 机制记录；不需要 Odoo 扫码。

v0.3 ORM 实测 `tracking='serial'` 的 move line 缺少 SN 时标准验证会阻止 Picking；提供 SN 时 Picking 完成并记录 lot。`tracking='none'` 的原材料可以无 SN 完成。此前用 tracking none 加显式 lot 关联的混合形态实验结果仍作为历史事实保留，但该路径不属于当前业务设计。

**Evidence** `addons/stock/models/product.py:721-726`；`addons/stock/models/stock_picking.py:1340-1385`；`addons/stock/models/stock_move_line.py:47-50, 596-663, 719-729`。v0.3 ORM 临时 Picking、Lots、quants 均回滚；未做 KR/Gateway 实际联调。

**TDD / CC Impact** API07 创建模板时依据共享 productForm 设置 tracking；之后同码 owner 变体复用模板且不得重设 tracking。CC-GIN-005 应使用 KR SN 模拟数据经 Odoo 标准 Picking 流程测试。出库预分配中的 Picking/Reserve 行为不在本 TV 验证范围。

### TV-004 — 变体编码及现有 Ginlong/WMS 查找影响

**Question**  同一个 Ginlong `productCode` 在多个 owner 下复用一个模板时，现有 Odoo/API 产品识别是否仍正确？

**Method** 阅读 Odoo `product.product.default_code`、Ginlong 当前产品查找和 API 回传代码；沿用 v0.3 组合码 ORM 探针。

**Result — NOT VERIFIED（新产品身份实现未完成）** Odoo `default_code` 定义在 `product.product`；现有 API01/03/07 以 raw `default_code + ginlong_owner_code` 找产品，API09/API04/06/08 将 `default_code` 当外部产品码。v0.3 探针证明将 default_code 改为组合码后，原始码查找失败，回传会暴露内部组合码。现代码也没有按原始 `productCode` 搜索共享模板/跨 owner 创建变体的流程。

**TDD / CC Impact** 变体须保留：`owner`、可区分 owner 的组合内部编码、Ginlong 原始 `productCode`；模板以原始 `productCode` 为产品级身份。API01/03/07 用 `(owner, raw productCode)` 定位变体，API09 过滤真实库存后返回 raw `productCode`，API04/06/08 使用 raw code 回传。字段迁移与其他 WMS raw-code 查找回归纳入 CC-GIN-005。

### TV-005 — API07 属性归属及产品一致性

**Question**  当前 API07 字段是否落在负责人确定的 template/variant 边界，并能否拒绝同码固有属性冲突？

**Method** 阅读 `wms_extensions.py` 和 `services.api07()` 当前 upsert；沿用 v0.3 API07 ORM 探针中 Add/Edit、缺字段和未知 productForm 行为。

**Result — VERIFIED（现有字段现状）；NOT VERIFIED（新共享模板和一致性逻辑）**

| 属性 | 负责人确认的归属 | 当前代码中的定义/写入 |
| --- | --- | --- |
| 产品名称 | `product.template` | `product.template.name`，API07 写模板 |
| 规格 | `product.template` | `ginlong_specification_model` 当前在 `product.product` |
| 重量、尺寸 | `product.template` | `ginlong_weight/length/width/height` 当前在 `product.product`；Odoo 原生模板 weight/volume 是由变体计算并可反向写入的模板字段 |
| `productForm` | `product.template` | `ginlong_product_form` 当前在 `product.product` |
| `tracking` | `product.template` | Odoo 原生字段，已验证模板共享 |
| owner | `product.product` | `ginlong_owner_code` 当前在 `product.product` |
| 内部组合码、原始 `productCode` | `product.product` | `default_code` 是变体字段；当前没有独立 `ginlong_product_code` 原始码字段 |

现有 API07 按 owner 和 raw default_code 逐产品 upsert；未知非空 productForm 当前会被接受；尚无同码共享模板、一致性比较、明确冲突错误或冲突后模板不变的行为。规格、Ginlong 重量/尺寸及 productForm 从 variant 移到 template 需要核对现存产品值、API 回传/业务读取路径和升级迁移。

**TDD / CC Impact** API07 按原始 `productCode` 找一个模板，按 owner 建/改一个变体；更新共享字段前校验与模板既有属性一致。特别是同码 `productForm` 冲突必须明确拒绝且不覆盖已有模板。productForm 仅接受原材料/半成品/成品；tracking 从 form 确定，不接受 owner 变化或后续 API 请求单独改写。CC-GIN-005 应验证共享属性一致、冲突请求和记录不变。

### TV-006 — 原生 WMS 关系兼容性

**Question**  原生变体能否作为现有 WMS 订单和库存移动的产品引用？

**Method** 检查已注册 ORM 关系及订单/库存代码。

**Result — VERIFIED（模型/字段结构）；PARTIAL（所有权一致性流程）** 订单和 `stock.move.line.product_id` 可引用 `product.product` 变体。`stock.move.line.owner_id` 表示库存货主；`stock.quant.package.owner_id` 为计算只读字段，仅当该包内所有 quant owner 相同才返回该 owner，否则为 False。现有 inbound picking 创建代码将订单 `record.owner` 写入 Picking `owner_id`，但本地源码证据未证明 KR 导入时产品变体 owner、move line owner/quant owner 与 package 中所有内容一定一致。当前开发库无库存/作业数据，未执行此完整流程。

**Evidence** ORM 字段元数据显示上述 `product_id` 均关联 `product.product`；入库拣货代码 `mymodules/worlddepot/models/inbound_order_create_piking.py:35-43` 把 `record.owner` 写入 picking owner；出库拣货从托盘/库存 quant 获取 owner，并写入 move line。现有出库分配路径会使用 `product_id.tracking` 和库存产品/owner 数据。

**TDD Impact** 复用原生产品、Picking、move line、quant、package，不新增库存台账。CC-GIN-005 模拟 KR 实绩时验证变体 owner 与 Picking/move line 库存 owner 一致、包内库存均属于该 owner、API09 不跨 owner 汇总。不得把 package.owner_id 当作可独立写入的托盘主数据字段。

## 5. API01/03/04/06/07/08/09 改造影响

| API | 依据本决策的处理及数据来源 | 当前实现差距 / 后续验证 |
| --- | --- | --- |
| API01 | 读取 Ginlong owner + raw productCode，匹配对应 owner 变体；货主档案按已批准规则创建/复用。收单不产生实际库存变化。 | 当前产品定位用 `default_code + ginlong_owner_code`；迁移后需用 variant raw code。KR 实绩生成 Picking 时核对订单 owner、产品变体 owner、库存 owner、托盘归属。 |
| API03 | 按 `(owner, raw productCode)` 匹配变体；缺失组合按既有规则拒绝。API03 本身不创建预留 Picking 或 Odoo Reserve。 | 查找器需切至变体 raw code。API03 出库预分配明确排除在 CC-GIN-005 和本 TV 范围之外。 |
| API04 | 从 KR 实际收货结果生成/完成的 `stock.picking`、`stock.move.line` 读取真实 SN、产品、数量、托盘并手动回传。 | Callback 不能把内部组合 default_code 发给 Ginlong；货主/托盘一致性需 Mock E2E 验证。 |
| API06 | 从实际备货完成记录读取 `stock.picking` / move lines；遵循已批准的备货事件和字段来源。 | 读取变体及实际作业数据，回传 raw productCode；此 TV 不新增 API06 业务口径。 |
| API07 | 按 raw productCode 找共享模板，按 owner 建变体；模板固有属性共享且一致；三种 productForm 映射模板 tracking，冲突拒绝，不覆盖原数据。 | 当前按 owner+raw default_code 建独立产品，变体字段归属与共享模板流程均需调整；需迁移并测试同码冲突。 |
| API08 | 从对应订单状态及 KR 实际发货 Picking/move lines 手动回传；不在此接口重复扣库存。 | Callback 输出 raw productCode，验证产品变体和 move line owner、托盘所有权一致。 |
| API09 | 只读按 owner + warehouse 查询已记账的实际物理库存，使用库存 owner 隔离，不扣 reservation；响应输出 raw productCode。 | 当前过滤 `stock.quant.owner_id` 并取 `product.default_code`；输出编码需调整。通过现有 WMS 流程生成库存并核对 owner、产品变体及托盘归属；保持 API09 严格只读。 |

**共同边界：** Odoo 不模拟 KR 现场作业。CC-GIN-005 的模拟执行输入经过现有业务流程创建/完成 Picking 和 move line，不能直接改写 `stock.quant`。Gateway 和真实 XML 不在本范围。

## 6. API07 产品属性规则与 tracking

| 条目 | 项目负责人规则 / 当前 Odoo 情况 |
| --- | --- |
| 产品身份 | 一个 Ginlong `productCode` 对应一个 `product.template`；各 owner 对应不同 `product.product` 变体。 |
| 模板共享属性 | 产品名称、规格、重量、尺寸、productForm、tracking；同一 productCode 的固有属性必须一致，owner 不改变属性。 |
| 变体属性 | owner、组合内部编码、原始 Ginlong productCode。不同 owner 的变体可在相同模板下存在。 |
| API07 Form | 只接受“原材料”“半成品”“成品”。同码 form 冲突时返回明确错误、拒绝该请求且不修改已有模板/产品。 |
| Tracking | 原材料=`none`；半成品/成品=`serial`。模板首次创建时确定，后续 owner 变体继承，不单独设置。 |
| SN 来源 | KR 现场扫描并写入 KR 实绩；Odoo 将 KR 返回 SN 映射至标准 move line / Lot，利用 Odoo 原生 serial tracking，不增加 Odoo 扫描流程。 |
| 现有字段 | `ginlong_product_form`、`ginlong_specification_model`、`ginlong_weight/length/width/height` 目前定义于 `product.product`；API07 要求模板共享，需在实施中迁移到模板权威字段并处理旧值，不新增平行字段/模型。 |

### API07 / Picking 测试矩阵（供 CC-GIN-005）

| 场景 | 预期 | 已有证据 / 未完成项 |
| --- | --- | --- |
| 首次 Add 原材料 | 建一个 template + owner variant；模板保存固有属性，tracking=`none` | 原生模板/变体及 none Picking 行为已有 ORM 证据；API07 upsert/迁移未实现 |
| 首次 Add 半成品/成品 | 建一个 template + owner variant；tracking=`serial` | serial 模板有 KR SN 的标准 Picking 行为已有 ORM 证据；API07 upsert未实现 |
| 不同 owner、同码、固有属性一致 | 复用模板，创建正确 owner 变体，不产生另一模板 | 原生变体机制已验证；API07 路径未实现 |
| 不同 owner、同码、productForm 冲突 | 返回明确错误；已有模板属性、tracking、变体均不变 | 项目负责人已确认；实现和自动化证据待 CC-GIN-005 |
| 同码其它已确认共享属性冲突 | 拒绝不一致数据，不覆盖原模板 | 一致性原则已确认；每个字段映射与完整测试待实施 |
| 货主、产品变体、move-line owner、托盘 owner 一致 | Picking 记账后 quant/包内容属于同一 owner | package owner 是 quant 推导且混合 owner 时 False；完整 WMS/KR Mock 流程未验证 |
| KR SN 经 Picking 记账 | 半成品/成品 SN 记录在 Odoo 原生 Lot/move line；原材料无需 SN | 标准 Odoo tracking/Picking 逻辑已有 v0.3 ORM 证据；KR 数据映射未验证 |
| API09 隔离 | 同码跨 owner 不合并，查询只读返回实际数量及 raw productCode | 原始 API09 模拟 ORM 证据有隔离/物理数量结果；新变体/包 owner 关系未集成验证 |

## 7. 数据迁移与兼容性风险

1. **旧的每 owner 单独模板。** 当前 API07 为不同 owner 建独立模板/产品。迁移到每个 productCode 一个模板、多个 owner 变体前，需列明同码模板、属性冲突、历史订单/Picking/库存/估值引用；不得由 API07 在线请求自动合并。
2. **字段模型迁移。** `ginlong_specification_model`、`ginlong_weight`、尺寸及 `ginlong_product_form` 当前在 `product.product`，新规则把这些字段作为 template shared。需读取并比较所有旧 owner 变体值；一致后迁移模板值，冲突数据按项目处理，不静默选首条覆盖。Odoo native `product.template.weight` / volume 可从变体聚合并有反向 setter；Ginlong 自定义字段位置仍需按模型改造。
3. **编码迁移。** 将变体 `default_code` 用于 owner 组合内部码，另存 raw Ginlong `productCode`。API01/03/07 查找、API04/06/08 回传、API09 响应及其他 WMS 查找都需回归。
4. **货主库存关系。** 产品变体 `ginlong_owner_code` 与 `stock.quant.owner_id` 是不同关系；Picking/move line 必须用正确 owner，不能仅从产品字段推算库存归属。
5. **托盘 owner 不是独立可写来源。** Odoo `stock.quant.package.owner_id` 根据包内 quant 计算：无 quant 或包内 owner 不一致时为空；新增/出库移动期间的 package/product/owner 关系须从实际 move lines / quants 验证。
6. **原生 tracking 业务兼容性。** 模板 tracking 与所有变体共享；同码 form 一致后可确定一致跟踪。现有 WMS 全入/出库路径和 KR 回传 Pickings 仍须 CC-GIN-005 回归。
7. **预分配范围排除。** Picking 1 创建、Reserve、预留托盘/库位建议以及收到 KR 结果后取消 Picking 1 并创建 Picking 2 都不纳入 CC-GIN-005；须另立 CC 和 TV，不能在当前实现顺带加入。
8. **外部接口边界。** 本地 Mock KR XML 转换数据不证明 Gateway XML schema、VPN/FTP 或真实 Ginlong；真实联调留相应独立工作。

## 8. 合并 CC-GIN-005 的最小实施范围建议（供后续 CC 修订）

### 纳入

1. 对每个 raw Ginlong `productCode` 维护一个 template；不同 owner 建立/复用对应 variant。模板固有属性共享，货主、内部组合码、原始 productCode 落在 variant。
2. 将 Ginlong 名称/规格/重量/尺寸/productForm 等已批准共享字段及 tracking 从现有 variant 字段迁移/调整到模板层；先扫描、迁移、校验旧数据。API07 对共享属性及 productForm 先比对再写入；冲突明确拒绝，不覆盖已有模板。
3. API01/03/07 按 owner+raw productCode 定位正确变体；API04/06/08 从 KR 实际 Picking/move line 取已保存作业结果；API09 按 owner+warehouse 查询实际物理库存并返回 raw productCode，严格只读。
4. 用明确标记的 Mock KR 实际作业结果，调用现有 `worlddepot` WMS 流程创建/完成标准 Picking。验证产品变体 owner、Picking/move-line/quant owner 和托盘内容 owner 一致；验证半成品/成品 KR SN 走 Odoo native serial tracking、原材料不要求 SN；跨 owner 同码产品库存不混合。
5. 最小数据迁移、API01/03/07/09 和回传 Payload 的跨 owner 回归；仅运行受影响的自动化、ORM、组件集成及 CC 定义的本地浏览器 E2E。将完整证据记在后续 CC 的 ATR/IHR/HVR。

### 明确排除

- API03 创建预留 Picking 1。
- Odoo 原生 Reserve、预留托盘及库位建议。
- KR 回传后取消 Picking 1、再创建 Picking 2 的预分配机制。
- `karlrapp_gateway` 开发、真实 KR XML 联调、真实 Ginlong API/生产访问。

出库预分配另设独立 CC，先做 TV 与设计。Gateway/XML 作为独立项目处理。

### 上游门禁

新产品模板身份、属性归属和一致性规则会影响冻结的 SRS v1.0/TDD v0.9、Implementation Plan v1.0 与 CC-GIN-005 草案。实施前需完成上游需求/设计影响评估、必要修订与批准，更新计划有效性和 CC 追溯；本 TV 不自行修改这些文档或授权编码。

## 9. Open Items

| # | 待确认/待实施验证 | 影响 |
| --- | --- | --- |
| OI-01 | Ginlong 是否确认 `productForm` 只发送“原材料”“半成品”“成品”？V3.2 未列举枚举且样例含自由文本；本地规则只接受三值。 | 其它值按项目决定拒绝；外部兼容风险保留。 |
| OI-02 | API07 其余字段（如 unit、power、nationalStandard、certificationModel）的模板/变体字段落位及一致性比较范围。 | 不得由 owner 导致同码产品固有属性分叉；具体字段模型在 TDD 明确。 |
| OI-03 | 目标数据中同一 raw productCode 是否有多个模板、模板共享字段是否冲突及引用迁移关系。 | 需只读扫描并制定测试环境迁移/回滚；API07 不在线合并。 |
| OI-04 | 内部 `default_code` 组合编码格式、可逆规则和长度策略；旧 raw default_code 的引用迁移。 | API 查找、回传与其他 WMS 产品查找需要统一改造。 |
| OI-05 | KR 生成 Picking 时的 owner 写入来源以及是否能同时保证 product variant owner、move-line/quant owner 和 package 内容归属一致。 | 源码可见 stock move line owner 和 package 计算字段，但没有实际 KR 结果集成证据；列入 CC-GIN-005 Mock ORM/WMS 验收。 |
| OI-06 | API09 对没有 `stock.quant.owner_id` 的库存、或产品 owner 与库存 owner 不匹配时的处理。 | 影响库存隔离和物理数量口径；以批准规则/真实数据来源确定，不从产品 owner 推算。 |
| OI-07 | KR XML 的 SN、产品/数量/托盘关系及 Gateway 转换输出结构。 | Mock 可以先验证 Odoo 处理；真实 XML/Gateway 映射等待外部资料并在独立联调验收。 |
| OI-08 | `ginlong_product_form`、规格、Ginlong 重量/尺寸等已有 variant 字段迁移到 template 的实际策略，及原生 `weight` 与 Ginlong 重量字段的映射。 | 需保证历史值、报表、API06 重量和 WMS 读写兼容；不新增重复属性模型。 |
| OI-09 | 新模板身份/字段归属/产品一致性规则尚未纳入冻结 SRS v1.0、TDD v0.9 和 IMPLEMENTATION_PLAN v1.0 当前基线。 | 按项目工作流先完成人类批准的上游更新与计划影响评估，再冻结/实施 CC-GIN-005；不得把当前草案作为冻结基线。 |
| OI-10 | 出库预分配机制的业务规则和数据关系。 | 本 CC 排除；作为独立 CC 前置 TV/TDD，不得扩展至当前实现。 |

## 10. 项目负责人决策记录与 IHR 要求

**项目负责人最新决策（本次指令）：**一个 Ginlong `productCode` 对应一个 `product.template`；不同 `owner` 使用不同 `product.product` 变体。产品名称、规格、重量、尺寸、`productForm`、tracking 为模板共享属性；owner、内部组合编码、原始 productCode 为变体属性；同码产品固有属性跨 owner 一致。API07 productForm 只接受原材料/半成品/成品；冲突拒绝且不覆盖原模板。tracking 映射为原材料=`none`、半成品/成品=`serial`。KR 执行现场操作和 SN 扫描，Odoo 消费 KR 实绩并生成/完成 Picking；Gateway 仅处理 XML 安全解析和 JSON 转换。库存变体、量的 owner 与托盘内容归属须一致。CC-GIN-005 按第 8 节纳入/排除，预分配另行 TV/CC。此为本地业务规则，Ginlong V3.2 未正式确认 productForm 枚举。

本记录及本版字段归属/属性一致性/范围决策作为后续实施 IHR 的依据。实施时应在对应 CC 的新增 IHR 条目中引用本报告，写明“项目负责人本地决策 / Ginlong 正式确认未完成”，并保留后续 Ginlong 确认的单独证据；不回写或改写已关闭 CC-GIN-001–004 的历史 IHR。

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

**Human Review / Closure：李建强（项目负责人），2026-11-19，APPROVED，批准关闭 TV-GINLONG-PRODUCT-001。** TV v1.0 记录技术验证报告已关闭；OI-01–OI-10 按原文保留，尤其 OI-09 上游基线影响评估仍须在 CC-GIN-005 实施前完成并获批。模板同步继续 BLOCKED，沿用既有批准的流程例外，不伪记通过。

**代码修改：无。TDD/CC-GIN-005 修改：无。** 本次批准仅关闭 TV，不代表已修改或冻结 CC-GIN-005，也不授权编码。
