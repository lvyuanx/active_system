# Linux 一键部署

服务器需要 Linux、Bash 4+、Git、Docker Engine、Docker Compose v2（支持 `up --wait-timeout`）、
util-linux 的 flock、coreutils。当前用户必须能访问 Docker daemon，Git 必须能无交互拉取远程仓库。
依赖下载需要能访问镜像仓库、npm 和 PyPI；宿主机不需要 Node.js、pnpm 或 Python。
本方案用于全新安装，未提供旧服务器数据迁移；允许升级短暂停机。

## 首次配置

```bash
git clone <你的仓库地址> active_system
cd active_system
cp deploy/.env.example deploy/.env
chmod 600 deploy/.env
${EDITOR:-vi} deploy/.env
bash upgrade.sh
```

填写管理员密码（至少 12 字符）、随机 JWT_SECRET（至少 32 字符）及抽奖安全码（至少 6 字符），
示例值不能使用。可用 `openssl rand -hex 32` 生成随机值。配置为单行 KEY=value 字面值，
不加引号，支持字母、数字及 `_ . , : / @ % + = ! ? ~ -`；不支持空格、美元符号或 Shell 表达式。
未知键和重复键会拒绝。默认管理员为 admin、HTTP_PORT=80；APP_CORS_ORIGINS 默认空，同源请求不需要 CORS。
根目录 `.env` 只用于本地开发，部署脚本不会读取它。

成功后访问 `http://服务器地址/admin/`、`/screen/`、`/user/`；活动二维码指向 `/user/activity/<id>`，
大屏活动入口为 `/screen/?activity_id=<id>`。单独用户入口显示扫码提示。仅 Nginx 发布端口，后端在内部网络。
HTTPS 由外部反向代理提供，代理需保留 Host、设置 X-Forwarded-Proto，并支持 WebSocket Upgrade。
不要将 Docker daemon 的网络接口暴露给非信任用户。

## 日常升级

```bash
bash /你的绝对路径/active_system/upgrade.sh
```

脚本更新当前分支实际配置的上游，仅允许相等或落后；本地超前、分叉、任何修改或未跟踪文件均拒绝。
它不会丢弃代码、合并冲突或提交。Git 拉取更换脚本后会持原锁重新执行新脚本。
请只部署可信仓库中的已审核提交。`start.ps1 -Docker` 会指向本 Linux 入口。

两个镜像均构建且 Nginx/Compose 校验成功后才停止旧后端。完整备份后更新两个容器，健康检查最长等待
180 秒，再检查三端入口和 API；成功才更新记录。构建失败不会停止旧服务；不会执行 compose down。
每次尝试使用提交 SHA 加时间/PID 唯一标签，保存实际镜像 ID；同 SHA 重建不覆盖可恢复版本。

数据默认位于 `deploy/runtime/data/`，SQLite 和 media 一起持久化。`deploy/runtime/releases/<尝试名>/`
包含 compose.json（**含密钥**）、commit、backend-image、nginx-image、data-dir；已有实例的升级尝试还保存
data.tar.gz、data.sha256 和 restore-release。目录只允许部署用户访问，不要公开上传发布记录。
不要在需要恢复前执行 image prune、删除旧镜像或备份；磁盘需容纳至少两套镜像和完整数据备份。
脚本不自动清理备份，保留策略由运维按恢复需求制定。

## 故障与恢复

失败退出码非零并打印阶段、诊断命令和记录位置。构建/配置故障修复后重新运行即可；首次启动部分失败时，
脚本通过 pending 前驱链确认其自身创建的容器后允许重试。连续失败即使遗留不同尝试的 backend/nginx，
只要链记录完整、无环、数据目录一致且项目/服务/对应镜像/后端挂载全部匹配，仍可重试；
未知服务、外来镜像、数据挂载不符或坏链会拒绝。请保留失败尝试目录和 pending-parent，勿手工改写记录。
成功后 pending 指向 current，无记录外来容器拒绝自动接管。
备份失败会尝试恢复旧后端并检查健康；若明确提示恢复失败，应立即检查日志。
新版本启动后发生故障不会自动覆盖数据库。若后端已换成新镜像而 current 仍为旧成功版本，后续升级会
要求先显式恢复，防止把新版本数据与旧镜像配对。可先诊断：

```bash
docker compose -p active-system -f deploy/runtime/releases/<尝试名>/compose.json ps
docker compose -p active-system -f deploy/runtime/releases/<尝试名>/compose.json logs --tail=100
```

恢复到该次升级前的成功版本（选择**包含备份的升级尝试名**，不是旧版本名）：

```bash
bash deploy/scripts/restore.sh <带有data.tar.gz的尝试名>
```

恢复程序取得同一把锁，验证备份 SHA-256、路径和文件类型，先恢复到新的 `runtime/restored-*` 空目录，
再停止当前后端，用 restore-release 指向的旧配置及旧镜像启动两个容器并检查健康和入口。
恢复前的失败数据目录完整保留；恢复后业务回到备份时刻，此后写入不会自动合并。
成功后 current 更新为恢复记录，下一次 upgrade 自动沿用恢复后的数据目录。恢复凭据/端口来自旧配置，
下次升级前核对 deploy/.env 与期望值一致。恢复失败保留新目录和记录，修复后可再次显式调用；不会删除原数据。
首次部署没有旧成功版本和备份，只能修复启动问题后重试，不提供不存在的回滚目标。

## 验证

本次提交须另附实际执行证据；语法检查、模拟故障和本机代理验证不能证明 Linux Docker 实测通过。
发布验收应在 Linux 依次验证首次部署、含活动/用户/图片的二次升级、HTTP/HTTPS 登录上传和聊天/抽奖 WS、
构建/备份/健康故障及上述恢复步骤。未完成这些场景时不得认定 T6 验收通过。
