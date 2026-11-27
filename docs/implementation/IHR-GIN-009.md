# IHR-GIN-009 — 实施历史记录

| 字段 | 内容 |
|---|---|
| CC | [CC-GIN-009 v1.0 Frozen](CC-GIN-009-v1.0.md) |
| 冻结基线 | [SRS v1.6](../requirement/SRS_ginlong_apis-v1.6.md)、[TDD v1.9](../ginlong_apis/TDD-v1.9.md)、[Implementation Plan v2.4](IMPLEMENTATION_PLAN_ginlong_apis-v2.4.md) |
| 环境 | Odoo 18；既有 venv、odoo.conf、数据库 odooce_karlrapp |
| 模块 | ginlong_apis 18.0.2.0.44（通过 Odoo Shell ORM 核实 installed/latest version） |
| 人工 HVR | N/A（本 CC）；关闭后回到原项目 API02/API04 HVR |
| 外部访问 | 未访问真实 Ginlong、生产或 Karl Rapp/Gateway |

## IHR-001 — 冻结基线与授权

- Human Review 批准 CC-GIN-009 v0.2 设计并授权冻结实施。批准内容：API02 使用 inbound.order.status，planning→N、arrive/inbound→Y；最小收货确认操作只改 status、不改 lifecycle state；API04 自动扫描当前订单 Done/Incoming Picking，Picking 为本地独立 Event，成功跳过、失败由用户重试；每 Picking 使用实际确认人及 date_done；历史数据及 API06 共享字段保留。
- 冲突条款已在 SRS v1.6 / TDD v1.9 按授权范围解释：允许上述 status 与 Picking 级最小扩展；禁止改变订单生命周期或增加无关状态转换。
- Ginlong 对同一订单多 Picking 分别 CREATE 的接受语义仍留 CC-GIN-006。模板同步 BLOCKED 按既有批准例外保留。

## IHR-002 — 实施记录

- API02 回传直接读取已保存的订单 status；API02 收货确认操作调用既有业务模型方法写入 arrive，并由字段跟踪记录操作人/时间；不读取 Picking、move line 或旧收货明细。
- API04 自动按当前订单、Done、Incoming 筛选 Picking；每张 Picking 独立产生稳定 Event、HTTP POST 和来源 Picking 的 API Log。成功事件再次点击跳过；失败事件只在用户再次点击时重试。Payload 读取已完成 move line 的产品、Lot/SN、数量、托盘，operator 取 Picking 实际确认人，operationTime 取 date_done。
- 标准入库 Picking 成功完成时，如没有既有确认人，写入当前实际完成操作用户到 Picking 级字段；已有值不覆盖。没有逐 SN 人工维护。
- 入库单 Ginlong Notebook 移除 API02 明细编辑和 API04 Picking 手选，保留两个按钮和只读状态、时间、错误信息。API Log 的来源关联支持订单来源及 Picking 来源日志。
- 主要改动：mymodules/ginlong_apis/models/ginlong_callbacks.py、models/api_log.py、views/ginlong_callback_views.xml、data/idempotency_rules.json、tests/test_ginlong_api.py；mymodules/worlddepot/models/inbound_order.py、views/inbound_order.xml；ginlong_apis manifest 版本更新为 18.0.2.0.44。其他未提交文件属先前工作区内容，未清理或提交。

## IHR-003 — 自动化与回归

- Ginlong 全量 Odoo 测试：最终日志 /private/tmp/cc-gin-009-ginlong-20261124-final5.log。76 post-tests，0 failed、0 error(s)，14,484 queries。执行使用现有 odoo.conf、venv、数据库 odooce_karlrapp，通过 Odoo 标准测试运行器与 ORM。
- WorldDepot 必要回归：最终日志 /private/tmp/cc-gin-009-worlddepot-20261124-final2.log。8 post-tests，0 failed、0 error(s)，112 queries。
- 自动化通过真实按钮/模型入口及本机 Mock HTTP receiver 验证 API02 Payload、API04 两个独立 Picking 请求、Event 去重、失败重试、日志追加、实际操作字段及库存无副作用。
- 首次 final4 运行仅因测试断言期望的 JSON 无空格字符串与 API Log 的合法 JSON 序列化差异而失败；改为解析 JSON 后比较 returnStatus。失败历史保留于 /private/tmp/cc-gin-009-ginlong-20261124-final4.log，修正后的完整 final5 通过。
- CC-TEST-093 的 Odoo View/ORM 自动化通过。Codex 内置浏览器刷新后进入 Odoo Session Expired 登录页，未能登录并进行真实页面只读检查；该子项记录 PARTIAL/BLOCKED，不记 PASS。
- Odoo Shell ORM 只读检查模块状态：database=odooce_karlrapp，ginlong_apis state=installed，installed_version=latest_version=18.0.2.0.44。
- 未重启 8099 两个既有服务进程，因此 8099 live Registry 加载版本 NOT VERIFIED；不以测试运行器 registry 代替在线服务版本证据。

