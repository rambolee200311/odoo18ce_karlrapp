# CC-GIN-011 v1.0 Frozen — 入站 API 通用处理及响应规范统一

| 项目 | 内容 |
|---|---|
| 文档编号 | CC-GIN-011 |
| 状态 | **v1.0 Frozen / Closed** |
| 批准 | Human Review APPROVED；项目负责人 2026-11-25 |
| 模块 | ginlong_apis |
| 范围 | Ginlong 入站 API01、API03、API05、API07、API09 |
| 上游基线 | [SRS v1.9](../requirement/SRS_ginlong_apis-v1.9.md)、[TDD v2.2](../ginlong_apis/TDD-v2.2.md)、[Implementation Plan v2.7](IMPLEMENTATION_PLAN_ginlong_apis-v2.7.md) |
| 前序设计 | [CC-GIN-011 v0.1 Draft](CC-GIN-011-v0.1-Draft.md)；作为历史评审稿保留 |
| 模板同步 | BLOCKED；沿用批准的流程例外，不标记 PASS |
| 实施授权 | 已批准；仅限本 CC 范围、本地开发与自动化测试 |

## 1. 目标与边界

统一五个入站 API 对既有通用组件的使用方式及 HTTP/协议响应行为。优先复用 worlddepot 的 API User、Token、API Log 和 ginlong_apis 的 Error、Rate Limiter、Required Validator、Type Validator、Idempotency。

不得改变 API01/03/05/07 业务 Handler、业务键、Action、生命周期与字段映射；不得改变 API09 库存口径、货主/仓库隔离和只读行为；不得修改 API02/04/06/08/10 出站接口。API09 保持独立只读编排，不强制并入写接口 _dispatch，也不接入持久化幂等。

不访问真实 Ginlong 或生产环境。本 CC 不单独组织人工 HVR；关闭后回到项目原 HVR。

## 2. 八项通用组件适用矩阵

| 组件 | API01 | API03 | API05 | API07 | API09 |
|---|---|---|---|---|---|
| API User | 必须关联有效 API User | 同 API01 | 同 API01 | 同 API01 | 必须关联有效 API User；不增加额外业务权限 |
| Token | 复用 worlddepot Token 认证 | 同 API01 | 同 API01 | 同 API01 | 同 API01 |
| Log | 复用 worlddepot API Log | 同 API01 | 同 API01 | 同 API01 | 同 API01 |
| Error | 复用统一错误目录及协议错误响应 | 同 API01 | 同 API01 | 同 API01 | 同 API01 |
| Rate Limiter | 现有 10 次/秒及独立配置保持 | 现有 10 次/秒及独立配置保持 | 现有 10 次/秒及独立配置保持 | 现有 100 次/秒及独立配置保持 | 接入现有共享组件；默认 10 次/秒、独立配置 |
| Required Validator | API01 请求字段 | API03 请求字段 | API05 请求字段 | API07 请求字段 | 查询请求及生成响应 |
| Type Validator | 按字段规则校验请求 | 按字段规则校验请求 | 按字段规则校验请求 | 按字段规则校验请求 | 查询请求及生成响应 |
| Idempotency | 保持 API01 原策略 | 保持 API03 原策略 | 保持 API05 原策略 | 保持 API07 原策略 | **N/A**；只读查询不持久化 |

API User 是 Token 已通过后关联到 Odoo 用户的有效 WorldDepot API User 记录。不得增加额外项目授权或业务权限规则。

## 3. HTTP 状态及错误响应

下列状态映射是本项目的技术规范。Ginlong 是否接受此传输层状态映射，留真实联调确认；此项不阻塞本地实施和 Mock 验证。

| 结果 | HTTP | 返回体 |
|---|---:|---|
| 业务成功 | 200 | returnStatus=Y |
| 字段校验、幂等拒绝或业务规则错误 | 200 | returnStatus=N |
| Token 无效或过期 | 401 | Ginlong 错误结构 |
| API User 不存在或无访问资格 | 403 | Ginlong 错误结构 |
| 限流拒绝 | 429 | Ginlong 错误结构，保留 Retry-After |
| 未预期系统异常或限流存储故障 | 500 | Ginlong 错误结构 |

所有错误体仅含 returnStatus、exceptionInfo、operationTime。错误码和安全消息使用统一 Error 组件；内部完整诊断写 API Log，不返回异常堆栈或内部字段。RATE02 表示限流状态存储故障，按系统异常返回 500；RATE01 表示请求超限，返回 429。

API01、API03、API05、API07 成功体严格只含三个 Ginlong 协议字段。API09 成功体保留 V3.2 库存查询字段及 inventoryList 明细；不得混入数据库 ID、内部执行结果或调试字段。API09 错误体仍为三个错误字段。

## 4. 冻结的实施范围

