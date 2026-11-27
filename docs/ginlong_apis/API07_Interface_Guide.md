# API07 产品档案接口说明

| 项目 | 内容 |
|---|---|
| 接口编号 | API07 |
| 接口名称 | 物料接口 / Product Master |
| 文档版本 | 1.1 |
| 文档状态 | Human Review Draft |
| 编制日期 | 2026-11-24 |
| 适用读者 | Ginlong 接口调用方 |
| 调用方向 | Ginlong → Odoo |
| 接口对象 | `TPL_Product_Master` |

## 1. 接口概述

API07 用于向 Odoo 新增或修改产品档案。请求中的 `owner` 是货主编码，`productCode` 是 Ginlong 产品编码；产品档案按 `(owner, productCode)` 区分。

同一个 `productCode` 可以属于不同货主。不同货主的同码产品可以分别建立档案，但同码产品的共享属性必须一致。接口支持 `Add` 和 `Edit`，不支持 `Del`。

## 2. 地址与传输

| 项目 | 值 |
|---|---|
| HTTP Method | `POST` |
| URL Path | `/api/ginlong/TPL_Product_Master` |
| Content-Type | `application/json` |
| 字符编码 | UTF-8 |

完整 URL 为部署环境的 Odoo 主机地址加上述 URL Path。

## 3. 认证

先使用已分配的 API Key 和 API Secret 获取访问 Token：

```http
POST {ODOO_BASE_URL}/world_depot/api/auth/token
Content-Type: application/json
```

```json
{
  "api_key": "<API_KEY>",
  "api_secret": "<API_SECRET>"
}
```

成功结果包含 `access_token` 和 `expires_in`；当前 Token 有效期为 **3600 秒**。调用 API07 时使用以下 Header：

```http
Authorization: <ACCESS_TOKEN>
```

`Authorization` Header 的值直接填写 Token，不添加 `Bearer` 前缀。Token 过期后重新获取。不得在业务报文中传送 API Secret。

## 4. 请求参数

请求体为 JSON 对象，不包含 `details` 或 `snList` 数组。

| 字段 | 类型及长度 | 必填 | 说明 |
|---|---|---:|---|
| `action` | 字符串 | 是 | `Add` 或 `Edit`；大小写不敏感。 |
| `owner` | `VARCHAR(40)` | 是 | 货主编码，不是货主名称。 |
| `productCode` | `VARCHAR(40)` | 是 | Ginlong 产品编码。 |
| `productName` | `VARCHAR(100)` | 是 | 产品名称。 |
| `specificationModel` | `VARCHAR(100)` | 是 | 规格型号。 |
| `unit` | `VARCHAR(40)` | 是 | 计量单位名称；V3.2 未给出固定枚举。 |
| `power` | `VARCHAR(40)` | 否 | 功率。 |
| `nationalStandard` | `VARCHAR(100)` | 否 | 国家标准。 |
| `certificationModel` | `VARCHAR(100)` | 否 | 认证型号。 |
| `productForm` | `VARCHAR(40)` | 是 | 产品形态；允许值见 §5.4。 |
| `weight` | `DECIMAL(18,6)` | 否 | 重量数值。计量单位待确认，见 §10。 |
| `length` | `DECIMAL(18,6)` | 否 | 长度数值。计量单位待确认，见 §10。 |
| `width` | `DECIMAL(18,6)` | 否 | 宽度数值。计量单位待确认，见 §10。 |
| `height` | `DECIMAL(18,6)` | 否 | 高度数值。计量单位待确认，见 §10。 |

V3.2 的必填字段缺失、为 `null`、空字符串或纯空格时，请求会被拒绝。可选字段的省略、`null`、空字符串和 `0` 按下表处理；接口不会把空值自动转换成数值 `0`。

| 可选字段值 | `Add` 处理 | `Edit` 处理 |
|---|---|---|
| 字段省略 | 不为该字段写入请求值；新档案使用系统字段默认值。 | 保留该字段当前值。 |
| `null` | 与省略相同，不写入该字段请求值。 | 与省略相同，保留当前值。 |
| 空字符串 `""`，文本字段 | 接受空文本。 | 保存空文本，可清空 `power`、`nationalStandard` 或 `certificationModel`。 |
| 空字符串 `""`，数值字段 | 拒绝，返回 `BUS01`。 | 拒绝，当前数值不变。 |
| 数值 `0` | 合法数值，明确写入零。 | 合法数值，将当前值更新为零。 |

必填文本字段不能用 `null` 或空字符串代替。数值字段请按 `DECIMAL` 发送 JSON 数字；`0` 是有效值，不代表缺失。

## 5. 产品档案规则

### 5.1 Action

| Action | 行为 |
|---|---|
| `Add` | 新增货主与产品编码组合的产品档案。 |
| `Edit` | 修改已存在的货主与产品编码组合。重复发送相同 Edit 会再次执行更新。 |
| `Del` | 不支持。 |

