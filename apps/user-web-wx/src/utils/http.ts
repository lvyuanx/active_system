import { getRuntimeConfig } from "../config";

export class ApiError extends Error {
  constructor(public readonly status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

const trimBase = (value: string) => value.replace(/\/$/, "");

export const apiURL = (path: string) => `${trimBase(getRuntimeConfig().apiBaseUrl)}/${path.replace(/^\//, "")}`;

export const wsURL = (path: string) => `${trimBase(getRuntimeConfig().wsBaseUrl)}/${path.replace(/^\//, "")}`;

export const chatWebSocketURL = (activityId: string) => wsURL(`/activities/${activityId}/chat/ws`);

export const lotteryWebSocketURL = (activityId: string) => wsURL(`/activities/${activityId}/lottery/ws`);

export const mobileLotteryWebSocketURL = (activityId: string) => wsURL(`/activities/${activityId}/lottery/mobile/ws`);

export const mediaURL = (imageURL: string | null) => {
  if (!imageURL) return "";
  if (/^https?:\/\//i.test(imageURL)) return imageURL;
  const origin = getRuntimeConfig().apiBaseUrl.replace(/\/api\/v1\/?$/, "");
  return `${origin}${imageURL.startsWith("/") ? imageURL : `/${imageURL}`}`;
};

type RequestMethod = "GET" | "POST";

const readErrorMessage = (body: unknown) => {
  if (body && typeof body === "object" && "detail" in body) {
    const detail = (body as { detail?: unknown }).detail;
    if (typeof detail === "string" && detail) return detail;
  }
  return "请求失败，请稍后重试";
};

export const request = <T>(
  path: string,
  options: { method?: RequestMethod; data?: Record<string, unknown>; token?: string } = {},
) => new Promise<T>((resolve, reject) => {
  const header: Record<string, string> = { "Content-Type": "application/json" };
  if (options.token) header.Authorization = `Bearer ${options.token}`;
  wx.request({
    url: apiURL(path),
    method: options.method ?? "GET",
    data: options.data,
    header,
    dataType: "json",
    success: (response) => {
      if (response.statusCode < 200 || response.statusCode >= 300) {
        reject(new ApiError(response.statusCode, readErrorMessage(response.data)));
        return;
      }
      resolve(response.data as T);
    },
    fail: (error) => reject(new ApiError(0, error.errMsg || "网络请求失败，请检查网络连接")),
  });
});
