# API01 CC-GIN-011 人工回归指南

## 目的与状态

CC-GIN-011 已由 Human Review 批准关闭。其自动化和 HTTP/ORM 测试结果见 [ATR-GIN-011](../../../implementation/ATR-GIN-011.md)。以下是返回项目 API01 HVR 后增加的人工回归项，用于确认实际服务的 API01 成功、重复、字段错误及认证响应。

本指南使用本地开发服务，不调用真实 Ginlong。所有实例初始状态均为 **NOT RUN**；由项目负责人实际发送请求并检查 Odoo 记录后判定。成功实例会在开发数据库留下一个测试入库订单，不要重复使用同一订单号或删除该记录。

### ORM 只读前置核对（2026-11-25）

| 对象 | 实际核对结果 |
|---|---|
| 数据库 / 模块 | `odooce_karlrapp`；`ginlong_apis` installed/latest=`18.0.2.0.49` |
| 本地服务 | `http://127.0.0.1:8099/web/login` 返回 HTTP 200 |
| 货主 | `HVR01-20261121-OWNER-A` 存在，Partner ID `1080` |
| 产品 | Owner A + `HVR01-20261121-PROD-COMMON` 唯一匹配 Variant ID `1617`；`productForm=原材料`、`tracking=none`、active |
| 回归订单号 | `HVR01-CC011-20261125-01` 尚无 `reference` 记录 |

以上只读结果不替代发送前核对；如实际执行时间距本记录较久，请先在 Ginlong 入库单菜单按订单号搜索，确认未被其他人占用。

本指南内 3 个 JSON 已通过 Required/Type 静态契约预检：首次 Add 和认证负向请求通过字段检查；缺少 owner 的请求按预期被 Required Validator 拒绝。此预检不替代真实 HTTP HVR。

## 环境与请求设置

| 项目 | 值 |
|---|---|
| URL | `http://127.0.0.1:8099/api/ginlong/TPL_Pending_Receipt_Note` |
| Method | `POST` |
| Content-Type | `application/json` |
| Authorization | `Authorization: <有效 Token>`，Token 原样放入 Header，不加 `Bearer` |
| 订单查询 | Odoo `WorldDepot → Ginlong APIs → 入库单`，按 `inboundOrderNo` 搜索 |
| 日志查询 | Odoo `WorldDepot → Ginlong APIs → API 日志`，按 API/业务键查询 |
| 幂等查询 | Odoo `WorldDepot → Ginlong APIs → 幂等记录`，按 API/业务键查询 |

在终端本地设置当前有效 Token，勿将 Token 放入 JSON 文件、截图或验收记录：

```sh
export GINLONG_HVR_TOKEN='在本机填入有效Token'
```

每个 JSON 文件均位于本指南旁边的 `test_data/cc011_regression/`。请求示例：

```sh
curl --include --request POST \
  --url http://127.0.0.1:8099/api/ginlong/TPL_Pending_Receipt_Note \
  --header "Authorization: ${GINLONG_HVR_TOKEN}" \
  --header 'Content-Type: application/json' \
  --data-binary @docs/ginlong_apis/hvr/api01/test_data/cc011_regression/01_add.json
```

## 执行顺序和预期

### CC011-API01-01：首次 Add 成功

1. 确认 `HVR01-CC011-20261125-01` 尚无有效入库单。
2. 使用有效 Token 发送 `01_add.json`。
3. 预期 HTTP `200`，响应仅有 `returnStatus`、`exceptionInfo`、`operationTime`，值为 `Y`、`OK` 和本次处理时间。
4. 在入库单菜单确认只创建一张该业务键订单；在 API 日志和幂等记录菜单确认成功记录。

### CC011-API01-02：同单号重复 Add

1. 不修改 `01_add.json`，原样再次发送。
2. 预期 HTTP `200`、三字段错误响应，`returnStatus=N`，`exceptionInfo` 为 `IDM02: 重复新增，冲突键: inboundOrderNo`；`operationTime` 应是本次请求时间。
3. 确认仍只有一张订单，原订单字段未变；API 日志追加本次拒绝记录，首次成功幂等记录保留。

### CC011-API01-03：必填字段错误

1. 发送 `03_missing_owner.json`。
2. 预期 HTTP `200`、三字段错误响应，`returnStatus=N`，`exceptionInfo` 指出缺失字段 `owner`。
3. 确认订单号 `HVR01-CC011-20261125-REQ-01` 未创建、没有成功幂等记录，并在 API 日志找到字段错误详情。

### CC011-API01-04：无效 Token

1. 发送 `04_invalid_token.json`，使用指南指定的无效 Token Header（无需使用真实 Token）。
2. Header 示例：`Authorization: INVALID_HVR_TOKEN`；不要加 `Bearer`。
3. 预期 HTTP `401`，响应仍仅含 Ginlong 错误三字段，错误码为 `AUTH01`。
4. 确认订单号 `HVR01-CC011-20261125-AUTH-01` 未创建，并在 API 日志找到认证拒绝记录。

```sh
curl --include --request POST \
  --url http://127.0.0.1:8099/api/ginlong/TPL_Pending_Receipt_Note \
  --header 'Authorization: INVALID_HVR_TOKEN' \
  --header 'Content-Type: application/json' \
  --data-binary @docs/ginlong_apis/hvr/api01/test_data/cc011_regression/04_invalid_token.json
```

## 验收记录

| 用例 | HTTP 状态 / 脱敏响应 | Inbound Order ID / ORM 结果 | API Log ID | 幂等记录 | 判定 |
|---|---|---|---|---|---|
| CC011-API01-01 首次 Add | 待填写 | 待填写 | 待填写 | 待填写 | NOT RUN |
| CC011-API01-02 重复 Add | 待填写 | 待填写 | 待填写 | 待填写 | NOT RUN |
| CC011-API01-03 缺失 owner | 待填写 | 待填写 | 待填写 | 待填写 | NOT RUN |
| CC011-API01-04 无效 Token | 待填写 | 待填写 | 待填写 | 待填写 | NOT RUN |

请仅记录脱敏响应和可见记录 ID；不要记录 Token、Secret、密码或完整认证 Header。自动化 PASS 不替代以上人工判定。
