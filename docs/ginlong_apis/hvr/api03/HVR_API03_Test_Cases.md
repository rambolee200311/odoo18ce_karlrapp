# API03 HVR 测试用例

> 本目录的 Add/Edit/Del 是 API03 独立生命周期专项，不是项目级实际出库。项目主链仅运行[统一主线指南](../HVR_Project_Business_Flow_Guide.md)的 API03 Add；必须等待共享产品真实入库且 API09 查询有货。此后本目录的独立 Edit/Del 不得作用于主链单号。

所有用例使用 API01 HVR 已用的 `hvr_api01_manual` API User，通过同一个 `HVR01-20261121 API01 HVR Project` 的本地真实 HTTP 入口执行，不按 API 方向切换用户。主生命周期用例必须按顺序执行；遇到响应或业务数据不符即停止。

## 场景总览

| HVR | 覆盖内容 | 依赖 | Payload 文件 | 状态 |
|---|---|---|---|---|
| API03-HVR-01 | Add 创建订单并映射项目、货主、收货方、产品和包装字段 | 无 | `api03_01_add.json` | NOT RUN |
| API03-HVR-02 | 同单号相同/不同 Payload 重复 Add 均拒绝，原单不变 | 01 | `api03_01_add.json`、`api03_02_add_changed.json` | NOT RUN |
| API03-HVR-03 | 活动订单 Edit 和相同 Edit 重放均执行 | 01 | `api03_03_edit.json`（发送两次） | NOT RUN |
| API03-HVR-04 | 活动订单 Del 成功；取消后 Edit/Del 拒绝 | 01、04 首次 Del | `api03_04_delete.json`（发送两次）、`api03_12_delete_changed.json`、`api03_03_edit.json`（取消后再发送） | NOT RUN |
| API03-HVR-05 | cancel 后同 Payload 重新 Add；再 cancel 后不同 Payload 重新 Add | 04 | `api03_01_add.json`、`api03_04_delete.json`、`api03_05_readd_changed.json`（发送两次）、`api03_04_delete.json` | NOT RUN |
| API03-HVR-06 | 有效 owner + productCode 组合，不同货主同码分别映射 | 无；用两张不同单号 | `api03_06_owner_a_same_code.json`、`api03_07_owner_b_same_code.json`、`api03_08_delete_owner_a.json`、`api03_09_delete_owner_b.json` | NOT RUN |
| API03-HVR-07 | 未知货主、已知货主但不存在的产品组合拒绝；不自动建档 | 无 | `api03_10_unknown_owner.json`、`api03_11_missing_product_pair.json` | NOT RUN |
| API03-HVR-08 | 必填字段缺失和嵌套 DECIMAL 非法值均在业务写入前拒绝 | 无 | `api03_13_missing_business_type.json`、`api03_14_invalid_decimal.json` | NOT RUN |

## API03-HVR-01：首次 Add

1. 发送 `test_data/payloads/api03_01_add.json`。
2. 预期 HTTP 200，响应严格只含 Ginlong 协议字段 `returnStatus=Y`、`exceptionInfo=OK`、`operationTime`。订单 ID、Bill No 和 `state=new` 通过 Odoo 后台核对，不放入成功响应。
3. 在 **WorldDepot → Outbound → Orders** 按订单号打开订单，核对项目、货主、收货方、仓库、一个产品行及所有包装字段。
4. 确认订单仍为 New，未生成 Picking，库存没有因 API03 改变。
5. 核对新增 API03 成功日志和幂等记录。

## API03-HVR-02：重复 Add

对当前有效订单顺序发送：

1. 再发送 `api03_01_add.json`（相同键、相同内容）。预期 HTTP 200，`returnStatus=N`，错误码为 `IDM02`，消息指出 `outboundOrderNo` 重复。
2. 发送 `api03_02_add_changed.json`（同一键但数量/备注不同）。预期仍为 HTTP 200 / `IDM02`。
3. ORM/后台核对仍只有一张有效订单，产品数量和备注保持首次 Add 的值；没有新业务订单，没有覆盖第一次的成功 API Log 或幂等历史。

## API03-HVR-03：Edit

