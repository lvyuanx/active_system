任务：按 TASK-v2 修复多测试用户弹幕产量不足问题。
输入版本：TASK-v2；架构输入为 ARCHITECTURE-v2；输入快照为 HEAD-9ec1caa4-dirty-20260828-multi-sender。
状态：completed
结论：已将真实弹幕测试改为每个测试用户一个独立 sender task，首轮错峰，活动级锁串行化 SQLite 写入和聊天室/弹幕广播，并在停止或异常时回收全部 sender。
证据：
- `apps/backend/app/modules/danmaku/testing.py:163-215` 新增 `_run_user`，每个用户维护自己的消息游标、身份和随机延迟循环。
- `apps/backend/app/modules/danmaku/testing.py:222-252` 为活动创建 sender task 集合，使用 `asyncio.wait(FIRST_COMPLETED)` 监控，并在 finally 中取消和回收全部任务。
- `apps/backend/tests/test_danmaku_test_config.py:143-179` 使用 100 个测试用户验证每个用户均至少发出一条消息。
- `apps/admin-web/src/views/danmaku/DanmakuTestPanel.vue:13-17` 明确提示每个测试用户独立发送；README、WIKI、模块 AGENTS、LEARNING、MEMORY 已同步。
- 未新增接口字段，保留用户数量、延迟范围、活动隔离、聊天室和弹幕 WebSocket 协议。
变更文件：`testing.py`、弹幕测试集成/并发测试、管理端说明、模块文档和项目知识、TASK-v2 证据文件。
风险或阻塞：100 个用户会提高数据库写入和广播负载；活动级锁保证关键写入有序，但渲染端仍按轨道安全容量丢弃超量消息。
下一步：交由测试、审核和验收阶段复核。
