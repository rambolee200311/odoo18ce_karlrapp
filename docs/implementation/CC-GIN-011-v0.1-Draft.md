# CC-GIN-011 v0.1 Draft — 入站 API 通用处理及响应规范统一

| 项目 | 内容 |
|---|---|
| 文档编号 | CC-GIN-011 |
| 文档状态 | **v0.1 Draft — 待 Human Review** |
| 模块 | `ginlong_apis` |
| 范围 | Ginlong 入站 API01、API03、API05、API07、API09 |
| 当前基线 | [SRS v1.8](../requirement/SRS_ginlong_apis-v1.8.md)、[TDD v2.1](../ginlong_apis/TDD-v2.1.md)、[Implementation Plan v2.6](IMPLEMENTATION_PLAN_ginlong_apis-v2.6.md)、Ginlong V3.2 工作簿 |
| 授权 | 本轮仅审查和设计；**未授权修改代码、冻结基线、模块升级、测试或 Git 操作** |
| 模板同步 | BLOCKED；沿用已批准流程例外，不记为 PASS |

## 1. 目标

以 API01 已验证的通用处理链为参照，审查 API01/03/05/07/09 的 API User、Token、Log、Error、Rate Limiter、Required Validator、Type Validator、Idempotency 八项能力。识别实际缺口和接口间差异，按 Ginlong V3.2 定义各 API 的成功/失败响应边界，并提出最小修正与自动化验收契约。

本 CC 只统一通用接入与协议响应处理，不改变各 API 的业务对象、字段映射、业务键、Action、库存/订单规则或 API09 查询语义。每个 API 的有效业务响应仍按其自身 V3.2 契约保留。

## 2. 基线源码审查摘要

以下是基于当前源码、静态字段配置和既有测试代码的审查结果，不是本 CC 的运行时验收结论。

| 通用组件 | API01/03/05/07 当前实现 | API09 当前实现 | 初步结论 |
|---|---|---|---|
| API User | `validate_token` 将 Token 对应 Odoo 用户关联到 `world.depot.api.user`；共用 `_dispatch` 会拒绝没有 API User 的请求 | 同样执行 `validate_token`，但 API09 独立入口没有检查 `request.api_user` 是否存在 | Token 校验共用；API User 前置条件不一致，需确认 API09 是否应要求 API User 记录 |
| Token | 五个路由均使用 `worlddepot.controllers.validator_token.validate_token` | 相同 | 共用认证组件；不另建认证机制 |
| Log | 五个路由均使用 `worlddepot.controllers.api_logs.api_logger`，Ginlong 错误包装器可附加内部错误码和诊断信息 | 相同 | 共用日志模型与装饰器；需按真实 HTTP 失败、认证提前拒绝等路径验证日志状态和内容 |
| Error | 五个路由均经 `ginlong_error_response`；协议错误体由 `_protocol_error_response` 生成 | 相同 | 错误体统一为 Ginlong 协议字段；内部详细错误由现有日志记录 |
| Rate Limiter | API01/03/05/07 分别套用同一个 ORM 共享计数限流器；默认 10/10/10/100 次/秒，各接口独立配置 | 路由未套用限流器；当前设置模型没有 API09 阈值 | 覆盖范围不同。SRS v1.8 未给出 API09 限流要求；需由评审确认其为 N/A，还是要新增要求，不在本稿擅自增加 |
| Required Validator | `_dispatch` 对请求调用同一个 `validate_payload`，先于幂等和业务 ORM | 独立入口对请求和响应分别调用同一个 `validate_payload` | 校验器及静态字段规则共用；调用编排不同，需证明错误映射、日志和校验顺序一致 |
| Type Validator | 由 `validate_payload` 使用同一静态字段规则调用 | 相同 | 共用规则引擎；逐接口的字段规则依 V3.2 不同，属于协议配置差异 |
| Idempotency | API01/03/05/07 经 `_dispatch` 调用统一 `execute_idempotent`，按各自规则配置业务键和生命周期 | 配置为 `persistent=false`，由只读查询入口直接执行，不调用持久化幂等器 | API09 不持久化幂等符合只读查询设计；测试应证明不产生幂等记录，不应强行接入 |

### 2.1 当前已定位的实现差异

