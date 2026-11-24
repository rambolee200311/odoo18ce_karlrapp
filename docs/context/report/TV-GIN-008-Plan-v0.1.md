# TV-GIN-008 技术验证计划 v0.1

| 项目 | 内容 |
|---|---|
| 验证对象 | API01/03/05/07 Add 业务有效性与幂等生命周期 |
| 文档状态 | 已执行；验证结论见 [TV-GIN-008-v0.1.md](TV-GIN-008-v0.1.md) |
| 日期 | 2026-11-24 |
| 关联设计 | [CC-GIN-008 v0.1 Draft](../../implementation/CC-GIN-008-v0.1-Draft.md) |
| 当前代码范围 | `ginlong_apis` 与相关 `worlddepot` / Odoo 原生产品模型 |
| 数据约束 | 仅本地开发环境；数据库查看使用 `odoo shell -c odoo.conf` ORM；禁止直接 SQL、psql 或直连 PostgreSQL |
| 模板同步 | BLOCKED；沿用已批准流程例外，不伪记 PASS |

## 1. 验证目标

在冻结 SRS v1.3、TDD v1.6 和 CC-GIN-008 v0.2 之前，以源码、Odoo ORM 元数据及受控测试证据回答以下问题：

1. API01/03/05 是否能按全局业务键判定当前有效记录，且不会把 `project` 纳入唯一键或幂等判重范围；现有 project 归属、API User 权限和新单据归属保持不变。
2. 同一有效业务键并发 Add 是否能由数据库级约束保证最多一条有效业务记录。
3. API07 对归档变体重新 Add 时，恢复原变体和创建新变体分别会如何受 Odoo 原生唯一性约束及历史业务关联影响；据证据提出最小方案，不预先选定其一。
4. 现有 `ginlong.api.idempotency` 是否能在保留历史行/结果且不新增 `lifecycle_id` 预设的条件下，支持取消/归档后的新 Add 生命周期；若不支持，给出最小可行的字段/约束修改及其对其他 API 幂等行为的影响。
5. 修改建议是否能保持通用 Idempotency 不含 Odoo 模型、字段或状态硬编码，并保留 API02/04/06/08/10 的出站幂等行为。

本文件是计划，不是 TV 报告。完成计划评审前不运行验证，不修改代码、模块、数据库或 Git。

## 2. 已确认业务规则

| API | 全局业务唯一键 | 有效记录 | 无效记录 |
|---|---|---|---|
| API01 | `inboundOrderNo` | 入库单 `state != cancel` | `state=cancel` |
| API03 | `outboundOrderNo` | 出库单 `state != cancel` | `state=cancel` |
| API05 | `countOrderNo` | 盘点单 `state != cancel` | `state=cancel` |
| API07 | `(owner, productCode)` | 匹配产品变体 `active=True` | `active=False`（归档） |

API01/03/05 不把 `project` 加入业务唯一键或幂等判重作用域。跨 project 请求仍依原 API User 权限处理，订单写入仍归属于现有 project；若另一 project 已有同一全局有效单号，应拒绝新 Add，但错误响应不得泄漏原 project 的订单详情。

存在有效对象时，相同或不同 Payload 的 Add 都拒绝。没有有效对象时，历史成功幂等记录不得阻止新 Add，也不得重放旧成功结果。cancel/archive 历史业务行、幂等行和日志均保留。API07 归档后 Add 的具体处理方式尚未决定。

## 3. 预检源码事实（只读静态检查，不是 TV 结论）

