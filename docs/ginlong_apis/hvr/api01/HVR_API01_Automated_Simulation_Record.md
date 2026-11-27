# API01 本地模拟自动化验收记录

> **历史自动化记录（v1 payload，不能作为 v3 人工结果）**：本文件执行于旧 `.34` 版本。原 payload 已归档到 `test_data/archive/payloads_pre_rewrite_20261123/`；旧自动化 PASS/FAIL 仅用于历史追溯。

**执行日期：** 2026-11-21  **版本：** `ginlong_apis 18.0.2.0.34`  **数据库：** `odooce_karlrapp`  **服务：** `http://127.0.0.1:8099`

## 执行范围

使用生成的 19 个独立 JSON/curl 脚本，通过本机 Odoo HTTP 路由 `POST /api/ginlong/TPL_Pending_Receipt_Note` 模拟 Ginlong 调用，并用 Odoo Shell ORM、WorldDepot Backend JSON-RPC 核对数据、日志和管理入口。未调用真实 Ginlong、KR Gateway 或生产环境。此记录是 Codex 模拟自动化证据，不代替项目负责人的人工 HVR 签字。

## 模块升级与服务

- Odoo ORM `ir.module.module.update_list()` 后执行 `button_immediate_upgrade()`；数据库安装版本与源码 manifest 均核验为 `18.0.2.0.34`，`latest_version` 与 `installed_version` 一致。
- 重启本地 8099 进程以加载本轮 Python 路由代码；`GET /web/login` 返回 HTTP 200，完成验收后 8099 继续运行。
- 凭据文件仅保存在 `test_data/.api01_hvr.env`，文件权限 `0600`；未写入 HTTP 证据或本报告。

## HVR01-01 至 HVR01-19：真实本地 HTTP 请求

| 实例 | HTTP | `returnStatus` | `exceptionInfo` | `operationTime` | 模拟结果 |
|---|---:|---|---|---|---|
| HVR01-01 首次 Add：保存入库指令及三级明细 | `200 OK` | `Y` | `OK` | `2026-11-21 08:34:12` | PASS |
| HVR01-02 相同 Payload 重复 Add：复用成功结果（旧验收规则） | `200 OK` | `Y` | `OK` | `2026-11-21 08:34:12` | 历史 PASS；已被新规则取代 |
| HVR01-03 相同单号、不同 Payload：按旧规则拒绝 | `200 OK` | `N` | `BUS01: The reference "HVR01-20261121-IN-` | `2026-11-21 08:34:13` | 历史 PASS；已被新规则取代 |
| HVR01-04 货主档案不存在时按编码自动创建并关联 | `200 OK` | `Y` | `OK` | `2026-11-21 08:34:13` | PASS |
| HVR01-05 已有货主编码复用同一档案 | `200 OK` | `Y` | `OK` | `2026-11-21 08:34:13` | PASS |
| HVR01-06 相同 productCode 按不同 owner 匹配各自变体 | `200 OK` | `Y` | `OK` | `2026-11-21 08:34:14` | PASS |
| HVR01-07 数量 0 是合法 DECIMAL 值 | `200 OK` | `Y` | `OK` | `2026-11-21 08:34:14` | PASS |
| HVR01-08 可选 snList 缺省 | `200 OK` | `Y` | `OK` | `2026-11-21 08:34:14` | PASS |
| HVR01-09 一次报告多个缺失表头必填字段 | `200 OK` | `N` | `REQ01: 缺失字段: owner, businessType` | `2026-11-21 08:34:15` | PASS |
| HVR01-10 报告明细行缺失字段的完整路径 | `200 OK` | `N` | `REQ01: 缺失字段: details[0].productName` | `2026-11-21 08:34:15` | PASS |
| HVR01-11 必填 owner 为 null | `200 OK` | `N` | `REQ01: 空值字段: owner` | `2026-11-21 08:34:15` | PASS |
| HVR01-12 明细 quantity 为非法 DECIMAL | `200 OK` | `N` | `TYP01: 类型错误字段: details[0].quantity` | `2026-11-21 08:34:15` | PASS |
| HVR01-13 校验失败修正后使用同一单号重试 | `200 OK` | `Y` | `OK` | `2026-11-21 08:34:16` | PASS |
| HVR01-14 产品 owner + productCode 组合不存在 | `200 OK` | `N` | `BUS01: Product code HVR01-20261121-PRODU` | `2026-11-21 08:34:16` | PASS |
| HVR01-15 Del 仅取消订单，不物理删除 | `200 OK` | `Y` | `OK` | `2026-11-21 08:34:16` | PASS |
| HVR01-16 重复 Del 不产生重复副作用 | `200 OK` | `Y` | `OK` | `2026-11-21 08:34:16` | PASS |
| HVR01-17 按旧规则删除后创建修改版订单 | `200 OK` | `Y` | `OK` | `2026-11-21 08:34:17` | 历史 PASS；已被新规则取代 |
| HVR01-18 无效 Bearer Token | `401 UNAUTHORIZED` | `N` | `AUTH01: API认证失败` | `2026-11-21 08:34:17` | PASS |
| HVR01-19 有效 Token 对应的 API User 未配置 WMS Project | `200 OK` | `N` | `BUS01: The authenticated API user has no` | `2026-11-21 08:34:17` | PASS |

