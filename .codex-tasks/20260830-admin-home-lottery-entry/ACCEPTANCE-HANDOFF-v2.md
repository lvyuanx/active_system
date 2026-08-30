任务：按用户场景验收管理端首页抽奖大屏入口
输入版本：TASK-v2 + DEVELOPMENT-HANDOFF-v2 + TESTING-HANDOFF-v2 + REVIEW-HANDOFF-v2
状态：completed
结论：ACCEPTED
证据：

- AC-001：PASS。`apps/admin-web/src/views/home/index.vue:103-106` 在每个活动卡片 footer 渲染“打开抽奖大屏”按钮，未添加状态条件。
- AC-002：PASS。`apps/admin-web/src/views/home/index.vue:272-275` 使用当前卡片 `activity_id` 写入大屏 URL，并在新标签页打开；footer 的 `@click.stop` 阻止卡片主体跳转。
- AC-003：PASS。既有 `openActivity`、生命周期按钮和管理端抽奖路由未被删除或改写；管理端 typecheck、生产 build、静态行为断言和 diff 检查均退出码 0。

变更文件：

- `apps/admin-web/src/views/home/index.vue`
- `apps/admin-web/src/views/home/AGENTS.md`
- `apps/admin-web/AGENTS.md`
- `.env.example`
- `README.md`
- `MEMORY.md`
- `WIKI.md`

风险或阻塞：无必需验收阻断；真实浏览器点击未执行，需在本地服务运行且管理员已登录时补充观察新标签页实际打开结果。
下一步：完成任务证据归档并向用户交付。
