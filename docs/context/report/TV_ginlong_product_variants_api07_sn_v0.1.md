# Ginlong 多货主产品变体与 API07 SN 字段技术验证报告

| 项目 | 内容 |
| --- | --- |
| 文档编号 | TV-GINLONG-PRODUCT-001 |
| 项目 | `ginlong_apis` / `worlddepot` |
| 版本 | 0.1 |
| 状态 | Review Draft，等待 Human Review；未授权实施 |
| 验证日期 | 2026-11-19 |
| 技术环境 | Odoo 18 CE；现有 `venv`、`odoo.conf`、开发库 `odooce_karlrapp` |
| 总体结论 | 原生变体和库存隔离可行；现有 Ginlong API/WMS 查找路径与目标内部编码不兼容，SN 字段未实现，需先确认数据范围与迁移方案 |

## 1. 目的与边界

验证以 Odoo 原生 `product.template` 为基础档案、以 `product.product` 变体区分 Ginlong 货主的技术可行性；核对 API01/03/07/09 和现有 WMS 的实际字段与代码路径；验证暂定 `snTrackingRequired` 字段在当前 API07 中的行为。

本次只做源码检查及本地 Odoo ORM 技术验证。未修改 Python、XML、manifest 或业务数据；临时产品、属性、货主及库存均通过 ORM 创建，并在 shell 事务结束前显式回滚。未访问真实 Ginlong 或 Karl Rapp 环境，未使用 SQL、`stock_barcode` 或官方 Odoo 源码修改。

## 2. 结论摘要

1. **原生变体方案可行。** Odoo 按 `product.attribute` 的变体属性可以为一个 `product.template` 生成多个 `product.product`。试验中两个货主变体分别保存 `ginlong_owner_code`、`ginlong_unit`、`ginlong_weight`，并在同一内部库位形成不同产品的库存数量；查询没有跨产品合并。
2. **库存跟踪不是变体独立字段。** Odoo 的 `tracking` 实际定义在 `product.template`。试验中对一个变体写入 `tracking='serial'` 后，同模板下两个变体读到的值都变成 `serial`。因此若两个货主变体允许不同的 SN 要求，不能直接把 `snTrackingRequired` 当作原生 `tracking` 的逐变体值。
3. **现有 API 使用原始 `productCode` 作为 `default_code`。** API01/03/API07 按 `default_code + ginlong_owner_code` 查找；API09 和 API04/06/08 回传代码也从 `default_code` 取值。改为组合内部编码后，必须在产品变体保存原始 Ginlong `productCode`，并调整这些查找与回传点。ORM 探针证明当前 API01/03 查找器无法用原始编码找到 `default_code` 已改为组合值的产品。
4. **API07 当前没有 SN 字段能力。** `product.product` 不含 `snTrackingRequired` 对应字段。实际调用现有 API07 服务时，创建分别携带 `Y`、`N`、缺失、非法值，以及更新 `Y→N`、`N→Y` 和缺失均被接受，但标记都没有持久化；非法值也未被拒绝。这不是符合暂定契约的通过结果。
5. **开发库不代表实际库存迁移状态。** 当前库有 13 个模板、13 个变体、8 个产品带货主码 `2110`，但找不到对应货主联系人；没有已登记变体属性、库存量或 move line，只有仓库 `KRWH / KarlRapp-WH`。临时 ORM 测试只能证明 Odoo 机制，不证明 KR 实际库存已同步。

**建议：** 可以基于该 TV 起草最小实现方案，但实施前须评审模板共享属性、SN 与原生跟踪的边界，以及已有产品数据如何迁移。不得把本地暂定 SN 字段描述为 Ginlong 已确认契约。

## 3. 方法与数据库基线

