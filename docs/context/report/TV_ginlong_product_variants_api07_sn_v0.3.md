# Ginlong 多货主产品变体与 API07 productForm/SN 规则技术验证报告

| 项目 | 内容 |
| --- | --- |
| 文档编号 | TV-GINLONG-PRODUCT-001 |
| 项目 | `ginlong_apis` / `worlddepot` |
| 版本 | 0.3 |
| 状态 | Review Draft，等待 Human Review；未授权实施 |
| 验证日期 | 2026-11-19 |
| 技术环境 | Odoo 18 CE；现有 `venv`、`odoo.conf`、开发库 `odooce_karlrapp` |
| 总体结论 | 原生变体和库存隔离可行；产品模板级原生 tracking 不能区分变体，但已通过 Odoo ORM 验证由 Odoo 按 KR 实绩显式写入 stock.lot/stock.move.line.lot_id 的可行路径；Gateway/KR 集成及产品迁移仍待实施验证 |

## 修订记录

| 版本 | 状态 | 修订内容 |
| --- | --- | --- |
| 0.1 | Review Draft | 验证原生产品变体、API01/03/07/09 与暂定 `snTrackingRequired` 字段。 |
| 0.2 | Review Draft | 根据项目负责人 2026-11-19 决策，改由 API07 已有 `productForm` 决定 SN 要求；明确本地三种允许值及未知值拒绝；不新增 `snTrackingRequired`。 |
| 0.3 | Review Draft | 纠正 KR、Gateway、Odoo 的仓库作业职责；用 Odoo ORM 实测 `stock.picking` 在模板级 tracking 下的 SN 行为，并验证混合 productForm 变体通过显式 `stock.lot`/`lot_id` 记录 KR SN 的可行方案；补充 CC-GIN-005 承接建议。 |

## 1. 目的与边界

验证以 Odoo 原生 `product.template` 为基础档案、以 `product.product` 变体区分 Ginlong 货主的技术可行性；核对 API01/03/04/06/07/08/09 和现有 WMS 的实际字段与代码路径；核对 API07 `productForm` 与 KR 实际执行结果中 SN 的验证和库存记录路径。

系统职责及数据链为：Ginlong 下达指令 → Odoo 管理业务 Order 并转发作业指令 → Karl Rapp WMS 执行实际收货、上架、拣货、SN 扫描及发货并输出 XML → Gateway 接收 KR XML，进行安全解析及 XML→JSON 转换，不处理业务逻辑 → Odoo 接收 KR 实际作业结果，校验并创建/完成 `stock.picking`、`stock.move.line`，记录库存及 SN → Odoo 向 Ginlong 回传结果。Odoo 不执行 KR 现场作业，也不开发额外的 SN 扫描流程；SN 来源是 KR 作业结果。

本次只做源码检查及本地 Odoo ORM 技术验证。未修改 Python、XML、manifest 或业务数据；临时产品、属性、货主、Picking、Lot 及库存均通过 ORM 创建，并在 shell 事务结束前显式回滚。未访问真实 Ginlong、Karl Rapp 或 Gateway 环境，未执行 Gateway 集成测试；未使用 SQL、`stock_barcode` 或官方 Odoo 源码修改。

## 2. 结论摘要

