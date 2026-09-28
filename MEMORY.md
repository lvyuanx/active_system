# 当前进度

- 2026-09-21：用户端聊天室已加入 `visualViewport` 软键盘适配：键盘弹出时隐藏底部 Tabbar，聊天输入栏按可视高度贴近键盘，
  键盘收起后恢复导航；输入框文字固定 16px 以避免 iOS 聚焦缩放。用户端类型检查和生产构建已通过，本机活动回归确认长文本无横向溢出、
  离开聊天路由后导航和视口变量恢复；真实 iPhone/Android 软键盘仍需设备验收。

- 2026-09-21：完成独立 deploy 目录重构，使用 build.py 本地打包及 docker-compose.yaml 服务器运行。
- activate-backend/activate-nginx 两容器统一使用实际名称为 open-getaway-network 的显式 bridge 网络；
  代码和配置只读挂载，数据在 runtime/data。
- 两个容器不再直接发布宿主机端口；外部网关接入 open-getaway-network 后统一转发至 activate-nginx:8080，
  生产前端保持同源 API。
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
- 2026-09-21：新增 `deploy/rsync.py`，使用 Paramiko/SFTP 上传 deploy 内容；配置和明文密码保存在被 Git 忽略的
  `.rsync.local.json`，默认排除 `.env`、runtime 和本地缓存，支持 `--dry-run`、`--force`、主机指纹校验及原子替换。
  `deploy/tests/test_rsync.py` 的 10 项本地替身测试已通过；尚未连接真实 SSH 服务器验收。
