任务：审核管理端首页“打开抽奖大屏”入口
输入版本：TASK-v2 + DEVELOPMENT-HANDOFF-v2 + TESTING-HANDOFF-v2
状态：completed
结论：APPROVED
证据：

- `apps/admin-web/src/views/home/index.vue:103-124`：按钮放在既有 footer 事件隔离区域，不会触发卡片主体的活动首页跳转；开启、关闭、结束操作未修改。
- `apps/admin-web/src/views/home/index.vue:200-203`：大屏地址支持环境配置并保留本地默认值。
- `apps/admin-web/src/views/home/index.vue:270-276`：仅向大屏传递当前 `activity_id`，使用新标签页和 `noopener,noreferrer`，未改变后端接口或抽奖协议。
- 管理端 typecheck、build、静态行为断言和 `git diff --check` 均通过。

变更文件：

- 无；审核阶段未修改文件。

风险或阻塞：缺少已登录浏览器截图/真实点击证据，属于运行环境验证缺口；未发现代码阻断问题。
下一步：进入逐条验收。
