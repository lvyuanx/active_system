# TASK-v1 主 Agent 补充验证

- 通过TypeScript编译器转换真实源码并在独立VM执行，16个URL断言通过：HTTP/HTTPS默认同源API/WS，
  管理端用户/大屏入口编码，显式外部URL及原查询参数保留，本地开发5174/5175默认，
  Electron file来源下显式HTTP/HTTPS API生成ws/wss。未修改生产文件。
- `pnpm --filter @active/screen-web exec vite build --outDir ../../deploy/runtime/test-qa/electron-screen`：0。
  默认构建HTML引用 ./assets/index-*.js 和 ./assets/index-*.css，保留桌面相对资源。
  此为构建与URL兼容检查，不是完整Electron安装包/多显示器运行验证。
- 独立临时workspace只含根manifest/lock和三个Web package.json（无desktop importer目录），
  与Docker一致的 `pnpm install --frozen-lockfile --filter @active/admin-web --filter @active/screen-web
  --filter @active/user-web`：0，140依赖安装完成，锁未重新解析。宿主机Node22/pnpm11.16，非Docker构建。
- 已人工查看HTTPS用户入口及活动二维码截图，页面非空、链接子路径正确；新用户入口提示对比度可改善，
  已交开发作局部修正。测试端口18080/18081/18443在独立测试结束后均无监听。
- LinuxDocker/真实flock/自更新FD/真实容器备份恢复仍缺失；没有把这些补充检查归为Linux验收通过。
