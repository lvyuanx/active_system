<template>
  <main
    class="activity-page"
    :class="{ 'activity-page--keyboard-visible': keyboardVisible }"
    :style="viewportStyle"
  >
    <section v-if="loading" class="page-state" aria-live="polite">
      <div class="state-symbol state-symbol--loading"><VanLoading size="24px" color="var(--activity-gold)" /></div>
      <p class="state-kicker">活动入口</p>
      <h1 class="state-title">正在加载活动</h1>
      <p class="state-description">请稍候，马上为你打开活动页面。</p>
    </section>

    <section v-else-if="error" class="page-state" aria-live="assertive">
      <div class="state-symbol state-symbol--error"><VanIcon name="warning-o" /></div>
      <p class="state-kicker">进入失败</p>
      <h1 class="state-title">暂时无法进入活动</h1>
      <p class="state-message">{{ error }}</p>
      <VanButton type="primary" class="retry-button" @click="load">重新加载</VanButton>
    </section>

    <div
      v-else-if="activity && user"
      class="activity-shell"
      :class="{ 'activity-shell--keyboard-visible': keyboardVisible }"
    >
      <RouterView v-slot="{ Component }">
        <component :is="Component" :activity="activity" :user="user" />
      </RouterView>
      <VanTabbar
        v-show="!keyboardVisible"
        :model-value="activeTab"
        route
        safe-area-inset-bottom
        class="activity-tabbar"
      >
        <VanTabbarItem :to="{ name: 'activity-home', params: { activityId } }" icon="home-o">
          首页
        </VanTabbarItem>
        <VanTabbarItem :to="{ name: 'activity-chat', params: { activityId } }" icon="chat-o">
          聊天
        </VanTabbarItem>
        <VanTabbarItem :to="{ name: 'activity-me', params: { activityId } }" icon="contact-o">
          我的
        </VanTabbarItem>
      </VanTabbar>
    </div>

    <section v-else class="auth-section">
      <div class="auth-shell">
        <header class="login-hero">
          <div class="login-kicker" aria-hidden="true"><span></span><strong>活动入口</strong><span></span></div>
          <img class="activity-logo" :src="activityLogo" alt="ACTIVE 活动标识" />
          <p class="activity-context">{{ activity?.name || "当前活动" }}</p>
          <h1 class="login-title">{{ needsName ? "补充姓名" : "短信登录" }}</h1>
          <p class="login-description">
            {{ needsName ? "验证码已通过，请输入姓名完成登录。" : "使用手机号接收验证码，验证后进入活动。" }}
          </p>
        </header>
        <VanForm class="login-form" :show-error="true" :show-error-message="false" @submit="submit">
          <section class="field-stack">
            <div class="field-item">
              <label for="activity-phone">手机号</label>
              <VanField
                id="activity-phone"
                v-model="form.phone"
                name="phone"
                center
                left-icon="phone-o"
                type="tel"
                placeholder="请输入手机号"
                autocomplete="tel"
                clearable
                :readonly="needsName"
                :rules="[{ required: true, message: '请输入手机号' }]"
              />
            </div>
            <div class="field-item">
              <label for="activity-sms-code">验证码</label>
              <VanField
                id="activity-sms-code"
                v-model="form.code"
                name="code"
                center
                left-icon="shield-o"
                type="tel"
                maxlength="8"
                placeholder="请输入短信验证码"
                autocomplete="one-time-code"
                clearable
                :rules="[{ required: true, message: '请输入验证码' }]"
              >
                <template #button>
                  <VanButton
                    size="small"
                    type="primary"
                    native-type="button"
                    class="code-send-button"
                    :loading="sendingCode"
                    :disabled="sendingCode || codeCountdown > 0"
                    @click="sendCode"
                  >
                    {{ codeCountdown > 0 ? codeCountdown + "s" : "发送验证码" }}
                  </VanButton>
                </template>
              </VanField>
            </div>
            <div v-if="needsName" class="field-item">
              <label for="activity-username">姓名</label>
              <VanField
                id="activity-username"
                v-model="form.username"
                name="username"
                center
                left-icon="contact-o"
                placeholder="请输入姓名"
                autocomplete="name"
                maxlength="100"
                clearable
                :rules="[{ required: true, message: '请输入姓名' }]"
              />
            </div>
            <VanButton block type="primary" native-type="submit" :loading="submitting" class="login-submit">
              {{ needsName ? "完成登录" : "验证并进入" }}
            </VanButton>
          </section>
        </VanForm>
        <p class="auto-register-note">
          <VanIcon name="info-o" aria-hidden="true" />
          <span>{{ needsName ? "姓名仅在首次进入活动时填写" : "新用户验证后补充姓名即可进入" }}</span>
        </p>
      </div>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, provide, reactive, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
  Button as VanButton,
  Field as VanField,
  Form as VanForm,
  Icon as VanIcon,
  Loading as VanLoading,
  Tabbar as VanTabbar,
  TabbarItem as VanTabbarItem,
  showToast,
} from "vant";
import "./activity.css";
import "./activity-auth.css";
import activityLogo from "../../assets/active-logo.png";
import { activitySessionKey, type ActivitySession } from "./session";
import { activityKeyboardVisibleKey, useKeyboardViewport } from "./useKeyboardViewport";
import {
  clearActivityToken,
  getActivity,
  getActivityMe,
  getActivityToken,
  sendActivitySmsCode,
  setActivityToken,
  smsLoginActivityUser,
  type Activity,
  type ActivityUserResponse,
} from "../../api/client";

