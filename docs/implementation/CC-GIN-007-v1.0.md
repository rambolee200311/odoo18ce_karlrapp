# CC-GIN-007 v1.0 Frozen — API01 按业务类型处理入库预报 SN 数据

| 项目 | 内容 |
|---|---|
| CC ID / 版本 | CC-GIN-007 / v1.0 Frozen with Open Items |
| 状态 | **Frozen；Human Review：APPROVED；本地实施已授权。** |
| Intent ID | GINLONG-API01-BUSINESS-TYPE-SN-FORECAST-007 |
| 模块 | ginlong_apis；复用 worlddepot 现有入库 Order 记录 |
| 目标 | 按 businessType 有条件地校验和保存 API01 入库预报 snList；隔离订单预报数据与实际库存/SN/托盘对象；保持 API04 从实际入库记录取数。 |
| SRS | [SRS v1.2 Frozen with Open Items](../requirement/SRS_ginlong_apis-v1.2.md)；含已批准 API01 条件规则。 |
| TDD | [TDD v1.5 Frozen with Open Items](../ginlong_apis/TDD-v1.5.md)；历史 Review Draft 保留。 |
| Implementation Plan | [v1.9 Frozen](IMPLEMENTATION_PLAN_ginlong_apis-v1.9.md)；阶段 4B 映射 CC-GIN-007。 |
| 上下文 CC | [CC-GIN-005 v1.1 Frozen with Open Items](CC-GIN-005-v1.1.md)；不覆盖、不修改其历史范围和证据。 |
| 模板同步 | BLOCKED：项目模板源缺失；沿用已批准流程例外，不记为 PASS。 |

## 1. 批准基线与实施授权

项目负责人对 v0.1 给予有条件设计批准；本文件已落实 HVR、日志及核对范围三项修订，并完成 SRS v1.2、TDD v1.5、Implementation Plan v1.9 的基线更新。CC-GIN-007 v1.0 已冻结，授权在现有开发环境中实施 API01 变更并运行 Odoo 自动化/组件集成测试及 Mock HTTP。不得访问真实 Ginlong、生产或 KR/Gateway 环境。模板同步继续 BLOCKED，沿用已批准流程例外，不影响本 CC 冻结或实施。

## 2. 范围提案

### 2.1 纳入范围

门禁满足后，拟实施以下 API01 Add 行为：

- 以 V3.2 和获批 SRS 为准处理必填字段、类型、认证、幂等、统一错误和日志；复用现有组件。
- 按精确业务类型「保税_海外收货入库」决定是否检查和保存 snList。
- 保税类型下，依据 owner + productCode 解析现有产品变体，并依产品 tracking 验证真实 SN 或原材料托盘分配行。
- 对 details 产品、snList 产品、SN、托盘标识和数量执行整单一致性校验；校验必须在业务 Order 写入前完成。
- 仅将 Ginlong 客户预报写入现有 inbound.order 及其现有结构化订单子记录；失败不得留下部分业务单据或成功幂等结果。
- 保税类型以外的业务类型忽略 snList：不校验其容器、行内容或业务含义，不保存到 Order SN 预报字段/子记录。
- 保持现有 API01 Add 重复请求、Delete、事务、响应结构和错误码策略；仅在必要处作最小兼容调整。
- 验证实际收货记录仍由后续真实/本地 WMS Picking 流程产生；API04 继续只读取实际 Picking / Move Line 数据，本 CC 不修改 API04 实现。

### 2.2 保税业务类型规则

当 API01 Add 的 businessType 精确等于「保税_海外收货入库」：

