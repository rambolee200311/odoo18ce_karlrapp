# TV-GIN-008 技术验证报告 v0.1

| 项目 | 内容 |
|---|---|
| 状态 | 已完成；作为 SRS v1.3 / TDD v1.6 / Plan v2.1 与 CC-GIN-008 v1.0 的冻结依据 |
| 验证日期 | 2026-11-24 |
| 环境 | 本地 Odoo 18 CE；数据库 `odooce_karlrapp`；仅 Odoo Shell ORM；无生产或外部 API 访问 |
| 模板同步 | BLOCKED；沿用已批准流程例外，不记为 PASS |

## 1. 验证方法

检查实际自定义模块源码及 Odoo 18 原生 `product.product` 源码；用本地 `odoo shell -c odoo.conf` 读取 ORM 字段、状态、模型约束及记录计数；归档恢复试验在 Odoo ORM savepoint 中运行，并以异常回滚，未留测试记录。全程未直接访问 PostgreSQL、执行 SQL、清理或修改现存业务数据。

## 2. 业务模型与存量键检查

Odoo ORM Registry 读取确认：

| 模型 | 业务字段 / 有效状态 | 现状约束 |
|---|---|---|
| `world.depot.inbound.order` | `reference`；`state != cancel` | 仅有 Python 项目内搜索约束，无全局数据库有效键约束 |
| `world.depot.outbound.order` | `reference`；`state != cancel` | 未发现全局有效键数据库约束 |
| `world.depot.stocktake.order` | `count_order_no`；`state != cancel` | 订单号有普通索引，未发现全局有效键数据库约束 |
| `product.product` | `ginlong_owner_code` + `ginlong_product_code`；`active=True` | 未发现 Ginlong 复合有效键约束 |
| `ginlong.api.idempotency` | `api_code/business_key/event_key/request_fingerprint/state` | `event_key` 已存在；旧唯一约束不包含它 |

ORM 分组统计结果：API01/03/05 全局有效单号重复组均为 0；API07 active `(owner, productCode)` 重复组为 0。该结果允许当前开发库增加约束，不代表其他环境升级无需预检。

本次实际只读查询输出摘要：API01 幂等历史 7 行、API03 0 行、API05 0 行、API07 10 行。统计不删除或改写记录。

## 3. API07 产品变体归档验证

Odoo 18 原生源码 `addons/product/models/product_product.py` 的变体唯一性为针对 active 组合的部分唯一索引 `(product_tmpl_id, combination_indices) WHERE active IS TRUE`。因此归档 variant 可释放活动组合身份，重新激活原 variant 可重用原身份。

在 ORM savepoint 中创建临时 Ginlong variant，归档后重新激活，验证恢复前后 `product.product.id` 相同、货主编码及 productCode 不变、active variant 数为 1；随后抛出 sentinel 并由 savepoint 回滚。报告：`original_id=2059, restored_id=2059, active_variant_count=1, owner_code_preserved=True, product_code_preserved=True`。该临时记录已回滚，未污染业务数据。

只读历史引用统计：当前归档 Ginlong variant 0；本地库相关 API 入库/出库产品行、lot、quant 与 stocktake result 的归档引用计数均为 0。方案选择恢复同一 variant，可保留将来存在的产品记录引用。

## 4. 幂等生命周期与并发方案结论

`ginlong.api.idempotency.event_key` 已存在且可保存不透明事件身份；可将唯一约束与读取域扩展为包含 `event_key`，无需新增 `lifecycle_id`。旧 event_key 为空的历史行保留。新增 Add 生命周期分配新 event_key；删除事件使用当前 WMS 记录身份，避免跨生命周期复用事件键。

通用幂等组件通过可选 adapter callback 询问当前记录有效性并获取事件键；具体模型和状态只放在 Ginlong 业务 adapter。数据库级有效身份唯一字段负责独立事务竞争下的最终防线，服务端对唯一冲突后重新查询当前有效对象，只有识别为业务键冲突才返回幂等错误。

该结论基于现有字段/约束检查及 ORM 元数据，不是本报告所述的多 worker 并发测试结果。真实并发验收列入 CC-TEST-078/079；未执行项在 ATR 中必须保留 BLOCKED / NOT RUN，不能据设计可行性宣称通过。

## 5. 主要风险及处理

| 风险 | 证据与处理 |
|---|---|
| 订单单号历史跨 project 冲突 | 全局分组当前无重复；新增约束前仍执行升级期 ORM 预检，发现冲突停止，不自动修改数据 |
| 旧成功幂等记录阻塞新生命周期 | 当前执行器确有历史成功键检查与指纹重放；改用事件键隔离新 Add 生命周期，先查业务有效性 |
| Delete 遇到多轮 cancel 历史 | 当前部分查询未统一过滤 cancel；实施中按当前 project 的有效对象定位 Delete/Edit |
| 产品归档后不能重新 Add | 当前 `active_test=False` 搜索会将归档产品当冲突；实施改为有效记录判重并恢复同一 variant |
| 多 Worker 冲突错误误分类 | 数据库约束冲突需在 savepoint 回滚后重新 ORM 检查有效对象；未知冲突重新抛出 |
| 其他安装库存量数据 | 本环境 0 重复不代表其他库无冲突；预检脚本在升级时执行并以错误阻止模块升级 |

## 6. 结论

**TV 结论：通过设计与数据可行性验证；并发运行结果仍须按 CC 自动化实测。** 当前开发库可实施全局有效键唯一约束，event_key 足以承载生命周期区分，API07 恢复归档 variant 是最小且保留关联的路径。

本 TV 不验证 API 行为测试、不验证真实多 Worker 并发，也不验证真实 Ginlong/KR 联调。相应结果由 ATR 单独记录。