1. **原生变体方案可行。** Odoo 按 `product.attribute` 的变体属性可以为一个 `product.template` 生成多个 `product.product`。试验中两个货主变体分别保存 `ginlong_owner_code`、`ginlong_unit`、`ginlong_weight`，并在同一内部库位形成不同产品的库存数量；查询没有跨产品合并。
2. **原生库存跟踪不是变体独立字段。** Odoo 的 `tracking` 实际定义在 `product.template`。试验中对一个变体写入 `tracking='serial'` 后，同模板下两个变体读到的值都变成 `serial`。本项目已决定用变体字段 `ginlong_product_form` 判定是否要求 SN；不能把它同步写入共享模板的 `tracking`。
3. **现有 API 使用原始 `productCode` 作为 `default_code`。** API01/03/API07 按 `default_code + ginlong_owner_code` 查找；API09 和 API04/06/08 回传代码也从 `default_code` 取值。改为组合内部编码后，必须在产品变体保存原始 Ginlong `productCode`，并调整这些查找与回传点。ORM 探针证明当前 API01/03 查找器无法用原始编码找到 `default_code` 已改为组合值的产品。
4. **API07 已有 `productForm` 持久化，但 API 规则未落地。** 现有 API07 已把 `productForm` 保存到变体字段 `ginlong_product_form`；临时 ORM 探针确认“原材料”“半成品”“成品”均可保存且可更新。当前 API07 仍接受其它非空值，三值白名单尚未实现。
5. **开发库不代表实际库存迁移状态。** 当前库有 13 个模板、13 个变体、8 个产品带货主码 `2110`，但找不到对应货主联系人；没有已登记变体属性、库存量或 move line，只有仓库 `KRWH / KarlRapp-WH`。临时 ORM 测试只能证明 Odoo 机制，不证明 KR 实际库存已同步。
6. **Odoo 标准 Picking 的 SN 行为已用 ORM 验证。** 模板设为 `tracking='serial'` 时，同模板的原材料变体也被要求提供序列号；设为 `tracking='none'` 时，仅写 `stock.move.line.lot_name` 文本不会建立 lot 关联。对 tracking 为 none 的模板，显式创建/查找标准 `stock.lot` 并把它写入 KR 实绩对应的 `stock.move.line.lot_id`，可完成 Picking，并将数量记在对应 lot 下。该测试证明 Odoo 记录路径可行，不代表 KR/Gateway 数据映射已完成。

**建议：** 后续实现复用 `ginlong_product_form`，在 Odoo 消费 Gateway 转换后的 KR 实绩时按变体形态校验 SN 是否存在；SN 从 KR 数据取得，并用标准 `stock.lot` 与 `stock.move.line.lot_id` 记录。不要将模板设为 serial 来替代逐变体规则，也不开发 Odoo 扫码/现场作业流程。V3.2 未列举 `productForm` 枚举，本地限定三种值属于项目负责人决策，不得描述成 Ginlong 已正式确认的枚举。

## 3. 方法与数据库基线

| 验证方法 | 实际结果 |
| --- | --- |
| 源码阅读 | 检查 Odoo 原生产品模板、变体、库存跟踪代码；`ginlong_apis` API 服务/扩展字段；`worlddepot` 产品查找、入库/出库模型与拣货流程。 |
| Ginlong 文档核对 | V3.2 API07 0709 字段为必填 `VARCHAR(40)` 且无枚举；请求示例含自由文本；物料信息表 8 行有 4 个“原材料”、4 个“成品”，未出现“半成品”。旧 `.xls` 只读转换到 `/private/tmp` 后扫描，未修改原文件。 |
| ORM 只读检查 | `ginlong_apis`、`worlddepot`、`product`、`stock` 均为 installed；`product.template` 13 条、`product.product` 13 条、`res.partner` 7 条、`stock.quant` 0 条、`stock.move.line` 0 条；仓库 1 个：`KRWH`。 |
| 产品数据检查 | 有 8 个产品带 `ginlong_owner_code='2110'`；没有 `res.partner.ginlong_owner_code='2110'` 的联系人；当前 13 个有内部编码的产品没有重复 `default_code`；13 个模板均没有属性行。上述均为查询当时开发库事实。 |
| 模板同步检查 | `check_template_sync.py --template technical-verification` 返回 `BLOCKED：找不到项目模板来源`；按已有项目流程例外记录，未将模板同步标为 PASS。 |
| 变体/库存 ORM 探针 | 临时建一个有两个货主属性值的模板和两个变体，分别写入货主码、Ginlong 单位和重量；通过 Odoo `stock.quant._update_available_quantity` 建立 12/7 数量并给其中一项预留 3，调用 API09，随后显式回滚。 |
| API07 ORM 探针 | 临时建测试货主、项目、API 用户，直接调用当前 `api07()` 服务创建/更新三种 `productForm`，并验证缺失/未列值行为；随后显式回滚。该探针验证的是现有实现，不是新增代码。 |
| 产品查找探针 | 临时产品的 `default_code` 使用组合码，调用现有 `_find_product()` 按 Ginlong 原始产品码及货主码查询，得到“未找到”；随后显式回滚。 |
| Picking / SN ORM 探针 | 在回滚事务中创建临时模板、原材料/半成品变体及入库 Picking，分别验证模板 tracking=serial 与 none、KR SN 对应 lot_name 文本及显式 `stock.lot`/`lot_id` 写入，调用标准 `button_validate()`，并检查 move line、quant 的 lot 归属；所有记录均显式回滚。 |

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

