<template>
  <div
    v-if="(phase === 'selecting' || phase === 'revealed') && winnerName"
    class="globe-winner-focus"
    data-winner-focus
    role="status"
    aria-live="polite"
  >
    <span class="globe-winner-focus__eyebrow">LUCKY WINNER</span>
    <span class="globe-winner-focus__avatar">
      <img :src="avatarSources[winnerAvatarId] || avatarSources[1]" alt="" />
    </span>
    <span class="globe-winner-focus__name">{{ winnerName }}</span>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import type { LotteryDraw, LotteryRoundParticipant } from "../../api/client";
import { avatarSources } from "./avatar-sources";

const props = defineProps<{
  phase: string;
  participants: LotteryRoundParticipant[];
  winnerId?: number | null;
  winner?: LotteryDraw["winner"] | null;
}>();

const winnerId = computed(() => props.winnerId ?? props.winner?.activity_user_id);
const winnerParticipant = computed(() => props.participants.find(
  (participant) => participant.activity_user_id === winnerId.value,
));
const winnerName = computed(() => winnerParticipant.value?.username || props.winner?.username);
const winnerAvatarId = computed(() => winnerParticipant.value?.avatar_id || props.winner?.avatar_id || 1);
</script>

<style scoped src="./LotteryWinnerReveal.css"></style>
