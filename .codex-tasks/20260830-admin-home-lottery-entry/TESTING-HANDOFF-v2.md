任务：验证管理端首页“打开抽奖大屏”入口
输入版本：TASK-v2 + DEVELOPMENT-HANDOFF-v2
状态：completed
结论：类型检查、生产构建、静态行为断言和 diff 检查均通过；按钮始终展示于活动卡片 footer，活动 ID 查询参数和新标签页打开逻辑已覆盖。
证据：

- `pnpm --filter @active/admin-web typecheck`：退出码 0。
- `pnpm --filter @active/admin-web build`：退出码 0；仅有依赖纯函数注释和 chunk 体积提示。
- 首页静态断言：检查“打开抽奖大屏”、`VITE_SCREEN_WEB_BASE_URL`、默认端口、活动 ID 查询参数、`window.open` 新标签页参数以及 footer `@click.stop`，退出码 0。
- `git diff --check`：退出码 0；仅报告现有工作树文件的换行符提示。

变更文件：

- 无；测试阶段仅读取源码并执行类型/构建检查。

风险或阻塞：未输入管理员凭据进行真实浏览器点击；运行时验证可在启动管理端和大屏服务后补充，不影响当前源码和构建证据。
下一步：交由审核阶段复核实现范围和既有行为。
