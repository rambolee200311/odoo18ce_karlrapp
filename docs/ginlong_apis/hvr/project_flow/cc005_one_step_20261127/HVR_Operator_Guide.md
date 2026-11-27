# CC-GIN-005 一步出入库主链 HVR 操作指南

**本指南对应运行：** `R8239A3`（2026-11-27）  
**目的：** 记录本轮实际执行方式及后续重跑前置条件。它不是“全流程已通过”的说明，也不预填真实人工 HVR 结果。

## 业务约束

- 一步入库、一步出库：每张订单最多执行一张对应方向的实际 Picking。
- 不创建内部备货 Picking，不配置或切换多步 Route。
- API02 收货确认、API06 备货完成（回传动作）、API08 实际离仓确认及 API10 回传均不得额外产生库存移动；只有实际 Done 的 incoming/outgoing Picking 改变物理库存。
- API04 只取实际 Done/Incoming Picking；API06 取实际备货记录；API08 的 Ginlong V3.2 报文只有出库单号、Action、发货确认状态，不含托盘字段。
- 盘点从实际剩余库存执行，实盘结果通过 WorldDepot 盘点结果录入，不使用 `stock.quant` 代替实盘。

## 本轮数据和已完成步骤

本轮单号分别为：

- 入库：`HVR005-20261127-R8239A3-IN-001`
- 出库：`HVR005-20261127-R8239A3-OUT-001`
- 盘点预定：`HVR005-20261127-R8239A3-COUNT-001`
- 货主：`HVR01-20261121-OWNER-A`；仓库：`KRWH`
- 产品/托盘/数量见同目录 `run_manifest.json` 和最终报告。

已通过浏览器和真实本地 HTTP 完成 API07、API09 期初、API01、API02（先 N，确认收货后 Y）、一张 incoming Picking、API04、API09 入库后、API03、一张 outgoing Picking、API06、API09 出库后、API05 和 API10。入库 Picking 为 `KRWH/KRIN/01180`，Done；出库 Picking 为 `KRWH/KROUT/00749`，Done，关联出库单 `OO202611271380`。当前接口与 Mock 记录详见[模拟 HVR 最终报告](CC-GIN-005_Simulated_HVR_Final_Report.md)及[本次 ORM 证据](evidence/api04_api06_api10_nonserial_orm_evidence_20261127.json)。

非 SN RAW 的 API04/06/10 行均按已确认规则使用 `productSN=productCode`，数量取实际 Picking 或实盘记录；SN 产品使用实际 SN。旧 API04 Log 9499 的 `productSN:false` 是修正前历史证据，修复后 Log 9533 已通过本地 Mock。回传期间没有改变产品追踪方式、创建虚假 SN 或改动库存。

## 当前仍未完成的事项

API04、API06、API09 出库后查询、API05 和 API10 已完成。不要再建第二张 outgoing Picking，也不要删除、冲销当前已过账 Picking。

唯一未完成的主链回传项为 **API08**。当前出库订单 `HVR005-20261127-R8239A3-OUT-001` 的状态仍是 `Planning`，`actual_outbound_datetime` 为空，现有页面没有可执行的“实际离仓确认”状态按钮；当前 API08 按钮还依赖空的 Ginlong 发货明细表。不得手工复制 Picking 明细或填写虚构离仓时间来绕过。完成已批准的一步出库状态操作/API08 设计后，再只补测 API08。

## 本轮主链验收结果

1. API07、API09 期初、API01、API02（N/Y）、实际入库 Picking、API04、API09 入库后、API03、实际出库 Picking、API06、API09 出库后、API05、实盘结果及 API10 均已在同一主链完成。
2. API04、API06、API10 的 RAW 行以 `productSN=productCode` 回传；实际数量分别按 Picking move line 或实盘结果取值。
3. 出库后物理库存为 FG=2、SF=2、RAW=9，预留量为 0。API04/06/10 的回传没有产生库存移动。
4. API08 暂 BLOCKED，具体差异和截图见最终报告；不得用人工填写重复明细替代实际离仓业务操作。

## 每个节点的验收记录

本指南记录的是 Codex 浏览器模拟结果。API08 补测前，保留本次已通过步骤的证据，不重复已完成接口；只使用本地 Mock，不访问真实 Ginlong。库存节点使用 Odoo ORM 只读核对，真实人工验收的 PASS/FAIL 仍由项目负责人填写，Codex 模拟结果不能代签。