### TV-003 — KR SN 实绩写入 Odoo Picking 的可行性及模板 tracking 影响

**Question**  同一模板下原材料与半成品/成品 owner 变体能否按 `ginlong_product_form` 使用 Odoo 原生库存模型记录 KR 返回的 SN，而不要求 Odoo 执行 SN 扫描？

**Method** 检查 `product.template.tracking`、`stock.picking.button_validate()` 对跟踪产品的校验，以及 `stock.move.line` 的 `lot_id`/`lot_name` 处理；在 Odoo ORM 回滚事务中创建同模板原材料和半成品变体，运行标准入库 Picking 验证。KR SN 作为测试作业结果输入，不模拟 Odoo 扫码操作。

**Result** 逐变体原生 tracking 不可行；KR 实绩按标准 Lot/SN 模型入账可行（有条件）。

- `tracking='serial'` 是模板级共享字段。通过一个变体写 serial 后，同一模板的原材料和半成品变体都读到 serial；入库 Picking 中原材料行没有 SN 时，标准 `button_validate()` 因跟踪产品缺少 Lot/Serial Number 而阻止完成。若两条变体行都提供 SN，标准 Picking 可完成并在 move line 保存 lot 关联。
- `tracking='none'` 时，仅给实际执行 move line 写入 `lot_name` 字符串，Picking 可以完成但 `lot_id` 仍为空，Lot 未形成结构化关联。
- `tracking='none'` 时，按 KR 返回 SN 通过 ORM 创建标准 `stock.lot`，并将 `lot_id` 写入半成品 move line；原材料行不提供 Lot。标准 Picking 可完成，原材料 quant 无 lot、半成品 quant 关联到对应 Lot。该路径使用 Odoo 原生库存记录，不新增平行库存/SN 模型。

**Evidence** `addons/stock/models/product.py:721-726` 定义模板级 `tracking`；`addons/stock/models/stock_picking.py:1340-1385` 对 tracked move line 检查 Lot/Serial Number；`addons/stock/models/stock_move_line.py:47-50, 596-663, 719-729` 定义 Lot 字段并在过账时把 move line 的 lot 写入量记账。`worlddepot/models/my_product_template.py:57-69` 现有导入也将 LOT/SN 设置在模板级 tracking。上述结果为本地 Odoo ORM 标准 Picking 探针，全部回滚。

**TDD / CC Impact** API07 以已有变体字段 `ginlong_product_form` 作为规则来源。Odoo 消费 Gateway JSON 时校验：原材料可以无 SN；半成品、成品必须在 KR 实绩中包含 SN。再从实绩将 SN 映射到标准 `stock.lot` 和 `stock.move.line.lot_id`。如果一个模板内有需要 SN 和不需要 SN 的不同变体，不能将模板 tracking 设为 serial；采用 tracking none 加导入时的形态检查和显式 lot 关联。tracking none 下由导入流程负责所需 SN 的存在性检查，不能依赖 Odoo serial tracking 自动拦截。此项不创建现场扫描流程、不新增 SN 模型，也不据此增加未经确认的 SN 唯一性业务规则。Gateway XML→JSON 与 KR 真实数据尚未联调，需在 CC-GIN-005 通过 Mock 归一化结果验证。

