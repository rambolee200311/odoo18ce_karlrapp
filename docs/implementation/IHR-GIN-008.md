# IHR-GIN-008 — 实施历史记录

| 日期 | 记录 |
|---|---|
| 2026-11-24 | Human Review APPROVED：批准冻结 SRS v1.3、TDD v1.6、Implementation Plan v2.1、CC-GIN-008 v1.0，并授权本地实施。模板同步 BLOCKED 按已批准例外保留。 |
| 2026-11-24 | TV-GIN-008 完成：ORM 确认四类有效键当前无重复组；订单模型无全局有效键 DB 约束；幂等模型已有 event_key；Odoo 产品变体部分唯一约束只覆盖 active 组合。ORM savepoint 验证 archived variant 可恢复为原 ID 并保留 owner/product code。见 TV-GIN-008-v0.1.md。 |
| 2026-11-24 | 开始实施 CC-GIN-008。代码修改、升级、自动化和并发验证的每次运行结果均在下方追加，不覆盖历史记录。 |

## 实施与验证追加记录

| 日期 | 记录 |
|---|---|
| 2026-11-24 | 实施有效业务身份约束：API01/03/05 订单以全局订单号构造有效身份，`state=cancel` 时释放；API07 以 owner 与原始 productCode 组合构造有效身份，归档时释放。订单键不含 project，保留现有订单归属及 Delete/Edit project 权限。幂等唯一范围加入既有 `event_key`，新增 Add 生命周期使用独立事件键。 |
| 2026-11-24 | API01/03/05/07 Add 前由业务适配器按当前有效对象检查；有效记录冲突返回现有 IDM 错误。订单取消后相同订单号可在当前 API User project 下重新 Add；API07 命中归档变体时共享模板字段检查通过后恢复原变体。数据库唯一约束作为并发最终防线；并发约束冲突使用新 ORM 环境重新确认业务键，不把任意 IntegrityError 映射成重复 Add。 |
| 2026-11-24 | Odoo 模块版本升至 `18.0.2.0.42`。在 `odooce_karlrapp` 升级成功；`/private/tmp/ccgin008_upgrade_retention_r1.log` 记录 Modules loaded 与 Registry loaded。升级前后只通过 Odoo ORM 比较 ID：inbound 8、outbound 1、stocktake 1、product.product 29、幂等 17、WorldDepot API 日志 287；无记录丢失或额外插入。 |
| 2026-11-24 | Ginlong 全量 Odoo 自动化：命令 `./venv/bin/python odoo-bin -c odoo.conf -d odooce_karlrapp -u ginlong_apis --test-enable --test-tags /ginlong_apis --stop-after-init --http-port=0 --gevent-port=0 --log-level=info --log-handler=odoo.tests:INFO --logfile=/private/tmp/ccgin008_ginlong_full_r12.log`，结果 73 post-tests、0 failed、0 error(s)，13,526 queries。测试包含 API01/03/05/07 生命周期 HTTP/ORM、Add/Delete/Add、相同及不同 Payload、重复拒绝、归档变体恢复、历史保留及 API01–10 回归。 |
| 2026-11-24 | WorldDepot 自动化回归：命令 `./venv/bin/python odoo-bin -c odoo.conf -d odooce_karlrapp --test-enable --test-tags /worlddepot --stop-after-init --http-port=0 --gevent-port=0 --log-level=info --log-handler=odoo.tests:INFO --logfile=/private/tmp/ccgin008_worlddepot_regression_r2.log`，8 post-tests、0 failed、0 error(s)。 |
| 2026-11-24 | 并发定向测试 `/private/tmp/ccgin008_effective_concurrency_targeted_r6.log`：1 个测试通过，以两个独立 ORM cursor/transaction 令 API01/03/05/07 分别竞争相同/不同 Payload；每组仅一条有效记录。该证据验证数据库独立事务竞争，不是多个 Odoo Worker 进程下的真实 HTTP 并发验收。 |
| 2026-11-24 | 跨 project 定向测试 `/private/tmp/ccgin008_cross_project_targeted_r2.log`：1 个测试通过，API01/03/05 全局业务键在另一 project 下冲突，同时保留订单按当前 API User project 创建及现有范围权限。 |
| 2026-11-24 | 准备人工 HVR 包 `docs/ginlong_apis/hvr/cc_gin_008/`：四类对象的计划、生命周期步骤、Payload、调用脚本和 NOT RUN 记录已创建。11 个 Payload 均通过实际 `validate_payload`（Required + Type）验证，脚本 `bash -n` 通过。HVR 真实 HTTP 未运行；跨 project API User 凭据与可用 Owner/Product 由负责人按包内前置条件确认。 |
| 2026-11-24 | 开发期间保留失败证据：并发测试 r1–r4 曾因测试重复使用同一键、断言元组形状错误、API05 夹具缺少 SN 明细而失败；测试夹具及断言修正后，定向测试 R6 与完整 R12 通过。跨 project 测试首轮因原始唯一约束探针复用出库单号失败，改用独立 `-DB` 键后 R2 通过。全量 R8 有一项 API07 夹具错误地改变模板共享属性导致失败；改为只改变非冲突的可选字段后 R12 通过。上述为测试设计/夹具问题，未放宽冻结业务规则。 |
| 2026-11-24 | 迁移检查脚本曾尝试从预更新 registry 执行重复键检查，因 Odoo migration 函数签名和旧 registry 字段可用时点不符而失败；脚本已移除，没有保留迁移钩子、没有执行破坏性 SQL，也没有修改/删除业务数据。有效键预检及升级后保留核对均以 Odoo ORM 完成。 |
| 2026-11-24 | 本轮追加记录时再次尝试只读 Odoo Shell 查询，但 shell 在 ORM 初始化前因沙箱禁止 macOS `sysctl(KERN_PROC_ALL)` 进程枚举而退出（`PermissionError: Operation not permitted`）。该尝试未连接/写入数据库；模块版本及数据保留状态以之前成功的 Odoo ORM/升级测试证据为准。 |
| 2026-11-24 | 补充 API07 归档恢复真实 HTTP 验收：首次定向运行 R1 暴露测试夹具使用独立 cursor 读取 HttpCase 未提交产品的问题（`MissingError`），未发现业务代码缺陷；改为在 HttpCase 当前 ORM 事务中归档后，定向 R2 通过，1 post-test、0 failed、0 errors，日志 `/private/tmp/ccgin008_api07_archive_http_r2.log`。该用例验证首次 Add、有效重复拒绝、归档后同内容 Add、再次重复拒绝、再次归档后不同 Payload Add、再次重复拒绝；断言始终复用同一变体 ID、三条成功生命周期幂等记录及每次请求日志。 |
| 2026-11-24 | 最终 Ginlong 全量回归 R13：先对全部修改的 Python 文件执行 `py_compile`，再运行 `/private/tmp/ccgin008_ginlong_full_r13.log`；74 post-tests、0 failed、0 error(s)，13,901 queries。新增 API07 HTTP 归档恢复用例包含在本次完整回归中。 |
| 2026-11-24 | 尚未启动或核实 8099 实际服务是否已重新加载 `.42` Registry；未访问真实 Ginlong/KR，未执行人工 HVR，未提交或推送 Git。人工 HVR 与真实多 Worker HTTP 并发部署验收继续 NOT RUN；模板同步 BLOCKED 按批准例外保留。 |

