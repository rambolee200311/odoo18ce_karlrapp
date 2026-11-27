# API07 产品档案 HVR 人工执行记录

> **HVR 状态：Frozen / Closed。** 项目负责人于 2026-11-21 批准关闭本轮 API07 人工验收。

## 执行信息

| 项目 | 记录 |
| --- | --- |
| HVR 包 | API07 产品档案 |
| 测试环境 | 本地 Odoo；数据库 `odooce_karlrapp` |
| 本地入口 | `POST http://127.0.0.1:8099/api/ginlong/TPL_Product_Master` |
| Odoo 后台登录名 | `hvr_api07_manual`（密码仅在被忽略的本地凭据文件中） |
| API User 认证 | API Key / API Secret 换取 Bearer Token；凭据仅在被忽略的本地凭据文件中 |
| 人工执行者 | 项目负责人（用户在会话报告） |
| 执行日期 | 2026-11-20–2026-11-21 |
| HVR 包版本 / Git commit | ____ |
| 原始响应与截图目录 | 用户在会话提供人工响应；本地 API 日志 ID 1724、1726、1995、1999–2021 及 Odoo ORM 记录作为佐证；未提供截图 |

本记录最初仅包含 Codex 的前置准备。经人工执行、日志/ORM 核对及项目负责人后续判定，HVR07-01–22 均记录为 PASS。HVR07-19 于 2026-11-21 01:21:35 返回成功；项目负责人明确确认 `productName=12345` 可接受，模板名称实际以文本 `'12345'` 保存，因此按该决定记 PASS。HVR07-22 也按项目负责人判定记 PASS，同时保留日志 2021 显示 `Invalid token`、未独立证明有效且无 Project Token 业务路径的证据限制。所有历史响应、错误、误用凭据及复测记录均保留。

## Codex 前置准备证据（不是 HVR 验收结果）

2026-11-20 使用项目现有 `venv`、`odoo.conf`、数据库 `odooce_karlrapp`，通过 `odoo-bin shell --no-http` 执行 `reset_api07_hvr.py`、`prepare_api07_hvr.py` 和只读 `verify_api07_hvr.py`。所有数据库读写均通过 Odoo ORM；未执行 SQL，也未发送 API07 业务用例请求。仅检查后台登录页、执行模块升级及后台账号登录核验。

| 数据 | ORM 核对结果 |
| --- | --- |
| HVR 货主 A / B | `res.partner` ID 742 / 743；编码分别为 `HVR07-20261119-OWNER-A`、`HVR07-20261119-OWNER-B` |
| 测试 Project | ID 146，关联货主 A 和现有仓库 ID 1 |
| HVR 后台登录用户 | `res.users` ID 59，登录名 `hvr_api07_manual`，具备 `stock.group_stock_manager`；未保留系统管理员组 |
| 有 Project 的 API User | ID 110，关联登录用户 ID 59、Project ID 146；Token 记录 ID 210，未输出 Token 值 |
| 无 Project 的 API User | ID 111，用户 ID 4，Project 为空；Token 记录 ID 211，未输出 Token 值 |
| 编辑基准产品 | 初始准备记录：EDIT-NAME 模板 ID 1098 / 变体 ID 1133；EDIT-REPEAT 模板 ID 1099 / 变体 ID 1134。复核时旧 ID 已不存在，EDIT-REPEAT 当前记录也未找到。2026-11-20 09:58，Codex 通过 ORM 将现有 EDIT-NAME 变体 ID 1544 / 模板 ID 1471 恢复为 HVR07-07 基准字段，供修复后人工复测 |
| 单位档案 | 既有“台”ID 31、“个”ID 30；另建临时同类别单位 `HVR07-20261119-UNIT-ALT` ID 35，与“台”同属 UoM 类别 ID 10 |
| 初始前置状态（首次人工请求前） | 测试产品通过服务方法建立；当时 ORM 核对为 0 条 API07 日志、0 条本轮幂等记录 |
| HTTP 服务 / 模块升级 | Odoo 已于本轮重新启动并监听 8099（PID 18645）；后台 `GET /web/login` 返回 HTTP 200。XML-RPC `button_immediate_upgrade` 已执行；模块状态 `installed`, 版本 `18.0.2.0.13`。日志未发现 ERROR/CRITICAL/Traceback；仅见 WorldDepot 既有 `create` 批量方法弃用警告 |
| 后台登录核验 | `hvr_api07_manual` 通过 XML-RPC 认证，用户 ID 59；已移除临时系统管理员权限，保留库存管理员权限 |
| API User 凭据 | API User ID 110 的 API Key 与 API Secret 已通过 ORM 设置；`verify_secret` 核验成功。API Key、Secret、Bearer Token 均只保存在 `test_data/.api07_hvr.env`，文件权限 `0600` 且被 `.gitignore` 忽略；现有 Bearer Token 有效期截至 `2026-11-27 01:23:36`。执行记录不保存任何凭据明文 |