| 位置 | 已观察到的现状 | 待 TV 验证的问题 |
|---|---|---|
| `mymodules/worlddepot/models/inbound_order.py:160` | `check_reference_unique_by_project` 的搜索约束包含 `project`、`reference` 且排除 cancel | 不满足全局键；ORM 搜索约束是否有并发竞态，及最小全局数据库约束方式 |
| `mymodules/worlddepot/models/outbound_order.py` | 当前未发现按全局 reference 排除 cancel 的唯一约束 | 有效出库单是否可能跨 project 同号或并发重复 |
| `mymodules/worlddepot/models/stocktake.py` | `count_order_no` 有索引，状态为 `new/cancel`；当前未发现有效全局唯一约束 | 有效盘点单是否可能跨 project 同号或并发重复 |
| `mymodules/ginlong_apis/idempotency.py` | 成功一次性请求按业务键历史查重；同指纹成功记录可返回保存的响应 | 如何优先检查当前有效对象，并在其失效后隔离新生命周期而不覆盖旧结果 |
| `mymodules/ginlong_apis/models/api_control.py` | 幂等唯一约束为 `(api_code,business_key,request_fingerprint)`；另有 `event_key` 字段 | 现有字段/索引能否用最小改动保留同键同指纹的多期历史；是否必须扩展字段尚未判断 |
| `mymodules/ginlong_apis/services.py:367` | API07 Add 用 `active_test=False` 检查同 owner+productCode 的任何变体，并查询历史成功幂等记录 | 归档记录应允许进入 Add，但由原记录恢复或创建新变体需要验证原生约束和历史关联 |
| `mymodules/ginlong_apis/services.py:439,464,570,688` | API01/03 删除及 API05 删除按业务号查询时未统一限定当前有效记录 | 多次 cancel/re-add 后 Delete 是否能准确定位唯一有效对象且忽略旧历史 |

以上仅是仓库代码阅读所得，不代表数据库数据或真实并发行为已验证。TV 执行时应记录实际源码版本及 ORM 证据。

## 4. TV 工作包

### TV-008-A：全局业务键与现有数据约束

**检查对象：** 入库、出库、盘点订单与产品变体模型；API01/03/05/07 Handler 和幂等入口。

**方法：**

1. 读取 Odoo 模型字段、约束元数据及实际 API 查询域，确认订单 Add、Delete、Edit 分支的业务键和状态使用情况。
2. 用 Odoo Shell ORM 只读统计全库有效记录的重复键，订单键分别只按 `inboundOrderNo`、`outboundOrderNo`、`countOrderNo` 汇总，不按 project 分组；产品按 `(owner, productCode)` 汇总 active 变体。
3. 只输出脱敏的键/记录计数和必要的内部证据。不得删除、取消、归档、合并或修改发现的存量记录。
4. 设计跨两个不同 project 的请求场景，验证同一有效订单号仍为全局冲突；同时核对调用方权限、返回内容不泄漏另一 project 的订单数据，新单据归属仍按 API User 既有 project。
5. Add 有效性判重按全库业务键；Delete 的目标选择仍受当前 API User/project 权限约束，不得借全局判重越权取消另一 project 单据。对同一权限范围内多条 cancel 历史和一条 active 记录，只命中 active；无 active 时按现有 Delete 契约记录，不补造语义。

**通过条件：** 全局查询键和错误映射不含 project；project 字段/归属/权限路径未被移除；存量重复键获得明确结果并可形成安全迁移门禁。

### TV-008-B：数据库级并发唯一性

**检查对象：** API01/03/05 有效订单键、API07 有效 owner+productCode 键，以及 Odoo 18 可支持的 ORM 管理约束方式。

**方法：**

1. 核实可否用模型持久字段/计算字段与 ORM 管理的数据库唯一约束表达“有效记录占有键、cancel/archive 后释放键、多个无效历史行并存”。比较现有约束、加字段方案及 Odoo 声明式约束能力，不预先指定实现。
2. 特别验证订单键约束必须全局，不含 project；API07 约束为 owner+productCode，允许不同 owner 的相同 productCode。
3. 在验证授权后，用 Odoo 标准自动化/HTTP 测试和独立事务并发触发相同业务键 Add，分别测相同和不同 Payload、同 project 和跨 project。观察提交结果、错误响应、业务记录数、幂等成功行和日志。
4. 验证一个事务获胜后，失败事务完整回滚，不产生部分业务数据或成功幂等结果；并发后有效记录数必须为 1。
5. 不用串行测试、进程内锁或单 Worker 结果替代并发证据；测试不执行 SQL/psql。若标准测试工具无法生成真实并发，明确 BLOCKED 并说明所需验证环境，不宣称通过。

