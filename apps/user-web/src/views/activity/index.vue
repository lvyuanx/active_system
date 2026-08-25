<template>
  <main class="activity-page">
    <VanNavBar
      v-if="!loading && user"
      class="activity-nav"
      :title="activity?.name || '活动入口'"
      left-arrow
      safe-area-inset-top
      @click-left="goBack"
    />

    <section v-if="loading" class="page-state" aria-live="polite">
      <div class="state-symbol state-symbol--loading">
        <VanLoading size="24px" color="var(--activity-gold)" />
      </div>
      <p class="state-kicker">活动入口</p>
      <h1 class="state-title">正在加载活动</h1>
      <p class="state-description">请稍候，马上为你打开活动页面。</p>
    </section>

    <section v-else-if="error" class="page-state" aria-live="assertive">
      <div class="state-symbol state-symbol--error">
        <VanIcon name="warning-o" />
      </div>
      <p class="state-kicker">进入失败</p>
      <h1 class="state-title">暂时无法进入活动</h1>
      <p class="state-message">{{ error }}</p>
      <VanButton type="primary" class="retry-button" @click="load">
        重新加载
      </VanButton>
    </section>

    <template v-else-if="activity && user">
      <section class="home-content">
        <section class="home-hero">
          <div class="home-hero-top">
            <span class="section-kicker">活动空间</span>
            <VanTag
              round
              :type="
                activity.status === 'open'
                  ? 'success'
                  : activity.status === 'ended'
                    ? 'danger'
                    : 'primary'
              "
              :aria-label="'当前活动状态：' + statusLabel(activity.status)"
            >
              {{ statusLabel(activity.status) }}
            </VanTag>
          </div>
          <h1 class="home-title">你好，{{ user.username }}</h1>
          <p class="home-description">
            {{ activity.description || "活动内容即将开始，敬请期待。" }}
          </p>
          <div class="activity-meta">
            <span>当前活动</span>
            <strong>{{ activity.name || "活动入口" }}</strong>
          </div>
        </section>

        <section class="service-section" aria-labelledby="service-heading">
          <div class="section-heading">
            <div>
              <p class="section-kicker">参与服务</p>
              <h2 id="service-heading">活动服务</h2>
            </div>
            <span class="section-count">1 项</span>
          </div>
          <VanCellGroup class="service-list">
            <VanCell
              title="活动首页"
              label="报名、签到和活动内容将在这里开放"
            >
              <template #icon>
                <span class="service-icon" aria-hidden="true">
                  <VanIcon name="apps-o" />
                </span>
              </template>
              <template #value>
                <span class="service-value">即将开放</span>
              </template>
            </VanCell>
          </VanCellGroup>
        </section>
      </section>
    </template>

    <section v-else class="auth-section">
      <div class="auth-shell">
        <header class="login-hero">
          <div class="login-kicker" aria-hidden="true">
            <span></span>
            <strong>活动入口</strong>
            <span></span>
          </div>
          <img class="activity-logo" :src="activityLogo" alt="ACTIVE 活动标识" />
          <p class="activity-context">{{ activity?.name || "当前活动" }}</p>
          <h1 class="login-title">登录活动</h1>
          <p class="login-description">填写以下信息，即可进入当前活动。</p>
        </header>

        <VanForm
          class="login-form"
          :show-error="true"
          :show-error-message="false"
          @submit="submit"
        >
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
            <VanButton
              block
              type="primary"
              native-type="submit"
              :loading="submitting"
              class="login-submit"
            >
              登录并进入
            </VanButton>
          </section>
        </VanForm>
        <p class="auto-register-note">
          <VanIcon name="info-o" aria-hidden="true" />
          <span>未注册用户会自动注册</span>
        </p>
      </div>
    </section>
  </main>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import "./activity.css";
import "./activity-auth.css";
import activityLogo from "../../assets/active-logo.png";
import {
  Button as VanButton,
  Cell as VanCell,
  CellGroup as VanCellGroup,
  Field as VanField,
  Form as VanForm,
  Icon as VanIcon,
  Loading as VanLoading,
  NavBar as VanNavBar,
  Tag as VanTag,
  showToast,
} from "vant";
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
const activity = ref<Activity>();
const user = ref<ActivityUserResponse>();
const loading = ref(true);
const submitting = ref(false);
const error = ref("");
const form = reactive({ username: "", phone: "" });

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
    const credentials = {
      username: form.username.trim(),
      phone: form.phone.trim(),
    };
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
const goBack = () => router.back();
const statusLabel = (status: Activity["status"]) =>
  ({ closed: "活动未开始", open: "活动进行中", ended: "活动已结束" })[status];
onMounted(load);
</script>
