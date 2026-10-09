type SocketMessage = string | ArrayBuffer;

interface SocketTaskLike {
  send(options: { data: string; success?: () => void; fail?: (error: { errMsg: string }) => void }): void;
  close(options?: {
    code?: number;
    reason?: string;
    success?: () => void;
    fail?: (error: { errMsg: string }) => void;
  }): void;
  onOpen(callback: () => void): void;
  onMessage(callback: (event: { data: SocketMessage }) => void): void;
  onClose(callback: () => void): void;
  onError(callback: (error: { errMsg: string }) => void): void;
}

interface ReconnectingSocketOptions {
  onOpen?: () => void;
  onMessage?: (payload: Record<string, unknown>) => void;
  onClose?: () => void;
  onError?: (message: string) => void;
  minDelay?: number;
  maxDelay?: number;
}

const textFromMessage = (data: SocketMessage) => {
  if (typeof data === "string") return data;
  try {
    return String.fromCharCode(...new Uint8Array(data));
  } catch {
    return "";
  }
};

export class ReconnectingSocket {
  private task?: SocketTaskLike;
  private reconnectTimer?: number;
  private stopped = true;
  private reconnectAttempt = 0;
  private opened = false;

  constructor(
    private readonly url: string,
    private readonly options: ReconnectingSocketOptions = {},
  ) {}

  start() {
    this.stopped = false;
    this.reconnectAttempt = 0;
    this.connect();
  }

  stop() {
    this.stopped = true;
    if (this.reconnectTimer !== undefined) clearTimeout(this.reconnectTimer);
    this.reconnectTimer = undefined;
    const task = this.task;
    this.task = undefined;
    const opened = this.opened;
    this.opened = false;
    if (task && opened) this.closeTask(task, "页面离开");
  }

  send(payload: Record<string, unknown>) {
    if (!this.task) return false;
    try {
      this.task.send({
        data: JSON.stringify(payload),
        fail: (error) => this.handleError(error.errMsg || "WebSocket 消息发送失败"),
      });
      return true;
    } catch {
      return false;
    }
  }

  private connect() {
    if (this.stopped) return;
    console.info("[微信小程序 WebSocket] 开始连接", { url: this.url });
    let current: SocketTaskLike;
    try {
      current = wx.connectSocket({ url: this.url }) as unknown as SocketTaskLike;
    } catch (error) {
      this.handleError(error instanceof Error ? error.message : "WebSocket 连接失败");
      this.scheduleReconnect();
      return;
    }
    this.task = current;
    this.opened = false;
    current.onOpen(() => {
      if (this.task !== current || this.stopped) {
        this.closeTask(current, "页面离开");
        return;
      }
      this.opened = true;
      this.reconnectAttempt = 0;
      console.info("[微信小程序 WebSocket] 连接已建立", { url: this.url });
      this.options.onOpen?.();
    });
    current.onMessage((event) => {
      if (this.task !== current || this.stopped) return;
      try {
        const payload = JSON.parse(textFromMessage(event.data)) as Record<string, unknown>;
        this.options.onMessage?.(payload);
      } catch {
        this.handleError("实时消息格式无效");
      }
    });
    current.onError((error) => {
      if (this.task !== current) return;
      const message = error.errMsg || "WebSocket 连接失败";
      console.error("[微信小程序 WebSocket] 连接错误", { url: this.url, message });
      this.handleError(message);
    });
    current.onClose(() => {
      if (this.task !== current) return;
      this.task = undefined;
      this.opened = false;
      this.options.onClose?.();
      this.scheduleReconnect();
    });
  }

  private handleError(message: string) {
    this.options.onError?.(message);
  }

  private closeTask(task: SocketTaskLike, reason: string) {
    try {
      task.close({
        code: 1000,
        reason,
        // 连接尚未分配 task ID 时，微信会通过 fail 返回 taskID not exist。
        fail: () => undefined,
      });
    } catch {
      // 关闭已经失效的连接是幂等清理，不影响页面继续运行。
    }
  }

  private scheduleReconnect() {
    if (this.stopped || this.reconnectTimer !== undefined) return;
    this.reconnectAttempt += 1;
    const minDelay = this.options.minDelay ?? 500;
    const maxDelay = this.options.maxDelay ?? 10000;
    const delay = Math.min(maxDelay, minDelay * 2 ** Math.min(this.reconnectAttempt - 1, 4));
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = undefined;
      this.connect();
    }, delay) as unknown as number;
  }
}
