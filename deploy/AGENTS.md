# 部署模块

`compose/docker-compose.yml` 定义固定项目名 active-system 的 backend/nginx 两服务。
后端单进程，SQLite 与媒体挂载在 `/app/data`；只有 Nginx 发布端口。
`docker/frontend.Dockerfile` 使用 pnpm 11.16.0 frozen lock 构建三个 Web，CLI base 分别为
`/admin/`、`/screen/`、`/user/`；不执行 Electron。大屏默认 Vite 相对 base 保留给桌面打包。

## 升级数据流

根 `upgrade.sh` 整体解析 main 后进入 `scripts/common.sh`：固定 flock、严格字面 env、依赖和干净树检查、
当前上游 fetch/ff-only、自更新 exec 续跑。`scripts/release.sh` 保存唯一尝试目录、构建镜像、固定镜像 ID、
校验配置，停旧后端并完整备份，再 force-recreate 两容器，检查健康与站点，成功才推进 current/previous。
首次失败用 pending 的前驱链核实受控容器，以支持连续失败后的重试；新尝试切换前保存 pending-parent，
不能丢失旧尝试镜像记录。整条链必须存在、无环且数据目录一致；容器的项目、服务、对应服务的镜像 ID、
后端 /app/data 挂载必须全部匹配。成功时 pending 指向 current；没有记录的现有部署不自动接管。
备份阶段失败或信号恢复旧后端；切换开始后不自动覆盖数据。

## 文件与恢复

`deploy/.env` 是不被 Git 追踪的严格 KEY=value，不 source/eval，不读取根 .env；白名单配置见示例。
`runtime/` 忽略 Git 和 Docker，保存 data、releases、current、previous、pending 和固定锁。
每个发布保存完整解析配置（含密钥，目录 700）、SHA、镜像 ID、绝对数据路径、配套备份及 SHA-256。
`scripts/artifacts.py` 只在已有后端镜像内处理归档和 JSON，不要求宿主机 Python。
`scripts/restore.sh <尝试名>` 明确人工调用，将切换前备份恢复到新目录，使用配套旧配置/镜像启动。
原失败数据保持不动，成功记录指向新数据目录，后续升级据此继续。

## 验证边界

脚本语法、归档测试、三端构建与本机 Nginx 检查不替代 Linux Docker 首次/二次/故障/恢复实测。
部署步骤和人工恢复流程见 README.md；workflow 目录由主 Agent 维护。
