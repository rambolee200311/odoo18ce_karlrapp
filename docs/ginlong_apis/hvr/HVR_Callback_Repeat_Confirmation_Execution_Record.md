# API02 / API04 / API06 / API08 重复回传确认 HVR 执行记录

> 这是项目级本地 Mock 人工操作记录，不属于 CC-GIN-010 独立 HVR。所有结论由业务验收人填写；Codex 浏览器模拟另见 [浏览器模拟记录](HVR_Callback_Browser_Simulation_Record.md)。

## 环境

| 项目 | 值 / 状态 |
|---|---|
| Odoo | `http://127.0.0.1:8099/odoo`；数据库 `odooce_karlrapp` |
| 当前模块 | Odoo ORM 证据：`ginlong_apis 18.0.2.0.47`（ATR-GIN-010 RUN-009） |
| API02 Mock | `http://127.0.0.1:18102/API/WMS_JSON/TPL_Receipt_Confirmation` |
| API04 Mock | `http://127.0.0.1:18104/API/WMS_JSON/TPL_Inbound_Completion` |
| API06 / API08 Mock | 按现有 API Settings 配置本地 loopback 接收端；真实 Ginlong 禁止用于本 HVR |
| API02/API04 已有捕获 | 各有历史 JSONL 行；开始测试前记录现有行数，按增量核对，不清空历史文件 |
| 执行人 / 日期 | 待业务验收人填写 |

## 执行规则

- 只从对应订单的 **Ginlong 回传数据**页点击实际按钮；不手工构造 API02/04/06/08 请求，不直接 POST Mock。
- 测试前记录该 Mock 的现有捕获行数、对应 API Log/Event 数；测试后只比较增量。
- 成功同 Payload 的重复请求必须出现确认窗口。取消是零 HTTP；确认才产生一次新 HTTP、关联 Event 和 API Log。
- 明确 `returnStatus=N` 可直接人工重试；无明确 N 的 5xx、超时/连接异常及无效/不完整响应属于 unknown，必须先显示风险并经用户确认。
- 多 Picking 场景按接口事件粒度：API04 每 Picking 一个事件；API06 多 Picking 聚合为一个订单事件。API02/API08 为订单级事件。
- 连续点击/不同浏览器标签页并发以 Mock 的真实 HTTP 行数为最终计数；处于发送中的同一稳定事件不得并发发送。
- 不将 Codex 模拟或自动化 PASS 记为人工 HVR PASS。真实 Ginlong 联调不在本地 Mock 验收范围。

## 项目级人工场景

| HVR | API | 场景与人工操作 | 预期 UI / 业务结果 | HTTP / Event / Log 断言 | 状态 |
|---|---|---|---|---|---|
| HVR-REP-01 | API02 | 在入库订单页首次回传；成功后再点，先取消，再重新点并确认 | 首次直接发送；重复时显示订单、上次时间/状态/结果摘要；取消关闭向导 | 首次 + 确认合计增加 2 POST；取消不增加 POST/Event/HTTP Log；确认新增子 Event、Log、Chatter | NOT RUN |
| HVR-REP-02 | API02 | 首次明确失败后直接再点；另用 unknown Mock 结果测试确认风险及取消/确认 | 明确失败直接重试；unknown 显示可能已被接收，取消零发送，确认才发送 | 明确失败重试每次追加 Log；unknown 决策前请求数不变，确认后 +1 | NOT RUN |
| HVR-REP-03 | API04 | 订单关联多张 Done/Incoming Picking，混合成功、明确失败、首次及 unknown；依次用默认、回传全部、取消 | 默认仅回传首次/明确失败；全量发送已成功项需确认；unknown 需风险确认；取消不发送 | 每张 Picking 独立计数/Event/Log；逐项比对 Payload 和 Picking 来源 | NOT RUN |
| HVR-REP-04 | API04 | 同一订单两个浏览器标签页同时操作同一 Picking；发送过程中连续点击 | 同事件第二次不发送，不展示已成功确认窗口；页面显示本次未发送/处理中提示 | Mock 对该并发事件只增加 1 POST；无第二 HTTP Log/Event | NOT RUN |
| HVR-REP-05 | API06 | 选择多张已有备货实绩 Picking，首次回传；成功后取消一次、确认一次 | 业务用户看到订单级确认摘要，不拆成 Picking 回传 | 多 Picking 合并一个 Payload/Event；取消增量为 0，确认实际 +1 POST 和新子 Event/Log | NOT RUN |
| HVR-REP-06 | API06 | 明确失败重试、unknown 风险确认；重复点击同一确认按钮 | 明确失败可直接重试；unknown 需确认；确认向导一次性消费 | 明确失败/重试各自有 Log；重复确认不得多发 HTTP | NOT RUN |
| HVR-REP-07 | API08 | 首次订单级回传；相同成功 Payload 再点并分别取消/确认 | 与 API02 使用相同通用确认交互 | 取消 0 POST；确认恰 1 POST；Event/Log/Chatter 可追溯 | NOT RUN |
| HVR-REP-08 | API02/04/06/08 | 页面快速连续点击，并在另一标签页/用户同时点击同一稳定事件 | 发送中按钮呈 loading/disabled；后端仍阻止跨标签页并发；结束后可再次按历史结果判定 | 每个稳定事件同一时刻最多 1 个 HTTP；截图、Mock 行、Event/Log 对照 | NOT RUN |

