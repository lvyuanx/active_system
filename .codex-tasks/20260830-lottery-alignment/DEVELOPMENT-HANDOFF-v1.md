任务：修复管理端实时抽奖奖品行对齐
输入版本：TASK-v1
状态：completed
结论：已将奖品行的数量、启用和删除控件改为顶部对齐；奖项头部和既有响应式列布局保持不变。
证据：

- `apps/admin-web/src/views/lottery/lottery.css:72-106` 保留奖项头部的 `align-items: center`，并为 `.prize-row` 设置 `align-items: start`。
- `apps/admin-web/src/views/lottery/AGENTS.md:31-32` 已记录奖品行首行对齐和 800px/520px 断点约定。
- `pnpm --filter @active/admin-web typecheck`：退出码 0。
- `pnpm --filter @active/admin-web build`：退出码 0；仅有依赖注释和 chunk 体积提示。
- 样式静态断言：奖品行顶部对齐、奖项头部居中、800px/520px 断点和无旧的整行居中声明均通过，退出码 0。

变更文件：

- `apps/admin-web/src/views/lottery/lottery.css`
- `apps/admin-web/src/views/lottery/AGENTS.md`
- `.codex-tasks/20260830-lottery-alignment/TASK-v1.md`
- `.codex-tasks/20260830-lottery-alignment/TASKGRAPH-v1.json`

风险或阻塞：当前工作树已有此前未提交的抽奖及其它模块改动；本次未回退或覆盖无关改动。管理端实际路由需要登录，未在浏览器中输入凭据；浏览器安全策略拒绝了临时同构布局夹具，已由编译产物静态断言替代。
下一步：进入测试、审核和验收阶段。
