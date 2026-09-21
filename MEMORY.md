# 当前进度

- 2026-09-21：完成独立 deploy 目录重构，使用 build.py 本地打包及 docker-compose.yaml 服务器运行。
- activate-backend/activate-nginx 两容器使用显式 bridge 网络；代码和配置只读挂载，数据在 runtime/data。
- .env 分别配置宿主机前后端端口，默认 8080/8000；生产前端保持同源 API。
- 后端 Dockerfile 已配置 pip 使用阿里云 PyPI 镜像。
- 服务器已完成镜像构建，但曾因缺少 runtime/data 创建容器失败；已在本地 Compose 中显式启用
  数据挂载 create_host_path: true，待将配置同步至服务器后验证首次启动。
- 已移除旧 Git 自动更新、发布及恢复脚本和专用测试；原运行数据及历史材料保留，workflow 标注为旧方案。
- 实际执行三端类型检查、生产子路径构建并生成后端产物；7 项部署测试通过，包含失败回滚、重复打包、
  排除敏感文件，以及仓库外复制后的 Compose 配置、端口和挂载解析。
- 原生 Nginx 1.28.0 配置检查和 HTTP/HTTPS 浏览器回归通过：三端入口、深层刷新、登录、二维码、上传、
  聊天与抽奖 WebSocket 均通过，无页面错误。证据：deploy/runtime/test-qa/proxy-1789996798448274000/results.json。
- Linux Docker daemon 仍无法连接；尚未验证真实镜像构建、容器首次启动、重建后的数据持久化与代码更新。
  未执行服务器发布，以上本机检查不等同于 Docker 实测验收。
