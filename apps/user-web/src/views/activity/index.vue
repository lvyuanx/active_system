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
          <h1 class="login-title">登录活动</h1>
          <p class="login-description">填写以下信息，即可进入当前活动。</p>
        </header>
        <VanForm class="login-form" :show-error="true" :show-error-message="false" @submit="submit">
          <section class="field-stack">
            <div class="field-item">
              <label for="activity-username">用户名</label>
              <VanField
                id="activity-username"
                v-model="form.username"
                name="username"
                center
                left-icon="contact-o"
                placeholder="请输入用户名"
                autocomplete="username"
                clearable
                :rules="[{ required: true, message: '请输入用户名' }]"
              />
            </div>
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
                :rules="[{ required: true, message: '请输入手机号' }]"
              />
            </div>
            <VanButton block type="primary" native-type="submit" :loading="submitting" class="login-submit">
              登录并进入
            </VanButton>
          </section>
        </VanForm>
        <p class="auto-register-note"><VanIcon name="info-o" aria-hidden="true" /><span>未注册用户会自动注册</span></p>
      </div>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, provide, reactive, ref } from "vue";
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
import { useKeyboardViewport } from "./useKeyboardViewport";
import {
  ApiError,
  clearActivityToken,
  getActivity,
  getActivityMe,
  getActivityToken,
  loginActivityUser,
  registerActivityUser,
  setActivityToken,
  type Activity,
  type ActivityUserResponse,
} from "../../api/client";

const route = useRoute();
const router = useRouter();
const activityId = String(route.params.activityId);
const basePath = `/activity/${activityId}`;
const activity = ref<Activity>();
const user = ref<ActivityUserResponse>();
const loading = ref(true);
const submitting = ref(false);
const error = ref("");
const form = reactive({ username: "", phone: "" });
const activeTab = computed(() => {
  if (route.path === `${basePath}/chat`) return 1;
  if (route.path === `${basePath}/me`) return 2;
  return 0;
});
const { keyboardVisible, viewportStyle } = useKeyboardViewport(computed(() => route.name === "activity-chat"));

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
const submit = async () => {
  submitting.value = true;
  try {
    const credentials = { username: form.username.trim(), phone: form.phone.trim() };
    let result: ActivityUserResponse;
    let automaticallyRegistered = false;
    try {
      result = await loginActivityUser(activityId, credentials);
    } catch (err) {
      if (!(err instanceof ApiError) || err.status !== 401) throw err;
      result = await registerActivityUser(activityId, credentials);
      automaticallyRegistered = true;
    }
    setActivityToken(activityId, result.access_token);
    user.value = result;
    showToast(automaticallyRegistered ? "已自动注册并进入活动" : "登录成功");
  } catch (err) {
    showToast(err instanceof Error ? err.message : "操作失败，请稍后重试");
  } finally {
    submitting.value = false;
  }
};

onMounted(load);
</script>
