# AGENTS.md

> 本文件定义整个仓库的通用开发规范、代码规范以及 AI Agent 的工作流程。
>
> **本文件不包含任何业务逻辑约束。**
> 如果项目存在业务相关、架构相关、技术栈相关的特殊要求，请在仓库根目录创建 `PROJECT_AGENTS.md` 作为补充约束。

---

# 一、工作原则

AI Agent 在开始任何开发任务之前，应遵循以下流程：

1. 阅读当前目录能够访问到的 `AGENTS.md`
2. 如果位于仓库根目录，则优先读取：
   - `AGENTS.md`
   - `PROJECT_AGENTS.md`（如果存在）
3. 如果当前开发内容属于某个功能模块，则继续读取该模块下最近的 `AGENTS.md`
4. 所有约束采用**就近原则**：
   - 根目录 `AGENTS.md`：全局规范
   - `PROJECT_AGENTS.md`：项目特殊规范
   - 子模块 `AGENTS.md`：当前模块实现说明

5. 对应结论不清楚时，不得仅凭猜测作出判断或报告结果：
   - 应优先通过源码、配置、日志、测试或其他可验证证据确认结论。
   - 如果结果需要在应用界面中确认，可以使用电脑控制功能打开对应应用程序并查看实际结果。
   - 无法确认时，应明确说明不确定性和缺少的证据，不得将推测表述为事实。

6. 与用户的所有交互沟通（包括提问、确认、说明、总结等）必须使用中文。

---

# 二、PROJECT_AGENTS.md

为了保持本文件的通用性：

**任何与当前项目强相关的约束，都不允许直接写入本文件。**

例如：

- 技术选型
- 数据库规范
- API 风格
- Git Flow
- CI/CD
- 部署方式
- 目录结构要求
- 编码规范补充
- 命名约束
- 日志规范
- 权限体系
- 多租户设计
- 微服务约束
- 领域模型说明
- 第三方平台接入规范

应统一放入：

```
PROJECT_AGENTS.md
```

AI Agent 在开始开发之前，必须读取该文件（如果存在）。

---

# 三、模块 AGENTS.md

## 每一个功能模块必须拥有自己的 AGENTS.md

例如：

```
backend/

    user/
        AGENTS.md

    order/
        AGENTS.md

    inventory/
        AGENTS.md

frontend/

    pages/
        user/
            AGENTS.md

    components/
        table/
            AGENTS.md
```

模块 AGENTS.md **不是代码规范文件**。

它用于描述：

- 当前模块职责
- 功能介绍
- 实现方式
- 模块结构
- 核心类
- 核心接口
- 数据流
- 依赖关系
- 注意事项
- 历史设计原因（可选）

让 AI 能快速理解模块，而无需阅读全部源码。

---

# 四、自动维护模块 AGENTS.md

AI Agent 修改代码时，应同步维护模块 AGENTS.md。

包括但不限于：

- 新增功能
- 删除功能
- 修改功能
- 调整目录
- 修改接口
- 修改数据流
- 新增核心类
- 新增公共组件
- 修改模块职责

若模块发生变化，则：

**必须同步更新对应模块 AGENTS.md。**

如果模块不存在 AGENTS.md：

**必须自动创建。**

禁止出现：

> 模块代码已经发生明显变化，而 AGENTS.md 长时间未更新。

---

# 五、模块 AGENTS.md 内容要求

模块 AGENTS.md 推荐包含：

```
模块简介

主要职责

目录说明

核心类

核心接口

主要流程

依赖关系

数据流

配置说明

扩展方式

注意事项
```

无需描述代码规范。

无需重复根目录 AGENTS.md。

仅关注当前模块自身。

---

# 六、代码修改原则

除非任务明确要求，否则应遵循：

- 优先修改现有代码
- 尽量避免重复实现
- 保持已有设计风格
- 保持向后兼容（如可行）
- 尽量减少影响范围
- 不进行无关重构
- 不修改无关文件

---

# 七、Git 提交规范