### 5.2 业务唯一性与货主

- 产品业务唯一键为 `(owner, productCode)`。
- 同一组合已有有效产品时，任何再次 `Add` 均返回 `N` 和 `IDM07`；请求内容相同或不同都不会覆盖已有产品。
- 同一 `productCode` 配合不同 `owner` 可以分别建立产品档案。
- 如果 `owner` 编码不存在，系统会自动建立货主档案；API07 不自动创建产品以外的货主产品映射。

### 5.3 共享属性

同一 `productCode` 下，所有货主产品的以下属性必须一致：产品名称、规格型号、单位、功率、国家标准、认证型号、产品形态、重量和尺寸。新货主新增同码产品时，若共享属性与已有档案冲突，请求会被拒绝。

`Edit` 修改共享属性后，同码产品读取到的共享属性会随之更新。`productForm` 与同码现有产品不一致时返回 `BUS02`，不修改档案。单位没有 V3.2 固定枚举；系统可接受新的单位名称，不建立单位换算关系。

### 5.4 `productForm` 与 SN 管理

`productForm` 仅接受以下值：

| `productForm` | SN 管理 |
|---|---|
| `原材料` | 不按 SN 管理 |
| `半成品` | 按 SN 管理 |
| `成品` | 按 SN 管理 |

其他值返回 `BUS06`。API07 只维护产品档案，不提交 SN 清单；实际 SN 由仓库作业数据提供。

### 5.5 归档产品

- 对已归档但仍存在的目标产品执行 `Edit`，可更新请求提供的共享属性；该操作不会使产品重新启用。
- 对已归档产品执行 `Add`，共享属性一致时会恢复原有产品档案；恢复后再次 `Add` 按有效产品重复新增处理并返回 `IDM07`。
- 若目标产品档案不存在，`Edit` 返回 `BUS03`，不会创建新档案。

## 6. 响应格式

成功和失败响应均仅包含 Ginlong 规定的三个字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `returnStatus` | 字符串 | 成功为 `Y`；失败为 `N`。 |
| `exceptionInfo` | 字符串，最多 40 字符 | 成功为 `OK`；失败为 `错误码: 错误消息`。 |
| `operationTime` | 字符串 | 格式为 `yyyy-MM-dd HH:mm:ss`；不包含时区偏移，时区口径见 §10。 |

响应不会返回产品档案 ID 等内部字段。业务成功或拒绝应以 `returnStatus` 判断，不能只看 HTTP 状态码。业务拒绝通常为 HTTP 200；认证失败为 HTTP 401；请求限流为 HTTP 429 并带 `Retry-After`。

## 7. 错误码与重试

`exceptionInfo` 使用 `ErrorCode: ErrorMsg` 格式，最长 40 字符。消息可能在边界处省略；调用方应依据错误码处理，不要解析中文消息作为程序分支。

| 错误码 | 含义 | 调用方处理建议 |
|---|---|---|
| `AUTH01` | Token 缺失、无效或过期 | 重新获取 Token 后再提交。 |
| `RATE01` | 请求频率超限 | 等待 `Retry-After` 指定时间后再试；API07 默认每秒 100 次，实际阈值可配置。 |
| `RATE02` | 限流服务暂不可用 | 暂停请求并联系系统管理员；不要密集重试。 |
| `IDM01` | 相同业务请求正在处理中 | 等待当前请求处理结束，再按查询到的产品状态决定后续操作。 |
| `REQ01` | 必填字段缺失或为空 | 按错误消息中的字段名补齐请求。 |
| `REQ02` | 请求格式无效 | 检查 JSON 格式及请求体结构。 |
| `TYP01` | 字段类型错误 | 检查数值字段及小数位格式。 |
| `IDM07` | `(owner, productCode)` 已有有效产品，重复 Add | 不要再次 Add；要修改现有档案时使用 `Edit`。 |
| `BUS01` | 业务数据或共享属性冲突 | 根据返回原因修正字段后再提交。 |
| `BUS02` | 同码产品的 `productForm` 不一致 | 使用与该 `productCode` 已有档案一致的形态。 |
| `BUS03` | Edit 目标产品不存在 | 核对 `owner` 和 `productCode`；需要新增时使用 `Add`。 |
| `BUS05` | 单位名称匹配到多个档案 | 暂停该请求并联系系统管理员核对单位档案。 |
| `BUS06` | `productForm` 不受支持 | 使用 `原材料`、`半成品` 或 `成品`。 |
| `SYS01` | 系统处理失败；业务处理返回 `returnStatus=N`，HTTP 通常为 200，外层或传输错误也可能表现为 5xx | 先确认目标产品当前状态，再决定是否重试；不要因 `SYS01` 直接认定 Add 未生效。 |

