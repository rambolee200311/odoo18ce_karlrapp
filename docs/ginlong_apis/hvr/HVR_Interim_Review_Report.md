# Ginlong API 项目 HVR 中期评估报告

**版本：** v0.2 Review Draft
**报告日期：** 2026-11-27
**状态：** Human Review Pending
**范围：** CC-GIN-001–012、现行 SRS/TDD/Implementation Plan、ATR/IHR、API HVR 及项目级模拟 HVR 记录
**本轮边界：** 仅撰写本报告；未修改业务代码，未重新执行测试，未访问真实 Ginlong 或生产环境。

**本版修订：** 分开累计跨版本链、已启动但未完成的 RUN03、最终版完整 HVR 和真实人工 HVR；补充 API01–10 横向审查、可关闭的纠正清单及 HVR Readiness Gate。未启动新的 HVR。

## 1. 结论摘要

项目此前没有完整业务主链，不是单一代码缺陷，也不能概括成“测试不充分”。问题是多个环节连续叠加：Agent 没有始终把已确认的仓库业务边界当作硬约束；由此产生错误的数据来源、额外作业步骤和不合理验收断言；局部自动化及宽松 Mock 又接受了这些假设；最后到浏览器 HVR 才暴露它们与真实订单、Picking、库存及调用数据不符。之后修复虽持续推进，但运行服务版本、HVR 数据和执行指南没有始终同步，进一步增加了复验和判断成本。

截至 2026-11-27，R8239A3 已形成 API01–API10 的累计业务主链证据，且 API08 单项已获负责人批准。该累计结果由跨模块版本记录组成：API01–07/API09/API10 的主链请求来自 ginlong_apis 18.0.2.0.54，API08 最终请求来自 .55。因此累计业务链证据可判 PASS，但不能据此宣称“同一最终版本的完整 HVR 已通过”。随后启动的 HVR005-20261127-RUN03 在 .55 环境下已有连续执行证据，已到 API05 指令；实际盘点结果和 API10 尚未完成，且运行记录尚未与实际证据同步，因此它只能列为未完成运行，不能列为完整 HVR PASS。本轮报告修订不继续该运行，也不启动新运行。负责人真实人工 HVR 为 NOT RUN，CC-TEST-055 普通库存操作员权限仍为 PARTIAL。较早主链报告记录 API08 BLOCKED，必须保留为历史并与后续单项通过证据并列，不得把跨版本补测拼成最终版完整 HVR。

R8239A3 的业务连续性为：同一 Owner、项目、KRWH、产品变体和三个托盘贯穿 API07、API09、API01、API02、入库 Picking、API04、API03、出库 Picking、API06、API08、API09、API05、实盘及 API10。实际入库后 FG/SF/RAW 为 3/3/12；一次实际出库 Picking 完成整托及拆托作业后为 2/2/9；回传按钮没有产生额外库存移动。API05/API10 使用出库后的剩余库存及实盘记录。API08 按 V3.2 三字段发送，用户已批准通过。

## 2. 证据口径

本报告依据冻结契约、CC/ATR/IHR、HTTP 请求响应、Mock 捕获、截图及 ORM 证据。历史 FAIL/BLOCKED 不删除；后续修复只更新当前判定，不抹去发现问题的记录。真实 Ginlong、生产、KR Gateway/XML 与本地 Mock/模拟 HVR 分开判断。

大量自动化结果证明了组件、事务或模型协作，不自动证明普通业务用户能从订单页面按真实业务顺序完成全流程。CC-GIN-012 自动化主链和 CC-GIN-005 浏览器/人工 HVR 是不同验收层次；前者关闭不能推导后者关闭。

## 3. 主要阻塞时间线

