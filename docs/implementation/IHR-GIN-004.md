# 实施历史记录：IHR-GIN-004

| 字段 | 值 |
|---|---|
| IHR 版本 | v1.0 |
| 冻结实施基线 | [CC-GIN-004 v1.0](CC-GIN-004-v1.0.md)；[TDD v0.9](../ginlong_apis/TDD-v0.9.md)；Plan v1.6 范围基线 |
| 当前状态 | CC-GIN-004 Closed；[关闭记录](CC-GIN-004-v1.1.md)；[FR-GIN-004 v1.0](FR-GIN-004.md) |
| 最终代码基线 | `3a7ec9c2de954cd1c88fd6c3d598c75b167ad4fe` |

## 0. 文档治理

本记录追溯 [CC-GIN-004 v1.0 Frozen](CC-GIN-004-v1.0.md) 的本地实施。上游冻结文件不被覆盖；测试证据及历史失败见 [ATR-GIN-004](ATR-GIN-004.md)。

## IHR-001 — 冻结基线及授权

- **阶段：** Baseline / Authorization
- **基线：** Implementation Plan v1.6、TDD v0.8、CC-GIN-004 v1.0 均由 Human Review APPROVED 并冻结。CC 范围为 API09 只读库存查询和 Ginlong 管理界面。
- **授权：** 本地开发、既有 Odoo 开发库 ORM 自动化及 Mock HTTP。未获真实 Ginlong 或生产环境访问授权。
- **既有约束：** 使用既有 `venv`、`odoo.conf`、`odooce_karlrapp`；数据库操作只经 Odoo ORM；不使用 `stock_barcode`；不重做 CC-GIN-001–003 已通过的行为。

## IHR-002 — API09 只读库存查询

- **阶段：** Implementation / Odoo automated verification
- **Action：** 在 `ginlong_apis` 增加 `/api/ginlong/TPL_Stock_Query` POST JSON 路由，复用 `worlddepot` Token 验证与 API logger。服务要求 `owner`、`warehouse` 两个不超过 40 字符的字符串；当前仅一个本地 Odoo 仓库，因此查询其内部库位的现有 `stock.quant`，按产品 `ginlong_owner_code + default_code` 区分，汇总 `quantity` 并返回 V3.2 字段；响应原样回显请求的 owner/warehouse。没有新增 Ginlong 仓库编码映射。
- **边界：** 只读，不写 quant、不创建 move、不扣除预留量。没有分页、产品过滤参数或协议外数量字段。响应数量为 JSON number，数据库实际可读精度受 Odoo UoM 规则影响。
- **测试证据：** ATR-RUN-008 最终 Ginlong 35 post-tests、0 failed / 0 error；覆盖路由/请求字段、owner 隔离、相同 productCode 跨 owner、多内部库位汇总、预留量不扣减、空结果、只读快照、现有 Token/logger、异常日志。
- **数据边界：** ORM 核验当前开发库仅有一个 warehouse、内部 quant 为 0。API09 自动化使用事务内 ORM 模拟库存；此结果不证明 Karl Rapp→Odoo 库存同步。

## IHR-003 — Ginlong 管理入口、日志定位与权限

- **阶段：** Implementation / view and ORM integration verification
- **Action：** 增加 Ginlong 根菜单，入口复用现有 Settings；增加现有 API Settings、API 日志、入库单、出库单、盘点单、产品的查询 Action。没有增加 API01–10 启用开关、独立监控或重发中心。
- **日志定位：** 在既有 `world.depot.api.log` 上增加一个 `Reference` 来源单据字段，支持入库单、出库单、盘点单和产品；现有五个 Odoo 回传按钮写入来源引用。新日志行追加，不修改历史日志。没有来源单据的失败请求引用为空。
- **权限：** Ginlong API 日志由现有 `stock.group_stock_manager` 只读查看；Settings 使用 `base.group_system`；业务记录查询复用 `stock.group_stock_user`。未新建用户角色体系。
- **测试证据：** ATR-RUN-008 覆盖菜单/Action、设置入口、Ginlong 日志筛选、只读 ACL、Reference 导航、无来源失败日志和四类业务查询入口。
- **人工交互范围：** 未执行浏览器人工 UI/WMS E2E；该部分由 CC-GIN-005 承接。

## IHR-004 — 回归、运行态及工作区验证

- **阶段：** Odoo automated regression / ORM verification
- **回归：** ATR-RUN-005 在既有 `odooce_karlrapp` 执行 `worlddepot` 8 个 post-tests，0 failed / 0 error，覆盖 Token/认证/日志、敏感信息保护、盘点订单/实盘结果既有关系。
- **运行态：** Odoo Shell ORM 确认 Ginlong addon `18.0.2.0.7` installed、日志 Reference 字段类型正确、经理只读 ACL 和单仓数据状态；测试后无测试产品或订单残留。完整输出摘要及边界见 ATR §4。
- **静态检查：** Python 编译、模块 XML 解析和 `git diff --check` 均通过。未发现 `stock_barcode` 依赖；测试进程结束后无遗留本地监听服务。
- **失败历史：** 首轮模块测试的夹具/测试替身错误、精度断言错误及一次缺少测试摘要的运行均保留在 ATR-RUN-001–003、006；后续运行验证通过，没有通过修改业务规则掩盖失败。

