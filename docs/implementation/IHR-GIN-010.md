# IHR-GIN-010 — 实施历史记录

| 项目 | 内容 |
|---|---|
| CC | [CC-GIN-010 v1.0 Frozen](CC-GIN-010-v1.0.md) |
| 实施状态 | **Closed；Closure SATISFIED** |
| 实施日期 | 2026-11-25 |
| 模块版本 | `ginlong_apis 18.0.2.0.47` |
| 数据库 | 本地开发库 `odooce_karlrapp` |
| 上游冻结基线 | [SRS v1.8](../requirement/SRS_ginlong_apis-v1.8.md)、[TDD v2.1](../ginlong_apis/TDD-v2.1.md)、[Implementation Plan v2.6](IMPLEMENTATION_PLAN_ginlong_apis-v2.6.md) |

## 1. 范围

实现 API02、API04、API06、API08 的重复/未知结果确认和稳定业务事件并发保护。维持各 API 既有业务事实来源、Payload、Action 和事件粒度。API10 不变。本地自动化使用 Odoo 测试数据库与 Mock HTTP，不访问真实 Ginlong、生产或 Karl Rapp。

## 2. 代码实施记录

| 文件 | 实施内容 |
|---|---|
| `mymodules/ginlong_apis/idempotency.py` | 规范化 Payload 指纹；稳定业务事件身份独立于 Payload 指纹和确认令牌；使用 ORM 事件代次及唯一执行槽位序列化发送；发送前 flush；竞争者读取已提交协调状态；结果检查与旧成功日志兼容 |
| `mymodules/ginlong_apis/data/idempotency_rules.json` | 为 API04/06 配置 `snList` 指纹排序规则；保持实际发送 Payload 不变 |
| `mymodules/ginlong_apis/models/api_control.py` | 在既有幂等模型增加执行槽位和稳定事件协调字段及数据库唯一约束 |
| `mymodules/ginlong_apis/models/ginlong_callbacks.py` | 区分明确失败、成功、结果未知；真实请求和 API Log 仍走既有回传流程 |
| `mymodules/ginlong_apis/models/callback_confirmation.py` | 一次性消费确认向导；重新读取 ORM 数据后重建 Payload 并执行发送 |
| `mymodules/ginlong_apis/models/api_log.py` | API Log 关联既有幂等 Event |
| `mymodules/ginlong_apis/models/__init__.py` | 注册通用确认向导模型 |
| `mymodules/ginlong_apis/views/callback_confirmation_views.xml` | 提供重复发送/结果未知确认界面 |
| `mymodules/ginlong_apis/views/ginlong_callback_views.xml` | 复用既有 Form 按钮入口及 Odoo 标准 RPC loading/disabled 行为；修正 API04 页面说明以匹配重复成功确认、明确失败重试、unknown 风险确认和处理中不重复发送 |
| `mymodules/ginlong_apis/__manifest__.py` | 注册确认视图并将模块版本升至 `18.0.2.0.47` |
| `mymodules/ginlong_apis/tests/test_ginlong_api.py` | 增补指纹、结果分类、确认重发/取消、跨令牌标签页并发、实际 Mock HTTP 次数及 API10 不变回归断言 |

## 3. 设计决定落地

- 并发身份只依赖稳定业务事件及原事件粒度，不依赖用户、标签页、确认令牌或 Payload 内容。
- 数据库执行槽位在 HTTP 调用前通过 ORM flush，唯一约束冲突的竞争请求不发送。
- 对象键顺序、空白、等值 `1`/`1.0` 不改变规范指纹；API04/06 `snList` 指纹排序不改变真实报文。
- 明确 `returnStatus=N` 归为 failed；发送后连接/超时异常、没有明确 N 的 HTTP 错误、无效/不完整响应归为 unknown。只有用户确认风险后才重试 unknown。
- 用户取消不产生 HTTP；实际发送追加 Event、API Log；重复确认记录写入来源 Chatter；历史记录不覆盖。
- API04 多 Picking 保持每 Picking 一个事件；API06 保持订单级聚合；API02/08 仍按订单级事件。

## 4. 未改变的边界

- API10 行为未改变。
- 不新增独立幂等、防抖或锁服务；未修改 Ginlong 协议、WMS 库存流程或 Karl Rapp Gateway。
- 本 CC 不做人工 HVR；API02/API04 项目级业务 HVR 按批准决定继续由验收人执行。
- 模板同步仍 BLOCKED，沿用批准的流程例外，不表示 PASS。
- 本地开发改动未执行 Git commit 或 push。

## 5. 评审状态

## 6. 关闭记录（2026-11-25）

- Human Review：**APPROVED**；项目负责人批准 CC-GIN-010 关闭。
- Closure：**SATISFIED**；CC-TEST-101～120 与实际测试方法/RUN/结果的映射见 [ATR-GIN-010 §3](ATR-GIN-010.md)。全量 82 post-tests 见 ATR-RUN-008；后续 7 个矩阵缺口测试见 ATR-RUN-013，7/0/0。
- 本地模块仍核实为 `18.0.2.0.47`；不访问真实 Ginlong/生产。
- 本 CC 独立人工 HVR 为 N/A；项目业务 HVR 仍单独执行，浏览器模拟和真人结论分开记录。
- 模板同步 BLOCKED 按已批准例外保留；真实 Ginlong Deferred；均不记 PASS。
- 关闭文件：[FR-GIN-010 v1.0](FR-GIN-010.md)。

最终复验特别记录：API04 Notebook 文案按新规则更新后，已重新升级模块并执行完整 Ginlong 套件，82 post-tests、0 failed、0 error（ATR-RUN-008）。随后 8099 本地 `/web/login` 返回 HTTP 200；通过 ORM 确认模块 `installed_version` 和 `latest_version` 均为 `18.0.2.0.47`（ATR-RUN-009）。
