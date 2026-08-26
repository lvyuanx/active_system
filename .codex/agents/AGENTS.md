# 子 Agent 模块说明

## 模块简介

本目录定义项目级 Codex 自定义子 Agent。每个 TOML 文件对应一个软件交付岗位，由主 Agent 根据
根级 `AGENTS.md` 中的通用任务分级和门禁流程调用。

## 主要职责

- 为每个岗位固定职责、模型、推理强度、沙箱权限和输出契约。
- 让阶段交接可验证，避免产品、实现、测试、审核和验收职责混杂。
- 通过任务图、权限同质批次和隔离工作包提高并发，同时保留单一主树集成者。

## 目录说明

| 文件 | 岗位 | 模型与推理强度 | 沙箱 |
| --- | --- | --- | --- |
| `product_manager.toml` | 产品经理 | `gpt-5.6-luna` / `max` | `read-only` |
| `solution_architect.toml` | 架构师 | `gpt-5.6-sol` / `max` | `read-only` |
| `developer.toml` | 开发 | `gpt-5.6-luna` / `max` | `workspace-write` |
| `tester.toml` | 测试 | `gpt-5.6-luna` / `max` | `workspace-write` |
| `reviewer.toml` | 审核 | `gpt-5.6-sol` / `xhigh` | `read-only` |
| `acceptance_owner.toml` | 验收 | `gpt-5.6-luna` / `max` | `read-only` |

项目级线程上限位于上一级 `.codex/config.toml` 的 `[agents] max_threads`。角色文件会从
`.codex/agents/*.toml` 自动发现；当前会话最多运行 6 个子线程，主线程不计入；只读批次最多 6 个，
隔离写入工作包最多 3 个，主工作树集成者最多 1 个。

## 核心接口

每个角色文件必须定义：

- `name`：稳定、唯一的调用标识。
- `description`：供 Codex 判断何时选择该角色。
- `developer_instructions`：岗位边界、工作流程和输出契约。
- `model` 与 `model_reasoning_effort`：角色模型配置；不可用时必须显式调整并重新验证。
- `sandbox_mode`：文件系统权限。

角色 TOML 不得添加 `[agents] enabled`。禁止角色继续派生子 Agent 由角色指令和主 Agent 调度门禁共同保证。

所有角色共享 `任务`、`输入版本`、`状态`、`结论`、`证据`、`变更文件`、`风险或阻塞`、
`下一步` 八个交接字段，并在其后追加岗位专属内容。字段标签不得改名、合并或省略；主 Agent 在进入
下一门禁前负责校验字段、枚举、输入版本和岗位专属内容。

## TaskGraph 与 WorkPackage

主 Agent 是唯一调度者。每次执行都建立 `TaskGraph`，至少包含 `plan_revision`、`task_version`、
`workflow_id`、`run_id`、`input_snapshot`、`input_snapshot_id`、`limits`、`nodes`、`batches`、`status`、
`metrics` 和 `events`。节点包含 `workflow_id`、`task_version`、`required`、`acceptance_refs`、`handoff_ref`、
`requested_mode`、`effective_mode`、`permission_class`、`priority`、`batch_id`、`attempt`、`thread_id`、
`outcome`、资源声明、状态、时间戳、证据引用和原因码；节点状态固定为 `PLANNED`、`READY`、`QUEUED`、
`RUNNING`、`SUCCEEDED`、`FAILED`、`BLOCKED`、`REJECTED`、`INVALIDATED`、`CANCELLED`。

节点失败或阻断时递归阻塞所有后继；不依赖该节点且资格通过的独立分支可以继续。optional 节点失败只记录
event/evidence，不改变必需结果。TaskGraph 只有所有 `required=true` 节点和最终集成、集成测试、审核、验收、
清理门禁均 `SUCCEEDED` 才能聚合为 `SUCCEEDED`；required `FAILED`、`BLOCKED` 或版本升级分别聚合为
`FAILED`、`BLOCKED`、`INVALIDATED`。

