任务：T3 审核修复后的完整重测，活动弹幕桌面悬浮工具
输入版本：TASK-v1
状态：completed
结论：审核修复后的完整回归通过；AC-001 至 AC-010 均有当前测试、静态或历史实测证据，未发现新的阻断问题。
证据：screen-web 单测和类型检查、后端 26 passed、全量 pnpm build、Electron typecheck、Windows x64 NSIS 均退出 0；WORKPACKAGE-v9 的 46 项 SHA-256 匹配，测试无越界受跟踪写入。
变更文件：无测试代码、生产代码或业务文档变更；更新 WORKPACKAGE-v9 测试结果和本交接证据。
风险或阻塞：本轮未重新驱动 Windows 覆盖窗口、底层鼠标穿透、多显示器移除、托盘/快捷键界面和真实网络离线故障；这些使用此前未改变部分的历史证据并明确列为覆盖缺口。
下一步：进入串行只读复审；复审通过后进入逐项验收。

## 测试环境和工作包

- Windows PowerShell；Node.js 22.21.1；pnpm 11.16.0；Python 3.11.1。
- 工作包：WORKPACKAGE-v9.json；工作树：D:\projects\active_system；输入 HEAD：
  4e35b3da19742aff672cdd58910bbf60b8935f59；输入 tree：
  0b0d3e4ed5a85a37eebe3aadf45782feaa8d0fb4。
- 输入实施清单：46 项；input_manifest_sha256：
  7C7BF61D0C365D69F4146940EF3B976EDE9094E6F7265B5B124B1AFD660D2955。
- 当前 46 项实施文件均在预期清单内，声明 SHA-256 与实际一致；测试工作包 actual_file_manifest 为空，
  未产生 write_scope 外的受跟踪写入。
- 测试子角色未返回完整命令结果，主线程按同一冻结 v9 工作包串行接管测试；该接管事实不影响命令退出码，
  并已写入任务图事件。

## 命令结果

| 命令 | 退出码 | 结果 |
| --- | ---: | --- |
| pnpm --filter @active/screen-web test | 0 | message-order tests passed，含 201 个信号边界和入口四值测试 |
| pnpm --filter @active/screen-web typecheck | 0 | vue-tsc --noEmit 通过 |
| python -m pytest -q apps/backend | 0 | 26 passed，1 条既有弃用警告 |
| pnpm build | 0 | admin、danmaku-desktop、screen、user 四个工作区构建完成 |
| pnpm --filter @active/danmaku-desktop typecheck | 0 | tsc --noEmit 通过 |
| pnpm dist:danmaku:win | 0 | x64 NSIS、win-unpacked 和内置 screen-web 生成完成 |

NSIS 使用 CSC_IDENTITY_AUTO_DISCOVERY=false 和
ELECTRON_MIRROR=https://npmmirror.com/mirrors/electron/。

## 审核修复回归

- AC-008：实时补齐状态从完整消息 Map 改为最多 200 个去重消息 ID；超限淘汰最早信号，
  但 HTTP 恢复仍从 lastMessageId 通过 after_id 获取完整遗漏范围。
- 托盘退出：before-quit 先设置 isQuitting，launcher close handler 放行，will-quit 仅注销全局快捷键。
- 入口分流：只有 danmaku-overlay=1 进入弹幕层，无参数、0、false 进入普通大屏。
- AC-009 既有首次 ready 前断线修复保持通过：ready 快照不会直接抬高客户端游标。

## AC 映射

| AC | 结果 | 当前证据 |
| --- | --- | --- |
| AC-001 | PASS | 后端测试覆盖配置范围、区域关系和 activity_id 隔离。 |
| AC-002 | PASS | 后端测试覆盖当前 token 稳定、轮换、旧 HTTP/WS 拒绝和连接失效。 |
| AC-003 | PASS | 后端 WebSocket 测试覆盖首帧认证、ready、结构化错误和关闭。 |
| AC-004 | PASS | 后端测试确认聊天室完整事件保留，弹幕只传四字段摘要。 |
| AC-005 | PASS | 后端测试确认配置保存向连接者推送 settings.updated。 |
| AC-006 | PASS | 当前全量构建和 Electron 类型检查通过；token、启动和显示器流程未被修复改动，
  历史 v2/v3 实测确认过启动和显示器选择，本轮未重新操作界面。 |
| AC-007 | PASS | 当前 Electron 构建和静态窗口安全配置通过；before-quit 修复覆盖托盘退出生命周期，
  历史 v2/v3 实测确认过鼠标穿透，本轮未重新操作窗口。 |
| AC-008 | PASS | 当前 screen-web 自动测试覆盖 201 个信号的 200 条上限、最早淘汰、最新保留、
  重复 ID 不增长；源码和构建确认轨道及全部样式参数。 |
| AC-009 | PASS | 当前自动测试覆盖 100 -> 101 首次 ready 前断线补齐及乱序去重；后端覆盖 after_id
  和关闭活动；历史 v2/v3 有离线恢复实测，本轮未重新注入网络故障。 |
| AC-010 | PASS | 当前所有命令和 x64 NSIS 构建均退出 0。 |

## 产物证据

| 产物 | 大小 | SHA-256 |
| --- | ---: | --- |
| apps/danmaku-desktop/release/ACTIVE 弹幕工具 Setup 0.1.0.exe | 119,665,499 bytes | E458C99DB9CF9C5F2A92BB2FEDE56A4DE848F5B1C4BDBD56BC068244AC41B9C1 |
| apps/danmaku-desktop/release/win-unpacked/resources/app.asar | 17,699 bytes | 43B876DEF2D5228F7B4169476B2A79E43ACCFE516BF4D5C2C6DE83E142DF25DA |
| apps/danmaku-desktop/release/win-unpacked/resources/screen-web/index.html | 169 bytes | E20D9A7399BAA58327502C5CBA807CA7275D6BBEC8C67505564210BBEFFA1638 |

打包内 screen-web 共 3 个文件，与当前 apps/screen-web/dist 的大小和 SHA-256 完全匹配。

## 范围和质量核对

- WORKPACKAGE-v9 的实施清单 SHA-256：46/46 匹配。
- 测试前后主工作树的实施文件均未超出 v9 预期清单；测试写入范围内无受跟踪新增或修改。
- 27 个实施代码/模板/样式文件通过单行不超过 120 字符、单文件不超过 500 行检查。
- git diff --check 通过。
- App.vue 的普通入口和严格 =1 弹幕入口、message-order 测试和 Electron before-quit 均已静态复核。

## 覆盖缺口

本轮未独立重新执行 Windows 覆盖窗口启动、底层普通应用点击、多显示器拔除、托盘/快捷键操作、
真实网络离线/恢复故障注入；这些不被表述为本轮新实测。历史 v2/v3 的鼠标穿透、启动选择和离线恢复
证据仅用于未改变功能的补充回归。单进程内存广播、多副本部署限制和 HTTP 环境下 token 传输风险仍存在。

## 门禁结论

- 包级测试门禁：PASS。
- 集成测试门禁：PASS；开发修复工作包 v8 与本次 v9 均完成，required_package_barrier 通过。
- 本轮测试无代码或文档写入。
- 未申请用户豁免。
