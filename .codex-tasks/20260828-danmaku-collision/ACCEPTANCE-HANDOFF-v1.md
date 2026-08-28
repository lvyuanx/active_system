任务：按 TASK-v1 对 B站式弹幕碰撞避让改造执行最终验收。
输入版本：TASK-v1；审核交接为 REVIEW-HANDOFF-v1；测试交接为 TESTING-HANDOFF-v1。
状态：completed
结论：ACCEPTED。AC-001 至 AC-009 全部 PASS，达到本次确认的“碰撞预测 + 单一最大等待时间配置”目标。
证据：
- AC-001 PASS：新配置默认 1.5 秒；旧 SQLite 通过启动初始化检测并增加字段，迁移记录读取为 1.5 秒（`apps/backend/tests/test_danmaku.py:172-255`）。
- AC-002 PASS：0.5、1.5、5.0 成功，0.4、5.1 返回 422，旧客户端省略字段的更新请求成功（`apps/backend/tests/test_danmaku.py:95-118,172-200`）。
- AC-003 PASS：HTTP 设置回包和既有 `danmaku.settings.updated` 广播包含新字段，screen-web/Electron 类型已同步。
- AC-004 PASS：几何测试证明安全的同轨道短弹幕可提前入场，并使用 8px 最小水平间距；CSS 终点与几何终点均为文本完全离屏（`apps/screen-web/scripts/test-danmaku-layout.mjs:19-37,48-53`）。
- AC-005 PASS：几何测试覆盖过早入场和长弹幕追赶短弹幕，冲突轨道会被跳过并尝试其他轨道。
- AC-006 PASS：队列按本地入队时间 FIFO 重试，队首超过配置等待上限后丢弃；实现证据为 `DanmakuOverlay.vue:164-211` 和布局测试过期断言。
- AC-007 PASS：保留 200 条上限、50ms 重试、轮询轨道游标和统一帧生命周期调度；screen-web 测试通过。
- AC-008 PASS：配置更新不清空活动项，当前项保留已有轨迹，新项使用新设置；既有类型检查、构建和消息/调度回归通过。
- AC-009 PASS：模块文档、项目知识、任务图和交接证据已同步；后端全量测试、四项目类型检查和全仓构建通过。
- 浏览器证据：普通大屏入口和 `?danmaku-overlay=1` 入口均可加载并显示预期占位结构；Electron 活动会话注入不在浏览器能力范围内，因此没有把入口检查表述为完整原生运行态验证。
变更文件：验收未修改工作树；验收依据实现、测试、审核和证据文件。
风险或阻塞：无阻断项；保留字体回退宽度误差和 Electron 原生桥接验证边界作为残余风险。
下一步：执行清理阶段，关闭本次启动的本地 Vite 服务，保留代码与任务证据，不创建提交。
