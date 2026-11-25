> **历史记录保留。** v3 的 NOT RUN/既有历史判定不是 CC-GIN-007 当前 HVR 结果；当前执行包见 [CC-GIN-007 HVR v0.1 Draft](../cc_gin_007_v0.1_draft/HVR_GIN_007_Execution_Record.md)。v3 原始 payload/curl 已归档。

# API01 入库单 HVR 执行记录

## CC-GIN-011 关闭后的 API01 响应回归（2026-11-25）

依据项目负责人批准关闭 CC-GIN-011 后恢复 API01 HVR 的决定，新增人工核对项见 [HVR_API01_CC011_Regression_Guide.md](HVR_API01_CC011_Regression_Guide.md)。

| 用例 | 结果 | 人工判定 |
|---|---|---|
| CC011-API01-01 成功 Add 三字段响应 | 尚待执行 | NOT RUN |
| CC011-API01-02 同单号重复 Add 错误响应及数据不变 | 尚待执行 | NOT RUN |
| CC011-API01-03 Required 校验错误响应 | 尚待执行 | NOT RUN |
| CC011-API01-04 Token 认证错误 HTTP/协议响应 | 尚待执行 | NOT RUN |

人工执行后追加 HTTP 状态、脱敏响应、Inbound Order ID、API 日志 ID、幂等记录及证据，不覆盖下方历史 HVR 结果。


## HVR API01 v3 历史记录（2026-11-23；已由 CC-GIN-007 HVR 取代）

当时的活动包包含 **5 个 HTTP 实例：HVR01-29 至 HVR01-33**。本表保留 2026-11-23/24 的历史状态；当前 CC-GIN-007 API01 业务 HVR 结果见 [CC-GIN-007 HVR 执行记录](../cc_gin_007_v0.1_draft/HVR_GIN_007_Execution_Record.md)，CC-GIN-011 后新增响应回归见本文件开头。

### 清理前 ORM 快照

经项目负责人确认，仅删除 HVR01 验收单据及对应 API01 幂等记录。清理前通过 Odoo Shell ORM 盘点：10 张 HVR01 入库单均为 `new`，未关联 stock/picking；对应 API01 幂等 ID 为 `1559, 1692, 1693, 1694, 1695, 1696, 1697, 1813, 2016, 2017`。保留 API 日志、非 HVR 入库单及 API07 产品准备幂等记录。已通过 Odoo Shell ORM 删除并复核：上述 10 张 HVR01 入库单及对应 10 条 API01 幂等记录均不存在；非 HVR 入库单 1 张、API07 setup 幂等记录 10 条仍保留；API 日志保留。

| HVR | v3 执行结果 | HTTP / ORM / 日志证据 | 判定 | 执行者 / 日期 |
|---|---|---|---|---|
| **HVR01-29 主场景** | **NOT RUN** | **三托盘、三产品、15 条托盘/SN 行；应核对托盘归属和逐产品数量 9/6/6** | **NOT RUN** | — |
| HVR01-30 单件 SN 数量错误 | NOT RUN | 预期拒绝并指出产品/托盘 | NOT RUN | — |
| HVR01-31 真实 SN 跨托盘重复 | `N / BUS01: SN重复`；API 日志 3341 | ORM：订单数 0，幂等记录数 0；日志保留完整产品/SN 诊断 | **PASS（预期拒绝）** | 项目负责人 / 2026-11-24 |
| HVR01-32 不同产品相同 SN 文本 | `Y / OK`；API 日志 3342 | ORM：订单 1047，两个不同产品变体分别保存相同 SN 文本；幂等 2636 `succeeded` | **PASS** | 项目负责人 / 2026-11-24 |
| HVR01-33 跨单据引用已有 SN | 首次 `Y / OK`，API 日志 3343；同单号重发返回 `N / IDM02`，日志 3344 | ORM：订单 1048 引用已存在于订单 1044 的产品/SN；幂等 2637 `succeeded`，重复 Add 未重复创建 | **PASS** | 项目负责人 / 2026-11-24 |

---

### v2 完整包处置记录

