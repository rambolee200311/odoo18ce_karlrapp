# CC-GIN-008 v1.0 — 有效业务记录与幂等生命周期

| 项目 | 内容 |
|---|---|
| 状态 | **Closed；Closure SATISFIED；Human Review APPROVED** |
| 批准日期 | 2026-11-24 |
| 上游基线 | SRS v1.3、TDD v1.6、Implementation Plan v2.1 |
| 实施状态 | Closed（2026-11-24 Human Review APPROVED） |
| 模板同步 | BLOCKED；沿用已批准流程例外，不记为 PASS |
| 授权范围 | 本地代码修改、Odoo 自动化/ORM/多事务验证；不访问生产、真实 Ginlong 或 KR |

## 1. 目标

API01/03/05/07 的 Add 判重以当前业务记录是否有效为准。取消或归档使当前记录失效后，允许相同业务键重新 Add；旧业务记录、幂等记录和 API 日志均保留。数据库并发约束保证同一有效键至多有一条记录。通用幂等组件通过适配器获得生命周期事件键和冲突判断，不硬编码 Odoo 模型、字段或状态。

## 2. 固定规则与范围

| API | 全局业务键 | 有效记录 | Add 冲突 | 失效后再次 Add |
|---|---|---|---|---|
| API01 | `inboundOrderNo`，不含 project | `world.depot.inbound.order.state != cancel` | IDM02 | 允许；新订单仍归属当前 API User 的 project |
| API03 | `outboundOrderNo`，不含 project | `world.depot.outbound.order.state != cancel` | IDM02 | 允许；新订单仍归属当前 API User 的 project |
| API05 | `countOrderNo`，不含 project | `world.depot.stocktake.order.state != cancel` | IDM02 | 允许；新订单仍归属当前 API User 的 project |
| API07 | `(owner, productCode)` | 对应 `product.product.active=True` | IDM07 | 允许；恢复同一归档变体并保留既有关联 |

API01/03/05 的跨 project Add 判重为全局，但 Delete/Edit 的对象定位及访问权限仍遵循当前 API User 的 project 范围；冲突消息不得泄露其他 project 的单据内容。API07 不新增 Ginlong Delete。Edit 继续按原有业务逻辑处理。

包含：有效业务身份字段及数据库唯一约束、幂等生命周期事件键、API01/03/05/07 Add 与 Delete 路径、归档产品恢复、历史兼容、自动化和人工 HVR 测试包。

不包含：出站接口及 API09 的行为变更、库存/Picking/KR Gateway 改动、物理删除历史、自动修复存量冲突、无关 WMS 重构。

## 3. 实施设计

1. 在对应业务模型上用存储计算身份字段表达当前有效键；失效时存空值。由 Odoo `_sql_constraints` 对该字段建立唯一约束，允许多个无效历史行。订单键不包含 project。产品键采用无歧义的 owner/code 组合。
2. 约束升级前以 ORM 全局预检有效重复键；发现冲突则停止升级并报告，不改写数据。
3. `ginlong.api.idempotency.event_key` 已存在，复用它表示生命周期事件；幂等唯一约束及读取域包含 `event_key`。Add 每个新生命周期分配新事件键；Delete 事件键绑定当前业务记录身份，重复相同 Delete 可复用结果。旧 `event_key` 为空的记录保留，不覆盖、不删除。
4. 通用幂等执行器仅接受可选生命周期适配回调。适配器负责判断有效记录、生成事件键及提供冲突错误；通用层不解释 Odoo 模型或状态。
5. 有效记录检查先于历史结果重放。Add 冲突始终返回相应幂等错误；失效后旧成功记录不阻断新 Add，也不重放旧生命周期响应。
6. 业务写入和本生命周期幂等成功记录处于同一 Odoo 事务。数据库有效键唯一约束是并发最终防线；只将确认属于有效键唯一约束的冲突映射为重复 Add，其他 IntegrityError 仍报真实错误。
7. API07 Add 命中归档变体时，经共享模板字段一致性检查后恢复同一 `product.product`，不创建第二个变体，不丢失既有引用。

## 4. 自动化验收

所有 HTTP 场景经真实 Ginlong 路由、认证、Error、幂等、业务 Handler 和 ORM 执行。测试使用唯一合成键及事务回滚；不得访问真实外部系统。

| 用例 | 验收内容 |
|---|---|
| CC-TEST-071 | API01/03/05/07 首次 Add 成功，ORM 有一条有效对象并生成独立生命周期记录 |
| CC-TEST-072/073 | 有效对象存在时，相同/不同 Payload Add 均拒绝；对象及原历史记录不变 |
| CC-TEST-074/075 | Cancel/Archive 后，相同/不同 Payload 再 Add 成功，旧对象保留 |
| CC-TEST-076/077 | 新生命周期重复拒绝；多轮失效/重建历史均保留且最多一条有效对象 |
| CC-TEST-078/079 | 独立事务并发提交相同/不同 Payload，恰有一个成功；失败事务无部分业务数据/幂等成功行 |
| CC-TEST-080 | Delete 只取消当前 project 内有效订单，历史 cancel 记录不造成歧义或越权 |
| CC-TEST-081 | API01/03/05/07 Edit 及其余 Ginlong API 回归 |
| CC-TEST-082 | 升级前 ORM 预检与升级后历史业务、幂等及日志保留 |
| CC-TEST-083 | 跨 project 相同有效订单号全局冲突；错误不泄露源单据；新单 project 权限不变 |

