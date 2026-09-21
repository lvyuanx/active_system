# 部署模块

## 职责与入口

build.py 在开发机用 Python 3.11+ 和项目指定 pnpm 安装锁定依赖、检查并构建三个 Web，
把后端代码和运行依赖清单打包到 deploy。服务器只需该目录和 Docker Compose。
docker-compose.yaml 定义 activate-backend、activate-nginx 两服务及同名容器，项目名 active-system。

## 构建与运行数据流

三端 base 为 /admin/、/screen/、/user/；API 固定同源 /api/v1，不构建 Electron。
build.py 在 deploy 内临时目录准备所有产物，成功后更名发布；失败恢复旧产物，
若恢复本身失败则保留暂存备份。只允许替换 OUTPUTS 中的四个产物，不修改配置、.env、runtime。
不要并发打包，也不要在运行中挂载的部署目录内打包。

backend 镜像只安装生成的 requirements.txt。app、migrations、nginx/html 与 Nginx 配置只读挂载；
SQLite 和媒体统一持久化到 runtime/data，并在后端单进程下使用。
数据挂载显式设置 bind.create_host_path: true，由 Compose 创建缺失的宿主机目录；
代码和配置挂载保持 false，避免把缺失产物误建为空目录。
两个服务加入显式 activate bridge 网络，Nginx 通过 activate-backend:8000 访问后端。

## 配置

deploy/.env 是 Compose 标准配置文件；FRONTEND_PORT 默认 8080、BACKEND_PORT 默认 8000，
控制两个容器各自的宿主机映射；容器内部端口固定，nginx.conf 无 80 监听。
必填凭据不设可用默认值。client.conf 在 server 内包含 backend.conf，不能在 http 层通配包含。
两服务健康检查和依赖确保后端健康后启动 Nginx；生产同源 API 保持不变。

## 升级与验证边界

旧 Git 发布、版本指针、备份恢复脚本已移除；旧 runtime 和 workflow 仅保留历史数据与证据。
升级先停服、备份，再替换产物和重建；保留服务器 .env 与 runtime，不自动迁移旧实例。
测试见 tests/AGENTS.md，使用说明见 README.md。静态检查不能替代 Linux Docker 实测。