| 验证方法 | 实际结果 |
| --- | --- |
| 源码阅读 | 检查 Odoo 原生产品模板、变体、库存跟踪代码；`ginlong_apis` API 服务/扩展字段；`worlddepot` 产品查找、入库/出库模型与拣货流程。 |
| ORM 只读检查 | `ginlong_apis`、`worlddepot`、`product`、`stock` 均为 installed；`product.template` 13 条、`product.product` 13 条、`res.partner` 7 条、`stock.quant` 0 条、`stock.move.line` 0 条；仓库 1 个：`KRWH`。 |
| 产品数据检查 | 有 8 个产品带 `ginlong_owner_code='2110'`；没有 `res.partner.ginlong_owner_code='2110'` 的联系人；当前 13 个有内部编码的产品没有重复 `default_code`；13 个模板均没有属性行。上述均为查询当时开发库事实。 |
| 模板同步检查 | `check_template_sync.py --template technical-verification` 返回 `BLOCKED：找不到项目模板来源`；按已有项目流程例外记录，未将模板同步标为 PASS。 |
| 变体/库存 ORM 探针 | 临时建一个有两个货主属性值的模板和两个变体，分别写入货主码、Ginlong 单位和重量；通过 Odoo `stock.quant._update_available_quantity` 建立 12/7 数量并给其中一项预留 3，调用 API09，随后显式回滚。 |
| API07 ORM 探针 | 临时建测试货主、项目、API 用户，直接调用当前 `api07()` 服务执行创建和更新，传入 SN 各种情况；随后显式回滚。该探针验证的是现有实现，不是新增代码。 |
| 产品查找探针 | 临时产品的 `default_code` 使用组合码，调用现有 `_find_product()` 按 Ginlong 原始产品码及货主码查询，得到“未找到”；随后显式回滚。 |

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

### TV-003 — Odoo 原生 SN 跟踪是否能逐变体设置

**Question**  同一模板的 owner 变体是否能分别设为 SN 跟踪与不跟踪？

**Method** 检查 `addons/stock/models/product.py` 的 `tracking` 定义，并通过 ORM 对一个变体写入 `tracking='serial'`，读取同模板另一变体。

**Result — NOT VERIFIED（逐变体独立的假设不成立）** Odoo 原生 `tracking` 定义在 `product.template`；写一个 `product.product` 的委派字段后，同模板两个变体都读回 `serial`。原生字段无法表达同模板 owner A=`Y`、owner B=`N`。

**Evidence** `addons/stock/models/product.py:721-726` 定义模板级 `tracking`；ORM 探针写入一个变体后两个变体均读到 `serial`。`worlddepot/models/my_product_template.py:57-69` 的导入流程也将 LOT/SN 设置到 `product.template.tracking`。

**TDD Impact** `snTrackingRequired` 可以作为 `product.product` 上的 Ginlong 独立字符串字段；但若 `Y/N` 必须控制 WMS 每个变体的现场 SN 采集，不能仅写原生 `tracking`。实施方案需要在“Ginlong 标识仅作外部属性”与“为逐变体要求增加最小 WMS SN 检查”之间明确边界；不得将所有者变体的字段静默映射到共享模板级跟踪。

### TV-004 — 组合内部编码对现有 Ginlong/WMS 查找的影响

**Question**  把 `default_code` 变为 owner 与产品码的无歧义组合后，现有 API 和 WMS 是否仍按原始产品码工作？

**Method** 检查 API01/03/07/09、Hoymiles 通用产品查找和回传 Payload 的代码；ORM 临时建立 `default_code` 为组合值的产品，以原始产品码调用 `_find_product()`。

**Result — NOT VERIFIED（现状与新编码兼容）；必须改造查找与对外编码路径。** `_find_product()` 当前以 `default_code=productCode AND ginlong_owner_code=owner` 查询；组合码不等于 Ginlong 原始 `productCode`，实际探针报产品不存在。API07 当前也以原始 `default_code` 定位并把它写回 `default_code`。API09 与 API04/06/08 回传也使用 `default_code`，会将内部组合值发给 Ginlong。`worlddepot/controllers/hoymiles/product_lookup.py` 也先按 `default_code` 查找，复用产品的跨系统调用需回归。

**Evidence** `mymodules/ginlong_apis/services.py:120-136, 435-485, 488-540`；`mymodules/ginlong_apis/models/ginlong_callbacks.py:53-84`；`mymodules/worlddepot/controllers/hoymiles/product_lookup.py:17-44`。开发库的 `product.product.default_code` 原生字段仅有索引，没有 SQL 唯一约束；当前 `product.product._sql_constraints` 为空。

