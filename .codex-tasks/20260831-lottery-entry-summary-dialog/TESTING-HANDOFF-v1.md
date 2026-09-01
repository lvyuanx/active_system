任务：抽奖名单摘要移入特殊配置弹窗
输入版本：TASK-v1；开发交接：DEVELOPMENT-HANDOFF-v1.md
状态：completed
结论：管理端阻断验证通过，未发现摘要迁移导致的类型、构建或静态结构问题。
证据：`pnpm --filter @active/admin-web typecheck` 退出码 0；`pnpm --filter @active/admin-web build` 退出码 0；主页面模板摘要文本扫描通过；弹窗统计和规则说明扫描通过；`git diff --check` 退出码 0。构建仅报告既有 Rollup 大包提示。
变更文件：测试资产未新增；验证依赖现有管理端构建和静态检查命令。
风险或阻塞：本轮未运行真实浏览器截图验收，Element Plus 弹窗视觉效果仍应在部署环境手工确认；自动化覆盖缺口不阻断源码结构验收。
下一步：进入只读审核并按 AC-001 至 AC-004 验收。
