# Ginlong API 校验器与幂等处理器自动化测试报告

| 项目 | 结果 |
|---|---|
| 报告日期 | 2026-11-19 |
| 代码基线 | Git HEAD `39d53d7`；工作区有未提交修改；`ginlong_apis` manifest `18.0.2.0.12` |
| 环境 | Odoo 18；仓库现有 `venv`、`odoo.conf`；数据库 `odooce_karlrapp` |
| 外部服务 | 使用 Mock/内存用例；未调用真实 Ginlong、生产或 KR Gateway |
| 最终结论 | **FAIL**：现有 Odoo 回归通过，但本轮要求的必填 `false` 和 BOOLEAN 类型用例失败，双向幂等处理器也未实现 |

## 1. 执行方式

Odoo 自动化套件使用现有开发/测试数据库和标准 Odoo 测试运行器：

```sh
./venv/bin/python odoo-bin -c odoo.conf -d odooce_karlrapp --test-enable --test-tags /ginlong_apis -u ginlong_apis --stop-after-init --http-port=0 --gevent-port=0 --log-level=info --log-handler=odoo.tests:INFO --logfile=/private/tmp/ginlong_three_components_suite.log
```

套件结果：**43 个 post-tests，0 failed，0 error**。日志中有并发幂等测试刻意触发的唯一约束冲突记录；Odoo 测试最终摘要为全通过。

必填和类型校验器另用临时内存配置执行定向用例，不修改模块源码或测试数据库；该配置用于覆盖 Ginlong V3.2 以外的通用 BOOLEAN 类型情形。幂等结构探针只检查当前实现和模型，不写入业务数据。

## 2. 必填字段校验器

定向验证 **11 项：10 PASS，1 FAIL**。

| 测试内容 | 结果 | 实际结果 |
|---|---:|---|
| 静态配置包含 API01–API10 | PASS | 加载成功 |
| 必填字段缺失、`null`、空字符串、纯空格 | PASS | 均拒绝并指出字段 |
| 数值 `0` 和非空对象/数组 | PASS | 接受 |
| 嵌套明细缺字段及完整路径 | PASS | 例如 `details[0].productCode`；一次收集多处错误 |
| 原始 Payload 不被修改 | PASS | 校验前后相同 |
| 必填 BOOLEAN 值 `false` | **FAIL** | 当前被 `_blank()` 判为缺失，报 `flag is empty` |

失败位置：[required_validator.py](/Users/lijianqiang/Documents/odoo18ce_karlrapp/mymodules/ginlong_apis/validators/required_validator.py) 的 `_blank()`。本轮测试要求 `false` 作为合法 BOOLEAN 值通过；当前实现仍按旧规则拒绝。

## 3. 字段类型校验器

定向验证 **16 项：14 PASS，2 FAIL**。

| 测试内容 | 结果 | 实际结果 |
|---|---:|---|
| VARCHAR 跳过类型检查 | PASS | 通过 |
| DECIMAL 整数、浮点数、数字字符串 | PASS | 通过，`0` 有效 |
| 非法 DECIMAL、布尔值 | PASS | 均拒绝 |
| 合法 DateTime、非法日期、错误格式 | PASS | 按 `yyyy-MM-dd HH:mm:ss` 检查 |
| 非必填字段缺失 | PASS | 跳过 |
| 嵌套错误路径、多错误收集、Payload 只读 | PASS | 通过 |
| BOOLEAN `true` | **FAIL** | 报 `unsupported configured Q type 'BOOLEAN'` |
| BOOLEAN `false` | **FAIL** | 报 `unsupported configured Q type 'BOOLEAN'` |
| BOOLEAN 字符串 | PASS | 被拒绝 |

失败位置：[type_validator.py](/Users/lijianqiang/Documents/odoo18ce_karlrapp/mymodules/ginlong_apis/validators/type_validator.py) 的 `_check_value()`：当前不支持 `BOOLEAN` 配置类型。

## 4. 幂等处理器

现有 Odoo 套件中 **9 个入站幂等/事务用例通过**，包括成功结果重放、业务键、不同 Payload 放行、失败回滚后重试、并发重复请求、提交失败及响应丢失恢复。API01/03/05/07 的业务键和 API09 不持久化幂等也通过现有测试/代码路径检查。

针对本轮新增的通用双向能力执行 **6 项结构探针：2 PASS，4 FAIL**。

