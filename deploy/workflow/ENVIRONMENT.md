# 本次验证环境

- 输入 HEAD：70793924d129de74b26517a852a1fe6cbe412fc3，初始工作区干净。
- Windows / PowerShell；Node v22.21.1、pnpm 11.16.0、Python 3.11；Git Bash 5.2.37 可用。
- Docker CLI 29.7.2，Compose v5.4.0 可解析配置；Linux daemon pipe 不存在。
- WSL 无可用环境。尝试隐藏启动已安装 Docker Desktop 后，日志显示 sailor-ingest.sock 访问错误。
- 不为本任务修改系统虚拟化、重装 Docker 或删除 Docker 内部状态。
- 基线 `python -m pytest -q apps/backend`：71 passed，11 个现有 HTTP 状态常量弃用警告。
- 基线三个 Web build：通过；管理端存在既有 chunk 大小及第三方 PURE 注释警告。
- Linux Docker 实际构建/部署/备份恢复证据：待验证，模拟测试不能替代。
- 开发前后端 wheel 检查失败：setuptools 自动发现 app/data/migrations 多个顶层包；
  已将 pyproject.toml 显式包发现修复纳入部署工作包，待复验。
- 原生 Windows Nginx 1.28.3 和独立 Playwright/Chromium 已准备且启动检查通过，
  可补充代理/UI运行验证，不能替代 Linux Docker 门禁。
