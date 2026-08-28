任务：TASK-v1 修复活动管理侧栏被内容撑高（验收阶段）
输入版本：TASK-v1；TESTING-HANDOFF-v1；REVIEW-HANDOFF-v1
状态：completed
结论：ACCEPTED。AC-001、AC-002、AC-003、AC-004 均 PASS；桌面侧栏不再受右侧长内容的网格行高影响，移动端仍保持自然高度，管理端验证通过。
证据：
- AC-001 PASS：`apps/admin-web/src/styles/index.css:245-250` 显式取消网格行拉伸并将侧栏高度限定为 `100dvh - 32px`。
- AC-002 PASS：同一规则使用 `position: sticky; top: 16px`，侧栏账户区域继续位于固定高度的 flex 容器内。
- AC-003 PASS：`apps/admin-web/src/styles/index.css:382-389` 在 800px 断点覆盖固定高度和粘性定位。
- AC-004 PASS：管理端 typecheck、生产 build、CSS 静态断言和 `git diff --check` 均退出码 0。
变更文件：无验收阶段写入。
风险或阻塞：真实登录态滚动截图未执行；源代码规则和构建验证已覆盖实现，保留该非阻断证据缺口。
下一步：执行清理门禁并结束 TASK-v1。

