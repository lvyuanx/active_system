# INTEGRATION-EVIDENCE-v1：抽奖大屏响应式布局 commitless 集成复核

输入版本：`TASK-v1`；主工作树 HEAD `807bd2238db9b07e4fb860b1476960bd06216008`；TREE `a2bbf8f652f5846d1bf2f672e6cc2bec4cdabf52`

## 集成路径

- 本任务按 `SERIAL_SHARED_WRITE` 执行，由唯一主工作树集成者直接保留当前未提交改动，不创建提交、不 push。
- 输出补丁为 `OUTPUT-PATCH-v1.diff`，大小 11,614 字节，SHA-256 为 `0ff863c36b3b29bdf729b32c1458ad5131dcf680f944fd9eba862240ae1c1d84`。
- `git apply --cached --check --binary --whitespace=nowarn OUTPUT-PATCH-v1.diff`：退出 0；该检查针对 HEAD 对应 index，不写入 index，确认补丁可从冻结基线应用。
- 随后 `pnpm --filter @active/screen-web typecheck`、`pnpm --filter @active/screen-web test`、`pnpm --filter @active/screen-web build` 和 `git diff --check` 均退出 0。

## 预览 worktree 与清理

- 按固定路径尝试创建 `D:/projects/active_system/.codex/worktrees/20260901-lottery-responsive/preview` 时，仓库既有 Electron 缓存长文件名导致 checkout 失败；目标目录未留下注册 worktree。
- 已核对并清理明确的临时目标；最终 `git worktree list --porcelain` 仅保留主工作树，无残留临时 worktree。
- 由于本任务是串行主树路径，未产生组合补丁集或隔离包合并冲突；index-base `git apply --check` 是最终补丁可应用性证据。

## 结果

- 主工作树 HEAD、TREE 和实现差异在集成检查前后保持不变。
- 实际变更仍限定在 `LotteryScreen.css`、大屏/抽奖模块说明、项目知识与任务证据范围内；未触及 Vue、TypeScript、WebSocket、API 或抽奖协议文件。