旧 v2 包含 32 个 HTTP 用例（01–19、21–33）、一个后台只读检查及两个 API07 setup 请求；v2 尚未开始人工验收。根据本轮 HVR 范围收敛，当前只需执行 29–33。因此已删除 v2 中 01–28 的未执行报文、两个不需要的 API07 setup 报文及旧完整 manifest；这些未执行文件不再占据活动目录或归档目录。早期 v1/R1 人工证据仍按原路径保留。

> 以下内容是 payload 重建前的 v1 历史执行记录。所有 JSON 引用均指向归档目录；其中 HVR01-29 的历史 PASS 不能代表当前 v3 HVR01-29 的执行结果。

**v1 历史状态：人工 HVR 部分完成。** HVR01-01–09 的既有判定和历史证据保留；其中 HVR01-01/04/05/06 的旧 PASS 使用了不符合当前 SN 规则的 payload。HVR01-01-R1 和 HVR01-01-R1-1 的单条 SN quantity=3 均曾从旧 8099 进程收到 Y/OK，按当前单件规则保留为 FAIL；第二次请求、ORM、日志、幂等记录及旧进程版本差异见本文补充记录。其他 R1 依赖/包含同类报文的实例未运行。HVR01-02 的首次失败记录保留。HVR01-29 首次 Add 已由项目负责人执行并以 ORM/日志核对为 PASS；重复 Add 记录另列。旧 v1 的 HVR01-30 已返回拒绝，但当时未显示产品/托盘定位，记 PARTIAL；HVR01-31–34 在 v1 未运行。当前应执行的 v3 用例状态见本文件开头；Codex 自动化证据不代替各实例人工判定。

人工复测开始前，自动化产生的 8 张入库单、对应 9 条幂等记录及 `OWNER-AUTO` 联系人已通过 ORM 清理，19 条 API 日志保留。随后项目负责人执行 HVR01-01，当时数据库保存了订单 713、幂等记录 1559 和日志 2056；这些订单和 API01 幂等记录已在本轮按负责人授权清理。Owner A/B、3 个产品变体、测试 API 用户和本地 0600 凭据文件保留。

## v3 当前执行环境

| 项目 | 记录 |
|---|---|
| 数据库 / 模块 | `odooce_karlrapp`；Odoo Shell ORM 确认 `ginlong_apis` installed/latest=`18.0.2.0.39` |
| 服务 | `http://127.0.0.1:8099`；PID 25730 监听；`GET /web/login` 返回 HTTP 200 |
| 产品前置 | ORM 确认 Owner A 的原材料 Variant 1617 (`tracking=none`)、成品 Variant 1754 (`serial`)、半成品 Variant 1755 (`serial`) 均存在 |
| 执行状态 | HVR01-31–33 已于 2026-11-24 执行并通过；HVR01-29–30 在此 v3 包中的状态仍为 `NOT RUN`，相关 CC-GIN-007 人工结果另有记录 |

## v1 历史执行环境

| 项目 | 记录 |
|---|---|
| 数据库 | `odooce_karlrapp`（Odoo Shell ORM 已确认） |
| 服务 | `http://127.0.0.1:8099`（HTTP 200；服务保持运行） |
| 当前模块版本 | Odoo Shell ORM 确认数据库 installed/latest=`18.0.2.0.37`；2026-11-23 已重启 8099，当前 PID 22584 在 `.37` 源码更新时间后启动，`GET /web/login` 返回 HTTP 200 |
| 执行者 / 日期 | 项目负责人 / 2026-11-22（HVR01-01–09；含 HVR01-07 二次报文） |
| HVR 包版本 / Git commit | ____ |
| 原始 curl 输出 | 临时原始响应含 `Set-Cookie`，已删除；脱敏摘要见模拟自动化记录 |
| Odoo 截图 / ORM 证据目录 | 本轮未做浏览器截图；ORM 摘要见模拟自动化记录 |
| API 日志与幂等记录证据 | ORM / Backend JSON-RPC 核对见模拟自动化记录 |

HVR01-01/02 的首次人工执行发生在版本 `.34`。版本 `.35` 已完成本地升级，8099 当前返回 HTTP 200。HVR01-02 与 HVR01-03 在 `.35` 上复测/执行通过；首次 HVR01-02 的旧响应、日志和幂等证据保留不变。

