import { completeSmsLogin, sendActivitySmsCode, smsLoginActivityUser } from "../../services/api";
import { Activity, ActivityUserResponse } from "../../types/api";
import {
  currentActivityId,
  goToHome,
  loadActivityContext,
  saveActivityUser,
  setCurrentActivityId,
} from "../../services/session";
import { setRuntimeConfigFromOrigin } from "../../config";
import { parseActivityId, parseScanTarget } from "../../utils/launch";

interface EntryData {
  loading: boolean;
  error: string;
  activityId: string;
  activity: Activity | null;
  user: ActivityUserResponse | null;
  statusBarHeight: number;
  sendingCode: boolean;
  submitting: boolean;
  codeCountdown: number;
  needsName: boolean;
  verificationToken: string;
  form: { phone: string; code: string; username: string };
}

const phonePattern = /^1[3-9][0-9]{9}$/;
const smsCodePattern = /^[0-9]{4,6}$/;

Page({
  data: {
    loading: false,
    error: "",
    activityId: "",
    activity: null,
    user: null,
    statusBarHeight: 0,
    sendingCode: false,
    submitting: false,
    codeCountdown: 0,
    needsName: false,
    verificationToken: "",
    form: { phone: "", code: "", username: "" },
  } as EntryData,

  countdownTimer: undefined as number | undefined,

  onLoad(options: Record<string, string | undefined>) {
    const activityId = parseActivityId({ query: options }) ?? currentActivityId();
    const metrics = getApp<IAppOption>().globalData;
    this.setData({ activityId: activityId ?? "", statusBarHeight: metrics.statusBarHeight });
    if (activityId) this.load();
  },

  async load() {
    const activityId = this.data.activityId;
    if (!activityId) return;
    this.setData({ loading: true, error: "" });
    try {
      const context = await loadActivityContext(activityId);
      if (context.user) {
        this.setData({ activity: context.activity, user: context.user });
        goToHome();
        return;
      }
      this.setData({ activity: context.activity, user: null });
    } catch (error) {
      this.setData({ error: error instanceof Error ? error.message : "活动不存在或已关闭" });
    } finally {
      this.setData({ loading: false });
    }
  },

  handlePhoneInput(event: WechatMiniprogram.Input) {
    this.setData({ "form.phone": event.detail.value.replace(/[^0-9]/g, "").slice(0, 11) });
  },

  handleCodeInput(event: WechatMiniprogram.Input) {
    this.setData({ "form.code": event.detail.value.replace(/[^0-9]/g, "").slice(0, 6) });
  },

  handleUsernameInput(event: WechatMiniprogram.Input) {
    this.setData({ "form.username": event.detail.value });
  },

  scanActivity() {
    wx.scanCode({
      onlyFromCamera: true,
      scanType: ["qrCode"],
      success: (result) => {
        const target = parseScanTarget(result.result || result.path || "");
        const activityId = target.activityId;
        if (!activityId) {
          wx.showToast({ title: "二维码不是有效的活动二维码", icon: "none" });
          return;
        }
        if (target.origin) setRuntimeConfigFromOrigin(target.origin);
        setCurrentActivityId(activityId);
        this.setData({ activityId, activity: null, user: null, error: "" });
        this.load();
      },
      fail: (error) => {
        if (!error.errMsg || !error.errMsg.toLowerCase().includes("cancel")) {
          wx.showToast({ title: "扫码失败，请重试", icon: "none" });
        }
      },
    });
  },

  async sendCode() {
    const phone = this.data.form.phone.trim();
    if (!phonePattern.test(phone)) {
      wx.showToast({ title: "请输入有效的手机号", icon: "none" });
      return;
    }
    this.setData({ sendingCode: true });
    try {
      const result = await sendActivitySmsCode(this.data.activityId, phone);
      this.setData({
        "form.phone": phone,
        "form.code": "",
        "form.username": "",
        needsName: false,
        verificationToken: "",
      });
      this.startCountdown(result.retry_after);
      wx.showToast({ title: result.message, icon: "none" });
    } catch (error) {
      wx.showToast({ title: error instanceof Error ? error.message : "验证码发送失败", icon: "none" });
    } finally {
      this.setData({ sendingCode: false });
    }
  },

  async submit() {
    const phone = this.data.form.phone.trim();
    const code = this.data.form.code.trim();
    if (!phonePattern.test(phone)) {
      wx.showToast({ title: "请输入有效的手机号", icon: "none" });
      return;
    }
    if (!smsCodePattern.test(code)) {
      wx.showToast({ title: "请输入 4-6 位数字验证码", icon: "none" });
      return;
    }
    this.setData({ submitting: true });
    try {
      const result = await smsLoginActivityUser(this.data.activityId, { phone, code });
      if (result.needs_name) {
        if (!result.verification_token) throw new Error("短信验证凭证缺失，请重新验证");
        this.setData({
          "form.phone": phone,
          "form.code": "",
          "form.username": "",
          needsName: true,
          verificationToken: result.verification_token,
        });
        return;
      }
      if (!result.user) throw new Error("登录响应缺少用户信息");
      this.finishLogin(result.user);
    } catch (error) {
      wx.showToast({ title: error instanceof Error ? error.message : "登录失败，请稍后重试", icon: "none" });
    } finally {
      this.setData({ submitting: false });
    }
  },

  async confirmName() {
    const username = this.data.form.username.trim();
    if (!username) {
      wx.showToast({ title: "请输入姓名", icon: "none" });
      return;
    }
    if (!this.data.verificationToken) {
      this.backToLogin();
      wx.showToast({ title: "短信验证已失效，请重新验证", icon: "none" });
      return;
    }
    this.setData({ submitting: true });
    try {
      const result = await completeSmsLogin(this.data.activityId, {
        verification_token: this.data.verificationToken,
        username,
      });
      this.setData({ needsName: false, verificationToken: "" });
      this.finishLogin(result);
    } catch (error) {
      wx.showToast({ title: error instanceof Error ? error.message : "登录失败，请稍后重试", icon: "none" });
    } finally {
      this.setData({ submitting: false });
    }
  },

  backToLogin() {
    this.setData({ needsName: false, verificationToken: "", "form.code": "", "form.username": "" });
  },

  finishLogin(user: ActivityUserResponse) {
    saveActivityUser(this.data.activityId, user);
    this.setData({ user });
    wx.showToast({ title: "登录成功", icon: "success" });
    goToHome();
  },

  startCountdown(seconds: number) {
    if (this.countdownTimer !== undefined) clearInterval(this.countdownTimer);
    this.setData({ codeCountdown: Math.max(1, Math.ceil(seconds)) });
    this.countdownTimer = setInterval(() => {
      const next = this.data.codeCountdown - 1;
      if (next <= 0) {
        if (this.countdownTimer !== undefined) clearInterval(this.countdownTimer);
        this.countdownTimer = undefined;
        this.setData({ codeCountdown: 0 });
      } else {
        this.setData({ codeCountdown: next });
      }
    }, 1000) as unknown as number;
  },

  onUnload() {
    if (this.countdownTimer !== undefined) clearInterval(this.countdownTimer);
  },
});