1. 产品的 SN 管理方式按已映射 Odoo 产品的 tracking 判断。
2. tracking=serial 的产品必须有完整 snList；每行 productSN 为实际 SN，quantity 必须等于 1。同一请求内，同一产品不允许重复 productSN，即使 palletCode 不同。不同产品允许相同的 productSN 文本。
3. 非 SN 管理原材料允许省略 snList。若提供行，productSN 必须等于 productCode；quantity 表示该产品在该托盘上的预报数量，允许大于 1。同一原材料可以有多条托盘分布行。
4. 每条提供的 snList 行必须关联 details 中存在的产品，并保存其 Ginlong 预报 `palletCode`。一个产品可以分布在多个托盘；一个托盘可以包含多个产品。
5. 按产品汇总 details.quantity 与该产品实际提供的 snList.quantity；有分配行的产品必须相等。所有 SN 管理产品必须完整提供行。没有分配行的非 SN 原材料只保留产品总量，不因省略 snList 失败。
6. palletCode 是客户预报标识，仅作为 Order 预报属性保存；不生成 Odoo 托盘号，不建立物理 package。
7. 失败拒绝整单。响应保持 Ginlong V3.2 三字段结构；exceptionInfo 不超过 40 字符，超长时保留完整错误码/字段名并以 ... 收尾；完整产品、SN、托盘、数量及路径详情留在现有 API 日志。

对于 businessType 不等于上述精确值的请求，snList 即使缺失、为 null、格式错误或含错误行也不进入校验和持久化；其余报文仍按通用契约校验。不得将本规则自动推广到 API05。

### 2.3 订单预报与实际库存的边界

- inbound.order 记录 Ginlong 预报的产品、数量及适用时提供的预报 snList。已有 world.depot.inbound.order.product.serial.number 子记录和 ginlong_* 扩展字段作为结构化预报存储；ginlong_sn_list_json 是现存原始报文副本字段，不得被当作第二套独立业务事实。
- Order 子记录的 serial_number / productSN 字符串，包括原材料的 productSN=productCode，只是预报文本，不是 stock.lot，也不表示已确认的实物 SN 身份。
- Order 中的 palletCode 只是客户提供的预报托盘标识，不是 Odoo 的 stock.quant.package。不得把它写入实际 package 关系或生成虚拟托盘编号。
- API01 不创建 stock.lot、stock.quant.package、stock.move、stock.picking 或库存变化；也不提前运行 WMS 实际收货流程。当前现有 Order 产品行的 pallets=1.0 仅作为既有数量计算分组，不得解释或展示为已知的实际托盘数。
- 实际收货后，Odoo 以 stock.picking / stock.move.line 记录实际产品、数量、Lot/SN 及托盘 package。API04 继续从选中的实际 Picking、Move Line 读取数据，不能用 API01 预报数据替代。
- 本 CC 保存客户预报字段，供既有业务记录留存；如未来需要比较预报与实收，须另行批准功能。本 CC 不实现比较、差异展示/处置、库存调整、实际收货门禁或 API04 回传规则。

### 2.4 超出范围

- API03、API05、API07、API04 功能实现；特别是不得将 API01 的 businessType 分支规则套用于 API05。
- 修改 API04 Payload、回传按钮、幂等、日志、stock.picking 或 stock.move.line 行为。
- 新建 SN 主档、托盘主档、映射模型、库存台账、状态机或审核流程。
- 创建 stock.lot、stock.quant.package、stock.move、stock.picking，或写入/调整 stock.quant。
- 修改 Ginlong 响应结构、认证、限流或现有幂等策略。
- 连接真实 Ginlong、生产环境、Karl Rapp 或 Gateway；构造 KR XML。
- 改写 CC-GIN-005 及任何已关闭 CC 的历史记录。

## 3. 变更边界提案

| 范围 | 拟允许修改 |
|---|---|
| API01 业务映射 | ginlong_apis 的 API01 分支、调用它的校验接入点；仅实现 businessType 对 snList 的条件处理与整单预检 |
| 持久化 | 复用 world.depot.inbound.order、其现有产品/序列号子记录及 ginlong_sn_list_json；只有评审确认现有字段不足时，才另行提出最小扩展 |
| 错误与日志 | 复用现有 Error、API 日志和日志详情能力；不增加 API 专属错误框架 |
| 自动化 | ginlong_apis 的 HTTP/ORM 测试；必要时仅增加验证 API04 继续读取实际作业数据的回归测试，不修改 API04 生产逻辑 |
| 文档 | TDD、CC、对应 IHR/ATR/HVR；仅在实施授权后记录实际事实 |