## 执行结果

| HVR | 场景 | 前置检查 | 实际 HTTP 状态 / `returnStatus` / `exceptionInfo` / 时间 | ORM / 界面证据 | API 日志 / 幂等证据 | 判定（PASS/FAIL/BLOCKED/NOT RUN） | 执行者 / 日期 |
|---|---|---|---|---|---|---|---|
| HVR01-01 | 首次 Add 与三级 Order 明细 | 已有 Owner A / 产品 Variant，单号此前不存在 | HTTP 200 / `Y` / `OK` / `2026-11-22 03:24:17` | Order ID 713：state=`new`，货主编码正确，KRWH，一个产品行数量 3、一个 SN，无 Picking | API 日志 ID 2056 success；幂等 ID 1559 Add/succeeded | PASS | 项目负责人 / 2026-11-22 |
| HVR01-02 | 同 Payload Add 重复请求 | HVR01-01 已成功，Order 713 存在 | 首次：HTTP 200 / `Y` / `OK` / `03:24:17`；复测：HTTP 200 / `N` / `IDM02: 重复新增，冲突键: inboundOrderNo` / `04:03:06` | ORM：仍只有 Order 713，state=`new`、原备注及数量 3 未变，仍一条明细 | 首次成功日志 2057 保留；复测错误日志 2233；幂等 ID 1559 仍为唯一 Add/succeeded，`attempt_count=1` | 首次 FAIL；复测 PASS | 项目负责人 / 2026-11-22 |
| HVR01-03 | 同单号不同 Payload | Order 713 已存在；请求改备注并将数量改为 99 | HTTP 200 / `N` / `IDM02: 重复新增，冲突键: inboundOrderNo` / `2026-11-22 04:04:19` | ORM：仍只有 Order 713，备注保持 `HVR01 本地人工验收`、数量保持 3、state=`new` | API 日志 ID 2234 为 IDM02/error；幂等仍只有 ID 1559，Add/succeeded、`attempt_count=1` | PASS | 项目负责人 / 2026-11-22 |
| HVR01-04 | 不存在货主自动建档并关联入库单 | 测试货主编码此前不存在；对应产品 Variant 已准备 | HTTP 200 / `Y` / `OK` / `2026-11-22 08:37:47` | ORM：货主 `HVR01-20261121-OWNER-AUTO` 仅一条（Partner 1143）；Order 756 关联 Partner 1143，子层产品行关联 Variant 1619 | API 日志 ID 2238 success；幂等 ID 1692 API01/Add/succeeded，`attempt_count=1` | PASS | 项目负责人 / 2026-11-22 |
| HVR01-05 | 已存在货主复用 | Owner A 已存在（Partner 1080） | HTTP 200 / `Y` / `OK` / `2026-11-22 08:38:45` | ORM：新 Order 757 的 `ginlong_owner_id` 指向已有 Partner 1080；该货主编码仍只有一条 Partner；子层产品行关联 Owner A Variant 1617 | API 日志 ID 2239 success；幂等 ID 1693 API01/Add/succeeded，`attempt_count=1` | PASS | 项目负责人 / 2026-11-22 |
| HVR01-06 | 跨货主同 productCode 变体隔离 | Owner A/B 对应产品变体分别存在（1617/1618） | HTTP 200 / `Y` / `OK` / `2026-11-22 08:52:50` | ORM：Order 758 关联 Owner B（Partner 1081）；三级结构的子层产品行关联 Owner B Variant 1618；Owner A Variant 1617 未误用 | API 日志 ID 2240 success；幂等 ID 1694 API01/Add/succeeded，`attempt_count=1` | PASS | 项目负责人 / 2026-11-22 |
| HVR01-07 | quantity=0（非 SN 原材料）；第二次请求省略 `snList` | Owner A、产品变体 ID 1617（`productForm=原材料`）；首次单据 IN-ZERO 已存在 | 首次：HTTP 200 / `Y` / `OK` / `08:56:55`；同号重发：`N / IDM02` / `08:59:17`；新单号 IN-ZERO1 且不含 `snList`：HTTP 200 / `Y` / `OK` / `08:59:34` | ORM：Order 759 与新 Order 760 均保留数量 `0.0`；Order 760 子层产品行关联 1617，`sn_count=0`、`ginlong_sn_list_json=[]`；产品 `tracking=none` | API 日志 ID 2241 success、2242 IDM02/error、2243 success；幂等 ID 1695 与 1696 分别对应两个成功 Add，均 `attempt_count=1` | PASS（第二次新单验证通过；同号重复按预期拒绝） | 项目负责人 / 2026-11-22 |
| HVR01-08 | 缺省可选 snList | Owner A、原材料产品 Variant 1617 | HTTP 200 / `Y` / `OK` / `2026-11-22 09:02:57` | ORM：Order 761 为 `new`；三级子层产品行关联 Variant 1617，数量 3；SN 明细数为 0 | API 日志 ID 2244 success，request_data 不含 `snList`；幂等 ID 1697 API01/Add/succeeded，`attempt_count=1` | PASS | 项目负责人 / 2026-11-22 |
| HVR01-09 | 一次收集多个必填表头字段错误 | owner、businessType 缺失；订单号尚未存在 | HTTP 200 / `N` / `REQ01: 缺失字段: owner, businessType` / `2026-11-22 09:08:37` | ORM：该单号无 Order；未创建货主或业务单据 | API 日志 ID 2245：REQ01，详情同时记录两字段缺失；无该业务键的幂等记录 | PASS | 项目负责人 / 2026-11-22 |
| HVR01-10 | 嵌套明细必填缺失 | NOT RUN | ____ | ____ | ____ | NOT RUN | ____ |
| HVR01-11 | owner=null | NOT RUN | ____ | ____ | ____ | NOT RUN | ____ |
| HVR01-12 | DECIMAL 非法值 | NOT RUN | ____ | ____ | ____ | NOT RUN | ____ |
| HVR01-13 | 校验失败后修正重试 | NOT RUN | ____ | ____ | ____ | NOT RUN | ____ |
| HVR01-14 | owner/product 组合不存在 | NOT RUN | ____ | ____ | ____ | NOT RUN | ____ |
| HVR01-15 | Del 仅取消 | NOT RUN | ____ | ____ | ____ | NOT RUN | ____ |
| HVR01-16 | 重复 Del | NOT RUN | ____ | ____ | ____ | NOT RUN | ____ |
| HVR01-17 | Del 后重复 Add 同一单号 | NOT RUN | ____ | ____ | ____ | NOT RUN | ____ |
| HVR01-18 | 无效 Token | NOT RUN | ____ | ____ | ____ | NOT RUN | ____ |
| HVR01-19 | 无 Project API User | NOT RUN | ____ | ____ | ____ | NOT RUN | ____ |
| HVR01-20 | Ginlong 日志与幂等只读入口 | NOT RUN | N/A | ____ | ____ | NOT RUN | ____ |

