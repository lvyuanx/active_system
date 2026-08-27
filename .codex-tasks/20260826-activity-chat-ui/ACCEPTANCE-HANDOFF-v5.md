任务：TASK-v5 活动聊天室输入框默认高度校准
输入版本：TASK-v5
状态：completed
结论：ACCEPTED（主 Agent 依据冻结验收标准完成逐条验收；验收角色线程未返回可用正文）
证据：

- AC-001：PASS。390×450 空输入/一行输入 Field 与发送按钮均为 44px，底边差为 0px；430×932 同样均为 44px。
- AC-002：PASS。390×450 两行 textarea/Field/按钮为 48/50/44px，三行为 72/74/44px；第四行 value 仍可编辑，textarea `clientHeight=72px`、`scrollHeight=96px`。
- AC-003：PASS。390×450 和 430×932 中输入区底边分别为 391/873px，均与 Tabbar 顶部一致，页面横向溢出为 `false`。
- AC-004：PASS。`chat.vue:90-116` 仍在追加前记录列表滚动快照，仅在距底部不超过可视高度三分之一时滚底；v4 已验证实时滚动正反向，v5 未改动该逻辑。
- AC-005：PASS。当前 DOM 中 `chat-header`、`chat-connection`、`chat-composer-identity` 均不存在，`activity-nav` 存在，消息区与输入区连续。
- AC-006：PASS。当前消息行显示本地头像、真实 `sender_username`、时间和气泡，其他用户与本人按左右方向排列。
- AC-007：PASS。`chat.vue:74-79` 只使用固定 1–20 本地头像 ID 映射和本地兜底，不加载外部路径或 HTML。
- AC-008：PASS。`chat.vue:119-184` 保留 `before_id`、`after_id`、WebSocket `auth`、`message.send`、`chat.ready`、`message.created` 和 `chat.error`。
- AC-009：PASS。`chat.vue:142-150` 继续使用加载前后的 scrollHeight 差恢复历史锚点，不触发底部滚动。
- AC-010：PASS。390×450 和 430×932 均检测到父级导航与底部 Tabbar，未发生横向溢出。
- AC-011：PASS。填入 600 个字符后实际 value 长度为 500，清空草稿后未发送；源码仍保留 `maxlength="500"`。

变更文件：无
风险或阻塞：390×450 截图接口连续超时，短屏使用 DOM/像素证据；AC-004 的实时消息实测证据来自未改变的 v4 回归，v5 以源码静态复核补充。验收角色线程未返回，结论由主 Agent 独立完成。
下一步：清理已登记的预览 worktree，更新任务图为完成态。