| 时间/阶段 | 事实及分类 | 直接原因、根因 | 应发现阶段与漏检原因 |
|---|---|---|---|
| 11 月 17–18 日，CC-001–004 | 建立 API 日志安全、接口映射、幂等/限流、API09 与管理界面基线。用户多次重申：Ginlong 下达指令，KR 做现场作业，Odoo 管业务记录并依据实际结果更新库存；盘点实盘独立于库存账。属于**需求理解及设计治理问题**。 | 设计曾从技术机制出发，再由用户纠正模型边界。未始终先检查现有 WMS 业务流程和数据来源。 | 应在 SRS/TDD 设计时先确定业务事件和权威数据源。项目认知虽有记录，却没有成为每个任务的实施前置检查；CC 单项关闭容易被误解成系统级业务链已验收。 |
| 11 月 19–21 日，API07 HVR | 同一 owner + productCode 重复 Add 曾返回成功，产品并未重复创建；错误原因起初被压成通用 BUS01。属于**真实幂等和错误反馈缺陷**。 | 成功结果重放先于当前业务键冲突检查，遮蔽了 API07 的重复新增拒绝；Error 组件不能传递足够具体的业务原因。 | 应由首次/重复 HTTP Add 与 ORM 不变性测试发现。自动化曾验证幂等结果可重放，没有充分断言“再次 Add 必须 IDM07 且产品不变”；人工 HVR 首次揭示差异。 |
| 11 月 21–24 日，API01 SN 与 payload | R1 报文中单条 SN 数量大于 1 曾得到成功；其后逐步确认：单件 SN 每条数量为 1，原材料托盘行用 productCode 表示实际数量，同产品可跨托盘，汇总须等于 details。API01 HVR v2 曾有 32 个 HTTP 实例、另有检查与准备报文；执行者仍无法判断哪些是当前必测。目录还出现重复扩展名和路径错误。属于**规则演进、测试数据错误、HVR 包设计缺陷**。 | SN 身份、预报数据与库存实绩的含义没有在 HVR 前稳定；代码版本和 8099 进程也曾不一致。 | 应在 V3.2 映射、API01/05 业务规则确认、定向 HTTP/ORM 测试、HVR 包预检和启动前版本核验阶段发现。静态 JSON 合法不代表业务语义正确；模块数据库版本也不能证明旧进程已重载新代码。ATR-RUN-033–035 记录包预检和旧进程响应旧代码的证据。 |
| 11 月 22–24 日，API01/03/05 生命周期 | Add/Delete/Add、重复 Del 和 cancel 历史的处理没有始终按当前有效业务记录判断。用户要求有效单据才允许冲突/删除；取消后可重新 Add；保留历史。属于**真实生命周期语义缺陷**。 | 把历史幂等成功记录误作业务对象永久状态，混淆技术去重与当前业务许可。 | 应在 CC-008 的 Add→Del→Add→Del HTTP 生命周期和并发业务键测试发现。早期组件测试并未覆盖完整生命周期；CC-008 后补齐且保留首轮失败。 |
| 11 月 23–24 日，API01/API05 预报与实盘 | API01 的 SN/托盘预报曾被误当作实际 SN、托盘或库存对象；保税/非保税 snList 适用条件也经历确认。用户最终明确 API01 只保存客户预报，不创建实际托盘/Lot/Picking/库存；API05 指令与实盘结果分离。属于**数据来源边界误解**。 | 未把客户预报、库存对象、实盘结果区分开。 | 应在 TDD 字段来源表和“订单接收无库存副作用”测试阶段发现。只检查模型字段或接口响应，无法证明没有错误写入库存对象。 |
| 11 月 24–25 日，API02/API04 | API02 曾依赖逐行收货明细/move line；API04 曾要求手动选择 Picking/补录实际数据。Human Review 后明确 API02 读 inbound.order.status；API04 自动扫描当前订单 Done/Incoming Picking，并按 Picking 为本地回传事件。属于**设计与业务事实来源不符**。 | 为生成 Payload 要求用户重复维护业务事实，而不是由业务模块记录、API 读取。 | 应在审阅 WMS 收货状态操作、Picking 关联及禾麦实现时发现。模型/视图已可用导致“技术上存在”被误认为“业务上需要”。CC-009 后完成了数据来源修正。 |
| 11 月 24–25 日，API03 HVR | 首轮 API03 请求使用不同项目的 API User 和 HVR-GIN005 收货方，BUS01 失败且未创建订单；该请求不能证明重复 Add 或正常 Add。属于**测试数据前置条件错误**。 | API03 与 API01 没有复用同一 Project/Owner/客户/产品上下文，导致业务检查先于预期断言失败。 | 应在发请求前检查 API User project、owner、warehouse、customer 和 owner+productCode。API03 执行记录保留了日志 7560/7562/7565/7567 的跨项目根因；最初 HVR 指南没有强制预检。 |
| 11 月 25–26 日，重复回传与出库路线 | 用户发现 API02/04/06/08 成功后不能静默复用旧成功；需提示用户后由其决定是否真实重发。另一次 HVR 把现有 Internal Transfers 路径作为主线，导致 Delivery Orders 受阻。属于**回传交互缺陷及未经批准的仓库流程假设**。 | 技术去重代替用户业务决策；Agent 用 Odoo 通用流程推导现场步骤，没有先取得项目批准。 | 应在 CC-010 交互评审及主链预案阶段发现。自动化已覆盖重复发送次数，但没有阻止错误的业务流程假设。负责人多次明确“一步入库、一步出库；一张订单一次实际 Picking”。 |
| 11 月 26 日，拆托断言 | 拆托后产品离开原托盘、余件仍留在原托盘，作业行保留来源托盘；Agent 曾将其判为托盘生命周期断链。属于**验收断言错误**。 | 把整托绑定预期套在拆托上，没有区分来源追溯与当前托盘绑定。 | 应在 HVR 预期评审和实际作业后进行业务语义复核。Agent 没有反过来检查断言是否符合仓库常识，直到负责人指出正常拆托行为。 |
| 11 月 26–27 日，回传字段与 API08 | API04 非 SN 产品曾生成 productSN=false，Mock 仍返回 Y/OK；后来按确认规则改为 productCode + 实际数量。API08 曾依赖空的额外发货明细，而不是订单状态与已完成出库记录。属于**真实映射缺陷、Mock 假阳性和数据源设计错误**。 | Mock 未验证 V3.2 请求，只表示端点可达；API08 读取了额外业务数据。 | 应在 Payload schema Mock、按钮+业务数据来源测试和完整主链阶段发现。先前“HTTP 200/Mock Y”被过度当成接口通过。 |
| 11 月 27 日，R8239A3 与 RUN03 | R8239A3 形成 API01–API10 累计节点证据；API08 单项依负责人决定，以 Done/Outgoing Picking 为前置、订单状态为业务动作，并向本地 Mock 发送 V3.2 三字段报文，获批准 PASS。随后 RUN03 在 .55 启动，证据已覆盖至 API05 指令。 | R8239A3 横跨 .54/.55；RUN03 的 HVR 执行记录仍保留初始 NOT RUN 占位，实际 HTTP/Mock/页面证据散落在独立文件；RUN03 的实盘及 API10 尚未完成。 | R8239A3 只能判累计跨版本证据 PASS；RUN03 判未完成，不构成最终完整 HVR。当前先整理证据并完成基线/测试整改，Readiness 全通过后才可批准新的最终版 Run。 |

## 4. 问题类型与根因

### 4.1 真实代码缺陷

- API07 重复 Add 被历史成功结果重放遮蔽，第二次错误地返回 OK。
- API01/03/05 生命周期判断未始终以当前有效业务记录为准；重复 Del/cancel 历史语义后由 CC-008 补齐。
- 错误消息曾被归一为泛化 BUS01；必填字段汇总、协议长度、日志明细和错误响应裁剪之后经过通用 Error/Validator 修复。
- API04 无 Lot 的非 SN 行曾输出 false；经业务规则确认后改为 productCode 与实际数量。
- API08 旧逻辑要求用户维护额外发货明细，和最后确认的数据来源不符；最新按钮路径已以订单状态和 Done/Outgoing Picking 为依据。
- 8099 曾运行源代码更新前启动的进程。这属于运行部署/验收控制缺陷，不是业务 Handler 缺陷，但直接污染行为判定。

### 4.2 需求理解和未经授权假设

- 把 Ginlong 的指令当成仓库完成或库存已变。
- 把备货、实际出库混成两个或更多 Picking；把回传动作设计成另一笔库存操作。
- 假定用户要为 API 重复录入已有业务数据。
- 未获批准时引入 Internal Transfers、额外状态/明细或库存/盘点结构。
- 把 API08 误写成需回传托盘数据；V3.2 的 API08 只有 outboundOrderNo、action、shipmentConfirmed。
- 把拆托产品离开托盘本身认作业务缺陷。
- 对规则未知的情况，Agent 有时先猜一种通用 Odoo 做法，再让负责人纠正；这不应归咎为需求本身不清。

### 4.3 测试数据和验收断言

- API01 payload 的 businessType、SN数量、产品 tracking、托盘分布等多轮不匹配已确认规则；错误目录过多也导致执行者无法知道唯一必测顺序。
- API03 HVR 的 Project、Owner、customer 与 API01 数据不匹配；错误先触发业务映射而不是预期测试结果。
- 自动化夹具出现 name 替代 productName、API05 单 SN quantity=2、同模板共享属性不一致、payload 重复 .json、浮点序列化尾差。
- 产品 ID 1619 缺 Owner 属性行：调查追溯至 HVR 准备脚本 _seed_ownerless_product() 的夹具，不是生产代码缺陷；不应通过改断言掩盖，后经用户授权清理。
- API04 Mock 对 productSN=false 仍返 Y/OK，造成假阳性。
- 拆托出库的托盘验收把来源记录等同于出库后绑定，属于错误预期，不是库存或代码故障。

