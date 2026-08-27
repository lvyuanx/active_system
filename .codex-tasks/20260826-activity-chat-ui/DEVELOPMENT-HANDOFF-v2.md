任务：TASK-v2 活动聊天室微信式 UI 与短屏布局修复
输入版本：TASK-v2；输入 HEAD `23c21c89141eff93fec55022493cae49128f4dbf`
状态：completed
结论：主 Agent 在开发子节点长时间无交接后接管完成实现，保留协议不变，完成短屏底部布局、微信式消息行和既有输入/滚动行为。
证据：

- `apps/user-web/src/views/activity/chat.vue` 展示消息发送者本地头像、真实用户名、时间和气泡，并按当前用户 ID 应用左右方向；输入区上方保留当前用户名与头像。
- `apps/user-web/src/views/activity/chat.vue` 使用固定 1–20 头像 ID 映射：当前用户使用 `user.avatar_id`，其他发送者根据稳定活动用户 ID 确定性映射，非法 ID 使用本地兜底；未修改消息或发送 payload。
- `apps/user-web/src/views/activity/activity.css` 将聊天壳设为固定可视高度并让消息列表承担剩余滚动空间，输入区位于 Tabbar 上方；消息气泡支持长文本换行。
- `pnpm --filter @active/user-web typecheck` 退出码 0。
- `pnpm --filter @active/user-web build` 退出码 0，Vite 转换 334 个模块。
- `git diff --check` 退出码 0，仅有现有 LF/CRLF 转换提示。
- 浏览器 390×844 已确认消息行头像/用户名/左侧气泡、输入区底部定位；浏览器 390×450 已确认聊天壳、身份提示、输入框和发送按钮位于 Tabbar 上方。

变更文件：

- `apps/user-web/src/views/activity/chat.vue`
- `apps/user-web/src/views/activity/activity.css`
- `apps/user-web/AGENTS.md`

风险或阻塞：现有 `ChatMessage` 协议不携带发送者 `avatar_id`，其他发送者头像是稳定的本地 ID 展示映射，不等同于后端分配头像；未修改 API/WebSocket 协议。真实移动设备键盘和安全区仍需回归。
下一步：交接 tester-v2，独立执行 TASK-v2 的 AC-001～AC-008 回归。

实现摘要：

- `chat-content` 使用明确 `height` 和 `overflow: hidden`，防止 390×450 短屏被消息内容撑高。
- `VanField` 使用 `minHeight: 24`、`maxHeight: 72`，超过三行后 textarea 内部滚动。
- 消息行使用头像 + 用户名/时间元信息 + 圆角气泡，来消息左对齐，本人消息右对齐。
- 实时消息继续使用追加前滚动快照，仅在列表可滚动且距底部不超过可视高度三分之一时滚底；历史加载保持滚动锚点。

方案偏差：TASK-v2 的协议不变约束使其他发送者无法读取后端真实 `avatar_id`，按冻结任务单使用确定性本地映射和固定兜底；未扩大到后端或 API。
