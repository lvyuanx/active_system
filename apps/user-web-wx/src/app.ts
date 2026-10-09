import { parseActivityId } from "./utils/launch";

const readWindowMetrics = () => {
  const info = wx.getWindowInfo?.() ?? wx.getSystemInfoSync();
  const safeArea = "safeArea" in info ? info.safeArea : undefined;
  const windowHeight = "windowHeight" in info ? info.windowHeight : 0;
  const safeAreaBottom = safeArea && windowHeight ? Math.max(0, windowHeight - safeArea.bottom) : 0;
  return {
    statusBarHeight: Number(info.statusBarHeight || 0),
    safeAreaBottom,
  };
};

App<IAppOption>({
  globalData: {
    activityId: undefined,
    statusBarHeight: 0,
    safeAreaBottom: 0,
  },
  onLaunch(options) {
    const metrics = readWindowMetrics();
    this.globalData.statusBarHeight = metrics.statusBarHeight;
    this.globalData.safeAreaBottom = metrics.safeAreaBottom;
    this.globalData.activityId = parseActivityId(options);
  },
  onShow(options) {
    const activityId = parseActivityId(options);
    if (activityId) this.globalData.activityId = activityId;
  },
});
