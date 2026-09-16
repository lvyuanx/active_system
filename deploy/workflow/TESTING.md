# TASK-v1 独立测试报告

任务：双容器部署升级包 qa-serial 独立测试。
输入版本：TASK-v1；完整读取 ARCHITECTURE.md、DEVELOPMENT.md、QA-PLAN.md；HEAD
70793924d129de74b26517a852a1fe6cbe412fc3。
状态：completed
结论：可执行的本机测试全部通过；必需 Linux Docker 用例缺失，T6 测试门禁 BLOCKED。
证据：本文命令、flow-963、git-118 和 proxy/results.json、10 张截图。
变更文件：新增 deploy/tests/test_release_flow.sh、test_git_flow.sh、run_proxy_qa.py、proxy_browser.cjs；
新增的临时数据库、媒体、日志、证据与报告均在 deploy/runtime/test-qa。
风险或阻塞：Linux Docker daemon 不可用；不以替身/Windows Nginx 结果替代部署验收。
下一步：开发同步测试说明及遗留文档；Linux 环境执行首次/二次升级、flock、自更新、备份恢复后重新测试门禁。

## 环境与工作包

Windows、Git Bash、Python 3.11、原生 Nginx 1.28.3、Playwright Chromium 1187；
HTTP 18080、backend 18081、外层自签 TLS 18443。后端独立 cwd 和显式测试环境变量，未读取根 .env。
启动与停止由测试脚本 finally 管理；结束查询三个端口均无 Listen。
包绝对路径 D:/projects/active_system；SERIAL_SHARED_WRITE；read_scope 全仓库，
write_scope deploy/tests 与 deploy/runtime/test-qa。开发完成屏障成立，生产期间未发生写入。
没有 detached worktree、补丁集成或 Git 元数据操作；临时测试仓库位于授权临时范围。
此处是共享主树开发完成后的串行应用集成回归，不声称执行了隔离补丁集成。

## 命令与结果

- `D:/services/Git/bin/bash.exe deploy/tests/test_release_flow.sh`：退出 0，12 个场景。
  config/build/nginx 失败不 stop/up；backup 失败恢复旧后端；up/probe 失败不推进 current；
  成功推进 current/previous；无记录、pending 缺失/外来镜像拒绝；匹配 pending 进入重试；
  成功记录镜像漂移拒绝。使用 Docker/Compose 替身，不证明实际容器或备份行为。
- `D:/services/Git/bin/bash.exe deploy/tests/test_git_flow.sh`：退出 0，7 个场景。
  真实临时 bare remote/clone：equal/behind 通过，ahead/diverged/missing-upstream/fetch-failed/dirty 拒绝，
  所有拒绝场景 HEAD 不变。exec 续跑入口以函数替身捕获，不证明 Linux FD 继承。
- `python deploy/tests/run_proxy_qa.py`：最终退出 0，HTTP/HTTPS 各执行完整业务回归。
  Nginx 配置 -t 成功；三个入口非空、四入口尾斜杠/根重定向保留查询、三个缺失资源 404；
  真实浏览器管理员登录、活动创建、注册用户、开启活动；活动页面刷新、二维码图与同源地址、
  大屏 popup URL 保留 activity_id、用户 chat 深路径刷新、页面自动建立 ws/wss；
  图片 multipart 上传、读取、错活动 404；聊天 message.created；开奖管理员 draw.result 和公共 drawn
  draw_id 一致、中奖用户正确、公共消息不泄露手机号；pageerror 为 0，无 localhost:8000 请求。
  第一次运行因测试临时目录缺少 Windows Nginx temp 子目录退出 1，修正测试夹具后通过；无生产变更。
- `git diff --check`：退出 0。现有 CRLF 提示不属于 diff 错误。
- PowerShell 对开发输入 40 个文件逐项 Get-FileHash：测试前后无差异；HEAD 前后不变。

## AC 映射

| AC | 实测子范围 | 正向/反向/边界/回归 | 完整结果 |
| --- | --- | --- | --- |
| AC-001 | 原生代理两协议三入口与健康 | 正向三端/health；反向缺资源；边界尾斜杠 | BLOCKED：无 Linux 镜像构建/两个健康容器 |
| AC-002 | Git 快进、发布记录切换顺序 | 正向推进记录；反向构建失败保持旧记录；数据切换前停止顺序 | BLOCKED：无实际容器升级及持久化 |
| AC-003 | 三入口、SPA 刷新、二维码、大屏 URL | 正向真实 UI；反向 404；边界查询保留、HTTPS；回归子路径 | BLOCKED：Electron/显式地址/本地开发及 Linux 未完整回归 |
| AC-004 | 真实登录注册、上传读取、chat 和开奖广播 | 正向 HTTP/HTTPS ws/wss；反向错活动媒体 404；公开广播不泄露手机号 | BLOCKED：Linux Docker 下同场景待执行 |
| AC-005 | 12 发布控制流和 7 Git 场景 | 反向失败不 stop/up/不推进指针；pending 重试边界；脏树/分叉/超前 | BLOCKED：真实 flock、完整自更新、缺依赖与密钥本轮未重跑 |
| AC-006 | 备份失败恢复旧后端控制流、失败诊断 | 反向 backup/up/probe；旧成功记录不变；不自动回滚数据 | BLOCKED：真实备份及人工恢复未执行 |

TASK-v1 只有 AC-001 至 AC-006；岗位模板 AC-018 不适用，不伪造不存在的验收编号。
包级测试资产与本机结果有效，但包级完整测试门禁 BLOCKED；Linux 集成门禁 BLOCKED。
既有 71 项 backend 基线、settings 和 artifacts 基础测试由开发执行，本次未无变化重跑，不能归为独立实测。

## 文件与快照

开发清单 development-manifest.json SHA-256：
73c096e63f3f81382669c55d670a90edc6ff4ac648fa0c569bca5d636dd74b64。
新增资产 SHA-256：

- test_git_flow.sh：8c9807e9d09b286a9944bebed1aed08586102e99c9116002a6cf53c20bbd7579
- test_release_flow.sh：fcf083b13aab8bb7b537bbf04bccc5100bf3bd1e632d32d538b24b7effff09ac
- run_proxy_qa.py：c5ce50d646bd46871a5dfe21cf3b160581d4c116e508b9838820f61be7341976
- proxy_browser.cjs：05bc9ab0c00f5f8c8b65ab22d44dfa2ff1fd757bffb5b2b6d193b0a9ffcbaf4a

共享串行路径无补丁 SHA，NOT_APPLICABLE；未调用 git add/commit/branch/worktree，未隐藏已有改动。
上述 Git 元数据限制针对主仓库；临时授权测试仓库执行了 init/add/commit/clone，提交信息使用中文。
QA_MANIFEST 可以指定快照路径；未提供可用文件时脚本明确提示跳过快照校验。本轮使用完整开发清单校验。

## 问题与覆盖缺口

本轮执行未复现生产阻断故障。主 Agent 另发现 WIKI.md 旧 start.ps1 -Docker 描述需开发修正；
测试未修改该业务文档。新增测试资产描述需开发同步 deploy/tests/AGENTS.md。
未执行 Linux Docker、真实 flock 竞争与中断、FD 自更新续跑、恢复后再次升级、低磁盘/信号注入、
精简 workspace frozen-lock 安装、Electron 和显式部署地址回归。截图人工检查活动页二维码与布局正常；
截图与地址断言没有使用扫码设备解码二维码。所有缺口不能记为 PASS。
