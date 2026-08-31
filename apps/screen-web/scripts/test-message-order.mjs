import assert from "node:assert/strict";
import fs from "node:fs";

const module = await import("../dist-test/realtime/message-order.js");
const message = (messageId) => ({
  message_id: messageId,
  activity_id: "test-activity",
  body: `消息 ${messageId}`,
  created_at: "2026-08-27T00:00:00+00:00",
});
const ids = (messages) => messages.map((item) => item.message_id);

// 用最小消费者模型验证路由函数的可观察行为：连续消息不会触发恢复，缺口消息只从当前游标恢复。
const createRealtimeConsumer = (initialCursor) => {
  let cursor = initialCursor;
  let pending = [];
  const displayed = [];
  const recoveryAfterIds = [];
  let recoveryCallCount = 0;
  const receive = (nextMessage, recoveryPending = false) => {
    pending = module.removeResolvedRealtimeMessages(pending, cursor);
    const decision = module.getRealtimeMessageDecision(
      cursor,
      nextMessage.message_id,
      recoveryPending || pending.length > 0,
    );
    if (decision === "ignore") return decision;
    if (decision === "direct") {
      displayed.push(nextMessage);
      cursor = nextMessage.message_id;
      return decision;
    }
    pending = module.addPendingRealtimeMessage(pending, nextMessage);
    const drained = module.takeContiguousRealtimeMessages(cursor, pending);
    pending = drained.remaining;
    drained.messages.forEach((item) => {
      displayed.push(item);
      cursor = item.message_id;
    });
    return decision;
  };
  const recover = (fetchAfter) => {
    recoveryCallCount += 1;
    const afterId = cursor;
    recoveryAfterIds.push(afterId);
    const recovered = fetchAfter(afterId);
    module.mergeOrderedMessages(cursor, recovered).forEach((item) => {
      displayed.push(item);
      cursor = item.message_id;
    });
    const drained = module.takeContiguousRealtimeMessages(cursor, pending);
    pending = drained.remaining;
    drained.messages.forEach((item) => {
      displayed.push(item);
      cursor = item.message_id;
    });
  };
  return {
    get cursor() {
      return cursor;
    },
    get displayed() {
      return displayed;
    },
    get pending() {
      return pending;
    },
    get recoveryCallCount() {
      return recoveryCallCount;
    },
    recoveryAfterIds,
    receive,
    recover,
  };
};

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
assert.equal(module.getRealtimeMessageDecision(10, 11, false), "direct");
assert.equal(module.getRealtimeMessageDecision(10, 12, false), "recover");
assert.equal(module.getRealtimeMessageDecision(10, 10, false), "ignore");
assert.equal(module.getRealtimeMessageDecision(10, 11, true), "recover");

const continuousConsumer = createRealtimeConsumer(10);
assert.deepEqual(
  [11, 12, 13].map((messageId) => continuousConsumer.receive(message(messageId))),
  ["direct", "direct", "direct"],
);
assert.deepEqual(ids(continuousConsumer.displayed), [11, 12, 13]);
assert.equal(continuousConsumer.cursor, 13);
assert.equal(continuousConsumer.recoveryCallCount, 0);
assert.deepEqual(continuousConsumer.recoveryAfterIds, []);
assert.deepEqual(continuousConsumer.pending, []);

const recoveryConsumer = createRealtimeConsumer(10);
assert.equal(recoveryConsumer.receive(message(12)), "recover");
assert.deepEqual(ids(recoveryConsumer.pending), [12]);
recoveryConsumer.recover((afterId) => {
  assert.equal(afterId, 10);
  return [message(11)];
});
assert.deepEqual(recoveryConsumer.recoveryAfterIds, [10]);
assert.equal(recoveryConsumer.recoveryCallCount, 1);
assert.deepEqual(ids(recoveryConsumer.displayed), [11, 12]);
assert.equal(recoveryConsumer.cursor, 12);
assert.deepEqual(recoveryConsumer.pending, []);

const duplicateConsumer = createRealtimeConsumer(10);
assert.equal(duplicateConsumer.receive(message(11)), "direct");
assert.equal(duplicateConsumer.receive(message(11)), "ignore");
assert.equal(duplicateConsumer.receive(message(12)), "direct");
assert.deepEqual(ids(duplicateConsumer.displayed), [11, 12]);

const outOfOrderConsumer = createRealtimeConsumer(10);
assert.equal(outOfOrderConsumer.receive(message(12)), "recover");
assert.equal(outOfOrderConsumer.receive(message(11)), "recover");
assert.equal(outOfOrderConsumer.receive(message(13)), "direct");
assert.deepEqual(ids(outOfOrderConsumer.displayed), [11, 12, 13]);
assert.deepEqual(outOfOrderConsumer.pending, []);

