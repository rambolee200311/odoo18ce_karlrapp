# CC-GIN-007 人工 HVR 测试计划 v0.1 Draft

| 项目 | 内容 |
|---|---|
| 状态 | 执行记录已更新：HVR-API01-01–06 完成；HVR-API01-07 为 API04 辅助出站核对，NOT RUN |
| 冻结依据 | CC-GIN-007 v1.0；TDD v1.5；SRS v1.2 |
| 数据库 | 既有 odooce_karlrapp |
| 模块基线 | ginlong_apis 18.0.2.0.40；8099 活动进程尚未确认加载 .40 |
| 外部系统 | 不访问真实 Ginlong、KR 或 Gateway；API04 仅发送到本机 Mock 接收器 |
| 用例范围 | API01 六个 HTTP 实例；API04 一个实际数据来源界面检查 |

## 1. 范围

本包只验证 CC-GIN-007 冻结的 API01 业务类型条件化预报行为，并复核 API04 继续读取已保存实际 Picking/Move Line。它不验证预报与实收差异比较，不实施 API04 改动，不测试 API05，也不重跑已通过的自动化测试矩阵。

API01 成功表示“客户预报被接收并保存在 Order”，不表示仓库已完成收货。API01 不创建 Picking、Move、Lot、Package 或库存记录。

## 2. 执行清单

人工执行下列 **6 个 API01 curl 脚本**。HVR-API01-07 是额外的 API04 出站 UI/Mock 核对，不是 API01 请求；CC-TEST-069 已通过并满足本 CC 的 API04 来源回归要求，因此此项 NOT RUN 不阻塞 CC-GIN-007 关闭。

| 顺序 | HVR | 唯一验证点 | 文件 | 预期 |
|---:|---|---|---|---|
| 1 | HVR-API01-01 | STANDARD、无 snList，SN 管理产品仍按非保税分支接单 | [JSON](test_data/payloads/hvr_api01_01.json) / [curl](test_data/curl/hvr_api01_01.sh) | Y/OK；订单无 SN 预报行 |
| 2 | HVR-API01-02 | STANDARD、畸形 snList 不处理/不校验/不保存；日志保留原请求 | [JSON](test_data/payloads/hvr_api01_02.json) / [curl](test_data/curl/hvr_api01_02.sh) | Y/OK；订单无 SN 行，API 日志请求保留该字段 |
| 3 | HVR-API01-03 | 保税类型下 3 产品/3 托盘混装和逐产品总数核对 | [JSON](test_data/payloads/hvr_api01_03.json) / [curl](test_data/curl/hvr_api01_03.sh) | Y/OK；保存 9 条预报分配行；无库存对象 |
| 4 | HVR-API01-04 | 保税类型原材料未提供 snList | [JSON](test_data/payloads/hvr_api01_04.json) / [curl](test_data/curl/hvr_api01_04.sh) | Y/OK；保存产品/总量，不生成托盘或 SN 子行 |
| 5 | HVR-API01-05 | 原材料数量 12 按 5/7 分托盘并与 SN 产品共托 | [JSON](test_data/payloads/hvr_api01_05.json) / [curl](test_data/curl/hvr_api01_05.sh) | Y/OK；两条原材料预报分配，数量分别对平 |
| 6 | HVR-API01-06 | SN 管理产品的单条 SN quantity=3 | [JSON](test_data/payloads/hvr_api01_06.json) / [curl](test_data/curl/hvr_api01_06.sh) | N；拒绝单条 SN 数量；无订单/明细/成功幂等 |
| 7（补充，非关闭门槛） | HVR-API01-07 | API04 来源为已保存选中的实际 Picking/Move Line | Odoo Form + 本机 Mock；[预期出站报文](test_data/expected/hvr_api01_07_api04_body.json)仅供比对，不是输入 | 如执行，Mock 收到所选实绩；不核对预报/实收差异；当前 NOT RUN |

## 3. 产品与单号

固定产品编码是此前本地 HVR 记录使用的标识，不代表当前数据中仍存在。执行前通过只读 ORM 检查确认 Owner A 变体唯一且 tracking 正确。不得通过直接 SQL 或重建库存数据补齐前置条件。

六个 API01 单号互不相同，仅供一次人工发送。请求会产生持久化 Order、日志和幂等记录；本包没有清理脚本，不要重放已成功 Add。

## 4. API01 核查方法

每个响应记录 HTTP 状态码、returnStatus、exceptionInfo 和 operationTime。成功响应仅含 Ginlong 三字段，状态为 Y/OK。

在 Odoo 中打开 WorldDepot → Inbound → Orders，按本例 inboundOrderNo 搜索单据，确认货主、单号、业务类型、产品及数量。通过只读 ORM 脚本核对结构化预报行的产品编码、SN、数量、托盘码，以及关联 Picking。

在 WorldDepot → Ginlong APIs → API 日志按业务键查询请求/响应和状态。HVR-API01-02 应能在请求日志看到畸形 snList，但 Order 预报数据中不得出现它。HVR-API01-06 应能看到拒绝原因及完整产品/SN/托盘诊断；协议响应受 40 字符限制。

## 5. API04 来源检查条件

HVR-API01-07 仅在开发数据库中找到一张**已完成且关联入库 Order** 的测试 Picking，并且其 Move Line 已保存产品、数量、Lot/SN、托盘、实际操作人编码和操作时间时执行。若找不到，登记 BLOCKED；不得为本包新建、确认或过账 Picking，不得用 API01 预报代替。

启动本机 Mock 接收器，记录原 API04 Endpoint。Odoo 设置中临时将 API04 Endpoint 指向本机 Mock，保存。打开 WorldDepot → Inbound → Orders，搜索关联 Order，在 Ginlong 回传数据 Notebook 中只勾选本次 Picking 并保存；打开 Picking 的 Ginlong 回传数据页核实实际操作人编码和时间已保存。回到 Order 点击“回传锦浪：入库完成”。

核对 Mock 实际收到的 POST JSON 与被选 move line 数据一致，核对 API 日志有本次请求/响应。恢复原 API04 Endpoint 并停止 Mock。不得将请求发送到真实 Ginlong。

## 6. 判定

- PASS：人工步骤已执行，响应和实际 Odoo 数据满足预期，证据路径已填写。
- FAIL：结果与预期不符；保留请求、响应和日志证据，不删除失败记录。
- BLOCKED：服务版本、产品、Token 或 API04 Picking 前置条件缺失。
- NOT RUN：尚未执行；自动化测试通过不能使其变为 PASS。

模板源同步继续按 CC 冻结记录为 BLOCKED（既有批准例外），与本 HVR 逐例判定分开。
