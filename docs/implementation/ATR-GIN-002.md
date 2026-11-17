# 自动化测试记录：ATR-GIN-002

## 0. 文档治理

本记录消费 [CC-GIN-002 v1.0](CC-GIN-002.md) 的测试契约，不改变其范围。测试在现有 Odoo 18 开发环境执行；本地模拟与组件测试不代表 Ginlong 真实 HTTP/API 联调。

## 1. 执行元数据

| 字段 | 值 |
|---|---|
| Intent ID | `GINLONG-API-INGRESS-001` |
| IHR | [IHR-GIN-002 v1.0](IHR-GIN-002.md) |
| CC | CC-GIN-002 v1.0 Frozen；后续已 Closed |
| Module | `ginlong_apis` |
| Environment | Odoo 18.0；项目 `venv`；`odoo.conf`；`odooce_karlrapp` |
| Test Framework | Odoo 标准 `--test-enable` / `TransactionCase` |
| 当前代码基线 | `GINLONG-WT-d87e0952022786c7f393438573b372fc870df629816b40c572b1764451a030ff` |
| 最后执行 | 2026-11-17 08:05:03（Odoo 日志时间；UTC） |
| 执行者 | Codex |

代码基线是 `mymodules/ginlong_apis/` 所有非缓存文件路径与内容的 SHA-256 聚合指纹。最终有效测试在该指纹对应内容上运行；本次文档勘误不修改 addon 源码，也不改变该测试基线。

## 2. 测试契约基线

| 来源 | 验证范围 |
|---|---|
| CC-TEST-001 | API01 全字段创建/删除；不确认实际执行或库存 |
| CC-TEST-002 | API03 全字段创建/删除；A-003 仅作本地假设；不确认实际执行或库存 |
| CC-TEST-003 | API05 独立任务字段和明细；不读写库存台账 |
| CC-TEST-004 | API07 现有产品对象新增/更新及字段覆盖 |
| CC-TEST-005 | 现有 Token/logger 复用、未授权拒绝及日志不暴露 Token |
| CC-TEST-006 | 当前环境模块升级、Odoo 自动化/ORM 组件测试 |

## 3. 当前自动化测试状态

| 指标 | 值 |
|---|---|
| Required Tests | 6 |
| PASS | 6 |
| FAIL / ERROR / SKIPPED / BLOCKED / NOT RUN | 0 / 0 / 0 / 0 / 0 |
| Latest Valid Run | ATR-RUN-009 |
| Current Code Baseline | `GINLONG-WT-d87e0952022786c7f393438573b372fc870df629816b40c572b1764451a030ff` |
| Evidence Baseline Match | Yes |

## 4. 测试覆盖矩阵

| CC / TEST | Automated Test | Run | Result | 实际证据 |
|---|---|---|---|---|
| CC-TEST-001 | `test_api01_maps_order_pallet_product_and_serial_without_execution` | ATR-RUN-009 | PASS | 表头、`name` 名称别名、details、SN 数量/托盘/产品/规格字段创建/删除；订单仍为 `new`，无关联 `stock.picking` |
| CC-TEST-002 | `test_api03_maps_all_source_fields_without_execution` | ATR-RUN-009 | PASS | 完整 API03 头/明细字段映射及数量；订单仍为 `new`，无 picking；测试后使用 WMS `unlink` 删除 |
| CC-TEST-003 | `test_api05_is_independent_and_preserves_task_scope` | ATR-RUN-009 | PASS | 创建/删除独立任务、备注、产品名称/规格、数量及 SN 原值；盘点服务无 `stock.quant` 模型引用 |
| CC-TEST-004 | `test_api07_creates_and_updates_native_product` | ATR-RUN-009 | PASS | 原生 `product.product` 新建/更新；验证编码、名称、规格、单位、功率、标准、认证、形态、重量及尺寸 |
| CC-TEST-005 | `test_api01_decorated_route_authenticates_and_logs_with_existing_logger`；`test_routes_use_worlddepot_token_and_api_log_decorators` | ATR-RUN-009 | PASS | 实际共享 Token validator 对测试 Token 授权；模拟请求上下文调用装饰路由，未授权返回 401 且不新增订单；验证使用既有 `api_logger` 并检查记录内容不含 Authorization Token |
| CC-TEST-006 | 模块升级与本模块 Odoo post-install 套件 | ATR-RUN-009 | PASS | `ginlong_apis` installed；Odoo 标准运行器报告 6 post-tests、0 failed、0 error |