const failedRecoveryConsumer = createRealtimeConsumer(10);
assert.equal(failedRecoveryConsumer.receive(message(12)), "recover");
const pendingBeforeFailure = failedRecoveryConsumer.pending;
assert.throws(
  () => failedRecoveryConsumer.recover(() => {
    throw new Error("temporary HTTP failure");
  }),
  /temporary HTTP failure/,
);
assert.deepEqual(failedRecoveryConsumer.pending, pendingBeforeFailure);
assert.deepEqual(ids(failedRecoveryConsumer.displayed), []);
assert.equal(failedRecoveryConsumer.cursor, 10);
assert.equal(failedRecoveryConsumer.recoveryCallCount, 1);

let pendingMessages = module.addPendingRealtimeMessage([], message(12));
pendingMessages = module.addPendingRealtimeMessage(pendingMessages, message(12));
pendingMessages = module.addPendingRealtimeMessage(pendingMessages, message(11));
assert.deepEqual(
  module.takeContiguousRealtimeMessages(10, pendingMessages).messages.map((item) => item.message_id),
  [11, 12],
);
assert.deepEqual(module.takeContiguousRealtimeMessages(10, pendingMessages).remaining, []);
assert.deepEqual(
  module.removeResolvedRealtimeMessages([message(11), message(12), message(13)], 12).map((item) => item.message_id),
  [13],
);

const firstReadyDisconnectCursor = 100;
const reconnectReadyLatestMessageId = 101;
const recoveryAfterId = module.getReadyRecoveryAfterId(
  firstReadyDisconnectCursor,
  reconnectReadyLatestMessageId,
);
assert.equal(recoveryAfterId, firstReadyDisconnectCursor);
assert.equal(module.getReadyRecoveryAfterId(firstReadyDisconnectCursor, 999), firstReadyDisconnectCursor);
assert.deepEqual(
  module.mergeOrderedMessages(recoveryAfterId, [message(reconnectReadyLatestMessageId)]).map((item) => item.message_id),
  [reconnectReadyLatestMessageId],
);

const boundedPendingMessages = Array.from({ length: 201 }, (_, index) => index + 1).reduce(
  (pending, messageId) => module.addPendingRealtimeMessage(pending, message(messageId)),
  [],
);
assert.equal(boundedPendingMessages.length, 200);
assert.equal(boundedPendingMessages.some((item) => item.message_id === 1), false);
assert.equal(boundedPendingMessages.some((item) => item.message_id === 201), true);
assert.deepEqual(
  module.addPendingRealtimeMessage(boundedPendingMessages, message(201)).map((item) => item.message_id),
  boundedPendingMessages.map((item) => item.message_id),
);
assert.deepEqual(
  module.removeResolvedRealtimeMessages(boundedPendingMessages, 200).map((item) => item.message_id),
  [201],
);

const isDanmakuOverlay = (search) => new URLSearchParams(search).get("danmaku-overlay") === "1";
assert.equal(isDanmakuOverlay(""), false);
assert.equal(isDanmakuOverlay("?danmaku-overlay=0"), false);
assert.equal(isDanmakuOverlay("?danmaku-overlay=false"), false);
assert.equal(isDanmakuOverlay("?danmaku-overlay=1"), true);
const appSource = fs.readFileSync(new URL("../src/App.vue", import.meta.url), "utf8");
assert.match(appSource, /new URLSearchParams\(window\.location\.search\)\.get\("danmaku-overlay"\) === "1"/);
const overlaySource = fs.readFileSync(
  new URL("../src/components/realtime/DanmakuOverlay.vue", import.meta.url),
  "utf8",
);
const directBranch = overlaySource.match(/if \(decision === "direct"\) \{[\s\S]*?\n  \}/)?.[0];
assert.ok(directBranch, "direct 路由分支应存在");
assert.match(directBranch, /queueMessage\(message\);/);
assert.doesNotMatch(directBranch, /reconcileRealtimeMessages|fetchMessagesAfter/);
assert.match(overlaySource, /pendingRealtimeMessages = addPendingRealtimeMessage\(/);
assert.match(overlaySource, /const messages = await fetchMessagesAfter\(lastMessageId\.value\);/);
assert.match(overlaySource, /pendingRealtimeMessages = removeResolvedRealtimeMessages\(/);
assert.match(overlaySource, /getReadyRecoveryAfterId\(lastMessageId\.value, session\.latest_message_id\)/);

console.log("message-order tests passed");
