# 抽奖大屏组件说明

## 模块职责

`src/components/lottery/` 提供公开活动抽奖大屏，不保存管理员凭证，不承担开奖控制，只消费活动级 lottery WebSocket。
`LotteryScreen.css` 负责大屏主视觉，`LotteryScreenImages.css` 负责奖品缩略图和中奖图片样式。

## 主要流程

组件连接 `/api/v1/activities/{activity_id}/lottery/ws` 后接收公开 `lottery.ready` 快照；ready 中的历史记录只建立已揭晓
基线。之后的 `lottery.drawn` 按 `draw_id` 去重并按序进入滚动候选名单队列，约 3 秒后揭晓中奖者。
`lottery.reset` 清空队列和名单，`lottery.config.updated` 更新奖项库存，错误事件只显示提示，不触发中奖动画。

## 安全与恢复

- 大屏只使用公开 WebSocket，不发送管理员 JWT 或开奖控制消息。
- 重连使用指数退避，重连成功以 ready 覆盖当前状态，已揭晓记录不会再次播放。
- 公开数据只展示用户名、奖项、序号、库存和安全奖品图片引用，不渲染手机号、名单标记、管理员字段或存储 key。
- 奖项进度显示奖品缩略图，中奖揭晓显示中奖奖品图；无图、404 或加载失败时隐藏图片并保留文字和库存。

## 视觉约定

保留深色霓虹背景、光晕、粒子、候选名单滚动和中奖揭晓动画；普通 screen-web 入口通过 `activity_id` 查询参数或活动路径
进入抽奖页面，弹幕 overlay 参数仍优先进入既有弹幕渲染器。
