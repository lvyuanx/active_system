import { Activity, ActivityUserResponse } from "../types/api";
import { getActivity, getActivityMe } from "./api";
import { clearActivityToken, getActivityToken, setActivityToken } from "../utils/storage";

export interface ActivityContext {
  activity: Activity;
  user?: ActivityUserResponse;
}

export const currentActivityId = () => getApp<IAppOption>().globalData.activityId;

export const setCurrentActivityId = (activityId: string) => {
  getApp<IAppOption>().globalData.activityId = activityId;
};

export const resolveActivityId = (options?: { activity_id?: string }) =>
  options?.activity_id?.trim() || currentActivityId();

export const loadActivityContext = async (activityId: string): Promise<ActivityContext> => {
  const activity = await getActivity(activityId);
  const token = getActivityToken(activityId);
  if (!token) return { activity };
  try {
    return { activity, user: await getActivityMe(activityId, token) };
  } catch {
    clearActivityToken(activityId);
    return { activity };
  }
};

export const saveActivityUser = (activityId: string, user: ActivityUserResponse) => {
  setActivityToken(activityId, user.access_token);
};

export const resetActivitySession = (activityId: string) => {
  clearActivityToken(activityId);
  getApp<IAppOption>().globalData.activityId = activityId;
};

type ActivityTabBar = {
  setData(data: { selected: number; hidden: boolean }): void;
};

export const setActivityTab = (selected: number) => {
  const pages = getCurrentPages();
  const page = pages[pages.length - 1] as unknown as {
    getTabBar?: () => ActivityTabBar | undefined;
  };
  page.getTabBar?.()?.setData({ selected, hidden: false });
};

export const goToEntry = () => {
  wx.reLaunch({ url: "/pages/entry/index" });
};

export const goToHome = () => {
  wx.switchTab({ url: "/pages/activity/home/index" });
};
