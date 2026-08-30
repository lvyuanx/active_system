<template>
  <aside class="app-sidebar">
    <div class="brand-lockup">
      <span class="brand-mark">A</span>
      <div><strong>ACTIVE</strong><small>活动管理中心</small></div>
    </div>
    <button class="back-button" type="button" @click="goActivityList">
      <span class="back-icon">←</span>活动列表
    </button>
    <div v-if="activity" class="sidebar-context">
      <span class="sidebar-label">当前活动</span>
      <strong>{{ activity.name }}</strong>
      <span>ID {{ activity.activity_id.slice(0, 8).toUpperCase() }}</span>
    </div>
    <nav aria-label="活动管理导航">
      <button
        class="nav-item"
        :class="{ 'nav-item--active': active === 'home' }"
        type="button"
        @click="goHome"
      >
        <span class="nav-icon">⌂</span>首页
      </button>
      <button
        class="nav-item"
        :class="{ 'nav-item--active': active === 'danmaku' }"
        type="button"
        @click="goDanmaku"
      >
        <span class="nav-icon">◌</span>弹幕工具
      </button>
      <button
        class="nav-item"
        :class="{ 'nav-item--active': active === 'lottery' }"
        type="button"
        @click="goLottery"
      >
        <span class="nav-icon">✦</span>实时抽奖
      </button>
      <button
        class="nav-item"
        :class="{ 'nav-item--active': active === 'participants' }"
        type="button"
        @click="goParticipants"
      >
        <span class="nav-icon">◌</span>参与者
      </button>
      <button class="nav-item nav-item--disabled" type="button" disabled>
        <span class="nav-icon">▥</span>数据概览
      </button>
    </nav>
    <div class="sidebar-footer">
      <span class="account-avatar">{{ username.slice(0, 1).toUpperCase() }}</span>
      <div class="account-copy"><strong>{{ username }}</strong><small>超级管理员</small></div>
      <el-button text class="logout-button" @click="logout">退出</el-button>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { useRouter } from "vue-router";
import { clearToken, type Activity } from "../api/client";

const props = defineProps<{
  activity?: Activity;
  activityId: string;
  active: "home" | "danmaku" | "lottery" | "participants";
  username: string;
}>();
const router = useRouter();

const goActivityList = () => router.push("/");
const goHome = () => router.push(`/activities/${props.activityId}`);
const goDanmaku = () => router.push(`/activities/${props.activityId}/danmaku`);
const goLottery = () => router.push(`/activities/${props.activityId}/lottery`);
const goParticipants = () => router.push(`/activities/${props.activityId}/participants`);
const logout = () => {
  clearToken();
  router.push("/login");
};
</script>
