# API01 入库单接口说明

| 项目 | 内容 |
|---|---|
| 接口编号 | API01 |
| 接口名称 | 入库单创建 / Pending Receipt Note |
| 文档版本 | 1.1 |
| 文档状态 | Human Review Draft |
| 编制日期 | 2026-11-24 |
| 适用读者 | Ginlong 接口调用方 |
| 调用方向 | Ginlong → Odoo |
| 接口对象 | TPL_Pending_Receipt_Note |

## 1. 接口概述

API01 接收 Ginlong 的入库订单及客户预报信息。请求成功表示订单指令已被 Odoo 接收，不表示 Karl Rapp 已完成收货，也不表示库存已经增加。

正式接口支持 Add 和 Del。修改已提交订单采用 Delete + Add：取消当前有效订单后，使用原 inboundOrderNo 提交新的 Add。API01 正式接口不支持直接 Edit。

## 2. 地址与传输

| 项目 | 值 |
|---|---|
| HTTP Method | POST |
| URL Path | /api/ginlong/TPL_Pending_Receipt_Note |
| Content-Type | application/json |
| 字符编码 | UTF-8 |

完整 URL 为部署环境 Odoo 主机地址加上述 URL Path。

## 3. 认证

先使用已分配的 API Key 和 API Secret 获取 Token：

~~~http
POST {ODOO_BASE_URL}/world_depot/api/auth/token
Content-Type: application/json
~~~

~~~json
{
  "api_key": "<API_KEY>",
  "api_secret": "<API_SECRET>"
}
~~~

认证成功后，从响应取得 access_token。当前 Token 有效期为 3600 秒。调用 API01 时，Authorization Header 的值直接填写 Token，不添加 Bearer 前缀：

~~~http
Authorization: <ACCESS_TOKEN>
~~~

Token 过期后重新获取。API Secret 只用于获取 Token，不得放入 API01 业务报文或共享文档。

## 4. 请求参数

请求体为 JSON 对象。一个订单只接受一个 owner。owner 必须是货主编码，不是货主名称。

### 4.1 表头

| 字段 | 类型及长度 | 必填 | 说明 |
|---|---|---:|---|
| owner | VARCHAR(40) | 是 | 货主编码。 |
| action | VARCHAR(10) | 是 | Add 或 Del，大小写不敏感。 |
| inboundOrderNo | VARCHAR(40) | 是 | 入库单号，也是 API01 业务唯一键。 |
| warehouse | VARCHAR(40) | 是 | Ginlong 仓库编码。 |
| businessType | VARCHAR(40) | 是 | 业务类型。只有精确值“保税_海外收货入库”启用第 6.1 节的保税预报规则。 |
| remark | VARCHAR(40) | 否 | 备注。 |

### 4.2 details 产品明细

Add 必须提供至少一条 details。Del 不要求 details。

| 字段 | 类型及长度 | 必填 | 说明 |
|---|---|---:|---|
| productCode | VARCHAR(40) | 是 | Ginlong 产品编码；与 owner 组合匹配已维护的产品档案。 |
| productName | VARCHAR(40) | 是 | 产品名称。 |
| specificationModel | VARCHAR(40) | 是 | 规格型号。 |
| quantity | DECIMAL(18,6) | 是 | 该产品的预报数量。 |

### 4.3 snList 预报行

V3.2 将 snList 及其行字段列为可选。保税业务和产品是否按 SN 管理，会进一步决定是否需要完整预报行，详见第 6 节。

| 字段 | 类型及长度 | V3.2 必填 | 说明 |
|---|---|---:|---|
| productSN | VARCHAR(100) | 否 | SN 管理产品的真实 SN；非 SN 原材料分托时等于 productCode。 |
| quantity | DECIMAL(18,6) | 否 | SN 管理产品每行必须为 1；非 SN 原材料表示对应托盘上的数量。 |
| palletCode | VARCHAR(40) | 否 | 该预报行对应的托盘码；适用保税预报时须按业务规则提供。 |
| productCode | VARCHAR(40) | 否 | 预报行产品编码，须与本请求的 details 对应。 |
| productName | VARCHAR(100) | 否 | 预报行产品名称。 |
| specificationModel | VARCHAR(100) | 否 | 预报行规格型号。 |

### 4.4 字段校验与业务校验

字段校验先检查必填项和报文结构；随后才进行产品匹配、SN 管理和数量一致性等业务校验。