### 4.4 环境与操作问题

- 127.0.0.1 对发起请求的机器而言是其自身；Postman 所在设备与 Odoo 所在主机不同会导致拒绝/超时。这是网络上下文问题，不是接口业务逻辑。
- 本地 8099 服务未总是随源码/模块升级重启，出现旧代码处理新测试的情况。
- 模拟 HVR 期间遇到 Odoo 会话过期、Mock 18102 无监听、Token/用户上下文混用及权限不足；有些是环境问题，有些是测试用户配置问题。
- 普通业务用户被自定义 Order ACL 拒绝。后续用临时管理员/高权限测试账户完成 UI 操作，只证明页面路径可用，不证明普通库存操作员权限。
- 业务执行者多次询问 payload 目录和顺序，反映交付操作指南没有达到可直接执行标准，不能把它归类为用户操作失误。

## 5. 工程产物有效性评估

| 产物 | 有效部分 | 失效点 |
|---|---|---|
| SRS | 明确系统职责、接口边界、货主+产品编码、盘点结果与库存台账分离等核心原则。 | SRS v1.9 尚未明确写入“一步入库/一步出库”不变量；FR-GIN-008 仍描述 API08 从发货明细生成。代码与后续批准决定不同，需在新 HVR 前受控修订。 |
| TDD | v2.2 记录了状态来源、幂等生命周期、Payload 校验、回传确认和并发机制。 | TDD v2.2 API08 仍要求发货明细来源，API06 仍保留选择/明细描述；当前代码及负责人最新决定采用 Done Outgoing Picking 的实际数据，API08 只读订单状态并发送三字段。必须受控对齐。 |
| TV | 产品变体技术验证为 template/variant、owner 隔离和 tracking 提供了真实可行性证据。 | 模型探针不等于仓库业务流程验证；未将产品、Picking、库存、托盘、盘点的全链意义纳入每次技术结论。 |
| Implementation Plan | 把功能按 CC 分阶段，明确 CC-012 主链自动化、CC-005 浏览器/人工验收、CC-006 真实联调边界。 | 完整 UI/WMS 业务链拖到后期才执行，核心跨模块风险发现过晚；早期没有“先过一条最小垂直切片”门槛。 |
| CC | CC-007–012 分别解决 SN、有效生命周期、API02/04 来源、重复回传确认、入站通用规范和主链自动化，留下了有效修复与证据。 | CC 单项关闭被高估为项目完成；测试追溯偏组件，跨 CC 的唯一主链状态没有及时形成权威证据入口。 |
| 自动化 | 后期真实 HTTP/ORM、事务、库存不变量、Mock 捕获测试有效；CC-012 揭示了 Chatter、盘点数据来源、SN 作业等真实缺陷。 | 测试总数不能代表业务链有效。宽松 Mock、错误 fixture、管理员账号及未经过 UI 的自动化不能替代用户操作验证。 |
| 模拟 HVR | 浏览器按钮、订单状态、API Event/Log、真实 HTTP 到本地 Mock 和库存不变量有累计证据；API08 单项通过是有效结论，但累计跨版本主链不是最终版完整 HVR。 | HVR 过晚、运行数据反复变化、payload 多而无唯一入口、旧报告状态未及时更新；曾把单接口/独立订单证据拼作主链或按错误断言判 FAIL。 |

## 6. Agent 与项目负责人介入分析

Agent 的主要失败不是缺少 Python/Odoo 知识，而是没有把业务语义落实为行为约束：

1. 用户多次解释 KR 负责实物作业、Odoo 只记录结果，Agent 仍提出 Odoo 现场操作或平行模型。
2. 用户明确简化的业务流程，Agent 又以通用 Odoo route/picking 经验推导出未批准的多步出库路径。
3. 实际出库、拆托和库存结果正确时，Agent 没先验证断言是否符合业务常识。
4. 把服务可达、Mock 成功、单元/组件测试绿色或数据库模块版本误当运行行为正确。
5. 决策已存在时仍让负责人再次说明；运行后的文件、payload 与状态报告没有形成唯一真源。

因此负责人反复介入，是为了纠正 Agent 的业务假设、测试预期和执行数据，而不只是提供需求细节。少数接口枚举、错误消息和真实 Ginlong响应语义确需客户确认，但“一步/两步、指令/实绩、订单/库存、拆托常识”等用户已明确的内容不应反复询问，也不应由 Agent 自行改变。


## 7. 现有主链证据与验收状态

本节把“跨版本累计证据”“已启动但未完成的 RUN03”和“最终版完整 HVR”分开判定。不得用前两者拼接出第三种结论。

### 7.1 R8239A3：累计跨版本主链证据

R8239A3 在同一组 Owner、Project、KRWH、产品变体和三个托盘上记录了 API01–API10 的连续业务节点。该证据证明业务资料可以在 API 间连续衔接；它跨越 ginlong_apis `.54` 与 `.55`，不等于同一最终版本完整 HVR。

| 节点 | 已记录证据 | 结论边界 |
|---|---|---|
| API07 / 期初 API09 | API07 Logs 9492–9494 建立产品；API09 Log 9495 查询目标 SKU 期初库存。 | 本地 HTTP/ORM 节点证据。 |
| API01 / API02 | API01 Log 9496 建立入库预报；API02 Logs 9497/9498 分别回传 N/Y。 | 订单与状态回传无库存副作用。 |
| 入库 Picking / API04 | Incoming Picking 1937 Done；API04 Log 9533 成功；入库后 FG/SF/RAW=3/3/12。 | 实际 Picking 才增加库存；API04 读取实绩。 |
| API03 / 出库 Picking / API06 | API03 Log 9503；唯一 Done/Outgoing Picking 1938；API06 Log 9535；出库后为 2/2/9。 | 一张实际出库 Picking；API06 本身不另行移动库存。 |
| API08 | API08 Log 9546、Event 8015；Mock 收到 V3.2 三字段 POST。 | API08 单项已获项目负责人批准 PASS；不代表全链同版本 PASS。 |
| API09 / API05 / 实盘 / API10 | API09 Log 9509 返回 2/2/9；API05 Log 9511 建立同链指令；API10 Log 9534 使用实盘结果。 | 盘点指令、实盘和库存台账保持独立。 |

### 7.2 HVR005-20261127-RUN03：当前未完成运行

RUN03 的请求文件及响应证据位于 [RUN03 目录](project_flow/hvr_run_20261127_run03/)，按钮回传捕获追加在 [本地 Mock JSONL](project_flow/test_data/outbound_received.jsonl)。这些证据显示该运行在本轮报告修订前已实际启动；本轮只整理报告，不继续浏览器操作、不补录实盘、不执行 API10。