**HTTP 场景汇总：** 19/19 符合各自预期。每个响应键集合均为 `returnStatus`、`exceptionInfo`、`operationTime`，`exceptionInfo` 长度不超过 40 字符。异常业务诊断较长时，响应按契约长度限制；ORM API 日志保留完整消息。日志记录范围为 API01 专属路径及 HVR01 业务键。

## 共用能力与后台入口

- **认证 / 错误响应：** 无效 Token（HVR01-18）返回 HTTP 401、`AUTH01` 三字段；有效 Token 但 API User 无 Project（HVR01-19）返回 `BUS01` 三字段，并在共享 API 日志保留内部诊断。
- **必填 / 类型校验：** HVR01-09/10/11 分别验证多个缺失字段、嵌套路径及 `null`；HVR01-12 验证非法 DECIMAL；校验失败没有产生订单；HVR01-13 修正同业务键后成功。
- **幂等（旧验收规则）：** HVR01-02 精确重放返回相同成功响应，HVR01-16 重复 Del 安全重放，HVR01-17 Del 后修改版 Add 创建新记录。项目负责人后来明确要求同一 `inboundOrderNo` 首次 Add 成功后任何 Add 都必须返回重复错误；本节历史结果不再代表当前 API01 Add 验收。
- **限流：** 额外以同一 API User 在 0.104 秒内提交 11 次空请求；前 10 次进入 Required Validator，11 次中第 11 个请求返回 HTTP 429、`RATE01`、`Retry-After: 1`。没有创建业务数据。
- **Ginlong 菜单/日志/幂等只读入口：** 使用本地 HVR `stock.group_stock_manager` 账号经 Backend JSON-RPC 登录，菜单可见 `Ginlong APIs`、`API 日志`、`幂等记录`；分别读取到 19 条 HVR API 日志、9 条 API01 幂等记录。ORM ACL 核验日志和幂等模型 `read=True, write=False, unlink=False`。这验证了可访问性和只读权限，未通过浏览器截图或 Administrator 账号完成视觉人工验收。

## ORM 持久化与副作用（自动化执行后、清理前）

- HVR 前缀入库订单共 8 张：7 张活动、1 张取消；API01 首次 Add 与重复 Add 最终只保留一张原单，Del 后新增修改版为另一张记录。
- 不存在货主 `HVR01-20261121-OWNER-AUTO` 经 API01 创建且唯一一条；Owner A/B 各一条。
- 相同 `productCode` 的 Owner A/B 分别关联 `product.product` 变体 ID `1617` / `1618`。
- API01 幂等表有 9 条成功记录；精确重放未另建成功记录，失败的业务/字段请求没有留下成功占位。
- 19 条 HVR HTTP 日志均为 Ginlong 三字段响应；测试 Token 未出现在请求/响应/错误日志字段。
- 3 个 HVR 产品没有 `stock.move`、`stock.quant`；HVR 入库订单没有关联 Picking。订单接收未确认实际仓库执行或改变库存。