前置准备 ID 仅用于定位当前开发数据库记录；执行 `reset_api07_hvr.py` 后会删除并重新生成，重新准备时须更新本表。

前述模块升级和账号登录验证不构成 API07 HVR。Codex 另曾使用独立临时编码做诊断 HTTP 请求；这些请求不计入人工 HVR，相关临时产品和幂等记录已清理，API 日志保留。HVR07-04 最初因对外返回通用 BUS01 而记为 PARTIAL；增加 BUS02 后，项目负责人于 2026-11-20 重新发送冲突请求并报告验证通过，现更新为 PASS。HVR07-05 半成品及 HVR07-06 成品的创建与 SN tracking 验证也已由项目负责人报告，并经 ORM、日志及幂等记录核实，现均更新为 PASS。HVR07-06 第二次 Add 因业务键已存在而返回 IDM07，属于预期重复新增拒绝，不影响首次创建结果。HVR07-07 的早期 Edit 问题及修复前证据见下文；项目负责人已使用目标 Payload 复测并报告返回 OK，ORM 与 API 日志核对确认既有产品被更新，现更新为 PASS。HVR07-09 首次请求因预置 EDIT-REPEAT 产品缺失而正确返回 BUS03；该请求后 Codex 补齐测试夹具，项目负责人随后连续两次 Edit 均返回成功，ORM 与日志确认重复 Edit 行为符合预期，现更新为 PASS。历史响应及问题证据均保留。

### API07 Edit 修复及 HVR07-07 复测结果

根因是旧 `api07` 实现把所有模板共享字段差异都当成冲突；同时在 Edit 目标不存在时会落到模板创建路径，导致 HVR 请求可能新建产品而非更新。版本 `18.0.2.0.26` 修复为：Edit 仅处理已存在的 `(owner, productCode)`，不存在时返回 `BUS03`；对既有产品允许更新名称、规格、单位及其他请求共享属性；同一 `productCode` 的 `productForm` 不一致仍返回 `BUS02`，不改档案。通过 Odoo 测试框架完成 5 项 API07 ORM/真实 HTTP 定向测试，结果 5 PASS、0 FAIL、0 ERROR，日志 `/tmp/ginlong_api07_editfix_final.log`。新 Odoo Shell 会话确认模块 `installed`、版本 `18.0.2.0.26`。

复测前，Codex 通过 Odoo Shell ORM 将既有变体 ID 1544、模板 ID 1471 恢复到测试基准。2026-11-20 项目负责人使用 [hvr07_07.json](test_data/payloads/hvr07_07.json) 人工发送并报告返回 OK。API 日志 ID 1828 记录 HTTP code=200、响应 `returnStatus=Y`、`exceptionInfo=OK`、`operationTime=2026-11-20 10:03:02`。随后通过 Odoo Shell ORM 确认 owner/productCode 组合只有一个变体，变体 ID 仍为 1544、模板 ID 仍为 1471；模板名称已更新为“HVR07 修改后名称”、规格型号为“HVR07-EDITED-MODEL”，`productForm=原材料`、`tracking=none`、单位“台”及其余报文值正确。Edit 属于 repeatable，未创建持久化幂等记录；每次调用的 API 日志独立保留。HVR07-07 现记为 PASS。

### HVR07-08 第二次 Edit 人工验收

