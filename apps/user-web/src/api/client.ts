const baseURL =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";
export const apiURL = (path: string) => `${baseURL}${path}`;
export const mediaURL = (imageUrl: string | null): string | null => {
  if (!imageUrl) return null;
  const origin = baseURL.startsWith("http") ? new URL(baseURL).origin : window.location.origin;
  return new URL(imageUrl, origin).toString();
};
export const chatWebSocketURL = (activityId: string) => {
  const url = apiURL(`/activities/${activityId}/chat/ws`);
  return url.replace(/^http:/, "ws:").replace(/^https:/, "wss:");
};

export interface Activity {
  activity_id: string;
  name: string;
  description: string | null;
  status: "closed" | "open" | "ended";
}
export type ActivityAvatarId =
  | 1
  | 2
  | 3
  | 4
  | 5
  | 6
  | 7
  | 8
  | 9
  | 10
  | 11
  | 12
  | 13
  | 14
  | 15
  | 16
  | 17
  | 18
  | 19
  | 20;
export interface ActivityUserResponse {
  access_token: string;
  token_type: string;
  activity_id: string;
  activity_user_id: number;
  username: string;
  joined_at: string;
  avatar_id: ActivityAvatarId;
}
export interface ChatMessage {
  message_id: number;
  activity_id: string;
  sender_activity_user_id: number;
  sender_username: string;
  body: string;
  created_at: string;
  message_type: "text" | "sticker";
  sticker: ChatSticker | null;
}
export interface ChatSticker {
  sticker_id: number;
  name: string;
  image_url: string;
  mime: string;
  width: number;
  height: number;
}
export interface ChatMessagePage {
  items: ChatMessage[];
  has_more: boolean;
}
export interface ActivityCredentials {
  username: string;
  phone: string;
}

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
  }
}

export const activityTokenKey = (activityId: string) =>
  `active_user_token:${activityId}`;
export const getActivityToken = (activityId: string) =>
  localStorage.getItem(activityTokenKey(activityId));
export const setActivityToken = (activityId: string, token: string) =>
  localStorage.setItem(activityTokenKey(activityId), token);
export const clearActivityToken = (activityId: string) =>
  localStorage.removeItem(activityTokenKey(activityId));

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set("Content-Type", "application/json");
  const response = await fetch(apiURL(path), { ...options, headers });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new ApiError(response.status, body.detail ?? "请求失败，请稍后重试");
  return body as T;
}

export const getActivity = (activityId: string) =>
  request<Activity>(`/activities/${activityId}`);
export const registerActivityUser = (
  activityId: string,
  payload: ActivityCredentials,
) =>
  request<ActivityUserResponse>(`/activities/${activityId}/auth/register`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
export const loginActivityUser = (
  activityId: string,
  payload: ActivityCredentials,
) =>
  request<ActivityUserResponse>(`/activities/${activityId}/auth/login`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
export const getActivityMe = (activityId: string, token: string) =>
  request<ActivityUserResponse>(`/activities/${activityId}/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });
export const getChatStickers = (activityId: string, token: string) =>
  request<ChatSticker[]>(`/activities/${activityId}/chat/stickers`, {
    headers: { Authorization: `Bearer ${token}` },
  });
export const getChatMessages = (
  activityId: string,
  token: string,
  params: { limit?: number; before_id?: number; after_id?: number } = {},
) => {
  const search = new URLSearchParams();
  search.set("limit", String(params.limit ?? 50));
  if (params.before_id !== undefined) search.set("before_id", String(params.before_id));
  if (params.after_id !== undefined) search.set("after_id", String(params.after_id));
  return request<ChatMessagePage>(`/activities/${activityId}/chat/messages?${search.toString()}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
};
