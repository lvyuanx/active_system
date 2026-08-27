# TASK-v5 集成证据

## 输入与范围

- HEAD：`23c21c89141eff93fec55022493cae49128f4dbf`
- 输入快照 ID：`ecb168db68bc859fbf13a3496a68e2aa48c0b20aa8b0d9dff626d0a8bb433916`
- 主工作树含前序用户改动；由于存在头像资源和 v4 聊天文件的未提交改动，隔离 worktree 资格为 `INELIGIBLE`，本次采用唯一主树串行集成。
- 写入范围仅为聊天输入实现、用户端模块说明、项目知识/进度文档和 v5 交付证据；未纳入头像 SVG、后端 API 或 WebSocket 文件。

## Required Package Barrier

本版本只有一个必需工作包 `wp-v5-main-integration`。开发和测试已完成，限定补丁生成并通过目标文件 `git diff --check`；无隔离包需要组合应用。

## 验证结果

- `pnpm --filter @active/user-web typecheck`：退出码 0。
- `pnpm --filter @active/user-web build`：退出码 0，Vite 转换 335 个模块。
- `git diff --check -- apps/user-web/src/views/activity/chat.vue apps/user-web/src/views/activity/chat.css apps/user-web/AGENTS.md MEMORY.md LEARNING.md WIKI.md .codex-tasks/20260826-activity-chat-ui/TASK-v5.md`：退出码 0。
- 受限补丁：`TASK-v5-scoped.patch`，SHA-256 `8f7952bb278bb95227ca6c3dcd49ef4e9fb718f59929b4b5a78f301177667e31`。
- 代码和文档文件 SHA-256 见 `WORKPACKAGE-v5.json`。
- 浏览器尺寸、输入增长和视觉证据见 `BROWSER-EVIDENCE-v5.md`。

## 预览补丁校验

- 预览 worktree：`D:\projects\active_system\.codex\worktrees\20260826-activity-chat-ui-v5\wp-v5-preview`，基于 HEAD `23c21c89141eff93fec55022493cae49128f4dbf`，使用 `core.autocrlf=false` 创建。
- `git apply --check --ignore-whitespace --whitespace=nowarn TASK-v5-scoped.patch`：退出码 0。
- `git apply --ignore-whitespace --whitespace=nowarn TASK-v5-scoped.patch`：退出码 0。
- `git apply --check --reverse --ignore-whitespace --whitespace=nowarn TASK-v5-scoped.patch`：退出码 0。
- `--ignore-whitespace` 仅用于兼容 Windows worktree 行尾，不改变补丁内容；之前不带该选项的检查失败已作为行尾差异定位，不再作为成功证据。

## 集成结论

本次 v5 代码改动已在当前主工作树完成，未创建 commit、未 push；仅保留审计所需的任务、补丁和浏览器证据文件。
