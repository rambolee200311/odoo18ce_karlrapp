# CC-GIN-003 v1.2 — 持久化回传 Form 修订

| 项目 | 内容 |
|---|---|
| 文档状态 | 经项目用户本轮明确授权的实施修订；实施中，尚未关闭 |
| 版本 | v1.2 |
| 日期 | 2026-11-18 |
| 上一批准基线 | [CC-GIN-003 v1.1 Frozen with Open Items](CC-GIN-003-v1.1.md)，原文保留 |
| 技术基线 | [TDD v0.5 实施修订](../ginlong_apis/TDD-v0.5.md)；TDD v0.4/v0.4.1 保留历史 |
| 项目认知 | [PROJECT_COGNITION.md v1.7](../context/cognition/PROJECT_COGNITION.md) |
| 实施授权 | 本地开发、Odoo 自动化测试与 Mock HTTP；不得访问真实 Ginlong 或生产接口 |
| 模板同步 | BLOCKED：缺少项目模板来源；沿用已批准流程例外，不记为 PASS |

本修订只变更五个人工回传接口的输入/确认界面及其验收方式。CC-GIN-003 v1.1 的其他范围、技术边界、未决事项以及 CC-TEST-008–024 条件保持不变；已通过的 CC-TEST-010/017/019 不重做。项目仍是 Ginlong–Odoo–Karl Rapp 专用对接：`worlddepot` 管理业务 Order、API User、盘点指令及实盘结果；Odoo `stock` 管理实际出入库与库存；`ginlong_apis` 只负责 Ginlong 协议与交换。

## 1. 修订决定

1. 五个人工回传接口不再使用 `TransientModel` Wizard。优先在现有业务单据 Form 增加「Ginlong 回传数据」Notebook 页面；必要的补充值写入现有持久化业务记录。
2. 回传按钮仅读取已保存的 ORM 数据。按钮不接收浏览器传来的未保存 Payload；Form 保存并重新打开后仍可查看、修改和再次发送。
3. 失败后用户可以修改已保存数据并手动重发。每次点击发送都新建一条现有 API 日志；不更新或覆盖旧日志。
4. 业务页面展示业务事件、单号、关联作业记录和关键业务数据，不展示原始 JSON，不提供 JSON 编辑器。
5. 本修订保留 API02/04/06/08/10 各自的字段级 Open Items。一个接口的 Open Item 只阻塞直接依赖它的字段或场景。

## 2. 数据来源与界面位置

| API | 业务单据与 Notebook | Payload 数据来源 | 业务边界 |
|---|---|---|---|
| API02 收货确认 | 入库 Order | `worlddepot` 入库 Order 业务状态 | 不从 picking 或库存过账推断确认状态 |
| API04 入库完成 | 入库 Order；关联 stock picking 的现有 Form 提供作业行补充项 | 实际 `stock.picking`、`stock.move.line` | 产品、SN、数量和托盘取实际作业行；不得用订单计划代替 |
| API06 备货完成 | 出库 Order；关联 stock picking 的现有 Form 提供作业行补充项 | 出库 Order 既有备货完成记录及实际 picking/move line | 识别已有备货完成事件；不增加状态门禁、审批或业务限制 |
| API08 发货完成 | 出库 Order | `worlddepot` 出库 Order 业务发货状态 | 不以 picking 创建或库存过账替代 Order 状态 |
| API10 盘点完成 | `world.depot.stocktake.order` | 关联 `world.depot.stocktake.result` 的实际采集记录 | 只选实际实盘结果；禁止读取 `stock.quant` 或用计划数据代替 |

API02/04 的按钮位于入库 Order；API06/08 位于出库 Order；API10 位于客户盘点 Order。用户可在订单 Notebook 选择本次实际 picking 范围、打开已关联作业单，并在其既有 Form 页面补充确实缺失的逐行资料。多个 picking 的选择值与逐行补充值均保存到对应 ORM 记录。

## 3. 持久化字段边界

只在现有业务模型上增加满足 Ginlong 必填字段的最小持久化字段，不创建回传业务模型、映射模型或状态机：

| 持久化对象 | 允许字段 | 用途 |
|---|---|---|
| `stock.move.line` | `ginlong_operator_code`、`ginlong_operation_time` | V3.2 要求每条 API04/06 SN 明细含实际操作人员和时间；原 move line 未保存此逐行资料，用户补充后保存。实际产品、SN、数量、托盘仍由 move line/lot/package 读取 |
| `stock.picking` | `ginlong_callback_selected` | 当一个 Order 关联多张实际作业单时，持久化本次回传范围；API04/06 仅从用户已保存选中的 picking 读取作业行 |
| `world.depot.stocktake.order` | `ginlong_api10_action` | 保存本次 API10 的 Add/Del 操作选择 |
| `world.depot.stocktake.result` | `ginlong_callback_selected`、`ginlong_operator_code` | 持久化本次所选实盘结果；在需要 Ginlong 人员编码而现有 `operator_id` 关系不能直接提供该 wire 值时，保存补充编码。实际操作人关系和 `operation_time` 仍复用原字段 |

以上字段全部位于既有持久化业务记录，不新增子表。API10 的实际产品、SN、数量、托盘、真实操作人关系和操作时间来自实盘结果；不得把客户盘点指令、计划 SN 或订单数量复制成实绩。

## 4. HTTP、Action 与日志要求