## 人工复测前清理

- 按项目负责人要求，通过 Odoo ORM 删除本轮创建的 8 张 HVR01 入库单及其子明细。
- 删除与这批测试业务键对应的 9 条 API01 幂等记录，避免人工使用相同报文时重放旧成功结果。
- 删除 API01 自动建档场景创建的唯一 `OWNER-AUTO` 联系人，使 HVR01-04 能重新验证自动建档。
- 保留当时已有的 19 条 API 日志、Owner A/B、3 个测试产品变体、API 测试用户和本地凭据文件；清理时确认订单、幂等记录和 `OWNER-AUTO` 均为 0，库存作业记录仍为 0。

## 清理后的人工 HVR01-01

项目负责人随后使用现有 API01 报文完成首次 Add，报告响应为 HTTP 200、`returnStatus=Y`、`exceptionInfo=OK`、`operationTime=2026-11-22 03:24:17`。Odoo ORM 核验订单 ID 713（state=`new`、货主编码和 `KRWH` 正确、产品变体 ID 1617、数量 3、1 条 SN、无 Picking），API 日志 ID 2056 为 success，幂等记录 ID 1559 为 Add/succeeded。HVR01-01 已在人工执行记录判定 PASS；该订单及其幂等记录保留供后续人工检查。

## 人工 HVR01-02：同 Payload 重复 Add

首次人工结果保留为 FAIL：项目负责人重发相同报文时响应为 `Y / OK`，`operationTime=2026-11-22 03:24:17`，日志 ID 2057 记为成功；当时 Order 713 未重复创建，幂等 ID 1559 的 `attempt_count=1`。在 `.35` 复测时，项目负责人再次发送相同 Payload，收到 `N / IDM02: 重复新增，冲突键: inboundOrderNo`，`operationTime=2026-11-22 04:03:06`。Odoo ORM 核对错误日志 ID 2233、原 Order 713、原成功幂等 ID 1559 均符合预期：订单未变化，幂等成功记录仍只有一条且 `attempt_count=1`。因此记录为“首次 FAIL、复测 PASS”，不覆盖首次失败证据。

## 人工 HVR01-03：不同 Payload 重复 Add

项目负责人对同一 `inboundOrderNo=HVR01-20261121-IN-001` 发送不同 Payload，将备注改为“同一入库单号的不同报文，不得覆盖原记录”，并将数量从 3 改为 99。接口返回 `N / IDM02: 重复新增，冲突键: inboundOrderNo`，`operationTime=2026-11-22 04:04:19`。Odoo ORM 核对 API 日志 ID 2234 为 IDM02/error；订单仍只有 ID 713，state=`new`、备注仍为 `HVR01 本地人工验收`、数量仍为 3；幂等记录仍只有 ID 1559、Add/succeeded、`attempt_count=1`。HVR01-03 判定 **PASS**。

## 结论与限制

**历史模拟自动化验证：PASS（原验收规则）。** 本地 HTTP API01 19 个用例、11 次限流边界、Backend JSON-RPC 菜单及日志/幂等读取、ORM 数据和副作用核对均完成。HVR01-02、03、17 的旧规则测试结果保留作历史证据，须以本轮代码修复后的定向自动化和人工复测结果取代当前验收状态。

**人工 HVR：部分完成。** HVR01-01 PASS；HVR01-02 首次 FAIL、`.35` 复测 PASS；HVR01-03 不同 Payload 重复 Add PASS；HVR01-04/05 货主创建及复用 PASS；HVR01-06 同码跨货主产品变体隔离 PASS；HVR01-07 数量 0、原材料非 SN 管理及新单省略 `snList` PASS；HVR01-08 独立省略 `snList` 场景 PASS；HVR01-09 多缺失字段汇总并在业务处理前拦截 PASS。HVR01-10 及之后人工实例仍为 NOT RUN。当前人工验证没有浏览器截图；Backend JSON-RPC 检查使用的是 HVR 库存管理员账号；该历史运行没有运行整套 Odoo 单元测试。

## 2026-11-22 重复 Add 规则修复验证