| 探针 | 结果 | 依据 |
|---|---:|---|
| 复用现有幂等表中的业务键、指纹、结果 | PASS | `ginlong.api.idempotency` 已有 `business_key`、`request_fingerprint`、`response_json` |
| API09 不进入持久化幂等 | PASS | 仍为只读查询，不调用幂等入口 |
| 存在独立 `idempotency_rules.json` | **FAIL** | 配置文件不存在 |
| 统一入口支持方向、Action 策略及事件上下文 | **FAIL** | 当前 `execute(env, api_code, payload, operation)` 为入站专用入口 |
| API02/04/06/08/10 回传调用幂等处理器 | **FAIL** | `send_callback()` 直接执行 `requests.post()` |
| 幂等表保存方向、Action、处理状态 | **FAIL** | 模型仅有 API 编号、业务键、指纹和结果字段 |

额外发现：当前处理器按完全相同的业务键和 Payload 指纹重放结果，不区分 Action。因而 Edit 的重复内容会被视作重试；这与本轮“Edit 可重复执行，包括重复内容”的测试要求不一致。该行为未作为通过项。

以下出站验收没有可调用的幂等实现，标记 **NOT RUN / BLOCKED**：成功事件不重复发送、失败/超时状态持久化后重试、相同事件标识重试、不同事件/版本独立发送、出站并发及出站幂等记录与响应的一致性。现有回传测试只能证明 HTTP Mock、响应判定和人工重试路径，不证明幂等。

## 5. API01–API10 接入核对

| API | 当前接入路径 | 本轮结果 |
|---|---|---|
| 01 | `_dispatch` 中在幂等和 ORM 前执行必填/类型校验 | PASS：共享入口核对；现有 API01 集成用例通过 |
| 02 | 回传 Payload 生成后、HTTP 前校验 | PASS：现有 Mock 回传测试通过；无幂等接入 |
| 03 | `_dispatch` 中在幂等和 ORM 前执行校验 | PASS：共享入口核对；现有 API03 集成用例通过 |
| 04 | 回传 Payload 生成后、HTTP 前校验 | PASS：现有 Mock 回传测试通过；无幂等接入 |
| 05 | `_dispatch` 中在幂等和 ORM 前执行校验 | PASS：共享入口核对；现有 API05 集成用例通过 |
| 06 | 回传 Payload 生成后、HTTP 前校验 | PASS：现有 Mock 回传测试通过；无幂等接入 |
| 07 | `_dispatch` 中在幂等和 ORM 前执行校验 | PASS：共享入口核对；现有 API07 集成用例通过 |
| 08 | 回传 Payload 生成后、HTTP 前校验 | PASS：现有 Mock 回传测试通过；无幂等接入 |
| 09 | 请求在库存查询前校验，成功响应输出前校验 | PASS：现有 API09 路由/库存用例通过；不持久化幂等 |
| 10 | 回传 Payload 生成后、HTTP 前校验 | PASS：现有 Mock 回传测试通过；无幂等接入 |

此表是现有接入点和套件覆盖核对，不代表逐个 API 的每项必填、类型边界组合都已完成端到端自动化验证。

## 6. 未覆盖项目与结论

- 本轮没有修改业务实现，也没有新增常驻测试用例；定向 validator 用例使用临时内存配置。
- V3.2 当前 Ginlong 字段没有 BOOLEAN 类型；BOOLEAN 两项是本轮对通用校验器的额外验收要求，现有实现不满足。
- 双向幂等处理器的出站部分当前不存在，相关成功去重、失败/超时状态、事件版本和并发验收不能通过测试证明。
- **最终结论：FAIL。** 现有 43 项 Odoo 回归通过，但必填 BOOLEAN、类型 BOOLEAN 用例失败，且新的双向幂等验收范围未实现/未运行；不将其记为通过。

## 7. 2026-11-19 非必填非文本字段空值修复复测（追加记录）

本节追加本轮结果，不覆盖上文原始测试记录。上文 validator 的 `false` / BOOLEAN FAIL 项已由本轮复测修复；幂等处理器部分未在本轮实施或重新验收，仍按第 4、6 节记录。

### 本轮修改

| 文件 | 修改内容 |
|---|---|
| `mymodules/ginlong_apis/validators/required_validator.py` | 明确只将 `None`、空串和纯空格视为必填缺失；`False`、数值 `0`、数组及对象不视为空值。 |
| `mymodules/ginlong_apis/validators/type_validator.py` | 在类型分派前统一跳过 `None` 与精确空串；其他值，包括 `0`、`False` 和空白文本，继续按配置类型校验，不转换或修改输入。 |
| `mymodules/ginlong_apis/tests/test_ginlong_api.py` | 增加必填、可选 DECIMAL、嵌套字段、DateTime、BOOLEAN、错误聚合及 Payload 不变性测试；同步修正 API09 对布尔值的预期，区分必填空值与后续编码匹配错误。 |

