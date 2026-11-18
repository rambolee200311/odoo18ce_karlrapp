# CC-GIN-003 v1.4 — 最终业务规则实施与验证增补

| 项目 | 内容 |
|---|---|
| 文档状态 | 用户授权实施；本地自动化完成；Open Items 按接口隔离；待 Human Review 关闭批准 |
| 版本 | v1.4 增补 |
| 日期 | 2026-11-18 |
| 上一实施基线 | [CC-GIN-003 v1.2](CC-GIN-003-v1.2.md)，原文保留；v1.1 冻结基线亦保留 |
| 技术基线 | [TDD v0.7 实施验证修订](../ginlong_apis/TDD-v0.7.md)；v0.4–v0.6 保留历史 |
| 项目认知 | [PROJECT_COGNITION.md v2.0](../context/cognition/PROJECT_COGNITION.md) |
| 实施授权 | 本地开发、Odoo 自动化测试与 Mock HTTP；不得访问真实 Ginlong 或生产接口 |
| 模板同步 | BLOCKED：缺少项目模板来源；沿用已批准流程例外，不记为 PASS |

本增补落实用户于 2026-11-18 明确批准的 API07 复合键及 API02/06/08 实际数据规则，并记录自动化、ORM 结果。CC-GIN-003 v1.1–v1.3 历史文件不覆盖；原有其他验收与 Open Items 继续有效。CC-TEST-010/017/019 既有证据保留，不因本增补重做。范围仍是专用 Ginlong–Odoo–Karl Rapp 对接。

## 1. 修订决定

1. 五个人工回传接口不再使用 `TransientModel` Wizard。优先在现有业务单据 Form 增加「Ginlong 回传数据」Notebook 页面；必要的补充值写入现有持久化业务记录。
2. 回传按钮仅读取已保存的 ORM 数据。按钮不接收浏览器传来的未保存 Payload；Form 保存并重新打开后仍可查看、修改和再次发送。
3. 失败后用户可以修改已保存数据并手动重发。每次点击发送都新建一条现有 API 日志；不更新或覆盖旧日志。
4. 业务页面展示业务事件、单号、关联作业记录和关键业务数据，不展示原始 JSON，不提供 JSON 编辑器。
5. 本修订保留 API02/04/06/08/10 各自的字段级 Open Items。一个接口的 Open Item 只阻塞直接依赖它的字段或场景。
6. API03 当前接口方向已由后续 Ginlong 接口矩阵确认是 Ginlong → Odoo；早期 A-003 只作为历史开发假设保留，不再列为待确认项。真实外部联调仍未执行。

## 2. 数据来源与界面位置

| API | 业务单据与 Notebook | Payload 数据来源 | 业务边界 |
|---|---|---|---|
| API02 收货确认 | 入库 Order | 持久化收货明细、状态及关联实际 move line | 全 Y 回传 Y、全 N 回传 N；明细状态混合时按用户确认阻止发送并记日志；不从订单确认/库存过账状态推断收货明细 |
| API04 入库完成 | 入库 Order；关联 stock picking 的现有 Form 提供作业行补充项 | 实际 `stock.picking`、`stock.move.line` | 产品、SN、数量和托盘取实际作业行；不得用订单计划代替 |
| API06 备货完成 | 出库 Order；现有作业单 Form 提供必要补充值 | 已选实际 `stock.picking` / `stock.move.line` | 托盘数按 `package_id` 去重；使用 V3.2 API07 `weight` 映射的 `product.ginlong_weight` × 实际数量；毛重默认净重且可人工修改；不增加状态门禁 |
| API08 发货完成 | 出库 Order | 持久化实际发货明细、状态及其关联实际 move line | 全 Y 回传 Y、全 N 回传 N；明细状态混合时按用户确认阻止发送并记日志；不以计划量冒充实绩；取消控制/回传不在本轮 |
| API10 盘点完成 | `world.depot.stocktake.order` | 关联 `world.depot.stocktake.result` 的实际采集记录 | 只选实际实盘结果；禁止读取 `stock.quant` 或用计划数据代替 |

API02/04 的按钮位于入库 Order；API06/08 位于出库 Order；API10 位于客户盘点 Order。API02/08 子表只关联对应 Order 的实际 move line；产品、SN、数量、托盘通过关系读取，不重复录入。用户可在订单 Notebook 选择实际作业范围、记录回传业务状态，并保存 API06 必要覆盖值。

## 3. 持久化字段边界

只增加满足已确认需求的最小持久化字段/明细，不创建产品映射模型或状态机。API02/08 的实际明细子表为本轮明确批准的例外：

