export function mergeOrderedMessages<T extends { message_id: number }>(
  lastMessageId: number,
  messages: Iterable<T>,
): T[] {
  const byId = new Map<number, T>();
  for (const message of messages) {
    if (message.message_id > lastMessageId) byId.set(message.message_id, message);
  }
  return [...byId.values()].sort((first, second) => first.message_id - second.message_id);
}

export const MAX_PENDING_REALTIME_SIGNALS = 200;

export function addPendingRealtimeSignal(
  pendingIds: readonly number[],
  messageId: number,
): number[] {
  if (pendingIds.includes(messageId)) return [...pendingIds];
  const nextIds = [...pendingIds, messageId];
  return nextIds.length > MAX_PENDING_REALTIME_SIGNALS
    ? nextIds.slice(-MAX_PENDING_REALTIME_SIGNALS)
    : nextIds;
}

export function removeResolvedRealtimeSignals(
  pendingIds: readonly number[],
  lastMessageId: number,
): number[] {
  return pendingIds.filter((messageId) => messageId > lastMessageId);
}

// ready 中的最大 ID 只能提示可能存在缺口，不能作为客户端游标。
export function getReadyRecoveryAfterId(lastMessageId: number, _readyLatestMessageId: number): number {
  return lastMessageId;
}