除上述范围外，修改其他 worlddepot/WMS 行为须暂停并提出影响评估，不因本 CC 自动获批。

## 4. 必须保持的既有行为

| 行为 | 验收要求 |
|---|---|
| API01 接单不等于实际入库 | 成功 Add 后没有 Picking、Move、Lot、Package 或库存变化 |
| 货主和产品定位 | 继续按 owner + productCode 复用现有产品变体；保留现有货主创建/复用规则 |
| 幂等 | 首次 Add、重复 Add、失败重试遵守已批准规则；校验失败不得产生成功幂等结果 |
| Ginlong 响应 | 仅 returnStatus、exceptionInfo、operationTime；成功为 Y / OK |
| API04 实绩 | 从实际已保存 Picking / Move Line 生成，不读取订单预报 SN JSON/子记录 |
| API05 | 保持已批准的盘点规则，不受 API01 businessType 条件影响 |
| 安全边界 | 只使用现有开发数据库、venv、odoo.conf 和 ORM；不直接 SQL，不访问生产或真实外部接口 |

## 5. 自动化测试契约（初始均为 NOT RUN）

所有测试通过真实本地 HTTP API01 路由，使用 Odoo 测试设施和 ORM 断言。每项记录请求、HTTP 响应、Order/子记录、幂等、日志及库存对象前后状态；不得用函数结构探针代替行为验证。

| 测试 ID | 场景 | 通过条件 |
|---|---|---|
| CC-TEST-057 | 非保税业务类型，snList 缺失 | 有效其余报文成功；产品和数量预报入 Order；无 SN 预报字段/子记录 |
| CC-TEST-058 | 非保税业务类型，snList 提供但内容错误 | snList 使用错误容器或无效行；其余报文有效时请求成功；snList 不触发校验错误、不写入 JSON/子记录 |
| CC-TEST-059 | 保税类型，多个 SN 产品完整清单 | SN 管理产品每件一条、quantity=1，产品总量匹配；成功保存每条 SN 与 palletCode |
| CC-TEST-060 | 保税类型，serial 产品缺失或部分 SN | 整单拒绝；无 Order/明细/货主副作用及成功幂等记录 |
| CC-TEST-061 | 保税类型，单条 SN quantity 不为 1 | 即使汇总数量相等仍拒绝；错误指向产品、SN/数量和托盘，外部长度不超 40，日志保留完整细节 |
| CC-TEST-062 | 保税类型，同产品重复真实 SN、托盘不同 | 拒绝；按 (productCode, productSN) 判重 |
| CC-TEST-063 | 保税类型，不同产品相同真实 SN 文本 | 在各自数量完整时允许；不得跨产品误判重复 |
| CC-TEST-064 | 保税类型，原材料未提供 snList | 原材料订单按 details 产品数量成功保存；不生成托盘/SN/库存对象 |
| CC-TEST-065 | 保税类型，原材料按托盘分布 | 同一 raw productCode/productSN 可在多个 palletCode 下重复，quantity 可大于 1；所有行合计与 details 相等 |
| CC-TEST-066 | 保税类型，多产品混托盘及关联错误 | 一个 palletCode 含多种产品、同一产品分布多托盘的有效组合通过；产品不在 details、raw productSN 不等于 productCode、palletCode 缺失、数量不足/超出分别拒绝整单 |
| CC-TEST-067 | 保税类型，serial + raw 混合订单 | serial 产品清单完整；raw 可省略分配行或按托盘提供；分别按产品汇总准确判断 |
| CC-TEST-068 | 全部拒绝路径原子性及副作用 | 不产生部分 Order/产品子行/成功幂等结果/货主档案；stock.lot、stock.quant.package、stock.move、stock.picking、stock.quant 无 API01 引起的新增或变化 |
| CC-TEST-069 | API04 数据来源独立性回归 | 验证 API04 Payload 从已选实际 Picking/Move Line 获取 Lot、数量及 package；API01 预报字段不是 API04 数据来源；不开发或测试预报/实收比较、差异展示或差异处置，不修改 API04 生产行为 |
| CC-TEST-070 | 重复 Add、Delete 和非目标业务回归 | 保留 API01 已批准的重复 Add 拒绝和 Delete 行为；API03/05、认证、通用校验、错误/日志及幂等回归不被破坏 |