1. 五个 API 均复用现有 validate_token、api_logger、Error 和字段校验组件。
2. API01/03/05/07 拒绝没有有效 API User 的 Token 用户；API09 使用相同前置条件。
3. API09 套用现有 ORM 共享 Rate Limiter，阈值独立读取 ginlong_apis.api09_rate_limit，默认 10 次/秒。
4. ErrorCode 到 HTTP 状态按 §3 集中处理；业务/字段/幂等失败统一 HTTP 200。
5. API03/API05 成功响应在 HTTP 出口严格裁剪到三字段，幂等内部结果维持原状。
6. API09 保持单独的只读请求/响应校验编排，不持久化幂等记录。
7. 现有 API01/03/05/07 限流默认和配置保持不变；不改任何业务处理及错误目录已有消息，除本 CC 为 403 所需的通用 API User 错误分类外。

## 5. 自动化及组件集成测试契约

测试必须通过 Odoo 实际 HTTP 入口并检查协议响应、API Log 和适用的 ORM 业务结果。API09 查询须断言库存只读及不写入幂等表。模板同步沿用批准例外，不列为 PASS。

| 测试 | 冻结验收内容 |
|---|---|
| CC-TEST-121 | 五个 API 的有效、无效及过期 Token；HTTP/协议错误、日志和无业务副作用 |
| CC-TEST-122 | Token 用户有关联/未关联有效 API User；所有接口访问前置行为及 403 |
| CC-TEST-123 | Required、Type、幂等、业务和系统错误统一 Error/Log 映射，诊断不泄露 |
| CC-TEST-124 | API01/03/05/07 必填字段及嵌套字段真实入口校验，0/false 和整单无副作用 |
| CC-TEST-125 | DECIMAL、DateTime、BOOLEAN 字段类型校验、错误路径、原始 Payload 不变 |
| CC-TEST-126 | API09 请求和响应校验、协议错误体、库存查询前后只读 |
| CC-TEST-127 | API01/03/05/07 既有幂等策略；API09 多次查询不产生持久幂等记录 |
| CC-TEST-128 | 写接口并发/幂等必要回归；API09 不误入写幂等 |
| CC-TEST-129 | API01/03/05/07 限流配置与隔离保持；API09 独立 10 次/秒默认及 429/Retry-After |
| CC-TEST-130 | API01 成功 HTTP 响应严格三字段 |
| CC-TEST-131 | API03 成功、重复/非法处理均为三字段；业务 ORM 结果符合现有契约 |
| CC-TEST-132 | API05 成功及错误响应严格三字段；盘点业务对象结果正确 |
| CC-TEST-133 | API07 既有三字段成功/失败响应不泄漏产品内部 ID |
| CC-TEST-134 | API09 V3.2 成功响应字段白名单、库存项字段白名单及只读 |
| CC-TEST-135 | 错误体字段、ErrorCode、exceptionInfo 长度及完整日志诊断 |
| CC-TEST-136 | 成功、业务错误、认证、API User、限流、系统故障 HTTP 状态矩阵 |
| CC-TEST-137 | 失败日志记录与业务事务边界、成功/失败状态和历史日志保留 |
| CC-TEST-138 | API09 Token 认证/API User 提前拒绝，不查询库存且记录 API Log |
| CC-TEST-139 | API01/03/05/07/09 路径、方法、请求/响应契约及适用组件端到端回归 |

单元测试、ORM/事务集成测试和 HTTP 入口测试分别记录；不得以静态结构检查或单层结果代替行为验收。

## 6. 验收与关闭

- CC-TEST-121～139 必须逐项映射到测试方法、运行编号、实际断言与状态。
- 未执行、失败、阻塞和 N/A 分别记录；只有有证据的结果标 PASS。
- 执行 Ginlong 自动化及必要的受影响模块回归；修复本 CC 引起的失败后重跑相关测试。
- 更新 ATR、IHR 和 FR。模板同步 BLOCKED 延续已批准例外，不伪记为通过。
- 不访问真实 Ginlong/生产、不组织独立 HVR、不自动提交 Git。

## 7. Human Review 与版本记录

| 版本 | 日期 | 决策 |
|---|---|---|
| v0.1 | 2026-11-25 | Draft；历史评审稿保留 |
| v1.0 | 2026-11-25 | Human Review APPROVED；批准 OI-01～OI-06 决策并授权修订冻结基线和实施 |

**冻结基线：Frozen；当前执行状态：Closed。** 实施结果与正式关闭状态由 IHR-GIN-011、ATR-GIN-011、FR-GIN-011 追踪。

## 8. 正式关闭记录（2026-11-25）

- Human Review：**APPROVED**；项目负责人批准关闭 CC-GIN-011。
- Closure：**SATISFIED**；CC-TEST-121～139 逐项证据见 ATR-GIN-011 §2，最终全量为 91 post-tests、0 failed、0 error。
- 正式状态：**Closed**；记录见 [FR-GIN-011 v1.0](FR-GIN-011.md)。
- 本 CC 不单独组织人工 HVR；按批准决定返回项目原 HVR。真实 Ginlong 兼容性留后续联调，未访问真实接口或生产。
- 模板同步仍按既有批准例外为 BLOCKED，不记 PASS。
