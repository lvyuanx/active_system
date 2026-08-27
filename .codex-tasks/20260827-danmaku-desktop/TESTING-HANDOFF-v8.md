任务：TASK-v2 管理端真实聊天室弹幕测试独立回归
输入版本：TASK-v2；WORKPACKAGE-v11 当前 HEAD/tree 和 14 项实际文件 SHA-256 已复核一致
状态：completed
结论：主工作树串行测试门禁通过；新增真实聊天、多用户、活动隔离、只读生命周期和管理员权限回归均通过。
证据：

- `python -m pytest -q apps/backend` 退出码 0，29 passed，包含真实聊天室 WebSocket、弹幕 WebSocket、历史接口、
  多测试用户、身份复用、跨活动隔离、closed/ended、运行中转只读、重复启停和无管理员权限用例。
- `pnpm --filter @active/admin-web typecheck` 退出码 0；`pnpm --filter @active/admin-web build` 退出码 0。
- `pnpm --filter @active/screen-web test` 退出码 0，message-order tests passed；`pnpm --filter @active/danmaku-desktop typecheck`
  退出码 0；launcher 与 message-order 脚本语法检查退出码 0；`git diff --check` 退出码 0。
- 静态核对确认 `testing.py` 调用 `create_message`，聊天 service 写入 `activity_chat_messages`，成功后分别调用
  `chat_manager.broadcast` 和 `danmaku_manager.broadcast_message`，且测试用户按活动保留手机号复用。
- 端到端用例验证两条 WebSocket 事件的消息 ID、活动 ID 和正文对应一致，聊天室事件包含“弹幕测试用户”发送者，
  聊天室和弹幕历史均可读；第二活动没有测试消息；停止/活动只读后不继续运行。
- WorkPackage-v11 的 14 项实际清单全部匹配；TaskGraph 已记录 peak_active_threads=1、
  peak_isolated_write_packages=0、queued_node_count=0、queue_total_duration=0、每节点队列时长、每批次时长状态、
  resource/platform/qualification 降级分类，以及无平台队列时的 raw_error/排队/出队不适用说明。

变更文件：无；测试回归阶段未修改生产代码、测试资产、业务文档或 Git 元数据。
风险或阻塞：独立 tester 子线程前两轮因工作包快照过期返回 BLOCKED，刷新 SHA-256/tree/read_scope 后第三轮未在平台时限内
形成交接；因此本文件的命令结果来自主集成者实际执行，不冒充子线程结论。浏览器未代填管理员密码，未形成认证后 UI 截图；
源代码集成、管理端构建和路由重定向检查通过。单进程任务和测试消息保留风险按 TASK-v2 记录。
下一步：只读审核员基于 TASK-v2、ARCHITECTURE-v2、WORKPACKAGE-v11 和本交接检查实现与证据；审核通过后进入验收。

## AC 映射

| AC | 结果 | 证据 |
|---|---|---|
| AC-011 | PASS | `DanmakuTestPanel.vue` 及 `index.vue` 集成标题、状态和双按钮；管理端 typecheck/build 通过。 |
| AC-012 | PASS | `open` 活动开启接口返回 running，端到端测试收到首条真实消息。 |
| AC-013 | PASS | 聊天/弹幕 WebSocket 的 message ID、activity ID、正文一致；聊天室和弹幕历史均读回成功。 |
| AC-014 | PASS | 两条消息来自不同稳定测试用户，名称和正文均带测试标识。 |
| AC-015 | PASS | 停止后重启收到相同测试用户 ID；保留手机号查询防止误复用同名普通用户。 |
| AC-016 | PASS | 活动任务字典和锁保证单任务；重复开启接口幂等，页面运行中禁用开启按钮。 |
| AC-017 | PASS | stop 取消并等待任务；已有消息可查，重复关闭成功。 |
| AC-018 | PASS | closed/ended 返回 409；运行中转 closed 后任务停止，重新 open 不自动恢复。 |
| AC-019 | PASS | 第二活动状态保持关闭且弹幕历史为空，首活动消息全部携带首活动 ID。 |
| AC-020 | PASS | 状态、开启和关闭接口无管理员 Bearer Token 均返回 401。 |
| AC-021 | PASS | 后端、管理端、screen-web、Electron、脚本、diff 检查和安装包回归均有退出码/产物证据。 |

## 覆盖缺口

- 未在浏览器中输入管理员密码或提交真实登录，认证后按钮的截图未形成；这是凭证安全边界，不影响构建和后端行为证据。
- Windows 多屏、鼠标穿透、托盘和离线恢复沿用 TASK-v1 的历史实测与最终 NSIS 产物复核，本轮未重复驱动。
