# 部署测试

test_build.py 使用临时目录和构建替身测试产物生成、依赖提取、失败保留旧产物、
重复打包去除废弃文件、发布失败回滚，以及不修改 .env、配置和运行数据。
test_compose.py 将部署配置和测试产物复制到仓库外，使用 docker compose config 验证
自定义端口、挂载路径、只读性、服务网络与缺失凭据错误，不连接 Docker daemon。
在 runtime/data 不存在时检查数据挂载显式启用 create_host_path，代码和配置挂载仍禁止自动创建。
run_proxy_qa.py 使用实际打包的 html 和后端代码、拆分后的 Nginx 配置，配合 proxy_browser.cjs
执行原生 Windows HTTP/HTTPS 登录、上传、聊天、抽奖和页面路由回归。
原生测试需要 QA_NGINX 指向 Nginx 可执行文件，并在其上级目录提供 test.crt/test.key。
QA_MANIFEST 仅显式提供时校验；每次测试输出到 runtime/test-qa/proxy-时间戳，不覆盖旧证据。
旧发布链路专用测试已移除。以上测试不能代替 Linux 容器构建、数据持久化和升级实测。
