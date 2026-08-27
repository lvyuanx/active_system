# TASK-v5 浏览器证据

## 输入版本

TASK-v5。测试地址：`http://localhost:5175/activity/41f9d161-c015-42d4-a4f5-0cc65ecec285/chat`。使用本地合成测试账号 `codex_ui_test_v5`，未发送新增消息。

## 390×450

- 空输入：`.van-cell` 高 `44px`，发送按钮高 `44px`，两者底边均为 `383px`；输入区底边为 `391px`，与 Tabbar 顶部一致。
- 一行输入 `一行消息`：Field 高 `44px`，按钮高 `44px`，两者底边差 `0px`。
- 两行输入：textarea 内容高 `48px`，Field 外框高 `50px`（包含上下边框），按钮保持 `44px`，三者底边一致。
- 三行输入：textarea 内容高 `72px`，Field 外框高 `74px`（包含上下边框），按钮保持 `44px`，横向间距 `8px`。
- 四行输入：textarea `clientHeight=72px`、`scrollHeight=96px`，value 仍包含第四行，证明超过三行后在控件内部滚动且仍可编辑。
- 短屏状态：横向溢出为 `false`；消息列表、输入区、发送按钮和 Tabbar 均位于视口内。

390px 截图通过浏览器 `Page.captureScreenshot` 连续三次超时，未生成 v5 短屏截图；上述 DOM 和实际像素测量均成功完成。

## 430×932

- 默认状态：Field 高 `44px`，按钮高 `44px`，两者底边均为 `865px`；输入区底边 `873px`，Tabbar 顶部 `873px`。
- 消息列表高度 `740px`，活动导航高 `53px`，Tabbar 高 `59px`，横向溢出为 `false`。
- `chat-header`、`chat-connection`、`chat-composer-identity` 均不存在；父级 `activity-nav` 存在；当前页面渲染 20 条消息。
- 视觉截图：[BROWSER-430x932-v5.png](./BROWSER-430x932-v5.png)。

## 输入限制

在 390×450 页面填入 600 个字符后，Vant Field 实际 value 长度为 `500`；清空草稿后未发送消息。源码仍保留 `maxlength="500"`。

## 不变行为检查

- `chat.vue` 仍使用 `before_id`、`after_id`、WebSocket 首帧 `auth`、`message.send`、`chat.ready`、`message.created` 和 `chat.error` 流程。
- 实时追加继续经由 `captureScrollSnapshot`、`revealNewMessages` 判断底部三分之一阈值；历史加载继续用高度差恢复锚点。
- 消息行继续渲染本地安全头像、`sender_username`、时间和气泡。