| 已执行节点 | 当前可见证据 | 判定 |
|---|---|---|
| API07、API09 期初、API01、API02 | API07 三份响应、API09 初始查询、API01 响应文件；API02 Mock 捕获行 9–10 分别为 planning/N 与收货确认/Y。 | 当前 RUN 已有成功响应证据。 |
| 入库作业、API04、API09 入库后 | 浏览器完成一张 Incoming Picking；运行时记录 API04 成功，Odoo API Log 10537；API09 返回 FG/SF/RAW=3/3/12。 | 有执行证据；API04 请求体/页面证据仍需归档到 RUN 记录。 |
| API03、出库作业、API06 | API03 响应文件；一张 Outgoing Picking 完成整托 P3 与拆托 FG SN001；API06 Mock 捕获行 20、Log 10541 成功。第一次按钮尝试因必填 `operationTime` 缺失在 HTTP 发送前被校验阻止；随后在现有持久化 Form 保存操作人/时间并重试。成功 Payload 的时间为 `06:55:00`，Picking `date_done` 为 `06:57:02 UTC`，两者是不同字段，不能描述成同一时间来源。 | API06 成功回传已发生；前置校验拦截与修正重试必须保留。 |
| API08、API09 出库后、API05 | API08 Mock 捕获行 21、Log 10542 成功；API09 HTTP 200 返回 FG/SF/RAW=2/2/9；API05 响应文件及 Log 10544 成功。 | 出库后物理数量与计划盘点数量相符；API08 仅三字段且不产生第二次库存移动。 |
| 实际盘点、API10 | RUN03 记录及证据目录尚无已保存的实际盘点结果与 API10 成功捕获。 | **NOT RUN**。不得因 API05 计划数量与库存相等而推定已完成实盘。 |

RUN03 的 [执行记录](project_flow/hvr_run_20261127_run03/HVR_Run_Record.md) 仍写着 API07–API05 全部 NOT RUN，与上述逐项证据不一致。该冲突是证据归档缺陷：既不能忽略实际请求/Mock 证据，也不能直接把过时表格改写为全链通过。正式收尾前必须保留原记录历史，并建立带修订时间的证据对照，准确标出已执行、未执行和证据位置。RUN03 已有业务数据不得当作之后新 Run 的“全新数据”。

### 7.3 分层验收结论

| 验收层 | 当前状态 | 依据与限制 |
|---|---|---|
| R8239A3 累计业务链 | **PASS（跨版本累计证据）** | 十个 API 节点和业务连续性有记录；不代表同一构建完整验收。 |
| CC-GIN-012 自动化/组件集成 | **PASS（历史 RUN）** | CC-TEST-140–157 在记录的 `.49` 基线通过，见 ATR-GIN-012；不替代浏览器 HVR。 |
| RUN03 本地模拟 | **PARTIAL / IN PROGRESS** | `.55` 环境下证据到 API05 指令；实盘和 API10未完成；执行记录未同步；不得结案。 |
| 同一最终版本、纠正后完整模拟 HVR | **NOT RUN** | 尚未完成本报告纠正计划和 Readiness Review；不能拿 RUN03 或 R8239A3 补齐。 |
| 项目负责人真实人工 HVR | **NOT RUN** | 只能由负责人独立执行并签署。 |
| CC-TEST-055 普通库存操作员权限 | **PARTIAL** | 现有模拟使用本地 HVR 测试用户；并未证明目标普通库存操作员权限。 |
| 真实 Ginlong、生产、KR Gateway/XML | **DEFERRED / NOT RUN** | 需按后续授权阶段开展；本地 Mock 不等于外部联调。 |
| 模板同步 | **BLOCKED（既有批准例外）** | 保留原例外，不伪记 PASS。 |

## 8. API01–API10 横向审查

本矩阵逐项对照已批准业务决定、V3.2 字段、现行代码/测试记录和 HVR 证据。本轮没有重新执行测试。历史自动化 PASS、单 API HVR PASS 与当前 RUN 状态分列，不互相替代。

