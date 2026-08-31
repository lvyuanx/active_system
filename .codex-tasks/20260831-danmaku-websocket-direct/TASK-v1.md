# TASK-v1：弹幕 WebSocket 完整消息直达

任务等级：T4（`screen-web` 单模块行为变更；沿用既有后端协议）

## 目标

- 正常连续实时消息直接使用 WebSocket 已携带的完整消息进入弹幕队列。
- 消除每条实时消息对应的 `/danmaku/messages` HTTP 请求。
- 保留首次连接、断线重连和消息 ID 缺口的可靠恢复能力。

## 用户场景

- 用户发送一条或连续多条弹幕时，渲染器直接消费 WebSocket 消息并进入现有滚动队列。
- WebSocket 消息乱序或中间消息遗漏时，渲染器通过 HTTP 补齐缺口并按消息 ID 展示。
- 首次连接或断线重连后，渲染器恢复断线期间的新消息，但不回放基线之前的历史消息。
- 同一消息因 WebSocket 重复、HTTP 补齐或恢复交错到达时，只展示一次。

## 范围

- 调整 `screen-web` 弹幕实时消息消费行为。
- 保留现有 WebSocket、session、ready、重连、队列、轨道和渲染流程。
- 自动化验证覆盖连续实时无 HTTP、缺口补齐、重复去重、首次连接和断线恢复。
- 同步更新受影响的 `screen-web` 模块说明及项目知识文档。
- 后端协议和生产代码仅作为兼容性验证对象，不纳入修改范围。

## 非目标

- 不修改后端 WebSocket 载荷结构，不删除 `/danmaku/messages` 接口。
- 不改变首次连接不回放历史的基线语义。
- 不改变轨道碰撞、队列容量、CSS 动画或调度器行为。
- 不处理透明窗口、GPU 或 DWM 渲染卡顿。
- 不新增跨应用共享协议或消息总线。

## 约束

- WebSocket 弹幕消息继续使用 `message_id`、`activity_id`、`body`、`created_at` 四字段。
- `message_id` 等于当前连续游标加一时，直接消费完整消息，不发 HTTP。
- 检测到消息 ID 缺口时，HTTP 必须从当前游标补齐，不能直接抬高游标。
- ready 快照中的最大 ID 不得直接成为已处理游标。
- WebSocket、HTTP 补齐和重连恢复交错时必须按消息 ID 排序并去重。
- 活动数据继续按 `activity_id` 隔离。
- 若实现需要修改后端协议或新增服务端字段，必须暂停并重新评估任务等级。

## 验收标准

### AC-001：连续消息直接消费

Given 当前连接已完成 ready 恢复，连续游标为 `N`，收到完整且 `message_id=N+1` 的 WebSocket 事件  
When 渲染器处理该事件  
Then 消息直接进入弹幕队列并展示一次，不通过 HTTP 获取消息正文。

### AC-002：连续实时消息不得发 HTTP

Given 恢复阶段已完成，WebSocket 连续推送 `N+1` 至 `N+k` 且没有缺口  
When 渲染器处理这一批事件  
Then 所有消息按 ID 各展示一次，不新增 `/danmaku/messages` HTTP 请求。

### AC-003：消息缺口补齐

Given 当前连续游标为 `N`，WebSocket 先收到 `N+2`，未收到 `N+1`  
When 渲染器检测到缺口并完成恢复  
Then HTTP 从 `after_id=N` 补齐，缺失消息和高 ID 消息按 ID 各展示一次，游标不跳过 `N+1`。

### AC-004：首次连接与断线重连恢复

Given 首次连接或断线重连前客户端已有当前游标，期间产生了游标之后的新消息  
When 收到 `danmaku.ready` 并完成恢复  
Then 从当前游标补齐遗漏消息，不展示基线之前的历史消息；ready 最大 ID 不单独推进游标，恢复后的连续
WebSocket 消息继续直接消费。

### AC-005：乱序、重复与恢复失败

Given 同一消息可能经 WebSocket、HTTP 或重连恢复重复到达，且 HTTP 恢复可能暂时失败  
When 事件与恢复继续处理  
Then 消息不重复、不丢失、不跳过游标；恢复成功后按 ID 各展示一次。

### AC-006：验证与文档同步

Given 实现完成  
When 执行 screen-web 测试、类型检查和后端弹幕协议回归，并检查文档  
Then 证据覆盖 AC-001 至 AC-005；`apps/screen-web/AGENTS.md` 与 `WIKI.md` 描述新链路，后端完整载荷
协议保持兼容。

## 风险、依赖与待确认

- 全局自增 `message_id` 可能因其他活动消息产生合法跳号，客户端会保守触发一次 HTTP 缺口检查。
- HTTP 恢复失败时不得丢失已缓存的高 ID WebSocket 消息。
- 依赖既有 `danmaku.message.created` 完整消息载荷和 `/danmaku/messages?after_id=` 恢复接口。
- 待确认项：无；本任务单进入开发阶段后冻结。
