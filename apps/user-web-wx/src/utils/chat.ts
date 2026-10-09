import { ActivityAvatarId, ChatMessage } from "../types/api";

export const mergeChatMessages = (current: ChatMessage[], incoming: ChatMessage[]) => {
  const byId = new Map<number, ChatMessage>(current.map((message) => [message.message_id, message]));
  incoming.forEach((message) => byId.set(message.message_id, message));
  return [...byId.values()].sort((left, right) => left.message_id - right.message_id);
};

export const messageAvatarId = (
  message: Pick<ChatMessage, "sender_activity_user_id">,
  currentUserId: number | undefined,
  currentUserAvatarId: ActivityAvatarId = 1,
): ActivityAvatarId => {
  if (message.sender_activity_user_id === currentUserId) return currentUserAvatarId;
  const senderId = message.sender_activity_user_id;
  if (!Number.isSafeInteger(senderId) || senderId < 1) return 1;
  return (((senderId - 1) % 20 + 20) % 20 + 1) as ActivityAvatarId;
};
