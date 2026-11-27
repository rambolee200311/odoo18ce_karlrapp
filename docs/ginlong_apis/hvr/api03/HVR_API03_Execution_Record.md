# API03 人工 HVR 执行记录

本文件初始状态为 NOT RUN。只有执行人实际发送请求并检查 Odoo 业务记录、API Log/幂等记录后，才填写结果。

| HVR | 实际 HTTP 状态与响应摘要 | Odoo 订单/状态/明细证据 | API Log / 幂等 ID | 截图或备注 | 判定 | 执行人/日期 |
|---|---|---|---|---|---|---|
| API03-HVR-01 首次 Add | — | — | — | — | NOT RUN | — |
| API03-HVR-02 相同及不同内容重复 Add | — | — | — | — | NOT RUN | — |
| API03-HVR-03 Edit 与重复 Edit | — | — | — | — | NOT RUN | — |
| API03-HVR-04 首次 Del、重复 Del、取消后 Edit | — | — | — | — | NOT RUN | — |
| API03-HVR-05 取消后相同/不同 Payload 重新 Add | — | — | — | — | NOT RUN | — |
| API03-HVR-06 跨货主同产品编码映射 | — | — | — | — | NOT RUN | — |
| API03-HVR-07 未知 owner / 缺失产品组合 | — | — | — | — | NOT RUN | — |
| API03-HVR-08 必填与 DECIMAL 类型校验 | — | — | — | — | NOT RUN | — |

## 执行环境

| 项目 | 执行时填写 |
|---|---|
| Odoo URL / 数据库 | `http://127.0.0.1:8099` / `odooce_karlrapp` |
| ginlong_apis 版本 | — |
| API User 对应项目 | `HVR01-20261121 API01 HVR Project`；复用 API01 HVR 的 `hvr_api01_manual` |
| Token 获取时间（不记录 Token） | — |
| 执行开始/结束时间 | — |
| 执行人 | — |

## 最终判定

- 人工结论：`NOT RUN`
- 未通过/阻塞用例：—
- 遗留问题：—
- 执行人签字/日期：—

## 初次请求失败记录及修正

2026-11-25 首轮 API03-HVR-01 使用了与 API01 不同项目的 API User 和 HVR-GIN005 收货方，真实 HTTP 请求均返回 `BUS01`，没有创建出库订单。API 日志 7560、7562、7565、7567 显示请求项目为 `HVR07-20261119 API07 HVR Project`，而请求的 `HVR-GIN005 recipient` 属于另一个项目。该结果是 HVR 测试上下文不一致，不代表 API03 Add 成功或业务订单已存在。

本次修正后，API03 payload 改为 API01 HVR 的项目上下文、Owner A 和产品；跨货主专项仅保留同项目 Owner B。上述失败证据保留，修正后的人工请求尚未执行，需从 `api03_01_add.json` 重新开始，并在执行记录中填入新的结果。