项目负责人报告 HVR07-08 返回 OK。API 日志 ID 1830（2026-11-20 10:07:27）记录 HTTP code=200、`returnStatus=Y`、`exceptionInfo=OK`。日志请求将单位改为 `HVR07-20261119-UNIT-ALT`，并将 power、重量和尺寸修改为报文值。Odoo Shell ORM 确认既有变体 ID 1544 / 模板 ID 1471 未变化，owner/productCode 仍为原组合；`ginlong_unit` 及原生 UoM 均指向临时同类别单位 ID 35，power=`1kW-edited`、`ginlong_weight=4.25`、尺寸为 110/55/45，HVR07-07 已设置的名称和规格继续保留。Edit 无持久化幂等记录符合 repeatable 策略。HVR07-08 记为 PASS。

### HVR07-09 重复 Edit 前置数据缺失与恢复

项目负责人首次执行 HVR07-09 时收到 `BUS03: API07 Edit目标产品不存在`（operationTime `2026-11-20 10:09:07`）。ORM 确认该请求的 owner/productCode 下产品数为 0，API 日志 ID 1832 记录此 BUS03，未产生产品或库存副作用；这是当时测试前置数据缺失，不是 Edit 处理缺陷。之后 Codex 通过准备脚本所用的同一 `services.api07` 业务服务补建唯一基准变体 ID 1562、模板 ID 1486，字段与 [hvr07_09.json](test_data/payloads/hvr07_09.json) 一致（`productForm=半成品`、`tracking=serial`）。项目负责人随后用同一 Payload 连续发送两次，API 日志 ID 1834（10:11:49）及 1836（10:12:14）均为 HTTP code=200、`returnStatus=Y`、`exceptionInfo=OK`。ORM 确认两次请求前后均为同一变体 ID 1562 / 模板 ID 1486、字段未改变，且未新增幂等记录；两次 Edit 均实际执行并各自写入日志。HVR07-09 记为 PASS，最初缺少前置数据的 BUS03 历史保留。

### HVR07-10 计量单位规则修订

项目负责人于 2026-11-20 10:14:28 使用未在 Odoo 建档的 `HVR07-NO-SUCH-UOM` 执行 API07 Add，得到 `BUS01: 业务处理失败`；API 日志 ID 1838 的内部诊断为该单位不存在。项目负责人随后确认 V3.2 未给出单位取值枚举，允许自动在 Odoo 标准 `Unit` 类别创建单位，换算因子为 1、不换算。API07 现仅在 Odoo 中找不到同名单位时自动创建该 UoM；既有单位继续复用，重名仍明确拒绝。版本 `18.0.2.0.27` 通过 3 项定向 Odoo 测试（0 failed、0 error），模块已升级，8099 重启后 `/web/login` 返回 HTTP 200。

项目负责人于 10:30:26 重发 HVR07-10，报告返回 OK。API 日志 ID 1850 记录 `returnStatus=Y`、`exceptionInfo=OK`；ORM 确认产品变体 ID 1570、模板 ID 1492 使用新建 UoM ID 40，类别为 `Unit`，factor/factor_inv 均为 1，productForm=`原材料`、tracking=`none`、重量 1.5；API07 Add 幂等记录 ID 1498 为 `succeeded`、attempt_count=1。HVR07-10 记为 PASS。

10:30:43 的后续请求日志 ID 1852 也返回 IDM07，但请求仍为 `unit=HVR07-NO-SUCH-UOM`，与 HVR07-10 完全相同，不计为 HVR07-11。项目负责人于 10:36:25 使用 `unit=台` 的 [hvr07_11.json](test_data/payloads/hvr07_11.json) 再次 Add，返回 `IDM07: 重复新增，冲突键(owner, productCode)`；API 日志 ID 1854 与实际报文匹配。ORM 确认仍只有产品变体 ID 1570 / 模板 ID 1492，`ginlong_unit` 和 UoM ID 40 保持 `HVR07-NO-SUCH-UOM`，幂等记录 ID 1498 仍为 `succeeded`、attempt_count=1。HVR07-11 记为 PASS；日志 1852 保留为同 Payload 重复 Add 历史。

HVR07-11 不再是“修正失败请求后重试”。HVR07-10 已成功建档；HVR07-11 使用同一 owner/productCode、`unit=台` 的不同报文再次 Add，应返回 IDM07，确认首次单位与产品档案不被覆盖。当前可执行该用例。