## IHR-005 — 评审状态与后续承接

- **结果（当时记录）：** CC-TEST-025–040 的本地自动化/组件验证均达到冻结要求；API09 库存数据覆盖明确为模拟 ORM 数据。该条记录提交评审时尚未生成关闭 FR；最终关闭决定及状态见 IHR-008。
- **Open / Not Run：** 模板同步因模板源缺失保持 BLOCKED，沿用批准的流程例外；真实 Ginlong 和生产访问未执行；完整浏览器 UI/WMS 人工 E2E 未执行；真实 KR 库存同步未验证。
- **后续 CC：** CC-GIN-005 承接完整本地 UI/WMS 集成与人工 E2E；CC-GIN-006 在另行授权后承接真实 Ginlong 环境联调。

## IHR-006 — API09 货主/仓库双维隔离补充验收

- **阶段：** User-directed acceptance supplement / Odoo automated verification
- **依据：** CC-GIN-004 冻结后，用户补充要求：未知 warehouse code 不得返回其他仓库存量；未知 owner code 不得返回其他货主库存；并要求覆盖缺失/不存在、无库存、40 字符边界及双货主×双仓组合。该补充作为后续指令执行并留证；CC-GIN-004 v1.0、TDD v0.8 和 Plan v1.6 历史冻结文件未被覆盖。
- **源码核对：** Odoo ORM 确认 `res.partner.ginlong_owner_code` 是索引 Char；`stock.quant.owner_id` 是指向 `res.partner` 的 Many2one；`stock.warehouse.code` 是现有短码 Char，长度 5，当前值 `KRWH`。Ginlong API09 请求 `warehouse` 字段允许 40 字符；对端编码与本地短码是否相同仍未确认，不能以 `stock.warehouse.name` 代替。
- **实现：** API09 先按 `res.partner.ginlong_owner_code` 找货主，再用对应 partner ID 限定 `stock.quant.owner_id`；不存在 owner 时返回空清单。仓库按 `stock.warehouse.code` 精确匹配，未知 code 作为请求错误返回，不再把请求无条件映射到唯一仓库。未增加映射模型或库存写逻辑；重复 owner code 无法唯一定位时拒绝查询。
- **自动化：** ATR-RUN-010 运行 Ginlong 37 post-tests，0 failed / 0 error。覆盖 12 类输入、四组合 OWNER-A/OWNER-B × WH-A/WH-B、未知 owner/warehouse、存在 owner 无库存及双未知组合。未知 warehouse HTTP 组件场景在合法仓库已有库存夹具下返回 HTTP 400 且不含 `inventoryList`；未知 owner 在其他 owner 有库存时返回空列表。
- **数据边界：** ORM 核验没有重复 Ginlong owner code，测试后没有 `Ginlong API09 matrix` 产品残留；开发库真实内部 quant 仍为 0。库存隔离证明基于事务内模拟数据，不代表 KR 同步已经验证。
- **限制/Open Item：** 本地仓库编码是 5 字符短码，Ginlong warehouse 字段允许 40 字符。自动化证明短码完全匹配时的仓库隔离；未证明任意 Ginlong 码可与本地短码对应。需要确认实际对端仓库码与现有短码相同且满足长度，或批准在现有仓库模型增加可保存 Ginlong 编码的字段，之后再验证相应输入。
- **Result：** 新增 12 类本地隔离自动化通过；不据此将 Ginlong 外部仓库编码兼容或 CC-GIN-004 正式关闭标为 PASS。

## IHR-008 — 项目负责人补充决策及 CC-GIN-004 关闭

