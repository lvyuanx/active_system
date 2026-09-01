任务：实时抽奖特殊配置安全码
输入版本：TASK-v1；验收交接：ACCEPTANCE-HANDOFF-v1.md
状态：completed
结论：已完成清理和交付前工作树核对；未创建隔离 worktree、分支或提交，保留用户原有脏工作树变更。
证据：测试生成的 `apps/backend/data/media/lottery-prizes/9ea0015877c84682bb4a470447d0338a.png` 已移出工作区；基线文件 `apps/backend/data/media/lottery-prizes/8a80136fb0da48179411e3bb531fe6ad.png` 已恢复；`git status --short` 中本任务文件与既有 screen-web/媒体变更可区分；`OUTPUT-MANIFEST-v1.md` 保存了本任务文件快照和验证命令。
变更文件：`.codex-tasks/20260831-lottery-special-config/` 任务证据文件。
风险或阻塞：根目录已有的媒体删除、screen-web 改动和上一任务证据未触碰；未提交状态由用户决定。
下一步：任务完成，无需继续修改。