### TV-004 — 组合内部编码对现有 Ginlong/WMS 查找的影响

**Question**  把 `default_code` 变为 owner 与产品码的无歧义组合后，现有 API 和 WMS 是否仍按原始产品码工作？

**Method** 检查 API01/03/07/09、Hoymiles 通用产品查找和回传 Payload 的代码；ORM 临时建立 `default_code` 为组合值的产品，以原始产品码调用 `_find_product()`。

**Result — NOT VERIFIED（现状与新编码兼容）；必须改造查找与对外编码路径。** `_find_product()` 当前以 `default_code=productCode AND ginlong_owner_code=owner` 查询；组合码不等于 Ginlong 原始 `productCode`，实际探针报产品不存在。API07 当前也以原始 `default_code` 定位并把它写回 `default_code`。API09 与 API04/06/08 回传也使用 `default_code`，会将内部组合值发给 Ginlong。`worlddepot/controllers/hoymiles/product_lookup.py` 也先按 `default_code` 查找，复用产品的跨系统调用需回归。

**Evidence** `mymodules/ginlong_apis/services.py:120-136, 435-485, 488-540`；`mymodules/ginlong_apis/models/ginlong_callbacks.py:53-84`；`mymodules/worlddepot/controllers/hoymiles/product_lookup.py:17-44`。开发库的 `product.product.default_code` 原生字段仅有索引，没有 SQL 唯一约束；当前 `product.product._sql_constraints` 为空。

**TDD Impact** 在 `product.product` 保留 `ginlong_product_code` 原始码以及 owner 标识；`default_code` 使用可逆、无歧义的组合码。API01/03/07 以 `(owner, ginlong_product_code)` 定位；API09 与 Ginlong 回传使用原始码；既有其他 WMS API 的 raw-code/barcode 查找要保持兼容或有明确迁移测试。组合编码格式、分隔/转义和唯一约束应在 TDD 冻结前定案。

### TV-005 — API07 `productForm` 持久化与 SN 分类

**Question**  现有 API07 是否把 `productForm` 保存在 owner 变体，且能否按项目规则确定 SN 要求？

**Method** 核对 V3.2 API07 0709、物料表样例、`ginlong_product_form` 字段及 API07 ORM 服务；临时调用服务创建三种类别、更新类别，并尝试缺失和未列值。

**Result — VERIFIED（字段存储及 Odoo 标准 Picking/Lot 机制） / NOT VERIFIED（API07 白名单及 KR 实绩导入校验）** 现有服务将三种类别精确保存到 `product.product.ginlong_product_form`，更新有效；缺少 `productForm` 会拒绝。V3.2 字段为必填 `VARCHAR(40)` 且没有枚举，物料样表仅包含“原材料”“成品”。本地项目负责人现已将允许值定为“原材料”“半成品”“成品”，并授权拒绝其它值；当前代码会接受并保存未知形态，白名单未实现。TV-003 已通过标准 Picking 验证模板跟踪及 Lot 关联机制，但当前业务代码尚未依据变体形态校验 KR 实绩 SN，也未把 Gateway 数据映射到实际 move line。

**Evidence** V3.2 工作簿 API07 字段 0709 和请求示例；`docs/ginlong_apis/物料信息.xls`；`mymodules/ginlong_apis/models/wms_extensions.py` 的 `ginlong_product_form`；`mymodules/ginlong_apis/services.py:435-485`。ORM 实测三种值创建、更新、缺失字段拒绝、未列值接受；临时记录均回滚。

