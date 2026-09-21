# 独立 Docker Compose 部署

## 开发机打包

开发机需要 Python 3.11+、Node.js 22+（满足 pnpm 11 的运行要求）、项目 package.json 指定的
pnpm 11.16.0，以及 npm 网络访问。无需本机 Docker。

在仓库根目录执行（也支持从其他工作目录用脚本绝对路径执行）：

```bash
python deploy/build.py
```

脚本锁定安装三个 Web 应用的依赖，执行类型检查，并输出
`nginx/html/admin`、`nginx/html/screen`、`nginx/html/user`。
部署构建固定使用同源 API 和三个站点子路径，不采用开发机 VITE 地址覆盖，不构建 Electron，
也不改变各应用原有 dist。后端 app 和 migrations 复制至 backend，
requirements.txt 从后端 pyproject.toml 的运行依赖生成。

全部构建成功才替换产物；重复打包删除产物中的废弃文件，不清空整个 deploy，
不覆盖 .env、Nginx 配置或 runtime。不要同时执行多个打包任务，也不要对正在挂载运行的目录执行打包。
产物被 Git 忽略：复制实际打包完成的 deploy 目录，不能用 git archive 替代打包。

## 服务器首次启动

服务器需要 Linux Docker Engine 和支持 `up --wait` 的 Docker Compose，
能够访问镜像仓库和阿里云 PyPI 镜像；无需 Git、Node.js、pnpm 或宿主机 Python。
后端镜像通过 PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/ 安装 Python 依赖。
复制整个打包后的 deploy 目录到服务器。该目录不依赖父目录或开发机绝对路径。

```bash
cd /你的路径/deploy
cp .env.example .env
chmod 600 .env
# 编辑 .env，填写管理员密码、JWT_SECRET 和 LOTTERY_SECURITY_CODE
docker compose --env-file .env config --quiet
docker compose --env-file .env up -d --build --wait
```

.env 使用 Compose 的标准语法。含美元符号等特殊字符的字面密钥可用单引号包裹；
Shell 中同名环境变量优先于 --env-file，请避免意外覆盖。必填凭据为空时 Compose 拒绝启动。
建议管理员密码至少 12 字符、随机 JWT 密钥至少 32 字符、安全码至少 6 字符。
启动时会按管理员配置初始化或更新超级用户密码。

| 配置 | 默认值 | 含义 |
| --- | --- | --- |
| FRONTEND_PORT | 8080 | 宿主机发布至 Nginx 容器 8080 |
| BACKEND_PORT | 8000 | 宿主机直接发布至后端容器 8000 |
| SUPERUSER_USERNAME | admin | 管理员账号 |
| SUPERUSER_PASSWORD | 必填 | 管理员密码 |
| JWT_SECRET | 必填 | JWT 签名密钥 |
| LOTTERY_SECURITY_CODE | 必填 | 抽奖特殊配置安全码 |
| DANMAKU_TOKEN_SECRET | 空 | 空时沿用 JWT_SECRET |
| APP_CORS_ORIGINS | 空 | 直接跨源调用 API 时允许的来源，逗号分隔 |

两个外部端口需可用且不同。默认访问：

- 管理端：http://服务器:8080/admin/
- 大屏：http://服务器:8080/screen/?activity_id=活动ID
- 用户端：http://服务器:8080/user/activity/活动ID
- API：http://服务器:8080/api/v1/health 或 http://服务器:8000/api/v1/health

前端总是经同源 /api 请求后端。两个服务、容器分别名为 activate-backend 和 activate-nginx，
处于 Compose 管理的 activate bridge 网络；Nginx 使用 activate-backend:8000 转发，
不依赖 BACKEND_PORT。修改外部端口后重新执行 up 命令即可，无需重新打包。

Nginx 不监听 80。nginx.conf 仅放全局与 http 配置，显式加载 client.conf；
client.conf 定义站点并在 server 内包含 backend.conf 的 /api location。
不要将 backend.conf 在 http 层通配加载。
HTTPS 由外部代理提供，需要保留 Host、X-Forwarded-Proto 和 WebSocket Upgrade。
后端端口按需求直接发布；正式公网访问及上传通常使用 Nginx 入口。

## 挂载与持久化

代码、迁移、静态资源及 Nginx 配置只读挂载；缺少挂载源会明确报错。
后端镜像仅安装 requirements.txt，Nginx 镜像移除默认站点，均不内置应用代码。
数据库和媒体分别存放于 runtime/data/active_system.db 和 runtime/data/media，
共同读写挂载到 /app/data。数据挂载显式设置 bind.create_host_path: true，
由 Compose 在首次启动时创建缺失的宿主机 runtime/data，无需手动 mkdir；已有目录及数据保留。

## 更新、备份和回退

本方案允许停机升级，不自动拉取 Git、创建版本记录、备份或回滚。
每次更新必须保留服务器的 .env 和完整 runtime；不要将开发机 runtime 覆盖到服务器。

1. 在开发机重新打包，传输到服务器的独立暂存目录。
2. 在服务器当前 deploy 中执行停止命令，避免复制过程中代码和数据变化。
3. 将当前代码、配置、依赖清单及完整 runtime/data 备份到 deploy 外的独立目录。
4. 用新包完整替换 backend/app、backend/migrations、backend/requirements.txt、nginx/html；
   同步 Dockerfile、Compose 和需要更新的配置。目录整体替换，避免残留已删除文件。
5. 保留服务器 .env 与 runtime，再执行启动命令。

```bash
docker compose --env-file .env stop
# 完成上述备份、替换后
docker compose --env-file .env up -d --build --force-recreate --wait
```

只替换后端文件并不会自动重载进程；必须重启或重建容器。
失败时查看日志，修复后重试。需要回退时先停止服务、另存失败数据，
再恢复配套的旧代码、配置、依赖和停机备份数据，最后重建启动；备份后的新增数据不会自动合并。
原有旧部署不自动接管或迁移；先按旧部署实际配置停服和备份，再人工确认数据位置及端口后迁移。
历史 runtime/releases 等记录保持原样，但新方案不消费这些记录。

## 日常检查与验证

```bash
docker compose --env-file .env ps
docker compose --env-file .env logs --tail=100
docker compose --env-file .env exec activate-nginx nginx -t
```

开发验证：`python -m unittest discover -s deploy/tests -p "test_*.py" -v`。
测试在独立临时目录内验证打包失败、重复打包和 Compose 可移植性，不使用真实部署凭据和数据。
run_proxy_qa.py 可使用 Windows 原生 Nginx 执行 HTTP/HTTPS 浏览器回归，
需预装对应测试依赖和证书；不能代替 Linux Docker 验收。
workflow 中保留的是旧 Git 发布方案的历史材料，不代表新方案已验收。
