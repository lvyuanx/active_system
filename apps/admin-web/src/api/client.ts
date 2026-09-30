const baseURL = (import.meta.env.VITE_API_BASE_URL
  ?? (import.meta.env.PROD ? "/api/v1" : "http://localhost:8000/api/v1")).replace(/\/$/, "");

export function apiURL(path: string): string {
  return `${baseURL}${path}`;
}

export function getToken(): string | null {
  return localStorage.getItem("active_admin_token");
}

export function clearToken(): void {
  localStorage.removeItem("active_admin_token");
  localStorage.removeItem("active_admin_username");
}

export async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  if (options.body instanceof FormData) headers.delete("Content-Type");
  else headers.set("Content-Type", "application/json");
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const response = await fetch(apiURL(path), { ...options, headers });
  if (response.status === 401) {
    clearToken();
    window.dispatchEvent(new CustomEvent("admin-unauthorized"));
  }
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.detail ?? "请求失败，请稍后重试");
  return body as T;
}

export interface LoginResponse { access_token: string; token_type: string; username: string }
export interface Activity {
  activity_id: string;
  name: string;
  description: string | null;
  start_time: string | null;
  end_time: string | null;
  status: "closed" | "open" | "ended";
  created_at: string;
  updated_at: string;
}
export interface ActivityParticipant {
  activity_id: string;
  activity_user_id: number;
  username: string;
  phone: string;
  joined_at: string;
  is_active: boolean;
  is_muted: boolean;
  can_mobile_lottery: boolean;
}
export interface ActivityParticipantPage {
  items: ActivityParticipant[];
  page: number;
  page_size: number;
  total: number;
  has_more: boolean;
}
export type ParticipantAction =
  | "mute"
  | "unmute"
  | "deactivate"
  | "activate"
  | "mobile-lottery/grant"
  | "mobile-lottery/revoke";
export interface ChatSticker {
  sticker_id: number;
  name: string;
  image_url: string;
  mime: string;
  width: number;
  height: number;
}
export interface AdminChatSticker extends ChatSticker {
  activity_id: string;
  image_id: string;
  size: number;
  is_enabled: boolean;
  created_at: string;
}
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
export interface DanmakuAdminResponse {
  activity_id: string;
  settings: DanmakuSettings;
  token: string;
  token_created_at: string;
  updated_at: string;
}
export interface DanmakuTestConfig {
  user_count: number;
  min_delay_seconds: number;
  max_delay_seconds: number;
}
export interface DanmakuTestStatus extends DanmakuTestConfig {
  running: boolean;
  detail: string;
}
export interface LotteryAward {
  award_id: number;
  name: string;
  sort_order: number;
}
export interface LotteryPrize {
  prize_id: number;
  award_id: number;
  name: string;
  quantity: number;
  remaining_quantity: number;
  sort_order: number;
  is_enabled: boolean;
  image_url: string | null;
}
export interface LotteryPrizeImageResponse {
  image_url: string | null;
  image_id?: string | null;
  mime?: string | null;
  size?: number | null;
}
export interface LotteryEntry {
  activity_user_id: number;
  username: string;
  phone: string;
  is_active: boolean;
  is_blacklisted: boolean;
  is_whitelisted: boolean;
}
export interface LotteryEntrySummary {
  total: number;
  eligible: number;
  blacklisted: number;
  whitelisted: number;
  inactive: number;
}
export type LotteryEntryStatus = "all" | "eligible" | "blacklisted" | "whitelisted" | "inactive";
export interface LotteryEntryPage {
  prize_id: number;
  items: LotteryEntry[];
  page: number;
  page_size: number;
  total: number;
  has_more: boolean;
  summary: LotteryEntrySummary;
}
export interface LotteryEntryUpdateResponse {
  prize_id: number;
  entry: LotteryEntry;
  summary: LotteryEntrySummary;
}
export interface LotterySecurityCodeResponse { verified: boolean }
export interface LotteryConfig {
  activity_id: string;
  no_repeat_across_prizes: boolean;
  rolling_name_count: number;
  awards: LotteryAward[];
  prizes: LotteryPrize[];
  updated_at: string;
}
export interface LotteryDraw {
  draw_id: number;
  activity_id: string;
  award_id: number;
  prize_id: number;
  award_name: string;
  prize_name: string;
  prize_image_url?: string | null;
  draw_number: number;
  remaining_quantity: number;
  winner: {
    activity_user_id: number;
    username: string;
    phone: string;
    joined_at: string;
  };
  drawn_at: string;
}
export interface LotteryHistoryPage {
  items: LotteryDraw[];
  has_more: boolean;
}
export interface LotterySnapshotPrize extends LotteryPrize {}
export interface LotterySnapshotAward {
  award_id: number;
  name: string;
  sort_order: number;
  prizes: LotterySnapshotPrize[];
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
  activity_status: Activity["status"];
  config: Pick<LotteryConfig, "no_repeat_across_prizes" | "rolling_name_count">;
  awards: LotterySnapshotAward[];
  draws: LotteryDraw[];
  latest_draw_id: number;
  selected_prize_id?: number | null;
  active_round?: LotteryRound | null;
}