| 持久化对象 | 允许字段 | 用途 |
|---|---|---|
| `stock.move.line` | `ginlong_operator_code`、`ginlong_operation_time` | V3.2 要求每条 API04/06 SN 明细含实际操作人员和时间；原 move line 未保存此逐行资料，用户补充后保存。实际产品、SN、数量、托盘仍由 move line/lot/package 读取 |
| `stock.picking` | `ginlong_callback_selected` | 当一个 Order 关联多张实际作业单时，持久化本次回传范围；API04/06 仅从用户已保存选中的 picking 读取作业行 |
| `world.depot.stocktake.order` | `ginlong_api10_action` | 保存本次 API10 的 Add/Del 操作选择 |
| `world.depot.stocktake.result` | `ginlong_callback_selected`、`ginlong_operator_code` | 持久化本次所选实盘结果和需要补充的外部人员编码 |
| `world.depot.inbound.order` 子表 | `ginlong.inbound.receipt.detail` | 一行对应实际收货 move line，保存 Y/N 收货状态；产品、SN、数量和托盘均关联读取 |
| `world.depot.outbound.order` 子表 | `ginlong.outbound.shipment.detail` | 一行对应实际发货 move line，保存 Y/N 发货状态；产品、SN、数量和托盘均关联读取 |
| `world.depot.outbound.order` | 自动托盘数、净重/有效总重量；手工托盘数/毛重及覆盖开关 | 手工覆盖值先保存后回传；默认托盘按实际 `stock.move.line.package_id` 去重；净重按 `product.ginlong_weight` × 实际数量计算；毛重默认净重 |
| `res.partner` | `ginlong_owner_code` | 现有 owner 档案可关联其 Ginlong owner code；不建映射模型 |
| `product.product` | 既有 `default_code`、`ginlong_owner_code` | API07 与 Ginlong API01/03/05 按复合键识别产品；允许不同 owner 同码 |

以上字段和两张实际明细子表均持久化在既有 Order Form 范围内；API10 的实际产品、SN、数量、托盘、真实操作人关系和操作时间来自实盘结果；不得把客户盘点指令、计划 SN 或订单数量复制成实绩。

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
| API02 | Endpoint、POST、JSON、`UPDATE`、持久化收货明细与状态 Payload；单明细及状态一致时 Mock 发送通过；混合状态阻止发送并追加错误日志 | V3.2 未定义混合状态 payload；用户已确认该场景不发送，因此本地行为无未决项。对取消订单的控制/回传不在本轮 |
| API04 | Endpoint、POST、JSON、`CREATE`、实际 picking/move line 读取和已保存逐行人员/时间、Payload 与 Mock 成功/失败重试 | 若某条实际作业缺少必填业务值，仅阻塞该作业资料完整的场景；多 picking/分批触发语义继续按 V3.2 Open Item 隔离 |
| API06 | Endpoint、POST、JSON、`CREATE`、实际 package 数、V3.2 Ginlong 产品重量×实际数量、手工覆盖、完整 SN 明细；托盘数/重量以 JSON string 发送并由自动化覆盖 | API06 数值序列化按用户最终确认采用 V3.2 样例的 JSON string；重量来源为 `product.ginlong_weight`。本地字段行为无未决项 |
| API08 | Endpoint、POST、JSON、`CREATE`、持久化发货明细与状态 Payload；单明细及状态一致时 Mock 发送通过；混合状态阻止发送并追加错误日志 | V3.2 未定义混合状态 payload；用户已确认该场景不发送，因此本地行为无未决项。对取消订单的控制/回传不在本轮 |
| API10 | Endpoint、POST、JSON、Add/Del、关联客户盘点单的持久化实盘结果筛选及本地 Mock | Ginlong 对撤销/部分采集请求范围的语义仍按 V3.2 逐场景保留；不阻塞字段来源明确的新增实盘回传模拟 |

API02、API06、API08 的本地代码必须提示各自准确未决字段，不能把一个接口的未决项变成其他接口共用的总阻塞，也不能静默省略 SRS/V3.2 必填项并声称接口验收通过。

## 6. 测试契约

本增补继续修订 CC-TEST-001–007，并按用户最终批准的 API07 要求完成 CC-TEST-023/024；其他 CC-TEST-008–024 原条件保持，010/017/019 沿用既有证据。

