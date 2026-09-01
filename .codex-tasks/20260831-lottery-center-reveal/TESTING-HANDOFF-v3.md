任务：移除最终中奖卡片
输入版本：TASK-v2；开发输入：DEVELOPMENT-HANDOFF-v2
状态：completed
结论：中心用户放大层保留到 revealed，最终矩形卡片 DOM/CSS 已删除；screen-web 自动化、类型检查、构建和静态阶段断言通过。
证据：

- `pnpm --filter @active/screen-web test`：退出码 0，既有消息、调度、弹幕、开奖顺序、球体数学和中心揭晓断言通过。
- `pnpm --filter @active/screen-web typecheck`：退出码 0。
- `pnpm --filter @active/screen-web build`：退出码 0，Vite 生产构建完成。
- `git diff --check`：退出码 0。
- `rg` 检查源码中不存在 `data-winner-card`、`class="globe-winner"`、`.globe-winner {` 或 `globe-winner-in`；中心层仍以 selecting/revealed 条件存在。
- 之前的 1280×720 和 390×844 隔离浏览器布局检查均无溢出、无控制台 error/warn；本次仅移除最终卡片，不改变页面尺寸逻辑。

变更文件：测试阶段未修改文件。
风险或阻塞：本次未重新截取 selecting/revealed 动画单帧；依赖源码静态断言、生产构建和既有浏览器布局证据。1920×1080 目标设备仍需发布前实测。
下一步：进入只读审核和用户场景验收。

## 用例与 AC 映射

- AC-001 PASS：中心层的 v-if 同时覆盖 selecting/revealed，scattering/scattered 不会挂载；卡片标记不存在。
- AC-002 PASS：revealed 继续复用中心头像/姓名层，静态断言确认不存在 `data-winner-card` 和 `.globe-winner`。
- AC-003 PASS：中心层保留减弱动效规则、最大宽度和移动端 letter-spacing，既有 390×844 布局证据无溢出。

## 覆盖缺口

- 未为本次改动单独捕获真实 selecting/revealed 过程截图；未改变动画计时或球体几何。
