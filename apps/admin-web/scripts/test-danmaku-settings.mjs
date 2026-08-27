import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";

const viewPath = fileURLToPath(new URL("../src/views/danmaku/index.vue", import.meta.url));
const source = await readFile(viewPath, "utf8");
const colorPicker = source.match(/<el-color-picker\b[^>]*\/>/)?.[0];

assert.ok(colorPicker, "弹幕设置页面必须包含颜色选择器");
assert.match(colorPicker, /(?:^|\s):show-alpha="false"(?:\s|$)/);
assert.match(colorPicker, /(?:^|\s)color-format="hex"(?:\s|\/?$)/);
assert.doesNotMatch(colorPicker, /(?:^|\s)show-alpha="false"(?:\s|$)/);
assert.match(source, /getDanmaku\(activityId\)/);
assert.match(source, /applyResponse\(await updateDanmaku\(activityId, \{ \.\.\.form \}\)\)/);
assert.match(source, /ElMessage\.success\("弹幕设置已实时同步"\)/);

console.log("danmaku settings load/save/color format assertions passed");
