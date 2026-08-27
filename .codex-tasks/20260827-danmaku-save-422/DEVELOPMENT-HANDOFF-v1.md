任务：TASK-v3 管理端弹幕播放设置保存 422 修复（开发阶段）
输入版本：TASK-v3；WorkPackage main-shared-422；输入 HEAD 52a164fa63a012f16234de966de137edda5970a6
状态：completed
结论：已完成最小前端修复：弹幕颜色选择器使用 Vue 布尔绑定 `:show-alpha="false"` 并固定
`color-format="hex"`，不透明颜色继续通过既有 `updateDanmaku` 提交六位十六进制值；增加无新依赖的管理端
静态回归脚本并同步模块与项目知识文档。AC-022 的加载、保存、成功反馈代码路径和 AC-023 的颜色格式约束均有
静态证据；方案偏差为无，未修改后端校验、PUT 接口、桌面端或真实测试。残余风险是本开发包未执行真实浏览器
请求/响应和后续 GET 的 API 集成验证，需由下游测试与验收阶段完成。
证据：
- WorkPackage 预写入核对：`WORKPACKAGE-v1.json` 中绝对路径为 `D:\projects\active_system`，HEAD、分支、输入树
  和 8 项输入文件 SHA-256 均匹配；共享主树明确 `detached_head=false`、`qualification=INELIGIBLE`、
  `qualification_reason=DIRTY_INPUT_UNSAFE`，按串行降级执行。
- `apps/admin-web/src/views/danmaku/index.vue:105` 使用 `:show-alpha="false" color-format="hex"`；
  保存仍在 `:223` 调用 `updateDanmaku(activityId, { ...form })`，成功反馈在 `:224`。
- `apps/admin-web/scripts/test-danmaku-settings.mjs:8-17` 检查颜色选择器布尔绑定、`hex` 格式、加载请求、保存
  回填和成功提示；`pnpm test:danmaku-settings` 退出码 0，输出 `danmaku settings load/save/color format assertions passed`。
- `pnpm typecheck`（工作目录 `apps/admin-web`）退出码 0。
- `pnpm build`（工作目录 `apps/admin-web`）退出码 0，Vite 转换 1673 个模块并生成生产产物；仅有依赖注释及
  chunk 大小提示，不影响退出状态。
- 目标路径 `git diff --check` 退出码 0，最终写入集合未发现尾随空白或超过 120 字符的代码行。
变更文件：
- `apps/admin-web/src/views/danmaku/index.vue`
- `apps/admin-web/src/views/danmaku/AGENTS.md`
- `apps/admin-web/scripts/test-danmaku-settings.mjs`
- `apps/admin-web/package.json`
- `MEMORY.md`
- `LEARNING.md`
- `WIKI.md`
- `.codex-tasks/20260827-danmaku-save-422/DEVELOPMENT-HANDOFF-v1.md`
风险或阻塞：无实现阻塞；共享工作树因既有用户改动不满足隔离 worktree 资格，未创建 detached worktree、未宣称并发验证。真实后端 HTTP 200、请求体、响应体、后续 GET、大屏同步和非法值 422 仍由下游集成测试确认。
下一步：将本交接交给 integration-test、review 和 acceptance；在主 Agent 复核范围、哈希和组合门禁前不提交、不推送、不发布。

## 实现摘要

- 将静态字符串属性 `show-alpha="false"` 改为真正的 Vue 布尔绑定 `:show-alpha="false"`。
- 为 Element Plus `el-color-picker` 增加 `color-format="hex"`，使颜色选择后的 v-model 保持不透明六位十六进制，既有回包回填和保存反馈逻辑保持不变。
- 新增 `apps/admin-web/scripts/test-danmaku-settings.mjs`，通过 Node 内置 `assert` 对加载、保存、成功反馈和颜色选择器配置做受控静态回归；在 `package.json` 增加 `test:danmaku-settings` 入口，未引入依赖。
- 在弹幕页面模块说明、`MEMORY.md`、`LEARNING.md` 和 `WIKI.md` 记录颜色格式约束及已验证结论。

## 关键技术决策

- 采用批准方案中的模板级修复：Boolean 类型属性使用 `:show-alpha="false"`，格式使用 Element Plus 支持的
  `color-format="hex"`；不在客户端放宽或重写后端校验。
- 保留 `updateDanmaku(activityId, { ...form })` 和 `applyResponse`，因此七个播放设置字段、活动 ID、成功回包
  回填及后端实时同步链路均未改变。
- 回归资产只使用 Node 内置模块，避免引入未使用依赖或建立新的测试框架。

## 工作包和路径范围

- WorkPackage：`main-shared-422`；workflow：`activity-danmaku-save-422`；目标工作树：`D:\projects\active_system`。
- 输入快照：HEAD `52a164fa63a012f16234de966de137edda5970a6`，分支 `refs/heads/master`，`input_tree_oid`
  `400f5afbb30ec7c92951e9e223da07cf59112f1a`；`detached_head=false` 是共享主树约束，不是遗漏。
- `read_scope` 包含根/项目/管理端/弹幕模块说明、页面、API、后端弹幕校验、后端测试和 TASK-v3/产品交接；
  `write_scope` 仅包含本交接列出的页面、弹幕模块说明、回归脚本、脚本入口、项目知识文档和开发交接。
