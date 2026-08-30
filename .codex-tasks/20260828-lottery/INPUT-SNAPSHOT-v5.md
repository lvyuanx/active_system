# TASK-v5 输入快照

- `input_snapshot_id`: `WORKTREE-AFTER-TASK-V4`
- `HEAD`: `17bceecc6ad68c506dc21c9b188b1bfa04b2ae7b`
- `HEAD^{tree}`: `bb2e756d2849148f970a89e107dcc21349a45c3f`
- 状态：开发开始前主工作树已包含 TASK-v1～v4 抽奖实现、参与者/弹幕等未提交改动，无法安全创建干净隔离 worktree；本任务采用串行主树集成。
- 读范围：`apps/backend`、`apps/admin-web`、`apps/screen-web`、`README.md`、`WIKI.md`、`MEMORY.md`、`LEARNING.md`。
- 写范围：见 `TASKGRAPH-v5.json` 的 `work_packages[0].write_scope`。
- 冻结时 `git status --porcelain=v1` 摘要：已修改 `LEARNING.md`、`MEMORY.md`、`README.md`、`WIKI.md`、admin/backend/screen 的既有 AGENTS、API/路由/样式文件及参与者模块；已存在未跟踪的 `apps/admin-web/src/views/lottery`、`apps/backend/app/modules/lottery`、`apps/backend/tests/test_lottery.py`、`apps/screen-web/src/components/lottery` 和 v1～v4 任务证据目录。上述均为本任务前脏工作树内容，未被回退。
- 证据限制：开发启动前未持久化逐文件 SHA-256 清单；本文件如实记录该历史缺口，不将当前输出清单伪装成输入内容。当前 HEAD 与上述 tree OID 可复核，完整输出文件 SHA-256 由 `OUTPUT-MANIFEST-v5.md` 补齐。
