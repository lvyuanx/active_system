任务：TASK-v1 修复活动管理侧栏被内容撑高（测试阶段）
输入版本：TASK-v1；DEVELOPMENT-HANDOFF-v1；管理端共享主工作树
状态：completed
结论：AC-001 至 AC-004 的实现证据和管理端基础验证通过；未修改活动业务流程。桌面规则与移动断点覆盖均已静态确认。
证据：
- AC-001/AC-002：`apps/admin-web/src/styles/index.css:242-250` 通过 `align-self: start`、固定视口高度和 `position: sticky` 解耦侧栏与右侧网格行高，并允许侧栏自身滚动。
- AC-003：`apps/admin-web/src/styles/index.css:382-389` 将侧栏恢复为移动端单列普通流和自然高度。
- AC-004：`pnpm --filter @active/admin-web typecheck` 和 `pnpm --filter @active/admin-web build` 均退出码 0；`git diff --check` 退出码 0。
- 本地管理端 `http://localhost:5173/` 加载后按路由守卫显示登录页，浏览器控制台错误数为 0；未提交或读取任何登录凭据。
变更文件：无测试资产变更；沿用开发阶段的 CSS 静态断言和构建验证。
风险或阻塞：未使用已登录活动页面执行真实滚动截图，原因是当前会话没有可用于该本地页面的登录态；CSS 规则、断点覆盖和生产构建证据完整。
下一步：交审核和验收阶段，并保留上述真实浏览器覆盖缺口说明。

