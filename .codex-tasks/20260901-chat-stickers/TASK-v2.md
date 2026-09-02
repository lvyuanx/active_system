# TASK-v2 测试弹幕随机表情

## 任务状态

- 任务等级：T4
- 版本：TASK-v2
- 来源：TASK-v1 聊天表情包端到端支持完成后的增量需求
- 目标模块：后端 `danmaku.testing` 测试消息生成链路
- 状态：completed

## 目标

管理端开启真实弹幕测试后，在当前活动存在启用表情包时，让测试消息按固定概率随机发送表情消息；无可用表情或表情在发送前被下架时，继续发送文本，保证测试任务不中断。

## 范围

- 在每条测试消息生成前读取当前活动启用表情库。
- 约 30% 的消息进入表情分支，并随机选择一个启用表情。
- 复用聊天 service 创建 sticker-only 消息，并沿用聊天室和弹幕广播链路。
- 表情创建校验因并发下架失败时回退对应文本消息。
- 为选择、广播、无表情和竞态回退增加后端自动化测试，并同步弹幕模块说明和项目知识文档。

## 非目标

- 不新增管理端概率配置。
- 不改变普通用户聊天、弹幕协议、图片资源或表情库管理接口。
- 不支持文字与表情混合消息。

## 验收标准

- **AC-016**：Given 当前活动存在启用表情；When 测试消息命中表情随机分支；Then 发送 sticker-only 消息，聊天室和弹幕广播均携带 `message_type` 与 `sticker`。
- **AC-017**：Given 当前活动没有启用表情；When 测试任务发送消息；Then 始终发送原有文本消息，测试任务正常运行。
- **AC-018**：Given 测试选择表情后管理员将其下架；When 创建消息校验失败；Then 当前消息回退为文本，测试任务不退出。
- **AC-019**：Given 测试任务持续运行；When 活动启用表情库发生变化；Then 后续消息按发送前读取到的启用列表选择，不继续使用已下架表情。

## 风险与验证

- 表情列表查询和消息创建之间存在下架竞态，必须保留 `create_message` 的最终启用校验并捕获 `ChatInvalidStickerError`。
- 验证命令：`python -m pytest -q apps/backend`、`pnpm typecheck`、`git diff --check`。

## 验证结果

- `python -m pytest -q apps/backend`：71 passed，退出码 0。
- `pnpm typecheck`：4 个 workspace 完成，退出码 0。
- `pnpm build`：4 个 workspace 构建完成，退出码 0。
- `pnpm --filter @active/screen-web test` 和 `pnpm --filter @active/admin-web test:chat-stickers`：均通过。
- `git diff --check`：退出码 0；仅报告 Windows 换行转换提示。
