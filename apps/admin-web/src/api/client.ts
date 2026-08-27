const baseURL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

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
  headers.set("Content-Type", "application/json");
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
export interface DanmakuSettings {
  track_count: number;
  font_size: number;
  opacity: number;
  duration_seconds: number;
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
