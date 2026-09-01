任务：抽奖球体停止后的中心放大揭晓
输入版本：TASK-v1；开发输入：DEVELOPMENT-HANDOFF-v1
状态：completed
结论：主流程补充验证通过，中心揭晓组件的静态阶段约束、数学交接边界、screen-web 回归、类型检查、生产构建和响应式布局检查均通过。
证据：

- `pnpm --filter @active/screen-web test`：退出码 0，消息顺序、任务调度、弹幕布局、开奖顺序、球体数学和中心揭晓静态断言全部通过。
- `pnpm --filter @active/screen-web typecheck`：退出码 0。
- `pnpm --filter @active/screen-web build`：退出码 0，Vite 完成 54 个模块转换和生产资源输出。
- `git diff --check`：退出码 0。
- 隔离大屏 1280×720：rolling 和 revealed 流程可用，`documentElement` 滚动尺寸为 1280×720，控制台 error/warn 为空；revealed 阶段存在 1 个 `data-winner-card`，selecting 结束后不存在 `data-winner-focus`。
- 响应式 390×844：滚动尺寸等于 390×844，揭晓布局无横向溢出，控制台 error/warn 为空；验证后已恢复默认视口。

变更文件：测试角色未修改文件；主流程补充验证未修改生产代码或测试资产。
风险或阻塞：真实 selecting 阶段未能在浏览器中截取单帧，采用组件挂载条件、CSS 构建、数学边界和最终浏览器流程共同覆盖；真实 1920×1080 设备仍需发布前实测。
下一步：交由审核角色检查实现范围、动画交接和文档同步，再由验收角色按 AC-001 至 AC-003 逐项确认。

## 用例与 AC 映射

- AC-001：`LotteryWinnerReveal.vue` 仅在 selecting 挂载，revealed 卡片条件独立；scattering/scattered 不匹配中心层静态条件。
- AC-002：`LotteryGlobe.vue` 保留从打散位置到中心的 Canvas 插值；`winnerFocusHandoff` 在 0.2 前为 0、0.6 达到 1；中心层样式提供放大、光环和长用户名截断。
- AC-003：revealed 卡片使用独立组件并带从 0.42 到 1.06 的中心回弹动画；1280×720 浏览器流程确认最终卡片存在且不溢出。

## 覆盖缺口

- 未对真实 selecting 时间窗口逐帧截图，未使用测试专用假时钟或修改生产动画时长。
- 未在真实 1920×1080 目标设备上验证字体和极长用户名；代码层已限制最大宽度并启用省略号。
