# CC-GIN-005 模拟 HVR 执行记录 — HVR005-20261127-RUN03

状态：进行中。不得把未执行项写为 PASS。

| 步骤 | 预期 | 实际结果/证据 | 状态 |
|---|---|---|---|
| 运行基线与 Mock preflight | 8099 可用、模块版本一致、Mock 本地健康 | 详见当前对话启动前证据；回归 ginlong_apis 95/95，worlddepot 8/8 | PASS（准备） |
| API07 Add FG/SF/RAW | 三个 owner+productCode 变体/共享属性正确 | 待执行 | NOT RUN |
| API09 入库前 | 三个新 SKU 无正库存 | 待执行 | NOT RUN |
| API01 Add | 仅入库预报，不生成实际库存/作业 | 待执行 | NOT RUN |
| API02 planning=N、收货确认后=Y | 同一订单状态回传；无库存移动 | 待执行 | NOT RUN |
| Incoming Picking | UI 创建并验证唯一一张 Picking | 待执行 | NOT RUN |
| API04 | 实际 Done/Incoming Picking 回传 | 待执行 | NOT RUN |
| API09 入库后 | FG3/SF3/RAW12 | 待执行 | NOT RUN |
| API03 Add | 同主链产品与项目/货主出库指令 | 待执行 | NOT RUN |
| Outgoing Picking | UI 完成唯一一张；整托P3 + 拆托P1 FG SN001 | 待执行 | NOT RUN |
| API06 | 备货回传，物理库存不再次变化 | 待执行 | NOT RUN |
| API08 | 仅订单状态和三字段回传，物理库存不变化 | 待执行 | NOT RUN |
| API09 出库后 | FG2/SF2/RAW9 | 待执行 | NOT RUN |
| API05 与实际盘点 | 盘点指令/实盘结果使用出库后库存 | 待执行 | NOT RUN |
| API10 | 实际盘点结果回传，不改变库存 | 待执行 | NOT RUN |