| API | 业务规则及权威数据来源 | 触发点 / UI | V3.2 报文关键点 | 库存预期 | 测试及当前证据 / 差异 |
|---|---|---|---|---|---|
| 01 入库单 | Ginlong 请求保存为 `inbound.order` 客户预报；owner 由 `ginlong_owner_code` 复用或按批准规则创建；产品按 `(owner, productCode)` 识别。保税业务才解析/保存预报 `snList`。 | 入站 HTTP `POST /api/ginlong/TPL_Pending_Receipt_Note`；不是用户在 Odoo 建单。 | `Add/Del`；订单业务键 `inboundOrderNo`。订单修改采用 Del 后 Add；Del 仅取消有效订单。 | API01 不创建 Picking、Lot、Package、Move 或库存。 | CC-005 CC-TEST-045、CC-012 CC-TEST-143；RUN03 API01 响应文件成功。主链的 API01 新鲜数据已创建，单据还需后续 UI 收货。 |
| 02 收货确认 | `inbound.order.status` 是来源：`planning→N`，`arrive/inbound→Y`；收货确认改变业务 status、记录业务操作日志，不改变生命周期 `state`。 | 入库单业务操作“收货确认”；然后在订单 Ginlong 页面点击 API02 回传。 | `POST` / `application/json`；`inboundOrderNo`、`action=UPDATE`、`receiptConfirmed`。 | 两次状态回传均不移动库存；只有唯一 Incoming Picking 完成后增加库存。 | CC-005 CC-TEST-049、CC-012 CC-TEST-144；RUN03 API02 Mock 捕获行 9–10 是 N/Y，收货操作未增库存。 |
| 03 出库单 | Ginlong 请求保存为 `outbound.order`；货主必须存在，所有明细须匹配已有 `(owner, productCode)` 变体；不自动创建货主/产品。 | 入站 HTTP `POST /api/ginlong/TPL_Pending_Delivery_Note`；不是用户在 Odoo 手工建出库 Order。 | `Add/Del/Edit`；业务键 `outboundOrderNo`；明细含 V3.2 要求的产品和包装字段。 | API03 不创建 Picking、不预留、不改库存。 | CC-005 CC-TEST-046、CC-012 CC-TEST-148；RUN03 API03 HTTP 响应成功，来源产品与 API07/API01 同一主链。 |
| 04 入库完成 | 只读取当前 inbound Order 关联的 Done/Incoming `stock.picking` 和完成的 `stock.move.line`；SN/非 SN、数量、托盘来自实际入库；操作人/时间依批准来源读取。 | 入库 Order 上按钮自动扫描符合条件的 Picking；不手选 Picking、不重复录入。一步入库每张订单只完成一张实际 Picking。 | `POST`；`owner`、`action=CREATE`、`inboundOrderNo`、`snList`；非 SN 行以 `productSN=productCode` 且数量取实际值。 | Picking Validate 改库存；API04 回传不再移动库存。 | CC-005 CC-TEST-049、CC-012 CC-TEST-146；RUN03 记录 Log 10537 成功，API09 入库后为 3/3/12；请求/页面证据尚未完整归档。真实 Ginlong 对逐 Picking CREATE 的接收语义仍留外部联调。 |
| 05 盘点单 | API05 创建 `world.depot.stocktake.order` 客户盘点指令；计划与 `world.depot.stocktake.result` 实盘结果分离。 | 入站 HTTP `POST /api/ginlong/TPL_Stocktake_Order`；之后由仓库用户在盘点业务 Form 建实盘结果。 | `Add/Del/Edit`；业务键 `countOrderNo`；SN/数量字段按适用规则校验。 | API05 不产生实盘行、不读取/写入库存台账、不做调整。 | CC-005 CC-TEST-051、CC-012 CC-TEST-154/155；RUN03 API05 响应成功，计划为 FG/SF/RAW=2/2/9；UI 实盘尚未执行，不能视作 API10 已验收。 |
| 06 备货完成 | 一步出库下，以当前 outbound Order 的唯一 Done/Outgoing Picking 及实际 move lines 为作业来源；数量、SN、托盘为实绩。`operator`/`operationTime` 使用持久化作业字段，不以回传点击人/点击时间冒充。 | 出库 Order 的 Ginlong 回传按钮；不建立第二张“备货 Picking”，不要求另一个库存移动。 | `POST`；`owner`、`action=CREATE`、`outboundOrderNo`、`palletQty`、`totalWeight`、`snList`。非 SN 产品以 `productCode` 作 `productSN`、数量取实际数量。 | 唯一 Outgoing Picking 改变库存；API06 回传本身不再扣减库存。 | CC-005 CC-TEST-050、CC-012 CC-TEST-149/150；RUN03 第一次尝试在 HTTP 前因缺 `operationTime` 被字段校验拦截，补入持久化字段后 Mock 行20/Log10541 成功；须保留首次拦截，Payload 的 `06:55:00` 不等于 Picking `date_done=06:57:02 UTC`。 |
| 07 物料档案 | 一个 `productCode` 对应共享 `product.template`，每个 Owner 有独立 `product.product`；身份键 `(owner, productCode)`。`productForm` 决定模板 tracking：原材料 none，半成品/成品 serial；其他值拒绝。 | 入站 HTTP `POST /api/ginlong/TPL_Product_Master`；Odoo 产品 Form 只用于核查结果。 | `Add/Edit`；V3.2 不支持 Delete。有效变体重复 Add 拒绝；共享模板属性冲突拒绝。 | 更新主数据，不产生库存。 | CC-005 CC-TEST-047/048、CC-012 CC-TEST-140/141；RUN03 三个 API07 HTTP Add 成功，产品供同一主链 API01/API03 使用。 |
| 08 发货完成 | 当前批准决定：以 outbound Order 的业务发货状态生成 `shipmentConfirmed`；发送前须有当前订单 Done/Outgoing Picking。业务状态按钮记录操作日志，不建第二个 Picking。 | 出库 Order 上“确认离仓并回传”；这是订单状态操作及 API 回传，不是库存操作。 | V3.2 固定三字段：`outboundOrderNo`、`action=CREATE`、`shipmentConfirmed`；不得加托盘字段。 | 唯一 Outgoing Picking 已完成库存变化；API08 仅改状态/回传，不产生库存移动。 | CC-005 CC-TEST-050、CC-012 历史 CC-TEST-152；负责人已单独批准 API08 PASS。RUN03 Mock 行21、Log10542 成功；其成功不覆盖全链未完成状态。活动旧文档及旧测试仍需按 COR-01/03 受控对齐。 |
| 09 库存查询 | 读取 Odoo 当前物理库存数量 `stock.quant.quantity`；按 owner 及 warehouse 隔离，Owner 编码对应 `ginlong_owner_code`/库存 Owner；只回传原始 `productCode`。本地主链仅涉及 `KRWH`，不推导多仓规则。 | 入站 HTTP `POST /api/ginlong/TPL_Stock_Query`。 | 请求 `owner`,`warehouse`；响应头和完整 `inventoryList` 的 `productCode`,`quantity`；不分页、不增加可用量/预留量字段。 | 严格只读；quantity 不扣 reserved。 | CC-005 CC-TEST-052、CC-012 CC-TEST-142/147/153；RUN03 初始为空、入库后 3/3/12、出库后 2/2/9 均有真实 HTTP 响应文件；出库查询首次被执行环境网络权限挡住，随后获准重试并收到 HTTP 200，不能将第一次本机错误记为 Odoo 接口失败。 |
| 10 盘点完成 | 从与 API05 指令关联的、已保存的 `world.depot.stocktake.result` 读取；不得以计划数或 `stock.quant` 推算实盘结果。 | 盘点 Order/结果 Form 保存真实盘点记录后，在 Ginlong 页面点击回传。 | `POST`；`owner`、`action=Add/Del`、`countOrderNo`、`snList`；按 V3.2 原字段组织。 | 实盘保存与 API10 回传均不改变库存，不做调整。 | CC-005 CC-TEST-051、CC-012 CC-TEST-155/156；R8239A3 有历史实盘/Log9534，RUN03 只有 API05 计划，实盘与 API10 NOT RUN。 |

### 8.1 横向审查的活动差异

1. **SRS/TDD/CC 基线冲突仍在。** SRS v1.9 的 FR-GIN-008、TDD v2.2 的 API08 章节及 CC-GIN-005 v1.1/CC-TEST-050 保留从发货明细或 move line 生成 API08 的旧表述；当前负责人决定是订单状态形成三字段回传，并以 Done/Outgoing Picking 作前置。CC-005 冻结文本还把 API06 描述成独立备货数据/选择路径，且一步入库/出库未在全部基线形成强约束。不能直接改写冻结文件，需受控增量版本。
2. **API06 的持久化实际作业字段须与界面预期清楚对应。** RUN03 的首个点击被缺失的 move-line `operationTime` 预校验拦截，之后用户在现有 Form 补存再发送成功。后续操作包和自动化断言必须明确哪些值从 Picking/Move Line 读取、哪些是允许保存的补充值，并保留真实取值，不把补充时间说成 `date_done`。
3. **测试 ID 按所属 CC 追踪。** CC-GIN-005 冻结用例是 CC-TEST-044–055；CC-GIN-012 的 CC-TEST-140–157 是独立自动化主链。API 行映射见上表，不能把 140–157 的自动化 PASS 贴成浏览器 HVR PASS。
4. **严格 Mock 与当前 Mock 现状有差距。** `mock_outbound_callbacks.py` 检查路径、Content-Type 和 JSON 对象，但对允许路径上的任意对象返回 `Y/OK`；它没有按 API 校验字段集合、Action 和类型。因此旧 Mock 请求成功只能证明本地 HTTP 发出/收到，不能单独证明契约正确。
5. **状态/副作用每步分开断言。** 必须记录 API01/02/03/05/07/09 不产生库存变化；API04/06/08/10 不额外记账；实际一张 Incoming Picking 与一张 Outgoing Picking 分别是主链中唯一的库存增加/扣减节点。
6. 本节只复核现有文件和执行证据，没有运行测试、浏览器操作或修改运行配置。

