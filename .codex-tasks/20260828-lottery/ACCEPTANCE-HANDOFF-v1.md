任务：验收 WebSocket 实时抽奖
输入版本：TASK-v1；审核输入：REVIEW-HANDOFF-v1。
状态：completed
结论：ACCEPTED。
证据：AC-001 至 AC-012 由 `apps/backend/tests/test_lottery.py`、`python -m pytest -q` 和协议 JSON 断言覆盖；AC-011 的前端 ready 基线/队列去重由 `apps/screen-web/scripts/test-lottery-order.mjs` 覆盖并通过；AC-013/014 由管理端与大屏浏览器 DOM、截图和实际开奖操作验证；AC-015 由 `pnpm -r typecheck`、`pnpm -r build`、后端 42 条全量回归及 `git diff --check` 覆盖。
变更文件：验收阶段未修改文件。
风险或阻塞：无未解决验收阻塞；多副本共享消息总线和目标 Windows 多屏硬件实测保留为后续部署计划，不影响本版本单进程功能验收。
下一步：执行清理，更新 TaskGraph 和项目当前进度。

逐项结果：

- AC-001 PASS：配置、名单和历史 HTTP 接口成功并按活动隔离。
- AC-002 PASS：管理员 JWT 首帧/非管理员/活动用户上下文拒绝。
- AC-003 PASS：公开 ready/drawn/reset/config.updated 不含手机号、名单或管理员字段。
- AC-004 PASS：管理员完整结果和同活动大屏脱敏事件实时到达。
- AC-005 PASS：6 路并发请求、数量 2 只产生 2 条中奖记录，序号为 1/2。
- AC-006 PASS：同 request_id 重试返回同一结果且 `idempotent=true`，无重复记录/大屏事件。
- AC-007 PASS：黑名单、白名单、停用和跨奖品不重复过滤通过。
- AC-008 PASS：错误事件不写记录、不触发大屏开奖动画。
- AC-009 PASS：WS 重置后管理员/大屏快照中奖记录均为空。
- AC-010 PASS：HTTP 保存后同活动收到安全配置更新事件，其他活动未收到。
- AC-011 PASS：ready 历史建立已揭晓基线，draw_id 队列排序/去重测试通过；浏览器实际连接使用重连逻辑。
- AC-012 PASS：ping/pong 和断开清理路径通过。
- AC-013 PASS：管理端未 ready 时控制不可用、连接后同步库存/历史、重置二次确认可见。
- AC-014 PASS：浏览器实际看到霓虹大屏、候选滚动和约 3 秒后中奖揭晓。
- AC-015 PASS：模块文档、项目知识和构建/全量回归均完成。
