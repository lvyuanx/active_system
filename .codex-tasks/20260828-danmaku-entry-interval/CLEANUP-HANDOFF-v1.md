任务：完成 TASK-v1 的临时服务、隔离 Electron 实例和交付证据清理。
输入版本：TASK-v1；验收交接为 ACCEPTANCE-HANDOFF-v1。
状态：completed
结论：临时测试服务和隔离 Electron 主进程已关闭；用户原有安装版 ACTIVE 弹幕工具会话未被停止或修改。
证据：
- 已停止本次启动的本地假 WebSocket/HTTP 服务和两个隔离 Electron 实例。
- 隔离实例使用的 `.codex-runtime/electron-entry-interval` 与 `.codex-runtime/electron-entry-interval-cdp` 仅包含 Electron 本地缓存，不属于项目源代码或 Git 产物；未执行破坏性清理以避免误删用户数据。
- `apps/danmaku-desktop/release/ACTIVE 弹幕工具 Setup 0.1.0.exe` 和对应 blockmap 已保留作为交付产物。
- TaskGraph 和五份角色交接证据已生成，工作树未执行 reset、clean 或提交。
变更文件：新增本清理交接；保留源代码、测试、文档和安装包，不删除用户既有未提交改动。
风险或阻塞：本地 Electron 测试缓存目录仍存在但不影响项目运行；如需释放磁盘空间，可人工删除这两个明确目录。
下一步：任务完成，等待用户使用新的 Windows 安装包。
