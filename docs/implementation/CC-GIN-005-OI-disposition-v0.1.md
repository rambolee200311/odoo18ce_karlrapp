# CC-GIN-005 Open Item 处置记录 v0.1

| 项目 | 内容 |
|---|---|
| 关联基线 | [CC-GIN-005 v1.0 Frozen with Open Items](CC-GIN-005-v1.0.md) |
| 文档状态 | Decision Record；按项目负责人明确指示记录 |
| 日期 | 2026-11-19 |
| 范围 | 记录 OI-GIN-005-01 至 OI-GIN-005-06 的项目负责人处置；不覆盖或改写 CC-GIN-005 v1.0 |
| 模板同步 | BLOCKED；沿用已批准例外，不标记 PASS |

本记录依据项目负责人最新指示整理 Open Item 状态。CC-GIN-005 v1.0 继续作为原冻结范围基线；本记录不授权编码、测试或修改其他冻结基线。

## 1. 处置结果

| 原 Open Item | 处置 | 依据与边界 |
|---|---|---|
| OI-GIN-005-01：产品模板/变体规则尚未进入上游基线 | **本轮按 SRS/TDD 版本更新任务处理；文档修订已起草，待评审。** 新稿为 [SRS v1.1 Review Draft](../requirement/SRS_ginlong_apis-v1.1.md) 和 [TDD v1.0 Review Draft](../ginlong_apis/TDD-v1.0.md)。 | 两份新稿已写入 API03 方向、产品 template/variant 身份、共享字段归属、API07 `productForm`/tracking 规则及 API09 实际物理库存口径；旧冻结件未改。SRS/TDD 尚未批准或冻结，因此上游实施门禁未通过。待两份文档获批后，再更新 Implementation Plan 的有效基线和 CC-005 追溯；本轮不修改冻结计划，也不据此开始实施。 |
| OI-GIN-005-02：现有产品数据重复模板、共享字段冲突和引用情况盘点 | **关闭为基线 Open Item。** | 是否存在重复/冲突数据属于 CC-005 实施前的数据迁移检查及验收工作，不再阻塞本 CC 文档范围。实施时仍须先检查数据和引用；冲突批次不得静默合并或覆盖，须暂停受影响迁移并提请项目负责人处理。关闭本项不代表该检查已经执行。 |
| OI-GIN-005-03：`productForm` 枚举未见于 Ginlong V3.2 | **关闭。** | 客户明确确认仅“原材料、半成品、成品”三类；原材料不按 SN 管理，半成品/成品按 SN 管理，其他值我方可拒绝。API07 本地规则已确定，不等待额外确认。决策依据与 TV OI-01 关闭记录见 [TV OI closure v1.1](../context/report/TV_ginlong_product_variants_api07_sn_OI-closure-v1.1.md)。V3.2 未列举该枚举的资料事实仍保留，但不构成本项目业务 Open Item。 |
| OI-GIN-005-04：内部 `default_code` 组合编码格式及迁移方案 | **关闭为独立业务 Open Item。** | TDD v1.0 Review Draft 规定内部编码由实现采用稳定、无歧义且不冲突的 owner+原始 `productCode` 表示；它不是 Ginlong 字段，不向外回传。具体编码算法和历史引用迁移属于 CC-005 实施细节及测试，不新增外部契约或 WMS 唯一性规则。 |
| OI-GIN-005-05：`unit`、`power`、`nationalStandard`、`certificationModel` 的字段层级未定 | **关闭。四项均归属 `product.template`。** | 已同步写入 SRS v1.1 §6.1/§7.1 与 TDD v1.0 §2.3。该归属是项目的 Odoo 数据模型决定，不表示 Ginlong 规定 Odoo 的模型字段层级；作为模板共享属性纳入 API07 同码一致性检查。 |
| OI-GIN-005-06：项目模板同步来源缺失 | **移出业务 Open Items，转为文档治理状态。** | 模板同步仍为 **BLOCKED**，沿用已批准流程例外；不得伪记 PASS。该状态不属于 API、产品、库存或 CC-005 业务需求 Open Item。 |

## 2. 当前门禁

1. 本轮 SRS v1.1 与 TDD v1.0 均为 Review Draft；经 Human Review 批准并按工作流冻结前，仍由 SRS v1.0 与 TDD v0.9 作为当前有效冻结基线。
2. CC-GIN-005 v1.0 的范围批准不等于实施授权。SRS/TDD 审批后，仍需更新 Implementation Plan 状态补充及追溯关系，并取得实施授权后才能编码或测试。
3. 完整模板同步核查当前 BLOCKED；已批准的流程例外继续适用。
4. 本轮没有修改业务代码、运行测试或访问真实 Ginlong/Karl Rapp 环境。

## 3. 版本记录

| 版本 | 日期 | 变更 | 状态 |
|---|---|---|---|
| v0.1 | 2026-11-19 | 记录 OI-01 至 OI-06 的项目负责人处置及 SRS/TDD 修订状态；保留 CC-GIN-005 v1.0 原冻结件 | Decision Record；SRS/TDD 草案仍待评审 |
