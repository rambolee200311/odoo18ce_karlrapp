# API07 产品档案 HVR 测试计划

> **HVR 状态：Frozen / Closed。** 2026-11-21 项目负责人批准按执行记录关闭本人工验收包。全部 22 项均按人工结果或项目负责人明确判定记录；HVR07-19 的数值型产品名称被接受，HVR07-22 的认证路径证据限制仍如实保留。

## 1. 目的与范围

本包只验收 Ginlong API07「物料接口」。依据 Ginlong V3.2 工作表「海外WMS与第三方系统的接口与处理逻辑」第 105–117 行、当前 `ginlong_apis` 路由/处理器、已批准的 API07 产品变体规则及已通过的自动化行为测试。

覆盖 API07 的 `Add` / `Edit`，不测试 Delete。通过真实本地 Odoo HTTP 路由发送 JSON，并由测试人员在 Odoo 后台核对 `product.template`、`product.product`、API 日志及幂等记录。HVR 结果必须由人工填写；自动化测试和 Codex 的数据准备不等于 HVR 通过。

## 2. 已核实的接口与数据规则

| 项目 | 已核实内容 |
| --- | --- |
| HTTP 入口 | `POST /api/ginlong/TPL_Product_Master` |
| Content-Type | `application/json` |
| 认证 | 当前项目请求 Header 为 `Authorization: <access_token>`，不加 `Bearer`；无效 Token 返回 401 |
| Action | API07 采用 `Add`、`Edit`，忽略大小写；本包不含 Delete |
| 唯一业务键 | Ginlong V3.2 说明为 `owner + productCode` |
| 必填字段 | `owner`、`productCode`、`productName`、`specificationModel`、`unit`、`productForm`；另含实现所需的 Add/Edit Action |
| 可选字段 | `power`、`nationalStandard`、`certificationModel`、`weight`、`length`、`width`、`height` |
| `productForm` | `原材料` → `tracking=none`；`半成品`、`成品` → `tracking=serial`；其他值拒绝 |
| Odoo 存储 | 同一原始 `productCode` 共享一个 `product.template`；不同货主对应不同 `product.product` 变体。模板保存名称、规格、单位、形态、tracking、功率及尺寸重量；变体保存 `ginlong_owner_code`、原始 `ginlong_product_code` 和内部 `default_code` |
| 新单位处理 | V3.2 未规定 `unit` 枚举；若 Odoo 中无同名单位，API07 在标准 `Unit` 类别自动创建 UoM，factor/factor_inv 均为 1，不推断换算关系 |
| 货主关联形式 | API07 在产品变体保存货主编码，并用原生 `Ginlong Owner` 产品属性生成货主变体；当前产品变体没有指向 `res.partner` 的货主 Many2one。测试联系人用于后台核对编码，不应误认为 API07 建立了联系人外键 |
| API 响应 | 严格返回 V3.2 的 `returnStatus`、`exceptionInfo`、`operationTime` 三个字段；成功 `returnStatus=Y`，业务/字段错误 `returnStatus=N`。不返回 Odoo 通用 `success`、`data`、`error` |

`action` 来自已确认的 Add/Edit 接口触发语义和现有 API07 实现，不是 V3.2 第 0701–0713 行的一项新增物料字段。`power` 在 V3.2 标为 VARCHAR；本包不把它的数值/字符串形式另行升格为规则。`weight`、尺寸按 DECIMAL 检查，合法 `0` 有效。

## 3. 测试环境与数据准备

- Odoo 数据库：`odooce_karlrapp`，配置：项目根目录 `odoo.conf`。
- 本地 API URL：`http://127.0.0.1:8099/api/ginlong/TPL_Product_Master`。端口来自 `odoo.conf` 的 `http_port=8099`。人工执行前确认服务仍运行；若已停止，参见 README 启动命令。
- Odoo 前置记录只通过 `odoo shell -c odoo.conf` 和 ORM 创建。准备脚本建立两个带唯一 Ginlong Owner Code 的联系人、HVR 后台登录用户、API User/Project、临时 Token，以及两个 Edit 基准产品。
- 初始运行标识：`HVR07-20261119`。测试产品、货主编码和临时同类别 UoM 都使用此前缀。由于现有“台”和“个”属于不同 Odoo UoM 类别，准备脚本另建一个仅供测试的同类别替代单位，用于验证产品单位字段修改；测试结束后由安全重置脚本删除。请先执行 `test_data/reset_api07_hvr.py` 再重新准备，避免旧的验收数据污染唯一键或模板属性。
- API Token 存于 `test_data/.api07_hvr.env`，权限 `0600`，已加入该目录 `.gitignore`。不要复制到 Markdown、截图或工单。

## 4. 执行顺序与场景矩阵

共 **22 个 HVR 实例**。先执行基础新增和重复，再进行共享模板/多货主、tracking、Edit、异常恢复、字段校验和认证场景。

