# CC-GIN-008 人工 HVR 测试用例

每个请求通过 `test_data/send_payload.sh` 发送。API01/03/05 的每个测试生命周期按 Add → 有效记录重复 Add → Delete → 相同 Payload Add → 再次 Delete → 不同 Payload Add → 再次重复 Add 执行；API01/03/05 另用项目 B Token 在项目 A 记录仍有效时尝试相同 Add。

| 用例 | 操作与 Payload | 预期响应 | Odoo 核对 |
|---|---|---|---|
| HVR-008-01 API01 | `api01_add.json` 使用项目 A；再用相同文件重复；用项目 B Token 发送相同文件；然后发送 `api01_delete.json`；之后依次发送原 Add、Delete、`api01_add_changed.json`、再次 changed Add。 | 首次 Add Y；有效期内相同/跨 project Add N/IDM02；Delete Y；取消后两次新生命周期 Add 均 Y；新生命周期重复 Add N/IDM02。 | 保留旧 cancel Order；新 Order 归项目 A；始终最多一条有效 `inboundOrderNo`；历史幂等记录保留；跨 project 错误不含项目 A 的单据详情。 |
| HVR-008-02 API03 | 按 API01 的生命周期顺序，使用 `api03_add.json`、`api03_delete.json`、`api03_add_changed.json`。跨 project 请求只在项目 A 出库单有效时发送。 | 与 API01 相同的生命周期预期，重复码 IDM02。 | 保留取消历史；新单归项目 A；全局有效 `outboundOrderNo` 唯一；业务明细字段未因重试而变化。 |
| HVR-008-03 API05 | 按 API01 的生命周期顺序，使用 `api05_add.json`、`api05_delete.json`、`api05_add_changed.json`。跨 project 请求只在项目 A 盘点单有效时发送。 | 与 API01 相同的生命周期预期，重复码 IDM02。 | 保留取消历史；新单归项目 A；全局有效 `countOrderNo` 唯一；API05 的实盘结果模型不被 Add 订单创建。 |
| HVR-008-04 API07 | 使用 `api07_add.json` 首次新增并重复 Add；在 Odoo 产品界面归档该变体；再发原 Add 并重复；再次归档后发送 `api07_add_changed.json` 并重复。 | 首次 Add Y；有效期重复 Add N/IDM07；归档后 Add Y 并恢复；恢复后的重复 N/IDM07；第二次归档后不同 Payload Add Y，之后重复 N/IDM07。 | 归档/恢复前后 `product.product` ID 相同；始终只有一条 active `(owner, productCode)`；不产生新的有效变体；模板共享属性保持一致。 |

## 日志与幂等核验

在 Odoo **WorldDepot → Ginlong APIs → API 日志**检查每次请求的 API、业务键、响应和错误码；在 **WorldDepot → Ginlong APIs → 幂等记录**按 API/业务键查看不同事件键及历史结果。每次手动失败/通过都记录日志 ID；日志及幂等历史不得删除或重置。

## 结果填写

在 `HVR_GIN_008_Execution_Record.md` 写入实际响应、记录 ID、事件键、证据路径和 PASS/FAIL/BLOCKED。没有实际证据的实例保持 NOT RUN。
