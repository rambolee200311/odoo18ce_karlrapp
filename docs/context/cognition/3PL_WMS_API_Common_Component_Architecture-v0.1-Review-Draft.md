# 3PL WMS API 通用组件架构规范 v0.1 Review Draft

| 项目 | 内容 |
|---|---|
| 文档性质 | 通用组件架构规范新建评审草案；仓库中未找到同名独立源文件 |
| 版本 / 日期 | v0.1 Review Draft / 2026-11-24 |
| 状态 | 待 Human Review；未冻结 |
| 适用范围 | 跨项目 WMS、ERP、TMS API 集成中的通用幂等组件 |

> 本稿作为“更新《3PL WMS API 通用组件架构规范》中 Idempotency 组件设计”的提案。仓库未找到原规范独立文件，因此这是新建草案，不宣称已更新或冻结仓库外文件。

## 1. 目标与分层

通用 Idempotency 组件负责 API 身份、业务键、请求指纹、生命周期尝试、并发结果和审计记录。具体业务对象的模型、字段、有效状态、业务键作用域和重复错误由业务适配器定义。组件不得通过客户 API 编号硬编码 Odoo 模型或状态。

| 层 | 责任 |
|---|---|
| 通用组件 | 提取配置键/Action；调用有效性策略；分配生命周期身份；协调唯一请求、事务结果和历史记录 |
| 对象适配器 | 按本业务模型查询有效对象、定义作用域、执行创建/取消并提供统一 Error 冲突映射 |
| 业务模型 | 保持业务事实，并提供数据库层的有效业务键原子唯一性 |
| API 日志 | 每次请求追加审计，追溯错误/响应，不删除历史 |

## 2. 有效性策略接口

适配器向通用层提供逻辑接口 `resolve_effective_record(scope, business_key) -> {exists, opaque_record_id?, conflict_error?}`。这是边界描述，不要求新增一个大型 Provider 框架。通用层只解释 `exists`；模型查询、状态和值域都由适配器负责。

## 3. Add 生命周期处理

1. 现有认证、字段和 Action 校验通过后，提取 API/作用域/业务键。
2. Add 先查当前有效业务记录；存在则无论 Payload 指纹是否相同均拒绝，且不重放历史成功响应。
3. 无有效记录时，为新的业务创建周期分配唯一、不透明的 lifecycle identity。历史成功幂等结果只用于审计，不参与本周期响应回放。
4. 业务创建和本周期幂等成功结果同事务提交；失败整体回滚。
5. 新周期不得覆盖旧成功记录。现有唯一键需扩展 lifecycle identity，使相同 Payload 在取消/归档后可留下新的独立幂等行。
6. 没有外部 Request ID 时不承诺跨网络 exactly-once。

## 4. 多 Worker 原子性

“先 ORM 搜索、再 create”不能保证并发唯一。每个业务模型必须由数据库约束保证当前有效业务身份至多一行。可评估模型侧存储的有效身份字段：有效时含模型定义键，无效（cancel/archive）时释放身份，唯一约束允许多个历史无效行。通用组件不使用 Python 全局锁、本地缓存或 Worker 内锁。

迁移前只读盘点存量有效重复键；遇到冲突必须停止升级并报告，不自动合并、删除或取消业务数据。

## 5. 历史与错误处理

- 保留取消/归档业务记录、所有历史幂等结果及 API 日志。
- 当前有效业务记录才阻止新的 Add；成功历史不能永久占用业务键。
- 已成功历史行不得变更为后续生命周期结果；每个新周期关联独立身份和日志。
- 只将已识别的有效键唯一冲突转换为重复 Add 错误，其他完整性异常保持正确分类。

## 6. Ginlong 适配示例

| API | 业务键 | 有效记录 | 失效方式 |
|---|---|---|---|
| API01 | `inboundOrderNo`（当前 WMS project 范围） | 入库单 `state != cancel` | Delete 设置 cancel |
| API03 | `outboundOrderNo`（当前 WMS project 范围） | 出库单 `state != cancel` | Delete 设置 cancel |
| API05 | `countOrderNo`（当前 WMS project 范围） | 盘点单 `state != cancel` | Delete 设置 cancel |
| API07 | `owner + productCode` | 产品变体 `active=True` | Odoo 归档；无 Ginlong Delete |

## 7. 最低验收

每类对象覆盖首次 Add、active 时相同/不同 Payload 拒绝、cancel/archive 后同/不同 Payload 新建、再次重复拒绝、多轮生命周期、历史保留、并发竞争，以及失败无部分数据。必须通过真实 HTTP 入口和 ORM 断言；静态检查或串行测试不证明多 Worker 原子性。详见 [CC-GIN-008 Draft](../../implementation/CC-GIN-008-v0.1-Draft.md)。

## 8. Review Items

1. lifecycle identity 字段与现有唯一约束的无损迁移。
2. 四个业务模型有效身份数据库唯一约束和存量冲突门禁。
3. API07 归档变体保留且新 active 变体可创建的 Odoo 原生限制。
4. API01/03/05 项目作用域与通用幂等业务键的对齐。
5. 沿用现有统一 Error 的具体 API 错误映射。

模板同步 BLOCKED；沿用已批准例外，不伪记 PASS。
