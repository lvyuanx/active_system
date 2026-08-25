import { createRouter, createWebHistory } from "vue-router";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/activity/:activityId", component: () => import("../views/activity/index.vue") },
    { path: "/:pathMatch(.*)*", redirect: "/" },
  ],
});

export default router;
