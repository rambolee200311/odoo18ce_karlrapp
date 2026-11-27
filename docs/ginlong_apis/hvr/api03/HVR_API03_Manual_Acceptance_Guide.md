# Ginlong API03 待出库单人工 HVR 指南

> **项目级流程优先：** 本指南中的 `api03_01_add.json` 等生命周期场景只用于 API03 专项。项目主链必须使用[项目级仓库业务流程 HVR](../HVR_Project_Business_Flow_Guide.md)中的 API03 Payload，在 API07 建档、API01 入库、实际 Incoming Picking Done、API09 确认同一 SKU 在库之后创建出库指令。项目主链出库单不能执行本指南的 Edit/Del 生命周期用例。

## 1. 验收目的与边界

通过真实 HTTP 请求验证 Ginlong API03 将待出库指令接收到现有 Odoo `world.depot.outbound.order`，以及 Add、Edit、Del、有效订单生命周期、幂等错误、货主与产品组合映射。

API03 仅创建/更新/取消业务出库订单，不代表仓库已备货或发货；本次不要确认订单、检查库存、创建 Picking 或过账库存。备货与实际发货分别由后续业务流程处理。

## 2. 测试环境与前置资料

以下前置数据通过本地 Odoo ORM 只读核实，编写本指南时 API03 测试单号均不存在：

| 项目 | 值 |
|---|---|
| 本地 Odoo | `http://127.0.0.1:8099` |
| API URL | `http://127.0.0.1:8099/api/ginlong/TPL_Pending_Delivery_Note` |
| HTTP / Content-Type | `POST` / `application/json` |
| Odoo 数据库 | `odooce_karlrapp` |
| ginlong_apis | ORM 核实 installed/latest 均为 `18.0.2.0.49` |
| API User 项目 | `HVR01-20261121 API01 HVR Project`；直接复用 API01 HVR 的 `hvr_api01_manual` API User |
| 项目仓库 | `KarlRapp-WH`；报文中的 Ginlong 仓库编码为 `KRWH` |
| 客户/收货方 | `HVR01-20261121 测试货主 A`，复用 API01 的既有联系人 |
| 货主 | `HVR01-20261121-OWNER-A`，与 API01 HVR 使用相同货主 |
| 产品 | API03 专项有效生命周期 Payload 已更新为 `HVR-PROJECT-FLOW-20261125-SN-001`；来源是项目级 API07 Add。专项出库单不创建 Picking、不改变库存 |
| 生命周期测试单号 | `HVR03-MANUAL-20261125-LIFE-01` |
| 同码跨货主测试单号 | `HVR03-MANUAL-20261125-PAIR-A`、`HVR03-MANUAL-20261125-PAIR-B` |

API03 HVR 与 API01 HVR 使用同一个项目和 API User。主要生命周期报文使用 API01 的 Owner A 与产品；收货方复用既有 Owner A 联系人，不创建测试主数据。跨货主专项用例仍使用同项目下已存在的 Owner B，以保留 `owner + productCode` 隔离验证。若执行前测试单号已被使用，应停止并为所有相关 payload 换一组未使用的 `outboundOrderNo`，不要删除历史订单或幂等记录。

不要为 API03 切换到另一套 API User。使用 API01 HVR 已用的 `hvr_api01_manual` 凭据和同一项目范围获取 Token；Key/Secret 不写入本指南。若使用 Postman 前置脚本，脚本中的 `api_key`、`api_secret` 必须属于这个 API User；脚本只会为这些凭据换取 Token，不会按接口自动切换用户。API01 与 API03 可以复用同一 Token，直到 Token 过期。若需要新 Token，通过现有本地认证入口获取：

```bash
curl --request POST \
  --url http://127.0.0.1:8099/world_depot/api/auth/token \
  --header 'Content-Type: application/json' \
  --data '{"api_key":"<本地 API Key>","api_secret":"<本地 API Secret>"}'
```

将响应中的 `access_token` 安全地放在当前终端环境变量，不要写入文件：

```bash
export GINLONG_HVR_TOKEN='<access_token>'
```