**TDD Impact** 在 `product.product` 保留 `ginlong_product_code` 原始码以及 owner 标识；`default_code` 使用可逆、无歧义的组合码。API01/03/07 以 `(owner, ginlong_product_code)` 定位；API09 与 Ginlong 回传使用原始码；既有其他 WMS API 的 raw-code/barcode 查找要保持兼容或有明确迁移测试。组合编码格式、分隔/转义和唯一约束应在 TDD 冻结前定案。

### TV-005 — API07 SN 字段现状

**Question**  现有 API07 能否创建/更新变体 SN 标记，并验证 `Y/N/缺失/非法值`？

**Method** ORM 检查 `product.product` 字段；调用现有 `api07()` 分别创建传 `snTrackingRequired=Y`、`N`、缺失及 `X` 的产品；再验证已有产品更新 `Y→N`、`N→Y` 及字段缺失。

**Result — NOT VERIFIED（目标能力不存在）** 当前字段注册表没有 `sn_tracking_required` / Ginlong SN 字段；API07 所需字段列表没有 `snTrackingRequired`，其余未知键未被使用。探针中 `Y`、`N`、缺失、`X` 的创建及 `Y→N`、`N→Y`、缺失更新均返回成功，但没有持久化标记；`X` 也没有被拒绝。不能将此结果认定为新字段测试通过。

**Evidence** `mymodules/ginlong_apis/models/wms_extensions.py` 中 `ProductProduct` 当前字段列表没有 SN 字段；`mymodules/ginlong_apis/services.py:435-485` 展示当前字段列表、创建/更新流程及保存字段。实际探针在事务中调用服务后已回滚。

**TDD Impact** 按暂定本地契约增加变体级、可空、无默认值的字段，外部传输仍为 String。只接受精确 `Y` / `N`；非法值必须在写入业务记录前报错。缺失不自动成为 `N`。创建缺失时是拒绝还是保持未设置、更新缺失时是拒绝还是保留原值，需在 TDD/契约复核中明确。

### TV-006 — 原生 WMS 关系兼容性

**Question**  原生变体能否作为现有 WMS 订单和库存移动的产品引用？

**Method** 检查已注册 ORM 关系及订单/库存代码。

**Result — VERIFIED（模型引用层）；PARTIAL（业务流程层）** 入库产品托盘、出库产品、`stock.move`、`stock.move.line` 的 `product_id` 均指向 `product.product`，原生变体可被现有订单和库存模型引用。当前开发库没有 stock moves/quants；未执行完整入库、出库、分配及过账流程，故未声称 WMS E2E 已通过。实际 owner 分配和 SN 捕获依赖也需按目标字段/流程回归。

**Evidence** ORM 字段元数据显示上述 `product_id` 均关联 `product.product`；入库拣货代码 `mymodules/worlddepot/models/inbound_order_create_piking.py:35-43` 把 `record.owner` 写入 picking owner；出库拣货从托盘/库存 quant 获取 owner，并写入 move line。现有出库分配路径会使用 `product_id.tracking` 和库存产品/owner 数据。

**TDD Impact** 复用原生产品和库存移动模型，不新增库存台账。需在实现阶段分别验证 owner A/B 变体的订单行、Picking、Lot/SN、stock quant 归属与 API09 输出链路。

## 5. API01/03/07/09 改造影响分析

| API | 目标处理 | 当前实现与必要影响 |
| --- | --- | --- |
| API01 | 读取 owner；货主不存在则创建/复用 Contact；按 `(owner, productCode)` 找到已存在的 owner 变体；不存在则拒绝产品行。 | 已创建/复用 Ginlong owner Contact，并将 `ginlong_owner_id` 关联到入库 Order；产品通过 raw `default_code + ginlong_owner_code` 查找。需改为原始产品码字段匹配并把正确变体关联到三层入库明细。另核实 base `record.owner` 与 Ginlong owner 是否一致，因为原生拣货将 `record.owner` 作为 stock owner。不能因订单接收产生实际库存变化。 |
| API03 | 货主及每一条产品组合必须存在；无效 owner/组合拒绝整张单，不自动创建产品或货主。 | 现有实现已校验 owner，并对每条明细按 `default_code + ginlong_owner_code` 查产品。改造查询键后保留事务完整性；当前 header owner 及行产品要继续落到正确变体。仓库分配时 `owner_id` 来自现存 pallet/quant，需确认与订单 owner 一致。 |
| API07 | 按 `(owner, productCode)` 更新或创建 `product.product` owner 变体；owner Contact 不存在则创建；各 owner 物料资料独立。 | 当前只给产品写 owner code，未调用 owner 创建/解析 helper；以 raw `default_code` 查找；未建 variant attribute；创建一个模板/一个产品；`productName`、UoM 写在共享模板，可能覆盖其他 owner；没有 raw code 独立字段，也没有 SN 字段。需将 owner 变体 upsert 到同一 base template，并把 owner 特有资料存于 variant。 |
| API09 | 按 owner 编码、warehouse 编码、原始 productCode 查询完整物理在手量，跨货主隔离，不扣预留。 | 当前 owner 匹配 `res.partner.ginlong_owner_code`、warehouse 匹配 `stock.warehouse.code`，按 `stock.quant.owner_id` 和仓库内部 location 汇总 `quantity`，这在临时 ORM 样本中不扣预留且分货主返回。需要增加变体 owner/raw productCode 范围并以原始字段返回，不可返回组合内部 `default_code`。现有开发库没有库存数据，也没有两个仓库，未验证真实同步数据或多仓库分区。 |

