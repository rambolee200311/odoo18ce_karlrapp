# 自动化测试记录：ATR-GIN-004

## 0. 文档治理

本 ATR 记录 [CC-GIN-004 v1.0 Frozen](CC-GIN-004-v1.0.md) 的本地实施和自动化/组件验证证据，以及 v1.1 关闭补充。不覆盖冻结 CC v1.0、TDD v0.8 历史原件或 Implementation Plan v1.6 原计划；当前 API09 数据来源修订见 TDD v0.9，阶段状态见 Plan v1.7。测试仅使用 Odoo 自动化、ORM 模拟记录及本地组件请求；没有访问真实 Ginlong、生产环境或 Karl Rapp WMS。

## 1. 执行元数据

| 字段 | 值 |
|---|---|
| ATR | ATR-GIN-004 v1.0 |
| IHR | [IHR-GIN-004](IHR-GIN-004.md) |
| CC | [CC-GIN-004 v1.0 Frozen](CC-GIN-004-v1.0.md) |
| Module | `ginlong_apis`；依赖现有 `worlddepot`、Odoo `stock` |
| Environment | Odoo 18；既有项目 `venv`、`odoo.conf`、数据库 `odooce_karlrapp` |
| Test Framework | Odoo 标准 test runner / `TransactionCase`；Odoo Shell ORM 只读核验 |
| 当前模块版本 | `ginlong_apis` `18.0.2.0.9`，installed；见 ATR-GIN-003 RUN-053 ORM |
| ATR-RUN-010 源指纹 | SHA-256 聚合值 `25d0228d5e2fb3cdec862e1d8eb7ce26ea307ec874d2ca5673a352a34c4f4f6d`；v0.2 当时 `mymodules/ginlong_apis` 下 19 个 Python/XML/CSV 源文件 |
| 当前代码基线 | `3a7ec9c2de954cd1c88fd6c3d598c75b167ad4fe`；最终全量运行见 ATR-GIN-003 RUN-055 |
| 执行者 | Codex |

测试使用现有数据库和环境。所有数据库核验及测试夹具均经 Odoo ORM；未使用 `psql`、数据库驱动或直接 SQL。没有添加、安装或启用 `stock_barcode`。组件模拟库存不能证明 Karl Rapp 库存同步已完成。

## 2. 冻结验收矩阵

| CC-TEST | 覆盖内容 | 结果 | 证据与边界 |
|---|---|---|---|
| 025 | API09 POST JSON route、Object ID、必填 `owner`/`warehouse` 与长度校验 | PASS | route 元数据、必填和格式用例由 Ginlong 最终套件覆盖；组件验证，不是外部 HTTP 联调 |
| 026 | 复用 `worlddepot` Token validator 与 API logger；无效 Token 不执行库存服务 | PASS | API09 route 组件用例检查既有装饰器；无效 Token 被拒绝；未访问 Ginlong |
| 027 | `owner` 编码找到 `res.partner` 并匹配 `stock.quant.owner_id`；`warehouse` 编码匹配 `stock.warehouse.code` | PASS（代码字段限制见 §6） | 双货主/双仓 ORM 交叉夹具；没有使用 Contact Name、仓库显示名称或映射表 |
| 027 | 现有字段读取：owner 编码找到 `res.partner`，以其 ID 匹配 `stock.quant.owner_id`；warehouse 以编码匹配现有 `stock.warehouse.code` | PASS | 双货主/双仓夹具和 ORM 查询覆盖；不使用 Contact Name、`stock.warehouse.name` 或映射表 |
| 028 | 相同 productCode 的跨货主隔离 | PASS | 模拟两个 owner 使用同一 `default_code`，量化库存行按 partner-backed `owner_id` 分开返回，没有跨货主合并 |
| 029 | V3.2 响应字段和 JSON 类型 | PASS | 响应只含批准字段；`quantity` 为 JSON number；实际来源受 Odoo UoM 精度约束 |
| 030 | 指定 owner 的完整产品清单；无分页和 productCode 请求过滤 | PASS | 多产品与空结果组件用例通过；请求只使用 owner、warehouse |
| 031 | 实际物理数量口径，汇总 `stock.quant.quantity`、不扣 reserved | PASS（模拟 ORM） | 模拟不同内部库位和预留量，核对物理数量汇总及跨货主隔离。开发库实有内部 quant 数为 0；未验证 KR→Odoo 同步，不能宣称已验证真实库存 |
| 032 | API09 严格只读 | PASS（模拟 ORM） | 调用前后 quant 快照和 stock.move 数一致；没有调用写库存/调整/过账路径 |
| 033 | 现有日志、凭据保护和异常记录 | PASS（组件） | 验证日志装饰器、请求结果记录及输入错误日志；无效入站请求不伪造来源单据 |
| 034 | Ginlong 菜单及现有 Settings/业务查询入口 | PASS（视图/Action 自动化） | 检查菜单、父菜单、Action、模型和用户组；没有执行浏览器人工 E2E |
| 035 | 现有 API Settings 入口 | PASS（视图/Action 自动化） | 菜单进入现有 `res.config.settings`，沿用 Ginlong 既有 Endpoint/限流配置，无新增接口启用开关 |
| 036 | Ginlong API 日志查询、只读展示 | PASS（视图/Action 自动化） | 验证日志筛选域、列表/Form 和禁止创建/修改/删除配置 |
| 037 | API 日志访问 ACL | PASS（ORM ACL） | `stock.group_stock_manager` 有只读权限；普通内部用户及 stock user 无读取权限；不新增角色 |
| 038 | 失败回传日志定位源单据 | PASS（组件/ORM） | 现有回传各次日志追加来源 Reference；测试通过日志动作打开原业务单据；修正后沿用原单据按钮，不建重发中心 |
| 039 | 入站失败且无业务单据 | PASS（组件/ORM） | 失败请求日志的 `source_record` 留空；不创建伪造订单链接 |
| 040 | 入库、出库、盘点、产品查询入口 | PASS（视图/Action 自动化） | 使用现有业务模型和对应 Action；不改原 WMS Action/业务方法 |
| 041 | 未知仓库编码不返回其他仓库存量 | PASS（API route 组件） | 已有仓库有库存时，未知 code 返回 HTTP 400、无 `inventoryList`，失败日志追加；路由不回退到唯一仓库 |
| 042 | 未知货主编码不返回其他货主库存 | PASS（ORM 服务） | 其他 owner 在同仓有库存时，请求不存在的 owner code 返回 `inventoryList: []` |
| 043 | 双货主×双仓库交叉隔离 | PASS（ORM 服务） | 两个 owner、两个 warehouse、重复 `P001` 及四组库存分别返回 100/200/300/400；包含存在但无库存 owner、未知 owner、未知 warehouse 及双未知组合 |