## 9. 系统性纠正计划

以下是提交 Human Review 的提案；**本轮只修订本报告，没有执行任何纠正项**。每项必须有明确产物和可核验关闭标准；前项未关闭时不得进入依赖阶段。

| 顺序 / ID | 纠正工作及依赖 | 责任阶段 | 必须产物/证据 | 客观关闭条件 | 当前状态 |
|---|---|---|---|---|---|
| 00 / COR-00 证据归档一致性 | 审阅并标记 RUN03 为未完成运行；把已存在 HTTP、Mock、浏览器、ORM 只读证据逐项映射到其记录；未完成盘点/API10保留 NOT RUN。不得删除或覆盖 R8239A3、RUN03、较早 API08 BLOCKED 记录。 | 文档证据收尾；需在任何新 HVR 以前完成。 | RUN03 执行记录的增量勘误/续记；每个 Case 的单一证据链接、判定和剩余项。 | RUN03 的状态、记录表、文件证据无矛盾；R8239A3 明确为跨版本累计；RUN03 明确未完成且不作为最终 Run。 | 待批准 |
| 01 / COR-01 基线受控对齐 | 保留 SRS v1.9、TDD v2.2、Plan v2.9、CC-005 v1.1 原档；按批准的最新业务决定编制新版本/补充，固定一步入库、一步出库、每订单唯一实际 Picking，十 API 的数据源、触发点、字段、库存副作用，尤其 API06/08。 | 基线修订；须 Human Review。 | 新版本 SRS/TDD/Implementation Plan 及 CC-005 追踪补充、差异表、审批记录。 | 同一条活动基线中 API01–10 均可逐项找到已批准规则；API08 仅三字段、数据源为订单状态且要求 Done/Outgoing Picking；API06 明确同一 Picking 的实绩；历史版本仍可追溯。 | 待批准 |
| 02 / COR-02 十 API 契约追踪 | 以 §8 矩阵建立正式的需求—代码路径—CC/自动化测试—HVR 步骤—证据映射，不以通用测试数量代替接口结果。 | 基线批准后。 | 十行追溯矩阵；每行列明 API 请求/按钮入口、来源模型/字段、Action/字段集合、库存期望、自动化与 HVR Case。 | API01–10 每项字段/行为均映射到当前批准条款、至少一个适用测试及一个连续主链检查点；不适用测试标 N/A 并说明。 | 待批准 |
| 03 / COR-03 测试契约判定 | 将 CC-TEST-044–055 与 CC-TEST-140–157 分层映射；逐个检查旧 API02/08 明细断言、API06 备货选择/来源断言、出库路线及库存副作用。旧历史测试保留，按新批准基线明确 KEEP/UPDATE/LEGACY/N/A；不得删除失败证据。 | COR-01/02 后。 | 测试适用性矩阵，包含测试名、原契约版本、目标新条款、修改授权/结果或历史状态。 | 当前执行门禁没有未标注的过期断言；每个冻结用例都有测试 ID、实际运行结果及证据；历史旧失败可追溯，不被覆盖。 | 待批准 |
| 04 / COR-04 最终基线自动化与回归 | 对齐后运行 Ginlong 自动化全集及受影响 WorldDepot 回归。重点覆盖 API 行为、真实 HTTP 入口、数据库写入/回滚、API Event/Log、Mock 次数、一步 Picking 数量和库存不变量。只修复可复现且违反新批准基线的缺陷。 | COR-01–03 批准并完成后。 | 精确代码 revision、模块版本、DB、命令、完整日志、测试列表/结果、隔离检查和修复链接。 | 最终候选版本的所有适用测试 PASS；未运行/阻塞/失败项分别保留并解释；无未解决强制失败；测试前后隔离数据证据齐全。 | 未执行 |
| 05 / COR-05 Strict Mock 契约校验 | 修订本地 Mock 或新增最小测试端校验，使其按 API02/04/06/08/10 分别验证允许路径、POST、JSON 字段集合、Action/类型及响应格式；无效报文不能收到伪成功。此项只属于测试 Mock，不改变生产调用协议。 | COR-01/02 后，HVR Readiness 前。 | Mock 合法/非法请求样例、返回状态、自动化断言及捕获计数。 | 对每个出站 API 有正向样例通过、至少一个错误结构拒绝；API08 只接受三字段；次数可精确核对；不再对任意 JSON 返回 `Y/OK`。 | 未执行 |
| 06 / COR-06 运行环境与权限基线 | 固定目标 DB、代码 revision、已安装模块版本、运行服务进程/启动时间、用户角色、KRWH Incoming/Outgoing 类型、Endpoint 和 Mock；检查普通库存用户访问，不用 Administrator 结果替代。HVR 开始后不改配置。 | 回归通过后、Readiness 前。 | 无凭据的 Environment Manifest、版本/服务检查、操作类型页面证据、普通用户权限证据、Mock health/Endpoint 列表。 | 运行服务确实加载获批候选 revision；目标普通用户可完成冻结步骤；只存在获批的一步流程；出站仅指本机 Mock；各配置已冻结。 | 部分历史证据；需复核 |
| 07 / COR-07 唯一可执行 HVR 包 | 收敛当前分散的 API 独立 HVR、项目流程、历史 payload 目录；指定一个当前活动指南、一个 Case Manifest、一个 Run 专属 Payload/证据目录。专项异常与主链分开，旧资料只读归档。 | COR-01–06 后。 | 包清单、按顺序的依赖图、唯一当前 payload 集、文件 JSON 解析结果、归档索引、证据模板。 | 操作者可从一个入口识别唯一的十 API 执行顺序；每一步输入/点击/预期/失败停止点/证据位齐全；不存在会误执行的冲突活动报文。 | 未执行 |
| 08 / COR-08 Readiness Review | 对 RR-01–09 逐门核证并形成审批结论。任一强制 Gate 为 FAIL/BLOCKED/NOT RUN 即停止，不创建全链业务数据、不启动新 HVR。 | COR-00–07 完成后。 | 签署版 Gate 表及证据索引；项目负责人对 Run ID 的启动批准。 | RR-01–09 全 PASS；批准明确绑定代码 revision、模块版本、DB、配置、测试用户和新 Run ID。 | 未执行 |
| 09 / COR-09 同版完整模拟 HVR | Readiness 获批后，以全新产品/单号/SN/托盘在单一候选版本中连续从 API07 到 API10。业务作业只在浏览器通过现有表单完成；API01/03/05/07/09 调真实本地 HTTP 路由；API02/04/06/08/10 由真实业务按钮发到严格 Mock。 | COR-08 PASS 并获启动批准后。 | 单一 Run 的开/闭版本快照、每一步请求/响应、页面、API Log/Event/业务日志、ORM 只读数据、Picking、库存快照及实盘结果。 | 十个 API 及必需业务作业全部在同一 Run PASS；恰有一张 Incoming 和一张 Outgoing Picking；只有它们分别改变库存；确认/回传/查询/实盘不改变库存；中途零代码或业务配置变更。 | 未启动；RUN03 不可替代 |
| 10 / COR-10 真实人工及外部验收 | 模拟 HVR 完整通过后，由负责人按独立指南执行真实人工 HVR；真实 Ginlong/KR/Gateway 另按授权阶段实施，不混入本地模拟结论。 | COR-09 PASS 后。 | 负责人签署记录；外部端点真实请求/响应、对方确认及环境证明。 | 人工 HVR 与真实外部联调各有独立 PASS/FAIL/BLOCKED；未经授权不得访问真实环境。 | NOT RUN / 后续阶段 |