Ginlong 回传 API04/06/08 也在 Payload 中读取 `product_id.default_code`（如 `ginlong_callbacks.py` API04），切换内部编码时应一并使用原始 `ginlong_product_code`，避免外部回传内部组合码。

## 6. API07 `snTrackingRequired` 暂定契约与测试矩阵

### 6.1 暂定契约

| 项目 | 暂定值 |
| --- | --- |
| 外部字段 | `snTrackingRequired` |
| 外部类型 | JSON String |
| 可接受值 | `Y`、`N` |
| 含义 | `Y`：必须采集 SN；`N`：不要求采集 SN |
| Odoo 存储位置 | `product.product` owner 变体 |
| 默认 | 不提供默认 `N`；缺失不等同 `N` |
| 当前状态 | Ginlong 尚未正式确认字段及协议变更；仅按项目负责人本地暂定契约进行评估 |

建议本地字段可空且不设默认值，外部仍按字符串交换。缺失创建/缺失更新如何处理不能从现有代码或资料推断，待契约决定：拒绝缺失，或允许未设置/保留原值；无论哪种均不得自动写 `N`。非法值 `X` 按暂定 `Y/N` 枚举应拒绝且不产生部分更新。

### 6.2 测试矩阵

| 场景 | 目标预期 | 当前 API07 探针 |
| --- | --- | --- |
| Add + `Y` | 创建 owner 变体并持久化 `Y` | **当前缺陷**：请求成功但字段被忽略 |
| Add + `N` | 创建 owner 变体并持久化 `N` | **当前缺陷**：请求成功但字段被忽略 |
| Add 缺失字段 | 不自动存 `N`；拒绝或保持空值按待定契约 | 当前请求成功，但无字段可持久化；目标缺失语义仍待定 |
| Add + 非法值（如 `X`） | 拒绝；不留下新/部分产品 | **当前缺陷**：请求成功，未知键被忽略，未因 `X` 拒绝 |
| Edit：`Y → N` | 同一个 owner 变体更新为 `N` | **当前缺陷**：请求成功但字段未实现 |
| Edit：`N → Y` | 同一个 owner 变体更新为 `Y` | **当前缺陷**：请求成功但字段未实现 |
| Edit 缺失字段 | 不清空成 `N`；拒绝或保留旧值按待定契约 | 当前请求成功但无字段/无遗漏更新语义 |
| 同产品码不同 owner | 生成两个不同变体并各自保留 SN 值 | 原生变体生成已验证；现有 API07 仍会创建两个不同模板，目标 API07 路径未验证 |
| 重复 Add 同一 owner+产品码 | 更新同一变体，不重复建档 | 当前单产品 upsert 通过探针；新变体/复合模板键尚未验证 |
| SN 要求与原生 `tracking` | 明确 `Y/N` 是否驱动 WMS 捕获 | 同模板变体的原生 tracking 共享，不能直接作为逐 owner 设置 |

## 7. 数据迁移与兼容性风险

