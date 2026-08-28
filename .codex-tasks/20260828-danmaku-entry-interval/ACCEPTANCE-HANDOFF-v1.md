任务：按 TASK-v1 对弹幕完整进入后间隔入场改造执行最终验收。
输入版本：TASK-v1；审核交接为 REVIEW-HANDOFF-v1；测试交接为 TESTING-HANDOFF-v1。
状态：completed
结论：ACCEPTED。AC-001 至 AC-009 全部 PASS。
证据：
- AC-001 PASS：新活动默认 `entry_interval_seconds=1.0`；旧 SQLite 启动初始化后自动增加该列并读取默认值。
- AC-002 PASS：入场间隔 0.1、1.0、5.0 保存成功，0.0 和 5.1 返回 422；旧请求体省略字段仍成功；原 `max_wait_seconds` 规则未改变。
- AC-003 PASS：HTTP 设置回包、`danmaku.ready` 和 `danmaku.settings.updated` 使用现有协议携带新字段。
- AC-004 PASS：同轨道在上一条完整进入前不能入场；隔离 CDP 测试记录第一条完整进入约 1155ms，第二条约 2238ms 出现，间隔约 1083ms，第一条仍在屏内。
- AC-005 PASS：不同轨道可立即使用；长弹幕追赶场景继续由全轨迹碰撞检测阻止并尝试其它轨道。
- AC-006 PASS：所有轨道不可用时按 FIFO 等待，队列等待从本地入队时刻起算，超过 `max_wait_seconds` 丢弃队首。
- AC-007 PASS：200 条上限、50ms 重试、轮询轨道和统一 `requestAnimationFrame` 调度回归通过。
- AC-008 PASS：设置更新不清空当前弹幕、不改变当前 CSS 轨迹，重连/补齐/多屏相关类型检查和构建通过。
- AC-009 PASS：模块文档、MEMORY/LEARNING/WIKI/README、TaskGraph 和交接证据已同步；全量测试、类型检查、构建及 Windows x64 NSIS 打包通过。
变更文件：验收未修改工作树。
风险或阻塞：无阻断项；已有安装版用户会话未被接管，隔离测试缓存目录仍为本地非跟踪文件。
下一步：执行清理阶段并交付安装包。