- 必填字段缺失、为 null、空字符串或纯空格时，请求被拒绝。
- Add 的 details 必须是非空数组；Del 不要求 details。
- 可选 remark 省略、传 null 或传空字符串均表示没有备注。
- 可选 snList 省略、传 null 或传空字符串均按未提供处理；空数组表示没有预报行。非空值须为数组，行须为对象。
- 非空数组中的 DECIMAL 字段必须使用合法数值或数字字符串；不要用 null 或空字符串代替数量。
- 数值 0 是合法的字段值，不会在字段校验阶段视作缺失。之后仍会执行适用的业务校验，例如保税产品的 SN/预报数量一致性。
- 字符串字段请按 V3.2 发送文本值。字段格式合规不代表产品、订单或预报业务规则也已通过。

## 5. Add、Del 与订单生命周期

### 5.1 Add 与业务唯一键

API01 以 inboundOrderNo 作为全局业务唯一键，不因 owner 或调用账户授权范围而区分。

- 如果同一 inboundOrderNo 存在未取消的有效订单，任何再次 Add 均被拒绝并返回 IDM02；报文相同或不同不改变结果。原订单不会被覆盖或重复创建。
- 如果没有有效订单，包括该单号只有已取消历史订单的情况，允许按正常校验和创建流程提交 Add。
- 取消历史订单保留。重新 Add 会建立新的有效订单生命周期。
- 所有 details.productCode 必须已在对应 owner 下维护。API01 不创建产品档案。

### 5.2 Del 的有效订单条件

Add 的重复判定以全局 inboundOrderNo 和“未取消”状态为准。Del 的目标则必须在当前认证 API 用户的授权业务范围内，按 inboundOrderNo 找到且仅找到一张未取消订单：

- 未找到有效订单、订单已取消，或同项目内匹配记录不唯一时，Del 返回业务错误。
- 已取消历史单不能作为再次 Del 成功的依据；重复 Del 不重放先前的成功响应。
- 当前 API 的可观察 Del 条件是订单状态不等于 cancel；订单 state 为 new 或 confirm 时均满足此条件。接口会把该订单标为 cancel。
- owner 是请求必填字段，但当前 Del 的目标查找依据是当前项目与 inboundOrderNo；它不将请求 owner 与订单中保存的货主另作一致性判断。
- 当前 API Del 仅检查订单是否未取消，不另外检查或处理关联的仓库作业单。已完成或未完成的关联作业记录与“可取消”的边界，仍待双方确认。

因此，接口调用方应区分“尚未取消的有效订单”和“业务上允许取消的订单”。本指南暂不把所有未取消订单都描述为已经确认可安全取消。

### 5.3 使用 Delete + Add 修改

修改订单不是再次 Add 覆盖旧数据，也不是直接发送 Edit。仅当确实需要撤销当前订单并以新报文重建时，才按业务流程先 Del，再用原 inboundOrderNo Add。

收到 IDM02 时，不要自动发送 Del。先通过双方约定的业务查询/管理流程核对当前订单；只有确实需要修改且该单据允许取消时，才由授权业务流程执行 Del + Add。

### 5.4 owner 与产品档案

- 每条明细按 owner + productCode 匹配已存在的货主产品档案；不存在或存在歧义时，请求失败。
- 如果 owner 编码尚无货主联系人档案，API01 可在订单创建流程中自动建立货主档案并关联订单。
- 自动创建的是货主联系人档案，不是产品档案，也不绕过产品匹配。所有产品明细必须先能按 owner + productCode 匹配到已有产品；若产品不匹配，API01 不会因为 owner 自动创建规则而接受该订单。
- 相同 productCode 可以属于不同 owner；不能只按 productCode 跨货主匹配。

### 5.5 客户预报与实际收货

API01 保存的是客户预报，不创建实际 Picking、库存移动、实际 SN 身份或实际托盘库存对象，也不改变物理库存。实际仓储作业完成后，Odoo 根据实际收货记录保存结果。API04 的入库完成回传使用实际收货数据，不用 API01 预报冒充实绩。

## 6. SN 与托盘预报规则

### 6.1 businessType = 保税_海外收货入库

产品是否按 SN 管理，以对应 owner + productCode 的产品档案为准。

**SN 管理产品：**

- 必须提供覆盖 details 中该产品全部数量的 snList。
- 每个 productSN 为真实 SN，每条 quantity 必须为 1。
- 同一请求内，同一产品的同一 SN 不得重复，即使 palletCode 不同也拒绝。
- 每条 SN 的 productCode 必须对应本请求 details 中的产品。

**非 SN 管理原材料：**

- 可以省略 snList；此时只提供订单产品总量，不提供原材料托盘分布。
- 如提交分托行，productSN 必须等于该行 productCode；quantity 表示该托盘上该原材料的实际预报数量，可大于 1。
- 同一原材料可按多个 palletCode 提交多行。

**共同规则：**

