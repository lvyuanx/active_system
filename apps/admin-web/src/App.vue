<template>
  <RouterView />
</template>

<script setup lang="ts">
import { onMounted, onUnmounted } from "vue";
import { useRouter } from "vue-router";
import { clearToken } from "./api/client";

const router = useRouter();
const handleUnauthorized = () => { clearToken(); router.push("/login"); };
onMounted(() => window.addEventListener("admin-unauthorized", handleUnauthorized));
onUnmounted(() => window.removeEventListener("admin-unauthorized", handleUnauthorized));
</script>
