# 实施历史记录：IHR-GIN-007

| 字段 | 值 |
|---|---|
| IHR 版本 | v0.5 |
| CC 基线 | [CC-GIN-007 v1.0 Frozen with Open Items](CC-GIN-007-v1.0.md) |
| 上游基线 | [SRS v1.2](../requirement/SRS_ginlong_apis-v1.2.md)；[TDD v1.5](../ginlong_apis/TDD-v1.5.md)；[Implementation Plan v1.9](IMPLEMENTATION_PLAN_ginlong_apis-v1.9.md) |
| 当前状态 | CC-GIN-007 Closed；CC-TEST-068 和 Ginlong 自动化全量回归通过；人工 HVR-API01-01–06 PASS；HVR-API01-07 NOT RUN（不阻塞关闭） |
| 环境 | Odoo 18；既有 `venv`、`odoo.conf`、`odooce_karlrapp` |
| 执行者 | Codex |

## 0. 授权和实施边界

项目负责人批准冻结 CC-GIN-007 并授权实施。工作限于 API01 的请求校验边界、保税入库预报处理、自动化测试及追踪记录。未访问真实 Ginlong、生产、Karl Rapp 或 Gateway；未实现或修改 API04；未持久化真实托盘、Lot、Picking、Move 或库存记录。API04 来源测试仅在回滚测试事务中构造 Picking 夹具。此后项目负责人已完成人工 HVR-API01-01–06；HVR-API01-07 尚未完成。

数据库操作通过 Odoo 标准测试运行器和 ORM。未使用直接 SQL、`psql` 或数据库驱动。保留现有工作区的其他修改。

项目模板源不可用，模板同步保持 BLOCKED；按既有批准的流程例外继续，未将其标记为 PASS。

## IHR-001 — API01 条件式 snList 处理

- **Controller：** API01 Add 且 `businessType` 不精确等于 `保税_海外收货入库` 时，只从字段校验副本移除 `snList`。传给业务服务的原始 Payload 不变，因此幂等指纹仍基于实际请求，WorldDepot API Logger 仍能记录完整原始报文。
- **Service：** 非保税 API01 Add 不解析、不执行 SN 一致性校验、不写入 `ginlong_sn_list_json` 或 Order SN 子记录。保税 API01 Add 沿用现有 SN 产品验证和结构化预报持久化。
- **保税原材料：** 在共享 SN 一致性函数中增加可选参数，允许 API01 保税入库的非 SN 产品完全省略托盘分配行；若已提供某产品的分配行，仍按产品汇总与 `details.quantity` 比较。SN 管理产品仍必须有完整清单，每条数量为 1。参数默认关闭，API05 不变。
- **测试：** 修正 API01 SN 测试夹具为保税业务类型；非 SN 产品货主建档测试不再伪造 SN；新增真实 HTTP/ORM 测试，覆盖非保税 `snList` 缺失、null、字符串、对象及错误行。测试确认 Order 不持久化该列表，而原始 API 日志保留原报文，且成功请求各有一条成功幂等记录。
- **回归夹具：** 修正既有 API05 Add/Edit/Delete 自动化用例，改用现有 SN 管理产品构造有效 SN 清单；仅修复测试输入，不改 API05 业务代码或规则。
- **版本：** `ginlong_apis` manifest 从 `18.0.2.0.39` 增至 `18.0.2.0.40`。
- **实际验证：** Odoo Shell ORM 确认既有数据库中 `ginlong_apis` 为 `installed`，`latest_version=18.0.2.0.40`。最终 8 项定向测试通过；Ginlong 全量 71 项运行仍有 1 项历史数据失败及 1 项旧 API05 测试夹具错误，详见 [ATR-GIN-007](ATR-GIN-007.md)。

未修改统一字段规则 JSON、Error、Token、限流、日志组件、API05 业务处理或 API04 回传代码。共享 SN 校验函数只增加默认关闭的 API01 专用可选参数；API05 定向测试通过。

## 1. 人工验收

项目负责人已报告 HVR-API01-01 至 HVR-API01-06 符合预期，逐项响应、ORM、日志及幂等证据见 HVR 执行记录。HVR-API01-07 仍 NOT RUN。8099 服务已按项目负责人此前要求重启用于人工 HVR；重启前失败及之后的成功复测均保留。

