任务：TASK-v4 活动聊天室指定附属区域移除回归
输入版本：TASK-v4；HEAD `23c21c89141eff93fec55022493cae49128f4dbf`
状态：completed
结论：主 Agent 完成测试回退并取得静态、构建和真实浏览器证据；测试子 Agent 未能在平台等待窗口内返回，未修改测试资产或生产文件。
证据：

- `rg` 未发现 `chat-header`、`chat-title`、`chat-connection`、`chat-composer-identity`、`connectionLabel` 或 `VanTag` 在聊天页/CSS中的残留引用。
- `pnpm --filter @active/user-web typecheck`：退出码 0。
- `pnpm --filter @active/user-web build`：退出码 0，Vite 转换 335 个模块。
- `git diff --check -- apps/user-web/AGENTS.md apps/user-web/src/views/activity/chat.vue apps/user-web/src/views/activity/activity.css apps/user-web/src/views/activity/chat.css`：退出码 0；仅有行尾转换提示。
- 浏览器 430×932：`chat-header`、`chat-connection`、`chat-composer-identity` 均不存在；父级 `activity-nav` 和底部 Tabbar存在；消息行头像/用户名/左右气泡和输入框/发送按钮可见；无横向溢出。
- 浏览器 390×450：三个目标区域均不存在；聊天壳范围 y=53..391，Tabbar y=391..450；空输入框和发送按钮底部 y=383；无横向溢出。
- 浏览器 390×450 三行输入：textarea 高度 72px，输入控件和发送按钮底部 y=383，Tabbar 顶部 y=391。
- 浏览器 390×450 四行输入：textarea 高度保持 72px、scrollHeight=96px、第四行文本仍存在，发送按钮底部 y=383，页面宽度仍为 390px。
- 浏览器实时滚动回归（当前 v4 DOM/CSS）：在列表顶部发送合成消息“最终顶部回归”后 scrollTop 保持 0；在列表底部发送合成消息“最终底部跟随”后 atBottom=true。合成消息写入本地开发数据库，仅用于本地回归。
- 可追溯截图与所有 DOM 尺寸/滚动数据见 `BROWSER-EVIDENCE-v4.md`，截图文件已保存到任务目录。

变更文件：无测试资产；未修改生产文件。
风险或阻塞：全量 `git diff --check` 受任务外头像 SVG 文件尾随空白影响；目标文件范围检查通过。未在真实物理设备上验证键盘弹出和 safe-area inset；浏览器视口已覆盖 430×932 与 390×450。
下一步：交接审核；审核需关注目标区域无残留、连接状态仍仅作为发送条件、协议/API未变以及消息滚动逻辑未回归。集成范围和预览 apply-check 见 `INTEGRATION-EVIDENCE-v4.md`。

测试环境：Windows PowerShell；工作目录 `D:\projects\active_system`；本地用户端 5175、后端 8000；浏览器视口 430×932、390×450；无测试文件写入。

AC 映射：

- AC-001：PASS，v4 实际输入高度和控件位置证据如上。
- AC-002：PASS，静态条件检查 + 顶部不跳/底部跟随真实 WebSocket 回归证据如上。
- AC-003：PASS，三个 DOM 区域不存在，父级 activity-nav 保留。
- AC-004：PASS，390×450 空输入与三行输入均在 Tabbar 上方且无横向溢出。
- AC-005：PASS，430×932 DOM/截图确认头像、真实用户名、时间、气泡及左右方向。
- AC-006：PASS，消息头像使用现有 ActivityAvatar 本地映射及稳定 ID 兜底。
- AC-007：PASS，`client.ts` 未变更；消息发送仍为 `{ type: "message.send", body }`，认证/事件流程未改。
- AC-008：PASS，`before_id` 路径保留高度差锚点，未调用实时滚底。
- AC-009：PASS，移除区域后的聊天消息区直接从导航下方开始，输入控件直接位于底部，无异常大间隙。
- AC-010：PASS，activity-nav 与底部 Tabbar在 430×932/390×450均存在。