## Human Review 收尾追加记录

| 日期 | 记录 |
|---|---|
| 2026-11-24 | Human Review **APPROVED**（项目负责人李建强）：认可既有独立数据库事务并发测试满足 CC 并发要求，不再要求多 Worker HTTP 并发；取消本底层机制 CC 的独立人工 HVR。多 Worker 部署级验证及完整业务人工验收移交最终项目集成；这些项目按 N/A/Deferred 记录，不标 PASS。 |
| 2026-11-24 | 部署预检脚本 `docs/implementation/scripts/cc_gin_008/pre_upgrade_effective_key_preflight.py` 已正式纳入部署顺序。使用 Odoo Shell ORM 再次运行，输出 `/private/tmp/ccgin008_pre_upgrade_effective_key_preflight_20261124_r2.log`：API01 inboundOrderNo、API03 outboundOrderNo、API05 countOrderNo、API07 `(owner, productCode)` 重复有效键组均为 0；脚本末尾回滚只读事务，没有修改记录。冲突时脚本非零退出，部署必须停止且不得自动修复。 |
| 2026-11-24 | 按维护流程执行本地 `ginlong_apis` 模块升级，数据库 `odooce_karlrapp`，命令参数 `-u ginlong_apis --stop-after-init`；日志 `/private/tmp/ccgin008_human_review_retention_upgrade_r1.log` 显示 Modules loaded、Registry loaded 后正常 shutdown，无 ERROR/CRITICAL/Traceback。 |
| 2026-11-24 | 升级前后均通过 Odoo ORM 生成关键字段快照 `/private/tmp/ccgin008_keyfields_before_20261124.json` 与 `/private/tmp/ccgin008_keyfields_after_20261124.json`。比较输出：inbound 8、outbound 1、stocktake 1、product.product 29、idempotency 17、WorldDepot API logs 287，逐项 missing=0、added=0、changed=0；数据库模块状态升级前后均为 `installed / 18.0.2.0.42`。报文内容仅保存 SHA-256 摘要，不在快照复制原文。 |
| 2026-11-24 | 8099 运行确认：PID 47141 命令行为指向 `odooce_karlrapp` 的本地 Odoo 服务。模块升级后该 PID 在 `/private/tmp/ginlong_8099_current.log` 记录 Registry loaded；之后同 PID 的 `/web/login` 请求返回 HTTP 200。结论：当时本地 8099 服务加载 `ginlong_apis 18.0.2.0.42`。 |
| 2026-11-24 | 首次在受限沙箱执行 `ps` 和本地 HTTP 检查分别因进程枚举权限限制及 loopback 网络隔离未完成；改用授权的本机检查后取得上述 PID、日志和 HTTP 200 证据。前次失败没有写入数据库。 |
| 2026-11-24 | 部署检查及升级后留存验证通过；FR-GIN-008 关闭评审稿已生成。CC 状态为 Closure Review Pending，等待 Human Review 后才能关闭。模板同步 BLOCKED 继续沿用已批准例外；未访问生产或真实 Ginlong，未执行人工 HVR，未提交 Git。 |
| 2026-11-24 | 项目负责人 Human Review **APPROVED**：批准 FR-GIN-008 Closure SATISFIED 并关闭 CC-GIN-008。多 Worker HTTP 与独立人工 HVR 保持 N/A/Deferred，不记 PASS；模板同步 BLOCKED 继续沿用已批准例外。 |
| 2026-11-24 | 关闭后应项目负责人要求补齐 API01 Delete + Add 完整生命周期覆盖：自动化真实 HTTP 用例分别验证原 Payload Add→Del→相同 Payload Add→Del，以及取消后不同 Payload Add→Del；重复 Delete 返回幂等结果，最终保留 3 条 cancel 历史 Order、0 条有效 `inboundOrderNo`，3 条 Add/3 条 Delete 幂等记录。HVR-008-01 同步补全两个完整周期，人工结果保持 NOT RUN。 |
| 2026-11-24 | API01 定向测试 R1 `/private/tmp/api01_delete_add_lifecycle_targeted_r1.log` 因新增 HTTP 请求使测试自身触发速率限制，非法输入用例收到 429；此为测试速率计数隔离缺陷，未发现业务生命周期失败。测试改用既有 `_post_with_rate_reset` 后 R2 `/private/tmp/api01_delete_add_lifecycle_targeted_r2.log` 通过：1 post-test、0 failed、0 error(s)，1017 queries。业务代码未修改。 |

