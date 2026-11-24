# CC-GIN-008 v0.1 Draft — API Add 业务记录有效性与生命周期幂等

| 项目 | 内容 |
|---|---|
| 状态 | **有条件通过设计评审；冻结前待完成 TV**；未冻结、未授权实施 |
| 日期 | 2026-11-24（评审意见修订） |
| 当前依据 | [SRS v1.2 Frozen](../requirement/SRS_ginlong_apis-v1.2.md)、[TDD v1.5 Frozen](../ginlong_apis/TDD-v1.5.md)、[Plan v2.0 Frozen](IMPLEMENTATION_PLAN_ginlong_apis-v2.0.md)；SRS/TDD/Plan/架构规范的本次修订待 TV 通过后依据证据更新 |
| 当前批准基线 | SRS v1.2、TDD v1.5、Plan v2.0；本草案不覆盖 |
| Baseline validity | **IMPACT REVIEW REQUIRED** |
| Human Review | 有条件通过设计评审；Global key、API07 archive 方案及 lifecycle 表示方式待 TV/冻结评审 |
| 模板同步 | BLOCKED；沿用已批准例外，不伪记 PASS |

## 1. 目标

API01/03/05/07 Add 改为按当前业务记录有效性判重。有效记录存在时拒绝；无有效记录时允许进入原校验与创建流程。订单取消或产品归档后，同一业务键可以开启新生命周期；历史业务对象、幂等行和日志均保留。必须支持多 Worker 并发，保证同键最多一条有效对象。

本稿仅供设计评审，不授权修改代码、模块升级、测试、HVR、数据清理或 Git 操作。

## 2. 范围

### 包含
- API01 `inboundOrderNo`、API03 `outboundOrderNo`、API05 `countOrderNo`：业务键为全局订单号，不含 `project`；对应订单 `state != cancel` 为有效，`state=cancel` 为无效。Delete 继续置 cancel，不物理删除；现有 project 归属及权限机制保持不变。
- API07 `(owner, productCode)`：对应产品变体 `active=True` 为有效；`active=False` 归档记录不阻止重新 Add。重新 Add 时是恢复原变体还是创建新变体，本 CC 不预定，待 TV 根据 Odoo 原生唯一性及历史业务关联提出最小方案。归档经现有 Odoo 产品管理操作完成，不新增 Ginlong Delete。
- 通用幂等有效性策略接口，以及现有 `ginlong.api.idempotency` 支持多生命周期所需的最小调整；不预设新增字段或 `lifecycle_id`。
- 具体业务模型并发有效键数据库约束、旧数据只读预检、统一错误和 API 日志接入。
- Odoo 自动化、真实 HTTP/ORM 集成测试和人工 HVR 测试包。

### 不包含
- API02/04/06/08/10 出站幂等、API09 库存查询、Edit 语义及 Ginlong 字段/SN规则调整。
- 改动 stock.picking、库存或 KR Gateway；真实 Ginlong/生产访问。
- 物理删除/覆盖历史订单、产品、幂等记录或 API 日志；自动合并/取消已有冲突数据。
- 新建平行业务模型、第二张幂等表、通用状态机或进程内锁。

## 3. 对象规则

| API | 全局业务唯一键（不含 project） | 有效记录 | 有效记录存在时 | 无有效记录时 |
|---|---|---|---|---|
| 01 | `inboundOrderNo` | 入库订单 `state != cancel` | 同/不同 Payload Add 都拒绝 | 正常校验并创建，归属仍按当前 API user/project 机制 |
| 03 | `outboundOrderNo` | 出库订单 `state != cancel` | 同/不同 Payload Add 都拒绝 | 正常校验并创建，归属仍按当前 API user/project 机制 |
| 05 | `countOrderNo` | 盘点订单 `state != cancel` | 同/不同 Payload Add 都拒绝 | 正常校验并创建，归属仍按当前 API user/project 机制 |
| 07 | `(owner, productCode)` | 匹配的 `product.product.active=True` | 同/不同 Payload Add 都拒绝 | TV 决定恢复既有归档变体或创建新的有效变体；须保留历史关联 |

API01/03/05 Delete 只定位当前有效对象并保持既有 cancel 行为；之前 cancel 的记录继续保留但不参与有效对象命中。新 Add 后再次重复提交仍拒绝。

