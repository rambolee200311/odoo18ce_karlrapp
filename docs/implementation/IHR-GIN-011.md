# IHR-GIN-011 — 实施历史记录

| 项目 | 内容 |
|---|---|
| CC | [CC-GIN-011 v1.0 Frozen](CC-GIN-011-v1.0.md) |
| 实施状态 | **Closed；Closure SATISFIED** |
| 日期 | 2026-11-25 |
| 数据库 | 本地开发库 `odooce_karlrapp` |
| 模块版本 | `ginlong_apis 18.0.2.0.49` |
| 上游基线 | [SRS v1.9](../requirement/SRS_ginlong_apis-v1.9.md)、[TDD v2.2](../ginlong_apis/TDD-v2.2.md)、[Implementation Plan v2.7](IMPLEMENTATION_PLAN_ginlong_apis-v2.7.md) |
| ATR | [ATR-GIN-011](ATR-GIN-011.md) |

## 1. 实施范围

按批准的 CC-GIN-011，统一 API01/03/05/07/09 的通用组件接入及错误响应状态映射；API09 增加有效 API User 前置条件与独立 10 次/秒限流，保持只读独立查询编排；API03/API05 成功 HTTP 响应严格裁剪为 Ginlong V3.2 三字段。没有修改业务 Handler、业务键、库存口径或出站接口。

## 2. 代码实施

| 文件 | 变更 |
|---|---|
| `mymodules/ginlong_apis/controllers/ginlong_controller.py` | 集中映射 AUTH01/02、RATE01/02、SYS01 的 HTTP 状态；统一协议错误响应；API09 认证 API User 并使用共享限流；API03/API05 成功响应严格裁剪；API09 成功响应保留库存协议字段 |
| `mymodules/ginlong_apis/models/api_control.py` | 增加 API09 独立限流字段、配置默认值与读取、正数校验 |
| `mymodules/ginlong_apis/views/res_config_settings_views.xml` | 在既有 Ginlong 设置入口显示 API09 每秒限流值 |
| `mymodules/ginlong_apis/data/error_codes.json` | 补充统一 API User 无访问资格错误 AUTH02 |
| `mymodules/ginlong_apis/tests/test_ginlong_api.py` | 更新过时状态码/响应字段断言；补充 API09 真实 HTTP 限流；补充五接口无效/过期 Token 与无 API User 的真实 HTTP 访问拒绝、错误日志和无业务副作用断言 |
| `mymodules/ginlong_apis/__manifest__.py` | 版本更新为 `18.0.2.0.49` |

文件此前已有其他项目未提交修改。本次只增量修改 CC-GIN-011 所需内容，未清理、重置、提交或推送其他工作区变更。

## 3. 实际验收

- 最终全量 Odoo 模块测试：91 post-tests，0 failed，0 error；模块统计 95 tests、17,314 queries。证据见 ATR-RUN-003。
- CC-TEST-121～139 的每项契约均映射到实际执行方法与行为断言，见 ATR §2。
- 首轮只因旧测试把 SYS01 的 500 仍断言为 200 而失败；失败历史保留。按已批准规范将断言改为 500 后完成全量通过，未放宽实现。
- 重启后 8099 `/web/login` HTTP 200。Odoo Shell ORM 只读确认安装版本与 latest version 均为 `18.0.2.0.49`，API09 独立限流参数为 10。
- Python 编译及 JSON 配置检查通过；Settings XML 由 Odoo 模块升级流程加载。

## 4. 未改变的边界与后续事项

- API01/03/05/07 的既有业务动作、业务键、数据映射及幂等策略保持不变。
- API09 不使用持久化幂等，不改变库存查询口径或库存数据。
- API02/04/06/08/10 出站接口未改。
- 没有访问真实 Ginlong、生产环境或 Karl Rapp Gateway。
- 真实 Ginlong 对 HTTP 状态码映射的兼容性留最终联调确认；模板同步 BLOCKED 按已批准例外保留。
- 本 CC 不单独组织人工 HVR；项目级 HVR 继续按原流程执行。

## 5. 实施完成时的关闭建议（历史记录）

本节记录关闭批准前的状态，后续已由 §6 的 Human Review 决定取代。冻结范围的实现、自动化、组件集成与本地服务版本核验已完成；当时建议 Closure 为 **SATISFIED**。未将 Deferred、N/A 或 BLOCKED 伪记为 PASS。

## 6. 关闭记录（2026-11-25）

- Human Review：**APPROVED**；项目负责人批准关闭 CC-GIN-011。
- Closure：**SATISFIED**；CC-TEST-121～139 全部映射并通过，最终回归见 ATR-RUN-003。
- CC-GIN-011 状态更新为 **Closed**；对应正式关闭记录见 [FR-GIN-011 v1.0](FR-GIN-011.md)。
- 项目原 API01 HVR 继续；本 CC 不单独组织 HVR。模板同步 BLOCKED 及真实 Ginlong Deferred 保持原状。
