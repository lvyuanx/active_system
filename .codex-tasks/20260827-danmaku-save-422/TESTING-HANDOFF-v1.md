任务：TASK-v3 管理端弹幕播放设置保存 422 修复测试
输入版本：TASK-v3；WorkPackage main-shared-422；输入 HEAD 52a164fa63a012f16234de966de137edda5970a6
状态：completed
结论：AC-022 PASS；AC-023 PASS。合法六位十六进制颜色的 API 保存、响应和再次读取通过，RGB/rgba/颜色名称/五位及八位颜色仍返回 422；源码、静态回归和构建证据一致。AC-001～AC-021 的受影响后端回归通过，未改变既有接口。真实浏览器登录后的 UI/Network 未执行，NSIS 未在本版本重跑，缺口已明确记录。
证据：Windows win32，Python 3.11.1、pytest 8.4.2、Node 22.21.1、pnpm 11.16.0；`pnpm test:danmaku-settings`、`pnpm typecheck`、`pnpm build`（apps/admin-web）均退出码 0；根目录 `pnpm -r --workspace-concurrency=1 build` 退出码 0；`python -m pytest -q apps/backend` 29 passed、1 warning；`pytest tests/test_danmaku.py -q -vv` 6 passed；临时隔离 SQLite TestClient 探针验证 `#12ab34` PUT 200、响应/后续 GET 为 `#12AB34`，`rgb(...)` 等非法格式 422；限定差异 8676 bytes，SHA-256 `4BBAA5A05195DCFEE9BF11E3BEA8C63F01519909EA247FA97EF9C7240B182DA`；测试前后工作树状态和 WorkPackage 文件 SHA-256 一致，`git diff --check` 退出码 0。
变更文件：无；未新增或修改测试资产，复用 `apps/admin-web/scripts/test-danmaku-settings.mjs` 与既有后端测试。
风险或阻塞：真实浏览器访问目标路由被重定向到 `/login`，未读取或输入密码/token，未捕获目标活动实际 PUT、Toast 或控制台 Network；未执行 Windows NSIS 打包、桌面真实窗口/渲染/离线故障注入。AC-001 的全部数值边界、AC-006～AC-009 的部分桌面运行时、AC-011～AC-021 的部分 UI/跨活动/生命周期场景保留覆盖缺口；不把缺口描述为本次实测通过。测试节点无代码失败，可交审核；若要求逐项全量 UI/NSIS 证据需另行安排环境。
下一步：交审核角色核对实现范围、后端校验未放宽、测试证据与残余缺口；审核通过后由验收角色仅按可复核证据逐条给出结论。

## 测试用例与 AC 映射

- T-022-01：默认有效设置不变 PUT 返回 200，响应设置一致，对应 AC-022。
- T-023-01：`#12ab34` PUT 返回 200，响应及后续 GET 为 `#12AB34`，对应 AC-023。
- T-023-02：`rgb(...)`、`rgba(...)`、颜色名称、五位及八位颜色均返回 422，对应 AC-023 非目标约束。
- T-REG-01：保存设置后 WebSocket 收到 `danmaku.settings.updated`，对应 AC-005。
- T-REG-02：token、session、WebSocket 首帧认证及旧 token 失效，对应 AC-002～AC-003。
- T-REG-03：聊天室完整消息、弹幕四字段摘要、测试消息及身份复用，对应 AC-004、AC-013～AC-015。
- T-BUILD-01：管理端静态回归、类型检查、生产构建及全仓构建，对应 AC-010、AC-021～AC-023。

## 逐项结果

- AC-001：部分覆盖；活动隔离及非法区域/颜色 422 通过，全部数值边界未单独覆盖。
- AC-002～AC-005：后端回归通过。
- AC-006～AC-008：未执行桌面真实 UI、渲染及队列运行时验证。
- AC-009：after_id 补齐及关闭后只读通过，真实断线重连未覆盖。
- AC-010：后端测试、四个 workspace 构建和桌面主进程构建通过；Windows NSIS 未执行。
- AC-011～AC-012：后端接口部分通过，管理端页面运行时未覆盖。
- AC-013～AC-015：后端实时消息、测试用户及身份复用通过。
- AC-016～AC-018：重复开启、关闭及 closed 活动 409 有证据；ended/只读转换和完整指标缺失。
- AC-019：跨活动测试流未单独覆盖。
- AC-020：未授权接口 401 通过，状态/消息不变未完整验证。
- AC-021：静态测试、构建和文档证据存在，但完整 UI/NSIS 回归有缺口。
- AC-022：PASS；默认 PUT 返回 200，源码含成功提示和回填逻辑。
- AC-023：PASS；合法六位十六进制返回 200、回包和 GET 大写归一化，RGB 等非法格式返回 422。

## 失败复现与边界

原问题场景的真实浏览器路由被重定向到 `/login`，测试未读取或输入任何认证信息，也未伪造浏览器 HTTP 结果；接口差异由隔离 SQLite TestClient 复现。测试节点按 `INELIGIBLE / DIRTY_INPUT_UNSAFE` 的共享主树串行包执行，峰值子线程 1、隔离写包 0、排队节点 0；`batch_duration` 未由平台提供，因此不宣称并发或完整 UI 验证。
