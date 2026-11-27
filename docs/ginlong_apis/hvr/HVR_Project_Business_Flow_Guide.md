# Ginlong 项目 HVR 执行入口

**Codex 模拟 HVR：PASS**，运行 `CC005-FINAL-20261127-01`，代码版本 `ginlong_apis 18.0.2.0.56`。  
**项目负责人真实人工 HVR：NOT RUN**。  
**真实 Ginlong、生产及 Karl Rapp Gateway 联调：NOT RUN**。

本页只作为入口，避免不同 HVR 目录中的历史报文被误当成当前执行数据。

## 当前唯一人工 HVR 数据集

- 操作指南：[CC-GIN-005 真实人工 HVR 操作指南](project_flow/CC-GIN-005_Manual_HVR_Operator_Guide.md)
- 唯一可执行报文目录：[real_hvr_20261128/payloads](project_flow/real_hvr_20261128/payloads)
- 数据集说明及执行顺序：[real_hvr_20261128/README.md](project_flow/real_hvr_20261128/README.md)
- 人工结果记录：[HVR 项目业务流人工执行记录](HVR_Project_Business_Flow_Execution_Record.md)
- Codex 模拟 HVR 证据：[CC-GIN-005 模拟 HVR 最终报告](project_flow/CC-GIN-005_Final_Simulation_HVR_Report.md)

真实人工验收时，先阅读操作指南，再严格按 README 中唯一顺序执行。API02、04、06、08、10 必须由 Odoo 中对应业务按钮生成请求；不要手工构造其 JSON。

## 业务主链基线

同一个 Project、Owner、Warehouse、产品及库存主链：

`API07 → API09 期初 → API01 → API02 → 一张入库 Picking → API04 → API09 入库后 → API03 → 一张出库 Picking → API06 → API08 → API09 出库后 → API05 → 实盘录入 → API10`

一步入库、一步出库。只有完成的入库和出库 Picking 改变库存；收货确认、备货回传、离仓状态回传、库存查询、盘点指令和盘点完成回传均不得额外移动库存。API08 只使用 Ginlong V3.2 的 `outboundOrderNo`、`action`、`shipmentConfirmed` 三个请求字段。

## 本地环境

- Odoo：`http://127.0.0.1:8099/odoo`
- HVR UI 用户：`hvr.ginlong.operator`
- API02 Mock：`127.0.0.1:18102`
- API04 Mock：`127.0.0.1:18104`
- API06、08、10 Mock：`127.0.0.1:18106`
- 本轮检查：Odoo 登录页及三个 Mock 健康检查均返回 HTTP 200；数据库中模块版本为 `18.0.2.0.56`。

## 历史材料

其他 HVR 目录、旧测试运行及归档 payload 保留作历史证据，不是本次人工验收的执行清单。不得从多个目录拼接报文，也不得删除、取消或重置历史业务记录来复用测试数据。