- Git 提交信息（commit message）必须使用中文。
- 提交信息应简洁、准确地描述本次变更内容；必要的技术名词、命令、路径或标识符可保留英文。

---

# 八、代码质量要求

生成代码应满足：

- 保持高可读性
- 保持模块化
- 避免重复代码
- 保持职责单一
- 尽量降低耦合
- 合理封装
- 命名清晰
- 删除未使用代码
- 删除明显无用变量
- 避免过度设计

---

# 九、代码规范

除非任务明确要求或生态工具另有强制格式，否则生成和修改代码时应遵循：

- 单行代码长度不超过 120 个字符
- 单个代码文件不超过 500 行
- 配置文件不受 500 行文件长度约束
- Agent 文档（如 `AGENTS.md`、`MEMORY.md`、`LEARNING.md`、`WIKI.md`）不受 500 行文件长度约束，但不得超过 1000 行
- 如果单个代码文件接近或超过 500 行，应优先拆分职责、提取模块或复用已有公共能力
- 不为满足行数限制进行机械拆分，应保持模块边界清晰、职责自然

---

# 十、修改风格

修改已有代码时：

优先：

- 延续已有代码风格
- 延续已有命名方式
- 延续已有组织方式

不要因为个人偏好而：

- 大规模格式化
- 修改无关代码
- 调整整个文件结构
- 更换已有实现方式

除非任务明确要求。

---

# 十一、注释原则

代码注释应：

- 解释为什么这样实现
- 避免解释代码本身
- 保持同步更新
- 删除失效注释

避免大量无意义注释。

---

# 十二、文档同步

如果本次修改影响：

- 使用方式
- 配置方式
- 模块结构
- 对外接口
- 开发流程

则应同步更新对应文档。

包括但不限于：

- README
- 模块 AGENTS.md
- PROJECT_AGENTS.md（若涉及项目约束）
- 其他设计文档

## 项目知识文件

AI Agent 应在项目根目录创建并维护以下文件；文件不存在时，应自动创建：

- `MEMORY.md`：记录项目当前进度，包括已完成事项、进行中事项、后续计划和阻塞问题。
- `LEARNING.md`：沉淀开发过程中遇到的问题、原因、解决方案和复盘结论。
- `WIKI.md`：保存长期有效的项目知识，包括架构、核心概念、约定和重要设计决策。

当相关信息发生变化时，应及时更新对应文件，并确保：

- `MEMORY.md` 只保留当前有效的进度信息，及时清理已失效内容。
- `LEARNING.md` 仅记录经过验证的结论，不得将未经确认的推测作为经验沉淀。
- `WIKI.md` 不记录临时任务状态，避免与 `MEMORY.md` 内容重复。

## Claude 指引文件

AI Agent 应在项目根目录创建并维护 `CLAUDE.md`；文件不存在时，应自动创建。

`CLAUDE.md` 必须明确告知 Claude：开始任务前应先读取并遵循项目根目录的 `AGENTS.md`，
并按其中的规则继续读取 `PROJECT_AGENTS.md` 和模块 `AGENTS.md`（如存在）。

`CLAUDE.md` 仅作为 Claude 的入口指引，不应重复 `AGENTS.md` 的完整内容；当 `AGENTS.md` 的读取流程
或约束层级发生变化时，应同步更新 `CLAUDE.md`。

---

# 十三、禁止事项

不要：

- 编造不存在的接口
- 编造不存在的配置
- 编造不存在的依赖
- 保留明显废弃代码
- 引入未使用的依赖
- 修改无关模块
- 忽略编译错误
- 忽略类型错误
- 忽略明显异常

---

# 十四、优先级

多个约束冲突时，优先级如下：

```
用户明确要求
        ↓
当前模块 AGENTS.md
        ↓
PROJECT_AGENTS.md
        ↓
根目录 AGENTS.md
```

越靠近当前模块，优先级越高。

---

# 十五、适用范围

本规范适用于但不限于：

