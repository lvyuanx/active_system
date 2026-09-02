import assert from "node:assert/strict";
import fs from "node:fs";

const { createTaskScheduler } = await import("../dist-test/realtime/task-scheduler.js");

let currentTime = 0;
let nextFrameId = 0;
const frames = new Map();
const canceledFrames = [];
const requestFrame = (callback) => {
  const frameId = ++nextFrameId;
  frames.set(frameId, callback);
  return frameId;
};
const cancelFrame = (frameId) => {
  frames.delete(frameId);
  canceledFrames.push(frameId);
};
const runFrame = (timestamp) => {
  currentTime = timestamp;
  const callbacks = [...frames.values()];
  frames.clear();
  callbacks.forEach((callback) => callback(timestamp));
};

const scheduler = createTaskScheduler({
  requestFrame,
  cancelFrame,
  now: () => currentTime,
});
const order = [];
scheduler.scheduleAt(30, () => order.push("late"));
scheduler.scheduleAt(10, () => order.push("first"));
scheduler.scheduleAt(10, () => order.push("second"));
assert.equal(frames.size, 1);
runFrame(9);
assert.deepEqual(order, []);
runFrame(10);
assert.deepEqual(order, ["first", "second"]);
runFrame(30);
assert.deepEqual(order, ["first", "second", "late"]);

const cancellationScheduler = createTaskScheduler({
  requestFrame,
  cancelFrame,
  now: () => currentTime,
});
const canceledTask = cancellationScheduler.scheduleAfter(100, () => order.push("canceled"));
cancellationScheduler.cancel(canceledTask);
assert.equal(cancellationScheduler.pendingCount(), 0);
assert.equal(frames.size, 0);
assert.ok(canceledFrames.length > 0);

const budgetOrder = [];
const budgetScheduler = createTaskScheduler({
  requestFrame,
  cancelFrame,
  now: () => currentTime,
  frameBudgetMs: 4,
  maxTasksPerFrame: 10,
});
budgetScheduler.scheduleAt(0, () => {
  budgetOrder.push("first");
  currentTime = 5;
});
budgetScheduler.scheduleAt(0, () => budgetOrder.push("second"));
runFrame(0);
assert.deepEqual(budgetOrder, ["first"]);
assert.equal(budgetScheduler.pendingCount(), 1);
runFrame(16);
assert.deepEqual(budgetOrder, ["first", "second"]);

const errors = [];
const errorOrder = [];
const errorScheduler = createTaskScheduler({
  requestFrame,
  cancelFrame,
  now: () => currentTime,
  onError: (error) => errors.push(error.message),
});
errorScheduler.scheduleAt(20, () => {
  throw new Error("expected task error");
});
errorScheduler.scheduleAt(20, () => errorOrder.push("continued"));
runFrame(20);
assert.deepEqual(errors, ["expected task error"]);
assert.deepEqual(errorOrder, ["continued"]);

const asyncEvents = [];
const asyncScheduler = createTaskScheduler({
  requestFrame,
  cancelFrame,
  now: () => currentTime,
});
asyncScheduler.scheduleAt(25, () => {
  asyncEvents.push("started");
  void Promise.resolve().then(() => asyncEvents.push("completed"));
});
asyncScheduler.scheduleAt(25, () => asyncEvents.push("next"));
runFrame(25);
assert.deepEqual(asyncEvents, ["started", "next"]);
await Promise.resolve();
assert.deepEqual(asyncEvents, ["started", "next", "completed"]);

const burstScheduler = createTaskScheduler({
  requestFrame,
  cancelFrame,
  now: () => currentTime,
});
for (let index = 0; index < 200; index += 1) burstScheduler.scheduleAt(30, () => {});
assert.equal(burstScheduler.pendingCount(), 200);
assert.equal(frames.size, 1);

const overlaySource = fs.readFileSync(
  new URL("../src/components/realtime/DanmakuOverlay.vue", import.meta.url),
  "utf8",
);
const overlayStyles = fs.readFileSync(
  new URL("../src/components/realtime/DanmakuOverlay.css", import.meta.url),
  "utf8",
);
assert.doesNotMatch(overlaySource, /\bsetTimeout\b/);
assert.doesNotMatch(overlaySource, /\bsetInterval\b/);
assert.match(overlayStyles, /animation:\s*danmaku-fly/);
assert.match(overlaySource, /scheduler\.scheduleAt/);
assert.match(overlaySource, /scheduler\.scheduleAfter/);
assert.doesNotMatch(overlaySource, /scheduler\.subscribeFrame/);

console.log("task-scheduler tests passed");