## Human Review 补充规则实施与回归（2026-11-24）

| 日期 | 记录 |
|---|---|
| 2026-11-24 | Human Review 补充：API01/03/05 的 Add/Edit/Del 按当前有效业务记录判断；Del 无有效记录（含仅有 cancel 历史）时返回业务错误，不得从成功幂等记录重放 OK。业务键、项目权限、历史数据保留均维持冻结规则。此项纳入 CC-GIN-008 收尾；之前记录的重复 Del 成功重放保留为历史证据，现以本补充验收结果为准。 |
| 2026-11-24 | 代码实现：`services.lifecycle_event_key` 对 API01/03/05 Del 在幂等结果读取前调用当前项目有效订单查询；无有效订单时统一返回 `BUS01: 有效订单不存在或已取消`，不创建成功幂等事件。API01/03 Edit 仅定位当前项目的非 cancel 订单，API05 Edit 同样过滤 cancel；Add 继续按全局业务键拒绝有效记录，取消后允许新生命周期。 |
| 2026-11-24 | Ginlong 回归 R1 `/private/tmp/ccgin008_del_validity_20261124_r1.log`：74 post-tests 中 0 failed、1 error，API05 人工生命周期用例因测试限流窗口累计达到上限，重新 Add 收到 429；确认是测试夹具请求计数未隔离。修复为复用 `_post_with_rate_reset`，未放宽限流或业务断言。 |
| 2026-11-24 | Ginlong 回归 R2 `/private/tmp/ccgin008_del_validity_20261124_r2.log`：74 post-tests、0 failed、0 error(s)，14,110 queries。随后补充 API05 在取消后以不同 Payload 重新 Add 并 Del 的断言。 |
| 2026-11-24 | Ginlong 最终完整回归 R3：命令 `./venv/bin/python odoo-bin -c odoo.conf -d odooce_karlrapp -u ginlong_apis --test-enable --test-tags /ginlong_apis --stop-after-init --http-port=0 --gevent-port=0 --log-level=info --log-handler=odoo.tests:INFO --logfile=/private/tmp/ccgin008_del_validity_20261124_r3.log`；74 post-tests、0 failed、0 error(s)，14,126 queries。真实 HTTP/ORM 用例覆盖 API01/03/05 首次 Del 成功、相同及不同 Payload 再 Del 返回 BUS01、cancel 后 Edit 拒绝、重新 Add 后 Del 成功；API05 覆盖相同与不同 Payload 两种重建周期。验证拒绝重试不新增成功幂等记录，历史订单保持 cancel。 |
| 2026-11-24 | 按用户此前授权重启本地 8099，并通过 Odoo Shell ORM 调用 `ir.module.module.button_immediate_upgrade()`；方法返回 Odoo 标准 `ir.actions.act_url`。其后再次重启，最终服务 PID 65649 记录 Modules loaded、Registry loaded；ORM 只读确认 `ginlong_apis installed / 18.0.2.0.43`，`/web/login` 返回 HTTP 200。未调用真实 Ginlong/KR，未运行人工 HVR，未执行 Git 提交。 |
| 2026-11-24 | 测试代码差异通过 `py_compile`；本轮相关 diff 通过 `git diff --check`。测试文件、ATR、IHR、契约和 HVR 均保留既有历史，不删除工作区其他改动。 |
