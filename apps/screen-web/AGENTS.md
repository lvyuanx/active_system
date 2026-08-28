# 大屏端模块说明

大屏端使用 Vue 3 + ECharts，保留普通活动大屏入口，并为 Electron 弹幕工具提供可嵌入渲染层。仅 URL 带有
`danmaku-overlay=1` 时，`src/components/realtime/DanmakuOverlay.vue` 才会使用桌面预加载层临时提供的 token 与会话
连接独立弹幕 WebSocket；普通入口继续显示活动数据大屏基础页面。弹幕仅显示聊天正文，首次 HTTP session 的最大消息 ID
是唯一不回放历史的基线。每次 `danmaku.ready` 都从当前游标以 `after_id` 有序补齐，ready 快照不得直接抬高游标；
实时事件乱序时同样通过 HTTP 补齐。`message-order.ts` 提供无浏览器依赖的消息 ID 合并和 ready 补齐游标逻辑，
由 `pnpm --filter @active/screen-web test` 覆盖高 ID 先到、去重、历史游标边界和首次 ready 前断线。轨道调度和有界队列
在渲染器内完成，更新后的设置即时影响新弹幕。`danmaku-layout.ts` 提供无浏览器依赖的文本宽度、运动矩形、碰撞预测
和轮询轨道选择；同轨道会在上一条弹幕完整进入视口并经过配置间隔后尝试入场，同时保持 8px 间距和追赶碰撞保护。
`task-scheduler.ts` 使用单个
`requestAnimationFrame` 循环和 `performance.now()` 派发生命周期、重连、重试和队列刷新任务；位移继续由 CSS
`transform` 动画完成，不在 JavaScript 中逐帧改写位置。

## 本次修复说明

- WS 实时补齐信号仅保留去重的消息 ID，容量上限为 200；超限丢弃最早信号，但保留最新信号以触发恢复。
- HTTP 恢复始终以已处理的 `lastMessageId` 调用 `after_id`，不会因信号溢出而跳过中间消息。
- 无浏览器测试覆盖 201 个信号的 200 条边界、最早项淘汰、最新项保留，以及无参数、`0`、`false` 和 `1` 四种入口值。
- 弹幕入场刷新任务按帧合并，轨道回收、节点回收、重连和 HTTP 重试均进入同一调度循环；渲染器运行时不使用
  `setTimeout` 或 `setInterval`。
- 新弹幕按 Canvas 实测宽度和 CSS 动画轨迹预测同轨碰撞；所有轨道不安全时以本地入队时间计时，默认最多等待 1.5 秒，
  管理端可配置为 0.5–5.0 秒，过期消息丢弃。
- 新弹幕同轨道的最早入场时间为上一条弹幕完整进入视口后的 `entry_interval_seconds`；该值默认 1.0 秒，管理端可配置为
  0.1–5.0 秒。不同轨道不受该间隔限制，当前活动弹幕不因设置更新而改变轨迹。
