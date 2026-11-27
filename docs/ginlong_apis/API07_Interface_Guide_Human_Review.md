# API07 接口说明 Human Review 记录

| 项目 | 内容 |
|---|---|
| 对应对外文档 | [API07_Interface_Guide.md](API07_Interface_Guide.md) |
| 状态 | Human Review Draft |
| 日期 | 2026-11-24 |
| 用途 | 保存对外接口指南中移出的内部验收状态、规范差异、依据及待确认事项 |

本文件供项目评审使用，不随面向 Ginlong 的 API07 接口指南交付。

## 1. 对外指南移出的验收记录

- API07 人工 HVR 执行记录将 HVR07-01 至 HVR07-22 判定为 PASS。对应执行记录保存 API 日志及 Odoo 后台核对信息。
- HVR07-19 使用 JSON 数值 `12345` 作为 `productName`。项目负责人确认该值按文本保存并接受该场景；这不改变 V3.2 将 `productName` 定义为 `VARCHAR`，对外指南仍要求调用方传字符串。
- HVR07-22 按项目负责人决定记 PASS，但日志保留 `Invalid token`。该次请求没有独立证明“有效 Token、但 API 用户无 WMS Project”的情况；对外文档不宣称该权限边界已由该用例验证。
- CC-GIN-008 的最终 Ginlong 自动化回归为 74 个 post-tests、0 failed、0 error。API07 归档产品的 `Add` 恢复原档案行为有真实 HTTP/ORM 自动化覆盖；自动化结果与人工 HVR 分开记录。

## 2. 规范、实现及测试差异

| 项目 | 核对结果 | 对外文档处理 |
|---|---|---|
| Authorization Header | 项目负责人确认实际调用格式为 Header 值直接填写 Token，不加 `Bearer`。现有验证代码兼容裸 Token 和 `Bearer <token>` 两种输入。历史 HVR 脚本中仍有 `Bearer` 示例。 | 对外指南按确认的调用格式写为 `Authorization: <ACCESS_TOKEN>`；历史 HVR 脚本不属于本轮修改范围。 |
| Action 字段 | V3.2 API07 字段表列出产品属性，未列 `action`；已提供的接口矩阵确认支持 `Add`、`Edit`，当前实现也按这两个动作处理。 | 按调用所需列为必填；不描述其来自 V3.2 字段表。 |
| `productForm` | V3.2 给出 `VARCHAR(40)`，未给枚举；`原材料`、`半成品`、`成品`及 SN 管理规则来自项目负责人确认并已实现。 | 作为已确认业务规则说明。 |
| 归档产品 `Edit` | 源码查询包含归档产品；满足规则时可更新共享属性，且 `Edit` 分支不重新启用产品。 | 说明当前处理结果；这是代码路径核对，未找到专门的归档 `Edit` 自动化用例。 |
| 归档产品 `Add` | 归档后重新 `Add` 会复用并重新启用原档案。 | 自动化验证已覆盖；对外指南仅陈述可观察行为。 |
| 可选字段 | 缺失和 `null` 不写入对应请求值；Edit 保留当前值。空字符串文本值可写入；空字符串 DECIMAL 后续数值转换失败并映射为 BUS01。数值 `0` 正常处理。 | 在对外指南中逐项说明，避免调用方把空值当成零。 |
| SYS01 | API07 业务处理器捕获的未预期异常返回 `returnStatus=N`、`SYS01: 系统处理失败`；当前业务入口对此类响应使用 HTTP 200。若异常逃逸到外层路由兜底，HTTP 可为 500。该错误不保证业务数据必定未写入。 | 对外指南要求检查 `returnStatus`，并先确认产品是否已存在，再决定是否重试 Add。 |

## 3. 尚待 Ginlong 确认的接口契约

1. **重量单位：** V3.2 将 `weight` 定义为 `DECIMAL(18,6)`，没有给出计量单位或换算口径。
2. **尺寸单位：** V3.2 将 `length`、`width`、`height` 定义为 `DECIMAL(18,6)`，没有给出长度单位或换算口径。
3. **`operationTime` 时区：** V3.2 指定日期时间格式，但没有定义时区；当前响应格式不包含 UTC offset。需要 Ginlong 确认双方将该无时区字符串解释为 UTC、北京/当地时间，还是其他约定。

在上述事项确认前，对外指南保留字段格式和当前响应行为，不自行指定单位或时区转换规则。

## 4. 依据

- [Ginlong V3.2 接口规范](海外WMS与第三方系统集成V3.2.xlsx)：API07 字段 0701–0713 及响应字段 0701–0703。
- [SRS v1.3](../requirement/SRS_ginlong_apis-v1.3.md)：API07 产品共享属性、产品形态及 SN 规则。
- [TDD v1.6](TDD-v1.6.md)：产品字段映射、单位处理及 API07 业务边界。
- [TV-GINLONG-PRODUCT-001 v1.0](../context/report/TV_ginlong_product_variants_api07_sn_v1.0.md)：产品变体与共享属性技术验证。
- [CC-GIN-008 v1.0](../implementation/CC-GIN-008-v1.0.md)、[ATR-GIN-008](../implementation/ATR-GIN-008.md)、[IHR-GIN-008](../implementation/IHR-GIN-008.md)：有效产品 Add、归档后恢复及回归证据。
- [API07 HVR 执行记录](hvr/api07/HVR_API07_Execution_Record.md)：人工请求响应、判定和证据限制。
- `mymodules/worlddepot/controllers/auth_controller.py`、`mymodules/worlddepot/controllers/validator_token.py`：Token 签发时效及实际 Header 处理。
- `mymodules/ginlong_apis/services.py`、`mymodules/ginlong_apis/controllers/ginlong_controller.py`、`mymodules/ginlong_apis/errors.py`：可选字段、归档 Edit、响应时间和 SYS01 的当前实现。
