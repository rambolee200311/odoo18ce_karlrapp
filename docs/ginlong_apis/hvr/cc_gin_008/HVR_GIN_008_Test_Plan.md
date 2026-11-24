# CC-GIN-008 人工 HVR 测试计划

## 范围

人工验证 API01/03/05 订单 Add 的全局业务键、Add/Delete/重新 Add 生命周期，以及 API07 `(owner, productCode)` 归档后恢复原变体。API01/03/05 的 project A/B 测试验证跨 project 冲突不泄露源单据信息；新订单仍应归入请求 API User 的项目。

自动化测试覆盖数据库并发和组件回归；本 HVR 不调用真实 Ginlong 或 KR。模板同步 BLOCKED 按批准例外保留。

## 覆盖矩阵

| 对象 | 有效键 | 失效方式 | 相同 Payload 再 Add | 不同 Payload 再 Add | 跨 project Add |
|---|---|---|---|---|---|
| API01 入库单 | `inboundOrderNo`（全局） | API01 `Del`，状态变为 `cancel` | 取消后允许；有效时拒绝 | 取消后允许；有效时拒绝 | project B 重复 Add 拒绝且不泄露项目 A 单据 |
| API03 出库单 | `outboundOrderNo`（全局） | API03 `Del`，状态变为 `cancel` | 取消后允许；有效时拒绝 | 取消后允许；有效时拒绝 | 同上 |
| API05 盘点单 | `countOrderNo`（全局） | API05 `Del`，状态变为 `cancel` | 取消后允许；有效时拒绝 | 取消后允许；有效时拒绝 | 同上 |
| API07 产品 | `(owner, productCode)` | Odoo Backend 归档变体 | 归档后 Add 恢复原变体；有效时拒绝 | 归档后允许且恢复原变体；有效时拒绝 | 不适用 |

## 测试数据与证据

- API01/03/05 示例使用 Owner `HVR01-20261121-OWNER-A`、Product `HVR01-20261121-PROD-COMMON`。运行前须核对该产品变体有效且 owner 匹配；不存在时先用已批准的 API07 产品准备流程建立，不要改变本包业务规则。
- API07 使用唯一 Owner/Product 前缀 `HVR08-20261124-*`；API07 按既有规则可创建缺失货主档案。
- 请求及不同 Payload 位于 `test_data/payloads/`；`send_payload.sh` 接收项目 A/B/API07 凭据选择。
- 每例保存三字段 Ginlong 响应、Odoo API 日志 ID、幂等记录/事件键、Order/Product ID 和关键状态截图或只读 ORM 核验输出。

## 完成判据

每项核实：有效记录存在时任意 Add 均为 `returnStatus=N` 且对应重复错误；Delete 只将当前 API User 项目内订单改为 `cancel`；失效后重建成功并保留历史；API07 恢复同一归档 `product.product`，不得产生第二个有效变体；跨 project 冲突不暴露其他项目单据信息。全部结果由负责人填写执行记录。
