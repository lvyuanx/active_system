# TASK-v5 输入清单（可复核快照）

## 快照元数据

- `snapshot_id`: `WORKTREE-AFTER-TASK-V4`
- `captured_at`: `2026-08-28T17:55:01+08:00`
- `head_sha`: `17bceecc6ad68c506dc21c9b188b1bfa04b2ae7b`
- `head_tree_oid`: `bb2e756d2849148f970a89e107dcc21349a45c3f`
- `status_source`: TASK-v5 开发启动前主线程执行的 `git status --short` 输出（session evidence）
- `record_format`: `path|state|sha256`

## 可确认的输入记录

以下记录按路径排序。`HEAD_CONTENT_SHA256` 是冻结 HEAD 中该文件内容的 SHA-256；`WORKTREE_DIRTY` 与
`WORKTREE_UNTRACKED` 表示开发前已存在的脏工作树覆盖，但开发启动前没有持久化其逐文件内容，因此以
`UNAVAILABLE_PRETASK_SHA` 明确标记，不将当前输出内容倒填为输入内容。

```text
.env.example|WORKTREE_DIRTY|UNAVAILABLE_PRETASK_SHA
LEARNING.md|WORKTREE_DIRTY|UNAVAILABLE_PRETASK_SHA
MEMORY.md|WORKTREE_DIRTY|UNAVAILABLE_PRETASK_SHA
README.md|WORKTREE_DIRTY|UNAVAILABLE_PRETASK_SHA
WIKI.md|WORKTREE_DIRTY|UNAVAILABLE_PRETASK_SHA
apps/admin-web/AGENTS.md|WORKTREE_DIRTY|UNAVAILABLE_PRETASK_SHA
apps/admin-web/package.json|WORKTREE_DIRTY|UNAVAILABLE_PRETASK_SHA
apps/admin-web/src/api/client.ts|WORKTREE_DIRTY|UNAVAILABLE_PRETASK_SHA
apps/admin-web/src/components/AGENTS.md|WORKTREE_DIRTY|UNAVAILABLE_PRETASK_SHA
apps/admin-web/src/components/ActivitySidebar.vue|WORKTREE_DIRTY|UNAVAILABLE_PRETASK_SHA
apps/admin-web/src/router/index.ts|WORKTREE_DIRTY|UNAVAILABLE_PRETASK_SHA
apps/admin-web/src/styles/index.css|WORKTREE_DIRTY|UNAVAILABLE_PRETASK_SHA
apps/backend/AGENTS.md|WORKTREE_DIRTY|UNAVAILABLE_PRETASK_SHA
apps/backend/app/api/router.py|WORKTREE_DIRTY|UNAVAILABLE_PRETASK_SHA
apps/backend/app/core/config.py|WORKTREE_DIRTY|UNAVAILABLE_PRETASK_SHA
apps/backend/app/core/database.py|WORKTREE_DIRTY|UNAVAILABLE_PRETASK_SHA
apps/backend/app/main.py|WORKTREE_DIRTY|UNAVAILABLE_PRETASK_SHA
apps/backend/app/modules/participants/AGENTS.md|WORKTREE_DIRTY|UNAVAILABLE_PRETASK_SHA
apps/backend/app/modules/participants/router.py|WORKTREE_DIRTY|UNAVAILABLE_PRETASK_SHA
apps/backend/pyproject.toml|WORKTREE_DIRTY|UNAVAILABLE_PRETASK_SHA
apps/screen-web/AGENTS.md|WORKTREE_DIRTY|UNAVAILABLE_PRETASK_SHA
apps/screen-web/package.json|WORKTREE_DIRTY|UNAVAILABLE_PRETASK_SHA
apps/screen-web/src/App.vue|WORKTREE_DIRTY|UNAVAILABLE_PRETASK_SHA
apps/screen-web/src/api/client.ts|WORKTREE_DIRTY|UNAVAILABLE_PRETASK_SHA
deploy/compose/docker-compose.yml|WORKTREE_DIRTY|UNAVAILABLE_PRETASK_SHA
deploy/nginx/default.conf|WORKTREE_DIRTY|UNAVAILABLE_PRETASK_SHA
.codex-tasks/20260828-lottery/|WORKTREE_UNTRACKED|UNAVAILABLE_PRETASK_SHA
apps/admin-web/scripts/test-lottery-image-race.mjs|WORKTREE_UNTRACKED|UNAVAILABLE_PRETASK_SHA
apps/admin-web/src/views/lottery/|WORKTREE_UNTRACKED|UNAVAILABLE_PRETASK_SHA
apps/backend/app/modules/files/AGENTS.md|WORKTREE_UNTRACKED|UNAVAILABLE_PRETASK_SHA
apps/backend/app/modules/files/service.py|WORKTREE_UNTRACKED|UNAVAILABLE_PRETASK_SHA
apps/backend/app/modules/lottery/|WORKTREE_UNTRACKED|UNAVAILABLE_PRETASK_SHA
apps/backend/tests/test_lottery.py|WORKTREE_UNTRACKED|UNAVAILABLE_PRETASK_SHA
apps/backend/tests/test_lottery_images.py|WORKTREE_UNTRACKED|UNAVAILABLE_PRETASK_SHA
apps/screen-web/scripts/test-lottery-order.mjs|WORKTREE_UNTRACKED|UNAVAILABLE_PRETASK_SHA
apps/screen-web/src/components/lottery/|WORKTREE_UNTRACKED|UNAVAILABLE_PRETASK_SHA
```

## 可验证摘要

- `HEAD` 与 `HEAD^{tree}` 可由 Git 重新验证；上面的状态记录可由 v5 启动阶段 session evidence 复核。
- 该清单的 SHA-256 只表示本清单文件内容，不能替代未保存的脏文件逐文件输入哈希；这是历史证据缺口，
  不应被误报为已完成的完整输入基线。
- 输出文件逐项 SHA-256 见 `OUTPUT-MANIFEST-v5.md`；任务图记录 `input_manifest_sha256` 为本文件实际 SHA-256。
