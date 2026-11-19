# TV-GINLONG-PRODUCT-001：productForm Open Item 关闭补充 v1.1

| 项目 | 内容 |
|---|---|
| 关联报告 | [TV-GINLONG-PRODUCT-001 v1.0 Closed with Open Items](TV_ginlong_product_variants_api07_sn_v1.0.md) |
| 状态 | 项目负责人/客户业务决策记录；OI-01 已关闭 |
| 日期 | 2026-11-19 |
| 范围 | 仅处置 TV v1.0 的 OI-01；其余 OI 和原报告状态不变 |

## 决策依据

客户确认：

> 按 productForm 区分，若为“原材料”，则不按 SN 管理；若为“半成品”“成品”，则按 SN 管理。productForm 如果不是这 3 类，我方可以拒绝。

## 关闭结论

API07 的本地产品主数据契约明确为：

| `productForm` | Odoo `product.template.tracking` | API07 处理 |
|---|---|---|
| 原材料 | `none` | 接受；不要求 SN |
| 半成品 | `serial` | 接受；要求 SN |
| 成品 | `serial` | 接受；要求 SN |
| 其他值 | 不设置/不改变已有 tracking | 拒绝请求，不修改已有产品 |

据此，TV v1.0 OI-01（是否限定上述三种 `productForm`）**关闭**。该决定足以确定本项目 API07 的校验和 SN 跟踪行为，不再等待额外业务确认。V3.2 工作簿未列出枚举这一资料事实仍保留；本地接受范围依据客户明确决定，不把该决定表述为 Ginlong V3.2 字段表的原文或 Ginlong 单独出具的协议确认。CC-GIN-006 可以验证实际接口数据，但该验证不再是本地规则实施的前置 Open Item。

本补充不改写 TV v1.0，也不关闭其他 TV Open Items，不声称相关代码或测试已完成。该规则已纳入 [SRS v1.1 Review Draft](../../requirement/SRS_ginlong_apis-v1.1.md) 与 [TDD v1.0 Review Draft](../../ginlong_apis/TDD-v1.0.md)，仍须通过上游文档评审和冻结后成为有效基线。
