任务：TASK-v2 管理端真实聊天室弹幕测试
输入版本：TASK-v2；输入快照为 HEAD 52a164fa63a012f16234de966de137edda5970a6 与当前已登记的弹幕桌面工具改动
状态：completed
结论：已完成管理端真实弹幕测试控制、后端多用户真实聊天发送、活动状态保护和端到端回归。
证据：

- `apps/backend/app/modules/danmaku/testing.py` 准备并复用 6 个带标记的测试活动用户，调用 `create_message`
  写入 `activity_chat_messages`，再广播聊天室完整事件和弹幕摘要。
- `apps/backend/app/modules/danmaku/router.py` 增加测试状态、开启和关闭管理员接口；开启仅允许 `open` 活动，
  每个活动最多一个运行任务。
- `apps/admin-web/src/views/danmaku/DanmakuTestPanel.vue` 已接入 `index.vue`，展示真实聊天室说明、运行状态及
  开启/关闭按钮。
- `python -m pytest -q apps/backend`：29 passed；新增用例确认聊天室 WebSocket、弹幕 WebSocket 的消息 ID/正文
  对应一致、历史可读、两个测试用户轮换、重复启停和非 open 活动拒绝。
- `pnpm typecheck`、`pnpm build`、`pnpm --filter @active/admin-web build`、`pnpm --filter @active/screen-web test`
  和 Electron 类型/脚本检查均已通过；最终 NSIS 回归在收尾阶段执行。

变更文件：

- `apps/backend/app/main.py`
- `apps/backend/app/modules/danmaku/{router.py,testing.py,AGENTS.md}`
- `apps/backend/app/modules/chat/AGENTS.md`
- `apps/backend/tests/test_danmaku.py`
- `apps/admin-web/{AGENTS.md,src/api/client.ts,src/views/danmaku/AGENTS.md,src/views/danmaku/index.vue}`
- `apps/admin-web/src/views/danmaku/DanmakuTestPanel.vue`
- `README.md`、`WIKI.md`、`MEMORY.md`

风险或阻塞：测试消息是真实运营演示数据，会保留在活动聊天记录中；测试任务与现有广播仍是单进程内存实现。
本次没有引入本地假预览，也没有改变用户端聊天协议或弹幕摘要字段。架构/测试/审核角色的独立交接仍需完成。
下一步：等待架构门禁后执行独立测试、只读审核、产品验收和最终清理。

## 实现摘要

测试任务在活动维度由 `DanmakuTestManager` 管理，使用保留手机号查找测试用户，避免把同名普通用户误当测试用户。
每次真实写入前复查活动状态；停止接口取消任务并等待退出，应用 lifespan 结束时统一清理任务。管理端 API 只使用
管理员 Bearer Token，前端不保存测试状态或测试用户凭证。

## 方案偏差

实现按架构方案直接复用聊天 service，而不是创建内部 WebSocket 客户端；这是为了保持真实持久化和广播语义、避免
额外 JWT/连接生命周期，并不改变客户端可观察的聊天室协议。