- 对提供了 snList 行的产品，snList.quantity 按 productCode 汇总后必须等于 details.quantity。
- 同一产品可以分布在多个托盘；同一托盘可以包含多种产品。
- SN 身份按 (productCode, productSN) 区分，托盘不参与身份判定；不同产品可使用相同 SN 文本。同一产品/SN 可在不同 API01 入库单中再次引用。
- 任一产品、SN、托盘或数量一致性检查失败，整单拒绝。

### 6.2 其他 businessType

只有 businessType 精确等于“保税_海外收货入库”时，才启用上述保税预报规则。

其他 businessType 的 Add 不以 snList 执行业务校验或保存预报明细；不过报文仍须符合通用字段结构和类型规则。例如，非空 snList 仍须是结构合法的数组。不要依赖在非保税报文中传入的 snList 作为订单预报数据。

## 7. 响应格式

成功和失败响应均仅包含 Ginlong 规定的三个字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| returnStatus | 字符串 | 成功为 Y；失败为 N。 |
| exceptionInfo | 字符串，最多 40 字符 | 成功为 OK；失败为“错误码: 错误消息”。 |
| operationTime | 字符串 | 格式为 yyyy-MM-dd HH:mm:ss；不带时区偏移，时区口径见第 10 节。 |

调用方应检查 returnStatus，不要只按 HTTP 状态码判断业务操作结果。业务接受或拒绝通常使用 HTTP 200；认证失败使用 HTTP 401；请求超限使用 HTTP 429 并提供 Retry-After；限流服务故障可返回 HTTP 503。系统级异常还可能通过 HTTP 5xx 返回。

## 8. 错误码与重试

exceptionInfo 使用 ErrorCode: ErrorMsg 格式，最多 40 个字符。消息过长时可能缩短；程序逻辑应按错误码判断，不应解析中文消息。

| 错误码 | 含义 | 建议处理 |
|---|---|---|
| AUTH01 | Token 缺失、无效或过期 | 重新获取 Token，再按调用方的请求追踪信息核对本次操作是否已处理。 |
| RATE01 | API01 请求频率超限 | 等待 Retry-After 指定的时间后再发送。默认限值为每秒 10 次，可由管理员配置。 |
| RATE02 | 限流服务暂不可用 | 暂停密集请求，联系系统管理员；收到服务恢复信息后再处理。 |
| REQ01 | 必填字段缺失或空值 | 按返回字段名修正请求。 |
| REQ02 | 请求 JSON 或结构无效 | 检查 JSON 语法及对象/数组结构。 |
| TYP01 | 字段类型错误 | 检查 DECIMAL 数量等类型和格式。 |
| IDM01 | 相同业务事件正在处理中 | 不要并发重发；等待当前请求结束，并通过双方约定的业务查询/管理方式核对结果。 |
| IDM02 | inboundOrderNo 已有未取消订单，重复 Add | 不自动 Del。先核对现有订单；仅当确有业务修改需求且该订单符合取消流程时，才有意执行 Delete + Add。 |
| BUS01 | 业务条件或数据关联检查失败 | 根据具体消息检查货主产品匹配、SN/托盘/数量或订单状态。已取消单再次 Del 也会得到业务错误。 |
| SYS01 | 系统处理失败，结果可能需要核实 | 不要盲目重复 Add 或发送 Del。先通过双方约定的订单查询/管理渠道确认是否已创建或取消，再决定后续操作。 |

对 IDM01、IDM02 或 SYS01，不要仅因重试方便就取消订单。取消会改变订单有效状态；只有业务负责人确认需要修改且该订单符合取消条件时，才执行取消流程。

## 9. 保税入库请求与响应示例

以下三个示例说明请求结构和预期响应结构。实际提交前，owner + productCode 必须已在 API07 产品档案中维护。示例响应时间仅作格式演示，实际 operationTime 由服务生成。

### 9.1 SN 管理产品跨托盘

同一 SN 管理产品分布在两个托盘，3 条单件 SN 与明细数量相等。

~~~json
{
  "owner": "2110",
  "action": "Add",
  "inboundOrderNo": "IN-20261124-FG-001",
  "warehouse": "SHANGHAI_WAREHOUSE_01",
  "businessType": "保税_海外收货入库",
  "remark": "海外收货入库预报",
  "details": [
    {
      "productCode": "050101030003",
      "productName": "Solis第6代户用并网单相5kW逆变器",
      "specificationModel": "S6-GR1P5K-S",
      "quantity": 3
    }
  ],
  "snList": [
    {
      "productSN": "FG-SN-0001",
      "quantity": 1,
      "palletCode": "PALLET-001",
      "productCode": "050101030003"
    },
    {
      "productSN": "FG-SN-0002",
      "quantity": 1,
      "palletCode": "PALLET-001",
      "productCode": "050101030003"
    },
    {
      "productSN": "FG-SN-0003",
      "quantity": 1,
      "palletCode": "PALLET-002",
      "productCode": "050101030003"
    }
  ]
}
~~~

