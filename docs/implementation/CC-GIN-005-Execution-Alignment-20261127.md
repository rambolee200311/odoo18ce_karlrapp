# CC-GIN-005 同一 CC 执行对齐补充（2026-11-27）

**性质：** 对已冻结 CC-GIN-005 v1.1 的经授权执行解释，不建立新 CC、不增加范围或审批轮次。v1.1 保留为历史冻结快照；本补充与当前 SRS v2.1、TDD v2.4 共同构成当前模拟 HVR 操作依据。

## 1. 必须执行的业务基线

- 一步入库、一步出库；每张业务订单只完成一张实际 Picking。出库 Picking Done 同时形成实际备货数据，API06 读取该记录；API08 仅在其后改变订单离仓状态并发送 V3.2 三字段，不新增 Picking、不改库存。
- API02 从 inbound Order `status` 取值并由订单按钮回传；API04 自动读取当前订单的 Done/Incoming Picking 和实际 move lines，不要求用户选择 Picking 或维护重复数据。
- API05 只创建客户盘点指令；API10 只读已保存的实际盘点结果，不从 `stock.quant` 推算。
- API01 snList 是客户预报，不创建实际 Lot、Package、Picking 或库存。
- API09 按 owner+warehouse 查询 Odoo 物理数量，只读。
- API07 产品模板共享属性与 owner 产品变体按现有契约；产品档案变化不形成库存。
- 拆托时允许拣出品离开原 package；必须保留来源 Picking 行可追溯，剩余货物保留原 package。不要用“拆出后仍须绑定原托盘”作为验收条件。

## 2. 十个 API 统一验收矩阵

| API | 入口/触发 | 本轮权威业务数据 | 预期业务副作用 |
|---|---|---|---|
| 01 | Ginlong HTTP | inbound Order 请求/预报行 | 建业务订单，不建 Picking/库存 |
| 02 | 入库订单回传按钮 | inbound Order `status` | POST 状态，不记库存 |
| 03 | Ginlong HTTP | outbound Order 请求/订单行 | 建业务订单，不建 picking/reservation |
| 04 | 入库订单回传按钮 | 该单唯一 Done Incoming Picking/move lines | POST 实绩，不记库存 |
| 05 | Ginlong HTTP | stocktake customer instruction | 建盘点指令，不建实盘、不改库存 |
| 06 | 出库订单回传按钮 | 该单唯一 Done Outgoing Picking/move lines | POST 实绩，不再扣库存 |
| 07 | Ginlong HTTP | product.template + owner product.product | 建/更新档案，不记库存 |
| 08 | 出库订单状态/回传按钮 | 已 Done Picking 的出库业务状态 | POST 三字段、只改状态，不新建 Picking |
| 09 | Ginlong HTTP | stock.quant `quantity` | 只读查询，不写记录 |
| 10 | 盘点单回传按钮 | 已保存的实际盘点结果 | POST 实盘，不改库存 |

## 3. 唯一主链及 Run 规则

本轮使用 `CC005-FINAL-20261127-01`，一套 owner/project/warehouse/产品、SN、托盘和全新业务单号贯穿 API01–10；唯一活动逐步记录见 `docs/ginlong_apis/hvr/project_flow/cc005_final_20261127/Execution_Record.md`。主链开始后代码、模块、数据库、业务配置、角色和 Mock Endpoint 均冻结。发生实际缺陷或环境配置变化时，结束本 Run，保留失败证据；修复/回归后必须另起全新业务数据 Run。

只有经过本机 HTTP 入口的 Ginlong 入站请求、由订单/回传按钮触发的真实本机 Mock POST、浏览器执行的业务作业、ORM 只读业务断言和对应 Mock/API Log/Event 证据可以支持相应步骤 PASS。自动化结果不替代 UI/HVR 结果，独立历史订单不替代本轮主链。

## 4. 已有证据与当前未完成项

- `.56` 在既有测试 DB 的 Ginlong 自动化：96 post-tests / 100 methods，0 fail/error；运行记录列于本轮 Execution Record。不重跑不受文档影响的组件测试。
- 本轮严格 Mock 的独立契约预检通过 3 tests；三个 Mock 本机健康，正式捕获行号在主链开始前登记。
- 新业务产品和订单唯一键在 Odoo ORM 只读冲突扫描后通过；未用 ORM 代替业务接口或 UI 创建。
- 此补充签发时，完整浏览器主链尚未开始；全部 API 步骤在执行记录中初始为 NOT RUN。真实人工 HVR 与真实 Ginlong/KR 联调不在 Codex 模拟 PASS 声明内。
