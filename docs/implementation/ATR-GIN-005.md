# 自动化测试记录：ATR-GIN-005

## 0. 文档治理

本 ATR 记录 [CC-GIN-005 v1.1 Frozen with Open Items](CC-GIN-005-v1.1.md) 的实施、Odoo 自动化、ORM 核验及本地 Mock 浏览器证据。冻结 SRS v1.1、TDD v1.0、Implementation Plan v1.8、CC-GIN-005 v1.1 均保留，不覆盖历史版本。本 ATR 不授权真实 Ginlong、生产或 KR/Gateway 联调。

## 1. 执行元数据

| 字段 | 值 |
|---|---|
| ATR | ATR-GIN-005 v0.1 |
| IHR | [IHR-GIN-005](IHR-GIN-005.md) |
| HVR | [HVR-GIN-005](../context/report/HVR-GIN-005.md) |
| CC | [CC-GIN-005 v1.1](CC-GIN-005-v1.1.md) |
| Module | `ginlong_apis` `18.0.2.0.11`；`worlddepot` `0.4` |
| Database | 既有 `odooce_karlrapp` |
| Test runner | Odoo 标准 test runner / `TransactionCase`；Odoo Shell ORM；Playwright 浏览器与 localhost Mock |
| 生产/真实外部服务 | NOT ACCESSED |

数据库读取、fixture 建立、模块升级、ORM 验证均通过 Odoo。没有直接 PostgreSQL 访问或 SQL。没有 `stock_barcode`。

## 2. 冻结测试矩阵

| CC-TEST | 内容 | 结果 | 证据和边界 |
|---|---|---|---|
| 044 | 使用既有 Odoo/venv/odoo.conf/DB，模块和迁移状态 | PASS（ORM） | 运行态版本 `ginlong_apis 18.0.2.0.11`、`worlddepot 0.4`；无新环境/数据库 |
| 045 | API01 入库请求映射、货主编码创建/复用和订单不造成库存变化 | PASS（自动化） | Ginlong suite；未将 API01 收单当作实际收货 |
| 046 | API03 出库按 owner + productCode 定位、无效组合拒绝且事务完整 | PASS（自动化） | Ginlong suite；未将 API03 收单当作备货、发货或库存变化 |
| 047 | `productCode` 模板、owner 原生变体、raw/internal code、共享属性、productForm 与 tracking | PASS（迁移 ORM + 自动化 + 浏览器） | 开发库 8 条既有 Ginlong 产品 ID 保持；不同 owner 同码变体；非法枚举/共享属性冲突测试通过；产品 Form 截图 |
| 048 | WorldDepot 产品查找复合键兼容 | PASS（自动化） | Ginlong 与 WorldDepot 回归覆盖 raw code + owner 定位及 legacy lookup |
| 049 | API02/04 入库收货确认与入库完成来源分离、持久化字段、失败重试 | PASS（自动化 + Mock 浏览器） | API02/04 读取保存的入库明细/Picking；API02 Mock 500 后修改、重开、重试；API04 从已完成 move line 回传 |
| 050 | API06 备货与 API08 发货事件及记录来源分离 | PASS（自动化 + Mock 浏览器） | API06 使用选中实际备货行、托盘与重量；API08 使用出库 Order 已保存状态及 Picking；各自单独发送 |
| 051 | API05 客户盘点指令与 API10 实盘结果独立 | PASS（自动化 + Mock 浏览器） | API10 使用现有 `worlddepot` 实盘 result；不访问/调整库存 |
| 052 | API09 `KRWH` owner/product 隔离、实际物理数量及严格只读 | PASS（标准 Picking 自动化） | 标准 receipt Picking 过账生成 A/P001=100、B/P001=300、A/P002=200；owner 隔离、raw code 返回；查询前后 quant 和 move 未改变。既有单元测试另验证 reserved quantity 不扣减 |
| 053 | 五个持久化业务 Form 保存、重开、读取已保存 ORM 数据并手动发送 | PASS（浏览器组件 E2E） | API02 状态、API04 操作人、API06 毛重、API08 状态、API10 Action 分别保存并重开；最终真实角色 ACL 另见 055 |
| 054 | 失败后修正、人工重试、每次尝试日志追加 | PASS（Mock 浏览器 + ORM 日志） | API02 首次 HTTP 500 (`Y`)；保存改为 `N` 并重开；重试成功，日志分别记录失败和成功，历史行未被覆写 |
| 055 | 必要 WMS/UI 回归、真实用户权限和业务数据入口 | PARTIAL | Ginlong 43/43 与 WorldDepot 8/8 自动化通过；浏览器用临时测试 ACL 验证页面/按钮。普通库存用户打开入库 Order 被现有 ACL 拒绝；实际操作组待项目负责人确认，未写入永久授权 |
| 056 | Karl Rapp Gateway/XML | OUT OF SCOPE / NOT RUN | 独立项目；CC-GIN-005 明确不是 Done Gate，不伪称模拟或真实 Gateway 通过 |

