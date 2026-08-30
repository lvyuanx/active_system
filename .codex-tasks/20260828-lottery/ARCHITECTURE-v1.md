# TASK-v1 架构交接

任务：设计 WebSocket 实时抽奖的活动数据、事务开奖、权限隔离和前后端事件流。
输入版本：TASK-v1。
状态：completed
结论：采用独立 lottery 模块和活动级进程内连接管理器；管理员 WebSocket 使用 JWT 首帧认证，公开大屏连接不认证；配置/历史走 HTTP，开奖/重置/状态走 WebSocket。SQLite 事务以 `BEGIN IMMEDIATE` 串行化候选计算、库存校验和中奖写入，提交后才广播。
证据：`apps/backend/app/core/database.py`、`apps/backend/app/modules/auth/router.py`、`apps/backend/app/modules/participants/router.py`、现有 `chat`/`danmaku` WebSocket manager 模式。
变更文件：架构交接文档；实现变更由开发阶段完成。
风险或阻塞：连接管理器只覆盖单进程；配置删除与已有中奖记录存在外键约束，因此服务层拒绝会影响历史的危险删除/降量；SQLite 读写并发依赖显式立即事务和连接超时。无高影响阻塞。
下一步：交由主工作树开发实现，随后执行后端协议/并发测试、前端类型检查、构建、审核和逐条验收。

## 模块边界

- `apps/backend/app/modules/lottery/service.py`：Pydantic 协议模型、配置/历史查询、候选计算、事务开奖、重置和快照构造。
- `apps/backend/app/modules/lottery/manager.py`：活动房间的管理员/大屏连接注册、按权限广播、失败连接清理；不持久化数据。
- `apps/backend/app/modules/lottery/router.py`：管理员 HTTP 配置/历史路由、管理员首帧认证 WS、公开只读 WS 和事件分发。
- `apps/backend/app/core/database.py`：新增 `lottery_configs`、`lottery_awards`、`lottery_prizes`、`lottery_entries`、`lottery_draws` 表及索引。
- `apps/backend/app/modules/participants/router.py`：新参与者注册时插入默认抽奖名单行；候选查询对缺少历史名单行按默认可参加处理。
- `apps/admin-web/src/views/lottery/`：管理端配置、开奖控制、历史和连接状态页面。
- `apps/screen-web/src/components/lottery/`：公开抽奖大屏、重连、ready 恢复、事件队列/去重和视觉动画。

## 数据模型

1. `lottery_configs` 以 `activity_id` 为主键，保存 `no_repeat_across_prizes` 和 `rolling_name_count`。
2. `lottery_awards` 保存活动奖项名称及顺序；`lottery_prizes` 通过同活动 `award_id` 关联奖项，保存名称、库存数量、顺序和启用状态。
3. `lottery_entries` 以 `(activity_id, activity_user_id)` 唯一，保存黑名单/白名单标记；缺失行表示普通可参加名单。若活动存在任意白名单行，只有白名单用户可参加。
4. `lottery_draws` 保存 `draw_id`、活动/奖项/奖品、活动用户、奖品内 `draw_number`、`drawn_at` 和 `request_id`，以 `(activity_id, request_id)` 和 `(activity_id, draw_id)` 保证幂等和活动隔离。
5. 剩余库存不单独存储，始终在同一事务中按 `quantity - COUNT(lottery_draws)` 计算，避免扣减字段与中奖记录分叉。

## HTTP 接口

- `GET /api/v1/admin/activities/{activity_id}/lottery`：返回管理员配置、奖项、奖品、名单和派生库存。
- `PUT /api/v1/admin/activities/{activity_id}/lottery`：按活动更新配置；支持新增/更新奖项、奖品、名单和规则，服务层校验同活动外键及已有中奖记录约束。
- `GET /api/v1/admin/activities/{activity_id}/lottery/history?limit=&before_id=`：返回包含手机号的管理员中奖历史。

HTTP 保存成功后，路由仅在服务事务返回成功后调用连接管理器广播 `lottery.config.updated`；发送给大屏的配置只包含奖项/奖品/安全规则，不包含名单和手机号。

## WebSocket 协议

- 管理端：`/api/v1/admin/activities/{activity_id}/lottery/ws`。服务端 accept 后等待首帧 `{type:"auth",token:"..."}`（同时兼容首帧直接为 JWT 字符串），校验超级管理员和活动存在，然后发送管理员完整 `lottery.ready`。
- 大屏端：`/api/v1/activities/{activity_id}/lottery/ws`。服务端 accept 后不要求首帧，立即发送公开 `lottery.ready`；客户端只能发送 `lottery.ping`，控制类消息均返回协议错误。
- 开奖请求：`{type:"lottery.draw.request",prize_id,request_id}`。成功结果含管理员完整 `draw`，同时向大屏发送用户脱敏的 `lottery.drawn` 和候选 `roll_names`。相同 request 重试只向当前管理连接返回已有结果，不再次广播。
- 重置请求：`{type:"lottery.reset.request"}`。成功事务删除中奖记录，分别向管理员/大屏发送权限对应的 `lottery.reset` 快照。
- 错误、配置更新、心跳分别使用 `lottery.draw.error`、`lottery.config.updated`、`lottery.pong`。

## 事务和安全

1. `draw_lottery` 进入 `transaction(settings)` 后立即执行 `BEGIN IMMEDIATE`。
2. 先查询同活动 `request_id`；命中则读取原记录并返回幂等结果。
3. 校验活动为 `open`、奖品属于同一活动且已启用、库存大于 0；在同一连接内计算白名单、黑名单、`is_active` 和跨奖品已中奖过滤。
4. 随机选择候选人，生成奖品内序号并写入中奖记录；异常回滚，不返回任何成功事件。
5. 事务上下文成功退出提交后，路由才使用 manager 广播。
6. 管理员认证沿用 HS256 JWT 与数据库 `is_superuser` 回查，并拒绝带 `activity_id` claim 的活动用户上下文；公开端没有写权限和敏感字段。

## 前端恢复

- 管理端和大屏端都使用 500ms 起始、指数退避至 8s 的重连；收到 `ready` 后以快照覆盖显示状态。
- 大屏连接本地维护已揭晓 `draw_id` 集合和按 ID 排序的待播队列；ready 中的 draw 只作为已揭晓基线，不进入动画队列。
- `lottery.draw.error` 只显示错误提示，不改变大屏揭晓状态；`lottery.reset` 清除集合、队列、当前揭晓和名单。
- 浏览器页面刷新后不回放 ready 历史；只有 ready 之后收到的新 `lottery.drawn` 才播放。

## 回滚和测试重点

- 回滚只需停止新 WS 路由和页面；保留新表不会影响既有活动、参与者、聊天和弹幕查询。
- 测试覆盖管理员鉴权/活动隔离、公开脱敏、事务提交后广播、并发库存、request 幂等、候选规则、错误不动画、重置、配置广播、断线 ready 和事件去重。
