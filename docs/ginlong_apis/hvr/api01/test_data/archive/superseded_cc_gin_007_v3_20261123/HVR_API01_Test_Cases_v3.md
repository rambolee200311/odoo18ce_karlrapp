> **已归档：本 v3 用例不再用于当前 CC-GIN-007 HVR。** 请使用 [CC-GIN-007 HVR v0.1 Draft](../cc_gin_007_v0.1_draft/README.md)。v3 的 STANDARD payload 不触发保税 snList 规则；原请求文件已移到 archive，历史结果不变。

# API01 入库单人工验收实例 v3（精简必测）

本轮只执行下列 **5 个 HTTP 实例**，不需要把归档目录中的所有 JSON 逐个发送。每例的报文与 curl 一一对应。接口地址为 `POST http://127.0.0.1:8099/api/ginlong/TPL_Pending_Receipt_Note`，认证从本地 `test_data/.api01_hvr.env` 读取。

## 前置条件

- API01 产品变体已在 Odoo 中存在：Owner A 原材料 `HVR01-20261121-PROD-COMMON`、成品 `HVR01-20261122-PROD-SERIAL`、半成品 `HVR01-20261122-PROD-SEMIFINISHED`。已用 ORM 确认三者的 tracking 分别为 `none`、`serial`、`serial`；无需再运行 API07 setup 报文。
- 服务使用 `ginlong_apis 18.0.2.0.39`。如果服务不是该版本，先停止 HVR 并升级/重启。
- 这些用例使用各自新的 `inboundOrderNo`。只按表中顺序执行一次；不要重复 Add，除非正在验证用例明确要求。

## 必测实例

| 顺序 | HVR | 要验证的唯一行为 | 请求文件 | 预期响应与 Odoo 结果 |
|---:|---|---|---|---|
| 1 | **HVR01-29** | 三托盘混装原材料、成品、半成品；逐托盘保存，逐产品与 `details.quantity` 对平 | [JSON](test_data/archive/superseded_cc_gin_007_v3_20261123/payloads/hvr01_29.json) / [curl](test_data/archive/superseded_cc_gin_007_v3_20261123/curl/hvr01_29.sh) | `Y / OK`。Order 有 3 个产品，保存 15 行；每托盘 5 行，原材料 3、成品 2、半成品 2；各产品合计为 9/6/6。不得生成 Picking 或改库存。 |
| 2 | **HVR01-30** | SN 管理产品单行 `quantity=3`，验证单件 SN 规则及错误定位 | [JSON](test_data/archive/superseded_cc_gin_007_v3_20261123/payloads/hvr01_30.json) / [curl](test_data/archive/superseded_cc_gin_007_v3_20261123/curl/hvr01_30.sh) | `N / BUS01`；错误应指出 SN 单行数量错误，并带可识别的产品/托盘定位。不得创建订单、明细或成功幂等记录；完整诊断在 API 日志。 |
| 3 | **HVR01-31** | 同一成品 SN 被分配到两个托盘 | [JSON](test_data/archive/superseded_cc_gin_007_v3_20261123/payloads/hvr01_31.json) / [curl](test_data/archive/superseded_cc_gin_007_v3_20261123/curl/hvr01_31.sh) | `N / BUS01`；同一 `(productCode, productSN)` 重复必须拒绝，托盘不同不构成例外；不得留下业务写入。 |
| 4 | **HVR01-32** | 不同产品使用相同 SN 文本 | [JSON](test_data/archive/superseded_cc_gin_007_v3_20261123/payloads/hvr01_32.json) / [curl](test_data/archive/superseded_cc_gin_007_v3_20261123/curl/hvr01_32.sh) | `Y / OK`；两个不同产品的 SN 行都保存。SN 身份键含 `productCode`。 |
| 5 | **HVR01-33** | 新入库单引用 HVR01-29 中成品的同一个 SN | [JSON](test_data/archive/superseded_cc_gin_007_v3_20261123/payloads/hvr01_33.json) / [curl](test_data/archive/superseded_cc_gin_007_v3_20261123/curl/hvr01_33.sh) | `Y / OK`；新单据成功，不能因另一张 API01 单据曾引用该 SN 而拒绝。 |

## 建议执行次序

1. 执行 HVR01-29，核对订单和 15 行托盘/SN 分布。
2. 执行 HVR01-30、31，分别确认错误拒绝及无部分写入。
3. 执行 HVR01-32，确认不同产品的相同 SN 文本允许。
4. 最后执行 HVR01-33；它复用 HVR01-29 的一个真实 SN，但使用新订单号。

每例记录 HTTP 三字段响应、时间、后台订单结果、API 日志和幂等记录。人工判定填写在 [执行记录](HVR_API01_Execution_Record.md)。自动化测试通过不代替人工判定。

## 本轮不需要重做的内容

- HVR01-01–19：常规 Add、幂等、货主、字段校验、Del、Token 等项目已有历史人工证据或自动化覆盖，本轮 SN/托盘规则没有要求重复验收。
- HVR01-21–28：分别覆盖缺 SN、数量不一致、产品不匹配、重复及部分 SN 等分支，保留 Odoo 自动化测试；人工 HVR 不要求逐个重放。
- API07 产品准备：三个所需产品变体已存在，不需要发送 setup payload。
- 上述被移出活动包的报文和 curl 已归档，只有在后续缺陷复测时才取用。
