任务：抽奖奖项与奖品树形编辑
输入版本：TASK-v3；REVIEW-HANDOFF-v3
状态：completed
结论：ACCEPTED
证据：
- AC-301 PASS：浏览器 DOM 和截图确认奖项为一级节点、奖品为其子节点，不再出现奖品所属奖项下拉框。
- AC-302 PASS：浏览器点击第一个奖项的新增按钮只新增其子奖品；新增未保存奖项显示待保存并禁用新增奖品。
- AC-303 PASS：前端类型检查和现有后端抽奖测试通过，保存数据仍由 `awards`/`prizes` 两个数组提交。
- AC-304 PASS：1280×720 视觉验收通过，管理端 typecheck/build 通过，干净浏览器控制台无 error/warn。
- 临时 FastAPI 8003、Vite 5188、浏览器 tab 和树形验收数据库均已清理。
变更文件：`.codex-tasks/20260828-lottery/ACCEPTANCE-HANDOFF-v3.md`；`apps/admin-web/src/views/lottery/AGENTS.md`
风险或阻塞：无验收阻塞。
下一步：完成清理记录并结束 TASK-v3。

