# API09 库存查询项目 HVR 用例

**状态：** 全部 `NOT RUN`；人工结论由项目验收人填写。项目主链数据、步骤和库存变化基线以[项目级仓库业务流程 HVR](../HVR_Project_Business_Flow_Guide.md)为准。

## 主线快照

主线在相同 Owner=`HVR01-20261121-OWNER-A`、Warehouse=`KRWH` 和 SKU=`HVR-PROJECT-FLOW-20261125-SN-001` 下执行三次查询：

| 用例 | 前序实际业务 | 目标 SKU 的预期物理 quantity | 约束 |
|---|---|---:|---|
| FLOW-09A | API07 建档后、实际入库前 | 0 或未出现在库存清单 | 若查询显示既有正库存，停止并换整套新 SKU；不得调库存归零 |
| FLOW-09B | API01 Order 关联的 Incoming Picking 已由 WMS Validate | 2 | 两个实际序列号各 1；API02/API04 回传不产生库存 |
| FLOW-09C | API03 Order 关联的 Outgoing Picking 已由 WMS Validate | 1 | 实际发出 SN-001，SN-002 留在库内；API06/API08 回传不产生库存 |

三次均使用 [`api09_owner_warehouse_query.json`](../project_flow/test_data/payloads/api09_owner_warehouse_query.json)。API09 返回该 Owner/仓库完整库存清单，只核对主线 SKU，不要求列表中只有该 SKU。响应数量是实际物理 `quantity`，不扣 reserved quantity。查询前后库存应相同。

## 独立只读与参数隔离场景

以下场景在主线完成后运行，所有请求只读，不改变 Owner、SKU、Picking、托盘、SN 或库存。运行前保存完整响应及 API Log ID；未知编码不得替换成真实编码。

| 用例 | 请求 | 预期及判定 |
|---|---|---|
| API09-HVR-UNK-OWNER | [`api09_unknown_owner.json`](../project_flow/test_data/payloads/api09_unknown_owner.json) | 现有实现对不存在 Owner 返回成功空清单：`returnStatus=Y`、`inventoryList=[]`，不能包含任何其他 Owner 的产品。若同仓已有其他 Owner 的正库存，将其中一个 SKU 作为不泄露哨兵核对；若没有哨兵库存，只能记录“未知 Owner 返回空”，不能声称完成了跨 Owner 有货隔离证明。 |
| API09-HVR-UNK-WH | [`api09_unknown_warehouse.json`](../project_flow/test_data/payloads/api09_unknown_warehouse.json) | 现有实现返回 Ginlong 错误三字段（`returnStatus=N`、`exceptionInfo` 为 BUS01 类错误、`operationTime`），不得带 `inventoryList` 或返回 KRWH 库存。 |
| API09-HVR-MISSING-OWNER | [`api09_missing_owner.json`](../project_flow/test_data/payloads/api09_missing_owner.json) | 必填校验拒绝，请求不得返回库存，且库存保持不变。 |
| API09-HVR-MISSING-WH | [`api09_missing_warehouse.json`](../project_flow/test_data/payloads/api09_missing_warehouse.json) | 必填校验拒绝，请求不得返回库存，且库存保持不变。 |

请求入口为 `POST /api/ginlong/TPL_Stock_Query`，认证 Header 为 `Authorization: <access_token>`，不加 `Bearer`。可使用项目统一脚本发送：

```bash
bash docs/ginlong_apis/hvr/project_flow/test_data/send_inbound_payload.sh \
  TPL_Stock_Query docs/ginlong_apis/hvr/project_flow/test_data/payloads/api09_unknown_owner.json
```

HTTP/响应断言之外，还应核对相应时间点前后的 Odoo 库存记录未改变，并检查 API Log。不要通过建立虚拟库存来制造隔离哨兵；如没有已有的其他 Owner 库存，则该隔离子断言记 `BLOCKED`。
