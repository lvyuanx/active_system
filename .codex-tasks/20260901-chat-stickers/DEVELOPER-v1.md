# 开发交接

任务：

实现 TASK-v1 的聊天表情包端到端支持，覆盖活动级媒体库、增量数据库迁移、聊天消息协议、管理端上传、移动端发送和弹幕滚动。

输入版本：

TASK-v1；架构交接 ARCHITECTURE-v1；工作包 wp-chat-stickers。实现工作在共享主工作树串行完成，原因码为 PERMISSION_NOT_READONLY。

状态：completed

结论：

已完成生产代码、前端界面、测试资产和模块文档更新。表情包按活动隔离保存，支持 PNG/JPG/WebP/GIF、单文件 5 MiB 限制、真实 Pillow 格式校验、版本化公开资源和软下架；旧文本消息迁移后默认为 text，表情消息保留兼容 body。管理端支持多文件逐个上传及逐项结果，移动端支持独立表情消息，screen-web 弹幕支持 GIF 动画、图片宽度参与调度和加载失败文字回退。

证据：

- `python -m pytest -q apps/backend`：64 passed，11 warnings。
- `python -m pytest -q tests/test_chat_stickers.py`（在 `apps/backend` 目录）：4 passed。
- `pnpm --parallel --filter @active/admin-web --filter @active/user-web --filter @active/screen-web typecheck`：通过。
- `pnpm build`：四个工作区构建通过；仅有既有 Rollup 注释和 chunk 体积提示。
- `pnpm --filter @active/screen-web test`：消息顺序、调度器、布局、表情、抽奖相关测试全部通过。
- `pnpm --filter @active/admin-web test:chat-stickers`：通过。
- `git diff --check`：通过。

变更文件：

- 后端：`apps/backend/app/core/database.py`、`app/modules/files/service.py`、`app/modules/chat/stickers.py`、`app/modules/chat/service.py`、`app/modules/chat/router.py`、`app/modules/danmaku/service.py`、`app/modules/danmaku/manager.py`、路由/启动接线及后端测试。
- 管理端：表情包 API、活动侧栏和路由、`apps/admin-web/src/views/stickers/` 页面及静态测试。
- 移动端：聊天 API、表情选择器、图片气泡和失败回退。
- 大屏端：弹幕消息模型、图片滚动渲染、宽度/碰撞调度、样式和测试。
- 文档：根目录项目知识文件及受影响模块 `AGENTS.md`。

风险或阻塞：

- 尚未在真实浏览器窗口执行管理端、390×844 移动端和 1280×720 大屏的人工验收；自动化构建与静态测试已覆盖对应代码路径。
- `test_danmaku.py` 与 `test_lottery.py` 原本已超过 500 行，本次仅做必要的期望值和测试隔离修改，未进行无关拆分。

下一步：

请测试角色按 TASK-v1/AC-001 至 AC-015 复核后端、前端和文档，随后进入集成、审核与用户场景验收。