## 4. 技术方案门槛

1. 通用组件只调用对象适配器的有效性策略；模型名、字段、状态与查询域留在具体业务适配器。
2. 有效性检查早于历史成功响应回放。有效记录存在时必定拒绝；无有效记录时历史成功行不阻止新 Add、不冒充新结果。TV 比较复用现有字段/约束调整等最小方案；不预设新增 `lifecycle_id`。
3. 业务创建与新周期成功幂等结果同事务提交；失败无部分业务数据、无成功幂等行。
4. 现有幂等唯一约束须支持同一业务键、相同/不同 Payload 在多个业务生命周期留下独立历史结果。TV 核对现有 `event_key`、指纹及唯一约束，评估最小无损修改；不强制新增字段。
5. 每个模型须有数据库级有效身份唯一性。仅 ORM search-before-create、`@api.constrains`、进程锁或串行测试不通过并发门禁。约束升级前只读盘点存量有效重复键；发现冲突停止并报告，不自动改业务数据。
6. 只将已识别的有效键唯一冲突转为重复 Add 错误；其它 IntegrityError 保持准确分类。使用统一 Error 组件和现有 API 日志。
7. API07 归档不阻止再次 Add。TV 必须核对 Odoo 原生模板/变体唯一约束及订单、库存移动、Lot 等历史引用，再提出恢复旧变体或新建变体的最小方案；本 CC 当前不选定其一。

## 5. 自动化验收矩阵（建议编号）

| ID | 场景 | 主要预期 |
|---|---|---|
| CC-TEST-071 | 四 API 首次 Add | 真实 HTTP 成功；ORM 有且仅有一条有效对象及独立幂等历史 |
| CC-TEST-072 | 有效对象 + 同 Payload Add | 明确重复拒绝；业务数据不变；不重放旧成功结果 |
| CC-TEST-073 | 有效对象 + 不同 Payload Add | 同样拒绝；不得修改原订单/产品 |
| CC-TEST-074 | cancel/archive 后同 Payload Add | 新生命周期创建成功，旧无效行不变 |
| CC-TEST-075 | cancel/archive 后不同 Payload Add | 经正常校验创建成功，旧历史保留 |
| CC-TEST-076 | 新生命周期再次 Add | 按新有效记录拒绝，不回放前一周期响应 |
| CC-TEST-077 | 多轮失效/重建 | 每轮业务/幂等记录均留存，始终最多一个有效对象 |
| CC-TEST-078 | 并发相同 Payload | 多事务/worker 竞争仅一个创建成功，其余重复拒绝 |
| CC-TEST-079 | 并发不同 Payload | 同键仍仅一个成功；失败事务无部分对象/成功幂等行 |
| CC-TEST-080 | Delete 有效目标解析 | 多条 cancel 历史+一条 active 时只取消 active，历史不变 |
| CC-TEST-081 | Edit/其他 API 回归 | API01/03/05/07 Edit 与 API02/04/06/08/10、API09 不回归 |
| CC-TEST-082 | 迁移/历史保留 | 历史业务/幂等/日志行及关键字段不变；存量 active 冲突停止升级 |
| CC-TEST-083 | 跨 project 全局键 | API01/03/05 同单号有效记录跨 project 也拒绝；project 归属和权限不变；响应不泄露原单详情 |

每个用例断言真实 HTTP 响应、ORM 状态、幂等生命周期和 API 日志。并发测试须真实多 Worker/事务；静态检查和单进程模拟不算通过。

## 6. 人工 HVR（建议）

| HVR | 操作 | 预期 |
|---|---|---|
| HVR-GIN-008-01 | API01 Add → 同/不同报文 Add → Delete → 相同报文 Add → Delete → 不同报文 Add → 再重复 | 有效期内拒绝；每次 cancel 后可创建新有效订单；历史订单和幂等行保留 |
| HVR-GIN-008-02 | API03 按同流程验证出库单号 | 同 API01；产品仍按 owner+productCode 校验 |
| HVR-GIN-008-03 | API05 按同流程验证盘点单号 | 同 API01；不触碰 stock.quant |
| HVR-GIN-008-04 | API07 Add → 重复 → Odoo Form 归档 → 同/不同 Payload Add | 有效产品时拒绝；归档后允许重新 Add；恢复/新建方式按 TV 结论冻结，核对历史关联未丢失 |
| HVR-GIN-008-05 | 对四对象重复第二轮失效/重建并检查管理页面 | 当前有效记录只有一条；历史业务、幂等与请求日志可追踪 |
| HVR-GIN-008-06 | 使用两个不同 project 的 API User，对 API01/03/05 提交相同有效业务号 | 第二个 Add 被全局判重；不泄露第一 project 的单据详情；新单据归属与权限规则不变 |