### Regression Verification

CC 未单独定义 `CC-PRESERVE-*` 编号。按 CC §2.3 与 CC-TEST-001/002 验证本次新增接收流程不调用确认/过账逻辑；两种订单均保持待执行状态，未创建 picking 或库存变动。完整 WMS 人工流程和真实仓库执行数据回写留给最终集成 CC。

## 5. 测试运行历史（仅追加）

| Run | 日志时间 | 调用范围 | 执行数 | 结果 | 结果说明 / 后续 |
|---|---|---|---:|---|---|
| ATR-RUN-001 | 07:46:41 | 模块 Odoo 测试 | 5 | FAIL：1 failed，2 error | ORM 暴露子模型 Ginlong 字段缺失及重复数量扩展；IHR-004 修正；日志 `debug_logs/odoo_181.log:2876–3000` |
| ATR-RUN-002 | 07:47:42 | 模块 Odoo 测试 | 5 | FAIL：1 failed | 测试桩将 logger 环境伪装成仅支持日志模型的假环境；生产 Token/logger 逻辑未报错；日志 `:3169–3175` |
| ATR-RUN-003 | 07:48:19 | 单项 Token/logger 组件测试 | 1 | FAIL：1 failed | 测试桩对所有 Odoo Environment 创建返回同一假环境；日志 `:3344–3350` |
| ATR-RUN-004 | 07:49:24 | 模块 Odoo 测试 | 5 | FAIL：1 failed | 函数包装器复制原函数 `__module__`，测试错误依赖模块名识别；改为检查实际共享装饰器引用；日志 `:3519–3525` |
| ATR-RUN-005 | 07:50:53 | 模块 Odoo 测试 | 5 | PASS：0 failed，0 error | 当时版本的 5 项测试通过；随后增加真实路由组件检查；日志 `:4006–4024` |
| ATR-RUN-006 | 07:52:35 | 模块 Odoo 测试（含路由组件） | 6 | FAIL：1 error | 测试环境工厂未接受 Odoo Environment 的额外构造参数；测试桩修正；日志 `:4340–4405` |
| ATR-RUN-007 | 07:53:34 | 模块 Odoo 测试（含路由组件） | 6 | FAIL：1 error | 测试断言直接 JSON 序列化 datetime；改为检查记录文本；日志 `:4721–4759` |
| ATR-RUN-008 | 07:55:08 | 模块 Odoo 测试 | 6 | PASS：0 failed，0 error | 当时指纹下 6 项通过；日志 `:5075–5095`；随后因补充字段断言及 API01 名称别名修正重跑 |
| ATR-RUN-009 | 08:05:03 | 最终模块 Odoo 测试 | 6 | PASS：0 failed，0 error | 命令：`venv/bin/python3 odoo-bin -c odoo.conf -d odooce_karlrapp -u ginlong_apis --test-enable --test-tags /ginlong_apis --stop-after-init --log-level=info --log-handler=odoo.tests:INFO`；当前指纹下 6 项通过；日志 `:5733–5736` |

早期失败及错误记录均保留；R1 的实现字段问题、R2–R7 的组件测试桩/断言问题已由后续实施记录及 ATR-RUN-009 复验处理。ATR-RUN-008 是当时代码指纹下的有效运行，随后因补充字段断言及 API01 名称别名修正而被 ATR-RUN-009 取代。ATR-RUN-009 是唯一绑定当前代码指纹的最终有效运行。

