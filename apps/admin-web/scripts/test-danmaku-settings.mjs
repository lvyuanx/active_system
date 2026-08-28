import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";

const viewPath = fileURLToPath(new URL("../src/views/danmaku/index.vue", import.meta.url));
const testPanelPath = fileURLToPath(new URL("../src/views/danmaku/DanmakuTestPanel.vue", import.meta.url));
const source = await readFile(viewPath, "utf8");
const testPanelSource = await readFile(testPanelPath, "utf8");
const colorPicker = source.match(/<el-color-picker\b[^>]*\/>/)?.[0];

assert.ok(colorPicker, "弹幕设置页面必须包含颜色选择器");
assert.match(colorPicker, /(?:^|\s):show-alpha="false"(?:\s|$)/);
assert.match(colorPicker, /(?:^|\s)color-format="hex"(?:\s|\/?$)/);
assert.doesNotMatch(colorPicker, /(?:^|\s)show-alpha="false"(?:\s|$)/);
assert.match(source, /getDanmaku\(activityId\)/);
assert.match(source, /applyResponse\(await updateDanmaku\(activityId, \{ \.\.\.form \}\)\)/);
assert.match(source, /ElMessage\.success\("弹幕设置已实时同步"\)/);
assert.match(source, /v-model="form\.max_wait_seconds"/);
assert.match(source, /v-model="form\.entry_interval_seconds"/);
assert.match(source, /label="入场间隔"/);
assert.match(source, /:min="0\.1"/);
assert.match(source, /:min="0\.5"/);
assert.match(source, /:max="5"/);
assert.match(source, /:step="0\.1"/);
assert.match(testPanelSource, /v-model="config\.user_count"/);
assert.match(testPanelSource, /v-model="config\.min_delay_seconds"/);
assert.match(testPanelSource, /v-model="config\.max_delay_seconds"/);
assert.match(testPanelSource, /每个测试用户会独立/);
assert.doesNotMatch(testPanelSource, /v-model="config\.user_count"[\s\S]*?:max="20"/);
assert.match(testPanelSource, /startDanmakuTest\(props\.activityId, \{ \.\.\.config \}\)/);
assert.match(testPanelSource, /最大延迟必须大于或等于最小延迟/);

console.log("danmaku settings and test config assertions passed");