**Add 重试注意事项：** 首次 Add 成功后，同一有效 `(owner, productCode)` 的任何再次 Add 均返回 `N / IDM07`，即使 Payload 完全相同。若 Add 返回 `SYS01`，先确认该组合是否已存在：存在时不要重试 Add；需要调整时使用 Edit。只有确认产品不存在时才重新 Add。`SYS01` 表示系统处理失败，不代表重复新增，也不保证请求未产生业务结果。

## 8. 已验证的请求与响应实例

以下为已实际验证通过的业务请求及对应响应。发送时按 §3 添加认证 Header；不要将凭据放入 JSON 请求体。

### 8.1 首次 Add

```json
{
  "action": "Add",
  "owner": "HVR07-20261119-OWNER-A",
  "productCode": "HVR07-20261119-RAW-A",
  "productName": "HVR07 原材料产品",
  "specificationModel": "HVR07-RAW-MODEL",
  "unit": "台",
  "productForm": "原材料",
  "power": "5kW",
  "nationalStandard": "HVR07-STD",
  "certificationModel": "HVR07-CERT",
  "weight": 0,
  "length": 0,
  "width": 0,
  "height": 0
}
```

```json
{
  "returnStatus": "Y",
  "exceptionInfo": "OK",
  "operationTime": "2026-11-20 07:32:03"
}
```

### 8.2 有效产品重复 Add

再次发送 §8.1 的相同报文，响应为：

```json
{
  "returnStatus": "N",
  "exceptionInfo": "IDM07: 重复新增，冲突键(owner, productCode)",
  "operationTime": "2026-11-20 07:32:26"
}
```

将相同请求的 `productName` 改为其他值再次 Add，也返回 `IDM07`，已有产品不会被覆盖。修改已存在产品请使用 `Edit`。

### 8.3 不同货主使用相同产品编码

```json
{
  "action": "Add",
  "owner": "HVR07-20261119-OWNER-B",
  "productCode": "HVR07-20261119-RAW-A",
  "productName": "HVR07 原材料产品",
  "specificationModel": "HVR07-RAW-MODEL",
  "unit": "台",
  "productForm": "原材料",
  "power": "5kW",
  "nationalStandard": "HVR07-STD",
  "certificationModel": "HVR07-CERT",
  "weight": 0,
  "length": 0,
  "width": 0,
  "height": 0
}
```

该请求在共享属性与已有同码产品一致时返回：

```json
{
  "returnStatus": "Y",
  "exceptionInfo": "OK",
  "operationTime": "2026-11-20 08:58:13"
}
```

### 8.4 Edit 产品档案

```json
{
  "action": "Edit",
  "owner": "HVR07-20261119-OWNER-A",
  "productCode": "HVR07-20261119-EDIT-NAME",
  "productName": "HVR07 修改后名称",
  "specificationModel": "HVR07-EDITED-MODEL",
  "unit": "台",
  "productForm": "原材料",
  "power": "1kW",
  "weight": 1.25,
  "length": 100,
  "width": 50,
  "height": 40
}
```

```json
{
  "returnStatus": "Y",
  "exceptionInfo": "OK",
  "operationTime": "2026-11-20 10:03:02"
}
```

相同 Edit 请求可以重复提交；每次均按请求内容执行更新。

### 8.5 同码产品形态冲突

将已有 `productCode` 的 `productForm` 改为与同码产品不一致的值时，返回：

```json
{
  "returnStatus": "N",
  "exceptionInfo": "BUS02: 同productCode的productForm必须一致",
  "operationTime": "2026-11-20 09:20:20"
}
```

## 9. 调用注意事项

1. `owner` 必须传货主编码；货主名称不能代替编码。
2. 产品新增使用 `Add`，已有产品修改使用 `Edit`。重复 Add 不会执行更新。
3. 不同货主可以使用相同 `productCode`，但该编码下的共享属性必须一致。
4. `productForm` 仅支持 `原材料`、`半成品`、`成品`；产品形态决定是否按 SN 管理。
5. 可选字段不需要传值时省略；数值零应显式传 JSON 数字 `0`。不要以 `null` 或空字符串代替数值。
6. `unit` 是数量计量单位；重量及尺寸各自的计量单位尚待接口双方确认。当前接口不对重量和尺寸数值执行单位换算。
7. `operationTime` 不带时区偏移；V3.2 未明确时区口径，双方确认前不要自行换算。

## 10. 待确认的接口契约

| 字段/规则 | 待确认内容 |
|---|---|
| `weight` | V3.2 未说明计量单位及换算口径。 |
| `length`、`width`、`height` | V3.2 未说明长度单位及换算口径。 |
| `operationTime` | V3.2 规定日期时间格式，但未说明时区；响应不携带 UTC offset。 |