## 问题 / 复测历史

| 关联 HVR | 首次结果 / 证据 | 问题与影响 | 修改/复测证据 | 最终人工判定 |
|---|---|---|---|---|
| HVR01-02 | 首次 HTTP 200，`Y / OK`，日志 ID 2057 success；单据仍只有 ID 713 | 首次行为违反重复 Add 必须拒绝的规则 | `.35` 复测返回 `N / IDM02`，时间 `04:03:06`，错误日志 2233；Order 713 和幂等 ID 1559 未变 | 首次 FAIL，复测 PASS |
| HVR01-03 | 同单号请求把备注改为“不同报文不得覆盖原记录”，数量改为 99；返回 `N / IDM02`，时间 `04:04:19` | 需确认失败请求没有覆盖既存订单或新增幂等成功记录 | 日志 ID 2234；ORM 显示仍只有 Order 713，备注为原值、数量为 3；幂等 ID 1559 仍唯一且 `attempt_count=1` | PASS |
| HVR01-04 | 返回 `Y / OK`，`operationTime=2026-11-22 08:37:47`；成功日志 ID 2238 | 验证缺失货主自动建档及订单货主关联 | ORM：Partner 1143 唯一，Order 756 指向 1143；三级明细子层关联 Variant 1619；幂等 ID 1692 为 API01/Add/succeeded | PASS |
| HVR01-05 | 返回 `Y / OK`，`operationTime=2026-11-22 08:38:45`；成功日志 ID 2239 | 验证 API01 使用已存在的 Ginlong owner 档案，不重复创建联系人 | ORM：Owner A 仍只有 Partner 1080；Order 757 指向 Partner 1080，三级明细子层关联 Variant 1617；幂等 ID 1693 为 API01/Add/succeeded | PASS |
| HVR01-06 | 返回 `Y / OK`，`operationTime=2026-11-22 08:52:50`；成功日志 ID 2240 | 验证同一 `productCode` 跨货主关联正确变体 | ORM：Owner A/B 两个 Variant 分别为 1617/1618；Order 758 关联 Owner B，三级明细子层 `product_id=1618`；幂等 ID 1694 为 API01/Add/succeeded | PASS |
| HVR01-07 | 返回 `Y / OK`，`operationTime=2026-11-22 08:56:55`；成功日志 ID 2241 | 验证数值 0 合法，并确认原材料不按 SN 管理 | ORM：Order 759 子层数量为 `0.0`；对应 Owner A Variant 1617 的 `productForm=原材料`、`tracking=none`；幂等 ID 1695 成功 | PASS |
| HVR01-07 二次提交 | 第一次用同号 `IN-ZERO` 省略 `snList`，按预期返回 IDM02（日志 2242）；随后改用新单号 `IN-ZERO1`，收到 `Y / OK`，时间 `08:59:34`，日志 2243 | 验证同号 Add 不重复执行；新单省略 `snList` 仍成功且不产生 SN 行 | ORM：Order 760 数量为 `0.0`、SN 数为 0、产品 Variant 1617 tracking=`none`；幂等 ID 1696 succeeded | PASS |