**TDD Impact** 不新增 `snTrackingRequired`。API07 必须增加三值白名单；Odoo 消费 KR 实际结果时按 `ginlong_product_form` 校验 SN 是否存在，并将 KR SN 写入标准 Lot/move line。V3.2 的 String/VARCHAR(40) 没有公布枚举；三值白名单和 SN 映射是本地负责人决策，不应写成 Ginlong 的正式枚举确认。

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
| API07 | 按 `(owner, productCode)` 更新/创建 owner 产品变体；货主不存在按已批准规则创建/复用 Contact。`productForm` 仅允许“原材料”“半成品”“成品”，其它值拒绝。 | 当前 API07 将产品形态存到 `ginlong_product_form`，但按 raw `default_code` 定位、未建立原生 owner 变体结构，也未校验三值白名单；`productName`、UoM 写在共享模板，可能覆盖其它 owner 数据。 |
| API08 | 从 KR 实际发货结果对应的 Order 状态及 `stock.picking`、`stock.move.line` 回传发货完成；SN 读取 KR 实绩关联的 Lot。 | 回传产品编码当前取 `product_id.default_code`，组合内部编码实施后要输出原始 Ginlong `productCode`。不在本 TV 推断发货确认状态或新增现场操作流程。 |
| API09 | 只读查询 Odoo 已有的物理库存，按 `owner + warehouse + productCode` 隔离，返回原始 Ginlong 产品编码，不扣预留量。 | 当前按 `res.partner.ginlong_owner_code`、`stock.warehouse.code`、`stock.quant.owner_id` 查询并汇总 `quantity`，临时 ORM 结果不扣 reserved quantity；需增加变体 owner/raw productCode 条件。当前开发库没有库存数据或双仓样本，未验证真实 KR 同步数据。 |

**跨接口影响：**当前 API04/06/08 回传及 API09 响应读取 `product_id.default_code`。若实施组合内部编码，相关 Ginlong 请求匹配和响应字段均需使用单独保存的原始 `ginlong_product_code`，并回归其他仍按 `default_code` 查询的 WMS 路径。KR 现场作业完成后，Gateway 仅做安全解析及 XML→JSON 转换；业务字段到 Odoo 订单/Picking/move line 的映射由 Odoo 侧完成。

## 6. API07 `productForm` 取值与 SN 规则

### 6.1 字段契约及项目规则

| 项目 | 依据 / 当前规则 |
| --- | --- |
| Ginlong V3.2 字段 | `productForm` 必填，类型 `VARCHAR(40)`；V3.2 未列举枚举，示例值为 `Three-phase Asynchronous Motor`。 |
| 物料表样例 | 8 条样例中 4 条为“原材料”、4 条为“成品”；样例没有“半成品”。 |
| 项目允许值 | “原材料”“半成品”“成品”；其它值拒绝。该三值范围是项目负责人决策，不表示 Ginlong 已确认枚举。 |
| SN 规则 | KR 实际结果中，“原材料”无需 SN；“半成品”“成品”必须带 SN。 |
| SN 数据来源 | Karl Rapp WMS 现场扫描并写入 KR 作业结果/XML；Odoo 不扫描、不要求重复录入，负责校验结果并记录。 |
| Odoo 存储 | 复用 `product.product.ginlong_product_form`；按需使用标准 `stock.lot` 与 `stock.move.line.lot_id`；不新增 `snTrackingRequired` 或平行 SN 模型。 |

### 6.2 验证结果与测试矩阵

现有 API07 必填列表包含 `productForm`，并保存到 `ginlong_product_form`。ORM 探针验证三种本地允许值可创建/更新；缺字段当前会拒绝；当前 API07 没有白名单，未知非空值仍被接受。TV-003 已验证 Odoo 标准 Picking 的模板 tracking 行为及 explicit `stock.lot`/`lot_id` 入账方式。业务代码尚未把 KR/Gateway 实绩映射到 Odoo，也未按变体 productForm 执行 SN 检查。