- **当前规则：** 项目负责人确认首次 Add 成功后，相同 `inboundOrderNo` 的任何后续 API01 Add（无论报文相同、内容变化或此前已 Del）均须返回 `N / IDM02`，不得重放成功响应、修改原单或新增订单。
- **实现版本：** `ginlong_apis 18.0.2.0.35`；通过现有 Odoo 测试运行器升级，Odoo Shell ORM 确认数据库 `odooce_karlrapp` installed/latest 版本均为 `.35`。
- **定向自动化：PASS。** `/private/tmp/api01_duplicate_add_idempotency_targeted_final.log` 有 4 个 post-tests、0 failed / 0 error，覆盖真实 HTTP API01 路由的相同 Payload 重复、改 Payload 重复、Del 后重加，以及 ORM 单据/幂等记录不变、独立 IDM02 错误日志。
- **完整 Ginlong 回归：FAIL。** `/private/tmp/api01_duplicate_add_idempotency_final.log` 有 66 个 post-tests、1 failed / 0 error。唯一失败是产品身份回归检查既有数据库产品 ID 1619 的 Owner 属性行；Odoo Shell ORM 确认它是 HVR01-AUTO 记录且属性行数为 0。没有修改该产品或放宽断言；此失败单独保留于 ATR。
- **人工验收：** HVR01-02 首次响应 `Y/OK` 及日志 2057 保留为 FAIL；`.35` 复测响应 `N/IDM02` 及错误日志 2233 经 ORM 核对，判复测 PASS。HVR01-03 不同 Payload 重复 Add 收到 `N/IDM02`，日志 2234 和 ORM 记录确认原订单数量/备注及幂等记录未变，判 PASS。后续人工实例状态按本节下方逐项记录更新；当前 HVR01-10 及之后仍为 NOT RUN。

## 人工 HVR01-04：货主自动建档

项目负责人提交 API01 Add 后收到 `Y / OK`，`operationTime=2026-11-22 08:37:47`。Odoo ORM 核对：货主 `HVR01-20261121-OWNER-AUTO` 仅有 Partner ID 1143；入库单 `HVR01-20261121-IN-AUTO-OWNER` 为 Order ID 756，其 `ginlong_owner_id` 指向 Partner 1143；API 日志 ID 2238 为 success，幂等 ID 1692 为 API01/Add/succeeded，`attempt_count=1`。HVR01-04 的货主自动建档及关联验收判定 **PASS**。

入库模型为 Order—外层分组—子层产品的三级结构。外层分组 `product_id` 为空符合模型结构；ORM 已确认 Order 756 的子层产品行关联 Variant ID 1619，因此产品与货主关联正确。

## 人工 HVR01-05：复用已存在货主

项目负责人提交 Owner A 的 API01 Add 后收到 `Y / OK`，`operationTime=2026-11-22 08:38:45`。Odoo ORM 核对：`HVR01-20261121-OWNER-A` 仍只有 Partner ID 1080；新入库单 `HVR01-20261121-IN-OWNER-REUSE` 为 Order ID 757，其 `ginlong_owner_id` 指向既有 Partner 1080；API 日志 ID 2239 为 success，幂等 ID 1693 为 API01/Add/succeeded，`attempt_count=1`。HVR01-05 的货主档案复用判定 **PASS**。

入库模型为三级结构；ORM 已确认 Order 757 的子层产品行关联 Owner A Variant ID 1617。

## 人工 HVR01-06：同码产品跨货主变体隔离

项目负责人提交 Owner B 的 API01 Add 后收到 `Y / OK`，`operationTime=2026-11-22 08:52:50`。ORM 核对到同一 `productCode=HVR01-20261121-PROD-COMMON` 的 Owner A/B 变体分别为 ID 1617/1618；Order `HVR01-20261121-IN-OWNER-B`（ID 758）关联 Owner B（Partner 1081），其三级结构子层产品行关联 `product_id=1618`，未误用 Owner A 的 1617。API 日志 ID 2240 为 success，幂等 ID 1694 为 API01/Add/succeeded，`attempt_count=1`。HVR01-06 判定 **PASS**。

## 人工 HVR01-07：quantity=0 与原材料 SN 跟踪

