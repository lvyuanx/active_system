# ARCHITECTURE-v1：抽奖球体停止、打散与中奖聚焦

任务：抽奖球体停止、打散与中奖聚焦
输入版本：TASK-v1
状态：completed
结论：采用公开 stopping 信号与前端可恢复动画阶段的方案。
证据：`apps/backend/app/modules/lottery/protocol.py` 在开奖事务前广播 `lottery.draw.stopping`；`round_state.py` 保存 `rolling/stopping`；`LotteryScreen.vue` 与 `LotteryGlobe.vue` 分离停止和揭晓阶段。
变更文件：后端 lottery 协议/状态模型、screen-web 抽奖组件与数学/Canvas/头像辅助、admin-web 控制 composable、客户端类型、测试和文档。
风险或阻塞：单进程连接管理器和内存轮次的既有多副本限制不变；停止广播与事务处理仍依赖同一进程事件顺序。
下一步：开发实现后验证事件顺序、阶段去重、重连和高人数浏览器表现。

## 方案

1. 管理端停止请求进入 lottery operation lock 后，后端先将内存轮次替换为 `phase=stopping`，向活动所有 admin/screen 连接广播仅含 `request_id`/`round_id` 的 `lottery.draw.stopping`。
2. 随后执行现有开奖事务；成功提交后维持原有 admin `lottery.draw.result` 与 screen `lottery.drawn` 的权限边界。事务失败则清理轮次并广播错误，不触发中奖揭晓。
3. 大屏收到 stopping 后将阶段切到 `scattering`，保留当前 rotation，不再修改 rotation；约 850ms 使用深度相关的径向放大和透明度衰减完成打散。
4. 如果结果尚未到达，阶段进入 `scattered` 等待；结果到达后进入 `selecting`，约 1300ms 将中奖用户从冻结坐标插值到画布中心、放大并绘制光环，非中奖用户淡出。
5. selecting 完成后进入 `revealed`，由现有 DOM 卡片展示中奖者。重连通过 `active_round.phase` 从 stopping 恢复；结果先到时仅缓存，不能跳过打散。

## 风险与回滚

- stopping 是新增公开事件但不含敏感字段；旧客户端忽略未知事件仍可等待原有结果事件。
- 前端若错过 stopping，在收到带轮次 ID 的 drawn 时回退进入 scattering，保证不会继续滚动到揭晓。
- 回滚可移除 stopping 阶段广播与前端阶段扩展，恢复原有 draw result/drawn 协议；数据库结构不需要回滚。