export interface LotteryConfigUpdate {
  no_repeat_across_prizes?: boolean;
  rolling_name_count?: number;
  awards?: Array<Pick<LotteryAward, "name" | "sort_order"> & { award_id?: number | null }>;
  prizes?: Array<
    Pick<LotteryPrize, "award_id" | "name" | "quantity" | "sort_order" | "is_enabled">
    & { prize_id?: number | null }
  >;
}

export const login = (username: string, password: string) => request<LoginResponse>("/auth/login", {
  method: "POST", body: JSON.stringify({ username, password }),
});
export const listActivities = () => request<Activity[]>("/admin/activities");
export const getActivity = async (id: string): Promise<Activity> => {
  try {
    return await request<Activity>(`/admin/activities/${id}`);
  } catch (detailError) {
    // 兼容尚未重启、没有单活动详情接口的旧后端进程。
    const activities = await listActivities();
    const activity = activities.find((item) => item.activity_id === id);
    if (activity) return activity;
    throw detailError;
  }
};
export const createActivity = (payload: Pick<Activity, "name" | "description" | "start_time" | "end_time">) =>
  request<Activity>("/admin/activities", { method: "POST", body: JSON.stringify(payload) });
export const changeActivityStatus = (id: string, action: "open" | "close" | "end") =>
  request<Activity>(`/admin/activities/${id}/${action}`, { method: "POST" });
export const listActivityParticipants = (
  activityId: string,
  options: { keyword?: string; page?: number; pageSize?: number } = {},
) => {
  const params = new URLSearchParams();
  if (options.keyword) params.set("keyword", options.keyword);
  if (options.page) params.set("page", String(options.page));
  if (options.pageSize) params.set("page_size", String(options.pageSize));
  const query = params.toString();
  return request<ActivityParticipantPage>(
    `/admin/activities/${activityId}/participants${query ? `?${query}` : ""}`,
  );
};
export const changeActivityParticipant = (
  activityId: string,
  activityUserId: number,
  action: ParticipantAction,
) => request<ActivityParticipant>(
  `/admin/activities/${activityId}/participants/${activityUserId}/${action}`,
  { method: "POST" },
);
export const listChatStickers = (activityId: string) =>
  request<AdminChatSticker[]>(`/admin/activities/${activityId}/chat/stickers`);
export const uploadChatSticker = (activityId: string, file: File, name?: string) => {
  const body = new FormData();
  body.append("file", file);
  if (name) body.append("name", name);
  return request<AdminChatSticker>(`/admin/activities/${activityId}/chat/stickers`, {
    method: "POST",
    body,
  });
};
export const disableChatSticker = (activityId: string, stickerId: number) =>
  request<AdminChatSticker>(`/admin/activities/${activityId}/chat/stickers/${stickerId}`, {
    method: "DELETE",
  });
export const restoreChatSticker = (activityId: string, stickerId: number) =>
  request<AdminChatSticker>(`/admin/activities/${activityId}/chat/stickers/${stickerId}/restore`, {
    method: "POST",
  });
