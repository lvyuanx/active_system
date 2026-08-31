# 产品交接

任务：
冻结 `TASK-v1`，将连续实时弹幕改为直接消费 WebSocket 完整载荷，HTTP 仅用于 ready、重连和 ID 缺口恢复。

输入版本：
`TASK-v1`；输入快照 `HEAD-5bc847a-clean-20260831`。

状态：completed

结论：
任务保持 T4；后端已经提供完整载荷，不改公共协议或后端生产代码。

证据：
`apps/backend/app/modules/danmaku/manager.py:45-54` 广播四字段完整消息；
`apps/screen-web/src/components/realtime/DanmakuOverlay.vue:311-318` 当前仍把完整消息降级为 ID 信号。

变更文件：
无。

风险或阻塞：
全局自增 ID 可能因跨活动消息产生合法跳号，因此缺口检测保持保守 HTTP 补齐；无高影响阻塞。

下一步：
开发依据 `TASK-v1` 实现，测试覆盖 AC-001 至 AC-006。
