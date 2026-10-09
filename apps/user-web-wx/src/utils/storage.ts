export const activityTokenKey = (activityId: string) => `active_user_token:${activityId}`;

export const getActivityToken = (activityId: string) => {
  const value = wx.getStorageSync(activityTokenKey(activityId));
  return typeof value === "string" && value ? value : undefined;
};

export const setActivityToken = (activityId: string, token: string) => {
  wx.setStorageSync(activityTokenKey(activityId), token);
};

export const clearActivityToken = (activityId: string) => {
  wx.removeStorageSync(activityTokenKey(activityId));
};
