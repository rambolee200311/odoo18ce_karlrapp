# API04 入库完成人工 HVR 执行记录

> 所有场景初始 NOT RUN。CC-GIN-009 不要求独立人工 HVR；本记录供 CC 关闭后原项目验收使用。Codex 不代填人工结果。

## 环境

| 项目 | 记录 |
|---|---|
| Odoo 数据库 | odooce_karlrapp（本地开发环境） |
| Odoo Backend | http://127.0.0.1:8099/odoo；执行前由用户确认可用 |
| API04 Mock | http://127.0.0.1:18104/API/WMS_JSON/TPL_Inbound_Completion |
| Mock 捕获 | test_data/received.jsonl |
| Ginlong 真实环境 | 未连接；本 HVR 不访问真实 Ginlong |
| 执行者/日期 | 待人工填写 |

## 实例结果

| HVR | 场景 | 状态 | Order / Reference | Picking | Mock 行 | API Log ID | 人工证据 |
|---|---|---|---|---|---|---|---|
| HVR-API04-01 | 单张 Done/Incoming Picking 回传 | NOT RUN |  |  |  |  |  |
| HVR-API04-02 | 同订单两张 Picking 独立批次 | NOT RUN |  |  |  |  |  |
| HVR-API04-03 | 同一成功 Picking 重复点击：默认未成功项、回传全部确认、取消 | NOT RUN |  |  |  |  |  |
| HVR-API04-04 | 失败后人工再次点击重试 | NOT RUN |  |  |  |  |  |
| HVR-API04-05 | 当前订单无合格 Picking | NOT RUN |  |  |  |  |  |
| HVR-API04-06 | 不合格 Picking 排除 | NOT RUN |  |  |  |  |  |
| HVR-API04-07 | 成功、明确失败、首次发送混合；默认仅未成功项 | NOT RUN |  |  |  |  |  |
| HVR-API04-08 | unknown 风险提示：取消为零发送，确认后真实重试 | NOT RUN |  |  |  |  |  |
| HVR-API04-09 | 同 Picking 跨标签页并发及连续点击，HTTP 恰一次 | NOT RUN |  |  |  |  |  |

## 验收结论

- 人工总判定：待验收人填写 PASS / FAIL / BLOCKED。
- 验收人：待填写。
- 日期：待填写。
- 备注：本机 Mock 验证与真实 Ginlong 分批协议确认分开记录。
- 完整重复回传场景另见 [通用执行记录](../HVR_Callback_Repeat_Confirmation_Execution_Record.md)；以上历史行未经人工重跑不得改为 PASS。

## CC-GIN-010 项目级重复回传场景

使用与 API02 相同的独立人工 HVR 订单 `HVR-GIN010-MANUAL-IN-20261125-01`（Order ID `2011`），由业务验收人在 UI 中完成真实收货 Picking；Codex 模拟单不混入人工记录。

| 场景 | 状态 | Picking / Order | Mock 行增量 | API Event / Log | 人工证据 |
|---|---|---|---|---|---|
| 多 Picking 首次独立回传 | NOT RUN |  |  |  |  |
| 成功/明确失败/首次混合，默认仅回传未成功项 | NOT RUN |  |  |  |  |
| 回传全部确认与取消分支 | NOT RUN |  |  |  |  |
| unknown 风险取消/确认重试 | NOT RUN |  |  |  |  |
| 连续点击及跨标签页相同 Picking 竞争 | NOT RUN |  |  |  |  |