写入节点必须携带 `WorkPackage`：`work_package_id`、`workflow_id`、`target`、`read_scope`、`write_scope`、
`ephemeral_scope`、`acceptance_refs`、`upstream_dependencies`、`downstream_dependencies`、`handoff_ref`、
`input_snapshot_id`、`input_manifest_sha256`、`input_tree_oid`、`head_sha`、`branch_ref`、`worktree_path`、
`upstream_patch_shas`、`output_patch_path`、`output_patch_sha256`、资源声明、`actual_file_manifest`、
`file_manifest`、补丁摘要、`qualification` 和状态。执行模式只能使用
`READ_ONLY_PARALLEL`、`ISOLATED_WRITE`、`SERIAL_SHARED_WRITE`、`MAIN_INTEGRATION_WRITE`；资格只能使用
`PENDING`、`ELIGIBLE`、`INELIGIBLE`、`NOT_APPLICABLE`。工作包只能在主 Agent 创建的仓库绝对路径
`.codex/worktrees/<run_id>/<work_package_id>` 中以 detached HEAD 运行。子 Agent 不得创建、修改或删除
Git 元数据，不得提交、推送、切换分支或管理 worktree。

`metrics`/事件必须记录 `peak_active_threads`、`peak_isolated_write_packages`、`queued_node_count`、
`queue_total_duration`、`queue_duration_by_node`、`batch_duration`、`degradation_category` 和
`degradation_reason_code`，并按资源、平台、资格分类统计降级。
在任何节点运行前，主 Agent 必须以 Kahn 算法校验唯一 `node_id`、存在的依赖和无自依赖；重复 ID、悬空依赖、
自依赖或任意环使整个图 `REJECTED`，记录原因码与输入图、依赖清单和校验结果 evidence，不得启动其他分支。

主 Agent 通过拓扑依赖生成批次，批次不得混合 `read-only` 与 `workspace-write`。第 7 个只读节点和第 4
个隔离写入工作包进入 `QUEUED`；达到上限分别记录 `THREAD_LIMIT` 或 `ISOLATED_WRITE_LIMIT`。实际派生工具
返回 `agent thread limit reached` 或等价平台容量错误时，节点必须保留为 `QUEUED`，记录
`THREAD_LIMIT`/`PLATFORM_CAPACITY`、`queue_started_at`、原始 `raw_error` 和重试次数；活动子线程低于
`limits.child_threads` 后按声明顺序重试并记录 `dequeued_at` 和出队事件，不得标记失败或丢弃节点。
平台可能没有原生 `QUEUED` 状态，排队和事件由工作流层维护；其他资格失败才记录完整原因码并自动串行降级，
线性输入继续使用原有顺序流程。

图预检失败使用 `DUPLICATE_NODE_ID`、`MISSING_DEPENDENCY`、`SELF_DEPENDENCY` 或 `DEPENDENCY_CYCLE`，
并将整个图标记为 `REJECTED`；预检 evidence 必须包含输入图、依赖清单和 Kahn 处理结果。

主 Agent 在包完成后核对实际文件清单和 SHA-256，必要时对新文件执行 intent-to-add，导出
`git diff --binary --full-index` 并记录补丁摘要；先在预览 worktree 执行 `git apply --check`，再由唯一
集成者应用到主树。越界、主树漂移或冲突必须停止集成并保留证据。该路径级约束由调度流程复核，不是
Codex 沙箱提供的硬锁。

集成节点必须等待所有 `required=true` 工作包的包级测试、补丁封装和审核节点成功，形成
`required_package_barrier`。必需包为 `FAILED`、`BLOCKED`、`QUEUED` 或 `INVALIDATED` 时，集成节点保持
`QUEUED` 或 `BLOCKED`，不得创建预览补丁或写主树；屏障成功后才可按拓扑组合补丁，校验主树快照并由单一
集成者一次应用，证据须包含工作包清单和门禁状态。

## 主要流程

