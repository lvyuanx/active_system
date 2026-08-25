const baseURL =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";
export const apiURL = (path: string) => `${baseURL}${path}`;

export interface Activity {
  activity_id: string;
  name: string;
  description: string | null;
  status: "closed" | "open" | "ended";
}
export interface ActivityUserResponse {
  access_token: string;
  token_type: string;
  activity_id: string;
  username: string;
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