1. **默认编码迁移。** 现有 Ginlong 产品把原始 `productCode` 存在 `default_code`；新方案要保存原始码并把内部码改成无歧义组合。必须先生成旧 `default_code`、owner code、新原始码、新组合码的迁移清单；核对碰撞、长度及已有引用。Odoo 原生产品未提供 default_code 全局唯一 SQL 约束，不能仅凭默认编码假设唯一。
2. **模板合并/变体重构。** 当前 API07 对同一 raw productCode 的不同 owner 建不同模板/单变体；新方案要求同一基础产品模板下形成不同 owner 变体。合并模板可能影响模板级名称、分类、UoM、tracking、销售/采购属性、供应商、历史单据关联及库存估值。开发库当前没有重复编码、属性行或库存，不能代表目标环境安全迁移。
3. **共享字段覆盖。** Odoo `name`、`uom_id` 和 `tracking` 是模板级；现有 API07 把 `productName` 和 UoM 写入模板。同一模板多个 owner 的值若不同，会互相覆盖。Ginlong 名称是否允许按 owner 不同，Odoo 库存基础单位是否必须一致，需要确定；Ginlong `unit` 文本字段可独立存储，但不能因此推断 Odoo 库存单位也可逐变体不同。
4. **库存 owner 与产品 owner 是两个关系。** 变体 `ginlong_owner_code` 和 `stock.quant.owner_id` 分别标记产品归属与库存所有者。现有 Picking 路径会从 Order、pallet 或 quant 取得 owner。迁移/回归须验证二者一致，避免 API09 查询漏库存或跨货主泄漏。
5. **其他 WMS 调用。** `product_lookup.py`、订单查询/报表及 Ginlong 回传目前读取 `default_code`。修改内部编码需一并处理原始码查询和展示，不可将组合码暴露给旧 API 或 Ginlong。
6. **SN 要求冲突。** 同模板 owner 变体不能拥有不同原生 `tracking`。若本地 SN 开关需要驱动拣货/入库逐序列号记录，需要最小 WMS 适配和回归测试；若字段只用于 Ginlong 产品档案，则不应改变 WMS 原生跟踪状态。
7. **开发库基线有限。** 当前 8 个 Ginlong 产品 owner code 均为 `2110`，但没有匹配联系人；库存、move line 为空。API01/API07 的 owner Contact 创建/关联和真实库存流转需在实施测试数据库中覆盖，不能从当前产品快照推定已完成。

## 8. 最小实施方案建议（供 Human Review）

1. 在 `product.product` 增加原始外部编码字段 `ginlong_product_code`；继续复用 `ginlong_owner_code` 作为现有 owner 业务键，API07 使用 `_resolve_ginlong_owner(..., create=True)` 确保 Contact 存在。无需新增货主产品映射模型。若需要强 ORM 关系，先评估现有 owner code 是否足够，避免同时维护重复 owner 字段。
2. 对每个 Ginlong `productCode` 建一个基础 `product.template`，通过 Odoo 原生 owner 属性生成 `product.product` 变体；每个变体持有 owner code、原始产品码及 owner 特有字段。`default_code` 存储可逆、无歧义的内部组合码。为同一 `(owner, ginlong_product_code)` 防止重复产品；组合格式和是否增加唯一约束在 TDD 中确定。
3. 先列明 Ginlong 字段映射到模板/变体的边界。名称若按 owner 不同，增加最小 variant 字段保存 Ginlong 名称；UoM 继续使用共同的 Odoo 库存单位，Ginlong 原始单位文本放 variant 字段，除非业务确认需要逐变体不同的 Odoo 库存 UoM。
4. API01 保持 owner Contact 自动创建/复用，并以 `(owner, ginlong_product_code)` 校验变体；API03 保持缺 owner/缺组合拒绝且不自动创建；API07 按同键 upsert 变体并创建/复用 Contact；API09 保持只读，按 owner、warehouse 和变体原始码筛选物理 `stock.quant.quantity`，排除保留量扣减，并回传原始产品码。
5. 将 `snTrackingRequired` 作为 nullable variant 字段，缺省不写 `N`；API 层验证 `Y/N`，其是否必填及缺失时 create/update 行为先在 Human Review/TDD 确认。不要直接映射到模板级 Odoo `tracking`。如果需要此标记实际约束现场 SN 采集，再在 `worlddepot` 相关 WMS 校验点增加最小逐变体检查，并用旧单据回归验证。
6. 迁移按 `(旧 owner code, 旧 default_code)` 建对照清单；先完成只读冲突扫描，再在测试库验证产品/属性/单据/库存引用迁移和回滚。禁止在实施方案批准前对现有业务数据做合并或改码。

