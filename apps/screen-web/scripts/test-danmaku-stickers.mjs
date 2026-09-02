import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const {
  DANMAKU_STICKER_HEIGHT_MULTIPLIER,
  measureDanmakuImageWidth,
} = await import("../dist-test/realtime/danmaku-layout.js");
const [overlay, styles] = await Promise.all([
  readFile(new URL("../src/components/realtime/DanmakuOverlay.vue", import.meta.url), "utf8"),
  readFile(new URL("../src/components/realtime/DanmakuOverlay.css", import.meta.url), "utf8"),
]);

assert.equal(DANMAKU_STICKER_HEIGHT_MULTIPLIER, 2.2);
assert.equal(measureDanmakuImageWidth(256, 256, 36).toFixed(1), "79.2");
assert.equal(measureDanmakuImageWidth(512, 128, 36).toFixed(1), "316.8");
assert.equal(measureDanmakuImageWidth(128, 512, 36).toFixed(1), "19.8");
assert.equal(measureDanmakuImageWidth(1, 1, 96).toFixed(1), "211.2");
assert.equal(measureDanmakuImageWidth(0, 0, 36).toFixed(1), "475.2");
assert.match(overlay, /message\.message_type === "sticker" && message\.sticker/);
assert.match(overlay, /class="danmaku-sticker"/);
assert.match(overlay, /@error="markImageFailed\(item\.key\)"/);
assert.match(overlay, /--danmaku-width/);
assert.match(overlay, /DANMAKU_STICKER_HEIGHT_MULTIPLIER/);
assert.match(overlay, /--danmaku-sticker-height/);
assert.match(overlay, /Math\.max\(imageWidth, fallbackWidth\)/);
assert.match(overlay, /new URL\(imageURL, apiBaseUrl\)/);
assert.match(styles, /height: var\(--danmaku-sticker-height\)/);
assert.match(styles, /margin-top: calc\(var\(--danmaku-sticker-height\) \/ -2\)/);
assert.match(styles, /width: 100%/);

console.log("danmaku sticker tests passed");
