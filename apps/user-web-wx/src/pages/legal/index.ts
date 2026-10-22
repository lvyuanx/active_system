import {
  getLegalDocument,
  LegalDocumentType,
  LegalSection,
} from "../../utils/privacy";

interface LegalPageData {
  statusBarHeight: number;
  title: string;
  subtitle: string;
  updatedAt: string;
  sections: LegalSection[];
}

Page({
  data: {
    statusBarHeight: 0,
    title: "",
    subtitle: "",
    updatedAt: "",
    sections: [],
  } as LegalPageData,

  onLoad(options: { type?: string }) {
    const type: LegalDocumentType = options.type === "privacy" ? "privacy" : "service";
    const document = getLegalDocument(type);
    this.setData({
      statusBarHeight: getApp<IAppOption>().globalData.statusBarHeight,
      ...document,
    });
  },

  goBack() {
    wx.navigateBack({
      delta: 1,
      fail: () => wx.reLaunch({ url: "/pages/entry/index" }),
    });
  },
});