## 3. 最终运行结果

| Run | 执行 | 结果 | 日志 |
|---|---|---|---|
| ATR-RUN-001 | Ginlong 全量标准 Odoo 测试 | PASS；43 post-tests，0 failed、0 error | `/private/tmp/ccgin005_final_ginlong.log` |
| ATR-RUN-002 | `worlddepot` 受影响回归 | PASS；8 post-tests，0 failed、0 error | `/private/tmp/ccgin005_final_worlddepot.log` |
| ATR-RUN-003 | API09 标准 Picking 定向测试 | PASS；1 test，0 failed、0 error | `/private/tmp/ccgin005_api09_standard_picking.log`；最终全量 RUN-001 亦包含该用例 |
| ATR-RUN-004 | 产品变体迁移 Odoo ORM 核验 | PASS | 既有 8 个 Ginlong 产品迁移且产品 variant IDs 保留；模板共享 `productForm`/tracking、owner variant 编码及 owner 属性行符合基线 |
| ATR-RUN-005 | 五个持久化回传 Form 浏览器 E2E | PASS（临时 ACL） | [HVR-GIN-005](../context/report/HVR-GIN-005.md)，localhost Mock 请求计数 API02×2、API04/06/08/10 各 1；所有 HTTP 均 POST JSON |
| ATR-RUN-006 | Python/XML/工作区检查 | PASS | 7 个 Python 文件 `py_compile`；6 个 Ginlong XML 由 lxml 解析；`git diff --check` |

### 自动化运行命令

```sh
./venv/bin/python odoo-bin -c odoo.conf -d odooce_karlrapp --test-enable --test-tags /ginlong_apis --stop-after-init --http-port=0 --gevent-port=0 --log-level=info --log-handler=odoo.tests:INFO --logfile=/private/tmp/ccgin005_final_ginlong.log
```

```sh
./venv/bin/python odoo-bin -c odoo.conf -d odooce_karlrapp --test-enable --test-tags /worlddepot --stop-after-init --http-port=0 --gevent-port=0 --log-level=info --log-handler=odoo.tests:INFO --logfile=/private/tmp/ccgin005_final_worlddepot.log
```

## 4. 失败/部分记录（保留）

