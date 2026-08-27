任务：T3 开发交接：活动弹幕桌面悬浮工具
输入版本：TASK-v1
状态：completed
结论：已完成活动级弹幕配置、版本化 HMAC token、独立只读 HTTP/WS 通道、管理端控制页、Vue 弹幕渲染器与 Windows Electron/NSIS 桌面工具。聊天室既有协议保持不变，消息成功落库后会额外向弹幕连接广播正文摘要。
证据：`python -m pytest -q apps/backend` 通过 25 项；`pnpm build` 通过四个工作区构建；`pnpm --filter @active/danmaku-desktop typecheck` 通过；`pnpm dist:danmaku:win` 成功生成 Windows x64 NSIS 安装包；真实 Electron 开发版与打包版均完成 token 会话加载和聊天消息投放。
变更文件：后端 `apps/backend/app/modules/danmaku/`、聊天室路由和 SQLite/配置/路由注册；管理端 `src/views/danmaku/`、API 与路由；`screen-web` 弹幕渲染器；新增 `apps/danmaku-desktop/`；相关 workspace、文档和测试文件。
风险或阻塞：临时浏览器验收数据库 `data/danmaku-browser-test.db` 因执行环境拒绝删除命令而保留，但它被 `.gitignore` 忽略且不在交付文件中。当前广播仍为单进程内存实现，多副本需要后续共享消息总线。Windows 置顶/鼠标穿透仅承诺 Windows 优先。
下一步：测试角色以 TASK-v1 和本交接执行 AC-001 至 AC-010 的独立验证；之后进入审核和产品验收。

## 实现摘要

- 后端新增 `activity_danmaku_settings`；管理员读取时懒创建默认配置，PUT 采用完整字段校验，保存后向活动弹幕连接发送 `danmaku.settings.updated`。
- token 是 `dm1.{activity_id}.{token_version}.{HMAC-SHA256}`，使用 `DANMAKU_TOKEN_SECRET` 或 `JWT_SECRET`；数据库只存版本和时间。轮换 token 后关闭旧弹幕 WebSocket。
- 弹幕端 `GET /danmaku/session`、`GET /danmaku/messages` 和 `/danmaku/ws` 仅接受弹幕 token。消息摘要不含用户名、手机号或活动用户 ID。
- 管理端活动详情新增“弹幕工具”入口，配置轨道/字体/不透明度/时长/区域/颜色，提供 token 复制与带确认的重新生成。
- 渲染器首次以服务端最新消息 ID 为基线；重连时缓冲实时事件、通过 `after_id` 拉取漏消息，再按 ID 顺序投放。队列最多 200 条，溢出时丢弃最旧项。
- Electron 启动器只在进程内保存 token，主进程验证会话并创建透明、无边框、置顶、不可聚焦、鼠标穿透的覆盖窗口。托盘、`Ctrl+Shift+D` 和显示器移除均支持停止/恢复流程。

## AC 映射与验证

| AC | 实现与证据 |
| --- | --- |
| AC-001 | `DanmakuSettingsUpdate` 范围/区域/颜色校验；`test_danmaku.py` 覆盖默认值、隔离和 422。 |
| AC-002 | token 版本化 HMAC，轮换关闭旧连接；后端测试覆盖稳定 token、旧 HTTP/WS 拒绝和旧连接断开。 |
| AC-003 | `GET /danmaku/session` 与首帧 `auth`；测试覆盖有效/无效 token。 |
| AC-004 | 聊天路由新增 `broadcast_message`，摘要白名单字段；测试对比完整聊天事件和弹幕事件。 |
| AC-005 | 管理员 PUT 后 manager 推送设置；后端测试和实际 Electron 新弹幕样式均验证。 |
| AC-006 | launcher 获取显示器、验证 token、创建覆盖层；实际开发版/打包版完成会话后只投放新消息。 |
| AC-007 | `BrowserWindow` 设置 `transparent/frame/alwaysOnTop/focusable/skipTaskbar` 与 `setIgnoreMouseEvents`；原生计算器在覆盖层下点击 7 后显示 7。 |
| AC-008 | `DanmakuOverlay.vue` 按轨道和配置 CSS 变量投放，并保留 200 条有界队列；实际新弹幕验证 52px、0.7、5s、`#FFCC00`。 |
| AC-009 | 重连使用 `after_id`；后端游标测试覆盖补齐摘要，渲染器补齐期间缓冲乱序实时事件。 |
| AC-010 | 全量 pytest、pnpm build、Electron typecheck、NSIS x64 构建均已执行成功。 |

## 关键验证记录

- 打包版 `file://` 覆盖页验证：会话 API 返回 200，聊天“打包版实时弹幕”显示在弹幕 DOM，样式为 52px 和 `#FFCC00`。
- Windows 安装包：`apps/danmaku-desktop/release/ACTIVE 弹幕工具 Setup 0.1.0.exe`，119,665,086 字节；`app.asar` 含 `dist/main.js`、`dist/preload.cjs` 和 `launcher/`，外部资源含 `screen-web` 构建产物。
- 打包器依赖：`electron-builder@26.15.7`，并在 `pnpm-workspace.yaml` 精确覆盖 `app-builder-lib>@electron/get: 3.1.0`，以提供 Windows NSIS 构建所需的缓存枚举；Electron 本体仍使用 `@electron/get@5.1.0`。

## 关键文件 SHA-256

```text
apps/backend/app/modules/danmaku/service.py 03670CA69469FE48D47592015E5CF9AE884D41D6927797DE6450F85A60BC3726
apps/backend/app/modules/danmaku/router.py B6BB5DF75B931B2A4742905D41747E3D58553214149513E315C8A860A549218A
apps/backend/app/modules/danmaku/manager.py 9550A28DE388A48FEC659863A1531E44C107350400C58D0DBB994EF63E8D5C32
apps/backend/tests/test_danmaku.py 7FB82E9996C0EDB6ACD845CA0F97CEA2FD0DC37F33F0E7DCB8251B538D0C3FA7
apps/admin-web/src/views/danmaku/index.vue 31B3421BAF94401A3DC77C6B624A41C9C7912331A055E70607C666CF69913D81
apps/screen-web/src/components/realtime/DanmakuOverlay.vue 256AEFDF1C42DC0B7176F770DD36AF72C14E41D63ED15F38BDBC3E3AFAF3865A
apps/danmaku-desktop/src/main.ts 0A3AED047D06274F12CE338F478686C71E86FF41370B7EA08DAF0DD6BA239129
apps/danmaku-desktop/src/preload.cts 95BC2B33D39C527FBE317F3ECBC8215B134064159B463F79BF26A254B451A1DA
apps/danmaku-desktop/package.json 318922CE7E7C1344E518D47E7B870748F953C32BDFD74B0262C93E2C6622EBC1
pnpm-lock.yaml E3D98A2AE7F9B5751293E6760F3696B62D3A8714D907CDAE80C9CE0E7303AE25
```
