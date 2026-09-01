任务：奖品级黑白名单配置
输入版本：TASK-v1；有效产品交接：PRODUCT-HANDOFF-v1.md
状态：completed
结论：保留旧 `lottery_entries` 作为迁移源，新增 `lottery_prize_entries` 和按活动迁移标记表；`ensure_config` 创建/确认默认奖品后，对尚未迁移的活动把旧规则复制到当时已有奖品并写入标记。名单接口继续沿用 `/lottery/entries` 路径，但要求 `prize_id` 查询参数；repository 的 join、摘要、过滤、更新和开奖候选统一带 `prize_id`。
证据：现有 `entry_where`、`lottery_entry_rows`、`lottery_entry_summary` 和 `_eligible_candidates` 是名单规则的共同数据流入口；开始/停止开奖已携带 `prize_id`，只需把当前奖品传入共同资格查询。
变更文件：`apps/backend/app/core/database.py`、`apps/backend/app/modules/participants/router.py`、lottery models/repository/service/router/模块文档、后端 lottery 测试；管理端 `client.ts`、lottery index、`LotteryEntriesDialog.vue`、模块文档、README/WIKI/MEMORY/LEARNING。
风险或阻塞：旧 API 缺少 `prize_id` 时不再有唯一语义，统一返回参数校验错误；旧数据复制必须在奖品存在后执行且不能对新增奖品重复复制。
下一步：开发实现、更新现有测试调用并新增跨奖品与迁移用例。