- Python
- Java
- Go
- Rust
- C#
- C++
- JavaScript
- TypeScript
- Vue
- React
- Angular
- Node.js
- Flutter
- Android
- iOS

以及其他语言和框架。

所有语言均遵循相同原则。

---

# 十六、目标

AI Agent 应始终做到：

- 理解模块，而不是仅修改代码
- 保持文档与代码同步
- 保持代码风格一致
- 尽量减少修改范围
- 保持实现简单、清晰、可维护
- 保证模块 AGENTS.md 始终反映当前实现

---

# 十七、通用软件交付型子 Agent 协作流程

本节定义可跨项目复用的软件交付型子 Agent 工作流，不包含具体项目的业务或技术栈约束。
`PROJECT_AGENTS.md` 只能补充当前项目的特殊要求，不得承载或重复本节公共逻辑。

## 17.1 团队结构与调度

当工作环境提供对应自定义角色时，主 Agent 按以下生命周期组织交付：

```text
产品经理 -> 架构师（按需）-> 开发 -> 测试 -> 审核 -> 验收
```

主 Agent 是唯一调度者，负责理解用户请求、划分任务等级、选择角色、维护阶段状态、处理回退，
并向用户提交最终结果。子 Agent 只完成被委派的岗位工作，不得修改上游需求或替代下游作结论。

| 角色 | 配置名 | 职责 | 禁止事项 |
| --- | --- | --- | --- |
| 产品经理 | `product_manager` | 整理任务单、范围和验收标准 | 设计实现、修改文件、代替用户作业务取舍 |
| 架构师 | `solution_architect` | 设计跨模块或高风险技术方案 | 修改文件、重新定义产品目标 |
| 开发 | `developer` | 实现生产代码、基础测试和相关文档 | 放宽验收标准、无关重构、提交或发布 |
| 测试 | `tester` | 设计测试、补充测试资产、执行回归 | 修改生产代码、业务文档或接受快照变化 |
| 审核 | `reviewer` | 审核代码和交付完整性 | 修改文件、代替验收作产品结论 |
| 验收 | `acceptance_owner` | 按用户场景逐条验收 AC | 修改文件、放宽标准、批准发布 |

## 17.2 任务分级与路由

主 Agent 在执行前根据最高风险特征确定等级。多个等级同时匹配时采用较高等级。

| 等级 | 判定条件 | 必经角色 |
| --- | --- | --- |
| `T0` | 问答、解释、只读调研，不发生任何工作区写入 | 主 Agent；必要时调用产品经理或架构师 |
| `T1` | 纯文档、小型非行为配置，不改变运行行为或公共接口 | 开发 -> 审核；用户可见结果再增加验收 |
| `T2` | 功能、缺陷、重构、测试或行为配置变更 | 产品经理 -> 开发 -> 测试 -> 审核 -> 验收 |
| `T3` | 跨模块、公共接口、数据迁移、权限安全、并发或重大性能变更 | 产品经理 -> 架构师 -> 开发 -> 测试 -> 审核 -> 验收 |

影响范围无法确定、回滚代价高、缺少自动化验证、涉及敏感数据，或用户明确要求更严格流程时，
主 Agent 可以提升任务等级。不得为降低成本而跳过当前等级的必经角色。

项目特殊规范可以增加门禁或提高任务等级，但除非用户明确要求，不得弱化本节公共门禁。

## 17.3 任务单与版本

所有进入开发阶段的任务都必须有版本化任务单，版本格式为 `TASK-v1`、`TASK-v2`，并使用 `AC-001`、
`AC-002` 等稳定编号记录 Given/When/Then 验收标准：

- `T1`：主 Agent 生成轻量任务单，至少包含目标、范围、非目标、变更文件范围和验收标准。若发现行为影响
  或高影响歧义，必须升级为 `T2` 并交由产品经理重建任务单。
- `T2` 和 `T3`：由产品经理生成完整任务单。
- `T0`：不进入开发阶段，交接中的输入版本使用实际读取快照或 `N/A`，不得伪造任务单。