### 9.1 停止与重开规则

主链开始后若出现失败、意外库存变化、请求/Payload 不符、错误业务来源或环境漂移，立即保存请求、页面、Mock、日志、业务记录和库存前后证据，停止所有依赖步骤。不得在同一 Run 中修改代码、模块、操作类型、Endpoint 或权限后继续；完成获批修复及回归后，建立新 Run ID 和全新业务数据。拆托出库按“来源托盘可追溯”和“拆出后当前托盘绑定”分别判断，不要求拆出产品继续绑定原托盘。

## 10. HVR Readiness Review

**当前 Readiness：NOT READY。** 下表仅基于现有资料做当前判断，没有执行门禁。COR-01–07 和 RR-01–09 全 PASS、且项目负责人书面批准 Run ID 后，才允许开始纠正后的新一轮模拟 HVR。

| Gate | 必须条件 | 现有状态 / 阻塞事实 | 通过证据 |
|---|---|---|---|
| RR-01 活动基线一致 | 一步入库/出库、每单一张 Picking、十 API 数据源/触发/UI/字段/库存边界均一致。 | **BLOCKED**：SRS v1.9、TDD v2.2、CC-005 v1.1 的 API06/API08 描述与后续决定仍有冲突。 | 批准的新 SRS/TDD/Plan/CC 追踪差异表。 |
| RR-02 候选版本冻结 | 代码 revision、模块版本、8099 进程、DB 和起止时间绑定。 | **NOT RUN**：本报告未重新检查当前进程；RUN03 启动前有 `.55` 预检记录，但不等于 Readiness 证据包。 | 同一时刻的 revision、ORM installed/latest、服务 PID/启动时间、DB 记录。 |
| RR-03 全量自动化 | 对齐后 Ginlong 全量与受影响 WorldDepot 回归均通过。 | **NOT READY**：历史 CC-TEST-140–157 在 `.49` PASS；RUN03 前 `.55` 回归日志称 95/95、WorldDepot 8/8，但基线纠正后的候选版还没有运行记录。 | 新候选版本命令/日志/测试映射；所有适用项 PASS。 |
| RR-04 全新数据 | 最终 HVR 的 Owner/产品/SN/托盘/业务编号全新、期初为零，无历史 Picking/实盘关联。 | **BLOCKED**：RUN03 已使用其唯一业务资料，不能复用为纠正后新的最终 HVR；新资料尚未准备。 | Odoo ORM 只读冲突扫描与新 Run Manifest，零写入预置。 |
| RR-05 一步流程与配置 | KRWH 使用既有 Incoming/Outgoing 类型；每张订单只一张 Picking；Endpoint/Mock 和配置提前冻结。 | **PARTIAL**：既有页面显示正确操作类型及 RUN03 实际一入一出；尚未对新的目标版本/Run 做冻结快照。 | UI 配置截图、只读模型快照、Mock endpoint 检查及负责人确认。 |
| RR-06 目标业务用户 | 目标普通库存用户能访问必需 Form、Picking、实盘和回传入口。 | **PARTIAL**：测试用户模拟成功；ATR-GIN-005 仍记录普通库存操作员权限未完全通过。 | 目标角色的真实浏览器权限证据，未改 ACL/组。 |
| RR-07 出入站 HTTP/Mock | 5 入站真实 HTTP；5 出站真实按钮 HTTP；Mock 按协议核字段并精确计数。 | **BLOCKED**：现用回传 Mock 对任意 JSON 对象可返回 Y/OK；不能以此作严格契约证明。 | Strict Mock 正反向契约测试、endpoint/计数快照、真实入口请求/响应。 |
| RR-08 HVR 执行包 | 一个活动流程、一个 payload 集、唯一顺序和停止条件，旧数据可辨识为历史。 | **BLOCKED**：现有文件分布于 API 单项、项目级、CC 历史目录；RUN03 执行表与散落证据不一致。 | COR-00/07 的证据对照、单一活动目录、文件校验和归档清单。 |
| RR-09 启动审批 | RR 状态、证据、检查人及新 Run ID 完整，负责人明确批准启动。 | **NOT RUN**：Readiness 尚未完成，本阶段未申请或授予启动批准。 | 已签署 Readiness 结论与唯一 Run ID。 |

只有当所有强制门禁状态为 PASS，整体才可判 **READY TO START**。PASS 只授权开始模拟，不等于模拟验收通过。

### 10.1 纠正后唯一完整主链

在同一候选代码 revision、同一 installed module version、同一 DB、冻结配置和新 Run ID 内，按以下连续顺序执行；用户业务事实必须由 Odoo UI 操作，ORM 只读核验允许，禁止用 ORM/Shell/直接业务方法代替操作：

