任务：验证高人数抽奖球体性能与可读性优化
输入版本：TASK-v1；开发输入：DEVELOPMENT-HANDOFF-v1
状态：completed
结论：screen-web 测试、类型检查、生产构建、compileall、diff check 和 300 人浏览器场景均通过。
证据：`pnpm --filter @active/screen-web test` 退出码 0，既有 4 组测试和 `lottery globe tests passed` 均通过；`pnpm --filter @active/screen-web typecheck`、`pnpm --filter @active/screen-web build` 退出码 0；`pnpm -r typecheck` 和 `pnpm -r build` 退出码 0；`python -m compileall -q apps/backend/app apps/backend/tests` 与 `git diff --check` 退出码 0；隔离页面测得 300 位参与者、rolling/revealed 阶段 document/body 无溢出，中奖者停止后正常居中。
变更文件：补充 `apps/screen-web/scripts/test-lottery-globe.mjs` 的渲染档位断言；测试阶段未修改后端生产逻辑。
风险或阻塞：构建保留既有 `@vueuse/core` PURE 注释和管理端大包体积提示；当前 1280×720 内置浏览器实际验证通过，其他真实硬件刷新率未测量。
下一步：交由审核检查范围、性能策略、可读性和停止动画兼容性。