- 管理员在 Odoo 配置每个回传 API 的完整 Endpoint URL（含 `{objectid}`）；HTTP 方法固定为 `POST`，请求头为 `Content-Type: application/json`。依据为用户给出的 Ginlong 资料及后续明确确认，不再把 HTTP 方法作为 Open Item。
- Action：API02=`UPDATE`；API04/06/08=`CREATE`；API10=`Add` 或 `Del`。API10 对 Action 不区分大小写，发送时规范化为 `Add` / `Del`。
- Odoo 标准按钮同步发送一次，15 秒超时，不自动或后台重试。发送失败后用户编辑已保存业务数据再手动发送。
- 每次发送及因当前缺少必要映射而阻止的按钮尝试，均追加 `world.depot.api.log` 记录请求、响应和错误。历史行保持不变；不增加日志模型或回传尝试模型。
- API 日志不得泄露 Endpoint 凭据。没有有效 Endpoint 或 Payload 无法按已确认字段构造时，不发 HTTP，给出具体提示并写入本次日志。
- 本地测试必须替换 HTTP 客户端为 Mock；不访问 Ginlong 测试或正式 URL，不访问生产环境。

## 5. 字段级 Open Items

| API | 可实施内容 | 仍阻塞的范围 |
|---|---|---|
| API02 | Endpoint、POST、JSON、`UPDATE`、Order 状态展示和错误记录 | Ginlong V3.2 未明确如何将现有 Order 状态映射为 `receiptConfirmed`，字段/确认与撤销组合仍有冲突。只阻塞 API02 Payload/HTTP 成功验收 |
| API04 | Endpoint、POST、JSON、`CREATE`、实际 picking/move line 读取和已保存逐行人员/时间、Payload 与 Mock 成功/失败重试 | 若某条实际作业缺少必填业务值，仅阻塞该作业资料完整的场景；多 picking/分批触发语义继续按 V3.2 Open Item 隔离 |
| API06 | Endpoint、POST、JSON、`CREATE`、已知备货事件与实际 picking/move line 读取 | V3.2 必填 `palletQty`、`totalWeight`，但实际数量/重量口径与 JSON 数值类型未确认；只阻塞 API06 完整 Payload/发送，不妨碍其他接口 |
| API08 | Endpoint、POST、JSON、`CREATE`、Order 发货状态读取 | `shipmentConfirmed` 与 Order 状态的 wire 映射仍未确认；只阻塞 API08 Payload/发送 |
| API10 | Endpoint、POST、JSON、Add/Del、关联客户盘点单的持久化实盘结果筛选及本地 Mock | Ginlong 对撤销/部分采集请求范围的语义仍按 V3.2 逐场景保留；不阻塞字段来源明确的新增实盘回传模拟 |

API02、API06、API08 的本地代码必须提示各自准确未决字段，不能把一个接口的未决项变成其他接口共用的总阻塞，也不能静默省略 SRS/V3.2 必填项并声称接口验收通过。

## 6. 测试契约

本修订替换 CC-GIN-003 v1.1 中与 Wizard/回传输入界面直接有关的 CC-TEST-001–007；CC-TEST-008–024 完全沿用 v1.1。

| 测试 | 验收要求 |
|---|---|
| CC-TEST-001 持久化 Form | 五个回传入口来自既有业务单据；Notebook 可读取和修改持久化记录；不存在 Ginlong 回传 TransientModel/Wizard 或 JSON 编辑器 |
| CC-TEST-002 保存后读取 | 保存并重新读取 Form/ORM 记录后点击按钮；Payload 只能由已保存 ORM 记录生成，调用不接受浏览器临时输入、context Payload 或 JSON 编辑文本 |
| CC-TEST-003 API04 实际入库记录 | 使用实际 picking/move line、lot/package 构造已确认字段；检查 Action、必填逐行操作资料、POST/JSON 与 Mock 响应/日志。缺少值不得用计划数据填充 |
| CC-TEST-004 API10 实盘结果 | 只从所选 `worlddepot.stocktake.result` 读取数据并关联客户盘点单；Add/Del 保存后重读、大小写归一；不读 `stock.quant` 或计划数据 |
| CC-TEST-005 失败修改重试 | 第一次失败写日志；修改已保存 Form 字段后第二次发送读取修改值；新增第二条日志，第一条历史日志内容不变 |
| CC-TEST-006 请求、响应与安全 | 固定 POST、`application/json`、合理超时；成功/HTTP 错误/响应解析错误均在现有日志留下结果；凭据不明文落日志；全程 Mock HTTP |
| CC-TEST-007 Open Item 隔离 | API02/06/08 分别因各自未决字段停止发送并记录明确原因；不影响 API04/API10 已具备数据和契约的本地模拟 |

测试以 Odoo 自动化及组件集成为主。浏览器级业务用户操作和完整 WMS 人工 E2E 留最终集成 CC。测试通过不代表 Ginlong 外部契约或真实环境验收通过。CC-TEST-010/017/019 采用已有 ATR 证据，不在本修订下重复运行。

## 7. 执行与证据

测试与实际执行结果写入 [ATR-GIN-003](ATR-GIN-003.md)，实施步骤及影响记录写入 [IHR-GIN-003](IHR-GIN-003.md)。保留先前失败、无效筛选及未执行记录。已通过的事务测试不重新执行；受本修订影响的回传自动化单独记录。模板同步仍为 BLOCKED，沿用已批准流程例外。

## 修订记录

| 版本 | 日期 | 修订内容 | 状态 |
|---|---|---|---|
| v1.1 | 2026-11-18 | 既有冻结基线，详情见原件 | Frozen with Open Items；Human Review APPROVED |
| v1.2 | 2026-11-18 | 按用户明确指示取消回传 Wizard，改用持久化 Form/Notebook 和已保存 ORM 数据；固定 POST/JSON 及 Action；每次发送追加日志；细化 CC-TEST-001–007 | 用户授权实施；In Progress，未关闭 |
