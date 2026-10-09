type TabItem = {
  name: "home" | "chat" | "me";
  label: string;
  pagePath: string;
  icon: string;
  activeIcon: string;
};

const items: TabItem[] = [
  {
    name: "home",
    label: "首页",
    pagePath: "/pages/activity/home/index",
    icon: "/assets/icons/tab-home.png",
    activeIcon: "/assets/icons/tab-home-active.png",
  },
  {
    name: "chat",
    label: "聊天",
    pagePath: "/pages/activity/chat/index",
    icon: "/assets/icons/tab-chat.png",
    activeIcon: "/assets/icons/tab-chat-active.png",
  },
  {
    name: "me",
    label: "我的",
    pagePath: "/pages/activity/me/index",
    icon: "/assets/icons/tab-me.png",
    activeIcon: "/assets/icons/tab-me-active.png",
  },
];

Component({
  data: {
    hidden: false,
    selected: 0,
    items,
    safeBottom: 0,
  },

  lifetimes: {
    attached() {
      this.setData({ safeBottom: getApp<IAppOption>().globalData.safeAreaBottom });
    },
  },

  methods: {
    handleTap(event: WechatMiniprogram.TouchEvent) {
      const index = Number(event.currentTarget.dataset.index);
      const item = items[index];
      if (!item) return;
      this.setData({ selected: index });
      wx.switchTab({ url: item.pagePath });
    },
  },
});
