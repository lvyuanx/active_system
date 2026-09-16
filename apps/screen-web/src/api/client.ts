export const baseURL = (import.meta.env.VITE_API_BASE_URL
  ?? (import.meta.env.PROD ? "/api/v1" : "http://localhost:8000/api/v1")).replace(/\/$/, "");
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
  message_type: "text" | "sticker";
  sticker: DanmakuSticker | null;
}
export interface DanmakuSticker {
  sticker_id: number;
  name: string;
  image_url: string;
  mime: string;
  width: number;
  height: number;
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
  new URL(withBaseURL(apiBaseUrl, "/danmaku/ws"), window.location.href).toString()
    .replace(/^http:/, "ws:").replace(/^https:/, "wss:");

export interface LotteryDraw {
  draw_id: number;
  activity_id: string;
  award_id: number;
  prize_id: number;
  award_name: string;
  prize_name: string;
  draw_number: number;
  remaining_quantity: number;
  winner: { activity_user_id: number; username: string };
  drawn_at: string;
  prize_image_url: string | null;
}
export interface LotteryPrizeSnapshot {
  prize_id: number;
  award_id: number;
  name: string;
  quantity: number;
  remaining_quantity: number;
  sort_order: number;
  is_enabled: boolean;
  image_url: string | null;
}
export interface LotteryAwardSnapshot {
  award_id: number;
  name: string;
  sort_order: number;
  prizes: LotteryPrizeSnapshot[];
  draws: LotteryDraw[];
}
export interface LotteryRoundParticipant {
  activity_user_id: number;
  username: string;
  avatar_id: number;
}
export interface LotteryRound {
  round_id: string;
  award_id: number;
  award_name: string;
  prize_id: number;
  prize_name: string;
  phase: "rolling" | "stopping";
  participants: LotteryRoundParticipant[];
  started_at: string;
}
export interface LotterySnapshot {
  activity_id: string;
  activity_name: string;
  activity_status: "closed" | "open" | "ended";
  config: { no_repeat_across_prizes: boolean; rolling_name_count: number };
  awards: LotteryAwardSnapshot[];
  draws: LotteryDraw[];
  latest_draw_id: number;
  active_round?: LotteryRound | null;
}
export interface LotteryDrawnEvent {
  type: "lottery.drawn";
  round_id?: string;
  draw: LotteryDraw;
  roll_names: string[];
}
export const lotteryWebSocketURL = (apiBaseUrl: string, activityId: string) =>
  new URL(withBaseURL(apiBaseUrl, `/activities/${encodeURIComponent(activityId)}/lottery/ws`),
    window.location.href).toString()
    .replace(/^http:/, "ws:")
    .replace(/^https:/, "wss:");

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