任务单进入开发阶段即冻结。冻结后遵循以下规则：

1. 开发、测试、审核和验收必须在交接中声明输入的任务单版本。
2. 澄清措辞但不改变可观察结果时，可以补充说明而不升级版本。
3. `T1` 的非行为范围、约束或验收标准变化由主 Agent 生成新版本；出现行为影响或高影响歧义时升级
   为 `T2`，由产品经理重建任务单。`T2`、`T3` 的变化始终由产品经理生成新版本。
4. 新版本发布后，旧版本的测试、审核和验收结论全部失效。
5. 高影响歧义、互斥验收标准或缺少用户决策时，产品经理返回 `blocked`，由主 Agent 询问用户。

## 17.4 阶段门禁与回退

正向门禁：

1. 产品门禁：任务单状态为 `completed`，且不存在高影响待确认项。
2. 架构门禁：`T3` 方案状态为 `completed`，关键接口、迁移、风险和测试重点明确。
3. 开发门禁：实现完成，相关模块文档已同步，并有基础验证证据。
4. 测试门禁：所有必需 AC 均有用例映射，阻断测试通过，覆盖缺口已明确。
5. 审核门禁：审核结论为 `APPROVED`，不存在阻断问题。
6. 验收门禁：验收结论为 `ACCEPTED`，每个必需 AC 均为 `PASS`。

只有当前门禁满足后，主 Agent 才能进入下一阶段。没有证据的“应该通过”不构成门禁通过。

失败回退：

| 失败位置 | 回退目标 | 重新执行范围 |
| --- | --- | --- |
| 开发发现需求冲突 | 产品经理 | 生成新任务单版本，再从开发阶段开始 |
| 开发发现架构不可实施 | 架构师 | 修订方案，再从开发阶段开始 |
| 测试失败 | 开发 | 修复后重新运行受影响测试和完整后续门禁 |
| 审核要求修改 | 开发 | 修改后重新测试、审核和验收 |
| 验收发现实现不符 | 开发 | 修改后重新测试、审核和验收 |
| 验收发现需求缺陷 | 产品经理 | 生成新任务单版本，并使旧结论失效 |

只有用户可以明确豁免未通过项。主 Agent 必须记录豁免内容和影响，不得让子 Agent 自行批准豁免。

## 17.5 并发与写入隔离

主 Agent 是唯一调度者，必须先建立任务图，再按依赖和权限批次派生角色。并发上限如下：

| 资源 | 上限 | 说明 |
| --- | --- | --- |
| 子 Agent 线程 | 6 | 来自 `.codex/config.toml`，主线程不计入；平台实际容量更低时以实际值为准 |
| 只读批次 | 6 | 输入稳定且依赖满足的只读节点可以同时运行 |
| 隔离写入工作包 | 3 | 仅在 Git、路径和资源隔离资格全部通过时启用 |
| 主工作树集成写入者 | 1 | 只允许一个集成者向主工作树应用补丁 |

### 17.5.1 TaskGraph 与 WorkPackage 契约

每次执行都必须有可复核的 `TaskGraph`。没有显式图时，主 Agent 自动把现有生命周期转换成线性图，
以保持原有顺序执行兼容路径；线性图不自动获得并发资格。`limits` 至少包含只读 6、隔离写入 3 和主树
集成者 1；`metrics` 至少记录峰值线程数、峰值写入包数、队列时间和降级原因。图至少记录以下字段：

| 契约 | 必填字段 |
| --- | --- |
| `TaskGraph` | `plan_revision`、`task_version`、`workflow_id`、`run_id`、`input_snapshot`、
  `input_snapshot_id`、`limits`、`nodes`、`batches`、`status`、`metrics`、`events` |
| 节点 | `workflow_id`、`task_version`、`node_id`、`role`、`stage`、`depends_on`、`required`、`acceptance_refs`、
  `handoff_ref`、
  `requested_mode`、`effective_mode`、`permission_class`、`priority`、`batch_id`、`attempt`、
  `thread_id`、`outcome`、`work_package_id`、`resource_claims`、`status`、`started_at`、`ended_at`、
  `event_refs`、`evidence_refs`、
  `reason_code` |
