任务：TASK-v7 主工作树集成复核
输入版本：TASK-v7
状态：completed
结论：主工作树集成复核通过；本任务因输入工作树含用户既有未提交改动，采用 SERIAL_SHARED_WRITE，未创建或应用隔离补丁。
证据：

- 开发交接中的目标文件已直接存在主工作树，且 `git diff --check` 通过（目标范围无空白错误）。
- `apps/user-web/src/router/index.ts`、`apps/user-web/src/api/client.ts` 和 `chat.vue` 未被 TASK-v7 改动；
  既有聊天室实现保持在输入基线中。
- 主工作树在测试、审核和验收阶段未发生超出任务范围的生产文件变更；临时验收环境使用独立端口和临时 env 文件。
- 测试完成后，临时前后端进程、临时 env 文件和浏览器标签均已清理；既有服务和用户工作树改动保留。

变更文件：无（集成复核只读）。
风险或阻塞：无。由于输入工作树非干净，未走隔离 worktree/补丁应用路径；该降级已在 TASKGRAPH-v7 的 `DIRTY_INPUT_UNSAFE` 证据中记录。
下一步：进入集成测试、最终审核和验收门禁。
