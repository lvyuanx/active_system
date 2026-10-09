import { Activity, ActivityUserResponse } from "../../../types/api";
import {
  currentActivityId,
  goToEntry,
  loadActivityContext,
  resolveActivityId,
  setActivityTab,
} from "../../../services/session";

interface HomeData {
  loading: boolean;
  error: string;
  activity?: Activity;
  user?: ActivityUserResponse;
  statusBarHeight: number;
  statusLabel: string;
  statusClass: string;
  serviceCount: number;
}

Page({
  data: {
    loading: true,
    error: "",
    activity: undefined,
    user: undefined,
    statusBarHeight: 0,
    statusLabel: "",
    statusClass: "",
    serviceCount: 2,
  } as HomeData,

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
    setActivityTab(0);
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
      const statusLabel = ({ closed: "活动未开始", open: "活动进行中", ended: "活动已结束" } as Record<string, string>)[
        context.activity.status
      ];
      const statusClass = context.activity.status === "open"
        ? "tag--success"
        : context.activity.status === "ended" ? "tag--danger" : "";
      this.setData({
        activity: context.activity,
        user: context.user,
        statusLabel,
        statusClass,
        serviceCount: context.user.can_mobile_lottery ? 3 : 2,
      });
    } catch (error) {
      this.setData({ error: error instanceof Error ? error.message : "活动加载失败" });
    } finally {
      this.setData({ loading: false });
    }
  },

  goLotteryResults() {
    wx.navigateTo({
      url: `/pages/activity/lottery-results/index?activity_id=${encodeURIComponent(this.activityId)}`,
    });
  },

  goLottery() {
    wx.navigateTo({ url: `/pages/activity/lottery/index?activity_id=${encodeURIComponent(this.activityId)}` });
  },

  goChat() {
    wx.switchTab({ url: "/pages/activity/chat/index" });
  },
});
