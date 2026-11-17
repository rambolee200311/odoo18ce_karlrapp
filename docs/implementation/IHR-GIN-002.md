# 实施历史记录：IHR-GIN-002

## 0. 文档治理

| 字段 | 值 |
|---|---|
| CC | [CC-GIN-002 v1.0 Frozen](CC-GIN-002.md) |
| IHR 版本 | v1.0 |
| TDD 基线 | v0.3 Frozen with Open Items |
| 模块 | `ginlong_apis` |
| 工作类型 | 新接口功能实施 |
| 实施负责人 | Codex |
| 开始 / 最后更新 | 2026-11-17 |
| 当前实施状态 | Implementation Complete；FR-GIN-002 v1.0 Closure SATISFIED；Human Review APPROVED；CC-GIN-002 Closed |
| 测试代码基线 | Ginlong addon 源码指纹 `d87e0952022786c7f393438573b372fc870df629816b40c572b1764451a030ff`（ATR-RUN-009） |

## 1. CC 基线

范围、边界及验收义务均引用 [CC-GIN-002 v1.0](CC-GIN-002.md)；本记录不扩展冻结范围。

| CC 项 | 实施状态 |
|---|---|
| CC-CHANGE-001 API01 | 完成：复用入库订单及原有订单→托盘→产品结构 |
| CC-CHANGE-002 API03 | 完成：按 A-003 本地假设复用出库订单和产品行 |
| CC-CHANGE-003 API05 | 完成：建立独立盘点任务及明细，未访问库存模型 |
| CC-CHANGE-004 API07 | 完成：扩展 `product.product`，使用原生产品模板/变体 |
| CC-TEST-001–006 | 见 [ATR-GIN-002](ATR-GIN-002.md) |

## 2. 当前实施状态

| 项 | 状态 |
|---|---|
| CC-CHANGE | 4 / 4 完成 |
| Preservation Impact | 有影响面；测试确认订单仍为待处理状态，未产生 picking 或库存过账 |
| 偏离 | 无 |
| Stop Condition | 未触发 |
| Open Issues | 外部协议及 Ginlong 确认事项按 CC 保留；不阻塞本地模拟验收 |
| 当前状态 | Implementation Complete |

## 3. 实施历史条目（仅追加）

### IHR-001 — 核对运行环境与既有能力

- 阶段：Implementation
- Action：确认 Odoo 18、现有 `ginlong_apis` addon、`worlddepot` 入/出库模型、共享 Token validator、API logger 及产品对象；确认本地模拟路由需与生产契约区分。
- Contract Reference：CC-CHANGE-001–004、CC-TEST-005/006
- Result：Completed
- Deviation：None
- Follow-up：真实 Ginlong 协议仍按 CC 记录待外部确认。

### IHR-002 — 建立 ORM 字段及盘点任务模型

- 阶段：Implementation
- Action：扩展现有入库、出库、订单行、入库序列号和 `product.product`；新增 `ginlong.stocktake.task` 与其产品明细模型及访问权限。以 Ginlong 原值字段保留现有 WMS 对象不能直接表达的字段，不做尺寸/重量换算。
- Files / Components：`models/ginlong_models.py`、`models/wms_extensions.py`、`security/ir.model.access.csv`
- Contract Reference：CC-CHANGE-001–004
- Upstream Reference：TDD §3、§5
- Result：Completed
- Deviation：None
- Follow-up：完整托盘生命周期及货主解绑属于后续 CC。

### IHR-003 — 接入 API01/03/05/07 本地模拟处理

- 阶段：Implementation
- Action：新增轻量 ORM 映射服务及四个明确标注为模拟的控制器路由；复用 `worlddepot` 的 Token validator 和 API logger。订单创建只调用原订单 `create`，不调用 `action_confirm`、过账或库存调整；盘点服务仅创建/删除独立任务；API07 在原生产品模型上新增/更新。
- Files / Components：`services.py`、`controllers/ginlong_controller.py`、`controllers/__init__.py`、addon `__init__.py`、`__manifest__.py`
- Contract Reference：CC-CHANGE-001–005、CC-TEST-001–006
- Result：Completed
- Deviation：None
- Follow-up：路由路径及传输协议仅供本地模拟，非 Ginlong 已确认生产 URL。