| 场景 | 项目要求 | 当前验证结果 |
| --- | --- | --- |
| API07 Add：原材料 | 保存形态；KR 实绩允许无 SN | 字段保存 **VERIFIED**；API07 三值白名单 **NOT IMPLEMENTED** |
| API07 Add：半成品 | 保存形态；KR 实绩必须有 SN | 字段保存 **VERIFIED**；Odoo 标准 Lot/`lot_id` Picking 路径 **VERIFIED**；实绩导入校验 **NOT IMPLEMENTED** |
| API07 Add：成品 | 保存形态；KR 实绩必须有 SN | 字段保存 **VERIFIED**；Odoo 标准 Lot/`lot_id` Picking 路径 **VERIFIED**；实绩导入校验 **NOT IMPLEMENTED** |
| API07 Edit：三种值互相更新 | 同一变体更新 `productForm` | ORM 字段更新 **VERIFIED**；更新后结果导入行为 **NOT IMPLEMENTED** |
| API07 缺少 productForm | 拒绝请求 | 当前服务返回缺少字段错误 **VERIFIED** |
| API07 productForm 为其它值 | 拒绝且不创建/更新产品 | 项目负责人已决定；当前代码接受并保存未知值，白名单**未实现** |
| 同模板原材料 + 半成品 | 原材料无 SN，半成品带 KR SN，均可由 Odoo 记录实际库存结果 | 模板 `tracking=serial` 时原材料被阻止；`tracking=none` + 半成品显式 lot 关联时 Picking 完成 **VERIFIED**；KR/Gateway 实绩导入 **NOT VERIFIED** |

**实施建议** API07 在写入前按项目决策只接受以上三种精确值。KR 完成现场作业并输出 XML 后，Gateway 转换格式；Odoo 按产品变体 `ginlong_product_form` 检查实绩 SN 必填性，再把 KR SN 关联到 Odoo 原生 `stock.lot` 和对应 `stock.move.line.lot_id`。这不是在 Odoo 建立现场 SN 采集流程。由于 `product.template.tracking` 对同模板所有变体共享，不能按 productForm 将它设成 serial 来要求半成品/成品 SN；混合形态下使用 tracking none 并由 Odoo 实绩导入校验负责检查 SN 是否存在。

## 7. 数据迁移与兼容性风险

1. **默认编码迁移。** 现有 Ginlong 产品把原始 `productCode` 存在 `default_code`；新方案要保存原始码并把内部码改成无歧义组合。必须先生成旧 `default_code`、owner code、新原始码、新组合码的迁移清单；核对碰撞、长度及已有引用。Odoo 原生产品未提供 default_code 全局唯一 SQL 约束，不能仅凭默认编码假设唯一。
2. **模板合并/变体重构。** 当前 API07 对同一 raw productCode 的不同 owner 建不同模板/单变体；新方案要求同一基础产品模板下形成不同 owner 变体。合并模板可能影响模板级名称、分类、UoM、tracking、销售/采购属性、供应商、历史单据关联及库存估值。开发库当前没有重复编码、属性行或库存，不能代表目标环境安全迁移。
3. **共享字段覆盖。** Odoo `name`、`uom_id` 和 `tracking` 是模板级；现有 API07 把 `productName` 和 UoM 写入模板。同一模板多个 owner 的值若不同，会互相覆盖。Ginlong 名称是否允许按 owner 不同，Odoo 库存基础单位是否必须一致，需要确定；Ginlong `unit` 文本字段可独立存储，但不能因此推断 Odoo 库存单位也可逐变体不同。
4. **库存 owner 与产品 owner 是两个关系。** 变体 `ginlong_owner_code` 和 `stock.quant.owner_id` 分别标记产品归属与库存所有者。现有 Picking 路径会从 Order、pallet 或 quant 取得 owner。迁移/回归须验证二者一致，避免 API09 查询漏库存或跨货主泄漏。
5. **其他 WMS 调用。** `product_lookup.py`、订单查询/报表及 Ginlong 回传目前读取 `default_code`。修改内部编码需一并处理原始码查询和展示，不可将组合码暴露给旧 API 或 Ginlong。
6. **SN 规则落地。** `ginlong_product_form` 已是变体字段；API07 白名单、Odoo 消费 KR/Gateway 实绩时的 SN 存在性检查及 Lot 关联尚未实现。ORM 已验证标准 Picking 可通过显式 `stock.lot`/`lot_id` 记录 KR SN；这项实现属于实际结果数据映射和校验，不是 Odoo 现场仓库作业。tracking 设为 serial 会同时要求原材料变体有 SN；混合形态下采用 tracking none 时，所需 SN 检查由 Odoo 实绩导入执行，不能依赖原生 serial 门禁。
7. **开发库基线有限。** 当前 8 个 Ginlong 产品 owner code 均为 `2110`，但没有匹配联系人；库存、move line 为空。API01/API07 的 owner Contact 创建/关联和真实库存流转需在实施测试数据库中覆盖，不能从当前产品快照推定已完成。
8. **模板 tracking 与现有 WMS 行为。** tracking none + Odoo 侧 productForm 检查及显式 lot 关联的验证范围是标准 Odoo 入库 Picking ORM 探针，不覆盖 `worlddepot` 完整订单、分配和出库流程。现有 WMS 有读取产品 tracking 的路径；实施前须回归这些路径，确认无需现场扫描的 KR 结果导入不会破坏现有业务。

