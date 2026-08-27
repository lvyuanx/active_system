# TASK-v4 集成范围证据

## 输入与模式

- 任务版本：TASK-v4
- workflow：activity-chat-ui-delivery-v4
- 输入 HEAD：`23c21c89141eff93fec55022493cae49128f4dbf`
- 集成模式：`SERIAL_SHARED_WRITE`；未创建或应用提交，主 Agent 保持唯一集成者
- 目标：仅集成用户端聊天页本次 4 个文件，排除任务外头像资源改动

## 目标写入清单

| 文件 | 类型 | SHA-256 |
| --- | --- | --- |
| `apps/user-web/src/views/activity/chat.vue` | 已跟踪修改 | `81E92B63BFA8ADAA34BA9029920A761B3AE57B1E31475F88BC93EB9AFA32B3FF` |
| `apps/user-web/src/views/activity/chat.css` | 本次新增 | `738741226F1203444BB0CCE8F220AC90FF39F9D1E8078D66F828F61DE863F52E` |
| `apps/user-web/src/views/activity/activity.css` | 已跟踪修改 | `685029FF233E79E59E8DA6E344902A7C3EDD5F5E9214718BAAB398CC2F346CDE` |
| `apps/user-web/AGENTS.md` | 已跟踪修改 | `197B13B75AC8711198304FC83E0609DB149B7E5F5C1744FEC5E561244C3A59E5` |

已跟踪目标路径执行 `git diff --name-only --` 的结果为：

```text
apps/user-web/AGENTS.md
apps/user-web/src/views/activity/activity.css
apps/user-web/src/views/activity/chat.vue
```

`chat.css` 是新增未跟踪文件，已通过实际文件清单和 SHA-256 纳入本任务；它是从 `activity.css` 提取的聊天专属样式，不是任务外写入。

## 排除清单

工作区同时观察到 `apps/user-web/src/assets/avatars/avatar-01.svg` 至 `avatar-20.svg` 的外部改动，及其尾随空白检查错误；这些文件不在 TASK-v4 `write_scope`，未被本任务修改、修复、删除或纳入上述目标清单。全量 `git diff --check` 不作为本任务门禁，目标路径检查退出码为 0。

## 集成门禁

- `pnpm --filter @active/user-web typecheck`：退出码 0
- `pnpm --filter @active/user-web build`：退出码 0，335 modules transformed
- `git diff --check -- apps/user-web/AGENTS.md apps/user-web/src/views/activity/chat.vue apps/user-web/src/views/activity/activity.css apps/user-web/src/views/activity/chat.css`：退出码 0
- 主树 HEAD 未漂移；未执行 commit、push、branch、worktree、stash、reset、clean
- 目标文件清单与实际写入范围一致，无路径越界
- 预览 worktree：从 HEAD 23c21c8 创建 detached worktree，限定补丁 `TASK-v4-scoped.patch` 的 `git apply --check --whitespace=nowarn` 退出码 0，实际应用后目标 tracked diff-check 退出码 0，随后按登记路径清理。
- 浏览器资产：`BROWSER-EVIDENCE-v4.md`、`BROWSER-430x932-v4.png`、`BROWSER-390x450-v4.png`。
- 完整 TaskGraph：`TASKGRAPH-v4.json`；WorkPackage：`WORKPACKAGE-v4.json`。