1. **成功响应字段裁剪不一致。** API01、API07 路由开启 `strict_success=True`；API03、API05 未开启，通用 `_success_body` 会保留业务 Handler 的 `success`、`data` 等内部字段后再加 Ginlong 字段。API09 不应裁成三字段，因为 V3.2 要求响应还包含 `owner`、`warehouse` 和 `inventoryList`。
2. **HTTP 状态码策略不一致。** API01/05/07 的 `_dispatch` 默认将请求/业务错误作为 HTTP 200 返回；API03 指定 HTTP 400；API09 的校验/业务错误为 400，系统错误为 500；Token 失败为 401，限流为 429。V3.2 字段表定义响应 JSON，没有定义这些 HTTP 状态映射，因此本 CC 需要记录并提交决策，不将现状推断成协议要求。
3. **API09 走独立接入编排。** 它自行解析 JSON、校验请求、调用只读服务、校验响应并映射异常；其他四个入站写接口通过 `_dispatch` 处理请求解析、校验和幂等。API09 的只读语义不适合接入写请求幂等，但两条路径仍应共用相同校验和 Error 行为。
4. **API User 门槛不同。** Token 装饰器会尝试设置 API User，但 API09 未检查查找结果；API01/03/05/07 在 `_dispatch` 中明确要求 API User。需要确认 API09 采用 Token 绑定用户即可，还是也要求有效 API User 记录；在确认前不得改变其访问条件。

## 3. V3.2 响应契约核对

以 `docs/ginlong_apis/海外WMS与第三方系统集成V3.2.xlsx` 的「海外WMS与第三方系统的接口与处理逻辑」工作表及 `data/field_rules.json` 为准。

| API | 成功响应允许字段 | 失败响应 | 当前主要核查点 |
|---|---|---|---|
| API01 | `returnStatus`、`exceptionInfo`、`operationTime` | 同三字段；`returnStatus=N` | 成功当前已严格裁剪；保持其既有业务结果 |
| API03 | `returnStatus`、`exceptionInfo`、`operationTime` | 同三字段；`returnStatus=N` | 成功需裁掉内部 `success`、`data`；当前没有严格成功裁剪 |
| API05 | `returnStatus`、`exceptionInfo`、`operationTime` | 同三字段；`returnStatus=N` | 成功需裁掉内部处理字段；当前没有严格成功裁剪 |
| API07 | `returnStatus`、`exceptionInfo`、`operationTime` | 同三字段；`returnStatus=N` | 成功当前已严格裁剪；不得影响其现有产品数据处理 |
| API09 | `returnStatus`、`exceptionInfo`、`operationTime`、`owner`、`warehouse`、`inventoryList`；数组项为 `productCode`、`quantity` | 同三字段；`returnStatus=N` | 保留 V3.2 库存响应数据，同时拒绝协议外内部字段 |

所有接口的错误 `exceptionInfo` 继续遵循现有统一 Error 组件和 V3.2 40 字符长度要求；完整错误诊断只保留在 API Log。不得为了响应字段统一而删除 API09 的库存响应，也不得把内部 ORM ID、幂等结果或调试字段返回给 Ginlong。

### 3.1 HTTP 状态码

V3.2 工作簿没有定义 HTTP 状态码与 `returnStatus` 的映射。当前源码对业务错误、校验错误和系统错误的 HTTP 状态存在差异（见 §2.1）。本 CC 建议由 Human Review 决定是否：

- 保留各路由当前 HTTP 状态，只统一协议响应体；或
- 为五个入站 API 确定一套一致的 HTTP 状态分类，同时保留 HTTP 401、429 等传输层语义。

未获批准前不得把某一方案写成冻结规则。自动化测试须先记录当前状态，并在决定后按批准契约断言。

## 4. 最小修正方案（供评审）

1. **复用现有认证与用户模型。** 保持 `validate_token`、`world.depot.api.token`、`world.depot.api.user`；仅按 Human Review 明确的 API User 适用性补齐一致行为，不建立新认证模型或 Token 机制。
2. **复用现有日志与错误组件。** 保持 `api_logger`、`ginlong_error_response`、错误目录及 API Log。所有 API 的失败响应均使用已配置错误码/消息，外部失败体只包含 V3.2 允许字段，日志保留错误码、消息和完整诊断。
3. **统一成功响应字段白名单。** API01/03/05/07 只输出 V3.2 三字段；API09 输出其 V3.2 查询响应字段及合法库存数组。可复用现有响应校验/包装能力，不新建响应框架。
4. **保留通用限流组件和适用范围。** API01/03/05/07 继续独立配置和共享数据库限流。API09 是否限流仅按 Human Review 决策处理；不得因为“统一”而自动新增阈值或改变吞吐规则。
5. **统一校验调用契约。** 两个校验器及 `field_rules.json` 不变更职责；API01/03/05/07 继续在幂等和 ORM 前校验，API09 继续校验请求及响应。允许保留符合只读语义的独立入口，但应共享错误映射、响应格式和日志结果。
6. **保留幂等适用边界。** API01/03/05/07 继续使用统一幂等器及各自规则；API09 维持无持久化幂等，并验证查询不写入幂等表。
7. **仅改必要路由配置或少量共用响应处理。** 不重构 `worlddepot` 通用组件，不复制认证、限流、校验或幂等逻辑，不修改五个接口的业务 Handler。

