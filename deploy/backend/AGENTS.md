# 后端部署运行环境

Dockerfile 基于 Python 3.11 安装 requirements.txt，以单进程 Uvicorn 监听 8000。
通过 PIP_INDEX_URL 使用阿里云 PyPI 镜像 https://mirrors.aliyun.com/pypi/simple/。
build.py 将 apps/backend/app、migrations 和 pyproject.toml 运行依赖生成到本目录。
生成文件忽略 Git，不应手工维护。Docker 构建上下文只包含依赖清单和 Dockerfile。
应用代码不进入镜像，由 Compose 只读挂载至 /app/app；迁移挂载至 /app/migrations。
数据统一写入可写的 /app/data，配置由 Compose 注入。应用源码更改后需重启容器。
