任务：实时抽奖特殊配置安全码
输入版本：TASK-v1；测试交接：TESTING-HANDOFF-v1.md
状态：completed
结论：APPROVED
证据：入口文案已由“配置黑白名单”改为“特殊配置”；`entryDialogVisible` 不再由按钮直接设置，只在服务端验证成功后设置；安全码来自后端 Settings，不进入 `LotteryConfigResponse`、验证响应仅返回 `verified: true`；错误映射覆盖未配置、错误码、未认证和活动不存在；现有名单接口与抽奖规则未改动；58 条后端测试、管理端 typecheck/build 和 diff 检查均通过。
变更文件：审核范围为 TASK-v1 冻结的实现、测试、文档和任务证据文件。
风险或阻塞：需要部署人员设置非公开的 `LOTTERY_SECURITY_CODE`；本次没有增加失败次数限制，暴力尝试防护仍属于后续安全建设范围。
下一步：执行 AC-001 至 AC-004 验收并完成任务清理记录。
