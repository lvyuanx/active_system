const baseURL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";
export const apiURL = (path: string) => `${baseURL}${path}`;

export interface DanmakuSettings {
  track_count: number;
  font_size: number;
  opacity: number;
  duration_seconds: number;
  entry_interval_seconds: number;
  max_wait_seconds: number;
  display_top: number;
  display_bottom: number;
  text_color: string;
}
export interface DanmakuMessage {
  message_id: number;
  activity_id: string;
  body: string;
  created_at: string;
}
export interface DanmakuMessagePage {
  items: DanmakuMessage[];
  has_more: boolean;
}
export interface DanmakuSession {
  activity_id: string;
  activity_name: string;
  activity_status: "closed" | "open" | "ended";
  settings: DanmakuSettings;
  latest_message_id: number;
}
export interface DanmakuOverlayBootstrap {
  apiBaseUrl: string;
  token: string;
  session: DanmakuSession;
}

const withBaseURL = (apiBaseUrl: string, path: string) => `${apiBaseUrl.replace(/\/$/, "")}${path}`;
export const danmakuWebSocketURL = (apiBaseUrl: string) =>
  withBaseURL(apiBaseUrl, "/danmaku/ws").replace(/^http:/, "ws:").replace(/^https:/, "wss:");

export async function getDanmakuMessages(
  apiBaseUrl: string,
  token: string,
  afterId: number,
): Promise<DanmakuMessagePage> {
  const response = await fetch(withBaseURL(apiBaseUrl, `/danmaku/messages?after_id=${afterId}`), {
    headers: { Authorization: `Bearer ${token}` },
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.detail ?? "弹幕消息补齐失败");
  return body as DanmakuMessagePage;
}