## IHR-004 — 待后续处理

- 浏览器只读页面核验需要一个有效的已登录 Odoo 会话；未取得会话时不执行 UI 检查，不点击业务回传按钮。
- API04 同单分 Picking CREATE 的真实 Ginlong 协议兼容性留待 CC-GIN-006；本地 Mock 结果不构成真实联调。
- CC-009 未访问真实 Ginlong、生产、KR Gateway；未执行独立人工 HVR；未提交 Git。

## IHR-005 — 8099 在线版本、CC-TEST-093 与项目 HVR 准备（2026-11-24）

- 按项目负责人授权重启本地 8099：正常终止原监听进程，再在项目目录沿用原启动参数、现有 `odoo.conf` 与数据库 `odooce_karlrapp` 启动。未创建虚拟环境或数据库。重启后 PID 84612 监听 `*:8099`；`GET http://127.0.0.1:8099/web/login` 返回 HTTP 200；启动日志 `/private/tmp/ginlong_8099_hr_del_20261124.log` 记录该进程加载 `odooce_karlrapp` Registry。Odoo Shell ORM 只读核实 `ginlong_apis` 为 installed，`installed_version=latest_version=18.0.2.0.44`；仓库 Manifest 版本亦为 `.44`。
- 完成 CC-TEST-093 登录后只读浏览器检查。Codex in-app browser 页面为 `http://127.0.0.1:8099/odoo/action-537/4/world.depot.inbound.order/world.depot.inbound.order/334`，打开的是既有记录 `IO202611190301` / `HVR-GIN005-IN-001`。页面的 Ginlong 回传 Notebook 实际显示 API02/API04 按钮、只读最近成功状态/时间/错误区域，以及关联 Picking 列表。没有点击业务按钮、回传按钮或修改字段；没有将此检查当作项目人工 HVR。
- 浏览器证据截图：[CC-GIN-009-CC-TEST-093.png](CC-GIN-009-CC-TEST-093.png)。页面读取内容和截图均来自实际内置浏览器标签，不以 ORM/View 自动化代替。
- 准备项目级 API02/API04 人工 HVR 指南：[HVR_Inbound_Business_Guide.md](../ginlong_apis/hvr/HVR_Inbound_Business_Guide.md)。固定 API01 测试 Payload 与本地发送脚本位于 `docs/ginlong_apis/hvr/test_data/`；测试订单尚未创建，用户的 API01/API02/API04 业务操作、Mock Payload 核对及 PASS/FAIL 全部尚未执行，仍为 `NOT RUN`。
- API02 Mock `127.0.0.1:18102` 与 API04 Mock `127.0.0.1:18104` 的健康检查均为 HTTP 200，均绑定 loopback；API04 首次 POST 设置为 503、后续成功。Odoo API02/API04 回传 Endpoint 已通过 ORM 核实/配置为本机 Mock，API04 原值有权限受限的备份。Mock capture 文件尚无记录。配置恢复脚本已纳入指南。
- 以上 Mock 与 Endpoint 仅为关闭后人工 HVR 的准备；没有发送任何 API02/API04 业务 Payload，没有开始人工 HVR，没有访问真实 Ginlong/生产/KR Gateway。
- 历史 IHR-003/004 中“会话过期”“未重启/在线 Registry 未验证”的记录保留为此前观察。IHR-005 为新证据，并将 CC-TEST-093 当前结果更新为 PASS；本 CC 进入关闭评审待 Human Review。

## IHR-006 — 项目级入库 HVR 就绪复核（2026-11-24）

