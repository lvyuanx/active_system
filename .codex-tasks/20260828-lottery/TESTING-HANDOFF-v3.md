任务：抽奖奖项与奖品树形编辑
输入版本：TASK-v3；DEVELOPMENT-HANDOFF-v3
状态：completed
结论：树形分组、子节点新增约束、未保存奖品过滤和响应式样式验证通过。
证据：
- `pnpm --filter @active/admin-web typecheck` 退出状态 0。
- `pnpm --filter @active/admin-web build` 退出状态 0；仅保留既有 PURE 注释和大包体积提示。
- 浏览器 1280×720 实测页面显示 2 个奖项、3 个奖品；每个奖项的子奖品在对应节点内展示。
- 浏览器实测点击第一个“添加奖品”后，该节点从 2 个子奖品变为 3 个，第二个奖项保持 1 个子奖品；新增奖项的“添加奖品”按钮为禁用状态。
- 干净浏览器 tab 的 error/warn 日志为空；后端既有抽奖回归 45 passed。
变更文件：`apps/admin-web/src/views/lottery/index.vue`；`apps/admin-web/src/views/lottery/lottery.css`；`.codex-tasks/20260828-lottery/TESTING-HANDOFF-v3.md`
风险或阻塞：无阻断问题；构建提示属于既有依赖/包体积提示。
下一步：由审核角色复核树形数据分组和保存兼容性。

