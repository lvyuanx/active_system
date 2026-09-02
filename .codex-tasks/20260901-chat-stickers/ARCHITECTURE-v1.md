# ARCHITECTURE-v1 聊天表情包端到端支持

## 架构门禁

- 输入版本：TASK-v1
- 方案版本：ARCHITECTURE-v1
- 结论：completed
- 方案来源：主 Agent 依据冻结任务单和源码补充；架构角色线程在两次等待及一次收束提示后未返回，已停止。
- 实现模式：单一 `SERIAL_SHARED_WRITE` 写入路径；不创建并行 worktree，避免父任务权限无法收紧造成主树漂移。

## 模块边界

- `apps/backend/app/modules/chat/` 负责表情库、聊天消息模型、活动用户列表、WebSocket 发送和消息序列化。
- `apps/backend/app/modules/files/` 提供可复用的命名空间媒体存储、真实 MIME 校验、随机 key、安全路径和按命名空间孤儿扫描。
- `apps/backend/app/modules/danmaku/` 复用聊天消息的表情摘要，向弹幕 WebSocket 和 HTTP 补齐输出脱敏消息。
- `apps/admin-web/src/views/stickers/` 负责活动级批量上传、预览、下架和恢复；通过 `ActivitySidebar` 接入活动管理壳。
- `apps/user-web/src/views/activity/chat.vue` 负责表情列表加载、选择器、图片气泡和 sticker-only WebSocket 发送。
- `apps/screen-web/src/components/realtime/` 负责图片/GIF 弹幕 DOM 展示和按图片比例测量；已有排序、队列和调度器保持不变。

## 数据模型与迁移

新增 `activity_chat_stickers`：

- `sticker_id` 主键、`activity_id` 外键级联、`name`、`image_id`、`image_storage_key`、`image_mime`、`image_size`、
  `image_width`、`image_height`、`is_enabled`、`created_at`。
- `image_id` 和 `image_storage_key` 均唯一；按 `activity_id, is_enabled, sticker_id` 建索引。

`activity_chat_messages` 增加：

- `message_type TEXT NOT NULL DEFAULT 'text'`，允许 `text`/`sticker`。
- `sticker_id INTEGER NULL`，外键指向表情记录；保留既有 `body` 非空约束。
- 既有消息自动成为文本；表情消息的 `body` 保存 `[表情] 名称` 兼容占位，新客户端使用嵌套表情对象。

`init_database` 在 `BEGIN IMMEDIATE` 内先创建表，再按列检查并增量 `ALTER TABLE`，最后创建新增索引；不重建、不删除旧聊天表。
服务层额外保证文本不能带 `sticker_id`、表情必须引用当前活动启用记录。软下架不删除行，避免历史外键失效。

## 媒体与安全

- 表情文件存储到 `MEDIA_ROOT/chat-stickers/{image_id}.{ext}`；奖品图片仍固定使用 `lottery-prizes`，不接受 GIF。
- 扩展媒体服务支持显式 namespace 和允许格式映射；表情允许 JPEG、PNG、WebP、GIF，均做扩展名、声明 MIME、Pillow 真实格式、大小和解压炸弹校验。
- 上传先写 `.tmp`，校验后原子移动；数据库绑定失败删除新文件。
- 图片接口只返回相对公开 URL，不返回 storage key；要求当前 `image_id` 版本参数，按 `activity_id + sticker_id + image_id` 查询。
- 图片读取不需要管理员凭证，因为公开弹幕 `<img>` 无法附带 Bearer；列表和发送仍分别要求活动用户 JWT 和当前活动上下文。
- 启动及表情操作按 namespace 扫描孤儿文件；下架记录仍是引用，因此历史媒体不会被清理。

## HTTP 与 WebSocket 契约

管理员接口需要超级用户 JWT：

- `GET /admin/activities/{activity_id}/chat/stickers`：返回全部记录及启用状态。
- `POST /admin/activities/{activity_id}/chat/stickers`：multipart `file`，可选 `name`；单请求一个文件。
- `DELETE /admin/activities/{activity_id}/chat/stickers/{sticker_id}`：软下架。
- `POST /admin/activities/{activity_id}/chat/stickers/{sticker_id}/restore`：恢复启用。

用户和公开接口：

- `GET /activities/{activity_id}/chat/stickers`：活动用户 JWT，只返回启用记录。
- `GET /activities/{activity_id}/chat/stickers/{sticker_id}/image?v={image_id}`：公开、版本化图片读取，允许读取已下架但仍被历史引用的记录。

公共对象字段：

```json
{
  "sticker_id": 1,
  "name": "开心",
  "image_url": "/api/v1/activities/{activity_id}/chat/stickers/1/image?v={image_id}",
  "mime": "image/gif",
  "width": 256,
  "height": 256
}
```

聊天消息在原字段上增加 `message_type` 和 `sticker`；文本消息为 `message_type=text, sticker=null`，表情消息发送
`{"type":"message.send","sticker_id":1}`，禁止同时提供 body。非法 ID、跨活动、下架表情返回结构化 `invalid_sticker`，
既有文本校验错误保持 `invalid_body`。

弹幕实时摘要和 HTTP 补齐使用相同的 `message_type/sticker/body` 字段，但继续排除发送者字段。`danmaku.ready`、token、桌面
IPC 和消息 ID 排序协议不变，旧客户端收到的 `body` 仍是可读占位。

## 前端实现

- 管理端新增 `/activities/:activityId/stickers`，多选文件后按选择顺序串行调用单文件上传接口；每个文件独立显示校验、上传或失败状态。
  名称默认使用文件名 stem，列表支持预览、软下架和恢复。
- 用户端在聊天 composer 增加表情按钮和网格；登录后加载当前活动启用表情，点击直接发送；表情气泡最大 120×120px，图片错误回退 `body`。
- 大屏弹幕使用 `<img>` 渲染 GIF/图片，显示高度等于当前弹幕 `font_size`，宽度按原始宽高比计算并限制为 `6 × font_size`；
  CSS 使用同一宽度，`danmaku-layout.ts` 使用该值参与现有碰撞和入场间隔算法。加载失败显示 `body`，不引入逐帧 JS 位移。
- 不修改 Electron 主进程，因为会话字段和 IPC 只需透传，额外消息字段由 screen-web 消费。

## 失败、回滚与测试重点

- 单个批量文件失败不影响同批其他文件；服务端失败不写入可用记录并清理临时/孤儿文件。
- 图片版本不匹配、错误活动或不存在记录统一 404；管理员和活动用户凭证不能互换。
- 表情下架只改变 `is_enabled`，因此可恢复；历史消息查询不依赖启用列表。
- 迁移为新增表/列，旧代码可忽略新增字段；回滚代码不会删除新表和媒体，旧版本仍可读取旧文本，新增表和文件由后续迁移处理。
- 测试必须覆盖格式/MIME/大小、活动与权限隔离、旧库迁移、WebSocket/历史/弹幕双通道、下架保留、GIF 及图片宽度/失败回退。

## 方案取舍

- 不把表情二进制或 data URL 放入消息；使用活动隔离的版本化公开资源引用，避免消息膨胀并让多端共享缓存。
- 不把 GIF 加入奖品媒体白名单；通过显式 namespace 复用安全能力，避免改变已有抽奖图片契约。
- 不硬删除被历史引用的资源；软下架以可恢复性和历史完整性优先，符合 TASK-v1 的 AC-012。
