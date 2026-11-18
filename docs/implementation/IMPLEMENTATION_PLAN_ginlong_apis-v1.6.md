# Ginlong API 实施计划 v1.6

| 项目 | 内容 |
|---|---|
| 文档 | `IMPLEMENTATION_PLAN_ginlong_apis-v1.6` |
| 版本 | v1.6 |
| 状态 | Frozen |
| 基线有效性 | VALID；对应 SRS v1.0 Frozen、TDD v0.8 Frozen、项目认知 v2.4 |
| 项目 / 模块 | `ginlong_apis`，按需扩展既有 `worlddepot` |
| 计划负责人 | 李建强 |
| 日期 | 2026-11-18 |
| Human Review | APPROVED；李建强（项目用户）；2026-11-18；批准冻结 v1.6 并按 CC-GIN-004 v1.0 实施 |
| 模板同步 | BLOCKED：模板源缺失；沿用既有用户批准的例外，不伪记 PASS |
| 执行授权 | 本地开发、现有 Odoo 开发库 ORM 自动化和 Mock HTTP；不访问真实 Ginlong 或生产 |

> 本计划是 Implementation Plan v1.0 与 v1.1–v1.5 的补充版本，历史计划原件保留。本版本只将 API09 和 Ginlong 管理界面纳入阶段 3；不重开 CC-GIN-001–003。

## 1. 上游基线

| 输入 | 版本 / 状态 | 用途 |
|---|---|---|
| SRS | ginlong_apis v1.0 Frozen | 业务边界及 API09 字段；本计划不改写 SRS |
| TV | Ginlong TV v0.2 有条件通过 | 已有可复用 WMS/API 能力证据 |
| TDD | ginlong_apis v0.8 Frozen | API09 查询、数据来源、只读和管理界面技术约束 |
| 项目认知 | PROJECT_COGNITION v2.4 | 三系统职责与 owner/warehouse/product 库存维度 |
| CC-GIN-004 | v1.0 Frozen | API09 与 Ginlong 菜单/查询入口的执行契约 |
| 前序 CC | CC-GIN-001–003 Closed | 已通过范围不重复实现或重测 |

当前完整数据流是 Ginlong 下达指令 → Odoo 管理业务订单并转交 KR → KR WMS 执行现场作业 → Odoo 根据结果由 `stock.picking` 和原生库存机制记录 → Odoo 向 Ginlong 回传/响应查询。此 CC 不实现 KR 库存同步或仓库业务。

## 2. 目标与范围

### 2.1 本计划阶段 3 的目标

- 实现 Ginlong API09：按请求货主编码读取 `product.product.ginlong_owner_code` 与 `default_code`，读取当前唯一仓库内部库位下的现有 `stock.quant.quantity`，按实际物理库存数量返回，不扣 `reserved_quantity`。
- 维持 Ginlong API09 只读，不创建/修改库存或作业记录。
- 提供 Ginlong 管理入口：既有 API Settings、现有 API 日志查询、入库/出库/盘点/产品查询入口，以及失败日志到原记录的定位。

### 2.2 不在本计划范围

- 新建库存/订单/日志模型或通用映射框架；修改 Karl Rapp Gateway；执行库存同步、库存移动或调整。
- 自动回传、重试中心、监控平台或 API 启用开关。
- 浏览器人工 WMS 全流程验收（CC-GIN-005）或真实 Ginlong 环境联调（CC-GIN-006）。

### 2.3 固定技术约束

- 库存按 `(ownerCode, warehouseCode, productCode)` 区分；货主通过产品现有 `ginlong_owner_code` 识别。
- 当前只有一个 Odoo 仓库，不做 Ginlong 仓库编码映射；查询该唯一仓库的内部库位。未来若扩为多仓，按 Ginlong 要求扩展现有仓库模型，不建映射模型。
- 当前开发库没有内部 `stock.quant`；测试可通过 ORM 使用清楚标记的模拟库存数据，模拟结果只证明查询组件，不证明 KR→Odoo 库存同步。
- 失败日志使用现有 `world.depot.api.log`，增加 Ginlong 业务记录 Reference 关联字段；日志只读权限复用 `stock.group_stock_manager`，不增加用户组。
- 使用 `odoo.conf`、项目 `venv` 和数据库 `odooce_karlrapp`；禁止直接 PostgreSQL/SQL，禁止 `stock_barcode`。不调用真实 Ginlong/生产。

## 3. 前置条件及环境

| 前置条件 | 状态 / 证据 | 处置 |
|---|---|---|
| SRS、TDD、Plan、CC 冻结 | SRS v1.0、TDD v0.8、Plan v1.6、CC-GIN-004 v1.0 已批准 | 满足 |
| Odoo 运行环境 | 复用现有 `odoo.conf`、`venv`、`odooce_karlrapp` | 不建隔离环境；只通过 Odoo ORM 操作数据库 |
| WMS/库存数据 | 开发库内部 quants 为 0；仅一个仓库 `KRWH / KarlRapp-WH`；产品 owner 字段已注册 | 自动化测试用明确标注模拟 quant；不得宣称真实同步验证 |
| 外部网络 | 真实 Ginlong 与生产端点无授权 | 只使用 Mock HTTP |
| 文档模板同步 | 源模板缺失，状态 BLOCKED | 按已批准例外继续，不标为 PASS |

## 4. 实施阶段和门禁

### 阶段 3A：API09 只读库存查询（CC-GIN-004 v1.0）

