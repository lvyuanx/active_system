任务：抽奖时沉浸式球体与揭晓后恢复
输入版本：TASK-v10；开发输入：DEVELOPMENT-HANDOFF-v10
状态：completed
结论：实现通过自动化回归、类型检查、生产构建、差异校验和本地页面检查。
证据：

- `pnpm --filter @active/screen-web test`：退出码 0，包含沉浸式状态、恢复计时和辅助文字隐藏断言。
- `pnpm --filter @active/screen-web typecheck`：退出码 0。
- `pnpm --filter @active/screen-web build`：退出码 0。
- `git diff --check`：退出码 0。
- 代码检查确认沉浸式规则覆盖 Header、标题、奖项板、底部信息和球体 caption；恢复路径设置 `activeRound.value = undefined`。

变更文件：测试阶段未新增生产代码或测试资产；使用开发阶段已更新的静态断言。
风险或阻塞：未通过真实管理端点击执行开奖，避免改变用户活动数据；阶段逻辑由源码断言、类型检查和生产构建覆盖。
下一步：进入只读代码审核。
