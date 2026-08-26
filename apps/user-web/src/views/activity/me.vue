<template>
  <section class="me-content">
    <section class="home-hero">
      <div class="me-profile">
        <ActivityAvatar :avatar-id="user.avatar_id" :alt="`${user.username}的活动头像`" />
        <div class="me-profile-copy">
          <p class="section-kicker">我的活动身份</p>
          <h1 class="home-title">{{ user.username }}</h1>
          <p class="home-description">你正在参与「{{ activity.name }}」</p>
        </div>
      </div>
    </section>
    <VanCellGroup class="me-list">
      <VanCell title="活动名称" :value="activity.name" />
      <VanCell title="活动状态" :value="statusLabel(activity.status)" />
      <VanCell title="活动用户 ID" :value="String(user.activity_user_id)" />
      <VanCell title="加入时间" :value="formatDate(user.joined_at)" />
    </VanCellGroup>
    <VanButton block plain type="primary" class="logout-button" @click="logout">退出当前活动</VanButton>
  </section>
</template>

<script setup lang="ts">
import { inject } from "vue";
import { Button as VanButton, Cell as VanCell, CellGroup as VanCellGroup, showToast } from "vant";
import ActivityAvatar from "../../components/ActivityAvatar.vue";
import type { Activity, ActivityUserResponse } from "../../api/client";
import { activitySessionKey, type ActivitySession } from "./session";

const props = defineProps<{ activity: Activity; user: ActivityUserResponse }>();
const session = inject<ActivitySession>(activitySessionKey);
const logout = () => {
  if (!session) { showToast("当前会话不可用"); return; }
  session.logout();
};
const statusLabel = (status: Activity["status"]) => ({ closed: "活动未开始", open: "活动进行中", ended: "活动已结束" })[status];
const formatDate = (value: string) => new Date(value).toLocaleString("zh-CN", { hour12: false });
</script>
