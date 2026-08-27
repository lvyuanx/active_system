<template>
  <section class="chat-content">
    <div ref="messageList" class="chat-messages">
      <VanLoading v-if="loading" class="chat-loading" size="24px" color="var(--activity-gold)" />
      <button v-else-if="hasMore" class="chat-load-more" type="button" @click="loadOlder">加载更早消息</button>
      <p v-if="!loading && messages.length === 0" class="chat-empty">还没有消息，来打个招呼吧。</p>
      <article
        v-for="message in messages"
        :key="message.message_id"
        class="chat-message"
        :class="{ 'chat-message--self': message.sender_activity_user_id === user.activity_user_id }"
      >
        <ActivityAvatar
          :avatar-id="messageAvatarId(message)"
          variant="small"
          :alt="`${message.sender_username}的活动头像`"
        />
        <div class="chat-message-content">
          <div class="chat-message-meta">
            <strong>{{ message.sender_username }}</strong>
            <time :datetime="message.created_at">{{ formatTime(message.created_at) }}</time>
          </div>
          <p class="chat-message-bubble">{{ message.body }}</p>
        </div>
      </article>
    </div>
    <form class="chat-composer" @submit.prevent="sendMessage">
      <div class="chat-composer-controls">
        <VanField
          v-model="draft"
          :disabled="activity.status !== 'open' || sending"
          maxlength="500"
          rows="1"
          :autosize="{ minHeight: 24, maxHeight: 72 }"
          type="textarea"
          placeholder="输入消息"
        />
        <VanButton native-type="submit" type="primary" :disabled="!canSend" :loading="sending">发送</VanButton>
      </div>
    </form>
  </section>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from "vue";
import { Button as VanButton, Field as VanField, Loading as VanLoading, showToast } from "vant";
import "./chat.css";
import {
  getActivityToken,
  getChatMessages,
  chatWebSocketURL,
  type Activity,
  type ActivityAvatarId,
  type ActivityUserResponse,
  type ChatMessage,
} from "../../api/client";
import ActivityAvatar from "../../components/ActivityAvatar.vue";

const props = defineProps<{ activity: Activity; user: ActivityUserResponse }>();
const messages = ref<ChatMessage[]>([]);
const loading = ref(true);
const hasMore = ref(false);
const draft = ref("");
const sending = ref(false);
const messageList = ref<HTMLElement>();
const connectionState = ref<"connecting" | "connected" | "offline">("connecting");
const socket = ref<WebSocket>();
const stopped = ref(false);
let reconnectTimer: number | undefined;
let reconnectAttempt = 0;
const ACTIVITY_AVATAR_COUNT = 20;
const FALLBACK_AVATAR_ID: ActivityAvatarId = 1;

const messageAvatarId = (message: ChatMessage): ActivityAvatarId => {
  if (message.sender_activity_user_id === props.user.activity_user_id) return props.user.avatar_id;
  const senderId = message.sender_activity_user_id;
  if (!Number.isSafeInteger(senderId) || senderId < 1) return FALLBACK_AVATAR_ID;
  return ((senderId - 1) % ACTIVITY_AVATAR_COUNT + 1) as ActivityAvatarId;
};

type ChatScrollSnapshot = { scrollable: boolean; nearBottom: boolean };

