# API05 盘点指令 HVR 测试用例

> 项目主线请求和依赖见[统一仓库业务流程指南](../HVR_Project_Business_Flow_Guide.md)。本目录为 API05 请求校验专项；API05 成功只保存客户盘点计划，不能当作 Actual Results。主线完成 API05 后，必须由仓库实际盘点并保存 Actual Results，再运行 API10。

所有实例以 JSON 文件为完整请求体，运行对应 curl 脚本。成功响应核对 `returnStatus=Y`、`exceptionInfo=OK`；失败响应核对 `returnStatus=N`、具体错误码/原因且不超过 40 字符，响应字段为 `returnStatus`、`exceptionInfo`、`operationTime`。

## 执行前置

主线 API05 不运行产品准备脚本；先按项目指南完成 API07、API01 和实际收货/出库，再使用项目共享 SKU 的主线 API05 Payload。下表是主线完成后的可选 API05 校验专项；如用例需要不同 `productCode` 或 tracking 配置，只能使用隔离专项数据，不得改动主线 SKU 或库存。管理员可在 **WorldDepot → Ginlong APIs → API 日志** 查询请求，并在幂等记录菜单核验 `API05 + countOrderNo + Add`。

| HVR | 请求 | 操作与预期 | ORM / 日志核验 |
|---|---|---|---|
| HVR05-01 | [JSON](test_data/payloads/hvr05_01.json) / [curl](test_data/curl/hvr05_01.sh) | SN 成品明细数量 2，由两个数量 1 的 SN 汇总；原材料数量 4 不传 SN；预期成功 | `world.depot.stocktake.order` 一张，`plan_details_json` / `plan_sn_list_json` 与请求一致；`result_ids` 为空 |
| HVR05-02 | [JSON](test_data/payloads/hvr05_02.json) / [curl](test_data/curl/hvr05_02.sh) | SN 产品数量为 2，完全省略 `snList`；预期 BUS01 明确指出缺少 SN 清单 | 不存在相同 `countOrderNo` 的任务或成功幂等行；日志有完整 productCode 诊断 |
| HVR05-03 | [JSON](test_data/payloads/hvr05_03.json) / [curl](test_data/curl/hvr05_03.sh) | 明细数量 2，SN 数量和为 1；预期 BUS01 数量不一致 | 不建立任务/计划；日志包含明细数量及 SN 数量和 |
| HVR05-04 | [JSON](test_data/payloads/hvr05_04.json) / [curl](test_data/curl/hvr05_04.sh) | 明细数量 2，SN 数量和为 3；预期 BUS01 数量不一致 | 同 03；无成功幂等记录 |
| HVR05-05 | [JSON](test_data/payloads/hvr05_05.json) / [curl](test_data/curl/hvr05_05.sh) | 明细仅含成品，SN 行使用原材料 productCode；预期 BUS01 产品不匹配 | 无任务；错误日志说明 SN 产品编码不属于请求明细 |
| HVR05-06 | [JSON](test_data/payloads/hvr05_06.json) / [curl](test_data/curl/hvr05_06.sh) | 同一个产品的两条 SN 使用同一 productSN；预期 BUS01 重复 SN | 无任务；日志包含重复 SN 和产品编码 |
| HVR05-07 | [JSON](test_data/payloads/hvr05_07.json) / [curl](test_data/curl/hvr05_07.sh) | SN 行省略 V3.2 必填 `productSN`；预期 REQ01 字段路径错误 | 无任务；日志保留完整 `snList[0].productSN` 路径 |
| HVR05-08 | [JSON](test_data/payloads/hvr05_08.json) / [curl](test_data/curl/hvr05_08.sh) | 原材料数量 3，省略 `snList`；预期成功 | 任务存在，SN 计划列表为空，实盘结果仍为空 |
| HVR05-09 | [JSON](test_data/payloads/hvr05_09.json) / [curl](test_data/curl/hvr05_09.sh) | 两个 SN 产品各需数量 1，只提供成品 SN；预期 BUS01 部分清单错误 | 无任务或成功幂等行；日志指出缺失半成品 SN 记录 |

所有测试请求均使用不同 `countOrderNo`。逐例记录时间、请求/响应、任务 ID、日志和幂等 ID；失败用例不清理或覆盖证据。


## SN 身份与引用补充场景（HVR05-10–12）

先完成项目主线 API07 产品、API01 入库及 FLOW-IN 实际 Picking。HVR05-10 使用该 Picking 实际生成的 SN `HVR-FLOW-SN-001`，并使用独立的未收货测试 SN；不依赖 API04 回传是否成功。该专项盘点单仍只保存客户指令，不生成实盘结果，不访问或改动 `stock.quant`，也不修改主线盘点单。

| HVR | 请求 | 操作与预期 | ORM / 日志核验 |
|---|---|---|---|
| HVR05-10 | [JSON](test_data/payloads/hvr05_10.json) / [curl](test_data/curl/hvr05_10.sh) | 同一成品明细引用 FLOW-IN 实际收货 Picking 生成、由 API04 读取的 `HVR-FLOW-SN-001`，以及一条尚未入库 SN；明细数量 2、每条 SN quantity=1；预期成功 | 保存的盘点计划保留两条 SN；只保存客户盘点计划，不创建 `stock.lot` / 实盘结果，不要求计划中的每条 SN 已入库；不依赖已归档 HVR01-29 |
| HVR05-11 | [JSON](test_data/payloads/hvr05_11.json) / [curl](test_data/curl/hvr05_11.sh) | 成品与半成品使用相同 productSN 文本、不同 productCode；预期成功 | 两条计划记录分别关联对应 productCode；不可按 SN 文本全局去重 |
| HVR05-12 | [JSON](test_data/payloads/hvr05_12.json) / [curl](test_data/curl/hvr05_12.sh) | 同一产品的相同 productSN 分在两个托盘；预期 BUS01 重复 SN | 不创建盘点订单或成功幂等记录；错误日志记录产品、SN 及两个托盘上下文 |

所有新增实例初始均为 `NOT RUN`；自动化测试结果不代替人工验收。
