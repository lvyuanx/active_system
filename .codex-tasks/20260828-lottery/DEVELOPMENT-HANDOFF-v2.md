任务：抽奖名单弹窗化与服务端分页优化
输入版本：TASK-v2；ARCHITECTURE-v2
状态：completed
结论：已完成名单摘要、服务端分页/搜索/状态筛选、单用户事务更新和管理端名单配置弹窗；配置奖项或奖品不再提交或替换全量名单。
证据：
- `apps/backend/app/modules/lottery/models.py` 增加 `LotteryEntrySummary`、`LotteryEntryPage`、`LotteryEntryUpdate` 和更新响应模型，配置响应移除 `entries`。
- `apps/backend/app/modules/lottery/repository.py` 使用 `LEFT JOIN`、活动条件和共享 `entry_where` 生成名单页及可抽奖摘要。
- `apps/backend/app/modules/lottery/service.py` 的名单更新使用 `BEGIN IMMEDIATE` 和活动用户归属校验；现有开奖候选计算复用同一资格条件。
- `apps/admin-web/src/views/lottery/LotteryEntriesDialog.vue` 实现关键词搜索、五类筛选、分页、单行即时保存和异常反馈；主页面只渲染统计摘要。
- `python -m pytest -q`（`apps/backend`）退出 0，45 passed；`pnpm -r typecheck` 退出 0；`pnpm -r build` 退出 0；`git diff --check` 退出 0。
变更文件：
- `apps/backend/app/core/database.py`
- `apps/backend/app/modules/lottery/models.py`
- `apps/backend/app/modules/lottery/repository.py`
- `apps/backend/app/modules/lottery/service.py`
- `apps/backend/app/modules/lottery/router.py`
- `apps/backend/tests/test_lottery.py`
- `apps/admin-web/src/api/client.ts`
- `apps/admin-web/src/views/lottery/index.vue`
- `apps/admin-web/src/views/lottery/LotteryEntriesDialog.vue`
- `apps/admin-web/src/views/lottery/lottery.css`
- 相关 AGENTS、README、WIKI、MEMORY、LEARNING 和任务证据文件
风险或阻塞：构建保留既有 `@vueuse/core` PURE 注释提示和管理端产物超过 500KB 提示；没有本次功能阻塞。
下一步：进入测试、审核和浏览器验收门禁。

