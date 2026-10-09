import {
  Activity,
  ActivityUserResponse,
  ChatMessagePage,
  ChatSticker,
  SmsCodeSendResponse,
  SmsLoginResponse,
} from "../types/api";
import { request } from "../utils/http";

export const getActivity = (activityId: string) =>
  request<Activity>(`/activities/${activityId}`);

export const getActivityMe = (activityId: string, token: string) =>
  request<ActivityUserResponse>(`/activities/${activityId}/me`, { token });

export const sendActivitySmsCode = (activityId: string, phone: string) =>
  request<SmsCodeSendResponse>(`/activities/${activityId}/auth/sms-code`, {
    method: "POST",
    data: { phone },
  });

export const smsLoginActivityUser = (
  activityId: string,
  payload: { phone: string; code: string },
) => request<SmsLoginResponse>(`/activities/${activityId}/auth/sms-login`, {
  method: "POST",
  data: payload,
});

export const completeSmsLogin = (
  activityId: string,
  payload: { verification_token: string; username: string },
) => request<ActivityUserResponse>(`/activities/${activityId}/auth/sms-login/complete`, {
  method: "POST",
  data: payload,
});

export const getChatStickers = (activityId: string, token: string) =>
  request<ChatSticker[]>(`/activities/${activityId}/chat/stickers`, { token });

export const getChatMessages = (
  activityId: string,
  token: string,
  params: { limit?: number; before_id?: number; after_id?: number } = {},
) => {
  const query = [
    ["limit", params.limit ?? 50],
    params.before_id === undefined ? undefined : ["before_id", params.before_id],
    params.after_id === undefined ? undefined : ["after_id", params.after_id],
  ]
    .filter((item): item is [string, string | number] => Boolean(item))
    .map(([key, value]) => `${key}=${encodeURIComponent(String(value))}`)
    .join("&");
  return request<ChatMessagePage>(
    `/activities/${activityId}/chat/messages?${query}`,
    { token },
  );
};