| `WorkPackage` | `work_package_id`、`workflow_id`、`target`、`read_scope`、`write_scope`、`ephemeral_scope`、
  `acceptance_refs`、`upstream_dependencies`、`downstream_dependencies`、`handoff_ref`、
  `input_snapshot`、`input_snapshot_id`、`input_manifest_sha256`、`input_tree_oid`、`head_snapshot`、
  `head_sha`、`branch_ref`、`worktree_path`、`upstream_patch_shas`、`output_patch_path`、
  `output_patch_sha256`、`resource_claims`、`file_manifest`、`actual_file_manifest`、`patch_digest`、
  `qualification`、`status` |

`limits.child_threads` 是本次图允许的活动子线程上限，默认等于配置的 6，主线程不计入。队列事件至少记录
`node_id`、`event`、`queue_started_at`、`dequeued_at`、`active_child_threads`、`limits.child_threads`、
`reason_code`、`raw_error`、`retry_attempt` 和声明顺序；这些字段属于工作流证据，不要求平台提供同名接口。

`metrics`/事件必须显式记录 `peak_active_threads`、`peak_isolated_write_packages`、`queued_node_count`、
`queue_total_duration`、每个节点的 `queue_duration_by_node`、每个批次的 `batch_duration`，以及按
`resource`、`platform`、`qualification` 分类的降级计数、`degradation_category` 和
`degradation_reason_code`。容量错误的队列、
出队和重试事件必须保留 `raw_error`、`queue_started_at`、`dequeued_at` 和 `retry_attempt`。

`requested_mode` 和 `effective_mode` 只能使用 `READ_ONLY_PARALLEL`、`ISOLATED_WRITE`、
`SERIAL_SHARED_WRITE`、`MAIN_INTEGRATION_WRITE`。`permission_class` 必须明确为 `read-only` 或
`workspace-write`；`required` 是节点是否为当前任务必需的布尔值，`acceptance_refs` 和 `handoff_ref`
分别指向验收标准和冻结交接证据。`qualification` 只能使用 `PENDING`、`ELIGIBLE`、`INELIGIBLE`、
`NOT_APPLICABLE`。

节点状态只允许使用 `PLANNED`、`READY`、`QUEUED`、`RUNNING`、`SUCCEEDED`、`FAILED`、`BLOCKED`、
`REJECTED`、`INVALIDATED`、`CANCELLED`。只有全部 `depends_on` 节点成功时节点才可从 `PLANNED` 进入 `READY`；
达到资源上限的 `READY` 节点进入 `QUEUED`，获得槽位后进入 `RUNNING`。失败或阻断节点的后继节点必须
进入 `BLOCKED`；资格不满足或交接无效的节点进入 `REJECTED`；任务单版本升级时旧图及其测试、审核、
验收结论必须进入 `INVALIDATED`。

节点失败或阻断后，主 Agent 必须沿依赖图递归阻塞所有后继，并为每次传播写入 `events`、`event_refs`、
`reason_code`、传播时间和目标节点证据。不依赖失败节点且资格通过的独立节点/分支可以继续运行；optional
节点失败只记录事件和证据，不改变必需结果。`TaskGraph` 聚合状态只有在所有 `required=true` 节点以及最终
集成、集成测试、最终审核、验收和清理门禁均为 `SUCCEEDED` 时才可为 `SUCCEEDED`；任一 required 节点
`FAILED` 时聚合为 `FAILED`，任一 required 节点 `BLOCKED` 时聚合为 `BLOCKED`，任务单版本升级时聚合为
`INVALIDATED`。聚合结论和 required/optional 判定必须写入 `events` 和 `evidence`。

### 17.5.1.1 执行前图校验