~~~json
{
  "returnStatus": "Y",
  "exceptionInfo": "OK",
  "operationTime": "2026-11-24 12:00:00"
}
~~~

### 9.2 非 SN 原材料分托

原材料总量为 12，分布在 3 个托盘；每行 productSN 等于 productCode。

~~~json
{
  "owner": "2110",
  "action": "Add",
  "inboundOrderNo": "IN-20261124-RM-001",
  "warehouse": "SHANGHAI_WAREHOUSE_01",
  "businessType": "保税_海外收货入库",
  "remark": "原材料分托预报",
  "details": [
    {
      "productCode": "RM-RAW-0001",
      "productName": "安装支架原材料",
      "specificationModel": "BRACKET-01",
      "quantity": 12
    }
  ],
  "snList": [
    {
      "productSN": "RM-RAW-0001",
      "quantity": 5,
      "palletCode": "PALLET-001",
      "productCode": "RM-RAW-0001"
    },
    {
      "productSN": "RM-RAW-0001",
      "quantity": 4,
      "palletCode": "PALLET-002",
      "productCode": "RM-RAW-0001"
    },
    {
      "productSN": "RM-RAW-0001",
      "quantity": 3,
      "palletCode": "PALLET-003",
      "productCode": "RM-RAW-0001"
    }
  ]
}
~~~

~~~json
{
  "returnStatus": "Y",
  "exceptionInfo": "OK",
  "operationTime": "2026-11-24 12:01:00"
}
~~~

### 9.3 三托盘混装 SN 产品与原材料

三个托盘都包含 SN 产品和原材料；原材料按托盘拆分，SN 产品共 4 条单件 SN，两个产品各自合计与 details 数量一致。

~~~json
{
  "owner": "2110",
  "action": "Add",
  "inboundOrderNo": "IN-20261124-MIX-001",
  "warehouse": "SHANGHAI_WAREHOUSE_01",
  "businessType": "保税_海外收货入库",
  "remark": "混合产品分托预报",
  "details": [
    {
      "productCode": "050101030003",
      "productName": "Solis第6代户用并网单相5kW逆变器",
      "specificationModel": "S6-GR1P5K-S",
      "quantity": 4
    },
    {
      "productCode": "RM-RAW-0001",
      "productName": "安装支架原材料",
      "specificationModel": "BRACKET-01",
      "quantity": 12
    }
  ],
  "snList": [
    {
      "productSN": "FG-SN-1001",
      "quantity": 1,
      "palletCode": "PALLET-001",
      "productCode": "050101030003"
    },
    {
      "productSN": "FG-SN-1002",
      "quantity": 1,
      "palletCode": "PALLET-001",
      "productCode": "050101030003"
    },
    {
      "productSN": "RM-RAW-0001",
      "quantity": 5,
      "palletCode": "PALLET-001",
      "productCode": "RM-RAW-0001"
    },
    {
      "productSN": "FG-SN-1003",
      "quantity": 1,
      "palletCode": "PALLET-002",
      "productCode": "050101030003"
    },
    {
      "productSN": "RM-RAW-0001",
      "quantity": 4,
      "palletCode": "PALLET-002",
      "productCode": "RM-RAW-0001"
    },
    {
      "productSN": "FG-SN-1004",
      "quantity": 1,
      "palletCode": "PALLET-003",
      "productCode": "050101030003"
    },
    {
      "productSN": "RM-RAW-0001",
      "quantity": 3,
      "palletCode": "PALLET-003",
      "productCode": "RM-RAW-0001"
    }
  ]
}
~~~

~~~json
{
  "returnStatus": "Y",
  "exceptionInfo": "OK",
  "operationTime": "2026-11-24 12:02:00"
}
~~~

## 10. 调用注意事项与待确认事项

1. Authorization Header 直接放 Token，不加 Bearer；Token 有效期为 3600 秒。
2. owner 是编码；每条产品明细必须能按 owner + productCode 匹配已有产品档案。未知 owner 自动建档不等于自动建产品。
3. inboundOrderNo 是全局有效订单业务键；不同 owner 或调用账户授权范围使用相同单号，也不能并存多张未取消订单。
4. 收到 IDM02 不要自动取消；仅在确需修改、且订单允许取消时，按 Delete + Add 处理。
5. operationTime 使用 yyyy-MM-dd HH:mm:ss，不含时区偏移。V3.2 未定义该字符串的时区，双方确认前不要自行按 UTC 或本地时区换算。
6. API01 Del 对订单状态的检查与已完成收货记录之间的边界仍待双方确认；本版仅列明当前接口行为，不将其视作已确认的可取消条件。