项目负责人提交 `HVR01-20261121-PROD-COMMON`（Owner A）数量为 0 的 API01 Add 后收到 `Y / OK`，`operationTime=2026-11-22 08:56:55`。Odoo ORM 核对：Order ID 759 已创建，三级结构子层产品行为 Variant ID 1617，数量保存为 `0.0`；该变体的 `ginlong_product_form=原材料`、`tracking=none`，因此此产品不按 SN 管理。API 日志 ID 2241 为 success，幂等 ID 1695 为 API01/Add/succeeded，`attempt_count=1`。HVR01-07 判定 **PASS**。

项目负责人随后再次用单号 `HVR01-20261121-IN-ZERO` 发送省略 `snList` 的 Add，收到 `N / IDM02`（日志 ID 2242），符合重复 Add 规则。之后改用新单号 `HVR01-20261121-IN-ZERO1`，保持 `quantity=0` 且省略 `snList`，收到 `Y / OK`，`operationTime=2026-11-22 08:59:34`。ORM 核对 Order ID 760 的数量为 `0.0`、SN 数为 0、`ginlong_sn_list_json=[]`，产品仍为原材料 Variant 1617 / `tracking=none`；日志 ID 2243 success，幂等 ID 1696 succeeded。第二次新单验证 PASS。此时 HVR01-08 独立 quantity=3 报文尚未执行；之后的人工执行结果见下方 HVR01-08 记录。

## 人工 HVR01-08：独立省略 snList 场景

项目负责人发送省略 `snList`、数量为 3 的 API01 Add 后收到 `Y / OK`，`operationTime=2026-11-22 09:02:57`。Odoo ORM 核对：Order ID 761 已创建，三级子层产品 Variant ID 1617 数量为 3，`product_serial_number_ids` 为空；该产品为原材料、`tracking=none`。日志 ID 2244 的 request_data 不含 `snList`，响应为成功；幂等 ID 1697 为 API01/Add/succeeded，`attempt_count=1`。HVR01-08 判定 **PASS**。

## 人工 HVR01-09：汇总多个缺失必填字段

项目负责人发送同时缺少 `owner` 和 `businessType` 的 Add 请求，收到 `N / REQ01: 缺失字段: owner, businessType`，`operationTime=2026-11-22 09:08:37`。日志 ID 2245 记录完整诊断 `Required fields: owner is missing; businessType is missing`。Odoo ORM 确认该 `inboundOrderNo=HVR01-20261121-IN-MISSING-MULTIPLE` 没有创建入库订单，也没有幂等记录；必填校验在业务处理前拦截。HVR01-09 判定 **PASS**。

原始 curl 响应曾临时保存于 `/private/tmp/api01_hvr_http/`，其中包含 Odoo 的临时 `Set-Cookie`；该临时原始输出不纳入仓库交付。最终证据只保留脱敏后的响应字段、ORM 摘要及本报告。


## 2026-11-22 API01/API05 SN 身份规则定向自动化（非人工 HVR）

- Odoo 测试运行器通过真实测试 HTTP 路由运行 API01/API05 四个 SN 用例：4 post-tests，0 failed、0 error；日志 `/private/tmp/ginlong_api01_api05_sn_identity_r2.log`。
- API01 覆盖单条 SN quantity=3 拒绝、同产品同 SN 跨托盘拒绝、不同 productCode 同 SN 允许及新业务单据复用已有 `(productCode, productSN)`；API05 覆盖已存在 lot 与未入库 SN 引用、不同产品同 SN。各项均断言 ORM 保存/未写入结果。
- HVR01-29 的人工报文经本地结构预检：旧 v1 报文含 3 个产品、3 个托盘和 9 个不同真实 SN；其原材料只记录订单总量，现由 v2 新规则取代；未发送 HVR 请求。HVR01-29–33、HVR05-10–12 继续为 NOT RUN。
- 完整 Ginlong 模块最终回归 70 post-tests，1 failed、0 error；唯一失败为既有产品 ID 1619 缺 Owner 属性行，详见 ATR-RUN-032。数据库模块已由测试运行器升级到 `.37`；8099 常驻进程本轮未重启。
