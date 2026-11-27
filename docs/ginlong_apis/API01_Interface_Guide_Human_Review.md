# API01 接口说明 Human Review 记录

| 项目 | 内容 |
|---|---|
| 对应对外文档 | [API01_Interface_Guide.md](API01_Interface_Guide.md) |
| 文档版本 | 1.1 |
| 状态 | Human Review Draft |
| 日期 | 2026-11-24 |
| 用途 | 记录对外接口说明中移出的内部验收证据、实现差异、待确认项和编制依据 |

本记录供项目评审使用，不随 API01 对外指南交付。本文没有执行新 HTTP 请求或自动化测试；证据均引用现存项目记录及源码核对。

## 1. 认证与响应字段核对

- Token 入口为 /world_depot/api/auth/token。控制器签发 Token 时设置 3600 秒有效期，响应包含 access_token、expires_in 和 expires_at。
- 当前认证校验接受 Authorization Header 的裸 Token，也兼容 Bearer 前缀。对外指南遵循项目负责人确认的正式调用方式：Authorization: <ACCESS_TOKEN>，无 Bearer。
- API01 通过 Odoo fields.Datetime.now() 生成 operationTime，再格式化为 yyyy-MM-dd HH:mm:ss。当前 Odoo 实现使用 Python datetime.now() 的无时区时间值；响应没有 UTC offset。V3.2 未指定应按 UTC、北京时间或其他时区解释，仍需双方确认。

## 2. API01 Add、Del 与数据映射核对

### 2.1 Add

- 全局 Add 有效性按 inboundOrderNo 查找 state != cancel 的订单，不含 project 和 owner；有效键策略另由数据库约束保护并发。
- 对每条 details，实际产品查找条件为 Ginlong owner 编码 + Ginlong productCode；不退回到单字段 default_code 查询。
- 所有明细产品查找和业务校验完成后，才解析/创建订单关联货主联系人。因此：
  - owner 编码不存在时，货主联系人可在成功建单流程中按该编码建立并关联到订单。
  - 该自动建档不创建产品，不绕过 API07 产品档案。产品组合缺失时请求失败，不能因创建一个联系人就使订单可成功。
  - 产品记录可以在联系人尚未创建前已由 API07 建立；产品识别按其 Ginlong owner/productCode 字段组合。
- API01 不创建实际 Picking、SN 身份、库存移动或库存调整；snList 只按已批准业务类型条件保存为预报信息。
- 非保税 Add 的 snList 仍通过通用请求结构及字段类型校验，但业务层忽略它且不持久化成订单预报。对外指南据此区分“业务忽略”与“字段层仍检查数组结构/提供值类型”。

### 2.2 Del 状态语义与实现差异（需评审）

当前 API01 Del 行为核对：

1. API 必须先取得认证用户所属 WMS project。
2. 以当前 project、inboundOrderNo 和 state != cancel 查找目标。
3. 没有记录或多于一条记录时返回 BUS01；恰好一条时 API 直接将该记录状态写为 cancel。
4. 请求 owner 虽为必填字段，但目标定位不核对其是否等于已保存订单货主。
5. API Del 路径未调用 InboundOrder 的原生 action_cancel 方法，也没有单独检查订单 state 是否为 new、是否已有 confirm、或关联 Picking 是否已 done；它也没有执行原生取消流程中对未完成 Picking 的清理。

WorldDepot 原生 action_cancel 的行为不同：若订单已 confirm 且关联 Picking 为 done，会阻止取消；若未完成则尝试删除相关 Picking 后取消。API01 当前路径直接状态变更，因此状态拦截和关联作业单处理均未与该原生方法一致。

该差异不是新的业务规则。本次受限于“仅修订接口说明、不改代码”，故指南准确陈述现有 API 可观察条件，并将 completed Picking/确认状态的处理列为 Human Review 决策，保持文档 Draft。还应由评审决定是否核验 owner 与订单货主一致性；本轮指南说明当前并未执行该检查。

## 3. 字段校验与业务校验核对

- 必填表头和 Add 明细执行 Required 校验；零值 quantity 是合法字段值。
- DECIMAL 提供的非空值执行格式/精度检查；0 不作缺失值。
- 可选 remark 的 null/空字符串最终按无备注传入业务字段。
- snList 在 V3.2 为可选。null/空字符串按未提供处理；空数组表示零条。非空容器必须是数组，数组项必须是对象；已提供非空数值字段做类型校验。
- 非保税 Add 在业务层忽略 snList，不保留其业务预报数据；通用字段层仍可能拒绝结构错误的 snList。这不是互相矛盾，而是两个层次。
- bonded branch 下业务一致性由 services 校验，包括产品 tracking、SN 完整性、单 SN quantity=1、非 SN 原材料按 palletCode 分配、产品数量汇总、SN 重复和产品编码匹配。
- 当前 Required/Type validator 对 VARCHAR/CHAR/TEXT 不进行类型判定。因此字段表标注 VARCHAR 并不能证明任意非字符串 JSON 类型都会被拒绝；调用方应始终发送 JSON 字符串。本项是实现/契约严格性的核对结果，不在本轮改码。

