import { onBeforeUnmount, onMounted, ref } from "vue";
import { lotteryWebSocketURL } from "../../api/client";

type LotteryMessageHandler = (event: MessageEvent<string>) => void;

export function useLotterySocket(activityId: string, onMessage: LotteryMessageHandler) {
  const connected = ref(false);
  let socket: WebSocket | undefined;
  let reconnectTimer: number | undefined;
  let retryCount = 0;
  let stopped = false;

  const scheduleReconnect = () => {
    if (stopped || reconnectTimer !== undefined) return;
    retryCount += 1;
    const delay = Math.min(8000, 500 * 2 ** Math.min(retryCount - 1, 4));
    reconnectTimer = window.setTimeout(() => {
      reconnectTimer = undefined;
      connect();
    }, delay);
  };

  const connect = () => {
    if (stopped) return;
    const current = new WebSocket(lotteryWebSocketURL(activityId));
    socket = current;
    current.onopen = () => {
      retryCount = 0;
      current.send(JSON.stringify({
        type: "auth",
        token: localStorage.getItem("active_admin_token") || "",
      }));
    };
    current.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data) as { type?: string };
        if (payload.type === "lottery.ready") connected.value = true;
      } catch {
        // 具体协议错误交给页面处理；连接状态只由 ready 帧确认。
      }
      onMessage(event);
    };
    current.onerror = () => current.close();
    current.onclose = () => {
      if (socket !== current) return;
      connected.value = false;
      scheduleReconnect();
    };
  };

  const send = (payload: Record<string, unknown>): boolean => {
    if (!socket || socket.readyState !== WebSocket.OPEN) return false;
    socket.send(JSON.stringify(payload));
    return true;
  };

  onMounted(connect);
  onBeforeUnmount(() => {
    stopped = true;
    if (reconnectTimer !== undefined) window.clearTimeout(reconnectTimer);
    socket?.close();
  });

  return { connected, send };
}
