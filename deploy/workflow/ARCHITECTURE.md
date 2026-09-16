# TASK-v1 架构交接

任务：双容器一键部署 T6 架构。
输入版本：TASK-v1；HEAD 70793924d129de74b26517a852a1fe6cbe412fc3。
状态：completed
结论：双服务 Compose、多阶段前端镜像、带发布记录串行升级；可进入开发。
证据：已读取冻结任务、应用说明、Compose/Dockerfile/Nginx、Settings、路由和 URL 调用。
变更文件：无（主 Agent 记录本交接）。
风险或阻塞：Linux daemon 不可用，实际 Docker 全部 AC 仍需运行证据。
下一步：开发、测试、审核、验收；完整原始架构交接保留在 architecture2 子 Agent。

## 模块及接口

- 保留 deploy/compose/docker-compose.yml 和两个 Dockerfile 路径，Compose 仅 backend/nginx，固定项目名。
  镜像完整提交 SHA 标签，保存实际 ID；backend expose 8000，无发布端口；nginx 默认可配 80。
- DATABASE_PATH=/app/data/active_system.db，MEDIA_ROOT=/app/data/media，绝对宿主机数据路径挂载。
  单 uvicorn；Python 标准库 HTTP health；nginx wget health。
- Node 多阶段锁 pnpm11.16.0/frozen lock，过滤三个 Web，不跑根 build/Electron。
  生产显式 /admin/ /screen/ /user/ base，大屏默认相对 base 保持 Electron。
- 各站独立 SPA，assets 缺失404，根和尾斜杠跳转；API 原路径、6m 上传、WS headers/长超时。
  后端重建时 nginx 同时重建，避免上游IP缓存。转发 Host/X-Forwarded-*。
- Router 用 BASE_URL；API 显式优先，生产同源、开发 localhost；URL API 推导 ws/wss。
  管理端本应用集中生成入口，保留活动参数/显式URL；桌面 bootstrap 优先。
  用户端根扫码提示不循环；同步 start.ps1 -Docker。

## 配置与主流程

- 根 upgrade.sh，可拆 deploy/scripts；deploy/.env.example；deploy/.env 不入 Git；
  deploy/runtime 保存数据/发布/备份，全部忽略；umask077，敏感文件600目录700。
- env 为严格单行 KEY=value 字面格式，不 source/eval；白名单、重复/未知键和插值字符拒绝，
  清除同名继承变量，导出已验证值；校验密码/JWT/安全码非空非示例，不输出解析配置。
- 定位仓库→固定 flock 非阻塞锁→依赖/daemon/Compose/config/干净树检查（含未跟踪）→
  当前分支实际上游fetch→只允许本地等于或落后上游→merge --ff-only；超前也拒绝。
- 自更新必须重新执行最新脚本，继承持锁FD且验证FD/锁路径/目标SHA，避免内部参数绕过与无限fetch。
  续跑重新校验配置；正在执行文件的修改通过 main 函数整体已解析/冻结入口处理。
- 构建两镜像及 compose config --quiet；临时 nginx --add-host backend:127.0.0.1 执行 nginx -t，
  不依赖首次部署DNS。全部通过前旧服务保持运行。
- 每次尝试唯一目录，保存提交/镜像ID/绝对数据路径/完整解析配置；配置密钥禁止日志输出。
  有容器无成功记录拒绝接管；有成功记录禁止静默换数据目录或项目名。

## 备份与恢复

- 按上一成功配置停 backend 并确认停止；旧镜像临时容器只读数据卷归档完整数据到 .partial，
  校验后原子改名，备份在数据目录外。失败/中断恢复旧后端并验证，恢复失败明确报告。
- 然后 up -d --no-build --pull never --force-recreate --wait --wait-timeout，不 down。
  检查两健康容器及经 nginx 三入口/API。全部通过才原子更新 current/previous 记录。
- 失败保留成功指针、失败尝试、镜像/备份，不自动覆盖数据；显示阶段及 ps/logs 命令。
- 人工恢复配套旧配置镜像及此次切换前备份：停后端，保存失败现场；恢复备份到新目录，
  旧配置受控副本改挂载；no-build/pull never 启动验证。原失败数据不删除不覆盖。
  恢复后记录必须可被下一次升级使用，不留下静默数据目录漂移。

## 验证

- Git 临时仓库+Docker替身：快进/分叉/超前/无上游/脏树/fetch/build/config失败/锁/自更新。
- env注入/重复键、备份失败恢复、信号、健康失败不推进指针、失败重试；切换前没有stop/up/down。
- 生产build、子路径/路由/二维码/显式URL/ws/wss/Electron、用户根入口。
- Linux真实首次/二次升级、数据/媒体、登录上传聊天抽奖WS及恢复；替身不替代真实验收。

## 工作包及权限

SERIAL_SHARED_WRITE，PERMISSION_NOT_READONLY，无并发资格；不创建隔离worktree。
开发仅当前主树指定部署/三Web/start.ps1/说明/测试；主Agent单独维护workflow。
绑定 TASK-v1/HEAD/输入清单。生产写入完成后测试才开始，测试仅测试资产。
平台角色不需在串行降级路径核对不存在的detached worktree，不宣称隔离或并发成功。
旧结论失效及门禁传播按TaskGraph；未完成Linux实测不称T6通过。
