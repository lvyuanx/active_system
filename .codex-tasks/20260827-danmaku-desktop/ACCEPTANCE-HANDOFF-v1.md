# 最终验收交接 v1

任务：T3 最终逐项验收，活动弹幕桌面悬浮工具
输入版本：TASK-v1
状态：completed
结论：ACCEPTED；AC-001 至 AC-010 全部 PASS。
证据：最终回归命令均退出 0；独立后端测试 26 passed；WORKPACKAGE-v10 的 46/46 文件 SHA-256 匹配；
三个 Windows 产物存在且哈希匹配；独立静态核对 13/13 通过；验收串行只读且 actual_file_manifest 为空。
变更文件：无；验收角色未修改生产代码、测试资产、业务文档、工作流资料或 Git 元数据。
风险或阻塞：本轮未重新驱动 Windows 覆盖窗口、鼠标穿透、多显示器移除、托盘/快捷键和真实网络离线恢复，
这些仅引用历史实测。浏览器无法访问本机旧开发服务，该服务另有 Vite 缺失 chunk 的 500 环境异常，
不影响已通过的生产构建和 NSIS 产物。单进程广播、多副本部署和 HTTP token 传输风险仍需按部署环境处理。
下一步：任务图完成；发布前在目标 Windows 部署环境进行专项实机验证。

## 验收环境和快照

- Windows PowerShell；Node.js 22.21.1；pnpm 11.16.0；Python 3.11.1。
- 工作树：D:\projects\active_system；分支：master。
- HEAD：4e35b3da19742aff672cdd58910bbf60b8935f59。
- HEAD tree：0b0d3e4ed5a85a37eebe3aadf45782feaa8d0fb4。
- 最终工作包：WORKPACKAGE-v10.json；46 项清单当前 46/46 匹配，未发现越界写入或 staged 文件。

## AC 映射

| AC | 结果 | 验收证据 |
| --- | --- | --- |
| AC-001 | PASS | 当前后端自动测试和源码静态核对覆盖配置读取/更新、范围/区域校验与 activity_id 隔离。 |
| AC-002 | PASS | 当前后端自动测试和 HMAC/版本静态核对覆盖 token 稳定、轮换、旧 HTTP/WS 拒绝和旧连接关闭。 |
| AC-003 | PASS | 当前 WebSocket 自动测试覆盖有效 token 的 session/ready 和无效 token 的结构化错误/关闭。 |
| AC-004 | PASS | 当前后端自动测试与摘要白名单核对确认聊天室完整事件保留，弹幕仅含四字段摘要。 |
| AC-005 | PASS | 当前后端自动测试和渲染器静态核对确认 settings.updated 实时推送及样式应用。 |
| AC-006 | PASS | 当前 Electron 源码、类型检查、构建/产物和历史启动/显示器选择实测支持；本轮未重做 Windows UI。 |
| AC-007 | PASS | 当前 Electron 安全配置和历史鼠标穿透实测支持；托盘、快捷键、显示器移除本轮未重做。 |
| AC-008 | PASS | 当前 message-order 自动回归覆盖乱序、去重、201 个信号的 200 条上限、游标完整补齐。 |
| AC-009 | PASS | 当前自动/后端测试覆盖首次 ready 前 100 -> 101、after_id、不重复和活动关闭；历史网络恢复实测补充支持。 |
| AC-010 | PASS | screen-web 测试/typecheck、后端 26 passed、全仓 build、Electron typecheck、Windows x64 NSIS 均退出 0。 |

## 当前独立补充检查

| 检查 | 结果 |
| --- | --- |
| python -B -m pytest -q -p no:cacheprovider apps/backend | 0，26 passed |
| screen-web 与 danmaku-desktop --noEmit typecheck | 均为 0 |
| node apps/screen-web/scripts/test-message-order.mjs | 0 |
| git diff --check | 0 |
| 46 项清单、三个产物哈希 | 0，均匹配 |
| 独立静态核对 | 0，13/13 |

## 证据边界

当前验收没有把历史 Windows UI、鼠标穿透和真实离线恢复写成当前新实测。浏览器检查因本机开发服务缺失
Vite chunk 返回 500 而未形成页面证据；生产构建与 NSIS 已独立成功并完成产物核对。流程记录
PERMISSION_NOT_READONLY，全部最终门禁按串行路径执行，不宣称并发权限隔离。