Codex 可准备专用 HVR 输入和核查步骤；人工 PASS 由项目负责人填写。HVR 不代替多 Worker 自动化。

## 7. 影响与待审事项

- 历史 IHR-GIN-005 IHR-009 记录的旧 API01 永久拒绝重加规则被 2026-11-24 决定取代；不得改写历史运行记录。
- API01 现有项目+reference 搜索约束不是数据库原子唯一；API03/API05 未发现对应数据库有效唯一；API07 当前检查将归档变体与历史幂等一并判重。
- `ginlong.api.idempotency` 当前唯一键为 `(api_code,business_key,request_fingerprint)`；需 TV 验证不新增 `lifecycle_id` 时能否通过现有字段/最小约束调整保存多个生命周期。
- 三个订单键是全局业务键，不含 project；需核实现有模型约束和幂等/有效性查询能否保持全局范围，同时不改变订单归属及权限。
- API07 归档再 Add 的恢复/新建方案、历史业务关联影响及变体唯一性待 TV。
- 多生命周期幂等不预定 `lifecycle_id`；由 TV 证明现有字段/约束的最小可行变更。
- 受影响 SRS/TDD/Plan 与通用架构规范当前均为 Review Draft；批准前 CC 不可冻结或实施。

## 8. 冻结与退出条件

退出条件包括：上游基线与本 CC 批准冻结；四类有效性策略都由对象适配器定义；同/不同 payload、多个生命周期、旧记录保留及失败回滚通过真实 HTTP/ORM 测试；数据库约束证明多 Worker 最多一个有效业务对象；全部适用自动化证据进入 ATR/IHR；人工 HVR 由负责人按冻结门禁完成。

当前状态：Draft，等待 Human Review。模板同步 BLOCKED；沿用已批准例外，不伪记 PASS。未授权代码修改、模块升级、测试、HVR、数据清理或 Git 操作。


## 9. 2026-11-24 条件评审决定与 TV 门禁

### 已确认的全局业务键

| API | 全局业务键 | 有效性 |
|---|---|---|
| API01 | `inboundOrderNo` | `state != cancel` |
| API03 | `outboundOrderNo` | `state != cancel` |
| API05 | `countOrderNo` | `state != cancel` |
| API07 | `(owner, productCode)` | `active=True` |

API01/03/05 的有效性查询、Add 判重和幂等身份范围为全局业务号，不纳入 `project`；即使请求来自不同 project，有效同号订单也须拒绝。新建订单仍写入当前 API User 所属 project；现有 project 归属及权限机制保持不变。Delete 不得因全局判重而绕过 API User 的既有 project 权限，也不得向调用方返回其他 project 的订单详情。

### TV 前不得预定的技术选择

- 不预先决定 API07 归档变体重新 Add 时恢复原变体还是创建新变体；TV 检查 Odoo 原生产品变体唯一性及关联历史订单/库存/Lot 后提出最小方案。
- 不预先要求新增 `lifecycle_id`；TV 检查现有 `ginlong.api.idempotency` 字段、`event_key`、指纹和唯一约束，证明保存重复业务生命周期的最小无损修改。
- 并发有效唯一须覆盖全局业务键。TV 核对 ORM 管理的数据库约束能否同时保留 cancel/archive 历史行。

### 评审顺序

本 CC 获有条件设计通过。先评审并批准 [TV-GIN-008 技术验证计划 v0.1](../context/report/TV-GIN-008-Plan-v0.1.md)；TV 完成并经评审通过后，依据证据形成 SRS v1.3、TDD v1.6、Plan v2.1、CC-GIN-008 v0.2 及通用架构规范的正式修订。当前 v0.1 仍为 Draft，不冻结、不授权代码、模块升级、数据变更或 Git 操作。
