# 弹幕模块说明

## 模块简介

`danmaku` 提供按 `activity_id` 隔离的管理员配置、桌面工具 token 认证、消息补齐和实时弹幕广播。

## 目录说明

- `service.py`：设置默认值和校验、SQLite 懒初始化、版本化 HMAC token、只读会话与消息游标查询。
- `router.py`：管理员配置/token 接口，以及桌面工具 HTTP/首帧认证 WebSocket 协议。
- `manager.py`：单进程活动弹幕监听连接和设置/消息广播。

## 数据流

首次管理端读取会创建 `activity_danmaku_settings` 默认记录。token 格式绑定活动 ID 和当前版本，数据库仅保存版本；
重新生成 token 会递增版本并关闭活动的现有弹幕连接；manager 同时记录最低有效版本，因此轮换与连接加入房间
交错时，旧版本也不能在关闭广播之后重新加入。聊天模块在消息成功落库后调用 `broadcast_message`，只传递正文摘要。

## 注意事项

- 弹幕 token 是只读凭证，不能替代管理员或活动用户 JWT。
- `DANMAKU_TOKEN_SECRET` 为空时回退使用 `JWT_SECRET`，签名比较必须保持常量时间。
- 当前 manager 为进程内实现，多副本部署需要替换为共享消息总线。
