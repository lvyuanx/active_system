<template>
  <section class="chat-content">
    <header class="chat-header">
      <div><p class="section-kicker">活动聊天室</p><h1 class="chat-title">{{ activity.name }}</h1></div>
      <VanTag round :type="activity.status === 'open' ? 'success' : 'primary'">{{ activity.status === 'open' ? '可发言' : '仅查看' }}</VanTag>
    </header>
    <div ref="messageList" class="chat-messages" @scroll="handleScroll">
      <VanLoading v-if="loading" class="chat-loading" size="24px" color="var(--activity-gold)" />
      <button v-else-if="hasMore" class="chat-load-more" type="button" @click="loadOlder">加载更早消息</button>
      <p v-if="!loading && messages.length === 0" class="chat-empty">还没有消息，来打个招呼吧。</p>
      <article v-for="message in messages" :key="message.message_id" class="chat-message" :class="{ 'chat-message--self': message.sender_activity_user_id === user.activity_user_id }">
        <div class="chat-message-meta"><strong>{{ message.sender_activity_user_id === user.activity_user_id ? '我' : message.sender_username }}</strong><time>{{ formatTime(message.created_at) }}</time></div>
        <p>{{ message.body }}</p>
      </article>
    </div>
    <p class="chat-connection" :class="`chat-connection--${connectionState}`">{{ connectionLabel }}</p>
    <form class="chat-composer" @submit.prevent="sendMessage">
      <VanField v-model="draft" :disabled="activity.status !== 'open' || sending" maxlength="500" show-word-limit rows="1" autosize type="textarea" placeholder="输入消息" />
      <VanButton native-type="submit" type="primary" :disabled="!canSend" :loading="sending">发送</VanButton>
    </form>
  </section>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from "vue";
import { Button as VanButton, Field as VanField, Loading as VanLoading, Tag as VanTag, showToast } from "vant";
import { getActivityToken, getChatMessages, chatWebSocketURL, type Activity, type ActivityUserResponse, type ChatMessage } from "../../api/client";

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

const appendMessages = (incoming: ChatMessage[]) => {
  const byId = new Map(messages.value.map((message) => [message.message_id, message]));
  incoming.forEach((message) => byId.set(message.message_id, message));
  messages.value = [...byId.values()].sort((a, b) => a.message_id - b.message_id);
};
const fetchMessages = async (
  params: { before_id?: number; after_id?: number } = {},
  updateHistoryState = true,
) => {
  const token = getActivityToken(props.activity.activity_id);
  if (!token) return;
  const page = await getChatMessages(props.activity.activity_id, token, params);
  appendMessages(page.items);
  if (updateHistoryState) hasMore.value = page.has_more;
  return page;
};
const fetchReconnectMessages = async () => {
  let cursor = messages.value.at(-1)?.message_id;
  while (!stopped.value) {
    const page = await fetchMessages(cursor ? { after_id: cursor } : {}, false);
    if (!page || page.items.length === 0 || !page.has_more) return;
    const latest = messages.value.at(-1)?.message_id;
    if (!latest || latest === cursor) return;
    cursor = latest;
  }
};
const loadOlder = async () => {
  const oldest = messages.value[0]?.message_id;
  if (!oldest) return;
  try { await fetchMessages({ before_id: oldest }); } catch { showToast("历史消息加载失败"); }
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
      appendMessages([data.message]);
      await nextTick();
      messageList.value?.scrollTo({ top: messageList.value.scrollHeight, behavior: "smooth" });
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
const handleScroll = () => { /* 保留滚动容器供后续触底加载扩展 */ };
const formatTime = (value: string) => new Date(value).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
const canSend = computed(() => props.activity.status === "open" && draft.value.trim().length > 0 && connectionState.value === "connected");
const connectionLabel = computed(() => ({ connecting: "正在连接聊天室…", connected: "已连接", offline: "连接中断，正在重连…" })[connectionState.value]);

onMounted(async () => {
  try { await fetchMessages(); } catch { showToast("消息加载失败"); } finally { loading.value = false; }
  connect();
});
onBeforeUnmount(() => {
  stopped.value = true;
  if (reconnectTimer) window.clearTimeout(reconnectTimer);
  socket.value?.close();
});
</script>