### 用户补充的 API09 12 类组合

| # | 请求组合 | 实际覆盖 | 结果 |
|---:|---|---|---|
| 01 | 存在 owner + 存在 warehouse | 有库存正常返回 | PASS |
| 02 | 不存在 owner + 存在 warehouse | 其他 owner 有库存，目标返回空清单 | PASS |
| 03 | 存在 owner + 不存在 warehouse | 有库存的合法请求后调用未知 code；HTTP 400、无库存字段 | PASS |
| 04 | 不存在 owner + 不存在 warehouse | ORM 调用返回校验错误，无数据 | PASS |
| 05 | 存在但该仓无库存的 owner + 存在 warehouse | 返回 `inventoryList: []` | PASS |
| 06 | OWNER-A + WH-A | 只返回 A/A 的 P001=100 | PASS |
| 07 | OWNER-A + WH-B | 只返回 A/B 的 P001=200 | PASS |
| 08 | OWNER-B + WH-A | 只返回 B/A 的 P001=300 | PASS |
| 09 | 缺失/空 owner + 存在 warehouse | 必填校验失败 | PASS |
| 10 | 存在 owner + 缺失/空 warehouse | 必填校验失败 | PASS |
| 11 | owner 超过 40 字符 + 存在 warehouse | 格式校验失败 | PASS |
| 12 | 存在 owner + warehouse 超过 40 字符 | 格式校验失败 | PASS |

第 06–08 项用于交叉过滤；第 04 项覆盖双未知输入。额外的 OWNER-B + WH-B 返回 P002=400 也通过。夹具使用本地 `stock.warehouse.code` 短码；这不是 Ginlong 长仓库编码映射的联调证据。

## 3. 运行历史（仅追加）