## IHR-002 — CC-TEST-068 原子性与库存副作用验收收尾

- **测试实现：** 在 `TestGinlongHttpAPI` 增加 `_stock_side_effect_snapshot()`，通过 Odoo ORM 对 API 请求涉及的产品采集 `stock.quant`、`stock.lot`、`stock.move`、`stock.move.line`、关联 `stock.picking` 与托盘记录字段快照，并比较库存模型请求前后的记录 ID 集合。
- **覆盖路径：** API01 保税入库 SN 校验失败的缺失列表、产品不匹配、数量不足/超出、SN 数量非 1、局部清单、重复 SN、原材料伪 SN 和 SN 行不完整；API05 对应拒绝路径及 SN 必填失败。每条路径还断言整单不存在、无成功幂等记录、失败日志存在。
- **业务规则：** 未修改 API01/API05 业务实现或冻结规则；本节仅增加验收断言。所有数据库检查均通过测试环境 ORM。
- **定向结果：** `/private/tmp/ccgin007_api01_cc068_targeted.log`：2 post-tests，0 failed、0 error，2,299 queries。API01 与 API05 新增库存快照断言均通过。
- **全量结果：** `/private/tmp/ccgin007_full_ginlong_cc068.log`：71 post-tests，1 failed、0 error，11,047 queries。唯一失败仍为产品身份全局断言命中 ID 1619。

## IHR-003 — 产品 ID 1619 全量回归失败调查

- **只读 ORM 事实：** `product.product(1619)`、模板 1529，名称为“HVR01 API01 自动建档产品”，创建时间 `2026-11-21 08:33:54`，创建者 OdooBot；`ginlong_owner_code`、`ginlong_product_code` 与复合 `default_code` 均存在，模板只有一个变体，但没有 Owner `product.template.attribute.line`，该变体也没有对应的 product-template attribute value。
- **来源证据：** [prepare_api01_hvr.py](../ginlong_apis/hvr/api01/test_data/prepare_api01_hvr.py) 中 `_seed_ownerless_product()` 以 ORM 直接建立该 HVR 前置产品，以便验证 API01 为尚无 Partner 档案的货主自动建档；创建值只含产品名称、复合 `default_code` 及 Ginlong owner/product code，没有创建 Owner 属性行。旧 HVR 执行记录曾记载 HVR01-04 使用该产品；本轮删除前 ORM 扫描未发现当前产品/模板引用，故保留历史证据并按当时实际引用结果执行删除。
- **分类：** 这是保存在开发数据库中的历史 HVR 测试夹具不满足变体属性结构断言；不是本轮自动化测试生成的临时数据，也没有证据表明当前 API01/API07 业务处理代码造成缺行。全局测试 `test_existing_ginlong_product_identity_is_owner_variant_and_raw_code_is_preserved` 将该记录纳入既有产品扫描，故失败是可复现的夹具/数据问题。
- **处置：** 未修改、删除或补写产品 1619，也未放宽该断言。问题保留为 CC-TEST-070 全量回归阻断项；若要求全量回归全绿，需先由项目负责人决定历史 HVR 夹具的正式处置方式，再按批准方式复验。

本次未重启 8099、未调用真实 Ginlong/KR/生产端点、未执行人工 HVR，也未操作 Git。模板同步继续按批准的流程例外保留 BLOCKED。

## IHR-004 — 用户授权清理 HVR 夹具并完成全量回归

- **授权对象：** 用户明确要求删除上一节调查的产品 1619。
- **删除前核查：** 通过 Odoo Shell/ORM 确认产品编码仍为 `HVR01-20261121-OWNER-AUTO` / `HVR01-20261121-PROD-AUTO`；无 `stock.quant`、`stock.lot`、`stock.move`、`stock.move.line`，也无其他产品/模板 Many2one 引用。若有引用，脚本会停止；实际核查无引用。
- **执行结果：** 通过 `product.product(1619).unlink()` 删除产品；因该模板仅有此一个变体，Odoo 同时删除唯一模板 1529。ORM 在 unlink 后确认产品和模板均不存在，并提交 Shell 事务。未删除货主 Partner、订单、日志、幂等记录或其他 HVR 数据。未使用 SQL。
- **全量复验：** `/private/tmp/ccgin007_full_ginlong_after_1619_delete.log`：71 post-tests，0 failed、0 error，11,046 queries。原产品身份回归和 CC-TEST-068 库存副作用断言均通过。
- **历史保留：** 删除前产品 1619 引发的失败仍保留在 ATR-RUN-006、008、011；本节及 ATR-RUN-012 记录授权删除后的新结果，不覆盖旧失败。

