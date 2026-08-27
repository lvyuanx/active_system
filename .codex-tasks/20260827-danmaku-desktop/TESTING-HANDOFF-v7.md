# 测试交接 v7

任务：T3 文档修正后的最终完整重测，活动弹幕桌面悬浮工具
输入版本：TASK-v1
状态：completed
结论：文档修正后的完整回归通过；AC-001 至 AC-010 均有当前测试、静态或历史实测证据，未发现阻断问题。
证据：screen-web 单测和类型检查、后端 26 passed、全量 pnpm build、Electron typecheck、Windows x64 NSIS 均退出 0；
最终 46 项实施清单重新核对，代码规范和 git diff 检查通过，打包内 screen-web 与源 dist 完全匹配。
变更文件：测试本身未修改生产代码、测试代码或业务文档；本轮输入包含此前已完成的 danmaku-desktop/AGENTS.md 路径 typo 修正。
风险或阻塞：本轮未重新驱动 Windows 覆盖窗口、底层鼠标穿透、多显示器移除、托盘/快捷键界面和真实网络离线故障；
这些使用此前未改变部分的历史证据，并明确列为覆盖缺口。
下一步：进入串行只读最终复审后的逐项验收。

## 测试环境和工作包

- Windows PowerShell；Node.js 22.21.1；pnpm 11.16.0；Python 3.11.1。
- 工作包：WORKPACKAGE-v10.json；工作树：D:\projects\active_system；输入 HEAD：
  4e35b3da19742aff672cdd58910bbf60b8935f59；输入 tree：0b0d3e4ed5a85a37eebe3aadf45782feaa8d0fb4。
- 最终 46 项实施文件的 input_manifest_sha256：ADF85AC263E60DD4212DCECB8AF1379F33A4954C2B5029339481A82B79DE1D85。
- 当前实施文件均在预期清单内，声明 SHA-256 与实际一致；测试工作包 actual_file_manifest 为空，
  未产生 write_scope 外的受跟踪写入。

## 命令结果

| 命令 | 退出码 | 结果 |
| --- | ---: | --- |
| pnpm --filter @active/screen-web test | 0 | message-order tests passed，含 201 个信号边界、去重、游标和入口四值测试 |
| pnpm --filter @active/screen-web typecheck | 0 | vue-tsc --noEmit 通过 |
| python -m pytest -q apps/backend | 0 | 26 passed，1 条既有弃用警告 |
| pnpm build | 0 | admin、danmaku-desktop、screen、user 四个工作区构建完成 |
| pnpm --filter @active/danmaku-desktop typecheck | 0 | tsc --noEmit 通过 |
| pnpm dist:danmaku:win | 0 | x64 NSIS、win-unpacked 和内置 screen-web 生成完成 |
| git diff --check | 0 | 通过；仅有 Git 的 LF/CRLF 提示 |

NSIS 使用 CSC_IDENTITY_AUTO_DISCOVERY=false 和
ELECTRON_MIRROR=https://npmmirror.com/mirrors/electron/。

## AC 映射

| AC | 结果 | 当前证据 |
| --- | --- | --- |
| AC-001 | PASS | 后端测试覆盖配置范围、区域关系和 activity_id 隔离。 |
| AC-002 | PASS | 后端测试覆盖当前 token 稳定、轮换、旧 HTTP/WS 拒绝和连接失效。 |
| AC-003 | PASS | 后端 WebSocket 测试覆盖首帧认证、ready、结构化错误和关闭。 |
| AC-004 | PASS | 后端测试确认聊天室完整事件保留，弹幕只传四字段摘要。 |
| AC-005 | PASS | 后端测试确认配置保存向连接者推送 settings.updated。 |
| AC-006 | PASS | 全量构建、Electron 类型检查和 NSIS 通过；历史 v2/v3 实测确认启动和显示器选择。 |
| AC-007 | PASS | 当前 Electron 构建和静态窗口安全配置通过；历史 v2/v3 实测确认鼠标穿透。 |
| AC-008 | PASS | 当前 screen-web 测试覆盖 201 个信号的 200 条上限、最早淘汰、最新保留和重复 ID；
  源码与构建确认轨道及全部样式参数。 |
| AC-009 | PASS | 当前自动测试覆盖 100 -> 101 首次 ready 前断线补齐及乱序去重；后端覆盖 after_id，
  历史 v2/v3 有离线恢复实测。 |
| AC-010 | PASS | 当前所有必需命令和 x64 NSIS 构建均退出 0。 |

## 产物证据

| 产物 | 大小 | SHA-256 |
| --- | ---: | --- |
| apps/danmaku-desktop/release/ACTIVE 弹幕工具 Setup 0.1.0.exe | 119,665,599 bytes | C013804732C796F43C7D3E50098ADE969C55A31C7A844C1EA57461EA523A58CF |
| apps/danmaku-desktop/release/win-unpacked/resources/app.asar | 17,699 bytes | 43B876DEF2D5228F7B4169476B2A79E43ACCFE516BF4D5C2C6DE83E142DF25DA |
| apps/danmaku-desktop/release/win-unpacked/resources/screen-web/index.html | 169 bytes | E20D9A7399BAA58327502C5CBA807CA7275D6BBEC8C67505564210BBEFFA1638 |

打包内 screen-web 共 3 个文件，与当前 apps/screen-web/dist 的大小和 SHA-256 完全匹配。

## 范围和质量核对

- WORKPACKAGE-v10 的实施清单应为 46/46 匹配；测试写入范围内无受跟踪新增或修改。
- 27 个实施代码/模板/样式文件通过单行不超过 120 字符、单文件不超过 500 行检查。
- App.vue 的普通入口和严格 =1 弹幕入口、message-order 测试和 Electron before-quit 均已静态复核。

## 覆盖缺口

本轮未独立重新执行 Windows 覆盖窗口启动、底层普通应用点击、多显示器拔除、托盘/快捷键操作、
真实网络离线/恢复故障注入；这些不被表述为本轮新实测。历史 v2/v3 的鼠标穿透、启动选择和离线恢复
证据仅用于未改变功能的补充回归。单进程内存广播、多副本部署限制和 HTTP 环境下 token 传输风险仍存在。

## 门禁结论

- 包级测试门禁：PASS。
- 集成测试门禁：PASS；开发修复工作包 v8 与最终回归工作包 v10 完成，required_package_barrier 通过。
- 本轮测试无代码或文档写入。
- 未申请用户豁免。
