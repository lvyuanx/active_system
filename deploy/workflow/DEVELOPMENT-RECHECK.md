# TASK-v1 开发修复交接

任务：修复连续首次部署失败重试及文档问题。
输入版本：TASK-v1、RISK-REVIEW.md、TESTING.md；HEAD 70793924d129de74b26517a852a1fe6cbe412fc3。
状态：completed
结论：P2/P3已修复，基础回归通过，生产已冻结。
证据：release.sh:50前驱链校验，test_release_flow.sh:122连续失败测试；22场景通过。
变更文件：release.sh、test_release_flow.sh、entry.vue、deploy三个AGENTS/README、WIKI、MEMORY。
风险或阻塞：Linux Docker实测缺口；替身不是容器验收。
下一步：使用新快照独立复核；不重复无变化的已验证范围。

切换前保存pending-parent，完整链无环/同数据目录；项目/service/对应image/backend实际mount核对。
成功pending收敛current。补测试资产说明与旧Docker入口文档，扫码提示#b8c1bd。
AC-005/006重试及外来容器拒绝增强，AC-003仅局部文字对比度；TASK-v1未改变。
`bash deploy/tests/test_release_flow.sh` 0，原12+新10场景（runtime/test-qa/flow-1283）。
两Shell `bash -n` 0；user-web vue-tsc及 /user/ build 0；diff --check 0。
deployment-serial主树串行，未派生/提交/改Git元数据，无方案偏差。
44文件清单runtime/test-dev/development-manifest-v2.json，SHA256：
e7123dc5ffea5c2390dad5521f47c4e9619f107aa04c19b206a7c87fc8ce6ba7。
