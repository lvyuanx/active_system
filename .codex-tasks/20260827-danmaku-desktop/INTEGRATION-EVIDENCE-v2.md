任务：TASK-v2 管理端真实聊天室弹幕测试集成回归
输入版本：TASK-v2；WORKPACKAGE-v11 已刷新为当前 HEAD tree 400f5afbb30ec7c92951e9e223da07cf59112f1a
状态：completed
结论：主工作树集成和集成级回归通过；真实测试消息已验证同时进入聊天室和弹幕链路。
证据：

- `python -m pytest -q apps/backend` 退出码 0，29 passed。
- 新增端到端用例打开真实聊天室和弹幕 WebSocket，开启管理员测试后验证两条通道消息 ID/活动 ID/正文一致，
  发送者为不同的“弹幕测试用户”，并从聊天室和弹幕历史接口读回；重复开启、关闭、重启复用身份和非 open 活动
  409 均有断言。
- `pnpm typecheck` 退出码 0；`pnpm build` 退出码 0；`pnpm --filter @active/screen-web test` 退出码 0；
  `node --check` 启动脚本退出码 0；`pnpm dist:danmaku:win` 退出码 0。
- 最终 NSIS 安装包：`apps/danmaku-desktop/release/ACTIVE 弹幕工具 Setup 0.1.0.exe`，SHA-256
  `31E6E6FBAE207A4BBD8B501DEF42FC22B1FECF2347C3BBD1B8B3812AA9E3F7D1`；app.asar SHA-256
  `B4CF4DE0469E6AB834188ACEF2611D868F249E2EF5C36429C94E4C2FEC4966DE`。
- 浏览器无已登录管理端会话，访问受保护弹幕路由正确显示管理员登录页；未在浏览器中代填密码或提交登录，
  管理端页面可见性以源代码集成、类型检查和生产构建为证据。

变更文件：无；集成者未提交或推送 Git 元数据。
风险或阻塞：未发现集成阻断。浏览器未形成认证后 UI 截图，Windows 多屏/鼠标穿透等实机行为沿用此前交付证据；
本次真实聊天测试相关行为由新增后端端到端用例直接验证。
下一步：独立测试通过后进入只读审核和产品验收；最终清理仅处理已登记的临时产物。

## 集成边界

本次新能力只增加管理员测试控制和后端测试任务，不改变用户端聊天协议、弹幕四字段摘要、token 认证、screen-web
渲染器或 Electron 多显示器实现。共享 SQLite、pnpm 缓存、主工作树和本地服务无法隔离，按 `UNISOLATED_RESOURCE`
使用唯一主树集成者串行执行。