## 单次执行证据

每个 HVR 行补充：操作者、日期、业务单号/来源 Picking、开始和结束 Mock 行数、实际发送次数、向导选项、响应摘要、API Event ID、API Log ID、Chatter 记录、截图路径、人工 PASS/FAIL/BLOCKED 和说明。未填写的项目保持 NOT RUN。

## Codex 浏览器模拟补充（2026-11-26）

以下仅为 Codex 使用本地 HVR 用户和内置浏览器进行的 UI 模拟，不是业务验收人 HVR，也不改变上方真实 HVR 的 `NOT RUN` 状态。

| API | 模拟动作 | UI 与请求结果 | ORM / Mock 证据 | 真实人工 HVR |
|---|---|---|---|---|
| API02 | 对已成功的收货确认再次点击，查看向导并选择取消 | 向导显示入库单、最近成功时间和 Y/OK 响应；取消后 UI 提示没有发送 HTTP | 已有成功 Log `8668`、`8669`；取消后无新 Log/请求 | NOT RUN |
| API04 | 对已成功的 Picking 结果再次点击，查看向导并选择取消 | 向导显示 Picking `KRWH/KRIN/01102`、成功时间和 Y/OK 响应；取消无发送 | 首次 503 Log `8670`，人工按钮重试成功 Log `8671`；取消后无新请求 | NOT RUN |
| API06 | 对已成功的备货事件再次点击，查看向导并选择取消 | 向导显示订单、上次成功时间与结果；取消提示没有发送 HTTP | API06 仅有成功 Log `8679`、幂等记录 `7291`；Mock 仅 1 次 API06 POST | NOT RUN |
| API08 | 当前事件尚未成功；尝试首次发送 | 当前 Order 状态已 Outbound、Picking Done，但校验提示 `shipmentConfirmed is empty`，HTTP 未发出；没有可测试的“重复成功”向导 | 失败 Log `8675`；`ginlong_shipment_detail_ids` 为空；接口当前数据源与已批准的 Order 状态原则不一致 | BLOCKED |

并发多标签页、连续快速点击、结果未知确认及重复确认按钮消费仍为 `NOT RUN`。API04/API06 截图分别见 `project_flow/evidence/codex_simulated_20261126/api04_duplicate_confirmation.png`、`api06_duplicate_confirmation.png`。不得把 Codex 模拟记录转填为业务验收 PASS。

## API08 修复后补充模拟（2026-11-26）

首轮 API08 阻塞记录及失败 Log `8675` 保留。以下是 API08 实际出库明细关系修复后的 Codex 浏览器模拟；不是业务验收人 HVR。

| 场景 | 浏览器操作及结果 | HTTP / ORM 证据 | 真实人工 HVR |
|---|---|---|---|
| API08 首次回传 | 在订单 `HVR-FLOW-20261125-OUT-001` 的 Ginlong 回传页保存 Done/Outgoing move line `1821` 与状态 Y，再点击回传；Mock 成功 | Log `8680`、Event `7292`；实际 POST 一次，HTTP 200、Y/OK | NOT RUN |
| 重复回传取消 | 再点按钮，在确认框选取消 | Chatter 有取消记录；Mock 行数、HTTP Log 均不增加 | NOT RUN |
| 重复回传确认 | 再次进入确认框并确认，实际发送同一 Payload | Log `8681`、独立 Event `7293`；Mock 增加 1 次 POST，HTTP 200、Y/OK | NOT RUN |
| 同一确认重复点击 | 再次点击已消费的确认操作 | 提示“该确认已使用，本次没有重复发送”；无第三次 HTTP，无新的成功 API Log。首次确认后的对话框在快照中仍显示，第二次被拒后关闭，记录为 UI 反馈问题 | NOT RUN |
| 业务行限制 | 实际 Outgoing Picking 由 `picking_Out` 关联，反向 `outbound_order_id` 为空；Done/Outgoing 可保存，内部备货 Picking 行被 ORM 约束拒绝 | 订单 1295；明细 395 → move line 1821；出库 Picking `KRWH/KROUT/00695` Done。模块 `18.0.2.0.50` | NOT RUN |

API08 收发货回传本身通过上述本地模拟；全项目回传确认人工 HVR 仍待业务验收人执行。并发多标签页、快速并发点击、结果未知风险确认不在这次浏览器模拟范围内，仍按各自验收记录保留未运行状态。

### `.51` API08 Done Picking 契约回归

Odoo 全量 Ginlong 套件最终 `95 post-tests / 0 failed / 0 error`；自动化覆盖已完成 Outgoing Picking 可保存 API08 明细、未完成 Outgoing Picking 拒绝、内部备货 Picking 拒绝。首次 `.51` 测试的 fixture/断言失败保留在 `/private/tmp/ginlong_full_validation_20261126_v051.log`；修正后结果见 `/private/tmp/ginlong_full_validation_20261126_v051_rerun.log`。这属于自动化结果，不改变 HVR-REP-01～08 的真实人工 `NOT RUN` 状态。浏览器/Mock/ORM 的项目模拟明细见 [项目浏览器模拟记录](HVR_Project_Browser_Simulation_Record.md)。
