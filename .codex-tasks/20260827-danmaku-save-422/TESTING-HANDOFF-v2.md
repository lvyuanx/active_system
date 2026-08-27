任务：TASK-v3 管理端弹幕播放设置保存 422 修复最终重测
输入版本：TASK-v3；WorkPackage main-shared-422-final；行为相关输入清单 SHA-256 AC4308419A59ED77733E440D395485F96B9028BADE95AC5FA32FA9B940A431E9
状态：completed
结论：最终行为快照下的测试门禁通过。AC-022 PASS：默认设置原样保存返回 HTTP 200。AC-023 PASS：合法 `#12ab34` 保存返回 200，响应与后续 GET 归一化为 `#12AB34`；`rgb(...)`、`rgba(...)`、颜色名、五位和八位颜色均保持 422。管理端静态回归、typecheck、管理端构建、全仓构建、后端 29 项、弹幕模块 6 项和 Windows x64 NSIS 构建均通过。真实浏览器登录态 Network/Toast 未执行，属于明确覆盖缺口，不影响本次 API 与构建结论。
证据：
- `pnpm --filter @active/admin-web test:danmaku-settings` 退出码 0，输出 `danmaku settings load/save/color format assertions passed`。
- `pnpm --filter @active/admin-web typecheck` 退出码 0。
- `python -m pytest -q apps/backend` 退出码 0，29 passed、1 条既有弃用 warning；`python -m pytest -q tests/test_danmaku.py` 退出码 0，6 passed。
- 隔离 SQLite TestClient 探针退出码 0：默认 GET 的设置 PUT 返回 200；`#12ab34` PUT 与后续 GET 为 `#12AB34`；`rgb(...)`、`rgba(...)`、`blue`、`#12345`、`#12345678` 均返回 422。
- `pnpm --filter @active/admin-web build` 退出码 0；`pnpm -r --workspace-concurrency=1 build` 退出码 0，admin、danmaku-desktop、screen-web、user-web 均构建完成。
- 首次 `pnpm dist:danmaku:win` 因下载 `20.205.243.166:443` 超时退出 1；使用 `CSC_IDENTITY_AUTO_DISCOVERY=false`、`ELECTRON_MIRROR=https://npmmirror.com/mirrors/electron/`、`ELECTRON_BUILDER_BINARIES_MIRROR=https://npmmirror.com/mirrors/electron-builder-binaries/` 重试后退出码 0。安装包 SHA-256 为 `0A2BA43798C93B67678950C926807E3E52DBA0C01288C8BAEE9B4F661FDF773D`，blockmap SHA-256 为 `5FBE580F1A8C003DA98DD20F5C6F34CD6052A8C6E31E7E898443CCCA0559FF8A`。
- 最终行为清单在重测后仍为 `AC4308419A59ED77733E440D395485F96B9028BADE95AC5FA32FA9B940A431E9`；`git diff --check` 退出码 0。
变更文件：无。测试只写入 WorkPackage 声明的构建/发布临时目录；未修改生产、测试或业务文档文件。
风险或阻塞：共享主树仍为 `INELIGIBLE / DIRTY_INPUT_UNSAFE`，所以本次是串行共享主树重测，不宣称隔离并发。真实浏览器访问目标管理路由会跳转登录页，未读取或传输任何账号凭证，未捕获实际浏览器 PUT、Toast 或 Network；后台 TestClient API 证据覆盖本次缺陷的请求/响应契约。Rollup 保留既有 `#PURE` 注释和 chunk 大小 warning，但构建退出码为 0。
下一步：以本交接和 WORKPACKAGE-v3.json 重新执行审核；审核通过后由验收角色依据 AC-022/AC-023 的实际证据作出验收结论，并保留既有大范围功能的覆盖缺口说明。

## AC 映射

- AC-001：活动隔离、颜色/区域非法输入由后端回归覆盖；全部数值边界未单独重测。
- AC-002～AC-005：现有弹幕后端 6 项回归覆盖 token、认证、消息摘要和设置广播。
- AC-006～AC-010：全仓构建与本次 NSIS 通过；未驱动桌面窗口、鼠标穿透和断网真实场景。
- AC-011～AC-020：既有真实弹幕测试的后端回归在后端全量 29 项中通过；管理端真实 UI、跨活动和部分状态切换的手动运行时覆盖仍缺失。
- AC-021：模块说明、项目知识、静态回归、后端回归、全仓构建和 NSIS 都有证据；真实 UI 覆盖缺口已保留。
- AC-022：PASS，默认设置加载后原样 PUT 200，页面保留 `applyResponse` 和成功提示路径。
- AC-023：PASS，颜色选择器使用 `:show-alpha="false" color-format="hex"`；TestClient 验证合法六位十六进制保存/GET 大写归一化，非法 RGB 等格式 422。
