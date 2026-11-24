# 3PL WMS API 通用组件架构规范 v1.0

| 项目 | 内容 |
|---|---|
| 状态 | Frozen with Open Items；用于 Ginlong CC-GIN-008 |
| Human Review | APPROVED；项目负责人李建强；2026-11-24 |
| 模板同步 | BLOCKED；沿用既有批准例外，不记为 PASS |

## 1. 适用原则

通用 API 组件只提供可复用的技术机制；具体业务对象、有效状态、唯一键和错误映射由模块适配器提供。组件不得把某个客户的 Odoo 模型名、字段名或状态值写入通用流程。

## 2. Idempotency 生命周期

1. 通用幂等执行器按接口配置读取业务键、Action 和方向；请求指纹用于区分同一事件的内容。
2. 对配置了业务有效性检查的 Action，执行器在历史结果重放前调用可选生命周期适配器。适配器检查当前业务记录；有效记录冲突时返回业务错误，不允许历史成功结果掩盖该冲突。
3. 适配器为新的业务生命周期提供稳定事件身份。相同事件重试可重用结果；失效后新建记录须使用新的事件键，使历史行与新周期并存。
4. 现有事件字段优先承载生命周期身份。只有证据证明现有字段无法表达且经评审批准，才可增加存储结构。
5. 业务记录和成功幂等结果须在同一个 Odoo 事务提交。失败回滚不得留下成功结果。
6. 并发防重最终依赖数据库唯一约束；进程锁、缓存、单 worker 串行测试不能作为保证。唯一冲突后仅在适配器确认当前业务键已有效占用时映射成重复业务错误。
7. Delete 的事件身份与具体业务记录生命周期关联；业务记录取消后重复同事件可读回结果，下一次 Add 属于新的业务生命周期。

## 3. Ginlong 适配示例

下表属于 Ginlong 适配配置，不是通用组件内置规则：

| API | 业务键 | 有效性由适配器判断 |
|---|---|---|
| API01 | `inboundOrderNo`，全局，不含 project | `world.depot.inbound.order.state != cancel` |
| API03 | `outboundOrderNo`，全局，不含 project | `world.depot.outbound.order.state != cancel` |
| API05 | `countOrderNo`，全局，不含 project | `world.depot.stocktake.order.state != cancel` |
| API07 | `(owner, productCode)` | `product.product.active=True` |

订单创建归属和 Delete/Edit 权限仍由 WMS project 机制处理；全局 Add 冲突不得泄露其他 project 单据内容。API07 已归档变体由 Ginlong adapter 按批准流程恢复原记录。

## 4. 验收要求

组件单测验证适配回调和事件键；数据库集成测试验证同事务、提交/回滚及唯一约束；HTTP E2E 验证真实入口。各层分别报告。自动化通过不能替代人工 HVR，单进程行为也不能代替多事务并发验证。

## 5. 修订记录

| 版本 | 日期 | 说明 |
|---|---|---|
| v0.1 Review Draft | 2026-11-24 | 历史评审稿，订单范围含 project 且生命周期字段待定；保留原件 |
| v1.0 | 2026-11-24 | 按批准决定明确全局业务键不含 project、适配器负责有效性、复用事件键并要求数据库并发唯一；Human Review APPROVED |
