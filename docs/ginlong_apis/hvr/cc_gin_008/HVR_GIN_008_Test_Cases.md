# CC-GIN-008 人工 HVR 测试用例

每个请求通过 `test_data/send_payload.sh` 发送。API01/03/05 分别验证两轮完整生命周期：Add → Delete → 取消后相同 Payload Add → Delete，以及 Add → Delete → 取消后不同 Payload Add → Delete；同时验证有效记录重复 Add 拒绝、重新 Add 后重复 Add 拒绝。首次 Delete 成功取消后，对同一业务键再次发送 Del（先相同、再修改非键字段的 Payload）均应返回业务错误，不得重放历史成功响应；重新 Add 后新的 Del 应成功。API01/03/05 另用项目 B Token 在项目 A 记录仍有效时尝试相同 Add。此处是人工 HVR 场景准备，不代表已执行；CC-GIN-008 的独立人工 HVR 仍依 Human Review 决定为 N/A，场景留作后续集成参考。

| 用例 | 操作与 Payload | 预期响应 | Odoo 核对 |
|---|---|---|---|
| HVR-008-01 API01 | `api01_add.json` 使用项目 A 并重复 Add；有效时用项目 B Token 发送相同 Add；发送 `api01_delete.json`；已取消后用原 Add 报文重发，应成功；再次 Del 应成功。再以 `api01_add_changed.json` 创建新生命周期，重复 Add 应拒绝；Del 成功后，对相同及修改 remark 的 Del 重发均应报错。 | 首次/重新 Add Y；有效期内重复或跨 project Add N/IDM02；每个有效生命周期首次 Del Y；仅有 cancel 历史时 Del N/BUS01，不论 Payload 相同或不同；重新 Add 后 Del Y。 | 保留三条历史 Order（最终均 cancel），最后一条明细反映 changed Payload；无有效 `inboundOrderNo`；只为实际成功执行的 Add/Del 保存幂等记录，拒绝的重复 Del 仅追加 API 错误日志；跨 project 错误不含项目 A 单据详情。 |
| HVR-008-02 API03 | 按 API01 的生命周期顺序，使用 `api03_add.json`、`api03_delete.json`、`apd.i03_add_changejson`。跨 project 请求只在项目 A 出库单有效时发送。 | 与 API01 相同的生命周期预期，重复码 IDM02。 | 保留取消历史；新单归项目 A；全局有效 `outboundOrderNo` 唯一；业务明细字段未因重试而变化。 |
| HVR-008-03 API05 | 按 API01 的生命周期顺序，使用 `api05_add.json`、`api05_delete.json`、`api05_add_changed.json`。跨 project 请求只在项目 A 盘点单有效时发送。 | 与 API01 相同的生命周期预期，重复码 IDM02。 | 保留取消历史；新单归项目 A；全局有效 `countOrderNo` 唯一；API05 的实盘结果模型不被 Add 订单创建。 |
| HVR-008-04 API07 | 使用 `api07_add.json` 首次新增并重复 Add；在 Odoo 产品界面归档该变体；再发原 Add 并重复；再次归档后发送 `api07_add_changed.json` 并重复。 | 首次 Add Y；有效期重复 Add N/IDM07；归档后 Add Y 并恢复；恢复后的重复 N/IDM07；第二次归档后不同 Payload Add Y，之后重复 N/IDM07。 | 归档/恢复前后 `product.product` ID 相同；始终只有一条 active `(owner, productCode)`；不产生新的有效变体；模板共享属性保持一致。 |

## 日志与幂等核验

在 Odoo **WorldDepot → Ginlong APIs → API 日志**检查每次请求的 API、业务键、响应和错误码；在 **WorldDepot → Ginlong APIs → 幂等记录**按 API/业务键查看不同事件键及历史结果。每次手动失败/通过都记录日志 ID；日志及幂等历史不得删除或重置。

## 结果填写

在 `HVR_GIN_008_Execution_Record.md` 写入实际响应、记录 ID、事件键、证据路径和 PASS/FAIL/BLOCKED。没有实际证据的实例保持 NOT RUN。