| Run | 时间（UTC） | 执行 | 结果 | 处理 |
|---|---|---|---|---|
| ATR-RUN-001 | 2026-11-18，初始尝试 | Odoo runner 启动 | BLOCKED：受限运行环境拒绝连接配置中的本地 Odoo 数据库端口，测试未启动 | 保留；随后使用已授权本机运行路径，不改 DB/配置 |
| ATR-RUN-002 | 2026-11-18，初次有效启动 | Ginlong 标准测试，35 post-tests | FAIL：0 failed、2 errors；错误来自测试库存产品未设为可储存及日志组件测试替身断言 | 保留错误证据；修正测试夹具/替身，不改认证及业务规则 |
| ATR-RUN-003 | 2026-11-18，后续运行 | Ginlong 标准测试 | PARTIAL：进程退出码为 0，但使用 error-only 日志配置没有可核验的测试数量和结果摘要 | 不计 PASS；改用 info 级 Odoo test runner 摘要 |
| ATR-RUN-004 | 2026-11-18 10:04:47 | Ginlong 标准测试，35 post-tests | PASS：0 failed、0 error | 当时有效运行；后续测试断言扩展后由 RUN-008 作为最新代码结果 |
| ATR-RUN-005 | 2026-11-18 10:05:57 | `worlddepot` 回归，8 post-tests | PASS：0 failed、0 error | 覆盖 API Token/认证日志、敏感信息保护、非认证业务日志和盘点客户指令/实盘关系；日志 `debug_logs/odoo_181.log`，PID 68649，行 21500–21512 |
| ATR-RUN-006 | 2026-11-18 10:07:26 | Ginlong 标准测试，35 post-tests | FAIL：1 assertion failure；Odoo ORM UoM 精度把测试数量 7.125 归整为 7.13 | 保留失败；测试期望改为 ORM 实际存储/读取精度，没有降低字段或库存行为要求 |
| ATR-RUN-007 | 2026-11-18 10:08:14 | Ginlong 标准测试，35 post-tests | PASS：0 failed、0 error | 修正精度断言后的有效运行；日志 `debug_logs/odoo_181.log`，PID 68815，行 25087–25089 |
| ATR-RUN-008 | 2026-11-18 10:08:57 | Ginlong 最终标准测试，35 post-tests | PASS：0 failed、0 error | 最新有效运行；包括菜单/Action/domain、日志 ACL、来源单据导航与无来源错误日志断言；日志 `debug_logs/odoo_181.log`，PID 68895，行 26866–26868 |
| ATR-RUN-009 | 2026-11-18 10:23:12 | 用户补充未知 owner/warehouse 测试后的 Ginlong 标准测试，36 post-tests | PASS：0 failed、0 error | 未知 owner 返回空库存；未知 warehouse 在有现存库存时返回 400；日志 `debug_logs/odoo_181.log`，PID 70018，行 28950–28952。随后用户要求改为 partner→owner_id 并补齐双仓矩阵，由 RUN-010 取代 |
| ATR-RUN-010 | 2026-11-18 10:27:40 | 按 partner→owner_id 和双货主/双仓矩阵修正后的 Ginlong 标准测试，37 post-tests | PASS：0 failed、0 error | 覆盖 12 类输入、四组交叉库存、未知 owner/warehouse 隔离；日志 `debug_logs/odoo_181.log`，PID 70278，行 31035–31037 |
| ATR-RUN-011 | 2026-11-18 11:07:15 | 最终 `ginlong_apis` 全量标准套件，40 post-tests | PASS：0 failed、0 error | 最终源代码即当前代码提交 `3a7ec9c2de954cd1c88fd6c3d598c75b167ad4fe`；本运行已作为 ATR-GIN-003 RUN-055 记录，原始日志 `/private/tmp/ccgin_api01_api03_full_r3.log`。CC-TEST-025–043 均由当前套件覆盖；未因关闭阶段重复运行 |

### 可复现命令

Ginlong 最终测试：

```sh
venv/bin/python odoo-bin -c odoo.conf -d odooce_karlrapp --test-enable --test-tags /ginlong_apis --stop-after-init --http-port=0 --gevent-port=0 --log-level=info --log-handler=odoo.tests:INFO -u ginlong_apis
```

`worlddepot` 受影响回归：

```sh
venv/bin/python odoo-bin -c odoo.conf -d odooce_karlrapp --test-enable --test-tags /worlddepot --stop-after-init --http-port=0 --gevent-port=0 --log-level=info -u worlddepot
```

以上命令使用 Odoo 标准运行器；未直接访问 PostgreSQL。

## 4. ORM 运行态核验

在最终自动化后通过 `odoo shell -c odoo.conf` 对既有 `odooce_karlrapp` 执行只读 ORM 核验：

- ATR-RUN-010 基线时 `ginlong_apis` 为 installed `18.0.2.0.8`；最终提交对应 installed `18.0.2.0.9` 由 ATR-GIN-003 RUN-053 的 Odoo Shell ORM 核验。
- `res.partner.ginlong_owner_code` 是索引 Char；`stock.quant.owner_id` 是 `res.partner` Many2one；`stock.warehouse.code` 是长度 5 的 Char。
- 当前本地仓库是 `KRWH / KarlRapp-WH`；货主编码没有重复记录。
- `world.depot.api.log.source_record` 类型为 `reference`；只读访问核验：stock manager 允许，普通内部用户/stock user 不允许。
- ORM 核验当前开发库内部 `stock.quant` 数为 0。
- 空库存查询返回完整规定响应字段、请求 owner/warehouse 和空 `inventoryList`。
- 测试专用产品和订单残留均为 0。

