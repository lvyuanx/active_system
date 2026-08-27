任务：T3 独立测试门禁，活动弹幕桌面悬浮工具
输入版本：TASK-v1
状态：blocked
结论：首次测试尝试未执行测试，因为 `main-tests` 缺少完整 WorkPackage 契约。
证据：测试角色核对 `TASKGRAPH-v1.json` 后发现只有 `work_package_id` 引用，无 `read_scope`、`write_scope`、
输入清单或 SHA-256。
变更文件：无
风险或阻塞：稳定原因码 `HANDOFF_INVALID`；此阻塞已由新增 `WORKPACKAGE-v1.json` 修复。
下一步：以 `WORKPACKAGE-v1.json` 和 `DEVELOPMENT-HANDOFF-v1.md` 作为完整冻结输入，重新执行测试门禁。

首次测试角色未运行任何会改动缓存或数据库的命令，未产生测试资产或生产代码变更。
