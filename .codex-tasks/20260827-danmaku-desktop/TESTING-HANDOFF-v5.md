任务：T3 修复后最终重测，活动弹幕桌面悬浮工具
输入版本：TASK-v1
状态：completed
结论：修复后的完整回归和 Windows x64 NSIS 打包通过；AC-001 至 AC-010 均有当前自动化、静态或历史实测证据，未发现新的阻断问题。
证据：screen-web 单测和类型检查、后端 26 passed、全量构建、Electron typecheck 均退出 0；NSIS 重跑退出 0；WORKPACKAGE-v7 的 46 项 SHA-256 清单匹配，测试过程无受跟踪写入。
变更文件：无测试代码、生产代码或业务文档变更；仅生成 WORKPACKAGE-v7 的测试结果和本交接证据。
风险或阻塞：NSIS 首次运行因本任务先前启动的旧打包版进程锁定 ACTIVE 弹幕工具.exe 而退出 1；确认 PID 16676 后停止该任务进程，以相同环境和命令重跑退出 0。当前未重新驱动 Windows UI、多显示器拔除或真实离线网络故障。
下一步：进入只读审核门禁；审核通过后按 AC-001 至 AC-010 逐项验收。

## 测试环境和工作包

- Windows PowerShell；Node.js 22.21.1；pnpm 11.16.0；Python 3.11.1。
- 工作包：WORKPACKAGE-v7.json，工作树：D:\projects\active_system，输入 HEAD：
  4e35b3da19742aff672cdd58910bbf60b8935f59。
- 输入实施清单：46 项；input_manifest_sha256：
  9CEA439FDE4ABDA5E4A1FB814CBF565EF49D6086D178A9ACD72BFA2547EFCB32。
- 清单核对：声明与实际 SHA-256 全部匹配；实施文件不在预期清单之外；测试写入范围内无受跟踪文件变化。
- 主线程接管原因：两个测试子角色均未返回完整结果；第二个子角色仅完成 screen-web 单测（退出 0）后按中断提示停止，
  因此主线程按同一冻结工作包串行执行剩余命令并保留实际证据。

## 命令结果

| 命令 | 退出码 | 结果 |
| --- | ---: | --- |
| pnpm --filter @active/screen-web test | 0 | message-order tests passed |
| pnpm --filter @active/screen-web typecheck | 0 | vue-tsc --noEmit 通过 |
| python -m pytest -q apps/backend | 0 | 26 passed，1 条既有弃用警告 |
| pnpm build | 0 | admin、danmaku-desktop、screen、user 四个工作区构建完成 |
| pnpm --filter @active/danmaku-desktop typecheck | 0 | tsc --noEmit 通过 |
| pnpm dist:danmaku:win（首次） | 1 | 旧任务进程锁定输出文件，EPERM unlink |
| pnpm dist:danmaku:win（释放锁后重跑） | 0 | x64 NSIS、win-unpacked 和内置 screen-web 生成完成 |

NSIS 重跑环境变量为 CSC_IDENTITY_AUTO_DISCOVERY=false 和
ELECTRON_MIRROR=https://npmmirror.com/mirrors/electron/。

## AC 映射

| AC | 结果 | 当前证据 |
| --- | --- | --- |
| AC-001 | PASS | 当前后端测试覆盖管理员配置、范围校验、显示区域关系和活动隔离。 |
| AC-002 | PASS | 当前后端测试覆盖 token 稳定读取、轮换、旧 HTTP/WS 凭证拒绝和连接失效。 |
| AC-003 | PASS | 当前后端 WebSocket 测试覆盖有效首帧 ready、无效 token 结构化错误和关闭。 |
| AC-004 | PASS | 当前后端测试确认聊天室完整消息事件保持不变，弹幕摘要只有四个字段。 |
| AC-005 | PASS | 当前后端 WebSocket 测试确认保存配置推送 danmaku.settings.updated。 |
| AC-006 | PASS | 当前构建和静态路径核对通过；此前 v2/v3 Windows 实测已确认启动页 token、会话和显示器选择，
  本轮未重复驱动界面。 |
| AC-007 | PASS | 当前 Electron 源码和 typecheck 确认透明、无框、置顶、不可聚焦、鼠标穿透配置；
  此前 v2/v3 Windows 实测已确认底层窗口点击，本轮未重复驱动界面。 |
| AC-008 | PASS | 当前源代码静态核对和构建确认轨道、字体、不透明度、时长、区域、颜色及 200 条有界队列；
  本轮未进行逐项动画视觉量测。 |
| AC-009 | PASS | 当前 screen-web 自动回归覆盖高 ID 乱序、去重、游标边界和首次 ready 前断线的
  100 -> 101 补齐；当前后端测试覆盖 after_id 和关闭活动；此前 v2/v3 已有真实离线补齐实测，
  本轮未重新注入网络故障。 |
| AC-010 | PASS | 当前屏幕单测、类型检查、后端 pytest、全量构建、Electron typecheck 和 NSIS 重跑均通过。 |

## 产物证据

| 产物 | 大小 | SHA-256 |
| --- | ---: | --- |
| apps/danmaku-desktop/release/ACTIVE 弹幕工具 Setup 0.1.0.exe | 119,665,430 bytes | 706B023FF26D34DCEFEE5E1F863F43D00AE171663D79B6E05D9569261E6E8E90 |
| apps/danmaku-desktop/release/win-unpacked/resources/app.asar | 17,661 bytes | 0AF6C425DBCE0E054E5B1906C389D62487FFB8C8E7552A3DA6E13FF47864C1A2 |
| apps/danmaku-desktop/release/win-unpacked/resources/screen-web/index.html | 169 bytes | B2B5131EE665C4AFBD59E7D280934DF0B730D4FA85DD6C7124E9B07DCC72828D |

打包内 screen-web 的 3 个文件与 apps/screen-web/dist 的大小和 SHA-256 均匹配。

## 静态和范围核对

- apps/screen-web/src/App.vue 普通入口渲染活动数据大屏，只有 URL 含 danmaku-overlay 时渲染弹幕层。
- message-order.ts 对消息按 ID 去重和升序合并；测试覆盖高 ID 先到、重复消息、游标过滤以及
  ready 最大 ID 为 101 但补齐游标仍为 100 的首次断线场景。
- 最终实施代码文件扫描：27 个代码/模板/样式文件，最大单行不超过 120 字符，单文件不超过 500 行。
- git diff --check 无空白错误；测试前后没有超出 WORKPACKAGE-v7 write_scope 的受跟踪写入。

## 回归范围和覆盖缺口

当前回归覆盖后端弹幕设置和 token、聊天室兼容广播、WebSocket 认证、配置推送、消息游标、关闭活动、
前端排序补齐、四端构建、Electron 主进程编译及 NSIS 产物。

本轮未独立重新执行：Windows 覆盖窗口启动、底层应用鼠标点击、多显示器拔除、托盘/快捷键交互和真实网络
离线/恢复注入；AC-006、AC-007、AC-009 的相关历史实测仅作为未改变部分的补充证据，不能视为本轮新实测。

## 门禁结论

- 包级测试门禁：PASS。
- 集成测试门禁：PASS；required_package_barrier 对应的开发修复工作包和本重测工作包均已成功。
- 测试角色的实际变更文件：无。
- 覆盖缺口已显式记录，未申请用户豁免。