任何测试只有实际运行并记录 ORM/HTTP 断言后才能改为 PASS。当前所有测试均为 NOT RUN。

## 6. 人工 HVR 场景（执行状态均为 NOT RUN）

HVR 使用本地开发环境和明确标识的测试单号，不访问真实 Ginlong。每个实例保存实际请求、响应、业务单据截图/ORM 证据、API 日志及幂等结果。

| HVR ID | 操作场景 | 预期 |
|---|---|---|
| HVR-API01-01 | 非保税业务类型，无 snList | Order 产品和总量保存；不出现 SN 预报行或实际托盘/库存记录 |
| HVR-API01-02 | 非保税业务类型，附畸形 snList | 接口不处理、不校验、不保存 snList 到 Order；其他字段有效则成功。现有 API 日志仍保留原始请求（含收到的 snList）；日志留存不代表业务接受或持久化该字段 |
| HVR-API01-03 | 保税业务类型，3 个产品 / 3 个托盘；每个托盘均混有 SN 产品和原材料，同一 SN 产品跨托盘 | 按下方托盘分配表发送；details 总量 A=4、B=2、C=12；真实 SN 每行 quantity=1；原材料 productSN=productCode；各产品托盘行数量合计等于 details；Order 保存预报分配，不创建真实 stock.lot/package/picking |
| HVR-API01-04 | 保税业务类型，原材料省略 snList | 订单总量被保存；不创建虚拟 pallet_no |
| HVR-API01-05 | 保税业务类型，原材料数量 12 分布在托盘 1/2（例如 5 与 7），并与 SN 产品共用托盘 1 | productSN=productCode，行 quantity 可大于 1；按产品总量与 details 对账；共享托盘码允许有不同产品行 |
| HVR-API01-06 | 真实 SN 缺失、重复、数量错误或产品/托盘/合计不符 | 返回明确 N 错误；无部分业务数据；日志包含完整定位信息 |
| HVR-API01-07 | API04 实际数据来源 | 检查 API04 Payload 来源于已保存实际 Picking/Move Line；不比较预报数量/SN/托盘与实际数据，不评定差异，也不自行阻断实际收货 |

HVR-API01-03 的有效托盘分配如下，Payload 中每个真实 SN 独占一行：

| 托盘 | SN 产品 A | SN 产品 B | 原材料 C |
|---|---:|---:|---:|
| PALLET001 | 2 个不同 SN，各 quantity=1 | 1 个 SN，quantity=1 | quantity=5，`productSN=productCode` |
| PALLET002 | 1 个不同 SN，quantity=1 | — | quantity=4，`productSN=productCode` |
| PALLET003 | 1 个不同 SN，quantity=1 | 1 个不同 SN，quantity=1 | quantity=3，`productSN=productCode` |
| **合计** | **4 件** | **2 件** | **12 件** |

上述分配确保每个托盘均混有原材料与至少一种 SN 产品；A 分布在三个托盘，C 分布在三个托盘。

人工操作流程、实际 HVR 执行状态和证据路径由实施后续记录；本冻结契约不代填 PASS。

## 7. Open Items 与追溯

