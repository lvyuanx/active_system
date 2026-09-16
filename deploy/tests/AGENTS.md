# 部署测试

test_settings.sh 在忽略的 runtime/test-dev 下构造配置，验证字面解析、继承覆盖、重复/未知键、端口、
缺密钥、示例值和注入拒绝；不读取真实配置。test_artifacts.py 验证备份校验和、拒绝覆盖、路径和链接拒绝。
test_release_flow.sh 使用 Docker/Compose 替身验证阶段顺序、失败指针、备份失败恢复旧后端及发布所有权；
包括首次 B 失败、C 失败遗留 B 或 B/C 混合后再次重试，拒绝外来项目/服务/镜像/数据和缺失/循环/异数据链。
test_git_flow.sh 使用授权临时 Git 仓库验证相等、落后、超前、分叉、无上游、fetch 失败和脏树；
它以替身截获 exec，不证明 Linux 文件描述符的锁继承。
run_proxy_qa.py 启动临时后端和 Windows 原生 Nginx，调用 proxy_browser.cjs 使用 Playwright 对
HTTP/HTTPS 登录、活动、上传、聊天、抽奖和页面路由执行真实业务回归，证据保存在 runtime/test-qa。
上述本机基础/替身/代理检查不能代替 Linux Compose 部署及恢复验收。