### HVR07-04 错误消息修复后的 Codex 本地验证（不替代人工验收）

2026-11-20 将 API07 同一 `productCode` 的 `productForm` 冲突接入统一错误目录，新增 `BUS02`。升级后的模块版本为 `18.0.2.0.25`。Codex 使用本地 HVR API User 通过真实 HTTP 向 `127.0.0.1:8099` 发送冲突 Edit，得到 HTTP 200：`returnStatus=N`、`exceptionInfo=BUS02: 同productCode的productForm必须一致`。随后通过 Odoo Shell ORM 核对日志 ID 1794（错误码、清晰消息及内部冲突字段诊断均已记录），货主 B 产品仍关联模板 ID 1451，模板仍为 `productForm=原材料`、`tracking=none`。API07 ORM 测试及真实 HTTP 自动化测试共 2 项通过。此项是 Codex 本地验证，不单独计作人工 HVR；项目负责人随后复测的结果见下段。

项目负责人随后报告 HVR07-04 复测通过，提供的响应 `operationTime=2026-11-20 09:20:20`。ORM 日志 ID 1796 与该时间及响应一致；货主 B 变体 ID 1519 仍关联模板 ID 1451，`productForm=原材料`、`tracking=none`，没有被冲突请求修改。该负责人复测作为 HVR PASS 证据。

### HVR07-05 半成品 SN tracking 人工验收

项目负责人报告 API07 返回 `returnStatus=Y`、`exceptionInfo=OK`、`operationTime=2026-11-20 09:28:06`。ORM API 日志 ID 1798 显示请求 `productForm=半成品`，响应时间一致且 `success=True`。产品变体 ID 1542（owner=`HVR07-20261119-OWNER-A`、productCode=`HVR07-20261119-SEMI-A`）关联模板 ID 1469，模板 `productForm=半成品`、`tracking=serial`。对应幂等记录 ID 1486 为 `succeeded`、`action=add`、`attempt_count=1`。该用例按项目负责人报告及 ORM 证据记为 PASS。

### HVR07-06 成品 SN tracking 人工验收

项目负责人报告同一成品请求发送两次，一次成功、一次失败。API 日志 ID 1800（2026-11-20 09:35:32）记录首次 Add 成功，响应 `returnStatus=Y`、`exceptionInfo=OK`；日志 ID 1802（09:37:53）记录第二次相同业务键 Add 返回 `IDM07: 重复新增，冲突键(owner, productCode)`。该失败符合 Add 重复请求契约。ORM 核实产品变体 ID 1543、模板 ID 1470，`productForm=成品`、`tracking=serial`，仅存在一个该 owner/productCode 变体；幂等记录 ID 1487 为 `succeeded`、`action=add`、`attempt_count=1`。该用例记为 PASS。

### HVR07-07 首次 Edit 人工验收（历史问题及修复后 PASS）

项目负责人报告 API07 Edit 返回 OK。API 日志 ID 1804（2026-11-20 09:40:22）记录 HTTP code=200、`success=True`、响应 `returnStatus=Y`、`exceptionInfo=OK`。请求将名称/规格改为“HVR07 修改后名称”/“HVR07-EDITED-MODEL”。当时 ORM 显示变体 ID 1544、模板 ID 1471 在 09:40:22.451481 创建，日志时间为 09:40:22.537438；原先登记的 Edit 基准 ID 1133/1098 已不存在，因此无法证明该次请求更新的是预置旧档案。随后项目负责人使用旧值报文尝试 Edit，日志 ID 1806 记录 `BUS01: 业务处理失败`，诊断为 `name, ginlong_specification_model` 冲突，产品未变。此问题已由 `18.0.2.0.26` 修复。复测前 ORM 将既有记录 ID 1544/1471 恢复至旧值基准。项目负责人随后重发 [hvr07_07.json](test_data/payloads/hvr07_07.json) 并报告返回 OK；API 日志 ID 1828 的 Ginlong 响应为 `returnStatus=Y`、`exceptionInfo=OK`。ORM 确认变体 ID 1544、模板 ID 1471 均未改变，名称及规格更新为请求值，其他报文属性符合预期。因此历史问题保留，修复后人工验收记为 PASS。此前 Edit 无幂等记录，符合 repeatable 策略。

