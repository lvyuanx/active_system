任务：TASK-v7“移除登录后顶部 Header、强化底部导航选中态”只读最终审核
输入版本：TASK-v7
状态：completed
结论：APPROVED。未发现 P0/P1/P2 问题或任务引入的行为回归。
证据：

- 已读取 `TASK-v7.md`、DEVELOPMENT-HANDOFF-v7、TESTING-HANDOFF-v7、BROWSER-EVIDENCE-v7 与
  `apps/user-web/AGENTS.md`。
- `index.vue:18-32` 的登录后分支只渲染活动壳、RouterView 和 Tabbar；`index.vue:35-43` 仍保留认证页
  `login-hero`。
- `index.vue:126-130` 根据响应式 `route.path` 派生 active 索引；三个命名路由目标与本地 Vant 4.10
  `TabbarItem` 的 `$route.matched` 名称匹配逻辑一致。
- `activity.css:120-129`、`chat.css:1-10` 分别处理顶部 safe-area、Tabbar 高度与聊天可用高度；
  `activity.css:342-372` 为选中项设置金色图标/文字、700 字重、背景和边框。
- 已复跑 `pnpm --filter @active/user-web typecheck`、`pnpm --filter @active/user-web build` 及限定范围
  `git diff --check`，均退出码 0。
- 模块和项目文档与当前代码、测试交接相符。

变更文件：无（只读审核）。
风险或阻塞：无阻断。未存档专门的 v7 PNG，且未模拟真机 safe-area；测试交接保留浏览器 DOM/交互测量，
不影响本版审核通过。
下一步：由 acceptance_owner 按 AC-001 至 AC-008 逐条验收。