## 8. 最小技术方案建议（供 Human Review）

1. 复用原生 `product.template` / `product.product`。新增或调整字段只用于保留原始 `ginlong_product_code`、owner 及确有必要的 owner 级物料属性；不新建货主产品映射模型。API07 的货主创建/复用沿用已批准规则。
2. 每个 `(owner, ginlong_product_code)` 定位一个产品变体；内部 `default_code` 的组合格式、迁移策略及唯一性实现需在实施方案中确定。API01/03/07 查找以及 API04/06/08/09 输出必须区分内部码和 Ginlong 原始产品码。
3. 先列明 Ginlong 属性映射到模板/变体的边界。Odoo `name`、`uom_id`、`tracking` 为模板共享字段；Ginlong unit 文本和产品形态等应保存在适当的变体字段，不以模板字段代表 owner 间不同值。
4. API01 保持已批准的货主创建/复用及产品组合校验；API03 保持缺货主/缺产品组合时拒绝，不自动创建；API07 按 `(owner, productCode)` upsert 并执行三值 `productForm` 白名单；API09 只读按 owner、warehouse、原始产品码筛选已有 `stock.quant.quantity`，不扣预留、不写库存。
5. KR 在现场采集 SN 并通过 XML 返回实际作业结果；Gateway 只负责安全解析及 XML→JSON 转换。Odoo 消费转换后的结果、按 `ginlong_product_form` 校验 SN（原材料可缺省，半成品/成品必填），并在生成/完成 Picking 时将 KR SN 写入标准 `stock.lot`、关联 `stock.move.line.lot_id`。禁止将原生 `tracking='serial'` 当作逐变体规则；同模板有不同 productForm 时，TV 验证的最小路径为 tracking none 加 Odoo 侧形态检查和显式 lot 关联，不增加 SN 唯一性等额外业务规则。
6. CC-GIN-005 应承接 API01/03/07/09 多货主变体和原始产品码回归；API04/06/08 读取由 KR 结果生成的 Picking/move line；API07 白名单；Odoo 导入层 productForm/SN 完整性检查及标准 lot 关联；五接口业务回传相关原有 E2E；API09 库存隔离和只读测试。测试使用清晰标识的 Mock Gateway 转换结果及模拟 KR 作业数据，不宣称 Gateway 或 KR 集成已通过。
7. 迁移按 `(旧 owner code, 旧 default_code)` 建只读对照清单；检查冲突后在测试环境验证产品/属性/单据/库存引用迁移和回滚。批准前不合并模板或改写业务数据。