## 逐实例记录

| HVR | 场景 | 预检状态 | 人工结果（PASS/PARTIAL/FAIL/BLOCKED/NOT RUN） | 实际 HTTP 状态 / 响应证据 | Odoo 数据与界面证据 | API 日志 / 幂等证据 | 执行者 / 日期 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| HVR07-01 | 新增原材料 | READY | PASS | 2026-11-20 07:32:03；POST 返回 HTTP 200，`returnStatus=Y`、`exceptionInfo=OK`（完整响应由 API 日志 1724 保存） | ORM：`product.product` ID 1513，模板 ID 1451；owner=`HVR07-20261119-OWNER-A`、productCode=`HVR07-20261119-RAW-A`，活动状态，tracking=`none` | API 日志 ID 1724 成功；幂等记录 ID 1466，`succeeded`、`attempt_count=1` | 项目负责人（用户报告）/2026-11-20 |
| HVR07-02 | 相同及不同 Payload 的 Add 重复提交 | READY | PASS | 相同 Payload：2026-11-20 07:32:26，HTTP 200，`returnStatus=N`、`IDM07`（日志 1726）。不同 Payload：2026-11-20 08:55:25，将 `productName` 改为“HVR07 原材料产品1”后再次 Add，HTTP 200，`returnStatus=N`、`exceptionInfo=IDM07: 重复新增，冲突键(owner, productCode)`（日志 1747） | ORM 核对仍只有产品变体 ID 1513、模板 ID 1451；名称仍为“HVR07 原材料产品”，没有覆盖或重复创建 | 日志 1726、1747 均记录 IDM07 拒绝；幂等记录仍为原成功记录 ID 1466，`attempt_count=1`，未新增成功幂等记录 | 项目负责人（用户报告）；ORM 由 Codex 复核 /2026-11-20 |
| HVR07-03 | 第二货主使用相同 productCode | READY | PASS | 2026-11-20 08:58:13；HTTP 200，`returnStatus=Y`、`exceptionInfo=OK`（API 日志 ID 1750） | ORM：货主 B 的变体 ID 1519 已创建；货主 A 变体 ID 1513 与 B 变体均关联同一模板 ID 1451，未重复建立模板；模板 `productForm=原材料`、`tracking=none` | API 日志 ID 1750 成功；货主 B 的幂等记录 ID 1475，`succeeded`、`attempt_count=1` | 项目负责人（用户报告）；ORM 由 Codex 复核 /2026-11-20 |
| HVR07-04 | 同码跨货主 productForm 冲突 | READY | PASS（项目负责人复测通过） | 原人工请求：2026-11-20 09:00:25，HTTP 200，`returnStatus=N`，`exceptionInfo=BUS01: 业务处理失败`。修复后 Codex HTTP 验证：日志 ID 1794，`BUS02: 同productCode的productForm必须一致`。项目负责人复测：`operationTime=2026-11-20 09:20:20`，响应为 `returnStatus=N`、`exceptionInfo=BUS02: 同productCode的productForm必须一致`；HTTP 状态码未在报告中提供 | ORM：货主 B 变体 ID 1519 仍关联模板 ID 1451；模板仍为 `productForm=原材料`、`tracking=none`，未被冲突请求修改 | 历史日志 ID 1753 保留；修复后 Codex 验证日志 ID 1794、负责人复测日志 ID 1796 均为 `BUS02`，诊断为 `ginlong_product_form, tracking` 冲突。货主 B Add 幂等记录 ID 1475 仍为 `succeeded`、`attempt_count=1` | 项目负责人 /2026-11-20；ORM 由 Codex 复核 |
| HVR07-05 | 半成品 serial tracking | READY | PASS | 2026-11-20 09:28:06；`returnStatus=Y`、`exceptionInfo=OK`；API 日志 ID 1798 显示 HTTP code=200、success=True | ORM：变体 ID 1542、模板 ID 1469；owner=`HVR07-20261119-OWNER-A`、productCode=`HVR07-20261119-SEMI-A`，模板 `productForm=半成品`、`tracking=serial` | API 日志 ID 1798；幂等记录 ID 1486，`succeeded`、`action=add`、`attempt_count=1` | 项目负责人（用户报告）；ORM 由 Codex 复核 /2026-11-20 |
| HVR07-06 | 成品 serial tracking | READY | PASS | 首次：2026-11-20 09:35:32，HTTP code=200，`returnStatus=Y`、`exceptionInfo=OK`（日志 ID 1800）。第二次重复 Add：2026-11-20 09:37:53，返回 `returnStatus=N`、`IDM07: 重复新增，冲突键(owner, productCode)`（日志 ID 1802，符合预期） | ORM：变体 ID 1543、模板 ID 1470；owner=`HVR07-20261119-OWNER-A`、productCode=`HVR07-20261119-FIN-A`，模板 `productForm=成品`、`tracking=serial`；该组合仅一个变体 | 成功日志 ID 1800；重复拒绝日志 ID 1802；幂等记录 ID 1487，`succeeded`、`action=add`、`attempt_count=1` | 项目负责人（用户报告）；ORM 由 Codex 复核 /2026-11-20 |
| HVR07-07 | 第一次 Edit：名称和规格 | READY（已修复并复测） | PASS | 项目负责人报告返回 OK；API 日志 ID 1828，2026-11-20 10:03:02，HTTP code=200，`returnStatus=Y`、`exceptionInfo=OK` | ORM：变体 ID 1544、模板 ID 1471 保持不变；名称为“HVR07 修改后名称”、规格为“HVR07-EDITED-MODEL”；productForm、tracking、单位、power、重量及尺寸符合请求 | API 日志 ID 1828；Edit 为 repeatable，无持久化幂等记录符合策略；历史日志 1804/1806 保留 | 项目负责人（人工请求及结果报告）；ORM 由 Codex 复核 /2026-11-20 |
| HVR07-08 | 第二次 Edit：单位及可选属性 | READY（HVR07-07 已通过） | PASS | 项目负责人报告返回 OK；API 日志 ID 1830，2026-11-20 10:07:27，HTTP code=200，`returnStatus=Y`、`exceptionInfo=OK` | ORM：变体 ID 1544、模板 ID 1471 保持不变；UoM 为临时同类别单位 ID 35，power=`1kW-edited`、重量=4.25、尺寸=110/55/45；07 的名称/规格保留 | API 日志 ID 1830；Edit 为 repeatable，无持久化幂等记录符合策略 | 项目负责人（人工请求及结果报告）；ORM 由 Codex 复核 /2026-11-20 |
| HVR07-09 | 相同 Payload 重复 Edit | READY（基准 ID 1562 / 1486） | PASS | 首次缺前置请求：10:09:07，日志 1832，BUS03；基准恢复后两次同 Payload：10:11:49 日志 1834、10:12:14 日志 1836，均 HTTP 200、`returnStatus=Y`、`exceptionInfo=OK` | ORM：owner/productCode 组合只有一个变体 ID 1562 / 模板 ID 1486；两次 Edit 后名称、规格、单位、SN tracking、power、重量、尺寸均保持与请求一致 | 日志 1834 / 1836 各记录一次成功处理；无持久化幂等记录，符合 Edit repeatable 规则；失败前置日志 1832 保留 | 项目负责人（两次人工请求）；ORM 由 Codex 复核 /2026-11-20 |
| HVR07-10 | 新单位自动建档并创建产品 | READY（`.27` 已升级，自动化通过） | PASS | 旧版请求：10:14:28，日志 1838，BUS01；修复后 10:30:26，日志 1850，HTTP 200、`returnStatus=Y`、`exceptionInfo=OK` | ORM：产品 ID 1570 / 模板 ID 1492；UoM ID 40，类别 `Unit`，factor/factor_inv=1；产品单位、形态、tracking、重量符合报文 | 成功日志 ID 1850；幂等 ID 1498 为 `succeeded`、attempt_count=1；旧失败日志保留 | 项目负责人（人工请求及结果报告）；ORM 由 Codex 复核 /2026-11-20 |
| HVR07-11 | 同键不同单位重复 Add 拒绝 | READY（HVR07-10 已通过） | PASS | 同 Payload 历史请求：10:30:43，日志 1852；HVR07-11 `unit=台` 请求：10:36:25，日志 1854，`returnStatus=N`、`IDM07: 重复新增，冲突键(owner, productCode)` | ORM：仍只有产品 ID 1570 / 模板 ID 1492；`ginlong_unit` 与 UoM ID 40 仍为 `HVR07-NO-SUCH-UOM`，没有覆盖或重复创建 | 幂等记录 ID 1498 仍为 `succeeded`、attempt_count=1；失败日志 1854 与原始成功日志 1850 分别保留 | 项目负责人（人工请求）；ORM 由 Codex 复核 /2026-11-20 |
| HVR07-12 | 拒绝不支持的 productForm | 模块 `.30`；人工复测完成 | PASS | 2026-11-20 14:38:46，HTTP 200，`returnStatus=N`，`exceptionInfo=BUS06: productForm仅支持原材料/半成品/成品`；API 日志 ID 1923。14:38:40 的 Token 过期日志 ID 1921 为独立认证失败；旧版 BUS01 日志 ID 1856 保留 | ORM：owner=`HVR07-20261119-OWNER-A`、productCode=`HVR07-20261119-BAD-FORM` 无产品变体、无关联模板 | 日志 1923 为 `success=False`、code=`BUS06`，诊断列明非法值 `包装物` 及允许枚举；不存在该业务键的成功幂等记录 | 项目负责人（人工请求及结果）；Codex（ORM 核对）/2026-11-20 |
| HVR07-13 | 缺失 owner；追加多字段必填错误 | `.33`；人工单字段与多字段复测完成 | PASS | 单字段：14:59:30 日志 1947 返回 `REQ01: 必填字段错误: owner is missing`。多字段：15:31:27 返回 `N / REQ01: 缺失字段: owner, productForm`，日志 ID 1995 | ORM：请求同时缺少 `owner`、`productForm`；原 RAW-A 货主 A/B 变体 ID 1513、1519 及共享模板 ID 1451 仍在，名称、形态和 tracking 保持原值 | 日志 ID 1995 的诊断完整记录 `owner is missing` 与 `productForm is missing`；该时段 API07 新增幂等记录为 0。旧版日志 1925、截断响应日志 1951 保留 | 项目负责人（人工请求）；Codex（ORM 核对）/2026-11-20 |
| HVR07-14 | owner 为 null | `.33`；人工完成 | PASS | 2026-11-21 01:15:55，`N / REQ01: 空值字段: owner`；HTTP 状态未提供；日志 1999 | 请求中 owner 为 null；`NULL-OWNER` 编码无产品变体 | 日志诊断 `owner is empty`；无相应幂等记录 | 项目负责人（人工请求）；Codex（ORM 核对）/2026-11-21 |
| HVR07-15 | productCode 为空字符串 | `.33`；人工完成 | PASS | 2026-11-21 01:17:55，`N / REQ01: 空值字段: productCode`；HTTP 状态未提供；日志 2001 | owner A 下无空编码变体 | 日志诊断 `productCode is empty`；无对应幂等记录 | 项目负责人（人工请求）；Codex（ORM 核对）/2026-11-21 |
| HVR07-16 | productName 纯空格 | `.33`；人工完成 | PASS | 2026-11-21 01:18:56，`N / REQ01: 空值字段: productName`；HTTP 状态未提供；日志 2003 | 请求名为三个空格；`BLANK-NAME` 编码无产品变体 | 日志诊断 `productName is empty`；无对应幂等记录 | 项目负责人（人工请求）；Codex（ORM 核对）/2026-11-21 |
| HVR07-17 | productForm 为 null | `.33`；人工完成 | PASS | 2026-11-21 01:19:50，`N / REQ01: 空值字段: productForm`；HTTP 状态未提供；日志 2005 | `NULL-FORM` 编码无产品变体 | 日志诊断 `productForm is empty`；无对应幂等记录 | 项目负责人（人工请求）；Codex（ORM 核对）/2026-11-21 |
| HVR07-18 | DECIMAL weight 非法文本 | `.33`；人工完成 | PASS | 2026-11-21 01:20:18，`N / TYP01: 类型错误字段: weight`；HTTP 状态未提供；日志 2007 | 请求 `weight="abc"`；`BAD-WEIGHT` 编码无产品变体 | 日志保留完整 Decimal 类型原因；无对应幂等记录 | 项目负责人（人工请求）；Codex（ORM 核对）/2026-11-21 |
| HVR07-19 | VARCHAR productName 为数字类型 | 项目负责人确认该值有效 | PASS（项目负责人判定） | 2026-11-21 01:21:35 返回 `Y / OK`；日志 2009 | 变体 ID 1614 / 模板 ID 1525 已创建，模板名称为字符串 `'12345'` | 幂等记录 ID 1543 为 `succeeded`、attempt_count=1；产品和记录保留 | 项目负责人（人工请求及判定）；Codex（ORM 核对）/2026-11-21 |
| HVR07-20 | productForm 为数字类型 | `.33`；人工完成 | PASS | 2026-11-21 01:22:06，`N / BUS06: productForm仅支持原材料/半成品/成品`；HTTP 状态未提供；日志 2011 | `BAD-FORM-TYPE` 编码无产品变体 | 日志诊断记录非法值 `7`；无对应幂等记录 | 项目负责人（人工请求）；Codex（ORM 核对）/2026-11-21 |
| HVR07-21 | 无效 Bearer Token | 纠正凭据后人工复测 | PASS | 初次 01:22:35 误用有效 Token 返回 Y，日志 2013；纠正后 01:25:47 返回 `N / AUTH01: API认证失败`，日志 2019 | 纠正请求使用新编码 `INVALID-TOKEN1`，无产品变体 | 日志 2019 诊断 `Invalid token`；纠正请求无幂等记录。初次误用有效 Token 创建的变体 ID 1615 / 幂等 ID 1545 保留 | 项目负责人（人工请求）；Codex（ORM 核对）/2026-11-21 |
| HVR07-22 | Token 与无 WMS Project API User | 项目负责人确认记 PASS；认证证据有差异 | PASS（项目负责人判定） | 01:23:28 误用有 Project Token 返回 Y，日志 2015；01:26:38 返回 `N / AUTH01: API认证失败`，日志 2021 | 初次误用请求创建变体 ID 1616；纠正请求未另行创建 | 日志 2015 的 `project_id=146`；日志 2021 诊断为 `Invalid token`，未证明有效无 Project Token 的业务路径。项目负责人确认最终结果可记 PASS；幂等 ID 1546 保留 | 项目负责人（结果判定）；Codex（ORM 核对）/2026-11-21 |

