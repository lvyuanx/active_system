import assert from "node:assert/strict";
import fs from "node:fs";

const module = await import("../dist-test/message-order.js");
const message = (messageId) => ({
  message_id: messageId,
  activity_id: "test-activity",
  body: `消息 ${messageId}`,
  created_at: "2026-08-27T00:00:00+00:00",
});

assert.deepEqual(
  module
    .mergeOrderedMessages(0, [message(3), message(1), message(2), message(3)])
    .map((item) => item.message_id),
  [1, 2, 3],
);
assert.deepEqual(
  module.mergeOrderedMessages(2, [message(1), message(4), message(3)]).map((item) => item.message_id),
  [3, 4],
);

const firstReadyDisconnectCursor = 100;
const reconnectReadyLatestMessageId = 101;
const recoveryAfterId = module.getReadyRecoveryAfterId(
  firstReadyDisconnectCursor,
  reconnectReadyLatestMessageId,
);
assert.equal(recoveryAfterId, firstReadyDisconnectCursor);
assert.deepEqual(
  module.mergeOrderedMessages(recoveryAfterId, [message(reconnectReadyLatestMessageId)]).map((item) => item.message_id),
  [reconnectReadyLatestMessageId],
);

const signalIds = Array.from({ length: 201 }, (_, index) => index + 1).reduce(
  (pendingIds, messageId) => module.addPendingRealtimeSignal(pendingIds, messageId),
  [],
);
assert.equal(signalIds.length, 200);
assert.equal(signalIds.includes(1), false);
assert.equal(signalIds.includes(201), true);
assert.deepEqual(module.addPendingRealtimeSignal(signalIds, 201), signalIds);
assert.deepEqual(module.removeResolvedRealtimeSignals(signalIds, 200), [201]);

const isDanmakuOverlay = (search) => new URLSearchParams(search).get("danmaku-overlay") === "1";
assert.equal(isDanmakuOverlay(""), false);
assert.equal(isDanmakuOverlay("?danmaku-overlay=0"), false);
assert.equal(isDanmakuOverlay("?danmaku-overlay=false"), false);
assert.equal(isDanmakuOverlay("?danmaku-overlay=1"), true);
const appSource = fs.readFileSync(new URL("../src/App.vue", import.meta.url), "utf8");
assert.match(appSource, /new URLSearchParams\(window\.location\.search\)\.get\("danmaku-overlay"\) === "1"/);

console.log("message-order tests passed");