| 测试 | 验收要求 |
|---|---|
| CC-TEST-001 持久化 Form | 五个回传入口来自既有业务单据；API02/08 的实际细节状态、API06 覆盖值保存并重开；不存在 Ginlong 回传 Wizard/JSON 编辑器 |
| CC-TEST-002 保存后读取 | 重新打开后，API02/08 从已保存子表，API06 从已保存选择及覆盖值，按钮生成 Payload；不得使用未保存前端值 |
| CC-TEST-003 API04 实际入库记录 | 使用实际 picking/move line、lot/package 构造已确认字段；检查 Action、必填逐行操作资料、POST/JSON 与 Mock 响应/日志。缺少值不得用计划数据填充 |
| CC-TEST-004 API10 实盘结果 | 只从所选 `worlddepot.stocktake.result` 读取数据并关联客户盘点单；Add/Del 保存后重读、大小写归一；不读 `stock.quant` 或计划数据 |
| CC-TEST-005 失败修改重试 | 第一次失败写日志；修改已保存 Form 字段后第二次发送读取修改值；新增第二条日志，第一条历史日志内容不变 |
| CC-TEST-006 请求、响应与安全 | 固定 POST、`application/json`、合理超时；成功/HTTP 错误/响应解析错误均在现有日志留下结果；凭据不明文落日志；全程 Mock HTTP |
| CC-TEST-007 Open Item 隔离 | PASS：API02/08 混合状态按用户确认阻止发送并追加错误日志；API06 DECIMAL 字段按用户确认与 V3.2 示例作为规范化 JSON string 发送。未决外部撤销/分批语义仍单独保留 |
| CC-TEST-023 API07 货主复合键 | PASS（Odoo 自动化）：相同编码跨 owner 创建独立产品；同 owner 查询/更新只命中本 owner；API01/03 使用 owner+productCode；Hoymiles/OFoundation 共用 resolver 按项目 owner 消歧，未配置且重复时报告歧义 |
| CC-TEST-024 受影响 WMS 回归 | PASS（已修改模块自动化范围）：Ginlong 30 项、worlddepot 8 项全部通过，覆盖 resolver、API01/03 订单与 Picking 保留、盘点双模型、Token/日志及回传关联；完整浏览器/人工 WMS E2E 留最终集成 CC |

测试以 Odoo 自动化及组件集成为主。浏览器级业务用户操作和完整 WMS 人工 E2E 留最终集成 CC。测试通过不代表 Ginlong 外部契约或真实环境验收通过。CC-TEST-010/017/019 采用已有 ATR 证据，不在本修订下重复运行。

### 6.1 本轮实际结果与关闭判断

ATR-RUN-042 的 7 个定向 post-tests、ATR-RUN-043 的 Ginlong 全量 30 个 post-tests、ATR-RUN-044 的 `worlddepot` 全量 8 个 post-tests、ATR-RUN-046 的最终规则定向 3 个 post-tests，以及 ATR-RUN-047/048 的 Ginlong 全量 31 个 post-tests 均为 0 failed / 0 error。RUN-048 还验证 API06 数值字段最多六位小数的规范化。Odoo Shell ORM 只读核实收/发货子模型、关联字段、API06 计算字段、产品 Ginlong 重量/货主字段和 move line 数据源均已注册；`ginlong.api.callback.wizard` 未注册。CC-TEST-001–007、023/024 自动化范围满足；CC-TEST-010/017/019 沿用既有 PASS，不重跑。

用户最终确认：API02/08 状态一致时按该状态发送，若明细 Y/N 混合则不发送；API06 `palletQty`/`totalWeight` 按 DECIMAL(18,6) 的 V3.2 JSON 样例作为 string 发送；重量来源采用 `product.ginlong_weight`。专项和全量自动化均通过。冻结 CC 允许保留的外部 Open Items（例如 Ginlong 撤销/部分执行语义和真实联调）未被伪记解决，也不阻塞已确认正常场景。CC-TEST-001–024 均有 PASS 证据，CC-GIN-003 具备提交 Human Review 关闭评估的条件；本文件不自行标记 Closed、不生成关闭 FR。

## 7. 执行与证据

测试与实际执行结果写入 [ATR-GIN-003](ATR-GIN-003.md)，实施步骤及影响记录写入 [IHR-GIN-003](IHR-GIN-003.md)。保留先前失败、无效筛选及未执行记录。已通过的事务测试不重新执行；受本修订影响的回传自动化单独记录。模板同步仍为 BLOCKED，沿用已批准流程例外。

## 修订记录

| 版本 | 日期 | 修订内容 | 状态 |
|---|---|---|---|
| v1.1 | 2026-11-18 | 既有冻结基线，详情见原件 | Frozen with Open Items；Human Review APPROVED |
| v1.2 | 2026-11-18 | 按用户明确指示取消回传 Wizard，改用持久化 Form/Notebook 和已保存 ORM 数据；固定 POST/JSON 及 Action；每次发送追加日志；细化 CC-TEST-001–007 | 用户授权实施；In Progress，未关闭 |
| v1.3 | 2026-11-18 | 纳入 API07 复合键、API02/08 实际明细子表及 API06 实际托盘/重量聚合与覆盖；扩充 CC-TEST-023/024 | 用户授权实施；In Progress，未关闭 |
| v1.4 | 2026-11-18 | 记录 API07 与 WMS owner resolver、API02/08 混合状态阻止、API06 JSON string 与 Ginlong weight 来源决定及自动化证据；本地 CC 测试条件通过，提交 Human Review 关闭评估 | 已实施；待 Human Review，不标记 Closed |