**数据控制：** 计划获批后优先使用测试框架中的专用合成键与事务回滚。若真实多 Worker 验证必须产生已提交测试数据，先列明具体键、记录类型及 ORM 清理方式，并取得所需授权；本轮不创建这些数据。

### TV-008-C：API07 产品归档与原生变体唯一性

**检查对象：** `product.template`、`product.product`、Ginlong owner/product code 字段、原生变体约束和引用产品变体的库存/WMS 模型。

**方法：**

1. 核对实际安装的 Odoo 18 原生产品模型源码/元数据、`product.product` 的组合唯一性规则及 ginlong 扩展字段约束。
2. 只读检查代表性 active/archived product variant 的历史引用类型与数量：产品模板关系、库存 Lot/Move/Picking、WorldDepot 订单明细及其他引用 `product_id` 的记录；不修改或迁移数据。
3. 在获批的临时自动化事务中分别评估两种候选流程：恢复归档变体；保留归档行并创建新的 active 变体。核对 Add 完成后 `(owner,productCode)` 仅有一条 active 变体、原历史业务关系仍指向可识别记录、模板共享属性及 Odoo 原生变体规则不冲突。
4. 对同 productCode 的不同 owner 做边界检查，确保独立变体仍可存在；不新增映射模型。
5. 根据实际约束/历史引用提出最小选择；若两种方式都需要额外模型改造或可能改写历史业务关联，则列为 BLOCKED/需 Human Review，不自行决定。

**通过条件：** 形成有证据支持的归档后重加方案，明确影响的旧关联、需要的最小字段/约束调整及迁移风险；在此之前不冻结 API07 实现细节。

### TV-008-D：幂等生命周期与历史保留

**检查对象：** `mymodules/ginlong_apis/idempotency.py`、`ginlong.api.idempotency`、`idempotency_rules.json`、API01/03/05/07 控制器和服务。

**方法：**

1. 记录幂等模型现有字段、索引/唯一约束及 API01/03/05/07 的查询、重放、失败重试调用顺序；确认 API02/04/06/08/10 出站策略实际使用的同一字段行为。
2. 设计“首次 Add 成功 → 取消/归档 → 相同 Payload Add → 再次 Add”的受控测试，验证旧成功行保持不变、第二生命周期新 Add 不被拦截/不重放旧 response、后续有效重复 Add 被拒绝。
3. 在不预设新 `lifecycle_id` 的前提下，比较可行的最小方案：调整现有唯一约束/查询域、复用 `event_key` 或其他已存在身份字段、或确需增加的最小字段。对每个方案评估旧行无损迁移、相同 fingerprint 多生命周期并存、失败重试语义、并发 Add 及出站幂等回归。
4. 校验不能以更新/删除旧成功幂等行为新生命周期腾位；所有旧行、response 和 API 日志需保留。
5. 通过真实 HTTP 路由和 ORM 断言完整 Add→Cancel/Archive→Add 生命周期。此计划未授权运行测试。

**通过条件：** TV 报告提出一个明确、最小且兼容历史的建议，或列出无法在既有表上安全达成的限制；不把建议方案冒充已验证实现。

## 5. API 专项场景矩阵

