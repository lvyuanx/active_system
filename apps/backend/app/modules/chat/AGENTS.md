# 聊天模块说明

## 模块简介

`chat` 为活动参与用户提供按 `activity_id` 隔离的持久化纯文本聊天室。

## 主要职责

- `service.py` 负责活动用户授权后的消息游标查询、状态校验和 SQLite 持久化。
- `router.py` 提供历史消息 HTTP 接口和首帧认证的 WebSocket 协议。
- `manager.py` 维护单进程活动房间连接并广播新消息。

## 数据流与接口

消息写入 `activity_chat_messages`，通过 `activity_user_id` 关联参与用户；HTTP 读取支持 `before_id` 和
`after_id` 游标，WebSocket 在持久化成功后广播 `message.created`。同一时刻还会向 `danmaku` 模块广播仅包含
消息 ID、活动 ID、正文和创建时间的摘要，聊天协议本身不变。只有 `open` 活动可发言，`closed`/`ended` 活动保持只读。

## 注意事项

身份必须使用参与用户稳定 ID，不按用户名推断发送者。当前房间广播为进程内实现，多副本部署时需要接入共享消息总线。
