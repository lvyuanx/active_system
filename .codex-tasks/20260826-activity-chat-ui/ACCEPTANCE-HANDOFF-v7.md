任务：按 TASK-v7 对“移除登录后顶部 Header、强化底部导航选中态”执行最终验收
输入版本：TASK-v7
状态：completed
结论：ACCEPTED；AC-001 至 AC-008 全部 PASS。
证据：

- 登录后活动壳不再渲染 `VanNavBar/activity-nav`；认证页保留 `login-hero`。
- `route.path` 响应式派生底部 active 索引，三个命名路由目标与 Vant route 模式匹配。
- `activity.css` 与 `chat.css` 保留顶部/底部 safe-area，移除旧 Header 高度并为 active 项提供金色、加粗、背景和边框。
- 主线程 In-app Browser 在 `430x932`、`390x450` 实测认证页、首页、聊天和“我的”页面；具体 DOM、computed style、
  路由和几何证据见 `BROWSER-EVIDENCE-v7.md` 与 `TESTING-HANDOFF-v7.md`。
- 点击导航、Back/Forward、直接访问及刷新均验证唯一 active 项与 URL 同步；聊天默认 Field/按钮均为 `44px`，
  四行输入 textarea `clientHeight=72`、`scrollHeight=96`，composer 始终位于 Tabbar 上方。
- `pnpm --filter @active/user-web typecheck`、`pnpm --filter @active/user-web build`、目标范围 `git diff --check`
  均退出码 0；页面控制台 warning/error 筛选为空。

逐条验收：

- AC-001：PASS，登录后首页、聊天、“我的”均 `headerCount=0`。
- AC-002：PASS，认证页 `loginHeroCount=1`，活动标识、上下文和标题正常。
- AC-003：PASS，直接访问及刷新三路由均仅对应项 active。
- AC-004：PASS，点击导航与浏览器前进/后退均同步路径和唯一 active。
- AC-005：PASS，active 项实测金色图标/文字、700 字重、背景和边框包裹，inactive 项弱化。
- AC-006：PASS，两组移动视口主体、composer 与 Tabbar 无重叠且无旧 Header 空白。
- AC-007：PASS，聊天区利用新增高度，输入最多三行并在超出后内部滚动。
- AC-008：PASS，API、Token、路由表、头像、聊天协议、历史锚点、条件滚动、重连和发送逻辑未被本任务改动。

变更文件：无（只读验收）。
风险或阻塞：无阻塞。未存档专门的 v7 PNG，未模拟真机 safe-area；保留为低风险覆盖边界。
下一步：更新 TASKGRAPH-v7 为 SUCCEEDED 并完成临时验收环境清理。