## HVR 关闭记录

| 项目 | 记录 |
|---|---|
| 关闭范围 | API07 产品档案本地人工验收 HVR07-01–22 |
| 关闭结果 | 22 项 PASS；包含项目负责人对 HVR07-19、HVR07-22 的明确判定 |
| 项目负责人批准 | APPROVED；2026-11-21（本会话） |
| 冻结状态 | 本轮 HVR 测试包 Frozen / Closed；不代表 TDD v1.0 被修改或 CC-GIN-005 关闭 |
| 保留说明 | HVR07-19 数值型名称被接受；HVR07-22 的无 Project Token 路径证据限制、误用 Token 所产生的测试数据及全部早期日志均保留，不伪造验证结论 |

## 单项证据清单

每个案例至少保存：

1. 原始 curl 输出（含 HTTP 状态与完整 JSON 响应；测试 Token 必须遮盖）。
2. Odoo 后台产品表单/列表截图，能识别测试 `productCode`、owner 和关键字段。
3. API 日志详情截图或 ORM 摘要；核对请求体和响应体。无效 Token 案例记录认证层响应且注明无业务 API 日志。
4. 涉及幂等的案例，保存 `test_data/verify_api07_hvr.py` 输出或管理员 ORM 核对记录。
5. 失败/阻塞时，记录错误文本、发生时间、是否有部分产品/变体/模板/幂等数据，以及复测关联编号。

人工完成一个案例后再填写对应行。`READY` 不是 PASS；Codex 预检、数据准备或自动化测试均不能替代人工结果。