在任何节点进入 `RUNNING`、任何工具派生或任何分支启动前，主 Agent 必须完成图结构预检：所有 `node_id`
必须唯一；每个 `depends_on` 必须引用存在的节点；节点不得依赖自身。预检使用 Kahn 拓扑校验：为全部节点
计算入度，反复处理入度为 0 的节点并删除其出边，最后比较已处理节点数与图节点总数。

重复 ID、悬空依赖、自依赖或 Kahn 校验发现的任意循环（包括多节点环）都必须使整个 `TaskGraph` 进入
`REJECTED`，记录 `reason_code`（`DUPLICATE_NODE_ID`、`MISSING_DEPENDENCY`、`SELF_DEPENDENCY` 或
`DEPENDENCY_CYCLE`）和 `evidence`（输入图快照、节点/依赖清单、Kahn 已处理数与未处理节点）；不得只拒绝
局部节点，也不得让其他分支先启动。只有预检通过后，节点才可进入 `READY` 并生成首个批次。

主 Agent 使用拓扑排序生成批次，并且一个批次只能包含同一 `permission` 类别。`read-only` 与
`workspace-write` 绝不能在同一批次混合；切换权限类别前必须等待上一批次结束并设置屏障。派生任何只读
角色前，父任务实时权限必须先切为只读并在派生后复核；权限无法收紧时记录 `PERMISSION_NOT_READONLY`
并停止该并发批次。节点的 `resource_claims`（端口、数据库、容器、外部服务或其他共享资源）必须
互斥或有明确命名空间；否则记录 `UNISOLATED_RESOURCE` 并串行降级。

### 17.5.2 资格检查、队列与串行降级

隔离写入并发只能在以下条件同时满足时启用：主工作树是 Git 仓库且状态干净；工作包的 `write_scope`
互不重叠；资源可隔离；工作树创建成功；不存在不安全的子模块或 Git 过滤器写入；平台剩余容量满足
当前批次。超过上限的第 7 个只读节点或第 4 个隔离写入工作包必须保留在 `QUEUED`，不得偷偷超额派生。

实际派生工具返回 `agent thread limit reached` 或等价平台容量错误时，主 Agent 不得把节点标记为
`FAILED`、丢弃节点或跳过后继。必须将节点转为 `QUEUED`，记录 `THREAD_LIMIT` 或 `PLATFORM_CAPACITY`、
排队开始时间和未经改写的 `raw_error`；活动子线程数低于 `limits.child_threads` 后，按图中声明顺序重新派生，
递增 `retry_attempt` 并记录出队时间和出队事件。重复容量错误继续留在 `QUEUED` 并追加事件；其他非容量错误
才按失败传播规则处理。

Codex 平台不保证提供原生 `QUEUED` 状态或持久队列，因此上述 `QUEUED`、排队/出队时间和事件日志由工作流
层维护，平台返回错误只作为原始证据保存。工作流层的兼容队列不得被描述成平台已经接受或后台保留了该节点。

除上述可恢复的容量排队外，其他资格失败必须记录一个稳定原因码，并自动退回线性串行路径：

