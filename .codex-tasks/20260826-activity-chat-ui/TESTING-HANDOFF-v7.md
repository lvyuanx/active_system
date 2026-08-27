任务：测试“移除登录后顶部 Header、强化底部导航选中态”
输入版本：TASK-v7
状态：completed
结论：所有 TASK-v7 验收标准均已通过实际浏览器、移动视口和交互验证；未发现页面运行日志错误。
证据：

- `pnpm --filter @active/user-web typecheck` 退出码 0。
- `pnpm --filter @active/user-web build` 退出码 0，Vite 6.4.3 转换 335 个模块。
- 目标范围的 `git diff --check` 退出码 0。
- 实际浏览器以 `430x932` 和 `390x450` 验证认证页、首页、聊天页和“我的”页。
- 有效会话下首页、聊天和“我的”页均未渲染 `.activity-nav` 或 `.van-nav-bar`，每个路由仅有一个 active Tabbar 项。
- 430x932 首页的 active 首页项为金色 `rgb(231, 202, 134)`、字重 `700`、背景
  `rgba(213, 179, 107, 0.14)`、边框 `rgba(213, 179, 107, 0.42)`；其余项为中性
  `rgb(143, 145, 141)`、字重 `400` 且透明背景/边框。
- 点击首页、聊天、“我的”完成路由切换；浏览器 Back 回到聊天且只高亮聊天，Forward 回到“我的”且只高亮“我的”。
- 直接访问及刷新首页、`/chat` 和 `/me` 均在活动壳挂载后显示唯一对应的 active 项。
- 430x932 聊天页 `chat-content` 底部为 `874px`，Tabbar 顶部为 `874px`；composer 底部亦为
  `874px`，输入区没有覆盖 Tabbar。默认 Field 与发送按钮均为 `44px`。
- 390x450 短屏的聊天 composer 底部为 `392px`，Tabbar 顶部为 `392px`；四行输入时 textarea
  `clientHeight=72`、`scrollHeight=96`，Field 高度 `74px`，发送按钮仍完整可见。
- 页面控制台警告/错误筛选为空；聊天历史消息在浏览器中成功渲染，未发送任何聊天消息。

变更文件：

- `.codex-tasks/20260826-activity-chat-ui/TESTING-HANDOFF-v7.md`
- `.codex-tasks/20260826-activity-chat-ui/BROWSER-EVIDENCE-v7.md`

风险或阻塞：无。测试期间浏览器最初无法访问既有仅 IPv6 回环的 5175 服务；改用临时、独立的
IPv4 验收实例后完成测试，既有服务未被停止或修改。
下一步：reviewer 以 TASK-v7、DEVELOPMENT-HANDOFF-v7 和本测试交接进行只读审核。

## 测试环境

- 用户端：Vue 3、Vant 4、Vite 6.4.3。
- 验收前端：临时 Vite 实例 `http://192.168.18.187:5177`，仅用于本任务；API 指向临时 FastAPI
  实例 `http://192.168.18.187:8002/api/v1`。
- 会话：复用已有本地合成账号 `codex_ui_test_v6`；只执行登录与页面浏览，不创建用户、不发送消息。
- 浏览器：Codex In-app Browser，使用 Playwright 只读测量、DOM 控件点击与两组 viewport 覆盖。

## AC 映射

| AC | 用例与结果 | 结果 |
| --- | --- | --- |
| AC-001 | 已登录首页、聊天、“我的”均检测 `headerCount=0`，无旧 Header 占位。 | PASS |
| AC-002 | 未登录认证页截图显示 `login-hero`；DOM 测得 `loginHeroCount=1`。 | PASS |
| AC-003 | 直接进入并刷新首页、聊天、“我的”，活动壳可见后均有唯一正确 active 项。 | PASS |
| AC-004 | 点击底部 Tabbar 后路径和 active 项同步；Back/Forward 分别回到聊天和“我的”。 | PASS |
| AC-005 | 读取 active/inactive 的颜色、字重、背景和边框，实际渲染与视觉截图均有明显区分。 | PASS |
| AC-006 | 430x932 和 390x450 视口中，主体、composer 与 Tabbar 边界相邻且不重叠。 | PASS |
| AC-007 | 默认一行 Field/按钮均 44px；四行时输入区最多显示三行、内部可滚动并保持在 Tabbar 上方。 | PASS |
| AC-008 | 登录后首页/我的内容和聊天历史消息实际渲染；未改 API、Token、聊天协议或聊天逻辑，控制台无错误。 | PASS |

## 覆盖边界

- 未发送消息，以避免改变本地聊天业务数据；已通过历史消息渲染、页面日志和源码范围检查验证聊天回归。
- 未模拟刘海硬件 inset；浏览器 viewport 中已验证活动壳、聊天 composer 与 Tabbar 的实际几何关系，
  safe-area CSS 仍由浏览器环境值负责。
