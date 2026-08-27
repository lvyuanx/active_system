任务：TASK-v4 活动聊天室指定附属区域移除
输入版本：TASK-v4；输入 HEAD `23c21c89141eff93fec55022493cae49128f4dbf`
状态：completed
结论：主 Agent 完成 v4 开发回退，移除聊天子页顶部标题区、连接状态行和当前用户身份提示区；保留父级导航、消息列表、微信式消息行、输入框、发送按钮和聊天逻辑。
证据：

- `apps/user-web/src/views/activity/chat.vue` 不再渲染 `chat-header`、`chat-connection` 或 `chat-composer-identity`；`activity-nav` 仍由父级 `index.vue` 渲染。
- `apps/user-web/src/views/activity/chat.vue` 保留 `messageAvatarId`、真实 `sender_username`、时间、消息气泡、左右对齐、实时条件滚动、重连补拉和历史滚动锚点。
- `apps/user-web/src/views/activity/activity.css` 保留活动页公共样式；聊天专属样式已提取到 `apps/user-web/src/views/activity/chat.css`，包括固定聊天壳高度、消息区滚动、气泡和输入控件。
- `apps/user-web/src/views/activity/chat.css` 的聊天壳高度使用 `100dvh - 112px`，390×450 时聊天壳底部与 Tabbar 顶部对齐。
- `apps/user-web/AGENTS.md` 已同步当前聊天消息和头像行为。
- `pnpm --filter @active/user-web typecheck`：退出码 0。
- `pnpm --filter @active/user-web build`：退出码 0，Vite 转换 335 个模块。
- 目标文件 `git diff --check`：退出码 0。
- 浏览器 430×932：拆分后的 `chat.css` 生效，三个目标区域均不存在，父级活动导航、消息行、输入框、发送按钮和 Tabbar 均存在且无横向溢出。
- 浏览器 390×450：三个目标区域均不存在；消息列表、输入框和发送按钮均位于 Tabbar 上方；三行输入 textarea 为 72px，第四行仍可编辑且高度保持 72px。
- 可追溯浏览器截图和尺寸/滚动数据见 `BROWSER-EVIDENCE-v4.md`，截图文件为 `BROWSER-430x932-v4.png` 与 `BROWSER-390x450-v4.png`。

变更文件：

- `apps/user-web/src/views/activity/chat.vue`
- `apps/user-web/src/views/activity/chat.css`
- `apps/user-web/src/views/activity/activity.css`
- `apps/user-web/AGENTS.md`

风险或阻塞：现有消息协议不含发送者 avatar_id，非当前用户消息头像继续使用稳定活动用户 ID 的本地确定性映射；未修改 API/WebSocket。全量工作区 diff-check 受到本任务之外的头像 SVG 尾随空白影响，目标文件范围检查通过。
下一步：交接 TASK-v4 测试与审核；不提交、不推送。限定补丁、预览 worktree 和 WorkPackage 证据见 `INTEGRATION-EVIDENCE-v4.md`、`WORKPACKAGE-v4.json`。

实现摘要：

- 删除聊天子页自身活动标题、连接状态和当前用户身份提示的 DOM 及无用样式，避免区域残留和大间隙。
- 保留微信式消息头像、真实用户名、时间和左右气泡。
- 保留输入框 1–3 行自适应、条件实时滚动、历史加载锚点和底部 Tabbar 布局。

方案偏差：开发子 Agent 未在平台等待窗口内返回，主 Agent 按回退规则完成 v4 实现；没有扩大到后端、API、WebSocket 或头像资源。

文件 SHA-256：

- `apps/user-web/src/views/activity/chat.vue`：`81E92B63BFA8ADAA34BA9029920A761B3AE57B1E31475F88BC93EB9AFA32B3FF`
- `apps/user-web/src/views/activity/chat.css`：`738741226F1203444BB0CCE8F220AC90FF39F9D1E8078D66F828F61DE863F52E`
- `apps/user-web/src/views/activity/activity.css`：`685029FF233E79E59E8DA6E344902A7C3EDD5F5E9214718BAAB398CC2F346CDE`
- `apps/user-web/AGENTS.md`：`197B13B75AC8711198304FC83E0609DB149B7E5F5C1744FEC5E561244C3A59E5`