该接口实际认证 Header 是 `Authorization: <access_token>`，不加 `Bearer` 前缀。Token 有效期按当前认证配置管理；过期后重新获取，不要复用失效 Token。

## 3. 发送方式

从仓库根目录执行。脚本会真实 POST 请求文件，不会隐藏 HTTP 错误状态；负向场景也会正常打印响应：

```bash
bash docs/ginlong_apis/hvr/api03/test_data/send_api03.sh \
  docs/ginlong_apis/hvr/api03/test_data/payloads/api03_01_add.json
```

必须按测试用例顺序执行。每个请求完成后先保存 HTTP 状态和响应，再检查 Odoo 订单、API 日志及幂等记录；若实际结果与预期不同，停止后续依赖用例并记录，不要重复发送以“试到成功”。

## 4. API03 报文字段

### 必填表头

| 字段 | 类型 | 含义 |
|---|---|---|
| `owner` | 字符串 | Ginlong 货主编码 |
| `action` | 字符串 | `Add`、`Edit` 或 `Del`；大小写不敏感 |
| `outboundOrderNo` | 字符串 | 出库订单业务唯一键 |
| `warehouse` | 字符串 | Ginlong 仓库编码；本地样例为 `KRWH` |
| `businessType` | 字符串 | 业务类型；样例使用 `STANDARD` |

### `details[]` 每行必填

`productCode`、`productName`、`specificationModel`、`quantity`、`net_wt_machine`、`net_wt_total`、`pack_qty`、`pallet_qty`、`pallet_len`、`pallet_wid`、`pallet_hgt`、`unit_vol`、`pack_unit`、`pack_wt`、`pallet_total_wt`、`total_vol`、`carton_wt_total`、`gross_wt_total`。

请求模板已按 V3.2 必填字段配置完整填写。`remark`、`customer`、`address`、`consignee`、`contact`、`contactEmail`、`shippingMethod` 及明细 `order_no`、`unit` 是可选字段。示例显式提供已有收货方 `customer`，以便核验 Odoo `unload_company` 映射。

所有重量、尺寸、包装和体积数值在样例中使用 JSON number。它们是 HVR 示例值，用于检查字段映射，不代表额外的重量/体积换算或业务校验规则。

## 5. Odoo 后台检查

### 5.1 订单

打开 **WorldDepot → Outbound → Orders**，按 `Reference` 搜索 `outboundOrderNo`。在订单表单核对：

- Project 为 `HVR01-20261121 API01 HVR Project`。
- Owner / Ginlong Owner Code 为报文的 `owner`。
- Warehouse 显示项目仓库 `KarlRapp-WH`，Ginlong warehouse code 为 `KRWH`。
- Reference 等于 `outboundOrderNo`，客户为 `HVR01-20261121 测试货主 A`。
- 产品明细关联正确的货主产品变体；数量、产品名称、规格及 Ginlong 包装字段与请求相符。
- 新建的订单保持未确认状态；API03 不应产生 Picking 或库存变动。
- Delete 后原单保留且 `state=cancel`；重新 Add 后出现新的订单记录，旧取消记录仍保留。

不要点击 `Confirm`、`Check Available` 或 `Create Picking`。这些是后续 WMS 操作，不属于 API03 接收验收。

### 5.2 API 日志与幂等记录

以 Administrator 打开 **WorldDepot → Ginlong APIs → API 日志**，按 API=`API03`、业务唯一键=`outboundOrderNo` 检查每次 HTTP 请求、状态、响应和错误码。再打开 **WorldDepot → Ginlong APIs → 幂等记录**，核对 API、业务键、Action、生命周期/结果及状态。重复 Add 或被拒绝的 Del 不得显示为本次成功，也不得覆盖历史日志。

## 6. 当前人工验收状态

`HVR_API03_Execution_Record.md` 中各场景初始为 `NOT RUN`。自动化测试、ORM 预检和本指南的数据准备不能代替人工 HVR PASS。人工响应及 Backend/API Log/幂等证据由执行人填写；Codex 可在执行人报告已发送后使用 Odoo ORM 核对，但不代填人工判定。
