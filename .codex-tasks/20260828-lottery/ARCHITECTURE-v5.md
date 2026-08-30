# ARCHITECTURE-v5：奖品图片上传与安全媒体访问

任务：为 TASK-v5 设计奖品图片上传、持久化、权限隔离、公开展示和清理方案。
输入版本：TASK-v5
状态：completed
结论：采用独立媒体接口，现有抽奖配置 PUT 继续保持纯 JSON；图片为可选字段，服务端使用随机存储标识和安全图片路由，不改变库存、中奖记录、抽奖资格或既有开奖事件语义。
证据：现有 `lottery_prizes` 无图片字段，`apps/backend/app/modules/files/__init__.py` 为空；配置响应、快照、开奖对象和管理端/大屏类型均需增加可选图片 URL。
变更文件：本交接只读；下游预计修改后端 database/config/files/lottery、管理端 lottery、大屏 lottery、测试、部署与项目知识文档。
风险或阻塞：无架构阻塞。跨文件系统与 SQLite 无法形成单事务，采用“验证临时文件 -> 原子落盘 -> 事务绑定 -> 提交后清理旧文件”，并以启动孤儿扫描补偿崩溃窗口。
下一步：开发按本方案实现，随后执行上传安全、权限、活动隔离、替换删除、清理、WebSocket 回归和浏览器验收。

## 模块边界

- `modules/files/` 负责大小/真实图片格式校验、临时文件、随机存储标识、原子移动、读取和孤儿扫描，不理解奖品业务。
- `modules/lottery/` 增加可选图片模型，按 `activity_id + prize_id` 查询/绑定，生成管理员和公开安全 URL；不改变库存和开奖流程。
- 管理端 lottery 维护本地预览、待保存、替换、移除和错误状态；未持久化新奖品先保存后上传。
- 大屏 lottery 消费可选图片 URL，图片加载失败隐藏图片但保留文字、库存、中奖动画和 WebSocket。

## 接口契约

- `POST /api/v1/admin/activities/{activity_id}/lottery/prizes/{prize_id}/image`：超级管理员 multipart 字段 `file`，上传/替换并返回 `{image_url, image_id, mime, size}`（不返回 storage key）。
- `DELETE /api/v1/admin/activities/{activity_id}/lottery/prizes/{prize_id}/image`：清空绑定，返回 `image_url: null`。
- `GET /api/v1/admin/activities/{activity_id}/lottery/prizes/{prize_id}/image`：超级管理员读取，`Cache-Control: no-store`。
- `GET /api/v1/activities/{activity_id}/lottery/prizes/{prize_id}/image?v={image_id}`：公开只读图片，校验当前活动/奖品绑定，旧版本统一 404。
- 现有 `PUT /admin/activities/{activity_id}/lottery` 不携带二进制；请求不含图片字段时保留现有绑定。
- `LotteryPrize`、公开/管理员快照及 `LotteryDraw` 增加可选 `image_url`/`prize_image_url`；显式白名单裁剪内部字段。

## 数据库迁移

在 `lottery_prizes` 增加可空 `image_id`、`image_storage_key`、`image_mime`、`image_size` 字段，并对非空标识加唯一索引。
新库直接创建，旧库在现有 `BEGIN IMMEDIATE` 初始化迁移中按 `PRAGMA table_info` 增量 `ALTER TABLE`；历史值 NULL 表示无图。
不修改 `lottery_draws`、库存计算和中奖外键。删除奖品前先读取旧 storage key，业务提交后再清理文件。

## 存储和访问

- 默认 `MEDIA_ROOT=./data/media`，奖品图位于 `MEDIA_ROOT/lottery-prizes/`，临时文件位于 `MEDIA_ROOT/.tmp/`。
- 文件名由服务端随机生成 UUID/随机扩展名；不使用用户文件名、路径或内容作为路径。
- 不直接挂载媒体目录为静态目录；读取必须通过活动/奖品绑定查询和安全路径解析。
- 响应使用已验证 MIME、`X-Content-Type-Options: nosniff`；公开读取可缓存，管理读取不缓存。
- Docker/Nginx 将媒体目录作为数据卷并允许至少 6 MiB 请求体，最终 5 MiB 限制仍由后端执行。

## 上传验证

只接受 `.jpg`/`.jpeg`、`.png`、`.webp`，大小上限 `5 * 1024 * 1024` 字节；分块写入临时文件并多读 1 字节检测超限。
使用 Pillow（或等价可靠解码器）实际打开并验证 JPEG/PNG/WebP，与扩展名及声明 MIME 一致；SVG、HTML、脚本、可执行文件、
base64 和外部 URL/path 均拒绝。失败删除临时文件、不更新数据库、不覆盖原图。

## 权限、隔离和清理

- 管理三个接口统一依赖 `require_superuser`；每次 SQL 同时带 `activity_id` 与 `prize_id`，跨活动/错误资源返回统一安全错误。
- 公开图片不需凭证，但只返回当前奖品的公开投影，不含管理员 JWT、绝对路径、数据库路径、storage key 或内部目录。
- 替换：验证临时文件 -> 生成新标识并原子移动 -> `BEGIN IMMEDIATE` 再次校验归属并写绑定 -> 提交后删除旧文件。
- 删除：事务内置 NULL，提交后删除旧文件；删除失败记安全日志，启动扫描重试。
- 绑定失败删除新文件；扫描只处理媒体目录和临时目录中超过保护时间且无数据库引用的文件，不跟随符号链接、不越界。
- 文件删除/清理失败不回滚已提交奖品业务，不影响库存和中奖记录；清理任务可重试。

## 快照、大屏、兼容和回滚

- `lottery.ready`、`lottery.config.updated`、`lottery.drawn`、`lottery.reset` 可带可选安全图片 URL；公开快照继续裁剪手机号/名单等敏感字段。
- 大屏图片存在且加载成功时显示缩略图/中奖图；无图、404 或加载失败隐藏图片并保留现有文字和动画。
- 历史数据库、旧配置 PUT、无图开奖和重置保持兼容；图片替换/删除不删除奖品、奖项或中奖记录。
- 回滚可停止图片路由和前端展示并保留可空字段/文件，旧抽奖数据无需重建。

## 测试重点

覆盖合法三格式、5 MiB 边界/超限、伪造 MIME/扩展名、SVG/HTML/脚本拒绝，未登录/活动用户/管理员权限，跨活动访问，
上传失败原状态、替换旧 URL 404、删除后 404、孤儿扫描和清理重试，配置 PUT 兼容，管理员/公开快照裁剪，WebSocket/库存/幂等/重置回归，
管理端预览/替换/移除和 multipart 请求，以及大屏图片和加载失败回退。
