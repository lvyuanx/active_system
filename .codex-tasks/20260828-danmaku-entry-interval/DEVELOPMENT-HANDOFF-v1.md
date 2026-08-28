任务：按 TASK-v1 实现弹幕完整进入视口后的同轨道间隔入场。
输入版本：TASK-v1；架构输入为 ARCHITECTURE-v1；输入快照为 HEAD-9ec1caa4-dirty-20260828-entry-interval。
状态：completed
结论：已完成独立入场间隔配置、旧 SQLite 迁移、ready gate、长弹幕追赶保护、管理端接入和三端类型同步；现有队列超时规则保持独立。
证据：
- `apps/backend/app/core/database.py:53,109-113` 增加 `entry_interval_seconds` 默认值、CHECK 范围和旧表增量迁移。
- `apps/backend/app/modules/danmaku/service.py:20,35,126-201` 完成默认值、Pydantic 校验、读写映射和更新 SQL；旧请求省略字段时使用 1.0 秒。
- `apps/screen-web/src/components/realtime/danmaku-layout.ts:53-78,164-190` 按 `durationMs * width / (viewportWidth + width)` 计算完整进入时间，并在同轨道 ready gate 通过后继续执行全轨迹碰撞预测。
- `apps/screen-web/src/components/realtime/DanmakuOverlay.vue:176-201` 同时读取入场间隔与队列最大等待，向轨道选择器传入当前时间和间隔；当前弹幕仍由 CSS transform 动画负责位移。
- `apps/admin-web/src/views/danmaku/index.vue:91-113,209-215` 增加“入场间隔”并将原字段标为“队列最大等待时间”；范围分别为 0.1–5.0 秒和 0.5–5.0 秒。
- `apps/admin-web/src/api/client.ts:42-50`、`apps/screen-web/src/api/client.ts:4-12`、`apps/danmaku-desktop/src/main.ts:14-22` 已同步公开 session/settings 类型。
变更文件：后端 schema/service/tests，screen-web 几何/渲染器/测试，管理端设置/静态测试，Electron session 类型，模块文档、项目知识和任务证据。
风险或阻塞：字体回退可能造成少量 Canvas 宽度差异，仍由 8px 间距和保守碰撞判断兜底；已有用户弹幕工具会话未被接管。
下一步：交由测试、审核和验收阶段复核。