### IHR-004 — 修复首轮 ORM 测试发现的字段不匹配

- 阶段：Fix
- Action：首轮真实 Odoo ORM 测试发现 API01 子产品与 API03 出库行缺少 Ginlong 原始字段；补齐 API01 产品编码字段，并删除对原生数量重复写入的扩展字段。
- Files / Components：`models/wms_extensions.py`、`services.py`
- Contract Reference：CC-CHANGE-001/002、CC-TEST-001/002
- Result：Completed；后续测试复验通过
- Deviation：None
- Follow-up：首轮失败保留于 ATR-RUN-001。

### IHR-005 — 完成完整字段和业务边界组件测试

- 阶段：Implementation / Fix
- Action：增加 Odoo `TransactionCase`，覆盖 API01/03/05/07、完整来源字段、创建/删除/更新及共享 Token/logger 调用；处理测试替身与包装器断言问题。所有修复后均重跑。
- Files / Components：`tests/test_ginlong_api.py`、`tests/__init__.py`
- Contract Reference：CC-TEST-001–006
- Result：Completed；最终 6 项测试全通过
- Deviation：None
- Follow-up：中间失败保留于 ATR-RUN-002–007。

### IHR-006 — 现有 Odoo 环境升级及最终复验

- 阶段：Implementation / Verification
- Action：用项目既有 Odoo 配置、venv、`odooce_karlrapp` 及 ORM 加载 addon；通过 Odoo 标准测试运行器完成最终测试。未创建隔离数据库或环境、未直接访问 PostgreSQL、未安装/启用 `stock_barcode`。
- Files / Components：现有 `odoo.conf`、`venv`、数据库 `odooce_karlrapp`
- Contract Reference：CC-TEST-006
- Result：Completed；初次最终复验见 ATR-RUN-008，补充字段复验见 ATR-RUN-009
- Deviation：None
- Follow-up：等待 Human Review；CC 状态不在本记录中提前关闭。

### IHR-007 — 补齐 API01 名称别名并加强字段复验

- 阶段：Fix / Verification
- Action：按 CC 明确的 `name/productName` 兼容字段，为 API01 入库明细增加名称别名映射；扩展 ORM 断言覆盖 API01 备注及 SN 数量/托盘/产品/规格，API03 备注与数量、API05 备注及产品名称/规格、API07 产品规格。使用同一 Odoo 标准运行器重跑全部模块测试。
- Files / Components：`services.py`、`tests/test_ginlong_api.py`、现有 Odoo 测试运行器
- Contract Reference：CC-CHANGE-001–004、CC-TEST-001–006
- Result：ATR-RUN-009 6/6 PASS，0 failed、0 error；随后 Odoo Shell ORM 确认 addon installed、模型及字段注册、测试数据无残留、`stock_barcode` 状态为 uninstallable。
- Deviation：None
- Follow-up：真实 Ginlong 协议/API03 方向仍待外部确认；模板同步继续 BLOCKED。

## 4. 实际变更清单（当前快照）