- **阶段：** Project Owner decision / closure
- **授权：** 项目负责人于 2026-11-18 明确授权关闭 CC-GIN-004 并提交、推送 Git；此前明确要求货主编码使用 `res.partner.ginlong_owner_code` 并经 `stock.quant.owner_id` 隔离库存，单仓库不建编码映射，未来多仓按 Ginlong 要求扩展现有仓库模型。
- **数据来源决议：** API09 owner 由 `res.partner.ginlong_owner_code` 定位，并以其 ID 限定 `stock.quant.owner_id`；未知 owner 返回空清单。warehouse 按现有 `stock.warehouse.code` 精确匹配；未知 warehouse 报错，不回退到唯一仓库。CC-TEST-041–043 对未知仓库、未知货主及双货主×双仓矩阵均有 PASS 证据。TDD v0.9 记录这一后续明确的技术数据来源，v0.8 保留为历史冻结版本。
- **最终证据：** CC-TEST-025–040 均 PASS；用户追加的 CC-TEST-041–043 也 PASS。ATR-GIN-004 RUN-010 记录 37 个 Ginlong post-tests、0 failed/0 error；最终代码基线的完整 Ginlong 套件见 ATR-GIN-003 RUN-055，共 40 个 post-tests、0 failed/0 error；`worlddepot` 受影响回归为 8 个 post-tests、0 failed/0 error。Odoo Shell ORM 核验模块 `18.0.2.0.9`、字段及权限已注册；语法、XML 和 `git diff --check` 通过。
- **实施基线：** `3a7ec9c2de954cd1c88fd6c3d598c75b167ad4fe`。最终 FR 和 CC 关闭状态记录随后的文档提交，不改变被测代码。
- **保留项：** 模板同步仍 BLOCKED，按既有用户批准例外保留，不记 PASS；浏览器 UI/WMS 人工 E2E 交 CC-GIN-005；真实 Ginlong、生产及 Karl Rapp 库存同步未执行，交 CC-GIN-006/后续集成确认。当前 `stock.warehouse.code` 是 5 字符短码，自动化只证明本地匹配与未知码隔离，不宣称任意 Ginlong 仓库码已联调兼容。
- **结果：** 用户授权 CC-GIN-004 Closed；FR-GIN-004 v1.0 Closure SATISFIED，Human Review APPROVED。CC-GIN-004 v1.0 冻结验收基线保留，v1.1 只记录补充决定及关闭状态。

## IHR 版本记录

| 版本 | 日期 | 说明 | 状态 |
|---|---|---|---|
| v0.1 | 2026-11-18 | 建立 CC-GIN-004 实施历史和运行证据 | Ready for Human Review |
| v0.2 | 2026-11-18 | 追加货主/仓库隔离测试及 API01/03 项目认知记录 | Ready for Human Review |
| v1.0 | 2026-11-18 | 追加项目负责人数据来源决议及正式关闭证据；保留模板、E2E 和真实联调未完成状态 | Closed |

## IHR-007 — API01/API03 货主与产品处理规则登记

- **阶段：** Project cognition update / future scope trace
- **来源：** 用户确认 API01 入库单按 owner code 查找 `res.partner.ginlong_owner_code`，有则复用、无则创建并关联入库单；API03 出库单必须先找到货主，并逐行按 `owner + productCode` 找现有产品，缺失则拒绝并记录业务错误，不自动创建产品，产品资料由 API07 维护。
- **Action：** 更新 [PROJECT_COGNITION.md v2.8](../context/cognition/PROJECT_COGNITION.md)。本次 CC-GIN-004 只覆盖 API09 和管理界面，没有修改 API01/API03 代码；相关实施需纳入后续获批 CC。
- **Result：** 已作为项目认知保存；CC-GIN-004 测试范围不扩大。
- **后续记录：** 上述内容是当时状态。API01/API03 随后经项目负责人单独授权实施，见 [IHR-GIN-003 IHR-021](IHR-GIN-003.md)；这部分不计入 CC-GIN-004 的关闭义务。

## 实际变更清单

| 文件 / 组件 | 变更 | 验收追溯 |
|---|---|---|
| `mymodules/ginlong_apis/services.py` | API09 owner/仓库内部库位查询及响应构造；只读汇总 `stock.quant.quantity` | CC-TEST-027–032 |
| `mymodules/ginlong_apis/controllers/ginlong_controller.py` | API09 POST 路由，复用 Token 验证、API 日志 | CC-TEST-025/026/033 |
| `mymodules/ginlong_apis/models/api_log.py` | 扩展既有 API 日志来源 Reference 与打开来源动作 | CC-TEST-036–039 |
| `mymodules/ginlong_apis/models/ginlong_callbacks.py` | 新增回传日志的源业务单据关联 | CC-TEST-038 |
| `mymodules/ginlong_apis/security/ir.model.access.csv` | 现有日志模型的库存管理员只读 ACL | CC-TEST-037 |
| `mymodules/ginlong_apis/views/ginlong_management_views.xml` | Ginlong 菜单、设置、日志和业务查询 Action/视图 | CC-TEST-034–040 |
| `mymodules/ginlong_apis/tests/test_ginlong_api.py` | API09、菜单/Action/权限/日志引用自动化覆盖 | CC-TEST-025–040 |
| `docs/context/cognition/PROJECT_COGNITION.md` | 记录 v2.8 的 API01/03 货主产品规则及 API09 owner/warehouse 隔离认知 | 项目认知记录 |

## 附录：版本记录

| 版本 | 日期 | 说明 | 状态 |
|---|---|---|---|
| v0.1 | 2026-11-18 | 初次记录 CC-GIN-004 冻结基线、实施、自动化/ORM 证据及后续 CC 移交 | Ready for Human Review |
| v0.2 | 2026-11-18 | 追加 IHR-006 用户补充的 API09 十二类隔离测试与仓库编码长度限制；追加 IHR-007 API01/API03 规则认知，不扩大本 CC 代码范围 | Ready for Human Review |
