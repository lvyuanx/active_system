任务：依据 TASK-v1 验证完整进入后间隔入场改造。
输入版本：TASK-v1；开发交接为 DEVELOPMENT-HANDOFF-v1。
状态：completed
结论：自动化测试、类型检查、生产构建、NSIS 打包和隔离桌面端运行验证均通过。
证据：
- `python -m pytest -q`（工作目录 `apps/backend`）：31 passed；仅保留既有 chat router 的 1 条弃用警告。
- `pnpm --filter @active/screen-web test`：message-order、task-scheduler、danmaku-layout 三组测试全部通过，覆盖完整进入时间、间隔门槛、单轨道提前入场、跨轨道、追赶和 CSS 终点。
- `node apps/admin-web/scripts/test-danmaku-settings.mjs`：入场间隔绑定、范围步长和队列最大等待控件静态回归通过。
- `pnpm -r typecheck`：admin-web、screen-web、user-web、danmaku-desktop 四个项目全部通过。
- `pnpm -r build`：三个前端和 Electron 主进程全部构建成功；仅有既有依赖注释和管理端 chunk 体积警告。
- `pnpm dist:danmaku:win`：退出码 0，生成 Windows x64 NSIS 安装包及 blockmap。
- 隔离 Electron/CDP 冒烟：单轨道、8 秒飞行、入场间隔 1 秒、队列最大等待 5 秒；第一条完整进入约 1155ms，第二条约 2238ms 出现，间隔约 1083ms，二者同时存在且第一条尚未离屏。
- AC 映射：AC-001/002 由后端默认、迁移和边界用例覆盖；AC-003 由 ready/session 与设置广播断言覆盖；AC-004/005 由几何测试和 CDP 运行数据覆盖；AC-006/007 由队列、调度和静态回归覆盖；AC-008/009 由类型检查、构建、打包和文档审计覆盖。
变更文件：测试阶段未修改生产代码以绕过失败；测试脚本和任务证据已同步。
风险或阻塞：系统中已有另一个安装版 ACTIVE 弹幕工具会话，未对其做输入或停止操作；隔离实例的透明系统截图受遮挡，但 CDP DOM 时间采样已验证实际入场时序。
下一步：交由审核阶段检查实现范围和证据一致性。