export const getDanmaku = (activityId: string) =>
  request<DanmakuAdminResponse>(`/admin/activities/${activityId}/danmaku`);
export const updateDanmaku = (activityId: string, settings: DanmakuSettings) =>
  request<DanmakuAdminResponse>(`/admin/activities/${activityId}/danmaku`, {
    method: "PUT",
    body: JSON.stringify(settings),
  });
export const regenerateDanmakuToken = (activityId: string) =>
  request<DanmakuAdminResponse>(`/admin/activities/${activityId}/danmaku/token`, {
    method: "POST",
  });
export const getDanmakuTestStatus = (activityId: string) =>
  request<DanmakuTestStatus>(`/admin/activities/${activityId}/danmaku/test`);
export const startDanmakuTest = (activityId: string, config?: DanmakuTestConfig) =>
  request<DanmakuTestStatus>(`/admin/activities/${activityId}/danmaku/test/start`, {
    method: "POST",
    body: config ? JSON.stringify(config) : undefined,
  });
export const stopDanmakuTest = (activityId: string) =>
  request<DanmakuTestStatus>(`/admin/activities/${activityId}/danmaku/test/stop`, { method: "POST" });
export const getLottery = (activityId: string) =>
  request<LotteryConfig>(`/admin/activities/${activityId}/lottery`);
export const verifyLotterySecurityCode = (activityId: string, securityCode: string) =>
  request<LotterySecurityCodeResponse>(`/admin/activities/${activityId}/lottery/security-code/verify`, {
    method: "POST",
    body: JSON.stringify({ security_code: securityCode }),
  });
export const updateLottery = (activityId: string, config: LotteryConfigUpdate) =>
  request<LotteryConfig>(`/admin/activities/${activityId}/lottery`, {
    method: "PUT",
    body: JSON.stringify(config),
  });
export const getLotteryEntries = (
  activityId: string,
  prizeId: number,
  options: {
    keyword?: string;
    status?: LotteryEntryStatus;
    page?: number;
    pageSize?: number;
  } = {},
) => {
  const params = new URLSearchParams();
  params.set("prize_id", String(prizeId));
  if (options.keyword) params.set("keyword", options.keyword);
  if (options.status) params.set("status", options.status);
  if (options.page) params.set("page", String(options.page));
  if (options.pageSize) params.set("page_size", String(options.pageSize));
  const query = params.toString();
  return request<LotteryEntryPage>(
    `/admin/activities/${activityId}/lottery/entries${query ? `?${query}` : ""}`,
  );
};
export const updateLotteryEntry = (
  activityId: string,
  prizeId: number,
  activityUserId: number,
  payload: Pick<LotteryEntry, "is_blacklisted" | "is_whitelisted">,
) => request<LotteryEntryUpdateResponse>(
  `/admin/activities/${activityId}/lottery/entries/${activityUserId}?prize_id=${prizeId}`,
  { method: "PUT", body: JSON.stringify(payload) },
);
export const mediaURL = (imageUrl: string | null): string | null => {
  if (!imageUrl) return null;
  const origin = baseURL.startsWith("http") ? new URL(baseURL).origin : window.location.origin;
  return new URL(imageUrl, origin).toString();
};
export const uploadLotteryPrizeImage = (activityId: string, prizeId: number, file: File) => {
  const body = new FormData();
  body.append("file", file);
  return request<LotteryPrizeImageResponse>(
    `/admin/activities/${activityId}/lottery/prizes/${prizeId}/image`,
    { method: "POST", body },
  );
};
export const deleteLotteryPrizeImage = (activityId: string, prizeId: number) =>
  request<LotteryPrizeImageResponse>(
    `/admin/activities/${activityId}/lottery/prizes/${prizeId}/image`,
    { method: "DELETE" },
  );
export const getLotteryHistory = (activityId: string) =>
  request<LotteryHistoryPage>(`/admin/activities/${activityId}/lottery/history`);
export const lotteryWebSocketURL = (activityId: string) =>
  new URL(`${baseURL}/admin/activities/${encodeURIComponent(activityId)}/lottery/ws`, window.location.href).toString()
    .replace(/^http:/, "ws:")
    .replace(/^https:/, "wss:");
