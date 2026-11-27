# API05 盘点指令 HVR 测试计划

**状态：** Draft，待人工执行。依据 Ginlong V3.2 API05 字段及项目负责人本次确认的 SN 业务规则。

> 项目级 HVR 不按本目录的孤立顺序执行：先完成[共享仓库业务主线](../HVR_Project_Business_Flow_Guide.md)，并以 API01 后真实完成的 Incoming Picking（由 API04 读取回传）及 API03 后真实完成的 Outgoing Picking（由 API08 读取回传）作为库存/盘点上下文。下表 HVR05-01–12 是补充请求校验；HVR05-10 已改为依赖项目主线实际收货过的 SN，不再依赖已归档的 API01-HVR-29。主线 API05 用 `project_flow/test_data/payloads/api05_count_remaining_stock.json`。

## 验收边界

- Ginlong API05 接收客户盘点指令，保存到 `world.depot.stocktake.order`；盘点指令不等于仓库实盘结果。
- `product.tracking == 'serial'` 的产品必须提供完整 SN 明细；`tracking != 'serial'` 的产品不强制提供 `snList`。
- 对每个产品分别检查 SN 数量和等于 `details[].quantity`、SN 的 `productCode` 属于请求明细、同一产品不重复 SN。
- 校验失败时不建立/修改盘点订单或成功幂等记录；完整错误写 API 日志，对外仅返回 Ginlong 错误三字段且 `exceptionInfo` 不超过 40 字符。
- API05 V3.2 对已提供的 SN 行要求六项字段齐全。API03 不在本 HVR 范围。
- 本 HVR 不访问、不调整 `stock.quant`，也不创建实盘结果。

## 环境与执行

| 项目 | 值 |
|---|---|
| 方法 / Content-Type | POST / `application/json` |
| URL | `${API01_BASE_URL}/api/ginlong/TPL_Stocktake_Order` |
| 认证 | `Authorization: ${API01_TOKEN}`，Header 不加 `Bearer`，从本地忽略文件读取 |
| 原材料产品 | `HVR01-20261121-PROD-COMMON`，tracking=`none` |
| SN 产品 | `HVR01-20261122-PROD-SERIAL`，`productForm=成品`、tracking=`serial` |
| Odoo 单据 | WorldDepot → Stocktake → Orders；按 `countOrderNo` 搜索 |
| API 日志 / 幂等 | WorldDepot → Ginlong APIs → API 日志 / 幂等记录 |

项目主线必须先完成 API07 产品建档、真实入库/出库及 API09C。主线 API05 只使用统一数据集的 Payload。专项 HVR05-01–12 可在主链完成后按用例执行；不运行旧 `setup_serial_product.sh` 为主链造产品，也不依赖 HVR01-29。每个专项业务键独立；失败后检查未产生盘点订单和成功幂等行。勿把盘点计划 SN 与实盘结果混为一谈。

## 覆盖矩阵

本目录共 12 个可选专项请求校验用例，不构成项目主线的执行序列。HVR05-10 引用项目主线 FLOW-IN 实际收货 Picking 生成的 `HVR-FLOW-SN-001`；API04 只报告该实绩，不创建库存或 SN，并使用独立盘点单号；不依赖已归档的 HVR01-29。主线 API05 使用 `../project_flow/test_data/payloads/api05_count_remaining_stock.json`，并继续要求后续实际盘点及 API10。

| HVR | 场景 | 预期 |
|---|---|---|
| HVR05-01 | SN 产品与原材料混合明细，SN 汇总匹配 | 成功；计划数据按原报文保存，不产生实盘结果 |
| HVR05-02 | SN 产品缺少 `snList` | BUS01，指出缺少 SN 清单；不写盘点订单 |
| HVR05-03 | SN 汇总数量不足 | BUS01 数量不一致；不写盘点订单 |
| HVR05-04 | SN 汇总数量超出 | BUS01 数量不一致；不写盘点订单 |
| HVR05-05 | SN `productCode` 不在本次 `details` | BUS01 产品不匹配；不写盘点订单 |
| HVR05-06 | 同产品重复 `productSN` | BUS01 重复 SN；不写盘点订单 |
| HVR05-07 | SN 行缺必填 `productSN` | REQ01 指出字段路径；不写盘点订单 |
| HVR05-08 | 原材料省略 `snList` | 成功；保存盘点指令且 SN 计划列表为空 |
| HVR05-09 | 两个 SN 管理产品只提供一个产品的 SN | BUS01 部分清单错误；不写盘点订单 |
| HVR05-10 | 引用实际入库 SN 及尚未入库的 SN | 成功；不检查入库/lot 状态，不创建实盘记录 |
| HVR05-11 | 不同 productCode 使用相同 productSN | 成功；SN 身份按产品区分 |
| HVR05-12 | 同产品相同 SN 位于不同托盘 | BUS01 重复；不写盘点订单 |

**HVR 判定规则：** 保存 HTTP 状态及响应、Odoo ORM 单据/明细、API 日志、幂等状态证据。没有验收者实际结果的实例必须保留 NOT RUN。
