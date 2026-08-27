<template>
  <DanmakuOverlay v-if="isDanmakuOverlay" />
  <main v-else class="screen-shell">
    <h1>活动数据大屏</h1>
    <p>实时数据展示基础结构已就绪。</p>
  </main>
</template>

<script setup lang="ts">
import DanmakuOverlay from "./components/realtime/DanmakuOverlay.vue";

const isDanmakuOverlay = new URLSearchParams(window.location.search).get("danmaku-overlay") === "1";
</script>