- `ephemeral_scope`：`apps/admin-web/dist`、`node_modules/.cache`、`apps/admin-web/node_modules/.cache`；构建
  产物未作为源文件变更纳入交接。
- 资源声明：`repository-main-worktree`、`pnpm-node-build-cache`、`apps-admin-web-dist`；未创建子 Agent 或 Git 元数据。

## 包级门禁

- 输入/HEAD 门禁：通过。写入前已核对 WorkPackage 文件清单 8 项 SHA-256、绝对路径、HEAD、分支和树对象。
- 资格门禁：按包记录为 `INELIGIBLE / DIRTY_INPUT_UNSAFE`，因为主树含既有用户改动；已按声明的共享主树串行路径
  执行，未把串行过程描述为隔离并发验证。
- 范围门禁：通过。本次实际写入集合均属于 `write_scope`，既有管理端 API、后端、桌面端和其它用户改动未修改。
- 文档门禁：通过。`apps/admin-web/src/views/danmaku/AGENTS.md` 及三个项目知识文件已同步。
- 基础验证门禁：通过。静态回归、typecheck、build 和目标路径空白检查均退出码 0。
- 输出补丁：共享主树串行包未生成独立可应用补丁；WorkPackage 预留的 `DEVELOPMENT-v1.patch` 由主 Agent 按集成
  流程决定是否从最终限定差异导出，不将当前工作树差异冒充隔离补丁。

## 验收标准映射

- AC-022：开发证据覆盖页面已通过 `getDanmaku` 加载、`updateDanmaku` 保存七字段、`applyResponse` 回填和
  `ElMessage.success("弹幕设置已实时同步")`；静态回归及 build 通过。HTTP 200 和无 422 需下游真实 API 验证。
- AC-023：开发证据覆盖 `:show-alpha="false"` 与 `color-format="hex"`；Element Plus 依赖版本为当前安装的
  2.14.4，静态回归通过。请求体六位格式、成功回包/后续 GET 大写值需下游浏览器/API 验证；后端严格校验未变。
- AC-001～AC-021：本包未改变其既有实现或接口，仅保持兼容；其完整回归不在本开发包的验证范围内。

## 已执行验证

| 命令 | 工作目录 | 结果 |
| --- | --- | --- |
| `pnpm test:danmaku-settings` | `apps/admin-web` | 退出码 0；加载/保存/颜色格式静态断言通过 |
| `pnpm typecheck` | `apps/admin-web` | 退出码 0；`vue-tsc --noEmit` 通过 |
| `pnpm build` | `apps/admin-web` | 退出码 0；Vite 生产构建通过 |
| `git diff --check -- <目标跟踪文件>` | 仓库根目录 | 退出码 0；无目标路径空白错误 |

## 补丁与 SHA-256 证据

当前共享树相对 HEAD 的限定差异摘要为：6 个已跟踪文件，29 行新增、6 行删除；另有 1 个新增回归脚本和本交接文件。
由于输入本身是脏工作树，摘要包含输入阶段已有的同范围文档/页面改动，不能将其全部归因于本修复。
按 `git diff --binary --full-index -- <6 个已跟踪写入路径>` 在内存计算的当前限定差异 SHA-256 为
`4BBAA5A05195DCFEE9BF11E3BEA8C63F01519909EA247FA97EF9C7240B182DA4`（8676 bytes）；该摘要同样包含脏输入中
已有的同范围差异，供主 Agent 复核，不是可独立应用的隔离补丁。

本次交接完成时文件 SHA-256：

- `apps/admin-web/src/views/danmaku/index.vue`：`6E24B3BA0F2A219A0F732199270D3DB385C4DB45F5B59C53E10503059DDB5437`
- `apps/admin-web/src/views/danmaku/AGENTS.md`：`9FE9E747077FFB4944CDD9C7E3EB7DF1F04D9242BE8096C8E3156BB8B842E3E5`
- `apps/admin-web/scripts/test-danmaku-settings.mjs`：`4A02B1419F91DD5C48542782B5BF5528CC556D700BE4B9E7BAD63410A3EDF1CE`
- `apps/admin-web/package.json`：`92BC08D2DA1AE6B38228AE5120F7EFF0A6E55FA1354611C67200594C6C3DD9F1`
- `MEMORY.md`：`0310364C4E25D54610AD5D58D8A72C3D95CEC0F0022ED5F3AEE733840BF73418`
- `LEARNING.md`：`474FBF97EE2CC55A7FF1B3D7B4422376D6DD995005D5147E584670A0B0D7F678`
- `WIKI.md`：`1CE31C59D32A9C657E4D668F5AC230AF69DDBB4E8F13AA4595ECA3180892BE0A`

## 与方案的偏差

无。实现采用任务交接建议的正确 Vue 布尔绑定和明确 `hex` 格式；未增加客户端绕过校验的转换逻辑，也未修改
后端服务、API client 接口、桌面工具、screen-web 或聊天室协议。

## 残余风险

- 当前阶段未在真实浏览器中操作 Element Plus 颜色面板，未捕获目标活动的实际 PUT 请求体、HTTP 200 响应和
  后续 GET；下游测试需确认浏览器缓存和构建产物加载了本变更。
- 生产构建保留既有 Rollup `/* #__PURE__ */` 注释提示和大于 500 kB chunk 警告，命令退出码为 0，与本修复无关。
