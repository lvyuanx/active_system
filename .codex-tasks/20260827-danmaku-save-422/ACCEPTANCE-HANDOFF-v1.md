任务：TASK-v3 管理端弹幕播放设置保存 422 修复验收
输入版本：TASK-v3；PRODUCT-HANDOFF-v1；DEVELOPMENT-HANDOFF-v1；TESTING-HANDOFF-v2；REVIEW-HANDOFF-v2；WORKPACKAGE-v3；TASKGRAPH-v1
状态：completed
结论：ACCEPTED。AC-022 PASS，默认 GET 设置原样 PUT 返回 200，页面仍加载、保存、回填并显示成功提示。AC-023 PASS，颜色选择器使用 `:show-alpha="false" color-format="hex"`；`#12ab34` PUT 返回 200，回包与再次 GET 为 `#12AB34`，RGB/RGBA/颜色名/五位及八位颜色均返回 422。修复范围无偏差，未放宽后端校验，PUT 路径、七个播放设置字段和实时广播路径保持不变。
证据：WorkPackage-v3 的 10 项行为文件 SHA-256 与当前文件一致，按路径排序聚合为 `AC4308419A59ED77733E440D395485F96B9028BADE95AC5FA32FA9B940A431E9`；`pnpm --filter @active/admin-web test:danmaku-settings` 退出码 0；最终测试交接记录后端 29 项、弹幕模块 6 项、管理端/全仓构建和 x64 NSIS 通过；审核结论为 APPROVED。验收独立 TestClient 流程用管理员权限创建隔离活动，验证默认保存 200、合法 hex 200/GET 大写归一化和非法颜色 422。目标前端文件 `git diff --check` 退出码 0。
变更文件：无。
风险或阻塞：未人工捕获真实已登录管理端的颜色面板操作、浏览器 PUT Network、HTTP 200 与成功 Toast；当前浏览器会话仅到登录页，未读取或传输管理员凭证。该缺口是非阻断体验证据缺口，不否定已通过的 API 契约验证。共享脏树为 `NOT_APPLICABLE_SHARED_DIRTY`，没有独立补丁或组合 `git apply --check` 验证。
下一步：主调度器闭环 TaskGraph cleanup 节点并向用户交付；本验收不构成发布批准。

## AC 结果

- AC-022：PASS。`index.vue` 在加载后调用保存路径并以 `applyResponse` 回填，TestClient 默认设置原样 PUT 返回 200，成功提示路径保持存在。
- AC-023：PASS。`index.vue` 使用非 alpha 的 hex 格式；合法 `#12ab34` 保存/读取归一化为 `#12AB34`；`rgb(...)`、`rgba(...)`、`blue`、`#12345`、`#12345678` 均保持 422。
