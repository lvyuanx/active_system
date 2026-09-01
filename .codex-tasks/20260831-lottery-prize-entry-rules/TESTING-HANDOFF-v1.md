任务：奖品级黑白名单配置
输入版本：TASK-v1；开发交接：DEVELOPMENT-HANDOFF-v1.md
状态：completed
结论：后端跨奖品名单/迁移回归、Python 编译检查、管理端类型检查、管理端生产构建和差异检查通过。
证据：`python -m pytest -q`（工作目录 `apps/backend`）退出码 0，结果 `60 passed`；定向抽奖回归 `python -m pytest -q tests/test_lottery.py tests/test_lottery_round.py tests/test_lottery_prize_entries.py` 退出码 0，结果 `14 passed`；相关 Python 文件 `python -m py_compile ...` 退出码 0；`pnpm --filter @active/admin-web typecheck` 退出码 0；`pnpm --filter @active/admin-web build` 退出码 0；管理端主页面/弹窗静态结构检查通过；相关代码行长度检查无超过 120 字符；`git diff --check` 退出码 0。构建仅保留既有 Rollup PURE 注释和大包提示。
变更文件：测试资产为 `apps/backend/tests/test_lottery_prize_entries.py` 及 `test_lottery.py`、`test_lottery_round.py` 的奖品上下文更新；其余为验证输出，不修改生产代码。
风险或阻塞：未自动化覆盖真实浏览器截图，但奖品选择器、摘要字段、主页面隐藏统计和带 `prize_id` 请求均已静态检查；后端迁移用例直接验证旧标记复制到已有奖品且新增奖品不继承。
下一步：进入代码审核，确认 AC-001 至 AC-005 与实现及证据一致。
