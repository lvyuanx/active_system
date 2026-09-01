任务：奖品级黑白名单配置
输入版本：TASK-v1；架构交接：ARCHITECTURE-v1.md
状态：completed
结论：已将黑名单、白名单、名单摘要和开奖候选池统一改为 `(activity_id, prize_id)` 作用域；管理端特殊配置弹窗先选择奖品后加载和保存名单，旧活动级数据按活动一次性迁移到迁移时已有奖品。
证据：`apps/backend/app/core/database.py:80-104` 新增 `lottery_prize_entries`、索引和迁移标记表；`apps/backend/app/modules/lottery/repository.py:48-119` 校验奖品并懒执行一次性迁移，`repository.py:142-305` 的过滤、分页、单行读取和摘要均限定当前奖品；`apps/backend/app/modules/lottery/service.py:50-147` 更新接口和 `service.py:311-455` 开奖候选池均传递当前 `prize_id`；`apps/backend/app/modules/lottery/router.py:200-250` 要求名单 GET/PUT 携带 `prize_id`；`apps/admin-web/src/views/lottery/LotteryEntriesDialog.vue:20-48` 增加奖品选择和当前奖品摘要，`index.vue:143-156` 主页面仅保留入口；`apps/backend/tests/test_lottery_prize_entries.py:23-170` 覆盖跨奖品隔离、开奖候选池和旧数据迁移。
变更文件：后端数据库、lottery models/repository/service/router、participants 注册路由及模块文档；管理端 API 类型、实时抽奖页面/名单弹窗及模块文档；`README.md`、`WIKI.md`、`MEMORY.md`、`LEARNING.md`；现有抽奖测试和新增奖品级名单测试；本任务证据文件。
风险或阻塞：这是涉及数据结构和开奖资格的 T6 变更；保留旧 `lottery_entries` 作为迁移源，不自动删除新增数据，迁移标记确保旧规则不会覆盖迁移后的新增奖品或管理员修改。
下一步：执行后端全量回归、管理端类型检查/构建、静态结构和差异检查，然后进行只读审核与逐项验收。