## 5. 范围

### 5.1 本 CC 建议纳入

- API01、API03、API05、API07、API09 的八项通用能力适用性与调用路径核对。
- 按 V3.2 修正/统一成功响应裁剪和错误响应包装，保留 API09 正常库存数据。
- 按 Human Review 决定处理 HTTP 状态与 API User 前置条件差异。
- 为实际存在的通用差异补充组件和真实 HTTP/ORM 自动化测试。
- 更新本 CC 对应的 ATR/IHR；不覆盖历史测试记录。

### 5.2 范围外

- 修改 API01/03/05/07 的业务规则、业务键、生命周期、订单/产品处理和字段映射。
- 修改 API09 的查询口径、owner/warehouse 隔离、返回数量语义或只读边界。
- 新增 API09 限流、幂等或 API User 业务权限规则，除非 Human Review 明确批准。
- 修改 API02/04/06/08/10 出站功能、Ginlong 协议、WorldDepot WMS 流程或 `stock` 库存逻辑。
- 新增 API 管理框架、业务模型、状态机、缓存/队列或外部基础设施。
- 真实 Ginlong/生产联调、完整项目人工 HVR；本 CC 不代替最终集成验收。

## 6. 自动化与组件集成测试契约

所有行为测试应通过真实业务入口和 Odoo ORM 断言；HTTP 测试使用本地测试数据库，不调用真实 Ginlong。通用组件扩展能力与 Ginlong V3.2 契约结果分开汇总。

| ID | 场景 | 必须断言 |
|---|---|---|
| CC-TEST-121 | 五个 API Token 认证矩阵 | 有效、无效、过期 Token 的 HTTP/协议响应；API Log 记录正确且不泄露凭据；无业务副作用 |
| CC-TEST-122 | API User 关联矩阵 | 有/无 API User 记录时各接口行为；先经 Human Review 冻结 API09 门槛，不以静态检查代替真实入口验证 |
| CC-TEST-123 | 错误目录跨 API | Required、Type、幂等、业务和系统异常均映射稳定错误码；错误响应字段符合 API 对应 V3.2 契约；日志含完整诊断但不含堆栈/凭据外泄 |
| CC-TEST-124 | 必填字段校验 | API01/03/05/07 请求缺失/null/空白及嵌套错误；一次汇总字段路径；合法 `0`、`false` 不误判；无 ORM 部分写入 |
| CC-TEST-125 | 字段类型校验 | DECIMAL/DateTime/BOOLEAN 等配置类型的正常、非法、空值；完整字段路径；Payload 不被修改 |
| CC-TEST-126 | API09 请求与响应校验 | 真实 HTTP 请求必填字段检查；响应库存数组逐行校验；错误结构与 API Log 正确；查询前后库存不变 |
| CC-TEST-127 | 入站幂等应用范围 | API01/03/05/07 验证 Add/Del/Edit 与有效业务生命周期规则；API09 查询多次不新增幂等记录 |
| CC-TEST-128 | 并发幂等回归 | 适用的写入 API 并发重复请求不产生重复有效业务记录；API09 作为只读查询不被错误地纳入写入幂等锁 |
| CC-TEST-129 | 限流隔离 | API01/03/05/07 各自阈值、跨 API 计数隔离、429 与 `Retry-After`；API09 按最终批准的适用性验证或标记 N/A |
| CC-TEST-130 | API01 成功响应裁剪 | 真实 HTTP 首次成功只含 V3.2 三字段；无内部 `success`、`data`、数据库 ID |
| CC-TEST-131 | API03 成功响应裁剪 | 真实 HTTP 首次成功只含 V3.2 三字段；重复/无效请求返回批准状态码和三字段错误，不改变已有业务结果 |
| CC-TEST-132 | API05 成功响应裁剪 | 真实 HTTP 首次成功只含 V3.2 三字段；无内部处理字段；业务对象结果正确 |
| CC-TEST-133 | API07 成功响应裁剪 | 保持既有 HVR/自动化已验证的三字段成功响应及错误码，不泄露内部产品 ID |
| CC-TEST-134 | API09 成功响应白名单 | 返回 `owner`、`warehouse`、`inventoryList` 及协议头字段；库存项仅含协议规定字段；无内部字段且库存只读 |
| CC-TEST-135 | 统一错误响应及长度 | 五 API 错误体符合各自响应契约；`exceptionInfo` 长度限制、字段路径/错误码及日志详情正确 |
| CC-TEST-136 | HTTP 状态映射 | 按 Human Review 批准的矩阵断言成功、认证、限流、校验、业务和系统错误状态；未批准前保持 NOT RUN/OPEN，不猜测 |
| CC-TEST-137 | 错误日志事务边界 | 主业务事务回滚时 API Log 仍可按现有独立事务记录；成功响应与 Log 状态一致，历史日志不覆盖 |
| CC-TEST-138 | API09 认证提前失败与日志 | 无效/过期 Token 真实 HTTP 拒绝，使用现有 API Log 记录；不读取或返回库存数据 |
| CC-TEST-139 | 五 API 合同回归 | 使用契约夹具逐接口核对方法、路径、Content-Type、允许请求/响应字段、嵌套字段及 HTTP 结果 |

