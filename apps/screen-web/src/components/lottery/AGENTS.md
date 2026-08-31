# 抽奖大屏组件说明

## 模块职责

`src/components/lottery/` 提供公开活动抽奖大屏，不保存管理员凭证，不承担开奖控制，只消费活动级 lottery WebSocket。
`LotteryGlobe.vue` 使用 Canvas 绘制头像与用户名 3D 球体，并按人数启用头像/光点/姓名的分层渲染；`lottery-globe-canvas.ts` 缓存球体引导线，
`lottery-globe-assets.ts` 缓存头像圆形位图；`LotteryScreen.css` 负责全屏主视觉，
`LotteryScreenImages.css` 负责奖品缩略图和中奖图片样式。

## 主要流程

组件连接 `/api/v1/activities/{activity_id}/lottery/ws` 后接收公开 `lottery.ready` 快照；ready 中的历史记录只建立已揭晓
基线，进行中的 `active_round` 会恢复球体。收到 `lottery.draw.started` 后冻结的全部用户进入持续旋转的球体；收到
`lottery.draw.stopping` 立即冻结旋转，球体先向外打散，再在收到带 `round_id` 的 `lottery.drawn` 后让中奖用户从打散位置
聚焦到中心，最后揭晓中奖者；若事件用户不在本地布局，仍使用事件中的用户名和默认头像揭晓。
旧版无轮次事件仍使用候选名单滚动兜底。高人数时全部用户仍保留为球面点，前景姓名通过数量上限和屏幕空间碰撞避让筛选，动画按人数降帧并降低 Canvas 像素比。
`lottery.reset` 清空轮次、队列和名单，`lottery.config.updated` 更新奖项库存，错误事件只显示提示并结束对应轮次。
`LotteryGlobe.vue` 不再绘制中心十字，中奖聚焦阶段使用光环和中心卡片作为视觉焦点。

## 安全与恢复

- 大屏只使用公开 WebSocket，不发送管理员 JWT 或开奖控制消息。
- 重连使用指数退避，重连成功以 ready 覆盖当前状态；无进行中轮次时从 ready 历史恢复最新中奖者，已揭晓记录不会再次播放。
- 公开开始轮次只展示活动用户 ID、用户名和头像 ID；中奖快照只展示用户名、奖项、序号、库存和安全奖品图片引用，
  不渲染手机号、名单标记、停用状态、管理员字段或存储 key。
- 奖项进度显示奖品缩略图，中奖揭晓显示中奖奖品图；无图、404 或加载失败时隐藏图片并保留文字和库存。

## 视觉约定

保留深色霓虹背景、光晕和粒子；抽奖时球体占据可用大屏区域，头像和用户名按深度缩放透明，停止后依次执行冻结、打散、
中奖用户聚焦到中心和卡片揭晓。
页面根节点使用 `100dvh` 和 `overflow: hidden`，奖项进度板在抽奖态作为紧凑浮层，不制造页面滚动。普通 screen-web 入口通过
`activity_id` 查询参数或活动路径进入抽奖页面，弹幕 overlay 参数仍优先进入既有弹幕渲染器。