未修改 `data/field_rules.json`、业务数据模型或接口业务处理逻辑。

### 本轮自动化结果

Odoo 全套命令：

```sh
./venv/bin/python odoo-bin -c odoo.conf -d odooce_karlrapp --test-enable --test-tags /ginlong_apis --stop-after-init --http-port=0 --gevent-port=0 --log-level=test
```

| 验收项 | 结果 | 证据 |
|---|---|---|
| 新增校验器行为用例 | **PASS** | `test_required_validator_rejects_missing_null_and_blank_but_accepts_zero`、`test_optional_configured_decimal_skips_only_missing_null_and_empty`、`test_required_nested_datetime_and_generic_optional_non_text_types` 均在全套中执行。 |
| ginlong_apis Odoo 回归 | **PASS** | 46 个 post-tests，0 failed、0 error，4.00 秒，4985 queries。 |
| 语法检查 | **PASS** | `py_compile` 覆盖两个 validator 和测试文件。 |
| Payload 只读及无空值转零 | **PASS** | 新用例比较校验前后输入；缺失、null、空串未被转换为零。 |

测试日志：`debug_logs/odoo_181.log`，本轮摘要在 2026-11-19 11:12:10，Odoo PID 8134（日志第 42668–42670 行）。

### 修复后结论及剩余事项

- 必填校验与字段类型校验：**本轮范围 PASS**。
- 当前 Ginlong `field_rules.json` 未定义 BOOLEAN 字段；BOOLEAN 通用行为使用符合配置结构的测试夹具验证，不代表 Ginlong V3.2 新增了 BOOLEAN 契约。
- 通用双向幂等处理器的出站能力未在本轮处理；完整三组件报告仍不能据此标记总 PASS，沿用第 4、6 节的未完成状态。

## 8. 2026-11-20 错误字段聚合与 40 字符限制复测（追加记录）

本节只记录本轮错误响应规则的补充修复和验证，不覆盖前述历史结论。

### 修复内容

- `REQ01` 必填错误一次列出同类字段，使用逗号分隔；`TYP01` 类型错误同样列出全部错误字段。
- 两类协议错误均按完整字段名边界压缩到 40 字符内；剩余字段以 `...` 表示，不截断单个字段名。
- 必填与类型错误同时存在时仍先返回 `REQ01`；API 日志诊断保留完整必填明细及全部类型错误明细。
- 对外响应仍使用 Ginlong 三字段结构；内部日志分别保留错误码、短消息和完整诊断。

### 验证结果

使用现有 `venv`、`odoo.conf` 和 `odooce_karlrapp` 执行定向 Odoo 测试：

```sh
./venv/bin/python odoo-bin -c odoo.conf -d odooce_karlrapp -u ginlong_apis --test-enable --test-tags '/ginlong_apis:TestGinlongAPI.test_ginlong_error_catalog_uses_stable_configured_codes,/ginlong_apis:TestGinlongHttpAPI.test_http_api07_add_duplicate_rejection_and_repeatable_edit,/ginlong_apis:TestGinlongHttpAPI.test_http_api01_add_replay_delete_authentication_and_validation' --stop-after-init --log-level=test --logfile=/tmp/ginlong-field-error-v033-rerun.log
```

| 验收项 | 结果 | 证据 |
|---|---|---|
| 必填/类型错误长消息格式与 40 字符限制 | **PASS** | `test_ginlong_error_catalog_uses_stable_configured_codes` 检查单字段、多字段、长字段清单及完整诊断。 |
| 必填与类型错误并存的优先级和日志 | **PASS** | API07 真实 HTTP 测试断言对外优先返回全部必填字段，API 日志同时保留 `weight` 类型错误原因。 |
| API01/API07 请求校验真实 HTTP 路径 | **PASS** | 两个 `HttpCase` 测试经本地 HTTP 入口执行并检查协议响应、日志和 ORM 副作用。 |
| Odoo 测试摘要 | **PASS** | 3 个 post-tests、7 个测试执行，0 failed、0 error；日志见 `/tmp/ginlong-field-error-v033-rerun.log`。 |
| 运行服务与安装版本 | **PASS** | ORM 确认模块为 `installed`、版本 `18.0.2.0.33`；`http://127.0.0.1:8099/web/login` 返回 HTTP 200。 |

示例响应：`REQ01: 缺失字段: owner, productForm`；类型错误为 `TYP01: 类型错误字段: weight, length`。若两类错误同时出现，对外按必填优先；类型错误完整清单保留在日志诊断中。