**HVR01-07 / HVR01-08 范围说明：** HVR01-07 第二次请求使用 `IN-ZERO1`、quantity=0 且省略 `snList`；HVR01-08 随后以独立单号和 quantity=3 再次验证省略 `snList`，已单独判 PASS。

| HVR | 执行摘要 | 验收目的 | ORM / 日志 / 幂等证据 | 判定 |
|---|---|---|---|---|
| HVR01-08 | 返回 `Y / OK`，`operationTime=2026-11-22 09:02:57`；日志 ID 2244 | 验证可省略非必填 `snList`，仍创建订单明细且不产生 SN 记录 | ORM：Order 761、数量 3、子层 Variant 1617（`tracking=none`）、SN 数 0；request_data 无 `snList`；幂等 ID 1697 succeeded | PASS |
| HVR01-09 | 返回 `N / REQ01: 缺失字段: owner, businessType`，`operationTime=2026-11-22 09:08:37` | 验证一次返回所有缺失必填字段，且业务处理前拦截 | 日志 ID 2245 的 exception_details 同时包含两字段；ORM 无对应订单、无幂等记录 | PASS |

**产品关系说明：** 入库订单是三级结构；外层分组的 `product_id` 为空是模型设计，实际产品关联存于 `inbound_order_product_pallet_ids` 子层。ORM 已确认 HVR01-04、05、06 分别关联 Variant 1619、1617、1618，故 HVR01-06 的跨货主隔离通过。

## 新增 SN 一致性实例（HVR01-21–28）

本组由本次规则补充，须先通过 `setup_serial_product.sh` 创建成品 SN 变体，再逐个执行。自动化测试 PASS 不填写人工判定；以下实例均待项目负责人 HVR。

**前置准备已完成（不代表 HVR 用例通过）：** API07 setup 报文均返回 `Y/OK`；Owner A 成品 Variant 1754（`productForm=成品`、`tracking=serial`）、半成品 Variant 1755（`productForm=半成品`、`tracking=serial`）。API 日志 2352/2353，API07 Add 幂等记录 1811/1812。HVR01-21–28 仍全部 `NOT RUN`。

