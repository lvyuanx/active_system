<template>
  <DanmakuOverlay v-if="isDanmakuOverlay" />
  <LotteryScreen v-else-if="activityId" :activity-id="activityId" />
  <main v-else class="screen-shell">
    <h1>活动数据大屏</h1>
    <p>请在地址中提供 activity_id 以进入实时抽奖大屏。</p>
  </main>
</template>

<script setup lang="ts">
import DanmakuOverlay from "./components/realtime/DanmakuOverlay.vue";
import LotteryScreen from "./components/lottery/LotteryScreen.vue";

const isDanmakuOverlay = new URLSearchParams(window.location.search).get("danmaku-overlay") === "1";
const params = new URLSearchParams(window.location.search);
const pathActivityId = window.location.pathname.match(/\/activities\/([^/]+)/)?.[1];
const activityId = params.get("activity_id") || params.get("activityId") || pathActivityId || "";
</script>