此核验不能证明外部库存同步、真实 Ginlong HTTP 或浏览器 UI 行为。模块升级/ORM 验证没有启动长期监听服务；本地监听端口检查无遗留进程。

## 5. 结构和工作区检查

| 检查 | 结果 |
|---|---|
| Python `compileall` | PASS |
| Ginlong 模块 XML 使用 lxml 解析 | PASS |
| `git diff --check` | PASS |
| 新增 `stock_barcode` 依赖或使用 | 未发现 |
| 真实 Ginlong/生产 HTTP | NOT RUN；未授权 |
| 浏览器人工 UI/WMS E2E | NOT RUN；由 CC-GIN-005 承接 |
| Ginlong/Karl Rapp 真实库存同步 | NOT RUN；开发库无内部库存记录，不声称通过 |
| 模板同步 | BLOCKED：模板源缺失；沿用已批准例外，不计 PASS |

## 6. 验收结论与移交

CC-TEST-025–040 均有 PASS 证据；用户追加的 CC-TEST-041–043 也通过。ATR-RUN-010 覆盖 37 个 Odoo post-tests；当前代码基线下的最终全量 40 项结果见 ATR-RUN-011 / ATR-GIN-003 RUN-055。CC-TEST-031 及交叉矩阵使用模拟库存，不是 KR 库存同步验证。单仓库规则是不建 Ginlong 仓库映射；本地组件按 `stock.warehouse.code` 精确匹配并对未知值报错，测试证明未知值不泄露其他仓库库存。现有仓库码长度 5，Ginlong 请求允许 40 字符；任意真实 Ginlong 编码兼容性没有在本 CC 验证，交 CC-GIN-006 按实际测试数据核对，不影响本地组件关闭。此前 v0.2 尚未生成 FR/关闭 CC；现已依据 FR-GIN-004 v1.0 判定 Closure SATISFIED 并由项目负责人授权 Closed。

CC-GIN-005 承接完整本地集成与浏览器 UI/WMS 人工 E2E；CC-GIN-006 在获得单独授权后承接真实 Ginlong 环境联调。模板同步仍 BLOCKED。

## 7. 关闭补充

| 项目 | 当前结果 | 证据 / 边界 |
|---|---|---|
| CC-TEST-025–040 冻结验收 | PASS | ATR-RUN-008/009/010；最终实现源代码另由 ATR-RUN-011（ATR-GIN-003 RUN-055）全量回归 |
| CC-TEST-041–043 用户追加隔离验收 | PASS | ATR-RUN-009/010；未知仓库、未知货主和双货主×双仓交叉矩阵均通过 |
| 当前代码基线 | `3a7ec9c2de954cd1c88fd6c3d598c75b167ad4fe` | Ginlong addon 18.0.2.0.9；关闭提交只更新文档 |
| 模拟库存边界 | NOT VERIFIED（真实同步） | 模拟 ORM 测试证明查询/隔离组件行为，不证明 Karl Rapp 库存同步 |
| 真实 Ginlong、生产、浏览器 E2E | NOT RUN | 未在本 CC 授权；分别交 CC-GIN-006、CC-GIN-005 |
| 模板同步 | BLOCKED | 沿用项目用户批准的流程例外，不记为 PASS |

依据 FR-GIN-004 v1.0（Closure SATISFIED；Human Review APPROVED），CC-GIN-004 已关闭。冻结 CC v1.0、原始失败/阻塞运行与外部未验证边界均保留。

## 附录：版本记录

| 版本 | 日期 | 说明 | 状态 |
|---|---|---|---|
| v0.1 | 2026-11-18 | 首次记录 CC-GIN-004 v1.0 的自动化、ORM、组件验证、运行历史和移交边界 | Review Evidence |
| v0.2 | 2026-11-18 | 追加未知仓库/货主隔离及双 owner×双 warehouse 12 类矩阵；以 res.partner.ginlong_owner_code→stock.quant.owner_id 作为 API09 货主来源；记录 stock.warehouse.code 长度限制及新 RUN-010 | Review Evidence |
| v1.0 | 2026-11-18 | 关联最终代码基线 40 项全量回归；记录项目负责人授权、FR-GIN-004 Closure SATISFIED 与 CC-GIN-004 Closed；模板同步和外部/人工未运行项保持原状态 | Closed |