| HVR | 场景 | HTTP / 预期 | ORM、日志及幂等证据 | 人工判定 |
|---|---|---|---|---|
| HVR01-21 | SN 成品与非 SN 原材料混合明细，SN 数量匹配 | ____ | ____ | NOT RUN |
| HVR01-22 | SN 成品省略 `snList` | BUS01 / ____ | ____ | NOT RUN |
| HVR01-23 | SN 汇总量小于明细量 | BUS01 / ____ | ____ | NOT RUN |
| HVR01-24 | SN 汇总量大于明细量 | BUS01 / ____ | ____ | NOT RUN |
| HVR01-25 | SN 产品编码不匹配请求明细 | BUS01 / ____ | ____ | NOT RUN |
| HVR01-26 | 同产品重复 SN | BUS01 / ____ | ____ | NOT RUN |
| HVR01-27 | SN 行缺少 `productSN` | BUS01 / ____ | ____ | NOT RUN |
| HVR01-28 | 两个 SN 管理产品仅提交其中一个产品的 SN | BUS01 / ____ | ____ | NOT RUN |


**注意：** 不覆盖失败和复测前证据；未执行、失败、阻塞和通过分别记录。没有人工响应、后台/ORM 证据的实例不得记 PASS。


## 既有核心场景修订后复测（R1）

原始 payload 和 HVR 结果不覆盖。R1 使用新 `inboundOrderNo`，SN 行数量改为 3，与对应 `details.quantity=3` 一致。HVR01-04-R1 使用新货主及产品编码；测试前需通过 `prepare_api01_owner_auto_r1.py` 创建产品变体但不创建货主。

| HVR | 实际 HTTP / JSON | 业务及 ORM 证据 | API 日志证据 | 判定 | 执行者 / 日期 |
|---|---|---|---|---|
| HVR01-01-R1 | 负责人报告：HTTP 状态未提供 / `Y` / `OK` / `2026-11-22 10:46:30` | 报文：details quantity=3，单条 SN quantity=3；尚未提供 ORM 及日志核对 | 未提供 | FAIL（返回成功，违反单件 SN quantity=1） | 项目负责人 / 2026-11-22 |
| HVR01-02-R1 | 未执行 | 依赖本应被拒绝的 HVR01-01-R1 母例；用例已由 HVR01-29–33 替代 | 无 | NOT RUN | — |
| HVR01-03-R1 | 未执行 | 依赖本应被拒绝的 HVR01-01-R1 母例；用例已由 HVR01-29–33 替代 | 无 | NOT RUN | — |
| HVR01-04-R1 | 未执行 | 报文含单条 SN quantity=3，不用于货主自动建档验收；由独立有效实例替代 | 无 | NOT RUN | — |
| HVR01-05-R1 | 未执行 | 报文含单条 SN quantity=3，不用于货主复用验收；由独立有效实例替代 | 无 | NOT RUN | — |
| HVR01-06-R1 | 未执行 | 报文含单条 SN quantity=3，不用于跨货主隔离验收；由独立有效实例替代 | 无 | NOT RUN | — |


## HVR01-29–34 执行补充与历史记录

HVR01-29、30 的原有人工响应和判定保留，不覆盖旧证据；HVR01-31–33 的 2026-11-24 执行结果补录如下。HVR01-29 的历史请求报文位于 [hvr01_29.json](test_data/archive/superseded_cc_gin_007_v3_20261123/payloads/hvr01_29.json)，curl 位于 [hvr01_29.sh](test_data/archive/superseded_cc_gin_007_v3_20261123/curl/hvr01_29.sh)：原材料、成品、半成品分布在 3 个托盘，原材料按托盘 quantity=3，SN 产品每托盘各有 2 条单件 SN；逐产品总量为 9/6/6。用例预期和后台核对步骤见 [v3 历史用例归档](test_data/archive/superseded_cc_gin_007_v3_20261123/HVR_API01_Test_Cases_v3.md)。

