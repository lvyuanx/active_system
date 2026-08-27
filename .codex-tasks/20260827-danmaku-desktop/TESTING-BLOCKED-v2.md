任务：AC-009 首次 WebSocket 断开边界核查
输入版本：TASK-v1；当前主工作树 HEAD 4e35b3da19742aff672cdd58910bbf60b8935f59
状态：blocked
结论：确认存在消息遗漏。首次 danmaku.ready 前断线后，下一次 ready 会提升游标并跳过该窗口内消息。
证据：DanmakuOverlay.vue 第 192 行将 lastMessageId 提升为新会话最大 ID 后直接返回，未通过 after_id 补齐。
变更文件：无。
风险或阻塞：AC-009 阻断缺陷，违反“运行期间遗漏消息补齐”。
下一步：返回开发修复，并新增首次 ready 前断线的回归用例后重新测试。

复现逻辑：

1. 启动会话返回 latest_message_id=100，渲染器将游标设为 100。
2. 首个 WebSocket 完成认证前或 danmaku.ready 到达前断开。
3. 在断开后、重连 ready 前产生消息 message_id=101。
4. 重连后服务端 ready.session.latest_message_id=101。
5. 客户端将游标直接设为 101 且不请求 /danmaku/messages?after_id=100，因此消息 101 未投放。

关联代码：

- DanmakuOverlay.vue 第 90、97、191-194、246-253 行。
- 后端弹幕 WebSocket 在 router.py 第 143-144 行读取会话并发送 ready。
- 现有 message-order 测试只覆盖排序、去重和游标过滤，不覆盖连接状态转换。