| 原因码 | 触发条件 |
| --- | --- |
| `THREAD_LIMIT` | 子线程达到会话上限 |
| `ISOLATED_WRITE_LIMIT` | 隔离写入工作包达到 3 个上限 |
| `RESOURCE_LOCK` | 资源已被其他节点锁定 |
| `TASK_VERSION_MISMATCH` | 节点输入任务单版本与当前图不一致 |
| `HANDOFF_INVALID` | 上游交接缺字段、非法枚举或证据引用失效 |
| `PARENT_PERMISSION_UNAVAILABLE` | 父任务无法提供所需实时权限 |
| `UNSUPPORTED_GIT_STATE` | 当前 Git 状态、子模块或过滤器不支持隔离 |
| `DIRTY_INPUT_UNSAFE` | 输入快照包含未授权改动，不能安全复用 |
| `WRITE_SCOPE_OVERLAP` | 两个工作包写入范围相交 |
| `IGNORED_WRITE_SCOPE` | 写入范围被忽略规则隐藏或无法纳入补丁证据 |
| `PATH_ESCAPE` | 实际路径逃逸工作包绝对路径 |
| `RESOURCE_CONFLICT` | 资源声明相冲突或无法命名空间隔离 |
| `MAIN_TREE_CHANGED` | 集成前主工作树相对快照发生变化 |
| `OUT_OF_SCOPE_WRITE` | 实际写入文件超出 `write_scope` |
| `PATCH_CHECK_FAILED` | 受限补丁未通过 `git apply --check` 或无法应用 |
| `DEPENDENCY_FAILED` | 前置节点失败，当前节点无法执行 |
| `VERSION_INVALIDATED` | 任务单升级使当前节点或证据失效 |
| `DUPLICATE_NODE_ID` | 图中存在重复的 `node_id` |
| `MISSING_DEPENDENCY` | `depends_on` 引用了不存在的节点 |
| `SELF_DEPENDENCY` | 节点依赖自身 |
| `DEPENDENCY_CYCLE` | Kahn 校验发现一个或多个依赖环 |
| `DIRTY_WORKTREE` | 主工作树存在未授权或未记录的改动（兼容别名） |
| `NON_GIT_REPOSITORY` | 当前目录不是可用 Git 仓库（兼容别名） |
| `OVERLAPPING_WRITE_SCOPE` | 写入范围相交（兼容别名） |
| `UNISOLATED_RESOURCE` | 资源没有独立命名空间（兼容别名） |
| `WORKTREE_CREATE_FAILED` | 隔离 worktree 无法按输入快照创建（兼容别名） |
| `UNSAFE_GIT_LAYOUT` | Git 布局无法安全隔离（兼容别名） |
| `PLATFORM_CAPACITY` | 平台容量不足（兼容别名） |
| `PERMISSION_NOT_READONLY` | 只读派生前父任务权限无法收紧（兼容别名） |
| `PATH_SCOPE_VIOLATION` | 实际写入文件越界（兼容别名） |
| `MAIN_TREE_DRIFT` | 主树漂移（兼容别名） |
| `PATCH_CONFLICT` | 补丁冲突（兼容别名） |
| `INPUT_SNAPSHOT_MISMATCH` | 输入或 HEAD 快照不一致（兼容别名） |

串行降级必须把原因码写入 `TaskGraph.metrics` 和交接证据；降级不是失败，也不能宣称并发验证已通过。
若线性路径自身失败，仍按 17.4 的阶段回退规则处理。

### 17.5.3 隔离 worktree 与 commitless 集成

隔离写入只由主 Agent 创建 worktree，路径固定为仓库绝对路径下的
`.codex/worktrees/<run_id>/<work_package_id>`，并使用 detached HEAD。主 Agent 在派生前记录输入
`HEAD`、任务单版本、输入文件快照和 `read_scope`/`write_scope`；子 Agent 必须在该绝对路径中工作。

集成节点必须显式依赖所有 `required=true` 工作包的包级开发、包级测试、补丁封装和包级审核节点。只有这些
节点全部为 `SUCCEEDED` 时，`required_package_barrier` 才能通过；任一必需包为 `FAILED`、`BLOCKED`、`QUEUED`
或 `INVALIDATED` 时，集成节点必须保持 `QUEUED` 或 `BLOCKED`，不得创建预览补丁、不得运行组合补丁校验、
不得写入主工作树。该屏障必须记录 required 工作包清单、各门禁状态、依赖节点和 `evidence_refs`。

子 Agent 不得创建、修改或删除 Git 元数据，不得执行 `commit`、`push`、`branch`、`worktree`、`stash`、
`reset` 或 `clean`，也不得扩大工作包范围。路径级写入限制不是 Codex 沙箱提供的硬锁，必须由主 Agent
复核实际文件清单；越界写入立即以 `PATH_SCOPE_VIOLATION` 终止该工作包。

