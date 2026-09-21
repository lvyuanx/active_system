# 前端与接口代理

Dockerfile 基于 Nginx，移除默认站点。html 由 build.py 生成，忽略 Git，通过只读挂载提供服务。
nginx.conf 定义全局及 http 配置、WebSocket 和转发协议映射，显式加载 conf.d/client.conf。
client.conf 在 8080 提供 /admin/、/screen/、/user/，支持 SPA 回退，缺失静态文件返回 404；
在 server 内包含 backend.conf，后者把 /api/ 转发至 Docker 服务 activate-backend:8000。
不使用 conf.d/*.conf 通配包含，避免 location 被加载到 http 层。默认无 80 监听。
上传限制 6 MiB，WebSocket 转发保留，HTTPS 由外部代理终止。
