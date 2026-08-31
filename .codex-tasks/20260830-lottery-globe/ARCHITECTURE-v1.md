# ARCHITECTURE-v1：抽奖球体动画与开始/停止开奖

任务：实现抽奖球体动画与开始/停止开奖
输入版本：TASK-v1
状态：completed
结论：采用“单进程轮次状态 + 事务开奖 + 提交后广播”的方案，管理端和公开大屏通过同一活动房间同步；球体布局完全在 screen-web 本地计算。
证据：`apps/backend/app/modules/lottery/round_state.py`、`protocol.py`、`state.py`、`service.py`、`router.py`；`apps/admin-web/src/views/lottery/useLotteryRoundControl.ts`；`apps/screen-web/src/components/lottery/LotteryGlobe.vue` 和 `lottery-globe-math.ts`。
变更文件：后端 lottery 轮次/协议/锁和模型；管理端轮次控制与锁定；大屏 Canvas 球体、全屏 CSS、头像资源、类型和测试；相关模块文档与项目知识。
风险或阻塞：内存轮次只支持单进程；重启取消未完成轮次；多副本部署仍需共享消息总线。无当前阻塞。
下一步：交由开发实现并由测试按 AC-001 至 AC-011 回归。

## 方案

1. `lottery.draw.start` 在共享操作锁内调用 `prepare_lottery_round`。该事务校验活动/奖品/库存/候选池，读取活动全部用户用于公开球体，
   仅保存候选用户 ID 集合用于实际开奖；`LotteryRoundStore` 按活动只保留一个轮次。
2. 轮次存入内存后广播 `lottery.draw.started`。公开对象只包含奖项、奖品、开始时间、轮次 ID和 `{activity_user_id, username, avatar_id}`。
3. `lottery.draw.stop` 在同一共享操作锁内把轮次候选 ID传给现有 `draw_lottery`。数据库仍使用 `BEGIN IMMEDIATE`，停止时重新计算有效用户，
   以轮次 ID命中 `(activity_id, request_id)` 幂等记录。
4. 中奖记录事务成功提交后清理内存轮次，再向管理员广播完整结果，向大屏广播带 `round_id` 的公开 `lottery.drawn`；幂等重试只返回当前连接，不广播。
5. ready 通过连接管理器广播屏障生成快照并合并 `active_round`，避免 ready 与 started/drawn/reset 的顺序竞争。配置/名单/图片/重置复用同一操作锁并拒绝活动轮次期间写入。
6. 大屏收到 started 后为全部 participants 生成 Fibonacci 球面坐标，Canvas 每帧执行旋转、深度排序、透视和透明度绘制。收到带轮次的 drawn 后才从持续旋转切换到约 2.2 秒 ease-out，
   计算中奖点目标角度并居中；若本地没有该点，保留事件用户名并使用默认头像显示揭晓卡片。

## 兼容与恢复

- 旧 `lottery.draw.request` 仍走既有单阶段事务和旧版候选名单动画；活动已有新轮次时拒绝旧开奖请求。
- 前端按 `draw_id` 去重；ready 历史建立已揭晓基线，不再重复播放。无进行中轮次且 ready 含历史时显示最新中奖者；进行中轮次优先恢复球体。
- 后端重启不恢复内存轮次，已提交历史保留；管理员需要重新开始新的轮次。