1. 发送 `api03_03_edit.json`。预期 HTTP 200、`returnStatus=Y`、`exceptionInfo=OK`；同一订单的明细数量更新为 3，备注更新。
2. 原样再次发送同一 Edit，预期仍成功；Edit 是可重复的修改操作，不应被 Add 的一次性策略拦截。
3. 后台核对业务订单仍是一张、`state` 仍非 cancel，明细只反映最后一次 Edit；每次请求单独有 API Log。

## API03-HVR-04：Delete 有效性

1. 发送 `api03_04_delete.json`。预期 HTTP 200、`returnStatus=Y`；订单转为 `state=cancel`，记录保留。
2. 再发送相同 Del。预期 HTTP 200、`returnStatus=N`、错误码 `BUS01`、消息说明有效订单不存在或已取消；不得重放首次 Del 的成功响应。
3. 发送 `api03_12_delete_changed.json`，同一业务键但备注不同。预期仍为 HTTP 200、`returnStatus=N`、错误码 `BUS01`，不能由新报文绕过当前业务有效性检查。
4. 将 `api03_03_edit.json`（Edit）再发一次。预期 HTTP 200、`returnStatus=N`、错误码 `BUS01`；取消订单不应被修改。
5. 核对首次 Del 的成功记录和后续拒绝记录均保留，订单仍为 cancel。

## API03-HVR-05：取消后重新 Add

1. 用 `api03_01_add.json` 对已取消的单号重新 Add。预期成功，并创建一张新的有效订单；此前取消记录保留。
2. 再发送 `api03_04_delete.json` 取消新订单，预期成功。
3. 用 `api03_05_readd_changed.json`（同一业务键、不同数量和备注）重新 Add，预期成功；这是新的业务生命周期，不受历史成功幂等记录阻止。
4. 再原样发送 `api03_05_readd_changed.json`，预期 HTTP 200 / `IDM02`。
5. 最后用 `api03_04_delete.json` 取消当前有效订单，预期成功。
6. 后台按同一 Reference 核对三条历史业务记录按生命周期保留：前两条为 cancel，第三条先有效后由本步骤取消；历史幂等记录和 API Log 均保留。

## API03-HVR-06：按 owner + productCode 识别产品

1. 分别发送 `api03_06_owner_a_same_code.json`、`api03_07_owner_b_same_code.json`，两者 `productCode` 相同、`owner` 不同、订单号不同。
2. 两次都预期 Add 成功。
3. 后台分别核对产品明细关联 `HVR01-20261121-OWNER-A` 和 `HVR01-20261121-OWNER-B` 的对应产品变体；不得因 `productCode` 相同而跨货主串用。
4. 执行 `api03_08_delete_owner_a.json`、`api03_09_delete_owner_b.json` 取消这两张 HVR 测试订单，保留取消记录。

## API03-HVR-07：无效业务组合

1. 发送 `api03_10_unknown_owner.json`。预期 HTTP 200、`returnStatus=N`、业务错误 `BUS01`；不创建货主或订单。
2. 发送 `api03_11_missing_product_pair.json`。货主存在但该 `owner + productCode` 组合不存在，预期 HTTP 200、`returnStatus=N`、业务错误 `BUS01`；不创建产品或订单。
3. 检查 API Log 保留具体错误详情；业务订单、货主和产品主数据均无对应新增。

## API03-HVR-08：字段校验及整单无副作用

1. 发送 `api03_13_missing_business_type.json`。报文缺少必填表头 `businessType`，预期 HTTP 200、`returnStatus=N`、错误码 `REQ01`；不创建订单或成功幂等记录。
2. 发送 `api03_14_invalid_decimal.json`。明细 `details[0].quantity` 为非法数字文本，预期 HTTP 200、`returnStatus=N`、错误码 `TYP01`；不创建订单或成功幂等记录。
3. 在 Ginlong API 日志中核对字段路径/完整校验详情。`exceptionInfo` 可能受协议长度限制，不能以其短消息代替完整日志核查。

## 用例记录

逐项填写 [HVR_API03_Execution_Record.md](HVR_API03_Execution_Record.md)，不得将预期结果或自动化测试结果填为人工 PASS。