## 9. Open Items

| # | 待确认内容 | 影响 |
| --- | --- | --- |
| OI-01 | Ginlong 是否正式确认 `productForm` 只会发送“原材料”“半成品”“成品”？V3.2 未列枚举，且示例值为 `Three-phase Asynchronous Motor`；本地已决定拒绝其它值。 | 若真实报文使用该 V3.2 示例或其它未列值，API07 会拒绝。此为外部兼容风险，不阻塞按本地决策进行实现。 |
| OI-02 | 不同 owner 的同一 `productCode` 是否允许有不同 `productName`、productForm 或 Ginlong unit？ | 决定模板与变体字段边界；模板共享的 name/UoM/tracking 不能表达所有 owner 差异。 |
| OI-03 | 内部 `default_code` 组合的规范编码格式、可逆规则和最大值策略。 | 避免简单拼接碰撞，决定迁移及其他 WMS 调用改造。 |
| OI-04 | Ginlong 产品 owner 是否仅由现有 `ginlong_owner_code` 字符串关联，还是要求 `product.product` 直接 Many2one 到 `res.partner`？ | 数据完整性、联系人改码及 API09 过滤方式。 |
| OI-05 | API09 的货主隔离是否要求同时验证 variant owner code 与 `stock.quant.owner_id`；对于没有 `owner_id` 的产品库存如何处理？ | 避免漏库存及货主串货；现有 WMS Order owner 到 stock owner 的映射需集成验证。 |
| OI-06 | 目标数据库中 owner/code 重复模板、历史订单、Picking/库存和估值的真实迁移基线。 | 迁移安全；当前开发库无库存及 owner 重复样例，无法验证。 |
| OI-07 | KR XML 中 SN 字段及其与订单行/产品/实际数量的关联方式是什么？本地未取得 KR XML 样例或 Gateway 转换契约。 | 阻塞真实数据映射；CC-GIN-005 可先以 Mock 转换结果验证 Odoo 的形态检查及 Lot 关联，真实 XML 字段映射留待 Gateway/KR 资料具备后确认。Odoo 标准 Picking 技术路径已在 TV-003 验证。 |
| OI-08 | 是否接受同模板混合 productForm 时使用模板 `tracking=none`，由 Odoo 导入层按产品形态检查 SN 并显式关联标准 Lot？ | 标准入库 Picking ORM 路径已验证；但 tracking none 不触发 Odoo 原生 serial 必填校验。CC-GIN-005 需回归 `worlddepot` 订单、分配和出库路径，并由评审确认该路径满足项目需要。 |

## 10. 项目负责人决策记录与 IHR 要求

**2026-11-19 项目负责人决策（本次任务指令）：**API07 `productForm` 本地只接受“原材料”“半成品”“成品”；KR 实际作业结果中，原材料无需 SN，半成品和成品必须提供 SN，其它形态拒绝。复用现有变体字段 `ginlong_product_form`，不新增 `snTrackingRequired`。KR 负责实际仓库作业及 SN 扫描并输出 XML；Gateway 安全解析并转换 XML→JSON，不处理业务逻辑；Odoo 接收作业结果、验证并生成/完成 `stock.picking`，记录库存和 SN。Odoo 不负责现场作业、不增加 SN 扫描流程。这是本地业务规则；V3.2 未定义枚举，Ginlong 未正式确认这组三值枚举。

本记录作为后续实施 IHR 的决策来源。实施时应在对应 CC 的新增 IHR 条目中引用本报告，写明“项目负责人本地决策 / Ginlong 正式确认未完成”，并保留后续 Ginlong 确认的单独证据；不回写或改写已关闭 CC-GIN-001–004 的历史 IHR。

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

**代码修改：无。业务实现授权：无。** 本报告提交 Human Review 后，待批准再将实施内容纳入 CC-GIN-005；本报告不修改 CC-GIN-005、TDD 或任何已冻结基线。