1. **API07**：通过 HTTP 建产品模板和 Owner 变体。
2. **API09 期初**：HTTP 查询三个新产品，无正库存；查询只读。
3. **API01**：HTTP 创建客户入库预报；检查仅订单预报数据，无实际库存对象/库存变化。
4. **API02**：订单规划状态按钮回传 N；UI 执行收货确认并记录业务操作后回传 Y；库存不变。
5. **实际入库**：在 UI 建立并完成唯一 Incoming Picking；多产品、多托盘、SN 与非 SN 数据按主链清单建立；只有此步骤增加库存。
6. **API04**：在入库 Order 页面回传唯一 Done/Incoming Picking 实绩；库存不再变化。
7. **API09 入库后**：HTTP 查询 owner/warehouse 下物理量并与 Picking 结果核对。
8. **API03**：HTTP 创建同一 Owner、项目、产品变体的出库订单；不创建第二张作业单、不预留、不改变库存。
9. **实际出库**：在 UI 完成唯一 Outgoing Picking，包含批准的整托与拆托场景；拆托产品允许解除当前托盘绑定，但必须保留来源作业追溯；只有此步骤扣减库存。
10. **API06**：从该 Picking 的实际已保存数据回传备货完成；不另建 Picking、不再次改变库存。若需补充 V3.2 必填作业字段，必须先保存到获准的持久化字段，再由后端读取。
11. **API08**：在订单页面执行离仓状态按钮，发送且仅发送 V3.2 三字段；不创建 Picking、不改变库存。
12. **API09 出库后**：核对物理量、SN/托盘实际剩余关系及查询只读。
13. **API05**：HTTP 创建对应同 Owner/仓库/产品的盘点指令；不建立实盘、不改变库存。
14. **实盘**：业务用户在现有盘点 Form 按实际剩余库存创建关联的实盘结果；不得以计划数量或 `stock.quant` 生成实盘结果。
15. **API10**：从保存的实际盘点结果回传；库存不变。
16. **统一收尾**：核对全部 HTTP/按钮响应、Mock 请求次数/字段、API Log/Event、业务日志、单据状态、仅一入一出 Picking、库存前后快照、实盘结果和版本快照。

同一 Run 中任何代码、模块、DB、配置或权限发生改变，该 Run 即停止且不能被修补为 PASS。跨版本累计、历史订单、独立接口 HVR 和自动化 PASS 只能作为旁证，不能填补当前 Run 的步骤。

## 11. 后续阶段、关闭准则及当前决定

1. **本轮输出：** 只修订本报告及其中的纠正计划；未修改业务代码、SRS/TDD/Implementation Plan/CC 冻结文件，未执行测试、部署、浏览器、数据库写操作或新 HVR。
2. **评审阶段：** 项目负责人批准本报告及 COR/RR 后，授权方可实施基线文档修订及测试契约对齐；任何上游基线修改都保留原版本并发布增量版本。
3. **自动化阶段：** COR-01–07 完成且代码候选固定后，运行必要自动化和受影响回归；产生真实测试报告，并接受失败/未运行状态，不改写旧证据。
4. **Readiness 阶段：** 完成 RR-01–09，逐项附证据并由负责人批准新 Run ID。未全部 PASS 不得开始完整主链。
5. **同版本完整模拟 HVR：** 纠正后使用全新数据，在单一最终版本执行 §10.1 全链。十个 API、唯一入库/出库 Picking、库存不变量、SN/托盘关系和实际盘点均通过才可判模拟 HVR PASS。
6. **真实人工与外部验证：** 项目负责人真实人工 HVR、Ginlong 真实接口/KR Gateway 联调分别判定；Codex 模拟、自动化及本地 Mock 不能代替。
7. **中期结论：** 累计跨版本业务证据 PASS；RUN03 为不完整且证据文档待核对；纠正后的最终版完整模拟 HVR 尚未通过 Readiness，故仍 NOT RUN；真实人工 HVR NOT RUN。**本阶段未启动新的 HVR。**

## 12. 证据索引

- [CC-GIN-005 v1.1](../../implementation/CC-GIN-005-v1.1.md)：冻结范围、CC-TEST-044–055 和原关闭标准。
- [ATR-GIN-005](../../implementation/ATR-GIN-005.md)、[IHR-GIN-005](../../implementation/IHR-GIN-005.md)：历史自动化、WMS 权限和 HVR 证据状态。
- [CC-GIN-007 / IHR-GIN-007](../../implementation/CC-GIN-007-v1.1.md)、[CC-GIN-008 / IHR-GIN-008](../../implementation/CC-GIN-008-v1.0.md)：API01 生命周期、SN 和历史保留。
- [CC-GIN-009 / IHR-GIN-009](../../implementation/CC-GIN-009-v1.0.md)：API02 状态、API04 Picking 来源和 UI。
- [CC-GIN-010 / IHR-GIN-010](../../implementation/CC-GIN-010-v1.0.md)：重复回传确认、取消、重试、并发及真实请求次数。
- [CC-GIN-011 / IHR-GIN-011](../../implementation/CC-GIN-011-v1.0.md)：入站认证、限流、错误和响应规范。
- [CC-GIN-012 / IHR-GIN-012 / ATR-GIN-012](../../implementation/CC-GIN-012-v1.0.md)：CC-TEST-140–157 自动化主链与库存断言。
- [历史项目级模拟最终报告](project_flow/CC-GIN-005_Final_Simulation_HVR_Report.md)：保留旧版本 `PARTIAL`、API08 阻塞及后续补证据记录。
- [项目流程执行记录](HVR_Project_Business_Flow_Execution_Record.md)、[浏览器模拟记录](HVR_Project_Browser_Simulation_Record.md)：历史手工步骤、浏览器观察和状态记录。
- [RUN03 执行证据](project_flow/hvr_run_20261127_run03/)：API07/01/03/05 请求响应和 API09 查询响应；文件中的 API01–API05 状态表待与真实证据对齐。
- [RUN03 出站 Mock 捕获](project_flow/test_data/outbound_received.jsonl) 第 20–21 行：API06、API08 实际按钮请求；Mock 本身尚不是严格 V3.2 校验器。
- [API02 Mock 捕获](api02/test_data/received.jsonl) 第 9–10 行：RUN03 的 N/Y 回传。
- [R8239A3 运行目录](project_flow/cc005_one_step_20261127/)：跨版本累计请求/响应、Mock、浏览器和库存证据。
- [TDD v2.2](../TDD-v2.2.md)、[SRS v1.9](../../requirement/SRS_ginlong_apis-v1.9.md)、[Implementation Plan v2.9](../../implementation/IMPLEMENTATION_PLAN_ginlong_apis-v2.9.md)：现行文件版本及需经批准后受控对齐的差异。

---

**报告结论：** 既有累计业务主链证据为 **PASS（跨版本）**；RUN03 为 **PARTIAL / 未完成**，API10 实际盘点与回传未执行，且运行记录与现存证据不一致；纠正后的最终版完整模拟 HVR 为 **NOT RUN / 尚未 Ready**；项目负责人真实人工 HVR 为 **NOT RUN**。本次仅修订报告及纠正计划，没有启动新 HVR。