**交付物：** Ginlong API09 POST JSON endpoint；使用现有认证及日志；按 owner 产品身份和唯一仓库查询 `stock.quant.quantity`；响应遵循 V3.2；严格只读。

**验收门禁：** CC-TEST-025–033 自动化/ORM 通过；跨货主相同 productCode 不合并；数量不扣预留；模拟数据标识清楚；请求前后库存/作业数据不变。当前无真实 KR 同步证据需继续标注 NOT VERIFIED，不阻塞 API09 组件验收。

### 阶段 3B：Ginlong 管理界面（CC-GIN-004 v1.0）

**交付物：** Ginlong 根菜单；复用现有 Settings；现有 API 日志的 Ginlong 筛选；入库、出库、盘点和产品查询入口；日志业务记录引用、失败日志定位；管理员组/库存管理员组按 CC 设置既有权限。

**验收门禁：** CC-TEST-034–040 自动化及组件集成通过；原有 WMS 菜单/权限不回退；通过 `stock.group_stock_manager` 只读 ACL 查阅历史日志；失败日志可以打开来源记录。

### 阶段 4：本地集成及完整 UI/WMS E2E（CC-GIN-005）

完整用户界面流程、WMS 实际作业与 Ginlong 本地集成回归留待后续 CC；不要求 CC-GIN-004 执行人工完整 E2E。

### 阶段 5：真实 Ginlong 环境联调（CC-GIN-006）

需要正式测试环境、外部凭据/端点授权与确认后的契约。当前不在本 CC 执行。

## 5. 阶段顺序与依赖

```text
阶段 3A API09 只读查询 ─┐
                         ├─ CC-GIN-004 组件验收
阶段 3B 管理界面 ────────┘
        ↓
阶段 4 CC-GIN-005 本地完整 UI/WMS E2E
        ↓
阶段 5 CC-GIN-006 Ginlong 测试环境联调（另行授权）
```

API09 查询与管理 UI 可在同一 CC 内并行开发，但共享日志扩展及菜单依赖应先稳定；CC-GIN-005/006 不得提前合并到 CC-GIN-004。

## 6. 验收与追溯

| 需求/设计 | 计划阶段 | 验收方式 | CC |
|---|---|---|---|
| SRS FR-GIN-009：库存查询 | 3A | ORM 自动化/组件测试；Owner、唯一仓库、产品编码、完整列表及响应契约 | CC-GIN-004 CC-TEST-025–033 |
| TDD API09 只读、防止库存副作用 | 3A | 模拟库存查询后量化 ORM 数据快照一致；不写 quant/move/picking | CC-GIN-004 CC-TEST-031/032 |
| 复用认证和日志 | 3A/3B | 认证回归、API 日志追加与凭据检查 | CC-GIN-004 CC-TEST-026/033/036 |
| 管理菜单/设置/业务查询/失败定位 | 3B | Odoo 自动化与组件视图/action 断言 | CC-GIN-004 CC-TEST-034–040 |
| 全链路 WMS/E2E | 4 | 浏览器人工 E2E 与 WMS 实际流程 | 拟建 CC-GIN-005 |
| 外部 Ginlong 联调 | 5 | 获得授权后对测试环境逐接口验证 | 拟建 CC-GIN-006 |

## 7. 验证策略与交付物

- Odoo 模块自动化测试：`TransactionCase`/HTTP Test Client，按 CC 覆盖路由、认证、只读、汇总、跨货主隔离、日志和菜单 action。
- ORM Runtime 核验：使用 Odoo Shell，仅走 ORM；确认安装/升级后的字段、权限、配置与数据行为。
- API09 数据：无真实库存时用测试夹具创建模拟库存记录并自动清理/回滚；不把测试值写入业务环境后冒充 KR 同步。
- 不执行浏览器全流程或真实 HTTP 联调；分别追踪到 CC-GIN-005/006。
- IHR、ATR 按运行追加；失败/Blocked/Not Run 保留。关闭时再按证据形成 FR 并提交 Human Review。

## 8. 风险和处置

| 风险 | 影响 | 处置 |
|---|---|---|
| Odoo 中没有 KR 同步库存 | 无法用开发库实际库存证明同步链路 | 以标记明确的 ORM 模拟数据验收 API09 代码；真实数据来源留后续本地集成/联调，不宣称通过 |
| 用户请求跨货主同码 | 发生错误合并 | 必须按 `ginlong_owner_code + default_code` 定位产品 |
| API 日志错误授权或丢失关联 | 暴露日志内容或无法定位失败源单 | 复用 `stock.group_stock_manager` 只读 ACL，添加现有日志 Reference 字段并验证打开来源记录 |
| 多仓库未来引入 | 单仓库查询范围需扩展 | 到时按 Ginlong 要求扩展现有仓库字段，重新评估并更新 TDD/Plan/CC |
| 模板源缺失 | 无法通过同步校验 | 保留 BLOCKED 状态和已批准例外，不伪记通过 |

## 9. 批准与修订记录

| 版本 | 日期 | 变更 | 状态 |
|---|---|---|---|
| v1.0 | 2026-11-17 | 原计划基线，保持历史不变 | Frozen |
| v1.1–v1.5 | 2026-11-18 | 执行补充及 CC-001–003 状态；原文保留 | 历史 |
| v1.6 | 2026-11-18 | 纳入 API09 实际物理库存与单仓库边界、模拟测试限制、Ginlong 管理 UI 和 CC-GIN-004/005/006 阶段映射 | Frozen；Human Review APPROVED |
