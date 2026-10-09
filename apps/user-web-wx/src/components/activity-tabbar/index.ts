type TabName = "home" | "chat" | "me";

Component({
  properties: {
    active: {
      type: String,
      value: "home",
    },
    hidden: {
      type: Boolean,
      value: false,
    },
  },
  data: {
    safeBottom: 0,
    items: [
      {
        name: "home" as TabName,
        label: "首页",
         icon: "/assets/icons/tab-home.png",
         activeIcon: "/assets/icons/tab-home-active.png",
      },
      {
        name: "chat" as TabName,
        label: "聊天",
         icon: "/assets/icons/tab-chat.png",
         activeIcon: "/assets/icons/tab-chat-active.png",
      },
      {
        name: "me" as TabName,
        label: "我的",
         icon: "/assets/icons/tab-me.png",
         activeIcon: "/assets/icons/tab-me-active.png",
      },
    ],
  },
  lifetimes: {
    attached() {
      this.setData({ safeBottom: getApp<IAppOption>().globalData.safeAreaBottom });
    },
  },
  methods: {
    handleTap(event: WechatMiniprogram.TouchEvent) {
      const name = event.currentTarget.dataset.name as TabName;
      if (name === this.properties.active) return;
      const url = `/pages/activity/${name}/index`;
      wx.switchTab({ url });
    },
  },
});
