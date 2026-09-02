# 聊天模块说明

## 模块简介

`chat` 为活动参与用户提供按 `activity_id` 隔离的持久化聊天室和活动级表情包能力。

## 主要职责

- `service.py` 负责活动用户授权后的消息游标查询、文本/表情消息状态校验和 SQLite 持久化。
- `stickers.py` 负责表情库 CRUD、媒体绑定、启用状态和版本化公开图片文件。
- `router.py` 提供表情库/图片 HTTP 接口、历史消息 HTTP 接口和首帧认证的 WebSocket 协议。
- `manager.py` 维护单进程活动房间连接并广播新消息。

## 数据流与接口

消息写入 `activity_chat_messages`，通过 `activity_user_id` 关联参与用户；HTTP 读取支持 `before_id` 和
`after_id` 游标，WebSocket 在持久化成功后广播 `message.created`。文字消息使用 `body`，表情消息额外保存
`message_type=sticker` 和 `sticker_id`，并用 `[表情] 名称` 作为旧客户端兼容正文。同一时刻还会向 `danmaku`
模块广播不含发送者身份但包含表情资源摘要的消息。弹幕测试继续调用同一持久化与广播链路。

管理员通过 `/admin/activities/{activity_id}/chat/stickers` 批量逐文件上传、下架和恢复表情；活动用户通过
`/activities/{activity_id}/chat/stickers` 读取启用列表。公开图片使用带 `image_id` 版本参数的活动级 URL，
允许历史消息在表情下架后继续显示。
只有 `open` 活动且参与用户处于 active、未 muted 状态时可发言；禁言发送返回 `chat.error` 的 `muted`，停用后的现有连接
返回 `unauthorized` 并关闭。

## 注意事项

身份必须使用参与用户稳定 ID，不按用户名推断发送者。表情发送只能单独携带 `sticker_id`，不能和文字混合；
只有当前活动启用的表情可以发送。当前房间广播为进程内实现，多副本部署时需要接入共享消息总线。
