任务：TASK-v5 活动聊天室输入框默认高度校准
输入版本：TASK-v5
状态：completed
结论：必需验收场景通过。默认空输入和一行输入时 Field 与发送按钮均为 44px；三行内容高度为 72px；第四行仍可编辑并在 72px 控件内部滚动；短屏和常规移动尺寸未出现页面横向溢出或 Tabbar 遮挡。
证据：

- 390×450 空输入：Field `44px`、按钮 `44px`、底边均 `383px`。
- 390×450 一行输入：Field/按钮高度差 `0px`、底边差 `0px`。
- 390×450 两行输入：textarea `48px`、Field `50px`、按钮 `44px`，三者底边一致且无横向溢出。
- 390×450 三行输入：textarea `72px`，Field `74px`，按钮 `44px`，水平方向间距 `8px`。
- 390×450 四行输入：textarea `clientHeight=72px`、`scrollHeight=96px`、value 包含第四行。
- 390×450 600 字符输入：实际 value 长度 `500`，清空后未发送。
- 430×932：Field/按钮均 `44px`，横向溢出 `false`，父级导航和 Tabbar 存在，三个指定附属区域不存在。
- 截图和完整测量明细见 `BROWSER-EVIDENCE-v5.md`；430px 最终视觉截图为 `BROWSER-430x932-v5.png`。
- `pnpm --filter @active/user-web typecheck`、`pnpm --filter @active/user-web build` 和目标文件 `git diff --check` 均退出码 0。

变更文件：

- `.codex-tasks/20260826-activity-chat-ui/BROWSER-EVIDENCE-v5.md`
- `.codex-tasks/20260826-activity-chat-ui/BROWSER-430x932-v5.png`

风险或阻塞：浏览器 390px 截图采集连续超时，未取得短屏 PNG；短屏功能状态已由 DOM 和像素测量验证。实时滚动、历史锚点和协议属于本次 CSS/展示改动之外，沿用 TASK-v4 已验证实现，并已做源码静态回归。
下一步：审核当前源代码、测试证据和文档同步状态。