## IHR-005 — 项目负责人完成 API01 人工 HVR 与 API04 报文说明（当时状态）

本节记录时 HVR-API01-07 尚未执行、CC 尚处于 In Progress；其后状态由 IHR-006 关闭记录更新。

- **HVR-API01-01–06：** 项目负责人报告六项均符合预期。01 保留旧进程下首次错误，重启 8099 后复测成功；02 保留过期 Token 错误并记录刷新 Token 后成功；03/04/05 为成功；06 以 `BUS01` 拒绝 SN 单条数量不为 1，符合预期。执行记录列出对应订单、API 日志和幂等证据。
- **HVR-API01-07 报文性质：** 该项验证 API04（Odoo → Ginlong）出站来源，不是 Ginlong → Odoo 请求，因此没有测试者要提交的输入 JSON。通过只读 Odoo ORM 读取候选 `stock.picking(300)`、关联入库 Order 与 Move Line 后，新增 `test_data/expected/hvr_api01_07_api04_body.json` 作为预期 HTTP body 比对样例；该样例不是已发送报文。
- **当时验收状态：** HVR-API01-07 的 UI 保存/选择、Mock HTTP POST、API 日志及 Endpoint 恢复尚未执行，继续标记 NOT RUN。后续项目负责人决定该 API04 补充手工核查不阻塞本 CC 关闭，详见 IHR-006。
- **限制：** 未调用真实 Ginlong；未创建或过账 Picking；本次数据核对为只读 ORM。项目模板同步仍按既有批准例外记为 BLOCKED。

## IHR-006 — CC-GIN-007 关闭决定

- **项目负责人澄清：** API04 是回传锦浪的出站接口。HVR-API01-07 的报文由 Odoo 根据实际 Picking/Move Line 生成，不是 API01 请求；这项补充人工 UI 检查不作为 CC-GIN-007 关闭阻断。
- **API04 来源证据：** CC-TEST-069 已通过，真实调用 API04 回传方法并断言其 Payload 从已选实际 Picking/Move Line 读取，不从 API01 预报取数。API04 业务代码在 CC-GIN-007 未修改。
- **HVR 状态：** 项目负责人已完成 HVR-API01-01–06。HVR-API01-07 保持 NOT RUN，不改记 PASS；其实际出站报文样例仅用于日后可选 UI/Mock 核对。
- **关闭结果：** 自动化 CC-TEST-057–070 通过；API01 六项人工 HVR 有实际响应及 ORM/API 日志证据；项目负责人明确授权关闭 CC-GIN-007。模板同步继续 BLOCKED，按既有批准例外保留。
- **边界：** 本次未访问真实 Ginlong/生产/KR/Gateway，未修改业务代码或数据库，不代表完整 WMS E2E 或外部联调完成。

## 修订记录

| 版本 | 日期 | 修订内容 |
|---|---|---|
| v0.1 | 2026-11-23 | 记录 CC-GIN-007 初始实施与历史测试证据。 |
| v0.2 | 2026-11-23 | 追加 CC-TEST-068 ORM 库存快照验收，以及产品 ID 1619 持久化 HVR 夹具根因调查；未修改既有业务数据。 |
| v0.3 | 2026-11-23 | 记录用户授权删除 HVR 夹具产品 1619/模板 1529，以及 71 项全量回归通过。 |
| v0.4 | 2026-11-23 | 记录项目负责人报告的 HVR-API01-01–06；说明 HVR-API01-07 无人工输入 JSON、补充 API04 预期出站 body 样例，并保留该项 NOT RUN。 |
| v0.5 | 2026-11-23 | 按项目负责人关闭授权更新 CC 状态；基于已通过 CC-TEST-069，记录 API04 辅助 HVR-API01-07 为非阻塞 NOT RUN，不伪记 PASS。 |