1. 主 Agent 读取项目规范并判断 `T0` 至 `T3` 任务等级，冻结任务单和输入快照。
2. 主 Agent 为 `T1` 建立轻量任务单，产品经理为 `T2`、`T3` 建立完整任务单；`T3` 再由架构师生成方案。
3. 主 Agent 将可独立节点按拓扑关系分成同权限批次；只读批次最多 6 个，隔离写入批次最多 3 个。
4. 工作包分别完成开发、包级测试和包级审核后，由唯一集成者验证并应用 commitless 补丁。
5. 集成后执行集成测试、最终审核和验收；验收负责人逐条验证产品标准，主 Agent 汇总最终结论。
6. 任一节点或门禁失败时，按根级 `AGENTS.md` 的失败传播和回退规则处理；无图或资格失败时走线性路径。

## 依赖关系与数据流

角色之间不直接修改对方的输出。主 Agent 将上游的最终有效交接正文或可读取的冻结引用作为下游输入，
并负责版本选择；不得只传任务编号、摘要或结论：

```text
用户请求
  -> 产品任务单
  -> 架构方案（T3）
  -> 开发交接与工作树
  -> 测试报告
  -> 审核结论
  -> 验收结论
  -> 主 Agent 最终交付
```

## 配置说明

- `.codex/config.toml` 的 `[agents]` 仅使用当前版本支持的 `max_threads`；不要写入 `enabled`、
  `max_concurrent_threads_per_session` 或默认子 Agent 模型字段。
- `.codex/agents/*.toml` 是自动发现的角色配置文件，文件内不要再嵌套 `[agents]` 表。
- `read-only` 是四个只读角色的默认沙箱；主 Agent 派生前还必须把父任务实时权限设为只读。
- 主 Agent 自行执行 `T0` 时也必须在首次工具调用前确认父任务实时权限为只读，并核对前后工作树。
- `developer` 可以在指定工作包中修改任务范围内的生产代码、测试和相关文档，并交付包级补丁证据。
- `tester` 的 `workspace-write` 仅用于测试资产和测试专用配置；该限制由指令、工作包和主 Agent 的变更清单
  复核实现。
- 同一 `WorkPackage` 内测试必须等待开发完成且不得与该包生产写入重叠；不同且互斥的隔离 worktree 工作包可
  并行进行包级开发和测试；主工作树集成测试必须在唯一集成者完成后单独运行。
- 角色文件未配置独立审批策略、MCP、技能或网络工具权限，这些能力继承父会话；连接器权限按具体工具生效。
- 模型不可用时必须显式修改对应 TOML，并重新验证，不允许运行时静默替换。

## 扩展方式

新增角色时必须：

1. 确认新职责无法自然归入现有岗位，避免角色重复。
2. 创建名称匹配的独立 TOML，补齐所有核心字段和中文交接要求。
3. 选择最小必要沙箱权限；写入角色必须纳入工作包和单一主树集成者规则。
4. 在本文件、根级 `AGENTS.md`、`README.md` 和 `WIKI.md` 中同步角色与公共路由。
5. 解析 TOML，并在新 Codex 会话中验证发现、模型、权限和输出格式。

## 注意事项

- `.codex/agents/` 中的 TOML 是可执行配置，不是仅供阅读的角色说明。
- 公共生命周期规则属于根级 `AGENTS.md`；`PROJECT_AGENTS.md` 只补充当前项目特殊约束。
- 角色指令不能替代平台沙箱。无法由沙箱表达的路径级约束必须由主 Agent 复核。
- 父任务的实时权限在派生时优先于角色沙箱默认值；只读角色必须在只读父任务下运行。无法收紧时必须
  记录 `PERMISSION_NOT_READONLY` 并串行降级。
- 自定义岗位使用隔离或有限上下文派生；完整历史派生会继承父 Agent 类型。
- 结构不完整的角色交接不得进入下一门禁；补全一次仍不合格时由主 Agent 标记为 `blocked`。
- 隔离派生不会自动获得上游对话；主 Agent 必须显式传入完整交接正文或可读取的冻结引用。
- 任务单升级后，不得继续使用旧版本测试、审核或验收结论。
- 修改角色职责、模型、权限或数据流时，必须同步维护本文件。