每项记录前置数据、HTTP 请求/响应、ORM 断言、日志/幂等证据及 PASS/FAIL/BLOCKED/NOT RUN。多事务并发须由真实独立事务/worker 验证；串行及进程内锁测试不替代。

## 5. 人工 HVR

在 `docs/ginlong_apis/hvr/cc_gin_008/test_data/` 提供四类对象的 Add→重复 Add→Delete/Archive→相同报文 Add→不同报文 Add→再次重复的可执行请求。API01/03/05 另外使用不同 project 的 API User 验证全局 Add 判重与权限边界。HVR 记录包括业务记录、事件键、请求日志和取消/归档历史。人工结果由项目负责人填写，自动化 PASS 不代替 HVR。

## 6. 风险与停止条件

- 数据库唯一约束建立即遇到既存有效重复键：停止升级，提交冲突键及记录引用摘要，不删除/取消记录。
- 并发数据库冲突无法与其他 IntegrityError 准确区分：停止将其映射成重复错误并报告。
- 跨 project 的 Delete/Edit 若无法保持现有权限：停止该变更并修复权限边界。
- 多 worker 环境不可用时，相关并发项保持 BLOCKED；不以单 worker 测试宣称通过。
- 模板同步 BLOCKED 按批准例外保留，不影响本 CC 文档批准，不得伪记通过。

## 7. 追溯与批准

本 CC 执行 SRS v1.3 §BR/FR 的有效性规则、TDD v1.6 §11 的对象适配器、事件键、有效键数据库唯一性及 API07 归档恢复设计。历史 Draft、TV 计划及既有 IHR/ATR 不覆盖；新验证追加到 IHR-GIN-008 / ATR-GIN-008。

| 项目 | 记录 |
|---|---|
| Human Review | **APPROVED**；项目负责人李建强；2026-11-24；批准冻结文档并进入 CC 实施 |
| 当前状态 | Frozen with Open Items；Implementation In Progress |
| 未关闭事项 | 依 ATR 记录实际自动化及多事务结果；真实 Ginlong/KR 不在本 CC |
| Git | 本次授权不包含提交或推送 |

## 8. Human Review 收尾修订（2026-11-24）

本节记录本 CC 冻结后的验收决定；不改变 API01/03/05/07 的业务键、有效性规则、生命周期幂等或并发控制设计。

| 项目 | 批准决定及执行结果 |
|---|---|
| Human Review | **APPROVED**；项目负责人李建强；2026-11-24；批准本节验收范围调整及 N/A/Deferred 处置，要求完成剩余证据后提交关闭评审 |
| 独立数据库事务并发 | Human Review 认可 CC-TEST-078/079 的真实独立 ORM cursor/transaction 并发测试满足本 CC 验收。多 Worker HTTP 并发不再是本 CC 门槛，状态为 N/A（本 CC）；部署级验证 Deferred 至最终项目集成。 |
| 人工 HVR | 取消本底层机制 CC 的独立人工 HVR 要求。HVR-GIN-008-01 至 06 标记 N/A（本 CC），完整业务人工验证 Deferred 至最终项目集成；既有自动化证据不冒充人工 HVR。 |
| 部署前有效键检查 | 正式部署步骤必须先通过 `docs/implementation/scripts/cc_gin_008/pre_upgrade_effective_key_preflight.py` 的 ORM 全局有效键预检。任何冲突都必须停止升级并报告，不自动修改业务记录。 |
| 升级后留存验证 | 升级前后通过 ORM 快照比较历史业务记录、幂等记录及 API 日志关键字段；本轮六类记录均无新增、丢失或关键字段变化。 |
| 本地服务版本 | 8099 当前 Odoo PID 已在升级后重新加载 Registry；数据库 `ginlong_apis` 状态为 `installed / 18.0.2.0.42`，`/web/login` 返回 HTTP 200。 |
| 模板同步 | 仍为 BLOCKED；沿用已批准流程例外，不伪记 PASS。 |

### 当前关闭状态

本 CC 冻结范围内的剩余验收已满足。项目负责人于 2026-11-24 批准关闭，CC 状态为 **Closed**。此前记录的部署级多 Worker、人工 HVR、真实 Ginlong/KR 与模板同步状态均按本节处理，历史实施记录保留；模板同步 BLOCKED 按批准例外保留。

### 版本与收尾记录

| 记录 | 日期 | 内容 |
|---|---|---|
| v1.0 Frozen | 2026-11-24 | Human Review APPROVED；冻结 API01/03/05/07 有效业务记录及幂等生命周期范围。 |
| v1.0 收尾增补 | 2026-11-24 | Human Review APPROVED；接受独立数据库事务并发证据，人工 HVR 与多 Worker HTTP 改为 N/A/Deferred，纳入部署前有效键 ORM 预检、升级后历史记录保留验证及 `.42` 服务加载确认；不改变冻结业务规则。 |
| v1.0 Closed | 2026-11-24 | Human Review APPROVED；FR-GIN-008 Closure SATISFIED；关闭 CC，模板同步例外及最终集成 Deferred 项保持原状态。 |
