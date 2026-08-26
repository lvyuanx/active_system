# ARCHITECTURE-v1：活动聊天室实施架构

## 交接

- 任务：TASK-v1 活动独立聊天室与移动端三栏导航
- 输入版本：TASK-v1
- 状态：completed
- 架构门禁：通过
- 变更文件：无（架构节点只读）
- 隔离资格：INELIGIBLE；当前工作树有受保护的 tracked dirty diff，开发使用主工作树串行写入。

## 模块边界

- 新增 `apps/backend/app/modules/chat/`：`router.py` 负责 HTTP/WS，`service.py` 负责消息查询、写入和活动状态校验，`manager.py` 负责进程内房间连接。
- `participants` 提供稳定活动用户 principal，聊天模块不按用户名确定发送者。
- `database.py` 的启动 schema 增加消息表和索引，使用 `CREATE TABLE IF NOT EXISTS` 兼容现有 SQLite。
- 用户端使用活动父壳管理活动加载、Token、登录门禁和 Tabbar，子页为首页、聊天、我的；为活动视图补充模块说明。

## 数据与身份

```sql
activity_chat_messages(
  message_id INTEGER PRIMARY KEY AUTOINCREMENT,
  activity_id TEXT NOT NULL REFERENCES activities(activity_id) ON DELETE CASCADE,
  activity_user_id INTEGER NOT NULL REFERENCES activity_users(id) ON DELETE CASCADE,
  body TEXT NOT NULL CHECK(length(body) BETWEEN 1 AND 500),
  created_at TEXT NOT NULL
)
```

建立 `(activity_id, message_id)` 游标索引和 `(activity_id, username, id)` 查询索引。时间保存 UTC ISO 字符串。

新 JWT 在保留 `sub=username`、`activity_id` 的同时增加整数 `activity_user_id`；活动用户响应增加稳定 ID 和 `joined_at`。
旧 Token 缺少该 claim 时，只有同活动用户名唯一才兼容；重名返回 401 要求重新登录。带 ID 但不匹配活动或用户时不得回退。

## HTTP 协议

`GET /api/v1/activities/{activity_id}/chat/messages` 使用活动 Bearer 鉴权，`limit` 默认 50、最大 100；`before_id` 和
`after_id` 互斥。无游标或 `before_id` 取最近消息，`after_id` 取断线后的消息；数据库可多取一条判断 `has_more`，最终按 ID 正序返回。

```json
{
  "items": [{
    "message_id": 1,
    "activity_id": "…",
    "sender_activity_user_id": 2,
    "sender_username": "小明",
    "body": "内容",
    "created_at": "2026-08-25T12:00:00+00:00"
  }],
  "has_more": true
}
```

## WebSocket 协议

- `WS /api/v1/activities/{activity_id}/chat/ws`
- 首帧：`{"type":"auth","token":"<activity token>"}`；Token 不放查询字符串。
- 成功：`chat.ready`；发送：`message.send`；持久化后广播 `message.created`。
- 正文先 `strip()`，长度 1–500；仅 `open` 允许发送，其他状态返回 `read_only`。协议错误、认证错误和非法正文返回结构化 `chat.error`。
- 认证超时/无效凭证以 1008 关闭；房间为进程内 `dict[activity_id, set[WebSocket]]`，用 asyncio 锁保护成员，SQLite 操作使用 `asyncio.to_thread`。

## 用户端与代理

- 嵌套路由为 `/activity/:activityId`、`/activity/:activityId/chat`、`/activity/:activityId/me`；未登录显示门禁，登录后显示 Vant Tabbar。
- 聊天初次加载最近 50 条，按 `message_id` 去重正序；断线按 1/2/4/8/10 秒重连，鉴权后以 `after_id` 补拉。
- “我的”展示活动名称、状态、活动用户 ID、用户名、加入时间；退出只清除当前活动 Token。
- Nginx `/api/` 增加 HTTP/1.1、Upgrade、Connection upgrade 和长连接读取超时。

## 测试重点

覆盖稳定身份和旧 Token、历史游标、正文校验、状态只读、跨活动 HTTP/WS 拒绝、双客户端广播/持久化、前端路由门禁/退出/重连补拉；保留现有 pytest 和 user-web typecheck 基线。
