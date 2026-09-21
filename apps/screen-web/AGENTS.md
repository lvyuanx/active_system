# 大屏端模块说明

## 服务器部署

deploy/build.py 通过 CLI 指定 `/screen/` base，默认 vite.config.ts 的 `./` 保留给 Electron。
产物在 deploy/nginx/html/screen，只读挂载至 Nginx，部署打包固定使用同源 API。
API 显式 VITE_API_BASE_URL 优先，生产同源 `/api/v1`，开发维持 localhost:8000。
组件显式 apiBaseUrl/桌面 bootstrap 优先；WS 使用 URL 解析后按 http/https 转换 ws/wss，兼容相对 API。

大屏端使用 Vue 3 + ECharts，保留普通活动大屏入口，并为 Electron 弹幕工具提供可嵌入渲染层。仅 URL 带有
`danmaku-overlay=1` 时，`src/components/realtime/DanmakuOverlay.vue` 才会使用桌面预加载层临时提供的 token 与会话
连接独立弹幕 WebSocket；普通入口继续显示活动数据大屏基础页面。弹幕显示聊天正文和表情图片，首次 HTTP session 的最大消息 ID
是唯一不回放历史的基线。每次 `danmaku.ready` 都从当前游标以 `after_id` 有序补齐，ready 快照不得直接抬高游标；
恢复完成后的连续实时消息直接消费 WebSocket 完整正文，只有恢复中、乱序或检测到 ID 缺口时才通过 HTTP 补齐。
`message-order.ts` 提供无浏览器依赖的消息 ID 合并、实时消息路由、待恢复完整消息缓存和 ready 补齐游标逻辑，
由 `pnpm --filter @active/screen-web test` 覆盖高 ID 先到、去重、历史游标边界和首次 ready 前断线。轨道调度和有界队列
在渲染器内完成，更新后的设置即时影响新弹幕。`danmaku-layout.ts` 提供无浏览器依赖的文本宽度、运动矩形、碰撞预测
和轮询轨道选择；同轨道会在上一条弹幕完整进入视口并经过配置间隔后尝试入场，同时保持 8px 间距和追赶碰撞保护。
`task-scheduler.ts` 使用单个
`requestAnimationFrame` 循环和 `performance.now()` 派发生命周期、重连、重试和队列刷新任务；位移继续由 CSS
`transform` 动画完成，不在 JavaScript 中逐帧改写位置。

`DanmakuOverlay.vue` 负责消息连接、排序恢复和队列，`DanmakuOverlay.css` 负责文字/图片弹幕的动画样式。

弹幕消息同时支持文字和活动聊天表情；表情使用 `<img>` 滚动，GIF 保持浏览器动画，图片按当前字体高度和原始宽高比
计算展示宽度，并使用同一宽度参与轨道碰撞和入场间隔；入场宽度至少覆盖兼容正文，确保失败回退可读。图片加载失败时显示兼容正文。
表情展示高度默认使用文字字号的 2.2 倍，宽度测量、CSS 占位高度和失败回退共用该倍率；表情垂直锚定到轨道中心，避免放大后视觉偏移。

## 实时抽奖大屏

`src/components/lottery/LotteryScreen.vue` 使用公开 `/api/v1/activities/{activity_id}/lottery/ws`，不发送管理员凭证和
控制命令。连接成功后以 `lottery.ready` 建立已揭晓 `draw_id` 基线，并从 `active_round` 恢复进行中的球体；
`lottery.draw.started` 传递开始时冻结的全部用户，大屏隐藏外围 UI 并让 `LotteryGlobe.vue` 使用 Canvas 铺满视口持续旋转头像和姓名，`LotteryWinnerReveal.vue` 负责中心揭晓；收到
`lottery.draw.stopping` 后立即停止旋转并打散，`lottery.drawn` 到达后把中奖者从打散位置聚焦到中心并交接到中心放大层，放大层持续展示到最终揭晓，随后自动恢复正常页面。旧版无轮次 `lottery.drawn`
仍通过 `lottery-order.ts` 兜底。
`lottery.reset` 清除轮次、队列和名单，`lottery.draw.error` 只结束带对应轮次 ID的失败动画。重连采用指数退避，ready 恢复最新库存和中奖名单，不重复播放历史结果。普通大屏通过 `activity_id`/`activityId` 查询参数或
`/activities/{activity_id}/...` 路径进入抽奖页面，`danmaku-overlay=1` 仍优先进入弹幕渲染器。

高人数球体使用 `lottery-globe-math.ts` 的渲染档位：全部用户保留球面点，头像和姓名按深度、人数和屏幕空间预算降级；头像圆形裁剪图、球体引导线和旋转矩阵均做缓存或复用，避免每帧重复创建高成本对象。

奖品配置和开奖事件携带可选安全图片引用；大屏只把相对引用解析到 API 服务，进行中轮次顶部标签按奖项/奖品 ID 从公开快照
匹配奖品图，当前奖品区或奖品板图片加载失败时隐藏图片并保留奖品名称、库存和中奖动画。
顶部活动标题区使用较小字号、顶部留白和面板间距，移动端与短屏使用更紧凑的覆盖值，以便抽奖面板保留更多可视空间。
活动名称不在页面正文中重复显示，而是动态写入浏览器 `document.title`；顶部标题区域仅显示当前奖品名称和可选图片，主抽奖面板不重复显示奖品名称或中奖奖品图片。
顶部当前奖品图片使用 80×80px 桌面尺寸和 64×64px 移动端尺寸，图片失败时仍只保留奖品名称。
中奖结果恢复到正常页面后显示用户头像；当前轮次使用公开参与者头像 ID，历史结果使用稳定本地头像兜底。
奖品板中的中奖用户名按 `prize_id` 分组显示在对应奖品下方，不再统一堆叠在奖项底部。
普通页面的抽奖区响应式布局按视口宽高比判断：1:1 方屏及横屏始终让主抽奖区和奖项进度板左右并列；严格小于 1:1 的竖屏改为主抽奖区在上、奖项进度板在下，进度板限制高度并仅在自身内容区域滚动，不覆盖抽奖内容或制造页面滚动。

## 本次修复说明

- 恢复完成后，连续的 WS 事件直接把文字或表情的完整消息加入弹幕队列，不再为每条实时消息发起 `/danmaku/messages` 请求。
- WS 乱序或 ID 缺口事件缓存完整消息并去重，容量上限为 200；超限丢弃最早缓存，但 HTTP 恢复仍以已处理的
  `lastMessageId` 调用 `after_id`，不会因缓存溢出而跳过中间消息。
- HTTP 恢复与 WS 事件交错时按消息 ID 合并；重复消息不重复展示，恢复失败保留未解决的完整 WS 消息并重试。
- 无浏览器测试覆盖 201 个实时消息的 200 条边界、最早项淘汰、最新项保留，以及无参数、`0`、`false` 和 `1` 四种入口值。
- 弹幕入场刷新任务按帧合并，轨道回收、节点回收、重连和 HTTP 重试均进入同一调度循环；渲染器运行时不使用
  `setTimeout` 或 `setInterval`。
- 新弹幕按 Canvas 实测宽度和 CSS 动画轨迹预测同轨碰撞；所有轨道不安全时以本地入队时间计时，默认最多等待 1.5 秒，
  管理端可配置为 0.5–5.0 秒，过期消息丢弃。
- 新弹幕同轨道的最早入场时间为上一条弹幕完整进入视口后的 `entry_interval_seconds`；该值默认 1.0 秒，管理端可配置为
  0.1–5.0 秒。不同轨道不受该间隔限制，当前活动弹幕不因设置更新而改变轨迹。
