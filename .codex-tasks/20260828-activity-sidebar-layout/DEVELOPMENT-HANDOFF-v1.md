任务：TASK-v1 修复活动管理侧栏被内容撑高（开发阶段）
输入版本：TASK-v1；共享主工作树；输入 HEAD 42a0d840fa735ca72226c2d3534083a8946475da
状态：completed
结论：已完成最小布局修复。桌面侧栏取消 CSS Grid 默认行拉伸，固定为视口可用高度并采用顶部粘性定位；内容过长时侧栏自身可滚动。800px 及以下断点恢复普通流、自动高度和可见溢出。
证据：
- `apps/admin-web/src/styles/index.css:242-255` 新增 `align-self: start`、`position: sticky`、`top: 16px`、`height: calc(100dvh - 32px)` 和 `overflow-y: auto`。
- `apps/admin-web/src/styles/index.css:382-389` 在移动断点覆盖为 `position: static`、`height: auto`、`min-height: auto` 和 `overflow-y: visible`。
- `pnpm --filter @active/admin-web typecheck` 退出码 0；`pnpm --filter @active/admin-web build` 退出码 0。
- 受控 CSS 静态断言确认桌面规则及移动端覆盖规则均存在，退出码 0；`git diff --check` 退出码 0。
变更文件：
- `apps/admin-web/src/styles/index.css`
- `apps/admin-web/AGENTS.md`
- `MEMORY.md`
- `LEARNING.md`
- `WIKI.md`
- `.codex-tasks/20260828-activity-sidebar-layout/TASK-v1.md`
风险或阻塞：工作树包含其他任务的既有未提交改动，未创建隔离 worktree；本次仅修改上述侧栏规则和文档，没有改动业务代码。
下一步：交测试、审核和验收阶段。