## 4. 原指南内部执行记录迁移

旧版指南第 9 节中的生命周期请求、响应和实测时间已移入本节。真实样例曾在 2026-11-24 对单号 HVR08-20261124-API01-001 执行；以下测试标识和时间仅保留供内部审计。

- 首次 Add：HTTP 200，returnStatus=Y，exceptionInfo=OK，operationTime=2026-11-24 06:59:35。
- 同一有效订单重复 Add：HTTP 200，returnStatus=N，exceptionInfo=IDM02: 重复新增，冲突键: inboundOrderNo，operationTime=2026-11-24 07:12:58。
- 首次 Del：HTTP 200，Y/OK，operationTime=2026-11-24 07:16:23。
- 取消后重复 Del：HTTP 200，N/BUS01: 有效订单不存在或已取消，operationTime=2026-11-24 07:16:25。
- 取消后同单号、不同内容重新 Add：HTTP 200，Y/OK，operationTime=2026-11-24 07:17:32。
- 新生命周期内再次 Add 返回 IDM02；第二生命周期 Del 成功，再次 Del 返回 BUS01。各请求保留在 Ginlong API 日志中。
- 该真实生命周期报文是 businessType=STANDARD、无 snList 的场景，不证明保税 SN/托盘示例已经人工验收。对外文档新增的保税示例是格式及规则示意，不作 PASS 声明。

## 5. HVR 与自动化历史状态（保留差异）

截至现有 API01 执行记录：
- 当前 HVR API01 v3 活动基线中，HVR01-31、32、33 有人工 PASS 记录；HVR01-29、30、34 记为 NOT RUN。旧归档版本中同编号场景的结果不能取代当前活动包状态。
- HVR01-31 为同产品重复 SN 跨托盘拒绝；HVR01-32 为不同产品可使用相同 SN 文本；HVR01-33 为不同 API01 单据可引用相同产品/SN。
- 旧 HVR01-29 有一次单独历史成功记录，但当前 v3 活动包将其列为 NOT RUN；两者须继续按版本区分，不合并成当前 PASS。
- CC-GIN-008 IHR 所载最终 Ginlong 自动化回归为 74 个 post-tests、0 failed、0 errors。自动化记录不代替未运行的 HVR 实例。
- 本轮没有执行 HVR、没有发送真实 Ginlong 请求，也没有新建测试订单。

## 6. 原指南规范差异与待确认项

| 项目 | 依据及观察 | 状态 |
|---|---|---|
| Authorization 格式 | 项目负责人确认裸 Token；当前认证代码还兼容 Bearer。 | 对外文档使用裸 Token。 |
| operationTime 时区 | V3.2 有日期格式，无时区定义；当前响应不含 offset，并由主机无时区时钟生成。 | 待 Ginlong/项目双方确认。 |
| Del 与关联收货作业 | API 路径只以 state != cancel 判有效并直接标 cancel；WorldDepot 原生取消对已 done Picking 有限制，并会清理未完成 Picking，但 API 路径未调用该流程。 | Human Review 必须裁定。 |
| Del 请求 owner 比对 | 请求 owner 必填，目标定位以当前 project + inboundOrderNo，不检查与订单保存货主是否一致。 | 请确认是否需要业务一致性校验；当前代码行为已如实写明。 |
| VARCHAR 类型 | JSON 配置声明 VARCHAR，但通用类型校验跳过文本类型；所见自动化记录未证明非字符串文本值一定拒绝。 | 调用方发送文本；如要求严格类型拒绝，应另行审批实施。 |
| 保税示例证据 | 新的三类完整 payload 为规则示例，不是人工 HTTP HVR 证据。 | 不得标 PASS；不扩大本轮 HVR。 |

## 7. 编制依据

- Ginlong V3.2《海外WMS与第三方系统集成》API01 字段、长度、类型和 O/V 必填定义，以及接口矩阵中的 API01 路径和 Action。
- [SRS v1.3](../requirement/SRS_ginlong_apis-v1.3.md)：全局 inboundOrderNo、有效记录、取消后重建及业务规则边界。
- [TDD v1.6](TDD-v1.6.md)：API01 Add/Delete 生命周期和保税预报 SN 处理。
- [CC-GIN-007 v1.0](../implementation/CC-GIN-007-v1.0.md)、[CC-GIN-008 v1.0](../implementation/CC-GIN-008-v1.0.md)：业务确认及验收基线。
- [ATR-GIN-008](../implementation/ATR-GIN-008.md) 与 [IHR-GIN-008](../implementation/IHR-GIN-008.md)：自动化和人工评审记录。
- [API01 HVR 执行记录](hvr/api01/HVR_API01_Execution_Record.md)：活动 HVR 状态和历史版本区分。
- [API07 接口说明](API07_Interface_Guide.md)：对外指南结构参照。
- 当前源码核对范围：ginlong_apis 的 API01 Controller、services、validators、Error Catalog；WorldDepot Token 签发、Token 验证及 Inbound Order 状态/取消逻辑。