| 顺序 | HVR | 场景 | 依赖 / 预期关系 |
| ---: | --- | --- | --- |
| 1 | HVR07-01 | 新增原材料 | 新产品；A 货主、Raw Code |
| 2 | HVR07-02 | 相同及不同 Payload 的 Add 重复提交 | 依赖 01；两种重复 Add 均返回业务失败，且不覆盖或重复创建产品 |
| 3 | HVR07-03 | B 货主新增相同 productCode | 依赖 01；复用 Template，新增独立 Variant |
| 4 | HVR07-04 | 同码跨货主 Edit 的 productForm 冲突 | 依赖 03；拒绝且不改模板/变体 |
| 5 | HVR07-05 | 半成品 tracking | 新产品；预期 serial |
| 6 | HVR07-06 | 成品 tracking | 新产品；预期 serial |
| 7 | HVR07-07 | Edit 修改名称/规格 | 已于 2026-11-20 通过；原变体/模板 ID 保持不变 |
| 8 | HVR07-08 | 同一产品第二次 Edit 修改单位/可选物料字段 | 已于 2026-11-20 通过；原变体/模板 ID 保持不变 |
| 9 | HVR07-09 | 同一 Edit Payload 重复发送 | 依赖准备脚本的 Edit 基准产品；相同内容应处理两次但不增建记录 |
| 10 | HVR07-10 | 新单位自动建档 | 新业务键；标准 Unit 类别新建无换算 UoM，随后产品 Add 成功；已于 10:30:26 人工通过 |
| 11 | HVR07-11 | 同键不同单位重复 Add | 依赖 10 成功；使用 `unit=台` 的不同 Payload，应返回 IDM07，保留首次产品单位；已人工通过 |
| 12 | HVR07-12 | 不支持的 productForm | 新业务键；应返回 `BUS06` 并说明允许值；拒绝且无模板/变体；已于 2026-11-20 人工通过，旧版本首次返回 BUS01 的记录保留 |
| 13–17 | HVR07-13–17 | 必填字段缺失、null、空/空白 | 独立无效请求；响应列出字段名且不得创建产品。HVR07-13–17 均已人工验证；日志分别为 1995、1999、2001、2003、2005。 |
| 18 | HVR07-18 | DECIMAL weight 为非法文本 | 已于 2026-11-21 验证；`TYP01: 类型错误字段: weight`，日志 2007，无产品或幂等记录。 |
| 19 | HVR07-19 | VARCHAR productName 为数字 | **PASS（项目负责人判定）**：`productName=12345` 返回成功并持久化为文本值 `12345`；产品/幂等证据保留。 |
| 20 | HVR07-20 | 数字型 productForm | 已于 2026-11-21 验证；返回 `BUS06`，日志 2011，无产品或幂等记录。 |
| 21 | HVR07-21 | 无效 Token | 纠正请求于 2026-11-21 返回 `AUTH01`，日志 2019；该请求键无产品或幂等记录。更早误用有效 Token 的记录另行保留。 |
| 22 | HVR07-22 | 有效 Token，但 API User 未配置 WMS Project | 项目负责人确认最终 `AUTH01` 响应可记 PASS。日志 2021 的具体原因是 `Invalid token`；先前误用 Project 146 Token 的成功数据仍保留，详见执行记录。 |

## 5. 已发现的 HVR 验收问题与记录

本计划最初发现并阻塞 API07 Edit 的代码问题，已由 `ginlong_apis` 版本 `18.0.2.0.26` 修复；HVR07-07/08 已完成人工验收。项目负责人随后确认未提供的 `unit` 值允许自动建档到标准 Unit 类别且不换算；版本 `18.0.2.0.27` 已升级并通过 3 项定向测试，HVR07-10/11 均已人工通过。HVR07-13–20 验证了字段校验和业务拒绝；HVR07-21/22 的判定依据及认证日志事实见执行记录。

1. **HVR07-19 的验收决定**：V3.2 将 `productName` 定义为 VARCHAR。既有类型校验器对 VARCHAR 不执行类型校验，Odoo `Char` 字段将 JSON 数值 `12345` 保存为文本 `12345`。项目负责人于 2026-11-21 明确认为该产品名称有效，并接受成功结果，因此此例按 PASS 关闭；该决定是项目验收判断，不宣称修改了 Ginlong 的 VARCHAR 字段定义。
2. **失败日志状态记录问题**：API07 字段/业务失败使用 HTTP 200 JSON 响应。现有 `worlddepot.api_logger` 对 `http.Response` 主要按 HTTP 状态码判定日志状态，可能把 `returnStatus=N` 的业务失败记录成日志 `success`。人工检查时必须核对响应体中的 `returnStatus`，不要只看列表状态；该观察作为后续日志一致性改进项，不影响本次已由 HTTP 响应和业务结果完成的 HVR 判定。

另：本次本地 HVR 实测的无效 Token 失败（日志 ID 2019）由 API Logger 记录，并返回三字段 `AUTH01`。HVR07-22 首次误用 Project 146 的有效 Token并创建了产品（日志 ID 2015）；后续失败日志 ID 2021 的诊断为 `Invalid token`。项目负责人决定 HVR07-22 按 PASS 记录，但该日志没有证明有效且无 Project 的 Token 路径已被执行；相关事实保留在执行记录中。

**关闭结论：HVR07-01–22 均为 PASS。** HVR07-19 按项目负责人对数值型 `productName` 的明确判断记录 PASS。HVR07-22 按项目负责人判定记录 PASS，同时保留实际日志显示 Token 无效、未独立证明有效且无 Project Token 路径的证据限制。执行记录保留所有早期失败、误用 Token 和复测记录，不覆盖历史。

## 6. 通过标准与记录

每个案例按 [HVR_API07_Test_Cases.md](HVR_API07_Test_Cases.md) 执行，必须保留 HTTP 响应、Odoo 后台证据及 ORM 检查摘要。执行者只在 [HVR_API07_Execution_Record.md](HVR_API07_Execution_Record.md) 填写本人、时间、PASS/FAIL/BLOCKED 和证据位置。

本轮 22 项已完成判定并关闭。上述执行标准用于说明本包的历史验收方法；后续若因代码变更重新验收，应新建执行轮次并保留本轮记录，不覆盖既有证据。