| 对象 | 已有有效时同/不同 Payload Add | cancel/archive 后同 Payload | cancel/archive 后不同 Payload | 多生命周期历史 | 跨 project / owner | 并发 |
|---|---|---|---|---|---|---|
| API01 | 拒绝 | 允许新周期 | 允许新周期 | 原入库单、幂等和日志保留 | 同单号跨 project 仍冲突；project 归属/权限保持 | 相同键只一条 active |
| API03 | 拒绝 | 允许新周期 | 允许新周期 | 原出库单、幂等和日志保留 | 同单号跨 project 仍冲突；project 归属/权限保持 | 相同键只一条 active |
| API05 | 拒绝 | 允许新周期 | 允许新周期 | 原盘点指令、幂等和日志保留 | 同单号跨 project 仍冲突；project 归属/权限保持 | 相同键只一条 active |
| API07 | 拒绝 | 允许再次 Add；恢复/新建待 TV | 允许再次 Add；恢复/新建待 TV | 归档产品及历史业务关联保留 | 不同 owner 相同 productCode 允许并存 | 相同 owner+code 只一条 active |

## 6. 输入、证据和报告

### 预期输入

- 冻结中的 CC-GIN-008 有条件设计决定和本批准后的 TV 计划。
- 当前代码、Odoo 18 模型/约束元数据及本地 `odoo.conf` / `odooce_karlrapp` 环境。
- 专用测试数据需在计划批准后建立；不得访问生产、真实 Ginlong 或 KR Gateway。

### 证据

- 代码位置及当前分支/版本识别。
- ORM 模型字段、约束元数据和只读存量重复键统计。
- 经批准的 HTTP 响应、ORM 业务记录及幂等/API 日志差异证据。
- 实际并发事务结果、数据库约束冲突分类和回滚结果。
- API07 候选归档处理路径的 ORM 关联计数、模板/变体约束与历史关联结果。
- 不运行的项目标为 NOT RUN；环境或现有数据无法支持时标 BLOCKED；实际失败保留 FAIL，不降低标准。

### 预期交付报告

`docs/context/report/TV-GIN-008-v0.1.md`，至少包含：验证方法、代码/模型事实、四类业务键作用域、Odoo 变体归档结论、幂等最小修改比较、多事务并发证据、存量键冲突、风险、通过/有条件通过/未通过结论及 CC-GIN-008 v0.2 修订输入。

## 7. 验证顺序与停止条件

1. 先只读确认源码、Odoo Registry/约束及全局有效键存量情况。
2. 若现存全局有效重复键已存在，停止数据库唯一约束可行性结论，提交冲突摘要；不得清理记录。
3. 核对 API07 原生变体唯一性和历史引用，再评估归档重加候选方式；不写入持久业务记录。
4. 核对幂等历史模型并形成可回滚自动化场景；未获额外验证执行授权前，不提交或保留测试业务记录。
5. 经批准后才执行并发/事务验证；若无法在当前 Odoo 环境可靠地测试跨 Worker 行为，明确 BLOCKED 与所需环境条件。
6. TV 报告完成人工评审通过后，再据实际证据修订 SRS v1.3、TDD v1.6、Implementation Plan v2.1、CC-GIN-008 v0.2 及通用架构规范。不得先行把未验证方案写成已验证结论。

## 8. 计划评审与状态

| 项目 | 状态 |
|---|---|
| TV 执行授权 | Pending TV Plan Human Review；本轮未执行 TV |
| 业务代码、模块升级 | 未授权 |
| 数据修改/测试数据创建 | 未授权 |
| 生产/Ginlong/KR 访问 | 不在范围 |
| Git | 未操作 |
| Human Review | Pending |

## 9. 执行记录

项目负责人于 2026-11-24 批准冻结文档并进入 CC 实施；TV 按本计划执行并形成 `TV-GIN-008-v0.1.md`。ORM 存量检查与归档恢复验证结果均已附证据。多 worker 并发测试尚未执行，属于 CC-TEST-078/079 的实施验收，不由本计划静态结论替代。

模板同步仍 BLOCKED，沿用已批准流程例外，不标记 PASS。