const appendMessages = (incoming: ChatMessage[]) => {
  const previousIds = new Set(messages.value.map((message) => message.message_id));
  const byId = new Map(messages.value.map((message) => [message.message_id, message]));
  incoming.forEach((message) => byId.set(message.message_id, message));
  messages.value = [...byId.values()].sort((a, b) => a.message_id - b.message_id);
  return messages.value.filter((message) => !previousIds.has(message.message_id)).length;
};
const captureScrollSnapshot = (): ChatScrollSnapshot => {
  const element = messageList.value;
  if (!element) return { scrollable: false, nearBottom: false };
  const scrollable = element.scrollHeight > element.clientHeight;
  const distanceFromBottom = element.scrollHeight - element.clientHeight - element.scrollTop;
  return {
    scrollable,
    nearBottom: scrollable && distanceFromBottom <= element.clientHeight / 3,
  };
};
const scrollToLatest = (behavior: ScrollBehavior = "smooth") => {
  const element = messageList.value;
  if (!element) return;
  element.scrollTo({ top: element.scrollHeight, behavior });
};
const revealNewMessages = async (previous: ChatScrollSnapshot) => {
  await nextTick();
  const element = messageList.value;
  if (!element) return;
  const scrollable = element.scrollHeight > element.clientHeight;
  const shouldScroll = (previous.scrollable && previous.nearBottom) || (!previous.scrollable && scrollable);
  if (shouldScroll) scrollToLatest();
};
const appendRealtimeMessages = async (incoming: ChatMessage[]) => {
  const previous = captureScrollSnapshot();
  if (appendMessages(incoming) === 0) return;
  await revealNewMessages(previous);
};
const fetchMessages = async (
  params: { before_id?: number; after_id?: number } = {},
  updateHistoryState = true,
  autoScrollNewMessages = false,
) => {
  const token = getActivityToken(props.activity.activity_id);
  if (!token) return;
  const page = await getChatMessages(props.activity.activity_id, token, params);
  const previous = autoScrollNewMessages ? captureScrollSnapshot() : undefined;
  const addedCount = appendMessages(page.items);
  if (updateHistoryState) hasMore.value = page.has_more;
  if (autoScrollNewMessages && previous && addedCount > 0) await revealNewMessages(previous);
  return page;
};
const fetchReconnectMessages = async () => {
  let cursor = messages.value.at(-1)?.message_id;
  while (!stopped.value) {
    const page = await fetchMessages(cursor ? { after_id: cursor } : {}, false, true);
    if (!page || page.items.length === 0 || !page.has_more) return;
    const latest = messages.value.at(-1)?.message_id;
    if (!latest || latest === cursor) return;
    cursor = latest;
  }
};
const loadOlder = async () => {
  const oldest = messages.value[0]?.message_id;
  if (!oldest) return;
  const list = messageList.value;
  const previousScrollHeight = list?.scrollHeight ?? 0;
  const previousScrollTop = list?.scrollTop ?? 0;
  try { await fetchMessages({ before_id: oldest }); } catch { showToast("历史消息加载失败"); }
  await nextTick();
  if (list) list.scrollTop = previousScrollTop + list.scrollHeight - previousScrollHeight;
};
const connect = () => {
  if (stopped.value) return;
  connectionState.value = "connecting";
  const token = getActivityToken(props.activity.activity_id);
  if (!token) return;
  const ws = new WebSocket(chatWebSocketURL(props.activity.activity_id));
  socket.value = ws;
  ws.onopen = () => { reconnectAttempt = 0; ws.send(JSON.stringify({ type: "auth", token })); };
  ws.onmessage = async (event) => {
    let payload: unknown;
    try { payload = JSON.parse(event.data); } catch { return; }
    if (!payload || typeof payload !== "object") return;
    const data = payload as { type?: string; message?: ChatMessage; detail?: string };
    if (data.type === "chat.ready") {
      connectionState.value = "connected";
      try { await fetchReconnectMessages(); } catch { /* 下一次重连时重试 */ }
    } else if (data.type === "message.created" && data.message) {
      await appendRealtimeMessages([data.message]);
    } else if (data.type === "chat.error" && data.detail) showToast(data.detail);
  };
  ws.onclose = () => {
    if (stopped.value) return;
    connectionState.value = "offline";
    const delay = Math.min(10000, 1000 * 2 ** reconnectAttempt++);
    reconnectTimer = window.setTimeout(connect, delay);
  };
  ws.onerror = () => ws.close();
};
const sendMessage = () => {
  const body = draft.value.trim();
  if (!body || !socket.value || socket.value.readyState !== WebSocket.OPEN || props.activity.status !== "open") return;
  sending.value = true;
  socket.value.send(JSON.stringify({ type: "message.send", body }));
  draft.value = "";
  window.setTimeout(() => { sending.value = false; }, 300);
};
const formatTime = (value: string) => new Date(value).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
const canSend = computed(() => props.activity.status === "open" && draft.value.trim().length > 0 && connectionState.value === "connected");

onMounted(async () => {
  try { await fetchMessages(); } catch { showToast("消息加载失败"); } finally { loading.value = false; }
  await nextTick();
  scrollToLatest("auto");
  connect();
});
onBeforeUnmount(() => {
  stopped.value = true;
  if (reconnectTimer) window.clearTimeout(reconnectTimer);
  socket.value?.close();
});
</script>
