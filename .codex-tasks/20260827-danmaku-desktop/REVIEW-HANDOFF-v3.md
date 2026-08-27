任务：TASK-v2 管理端真实聊天室弹幕测试最终代码审核
输入版本：TASK-v2；ARCHITECTURE-v2、DEVELOPMENT-HANDOFF-v8、TESTING-HANDOFF-v8、
INTEGRATION-EVIDENCE-v2、WORKPACKAGE-v11 和当前工作树
状态：completed
结论：APPROVED
证据：

- 管理端 `DanmakuTestPanel.vue` 只通过管理员 API 查询、开启和关闭测试，页面文案明确说明会向真实聊天室发送，
  不存在本地预览或本地消息队列实现。
- `testing.py` 使用 `create_message` 写入现有 `activity_chat_messages`，随后以同一序列化消息分别调用
  `chat_manager.broadcast` 和 `danmaku_manager.broadcast_message`；弹幕摘要白名单仍由既有 manager 保持四字段。
- 测试身份按 `(activity_id, 保留手机号)` 查询和创建；名称冲突返回 409，避免误把同名普通用户作为测试身份。
  任务字典按 `activity_id` 分组，锁保护重复开启，stop/stop_all 取消并等待任务退出。
- 三个控制接口均依赖 `require_superuser`；启动前和每次真实写入都校验 `open`，closed/ended 不再产生消息。
- `test_danmaku.py` 的端到端回归覆盖聊天室 WebSocket、弹幕 WebSocket、聊天室/弹幕历史、多用户身份复用、
  活动隔离、关闭后停止、ended 拒绝、重复启停和无管理员权限。
- `python -m pytest -q apps/backend` 为 29 passed；管理端 typecheck/build、screen-web 测试、Electron typecheck、
  全仓 build、NSIS 打包和 `git diff --check` 均为退出码 0；WorkPackage 14/14 哈希与当前文件匹配。

变更文件：无；本审核为主 Agent 只读替代审核，未修改生产代码、测试、业务文档或 Git 元数据。
风险或阻塞：审核角色子线程未能在平台使用额度内返回（状态查询为 not_found），因此这不是独立子代理的结论；
本文件如实记录为主 Agent 的只读审核。测试消息会保留在真实聊天记录中，单进程任务不具备多副本协调；
认证后页面没有浏览器截图，但管理端构建和后端端到端证据完整。
下一步：进入产品验收，逐项核对 AC-011 至 AC-021；发布前仍建议在目标 Windows 环境手工观察多屏覆盖和鼠标穿透。

## 审核发现

未发现阻断问题。

## 审核边界

- 本次没有改变用户端聊天协议、弹幕 token、弹幕摘要字段、screen-web 渲染器或 Electron 多屏实现。
- 通过 `get_danmaku_record` 获取测试状态会沿用原有懒初始化弹幕设置的行为，这是已存在的管理员读接口约定，
  不构成新的跨活动写入。
- Rollup 的大 chunk 警告和 FastAPI 旧 422 常量弃用警告均为既有非阻断警告，不由本次功能引入。
