Component({
  properties: {
    avatarId: {
      type: Number,
      value: 1,
    },
    alt: {
      type: String,
      value: "活动头像",
    },
    size: {
      type: String,
      value: "normal",
    },
  },
  data: {
    src: "/assets/avatars/avatar-01.svg",
  },
  observers: {
    avatarId(value: number) {
      this.updateAvatar(value);
    },
  },
  lifetimes: {
    attached() {
      this.updateAvatar(this.properties.avatarId);
    },
  },
  methods: {
    updateAvatar(value: number) {
      const id = Number.isInteger(value) && value >= 1 && value <= 20 ? value : 1;
      this.setData({ src: `/assets/avatars/avatar-${String(id).padStart(2, "0")}.svg` });
    },
    handleError() {
      this.setData({ src: "/assets/avatars/avatar-01.svg" });
    },
  },
});
