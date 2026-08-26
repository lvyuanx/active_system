<script setup lang="ts">
import { computed } from "vue";
import type { ActivityAvatarId } from "../api/client";
import avatar01 from "../assets/avatars/avatar-01.svg";
import avatar02 from "../assets/avatars/avatar-02.svg";
import avatar03 from "../assets/avatars/avatar-03.svg";
import avatar04 from "../assets/avatars/avatar-04.svg";
import avatar05 from "../assets/avatars/avatar-05.svg";
import avatar06 from "../assets/avatars/avatar-06.svg";
import avatar07 from "../assets/avatars/avatar-07.svg";
import avatar08 from "../assets/avatars/avatar-08.svg";
import avatar09 from "../assets/avatars/avatar-09.svg";
import avatar10 from "../assets/avatars/avatar-10.svg";
import avatar11 from "../assets/avatars/avatar-11.svg";
import avatar12 from "../assets/avatars/avatar-12.svg";
import avatar13 from "../assets/avatars/avatar-13.svg";
import avatar14 from "../assets/avatars/avatar-14.svg";
import avatar15 from "../assets/avatars/avatar-15.svg";
import avatar16 from "../assets/avatars/avatar-16.svg";
import avatar17 from "../assets/avatars/avatar-17.svg";
import avatar18 from "../assets/avatars/avatar-18.svg";
import avatar19 from "../assets/avatars/avatar-19.svg";
import avatar20 from "../assets/avatars/avatar-20.svg";

const props = withDefaults(
  defineProps<{
    avatarId: ActivityAvatarId;
    alt?: string;
    variant?: "large" | "small";
  }>(),
  { alt: "活动头像", variant: "large" },
);

const avatarSources: Record<ActivityAvatarId, string> = {
  1: avatar01,
  2: avatar02,
  3: avatar03,
  4: avatar04,
  5: avatar05,
  6: avatar06,
  7: avatar07,
  8: avatar08,
  9: avatar09,
  10: avatar10,
  11: avatar11,
  12: avatar12,
  13: avatar13,
  14: avatar14,
  15: avatar15,
  16: avatar16,
  17: avatar17,
  18: avatar18,
  19: avatar19,
  20: avatar20,
};

const source = computed(() => avatarSources[props.avatarId] ?? avatarSources[1]);
</script>

<template>
  <img
    class="activity-avatar"
    :class="`activity-avatar--${variant}`"
    :src="source"
    :alt="alt"
  />
</template>

<style scoped>
.activity-avatar {
  display: block;
  flex: 0 0 auto;
  box-sizing: border-box;
  border: 1px solid var(--activity-line-strong);
  border-radius: 50%;
  background: var(--activity-surface-strong);
  object-fit: cover;
}

.activity-avatar--large {
  width: 72px;
  height: 72px;
}

.activity-avatar--small {
  width: 52px;
  height: 52px;
}
</style>
