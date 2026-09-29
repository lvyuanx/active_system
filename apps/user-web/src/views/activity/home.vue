<template>
  <section class="home-content">
    <section class="home-hero">
      <div class="home-hero-top">
        <span class="section-kicker">活动空间</span>
        <VanTag
          round
          :type="activity.status === 'open' ? 'success' : activity.status === 'ended' ? 'danger' : 'primary'"
        >
          {{ statusLabel(activity.status) }}
        </VanTag>
      </div>
      <div class="home-profile">
        <ActivityAvatar :avatar-id="user.avatar_id" :alt="`${user.username}的活动头像`" />
        <div class="home-profile-copy">
          <h1 class="home-title">你好，{{ user.username }}</h1>
          <p class="home-description">{{ activity.description || "活动内容即将开始，敬请期待。" }}</p>
        </div>
      </div>
      <div class="activity-meta"><span>当前活动</span><strong>{{ activity.name || "活动入口" }}</strong></div>
    </section>
    <section class="service-section" aria-labelledby="service-heading">
      <div class="section-heading">
        <div><p class="section-kicker">参与服务</p><h2 id="service-heading">活动服务</h2></div>
        <span class="section-count">{{ user.can_mobile_lottery ? 2 : 1 }} 项</span>
      </div>
      <VanCellGroup class="service-list">
        <VanCell
          title="活动聊天室"
          label="与同场活动参与者实时交流"
          is-link
          :to="{ name: 'activity-chat', params: { activityId: activity.activity_id } }"
        >
          <template #icon><span class="service-icon" aria-hidden="true"><VanIcon name="chat-o" /></span></template>
        </VanCell>
        <VanCell
          v-if="user.can_mobile_lottery"
          title="移动端抽奖"
          label="切换奖品并发起抽奖"
          is-link
          :to="{ name: 'activity-lottery', params: { activityId: activity.activity_id } }"
        >
          <template #icon><span class="service-icon" aria-hidden="true"><VanIcon name="gift-o" /></span></template>
        </VanCell>
      </VanCellGroup>
    </section>
  </section>
</template>

<script setup lang="ts">
import {
  Cell as VanCell,
  CellGroup as VanCellGroup,
  Icon as VanIcon,
  Tag as VanTag,
} from "vant";
import ActivityAvatar from "../../components/ActivityAvatar.vue";
import type { Activity, ActivityUserResponse } from "../../api/client";

defineProps<{ activity: Activity; user: ActivityUserResponse }>();
const statusLabel = (status: Activity["status"]) =>
  ({ closed: "活动未开始", open: "活动进行中", ended: "活动已结束" })[status];
</script>
