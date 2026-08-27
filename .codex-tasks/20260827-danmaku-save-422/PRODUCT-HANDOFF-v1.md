任务：T2 缺陷修复：管理端弹幕工具“保存播放设置”返回 422
输入版本：用户问题快照-20260827 + TASK-v2 + HEAD 52a164fa63a012f16234de966de137edda5970a6
状态：completed
结论：产品门禁通过，任务冻结为 TASK-v3；完整目标、用户场景、范围、非目标、约束、风险、依赖、待确认项和 AC-001～AC-023 见同目录 TASK-v3.md。AC-001～AC-021 保持原义，新增 AC-022～AC-023，明确颜色选择器保存请求必须发送六位十六进制颜色。
证据：apps/admin-web/src/views/danmaku/index.vue:105 的静态 show-alpha="false" 经 Vue 编译为字符串；Element Plus 2.14.4 在 enableAlpha="false" 时将 #12ab34 序列化为 rgb(18, 171, 52)，而 apps/backend/app/modules/danmaku/service.py:37-43 仅接受六位十六进制；apps/admin-web/src/views/danmaku/index.vue:216-224 和 apps/admin-web/src/api/client.ts:84-88 原样提交该值。Node 与 compiler 复核命令均已在主线程执行并通过。
变更文件：无（产品角色只读；工作树中的 ARCHITECTURE-v2.md 不由本产品角色创建）
风险或阻塞：无高影响阻塞。用户未提供 422 响应体，开发/测试需记录实际请求体、响应体及保存后的再次读取结果；不得放宽后端颜色校验。
下一步：交开发实现并补充管理端颜色序列化回归，再执行测试、审核和验收门禁。