| 文件 | 动作 | 实际变更 | CC 来源 |
|---|---|---|---|
| `mymodules/ginlong_apis/__init__.py` | 修改 | 加载模型与控制器 | CC-CHANGE-001–004 |
| `mymodules/ginlong_apis/__manifest__.py` | 修改 | 版本升级并声明 ACL 数据 | CC-CHANGE-003 |
| `mymodules/ginlong_apis/services.py` | 新增 | API01/03/05/07 的轻量 ORM 字段映射和本地模拟动作 | CC-CHANGE-001–004 |
| `mymodules/ginlong_apis/controllers/` | 新增 | 四个本地模拟入口；引用现有 Token 与日志装饰器 | CC-TEST-005 |
| `mymodules/ginlong_apis/models/ginlong_models.py` | 新增 | 独立盘点任务及产品行 | CC-CHANGE-003 |
| `mymodules/ginlong_apis/models/wms_extensions.py` | 新增 | Ginlong 来源字段扩展到现有 WMS / 产品模型 | CC-CHANGE-001/002/004 |
| `mymodules/ginlong_apis/security/ir.model.access.csv` | 新增 | 盘点任务模型访问权限 | CC-CHANGE-003 |
| `mymodules/ginlong_apis/tests/` | 新增 | Odoo 自动化与 ORM 组件测试 | CC-TEST-001–006 |

## 5. 偏离与停止条件记录（仅追加）

| 事件 | 处理 | 状态 |
|---|---|---|
| Odoo Shell 在普通沙箱启动时绑定 HTTP 端口被拒绝 | 在用户既有环境授权下使用受控主机执行；随后用标准 Odoo 测试运行器执行。未更换配置/数据库或使用 SQL | 已解决；非代码偏离 |
| 项目模板来源缺失 | 按冻结 CC 的批准例外继续；同步检查状态仍为 BLOCKED | 保留 BLOCKED，不改写为通过 |

无代码范围偏离，无额外模型、认证框架、库存账或扫码依赖。

## 6. 后续问题

| 问题 | 状态 / 处置 |
|---|---|
| Ginlong URL、HTTP、鉴权/响应及字段语义 | 待外部确认；四路由仅为本地模拟，真实联调留后续阶段 |
| API03 方向 | A-003 Solis → Odoo 开发假设，未宣称为 Ginlong 确认 |
| API03 WMS 收货方 | 复用已有 `res.partner`；无唯一匹配记录时返回明确错误，不自动创建额外联系人 |
| 项目与货主解绑、托盘生命周期 | 项目必须完成的后续需求；未纳入本 CC 完成范围 |
| 模板同步 | BLOCKED；沿用 CC 已批准流程例外 |

## 7. 移交摘要

编码实施完成，ATR-RUN-009 在当前 Ginlong addon 指纹上 6/6 通过。该结果证明现有 Odoo 环境中的 ORM 映射及组件边界，不代表 Ginlong 生产协议或真实 HTTP 联调通过。原始移交时 FR-GIN-002 v0.2 等待 Human Review（见下方历史）；项目用户随后批准关闭，关闭记录见 IHR-008 与 FR-GIN-002 v1.0。本次关闭文档更新未修改业务代码、未重跑测试。

### IHR-008 — Human Review 批准与关闭状态记录

- 阶段：Closure documentation
- Action：依据项目用户明确决定，将 FR-GIN-002 更新为 v1.0，记录 Closure SATISFIED、Human Review APPROVED；将 CC-GIN-002 更新为 Closed，并回填 Implementation Plan。
- Result：Completed；最终有效测试基线仍为 ATR-RUN-009。未重跑测试。
- Deviation：None；不修改业务代码。
- Open items：Ginlong 外部协议、API03 正式方向及模板同步仍未解决；历史 BLOCKED/待确认状态保留。

## 附录：版本历史

| 版本 | 日期 | 说明 | 状态 |
|---|---|---|---|
| v0.1 | 2026-11-17 | 建立 CC-GIN-002 实施历史，记录四接口实施、测试修复及最终复验 | Implementation Complete |
| v0.2 | 2026-11-17 | 记录 API01 名称别名修正、字段断言加强及 ATR-RUN-009 最终复验 | Implementation Complete；FR Human Review Pending |
| v1.0 | 2026-11-17 | 记录 Human Review APPROVED、FR-GIN-002 v1.0 与 CC-GIN-002 v1.0 关闭；不重跑测试、不改代码 | Closed |