| HVR | 场景 | 实际 HTTP / JSON | ORM / 日志 / 幂等 | 判定 | 执行者 / 日期 |
|---|---|---|---|---|---|
| HVR01-29 | 三产品、三托盘、九个单件 SN | 项目负责人报告首次响应 `Y/OK`；业务单号 `HVR01-20261122-SN-R2-MULTI-PALLET` | ORM：Order 843，3 个产品明细组，SN 共 9 条；API 日志 2612 成功，幂等记录 2017 为 API01/Add/succeeded。随后重复 Add 的失败日志 2613 保留，不改变首次成功结果 | PASS（首次 Add）；重复 Add 单独符合 IDM02 | 项目负责人 / 2026-11-23 |
| HVR01-30 | 单条 SN quantity=3 必须拒绝，并定位产品和托盘 | 项目负责人报告 `N / BUS01: SN单条数量必须为1: snList.quantity`，时间 `2026-11-23 01:39:45` | 旧响应未带产品码/托盘码；本轮定向自动化将检查新响应短定位和 API 日志完整编码。无人工重测前不沿用自动化结果判 PASS | PARTIAL，待 `.38` 人工复测 | 项目负责人 / 2026-11-23 |
| HVR01-31 | 同产品重复 SN 跨托盘必须拒绝 | 2026-11-24：`N / BUS01: SN重复`；单号 `HVR01-20261124-DUP-SN-001`；日志 3341 | ORM：无订单、无幂等记录；日志保留产品码和 SN 完整诊断 | PASS（预期拒绝） | 项目负责人 / 2026-11-24 |
| HVR01-32 | 不同产品可以使用相同 SN | 2026-11-24：`Y / OK`；单号 `HVR01-20261124-SAME-SN-DIFFERENT-PRODUCTS-001`；日志 3342 | ORM：订单 1047 保存两个产品变体的同文 SN 行，幂等 2636 succeeded | PASS | 项目负责人 / 2026-11-24 |
| HVR01-33 | 不同 API01 单据可以引用相同产品 SN | 2026-11-24：新单首次 `Y / OK`，日志 3343；同单号重发 `N / IDM02`，日志 3344 | ORM：订单 1048 引用订单 1044 已保存的同一产品/SN；幂等 2637 succeeded，重发没有重复建单 | PASS | 项目负责人 / 2026-11-24 |
| HVR01-34 | 两种 SN 产品跨三托盘，另含原材料订单总量 | ____ | ____ | NOT RUN | ____ |

HVR01-34 的请求语义：成品、半成品各 6 件，每种产品在托盘 A/B/C 各 2 个单件 SN；两产品各自明细数量与 SN 汇总量一致。原材料数量 9 只记订单总量，不分配到托盘。V3.2 `details[]` 没有 `palletCode`，因此不得把本例写成原材料已在每个托盘上的证明。

## 补充人工结果：R1 新单号请求（2026-11-23）

项目负责人提供单号 `HVR01-20261122-R1-IN-001-1` 的响应 `Y/OK`，时间 `2026-11-23 01:17:09`。这次请求使用原材料产品 `HVR01-20261121-PROD-COMMON`，明细 quantity=3，且提供一条 quantity=3 的 SN 记录。

| 项目 | ORM / 运行证据 | 判定 |
|---|---|---|
| 产品属性 | product.product ID 1617 / template ID 1528；`productForm=原材料`、`tracking=none`，不是 SN 管理产品 | 不能作为 serial-tracking 产品用例 |
| 写入结果 | 入库单 ID 842；API 日志 ID 2610 为成功；API01/Add 幂等 ID 2016 为 `succeeded` | 记录保留，不删除 |
| 当时服务 | 响应由旧 PID 14462 返回；其启动时间早于 `.37` 的 manifest 与 `services.py` 修改时间 | **FAIL：旧进程误放行；不是 `.37` 当前代码的验收结果** |
| 恢复状态 | 旧进程已停止；新 PID 22584 从当前工作区启动，`GET /web/login` 返回 HTTP 200 | 当前服务就绪，等待人工用新单号复验 |

以上是 2026-11-23 `.37` 旧进程问题的历史记录，不是当前版本指导。当前人工验收按 v3 计划使用 `.39` 和 [HVR01-30](test_data/archive/superseded_cc_gin_007_v3_20261123/curl/hvr01_30.sh)；Codex 没有发送 v3 HVR 请求。