| 事项 | 状态 / 决定 | 影响 |
|---|---|---|
| SRS/TDD/Plan 上游基线 | **已关闭**：当前基线分别为 SRS v1.2、TDD v1.5、Plan v1.9 | CC-TEST 与 HVR 按本 CC 执行 |
| API 日志中的原始请求 | **已关闭**：非保税 snList 不进入 API01 业务校验或 Order 保存；既有日志仍保留收到的原始请求 | 不修改共享日志机制；HVR-API01-02 可按此验收 |
| Order 预报存储 | **已决定**：复用现有结构化 SN 子记录保存业务预报；JSON 字段如保留，仅为请求快照，不作为第二业务事实来源 | 不新增模型 |
| `pallets=1.0` 旧数量乘数 | **已明确**：不得当作 Ginlong 托盘数；托盘分布以订单预报 SN 子记录的 `palletCode` 行为准 | 不要求改造 WMS 计算字段或创建实体托盘 |
| 预报与实收差异比较及处置 | **移出本 CC**：未来如有需要，通过新需求/CC 提出 | 不阻塞 CC-TEST-069；本 CC 不开发比较、展示、拦截或处置 |
| 模板同步 | **BLOCKED**：沿用批准的流程例外，不伪记为 PASS | 不阻塞本 CC 冻结或实施 |

## 8. 追溯矩阵

| 业务/设计规则 | TDD 冻结设计 | CC 落点 |
|---|---|---|
| 保税业务 SN 管理规则 | TDD v1.5 §4 API01 businessType 分支 | CC-TEST-059–063、067；HVR-API01-03/06 |
| 保税业务原材料分配与混托盘 | TDD v1.5 §4 原材料分配规则 | CC-TEST-064–067；HVR-API01-04/05 |
| 非保税业务忽略 snList | TDD v1.5 §4 非保税分支 | CC-TEST-057/058；HVR-API01-01/02 |
| Order 预报不建库存对象 | TDD v1.5 §4 模型边界 | CC-TEST-064/068；HVR-API01-01–05 |
| API04 使用实际作业结果 | TDD v1.5 §4 实际收货及 API04 | CC-TEST-069；HVR-API01-07（仅来源独立性，不做差异比较） |
| 错误、事务、幂等、日志保持 | TDD v1.5 §5/§6 与既有冻结组件 | CC-TEST-060–062/066/068/070 |

## 9. Done Gate

本 CC 只有在实施授权后全部满足以下条件才可申请关闭：

- SRS、TDD 与 Implementation Plan 均已批准、冻结/基线化，且 CC 引用准确版本。
- 所有适用自动化测试通过；失败、未运行和阻塞证据如实记录。
- API01 正常/异常业务数据及重试行为通过真实 HTTP/ORM 验证。
- 确认 API01 不创建实际托盘、Lot、Picking、Move 或库存；API04 仍读取真实作业数据。
- HVR 由业务负责人实际执行并记录，Codex 不代填人工 PASS。
- IHR、ATR、HVR、变更记录及追溯矩阵更新完整。
- API01 预报/实收差异比较与处置不属于本 CC Done Gate；若后续提出，另行需求变更。

## 10. 冻结基线状态

| 项目 | 状态 |
|---|---|
| 文档 | CC-GIN-007 v1.0 Frozen with Open Items；Human Review APPROVED |
| TDD | v1.5 Frozen with Open Items；Human Review APPROVED |
| 上游基线 | SRS v1.2 / TDD v1.5 / Implementation Plan v1.9 均已更新 |
| 代码变更 | AUTHORIZED；本文件不声称实施已开始或完成 |
| 自动化测试 | NOT RUN |
| 人工 HVR | NOT RUN |
| 实施边界 | 本地 Odoo 开发、自动化/组件集成测试、Mock HTTP；无真实 Ginlong/生产/KR/Gateway 访问 |
| Git | 未提交；本轮不操作 Git |

## 11. Human Review 与冻结批准

| 项目 | 记录 |
|---|---|
| Human Review | APPROVED；项目负责人李建强；2026-11-23；有条件评审的三项修订均已完成 |
| 冻结决定 | CC-GIN-007 v1.0 Frozen with Open Items；保留 v0.1 Draft 历史文件 |
| 实施授权 | API01 本地修改及自动化/组件集成验证已授权；API04 仅验证来源边界，不修改实现 |
| Open Items 影响 | 预报/实收比较移出范围；模板同步按已批准例外保持 BLOCKED，不阻塞本 CC |
| 外部环境 | 不访问真实 Ginlong、生产或 KR/Gateway 环境 |