const route = useRoute();
const router = useRouter();
const activityId = String(route.params.activityId);
const basePath = "/activity/" + activityId;
const activity = ref<Activity>();
const user = ref<ActivityUserResponse>();
const loading = ref(true);
const submitting = ref(false);
const sendingCode = ref(false);
const needsName = ref(false);
const codeCountdown = ref(0);
const error = ref("");
const form = reactive({ username: "", phone: "", code: "" });
const phonePattern = /^1[3-9][0-9]{9}$/;
let countdownTimer: number | undefined;
const activeTab = computed(() => {
  if (route.path === basePath + "/chat") return 1;
  if (route.path === basePath + "/me") return 2;
  return 0;
});
const { keyboardVisible, viewportStyle } = useKeyboardViewport(computed(() => route.name === "activity-chat"));
provide(activityKeyboardVisibleKey, keyboardVisible);

const logout = () => {
  clearActivityToken(activityId);
  user.value = undefined;
  router.replace(basePath);
};
provide(activitySessionKey, { activityId, logout } satisfies ActivitySession);

const load = async () => {
  loading.value = true;
  error.value = "";
  try {
    activity.value = await getActivity(activityId);
    const token = getActivityToken(activityId);
    if (token) {
      try {
        user.value = await getActivityMe(activityId, token);
      } catch {
        clearActivityToken(activityId);
      }
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : "活动不存在或已关闭";
  } finally {
    loading.value = false;
  }
};

const stopCountdown = () => {
  if (countdownTimer === undefined) return;
  window.clearInterval(countdownTimer);
  countdownTimer = undefined;
};

const startCountdown = (seconds: number) => {
  stopCountdown();
  codeCountdown.value = Math.max(1, Math.ceil(seconds));
  countdownTimer = window.setInterval(() => {
    codeCountdown.value -= 1;
    if (codeCountdown.value <= 0) {
      codeCountdown.value = 0;
      stopCountdown();
    }
  }, 1000);
};

const sendCode = async () => {
  const phone = form.phone.trim();
  if (!phonePattern.test(phone)) {
    showToast("请输入有效的手机号");
    return;
  }
  sendingCode.value = true;
  try {
    const result = await sendActivitySmsCode(activityId, phone);
    form.phone = phone;
    form.code = "";
    form.username = "";
    needsName.value = false;
    startCountdown(result.retry_after);
    showToast(result.message);
  } catch (err) {
    showToast(err instanceof Error ? err.message : "验证码发送失败，请稍后重试");
  } finally {
    sendingCode.value = false;
  }
};

const submit = async () => {
  const phone = form.phone.trim();
  const code = form.code.trim();
  if (!phonePattern.test(phone)) {
    showToast("请输入有效的手机号");
    return;
  }
  if (!/^[0-9]{4,8}$/.test(code)) {
    showToast("请输入 4-8 位数字验证码");
    return;
  }
  const username = form.username.trim();
  if (needsName.value && !username) {
    showToast("请输入姓名");
    return;
  }
  submitting.value = true;
  try {
    const result = await smsLoginActivityUser(
      activityId,
      needsName.value ? { phone, code, username } : { phone, code },
    );
    if (result.needs_name) {
      needsName.value = true;
      showToast("请输入姓名");
      return;
    }
    if (!result.user) {
      throw new Error("登录响应缺少用户信息");
    }
    setActivityToken(activityId, result.user.access_token);
    user.value = result.user;
    showToast("登录成功");
  } catch (err) {
    showToast(err instanceof Error ? err.message : "操作失败，请稍后重试");
  } finally {
    submitting.value = false;
  }
};

onMounted(load);
onUnmounted(stopCountdown);
</script>
