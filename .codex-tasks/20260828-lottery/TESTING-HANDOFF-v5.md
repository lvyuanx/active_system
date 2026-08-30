任务：TASK-v5 奖品图片上传、持久化、安全访问、管理端交互和大屏展示测试
输入版本：TASK-v5 + ARCHITECTURE-v5 + DEVELOPMENT-HANDOFF-v5 + INTEGRATION-HANDOFF-v5
状态：completed
结论：最终开发修复后的自动化回归全部通过（55 passed）；主集成线程的真实浏览器证据覆盖管理端图片工作流及大屏带图/失效图回退，所有 AC-501～AC-514 均有通过证据。
证据：

- `python -m pytest -q apps/backend/tests`：退出码 0，55 passed，7 个弃用警告。
- `pnpm --filter @active/admin-web test:lottery-image-race`：退出码 0，保存竞态保护断言通过。
- admin typecheck/build/test:danmaku-settings：均退出码 0；admin 无通用 `test` script。
- screen typecheck/build/test：均退出码 0。
- Compose config、Compose YAML 解析和 Nginx 媒体代理静态核对：均通过。
- 新增后端图片测试覆盖三格式、5 MiB 边界/超限、真实 MIME/扩展名、脚本拒绝、失败保留、安全响应头、配置 PUT 保图、跨活动/错误奖品、权限和清理重试。
- 追加覆盖 DecompressionBombError、图片 POST/DELETE 后公开 WS 广播、公开图片无 `v` 拒绝、配置删除奖品/奖项级联媒体回收及中奖记录阻断保留。
- 真实 Edge 大屏收到 `lottery.ready`，渲染活动标题、奖品名、库存、实时连接和无图文字回退，控制台 error/warn 为空。
- 主集成线程浏览器证据（非本 tester 亲自登录）覆盖管理端合法 PNG 选择/预览、保存后预览保留、替换、移除、非法文件提示，及大屏带图 `naturalWidth=1254` 和失效图 404 自动移除回退。
- 主集成线程浏览器证据见 `BROWSER-EVIDENCE-v5-MAIN.md`；本 tester 的浏览器补充记录见 `BROWSER-EVIDENCE-v5.md`。

变更文件：

- `apps/backend/tests/test_lottery_images.py`（仅新增测试用例）
- `.codex-tasks/20260828-lottery/BROWSER-EVIDENCE-v5.md`
- `.codex-tasks/20260828-lottery/TESTING-HANDOFF-v5.md`

风险或阻塞：无阻断项。自动化存在 7 个弃用警告，admin 构建存在依赖注释和大 chunk 警告，均不影响测试结果；主集成浏览器证据来源已明确，未声称由本 tester 亲自登录。
下一步：交由审核和验收阶段复核主集成浏览器证据及本测试交接。

## 测试环境

- Windows 工作区 `D:\projects\active_system`。
- 临时服务：backend `127.0.0.1:8004`、admin `127.0.0.1:5189`、screen `127.0.0.1:5190`。
- Browser plugin `26.820.60940`，Edge extension；未读取 cookies/localStorage。
- 仅使用隔离活动 `aa5d844d-8326-408f-98e2-482a79d3f6c2`，未访问现有用户活动。

## AC 用例映射

| AC | 测试覆盖 | 结果 |
| --- | --- | --- |
| AC-501 | API 合法上传；主集成浏览器选择/预览 | PASS |
| AC-502 | 配置 PUT 保图；主集成浏览器保存后预览保留 | PASS |
| AC-503 | 替换、旧 URL 404、清理；主集成浏览器替换 | PASS |
| AC-504 | 移除、旧 URL 404、清理；主集成浏览器移除 | PASS |
| AC-505 | 无图配置、快照、WS、真实大屏 | PASS |
| AC-506 | SVG/脚本、伪造内容、MIME/扩展名拒绝 | PASS |
| AC-507 | 5 MiB 精确边界与超限 | PASS |
| AC-508 | API 失败保留原图；主集成浏览器非法文件提示 | PASS |
| AC-509 | 管理员/活动用户权限 API；主集成管理员页面 | PASS |
| AC-510 | 跨活动/错误奖品隔离 | PASS |
| AC-511 | 安全 URL、响应头、公开字段；主集成浏览器带图大屏 | PASS |
| AC-512 | 无图回退；主集成浏览器失效图 error 回退 | PASS |
| AC-513 | 替换/删除、孤儿扫描、清理重试 | PASS |
| AC-514 | 全量 lottery/WS/库存/幂等/重置回归 | PASS |

## 失败复现

无阻断失败。主集成线程已在隔离服务和临时管理员会话中完成管理端及大屏浏览器验收；本 tester 未重复输入凭证。

## 回归范围与覆盖缺口

- 回归范围：后端媒体校验/迁移/权限/活动隔离/安全头/替换删除/清理重试/配置 PUT/WS，管理端图片工作流，大屏无图/带图/失效图回退，前端构建及部署配置。
- 覆盖缺口：无必需 AC 缺口；浏览器证据来源为主集成线程，截图由 Browser 工具展示且未落盘。
