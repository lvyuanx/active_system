# 审核交接

任务：TASK-v1 聊天表情包端到端支持独立交付审核。

输入版本：TASK-v1；HEAD `99828b71566afcb26f66d87ccbace56958f2de33`；tree `89fbfa0612b89a21520616a544bccac55da9b3af`；补丁 SHA-256 `5e893b65aac5227dbfd28181f102c4a52b133b264c2fe8e6b6cddda76c6af8b1`。

状态：completed

结论：CHANGES_REQUIRED

证据：

- 补丁 SHA-256 与工作包声明一致，HEAD/tree 未漂移。
- SQLite 在 `apps/backend/app/core/database.py` 创建表情表并增量增加 `message_type/sticker_id`，旧消息默认为 `text`。
- 活动、权限和发送状态检查位于 `apps/backend/app/modules/chat/service.py`；公开媒体按活动、表情和版本校验位于 `apps/backend/app/modules/chat/stickers.py`。
- HTTP 与 WebSocket 使用同一消息模型；弹幕广播白名单不包含发送者字段。
- 后端、管理端、大屏和三端类型检查已有通过证据；根项目文档及受影响模块 AGENTS.md 已同步。

变更文件：无；本次审核未修改工作区。

风险或阻塞：

- 高：审核发现大屏图片失败时仍沿用窄图片宽度，竖图会截断兼容 `[表情] 名称`；已由开发修复为图片宽度和回退正文宽度的较大值，并补充定向测试。
- 高：审核发现媒体路径校验未拒绝命名空间目录符号链接；已由开发补充 namespace 根符号链接拒绝和测试。
- 高：原 ARCHITECTURE-v1 由主 Agent 代写，不能作为有效架构角色交接；正在重新获取架构角色复核。
- 高：原任务图的集成依赖和 AC 映射不完整；正在重建 AC-001 至 AC-015 映射及重新测试/集成证据。
- 中：此前测试覆盖未包含合法 JPG、迁移后文本发送、命名空间符号链接；本轮已补充 JPG、迁移后文本和符号链接测试。真实浏览器视口验收、大屏失败 DOM 测试和部分禁言/停用表情专用测试仍需独立验收确认。

下一步：待有效架构交接后重新封存开发/测试/集成证据，再执行独立审核和用户场景验收。
