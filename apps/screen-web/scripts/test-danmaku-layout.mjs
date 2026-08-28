import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const {
  DANMAKU_GAP_PX,
  findSafeTrack,
  getDanmakuBounds,
  getDanmakuEntryReadyAt,
  getDanmakuFullyEnteredAt,
  isPendingMessageExpired,
  measureDanmakuText,
  willDanmakuCollide,
} = await import("../dist-test/danmaku-layout.js");

const viewportWidth = 1000;
const shortMotion = { startedAt: 0, durationMs: 10_000, width: 100 };

assert.equal(DANMAKU_GAP_PX, 8);
assert.deepEqual(getDanmakuBounds(shortMotion, 0, viewportWidth), { left: 1000, right: 1100 });
assert.deepEqual(getDanmakuBounds(shortMotion, 10_000, viewportWidth), { left: -100, right: 0 });
assert.equal(getDanmakuFullyEnteredAt(shortMotion, viewportWidth).toFixed(2), "909.09");
assert.equal(getDanmakuEntryReadyAt(shortMotion, viewportWidth, 1000).toFixed(2), "1909.09");
assert.equal(measureDanmakuText("hello", 36, () => 120), 120);
assert.equal(measureDanmakuText("hello", 36, () => Number.NaN), 135);
assert.equal(isPendingMessageExpired(0, 1499, 1500), false);
assert.equal(isPendingMessageExpired(0, 1500, 1500), true);

const safeFollower = { startedAt: 2000, durationMs: 10_000, width: 100 };
assert.equal(willDanmakuCollide(shortMotion, safeFollower, viewportWidth), false);

const tooEarlyFollower = { startedAt: 900, durationMs: 10_000, width: 100 };
assert.equal(willDanmakuCollide(shortMotion, tooEarlyFollower, viewportWidth), true);

const longFollower = { startedAt: 2000, durationMs: 10_000, width: 1000 };
assert.equal(willDanmakuCollide(shortMotion, longFollower, viewportWidth), true);

const activeItems = [{ ...shortMotion, track: 0 }];
assert.equal(findSafeTrack(activeItems, tooEarlyFollower, 1, viewportWidth, 0, 1000, 1000), -1);
assert.equal(findSafeTrack(activeItems, safeFollower, 2, viewportWidth, 0, 2000, 1000), 0);
assert.equal(findSafeTrack(activeItems, tooEarlyFollower, 2, viewportWidth, 0, 1000, 1000), 1);
assert.equal(findSafeTrack([], safeFollower, 2, viewportWidth, 1, 2000, 1000), 1);

const overlaySource = await readFile(
  new URL("../src/components/realtime/DanmakuOverlay.vue", import.meta.url),
  "utf8",
);
assert.match(overlaySource, /findSafeTrack/);
assert.match(overlaySource, /max_wait_seconds/);
assert.match(overlaySource, /entry_interval_seconds/);
assert.match(overlaySource, /DANMAKU_QUEUE_RETRY_MS = 50/);
assert.match(overlaySource, /queuedAt/);
assert.match(overlaySource, /--danmaku-duration/);
assert.match(overlaySource, /translate3d\(-100%, 0, 0\)/);
assert.doesNotMatch(overlaySource, /-100vw - 100%/);
assert.doesNotMatch(overlaySource, /\.style\.transform/);
assert.doesNotMatch(overlaySource, /trackReleaseAt/);

console.log("danmaku layout tests passed");
