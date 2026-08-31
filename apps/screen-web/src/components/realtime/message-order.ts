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

export const MAX_PENDING_REALTIME_MESSAGES = 200;

export type RealtimeMessageDecision = "direct" | "recover" | "ignore";

export function getRealtimeMessageDecision(
  lastMessageId: number,
  messageId: number,
  hasRecoveryPending: boolean,
): RealtimeMessageDecision {
  if (messageId <= lastMessageId) return "ignore";
  if (!hasRecoveryPending && messageId === lastMessageId + 1) return "direct";
  return "recover";
}

export function addPendingRealtimeMessage<T extends { message_id: number }>(
  pendingMessages: readonly T[],
  message: T,
): T[] {
  if (pendingMessages.some((pending) => pending.message_id === message.message_id)) {
    return [...pendingMessages];
  }
  const nextMessages = [...pendingMessages, message];
  return nextMessages.length > MAX_PENDING_REALTIME_MESSAGES
    ? nextMessages.slice(-MAX_PENDING_REALTIME_MESSAGES)
    : nextMessages;
}

export function removeResolvedRealtimeMessages<T extends { message_id: number }>(
  pendingMessages: readonly T[],
  lastMessageId: number,
): T[] {
  return pendingMessages.filter((message) => message.message_id > lastMessageId);
}

export function takeContiguousRealtimeMessages<T extends { message_id: number }>(
  lastMessageId: number,
  pendingMessages: readonly T[],
): { messages: T[]; remaining: T[] } {
  const byId = new Map<number, T>();
  for (const message of pendingMessages) {
    if (message.message_id > lastMessageId) byId.set(message.message_id, message);
  }

  const messages: T[] = [];
  let cursor = lastMessageId;
  while (byId.has(cursor + 1)) {
    const message = byId.get(cursor + 1);
    if (!message) break;
    messages.push(message);
    byId.delete(cursor + 1);
    cursor += 1;
  }
  return {
    messages,
    remaining: [...byId.values()].sort((first, second) => first.message_id - second.message_id),
  };
}

// ready 中的最大 ID 只能提示可能存在缺口，不能作为客户端游标。
export function getReadyRecoveryAfterId(lastMessageId: number, _readyLatestMessageId: number): number {
  return lastMessageId;
}