| Run | 实际情况 | 后续处理 |
|---|---|---|
| ATR-RUN-007 | API09 新标准 Picking 用例首次运行在 API07 创建第二个同码 owner 变体时，因为测试 fixture 给同一共享模板使用不同名称而拒绝；0 failed、1 error | 只修正测试数据，使同码模板名称一致；定向复测 RUN-003 PASS，全量 Ginlong RUN-001 PASS。未放宽共享产品一致性规则 |
| ATR-RUN-008 | 首次以仅 stock user/manager 的浏览器账号打开入库单，Odoo ACL 拒绝 | 查实现有自定义 Order 无普通库存用户 ACL；后续仅给临时浏览器用户建立临时 ACL 供 UI 组件 E2E，完成后移除；最终用户权限仍 PARTIAL |
| ATR-RUN-009 | API04 浏览器字段首次保存后重新打开未保持新操作人值，因为列表编辑自动化在保存前没有 blur/commit 行编辑 | 自动化改为 Tab blur 后显式点击 Form Save；最终 HVR 操作人改值可重开读取，API04 payload 读取新值 |
| ATR-RUN-010 | XML-RPC 模块升级提议因无已知应用管理员凭据，尝试临时授予 browser user `base.group_system` 被 auto-review 拒绝；该操作未执行 | 保留拒绝；不绕过、不以 shell 或其他路径变相提权。运行时模块代码已在已安装版本基线上；本轮新增的只是测试代码和报告 |

并发幂等测试日志中可见 PostgreSQL 唯一约束冲突，这是测试刻意制造的多 Worker/并发路径；Odoo 标准套件最终摘要 0 failed / 0 error，不作为运行失败。

## 5. ORM / Mock 证据

- API09 标准 Picking test 建立所有库存的唯一路径为 `stock.picking` + `stock.move`/`stock.move.line` 的原生确认与过账；专用用例没有 `stock.quant.create()` 或 quant 写入。API09 调用前后快照对比 quant `quantity`、`reserved_quantity`、`write_date` 和相关 `stock.move` 数相同。
- 浏览器 Mock 最终请求顺序：API02 `{receiptConfirmed:Y}` → HTTP 500；API02 `{receiptConfirmed:N}` → HTTP 200；API04 `{action:CREATE, snList.operator:KR-OP-BROWSER}`；API06 `{action:CREATE, totalWeight:"3.25"}`；API08 `{action:CREATE, shipmentConfirmed:N}`；API10 `{action:Del}`。Mock 只监听 `127.0.0.1:18220`。
- 最终 run 的 source-linked log IDs：入库 order 623/624 为 API02 fail/retry，625 为 API04；出库 order 626 为 API06、627 为 API08；stocktake order 628 为 API10。日志 payload、响应、错误均由 Odoo Shell ORM 检查；没有直接 SQL。
- HVR 使用的临时 WMS ACL 只挂在临时浏览器用户组，不是项目永久 ACL。真实普通库存用户访问不通过，故 CC-TEST-055 不得标 PASS。
- E2E 收尾后以新的 Odoo Shell ORM 会话核验：临时 ACL 820–838 均已删除，临时组 65 已移除，五个 localhost Endpoint 配置均不存在。临时账号 30 已停用并保留，以维持历史 API 日志操作者关联；没有给真实 WMS 用户组增加权限。

## 6. 全部范围与移交

- API01–API10 本地映射/回传有自动化证据；API09 有标准 Picking 生成库存的组件证据，API02/04/06/08/10 有 localhost Mock 浏览器证据。
- CC-TEST-053/054 的 Form 数据流程在临时测试权限下已验证；真实业务用户权限未通过/未确认，CC-TEST-055 PARTIAL。不得据此建议 CC-GIN-005 已具备关闭条件。
- Arrival Date 是现有入库 Form 的 required 字段，但 V3.2 API01 header 未提供。浏览器 fixture 设置了该现有字段后才能保存 Order Form；没有猜测 Ginlong 值或增加默认规则。
- 模板同步仍 BLOCKED，保留批准的流程例外。
- 完整用户权限决策/人工验收移交本 CC 评审；真实 Ginlong 外部联调交 CC-GIN-006；KR Gateway/XML 另立阶段；以上都未测试。

## ATR 版本记录

| 版本 | 日期 | 说明 | 状态 |
|---|---|---|---|
| v0.1 | 2026-11-19 | 首次记录 CC-GIN-005 实施和当前 Odoo/Mock 运行证据；保留缺陷、权限差距及 BLOCKED/NOT RUN 边界 | In Progress |