## 9. Open Items

| # | 待确认内容 | 影响 |
| --- | --- | --- |
| OI-01 | `snTrackingRequired` 仅为 Ginlong 物料属性，还是必须驱动 Odoo/WMS 对该变体强制采集 SN？Ginlong 尚未正式确认字段。 | 决定是否修改 `worlddepot` SN 流程；不同 owner 的 Y/N 与模板级 `tracking` 冲突。 |
| OI-02 | `snTrackingRequired` 缺失时 Add/Edit 的明确语义：拒绝、创建为空、或 Edit 保留原值？ | API07 字段可空性和兼容旧 Ginlong 报文。 |
| OI-03 | 多货主共享同一个 `product.template` 时，`productName` 是否必须逐 owner 独立；各 owner 的 Ginlong `unit` 是否可能不同？ | 名称及 Odoo 库存 UoM 属模板级，不能直接独立设置。 |
| OI-04 | 内部 `default_code` 组合的规范编码格式、可逆规则和最大值策略。 | 避免简单拼接碰撞，决定迁移及其他 WMS 调用改造。 |
| OI-05 | Ginlong 产品 owner 是否仅由现有 `ginlong_owner_code` 字符串关联，还是要求 `product.product` 直接 Many2one 到 `res.partner`？ | 数据完整性、联系人改码及 API09 过滤方式。 |
| OI-06 | API09 的货主隔离是否要求同时验证 variant owner code 与 `stock.quant.owner_id`；对于没有 `owner_id` 的产品库存如何处理？ | 避免漏库存及货主串货；现有 WMS Order owner 到 stock owner 的映射需集成验证。 |
| OI-07 | 目标数据库中 owner/code 重复模板、历史订单、Picking/库存和估值的真实迁移基线。 | 迁移安全；当前开发库无库存及 owner 重复样例，无法验证。 |

## 10. 项目负责人决策记录与 IHR 要求

**2026-11-19 项目负责人决策（本次任务指令）：**按本地暂定契约评估 API07 `snTrackingRequired`，外部 JSON 类型为 String，`Y/N` 分别表示要求/不要求采集 SN，字段放在 `product.product` 变体；缺失不得默认 `N`。该决定授权本次技术验证和实施方案起草，**不表示 Ginlong 已批准或正式确认 API 字段变更**。

本记录作为后续实施 IHR 的决策来源。实施时应在对应 CC 的新增 IHR 条目中引用本报告，写明“项目负责人本地决策 / Ginlong 正式确认未完成”，并保留后续 Ginlong 确认的单独证据；不回写或改写已关闭 CC-GIN-001–004 的历史 IHR。

## 11. 证据索引

- Odoo 原生变体：`addons/product/models/product_attribute.py`、`addons/product/models/product_template.py` 的 `_create_variant_ids()`、`addons/product/models/product_product.py`。
- Odoo 原生库存跟踪：`addons/stock/models/product.py:721-726`。
- Ginlong 产品字段：`mymodules/ginlong_apis/models/wms_extensions.py` 中 `ProductProduct`。
- API01/03 产品定位：`mymodules/ginlong_apis/services.py:120-138, 156-188, 254-285`。
- API07 当前 upsert：`mymodules/ginlong_apis/services.py:435-485`。
- API09 查询及数量映射：`mymodules/ginlong_apis/services.py:488-540`。
- API04 等回传产品编码：`mymodules/ginlong_apis/models/ginlong_callbacks.py:53-84`。
- WMS 共用产品查找：`mymodules/worlddepot/controllers/hoymiles/product_lookup.py:17-44`。
- WMS 产品导入/原生跟踪：`mymodules/worlddepot/models/my_product_template.py:57-70`。
- WMS 入库库存 owner 来源：`mymodules/worlddepot/models/inbound_order_create_piking.py:35-43`；出库分配：`mymodules/worlddepot/models/outbound_order_create_picking.py`。

**代码修改：无。业务实现授权：无。** 本报告提交 Human Review 后，待批准再进入 TDD/CC 实施范围。