## 6. 回归验证

| CC 保护边界 | 自动化检查 | Run | 状态 |
|---|---|---|---|
| 接收入库不等于收货/上架完成 | `state == new`、`stock_picking_id` 为空、无关联 picking | ATR-RUN-009 | PASS |
| 接收出库不等于拣货/发货完成 | `state == new`、两个 picking 引用为空、无关联 picking | ATR-RUN-009 | PASS |
| 盘点任务不记库存 | 服务创建/删除只操作任务模型；源码引用检查无 `stock.quant` | ATR-RUN-009 | PASS |
| 既有认证与日志 | Ginlong 路由引用现有 `validate_token` / `api_logger`，有效/无效 Token 组件验证 | ATR-RUN-009 | PASS |

## 7. Issues

| 项 | 状态 | 影响 |
|---|---|---|
| ATR-RUN-001–007 的失败/错误 | Resolved | 历史保留；ATR-RUN-009 在最终代码指纹上通过 |
| Ginlong 生产 URL/协议、真实 HTTP E2E | BLOCKED / Not Run | 不在本 CC 的本地模拟验收中；不声称真实对端已验证 |
| API03 外部方向 | 待 Ginlong 确认 | 本地 A-003 假设，不阻塞本地组件验收 |
| 项目模板来源同步 | BLOCKED | 依 CC 已批准流程例外保留，不记为 PASS |

## 8. 特项验证与替身层级

- ORM 记录使用 Odoo `TransactionCase`，测试事务回滚；运行日志显示测试创建的订单及明细在事务结束时清除。
- API controller 是 Odoo 已装载的真实模块代码，但验证使用组件级模拟 request envelope；API logger 的独立持久化 cursor 在该路由组件测试中以测试替身捕获。此前 CC-GIN-001 ATR-RUN-005 验证了现有 `world.depot.api.log` logger 的真实 ORM 写入与敏感信息保护。
- 未运行网络/HTTP E2E、Ginlong sandbox 或 Karl Rapp/Gateway 联调。Mock/组件 PASS 不等于真实外部集成 PASS。
- 未访问 PostgreSQL 直连接口、未执行 SQL、未读取/修改 `stock.quant`，未安装或启用 `stock_barcode`。

## 9. Evidence Inventory

| Evidence | 类型 | 位置 | 对应 Run |
|---|---|---|---|
| E-001 | Odoo 标准测试日志 | `debug_logs/odoo_181.log:5733–5736` | ATR-RUN-009 |
| E-002 | Odoo Shell ORM 模块/字段检查 | `ginlong_apis=installed`；两个盘点模型注册；WMS 与产品字段存在；测试残留 0；`stock_barcode=uninstallable` | ATR-RUN-009 |
| E-003 | 最终 addon 源指纹 | SHA-256 `d87e0952022786c7f393438573b372fc870df629816b40c572b1764451a030ff` | ATR-RUN-009 |

## 10. 移交摘要

所需自动化验证：6；当前有效 PASS：6；FAIL/ERROR/BLOCKED/NOT RUN：0/0/0/0。ATR-RUN-009 与当前 addon 源指纹匹配。接口仅在本地模拟/ORM 组件范围验证，未做 Ginlong 或 KR 真实联调。进入 FR 与 Human Review；ATR 本身不宣布 CC Closed。

## 附录：版本历史

| 版本 | 日期 | 说明 | 状态 |
|---|---|---|---|
| v0.1 | 2026-11-17 | 建立 CC-GIN-002 测试覆盖矩阵，保留所有迭代运行，R8 为当时有效运行 | Review Evidence |
| v0.2 | 2026-11-17 | 补充 API01 名称别名和完整字段断言；保留 R1–R8 历史，R9 为当前有效运行及代码基线 | Review Evidence |
| v1.0 | 2026-11-17 | 勘误：明确 R8 已由 R9 取代；保留 R1–R8 历史，ATR-RUN-009 为唯一最终有效测试基线 | Closure Evidence |