- 通过正确的 ORM 模型 `world.depot.inbound.order` 只读核对：参考号 `HVR-GIN009-IN-20261124-01` 当前不存在；货主编码 `HVR01-20261121-OWNER-A` 存在；序列号产品 `HVR01-20261122-PROD-SERIAL` 唯一匹配 1 个 `product.product`。API User 182 处于启用状态并关联项目 `HVR01-20261121 API01 HVR Project`；该项目未预设 inbound Picking Type，因此指南要求操作员在订单确认前选择现有 Receipts 类型。测试数据具备 API01 前置主数据，尚未创建入库业务单。
- 同一 ORM 查询确认 `ginlong_apis` 已安装，版本 `18.0.2.0.44`；API02 Endpoint 为 `http://127.0.0.1:18102/API/WMS_JSON/TPL_Receipt_Confirmation`，API04 Endpoint 为 `http://127.0.0.1:18104/API/WMS_JSON/TPL_Inbound_Completion`。Endpoint 均指向本机 Mock，不是 Ginlong。
- 本次对 API02、API04 Mock 健康入口分别执行 GET，均返回 HTTP 200 和 `{"status":"ok"}`。监听进程为 API02 PID 75265、API04 PID 85106；Odoo 8099 PID 84612。两项 Mock 捕获文件尚无业务请求记录；没有调用 API01，也没有点击回传按钮。
- 已预检 API01 报文 JSON、发送脚本 Bash 语法和 Mock 捕获查看脚本 Python 编译；查看脚本确认当前无捕获记录。此类准备检查不是业务 HVR PASS。
- 合并指南将用户操作顺序设为 API01 创建单据、API02 planning→N、收货确认后 arrive→Y、WMS 实际分两批完成 Picking、API04 失败后人工重试、第二批增量回传、重复点击跳过成功批次。所有 HVR-IN-01–06 仍是 `NOT RUN`，由项目负责人亲自执行并记录。
- API04 失败注入当前配置为本地接收器首个 POST 返回 HTTP 503、后续返回成功。指南提供 Endpoint ORM 恢复脚本；项目 HVR 完成后应按指南恢复 Endpoint 并停止 Mock。
- 这些环境与报文只为项目级 HVR 做准备。待 CC-GIN-009 正式关闭并由项目负责人确认开始前，不执行业务步骤。

## IHR-007 — Ginlong 回传按钮入口修正（2026-11-25）

- 复核发现：订单表单上的 Ginlong 回传按钮仍有部分位于标准表头，与要求将回传入口放在“Ginlong 回传数据”Notebook 页不一致。保留 WMS 自身业务操作，只移动 Ginlong API02/04/06/08/10 回传按钮。
- 修改 `mymodules/ginlong_apis/views/ginlong_callback_views.xml`：从入库单、出库单和盘点订单的 `//form/header` 移除对应 Ginlong 回传按钮，分别放入“Ginlong 回传数据”页中的 API02、API04、API06、API08、API10 区域。未改回传业务方法或 Payload 逻辑。同步更新入库 HVR 操作指南的按钮位置说明。
- 将 Manifest 版本更新为 `18.0.2.0.45`。沿用现有 `odoo.conf`、venv 和数据库 `odooce_karlrapp` 重启本地 8099；进程 PID `89829` 监听 `*:8099`。Odoo 日志 `/private/tmp/ginlong_8099_callbacks_ui_20261125.log` 显示模块 `ginlong_apis` 已加载，Apps 中对 Ginlong APIs 执行 Upgrade 的 `button_immediate_upgrade` 请求返回 HTTP 200，随后 Registry 加载完成。
- 使用 Codex 内置浏览器实际检查入库单、出库单和客户盘点订单。三个单据的表头均没有 Ginlong 回传按钮；各自 Notebook 分别显示 API02/API04、API06/API08、API10 按钮及关联业务数据。只读检查未点击任何回传按钮，也未修改单据。
- 页面截图：[入库](Ginlong_Callback_Buttons_Notebook_20261125.png)、[出库](Ginlong_Callback_Buttons_Outbound_Notebook_20261125.png)、[盘点](Ginlong_Callback_Buttons_Stocktake_Notebook_20261125.png)。XML 使用 `lxml` 解析通过。未运行自动化回归或人工 HVR；未访问真实 Ginlong/生产环境，未提交 Git。
- 本记录更正 IHR-005 中“回传按钮已在 Notebook”的旧位置结论；IHR-005 的其余服务、模块版本及 HVR 准备记录不受影响。当前按钮位置以本节 `.45` 现场页面和截图为准。