工作包完成后，主 Agent 必须核对输入和 `HEAD` 快照、`write_scope`、实际文件清单及每个文件的 SHA-256，
对新文件先执行 intent-to-add，再导出限定范围的 `git diff --binary --full-index` 并记录补丁 SHA-256。
required package barrier 通过后，主 Agent 才能在预览 worktree 按拓扑顺序组合补丁并执行 `git apply --check`；
随后校验主工作树输入快照未变化，再由唯一集成者一次应用组合补丁。主树漂移记录 `MAIN_TREE_CHANGED`，
冲突或检查失败记录 `PATCH_CHECK_FAILED`，两者都必须停止集成并保留 worktree、补丁、快照和日志证据，不得
自动解决或提交。集成证据必须包含 `required_package_barrier`、预览校验结果、主树快照比较和单一集成事件。

集成完成后才能运行集成测试、最终审核和验收。成功后仅清理 `TaskGraph` 中登记的临时 worktree；失败时
保留现场。该流程是主 Agent 的 commitless 协作约束，不是平台提供的路径级锁或自动合并能力。

### 17.5.4 角色、T0 与兼容边界

开发和测试可以在不同工作包中并行，但每个工作包仍需独立通过包级门禁；主树集成、集成测试和最终门禁
保持单写入者。测试角色的写入范围仍仅限测试代码、夹具、测试数据和测试专用配置。六个角色配置必须
保持 `[agents] enabled = false`，不得继续派生下级 Agent；模型、推理强度和沙箱默认值不因本次并发改造
改变。

`T0` 在任何工具调用前仍必须确认父任务实时权限为只读，并记录执行前后工作树快照；发现差异不得宣称
完成。角色文件未覆盖的审批策略、MCP、技能或网络工具权限继承父会话，连接器权限仍按具体工具生效。

## 17.6 统一交接协议

所有子 Agent 使用中文，先返回以下公共字段：

```text
任务：
输入版本：
状态：completed | blocked
结论：
证据：
变更文件：
风险或阻塞：
下一步：
```

证据必须是可复核事实，例如文件和行号、执行命令与退出状态、测试报告、日志或截图。计划、推测、
其他角色的口头结论不能单独作为通过证据。

主 Agent 在接受交接前必须执行结构校验：

1. 八个公共字段必须使用上述精确标签，不能改名、合并或省略。
2. `状态`、审核结论、验收结论和逐项 AC 结果必须属于规定枚举。
3. `输入版本` 必须与当前有效任务单或只读快照一致，岗位专属内容必须完整。
4. 交接不合格时不得进入下一门禁；主 Agent 应要求同一角色补全一次，仍不合格则记为 `blocked`。
5. 主 Agent 汇总时可以压缩措辞，但必须保留原始角色结论和证据的可追溯性。
6. 派生下游角色时，主 Agent 必须传入完整的上游有效交接正文，或提供下游可读取且内容冻结的明确引用；
   只传任务编号、摘要或结论不构成有效输入，下游必须返回 `blocked`。

各岗位随后补充：

- 产品经理：目标、用户场景、范围、非目标、约束、风险、依赖、待确认项和编号验收标准。
- 架构师：方案、模块边界、接口与数据流、兼容或迁移策略、安全与性能风险、回滚和测试重点。
- 开发：实现摘要、技术决策、AC 映射、验证结果、方案偏差和残余风险。
- 测试：测试环境、用例与 AC 映射、结果、失败复现、回归范围、测试资产和覆盖缺口。
- 审核：`APPROVED`、`CHANGES_REQUIRED` 或 `BLOCKED`，以及按严重性排序的文件与行号证据。
- 验收：`ACCEPTED`、`REJECTED` 或 `BLOCKED`，以及每条 AC 的 `PASS`、`FAIL` 或 `BLOCKED` 证据。

## 17.7 最终交付

主 Agent 汇总各阶段的最终有效版本，向用户报告实际完成内容、验证证据、未完成或豁免项、残余风险，
以及被修改的文档。主 Agent 对最终陈述的准确性负责，不得简单转发子 Agent 的未经核验结论。
