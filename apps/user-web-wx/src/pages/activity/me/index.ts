import { Activity, ActivityUserResponse } from "../../../types/api";
import {
  currentActivityId,
  goToEntry,
  loadActivityContext,
  resolveActivityId,
  resetActivitySession,
  setActivityTab,
} from "../../../services/session";
import { openLegalDocument } from "../../../utils/privacy";

interface MeData {
  loading: boolean;
  error: string;
  activity?: Activity;
  user?: ActivityUserResponse;
  statusBarHeight: number;
  statusLabel: string;
  joinedAt: string;
}

const statusLabels: Record<string, string> = {
  closed: "活动未开始",
  open: "活动进行中",
  ended: "活动已结束",
};

Page({
  data: {
    loading: true,
    error: "",
    activity: undefined,
    user: undefined,
    statusBarHeight: 0,
    statusLabel: "",
    joinedAt: "",
  } as MeData,

  activityId: "",

  onLoad(options: { activity_id?: string }) {
    this.activityId = resolveActivityId(options) ?? currentActivityId() ?? "";
    this.setData({ statusBarHeight: getApp<IAppOption>().globalData.statusBarHeight });
    if (!this.activityId) {
      goToEntry();
      return;
    }
    this.load();
  },

  onShow() {
    setActivityTab(2);
    if (this.activityId && !this.data.loading) this.load();
  },

  async load() {
    this.setData({ loading: true, error: "" });
    try {
      const context = await loadActivityContext(this.activityId);
      if (!context.user) {
        goToEntry();
        return;
      }
      this.setData({
        activity: context.activity,
        user: context.user,
        statusLabel: statusLabels[context.activity.status],
        joinedAt: formatDate(context.user.joined_at),
      });
    } catch (error) {
      this.setData({ error: error instanceof Error ? error.message : "活动加载失败" });
    } finally {
      this.setData({ loading: false });
    }
  },

  logout() {
    wx.showModal({
      title: "退出当前活动",
      content: "退出后需要重新验证手机号才能进入，确定继续吗？",
      confirmColor: "#d5b36b",
      success: (result) => {
        if (!result.confirm) return;
        resetActivitySession(this.activityId);
        goToEntry();
      },
    });
  },

  openServiceAgreement() {
    openLegalDocument("service");
  },

  openPrivacyPolicy() {
    openLegalDocument("privacy");
  },
});

const formatDate = (value: string) => {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("zh-CN", { hour12: false });
};
