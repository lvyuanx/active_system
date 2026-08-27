# 大屏端模块说明

大屏端使用 Vue 3 + ECharts，保留普通活动大屏入口，并为 Electron 弹幕工具提供可嵌入渲染层。仅 URL 带有
`danmaku-overlay=1` 时，`src/components/realtime/DanmakuOverlay.vue` 才会使用桌面预加载层临时提供的 token 与会话
连接独立弹幕 WebSocket；普通入口继续显示活动数据大屏基础页面。弹幕仅显示聊天正文，首次 HTTP session 的最大消息 ID
是唯一不回放历史的基线。每次 `danmaku.ready` 都从当前游标以 `after_id` 有序补齐，ready 快照不得直接抬高游标；
实时事件乱序时同样通过 HTTP 补齐。`message-order.ts` 提供无浏览器依赖的消息 ID 合并和 ready 补齐游标逻辑，
由 `pnpm --filter @active/screen-web test` 覆盖高 ID 先到、去重、历史游标边界和首次 ready 前断线。轨道调度和有界队列
在渲染器内完成，更新后的设置即时影响新弹幕。

## 本次修复说明

- WS 实时补齐信号仅保留去重的消息 ID，容量上限为 200；超限丢弃最早信号，但保留最新信号以触发恢复。
- HTTP 恢复始终以已处理的 `lastMessageId` 调用 `after_id`，不会因信号溢出而跳过中间消息。
- 无浏览器测试覆盖 201 个信号的 200 条边界、最早项淘汰、最新项保留，以及无参数、`0`、`false` 和 `1` 四种入口值。
