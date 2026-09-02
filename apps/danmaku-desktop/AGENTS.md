# 弹幕桌面工具模块说明

## 模块简介

`apps/danmaku-desktop` 是 Windows 优先的 Electron 宿主。它通过管理员生成的活动级弹幕 token 校验会话，支持多屏投放；
让用户选择一个或多个显示器后，在每个目标屏幕创建透明、置顶、鼠标穿透的弹幕窗口。

## 目录说明

- `src/main.ts`：主进程，负责窗口、托盘、显示器、受限 IPC 和临时会话。
- `src/preload.cts`：使用 `contextBridge` 暴露逐项 IPC，不暴露通用 Electron API。
- `launcher/`：本地启动页，输入 token、API 地址和显示器；启动控制窗口默认 680×720，页面默认隐藏滚动条。

## 主要流程

启动页调用主进程校验 token 并读取 `/danmaku/session`；主进程只在内存保存 token、会话和 `displayIds`，
然后为每个选中屏幕创建一个 `screen-web` 弹幕渲染窗口。覆盖窗口使用 `setIgnoreMouseEvents(true, { forward: true })`，
不获取焦点。

## 注意事项

- 令牌不得写入 localStorage、文件、日志或安装包配置。
- 渲染窗口必须保持 `contextIsolation`、`sandbox` 和关闭 `nodeIntegration`。
- `Ctrl+Shift+D` 与托盘菜单共享停止/恢复逻辑；移除一个目标显示器时只关闭对应覆盖层，全部目标显示器移除后才回到启动页。

## 本次修复说明

- 托盘退出通过 `app.quit()` 触发；`before-quit` 先设置 `isQuitting`，使 launcher close handler 放行正常退出，
  `will-quit` 仅负责注销全局快捷键。
- 启动页支持勾选多个显示器，默认勾选主屏；同一会话在所有选中显示器上同步显示弹幕。
- 停止、恢复、快捷键和显示器移除流程保持原有行为；桌面模块使用 `pnpm --filter @active/danmaku-desktop typecheck`
  验证主进程类型。
- 弹幕覆盖窗口关闭 `backgroundThrottling`，保证非聚焦透明窗口中的 CSS 弹幕动画和统一调度循环不被后台节流；
  会话设置透传 `entry_interval_seconds` 和 `max_wait_seconds`，实际入场与碰撞调度由 screen-web 渲染器负责。
- `dist:win` 会先构建 `screen-web`，再把 `screen-web/dist` 写入 `release/win-unpacked/resources/screen-web`；
  弹幕表情渲染变更后必须使用新生成的安装包，旧解压目录不会自动更新。
