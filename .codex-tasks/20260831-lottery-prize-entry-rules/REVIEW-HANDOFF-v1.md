任务：奖品级黑白名单配置
输入版本：TASK-v1；测试交接：TESTING-HANDOFF-v1.md
状态：completed
结论：APPROVED
证据：数据库唯一约束包含 `activity_id, prize_id, activity_user_id`；名单 GET/PUT、摘要、黑白名单筛选和开始/停止候选池均使用同一奖品上下文；服务层校验奖品属于当前活动；旧表仅在 `ensure_config` 中按活动迁移一次；新参与者不再写入活动级名单表；前端弹窗选择已保存奖品后才发起带 `prize_id` 的请求，主页面不再显示活动级名单统计；测试、typecheck、build、静态检查和差异检查均通过。
变更文件：审核范围覆盖 `apps/backend/app/core/database.py`、`apps/backend/app/modules/lottery/`、`apps/backend/app/modules/participants/router.py`、`apps/backend/tests/`、`apps/admin-web/src/api/client.ts`、`apps/admin-web/src/views/lottery/`、相关模块文档和项目知识文件。
风险或阻塞：无阻断问题。需要部署时确认现有数据库初始化流程可执行新表创建；当前实现保留旧表和迁移数据，支持代码回滚读取旧活动级规则，但旧版本不会理解奖品级差异。
下一步：执行 AC-001 至 AC-005 逐项验收并完成工作树清理记录。