测试分层：组件单元测试、ORM/事务集成测试、真实 Odoo HTTP 入口测试分别记录，不以其中一层替代另一层。只运行必要的 Ginlong 及受影响 WorldDepot 自动化回归；不重复与本 CC 无关的全量 E2E。

## 7. Done Gate（建议）

1. API01/03/05/07/09 的组件适用范围与 API User、API09 限流及 HTTP 状态决策均有批准记录。
2. 每个接口成功响应严格符合 V3.2 对应结构；API09 保留库存数据，其他内部字段不外泄。
3. 所有失败响应、错误码、日志、认证提前拒绝和限流行为有真实执行断言。
4. 适用的字段校验、幂等、并发和只读测试通过；不适用项明确记 N/A 并有契约依据。
5. 更新 ATR/IHR，列出命令、数据库、测试运行编号、日志位置与真实断言；失败、阻塞和未执行项保留原状态。
6. 不将人工 HVR、真实 Ginlong 联调、模板同步 BLOCKED 或最终集成工作伪记为本 CC PASS。

## 8. Open Items

| ID | 问题 | 当前发现 | 需评审决定 |
|---|---|---|---|
| OI-01 | HTTP 状态映射 | API01/05/07 默认业务错误 200；API03 400；API09 校验/业务 400、系统 500；V3.2 工作簿未定义状态码 | 是否只统一响应体并保留当前状态，或批准共享 HTTP 状态分类 |
| OI-02 | API09 是否必须关联 API User | Token 装饰器会查询关联 API User，但 API09 未检查其存在；API01/03/05/07 要求存在 | Token 绑定用户是否足够，或 API09 也必须有有效 API User 记录；不得预设额外项目权限 |
| OI-03 | API09 限流适用性 | 当前 API09 无限流装饰器/阈值；配置仅覆盖 API01/03/05/07；SRS v1.8 未定阈值 | 明确 API09 为 N/A，或另行批准阈值和测试；本 CC 不擅自增加限流 |
| OI-04 | API03/API05 成功体字段裁剪 | 当前路由未启用严格成功裁剪，可能返回内部 `success`/`data`；V3.2 定义三字段 | 确认按 V3.2 修正并保持已有业务返回数据仅限内部使用 |
| OI-05 | API09 通用错误包装边界 | API09 使用独立解析/校验入口，但共用 Error、API Log 和字段校验器 | 允许保持独立只读编排，只要求外部行为一致；不强制合并 `_dispatch` |
| OI-06 | 模板同步 | BLOCKED，沿用批准例外 | 不作为本 CC PASS 条件 |

## 9. 文档与追溯

- 本 Draft 追溯至 SRS v1.8、TDD v2.1、Implementation Plan v2.6、V3.2 工作簿及 CC-GIN-001–010 已关闭记录。
- 本轮不修改上述冻结基线。Human Review 批准设计后，如确认需调整 SRS/TDD/Implementation Plan，应先保留历史版本并提出增量修订，再授权实施。
- CC-TEST 编号从 CC-GIN-010 的 101–120 后续编号；编号仅供本草案追溯，审批前不代表测试已运行。

## 10. 评审记录

| 版本 | 日期 | 状态 | 说明 |
|---|---|---|---|
| v0.1 | 2026-11-25 | Draft | 基于 SRS v1.8、TDD v2.1、Implementation Plan v2.6、V3.2 和当前源码审查；待 Human Review |

**Human Review：待定。** 本文为设计草案，不构成冻结、编码、模块升级、测试或真实环境访问授权。
