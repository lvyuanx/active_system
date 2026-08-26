import { createRouter, createWebHistory } from "vue-router";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/activity/:activityId",
      component: () => import("../views/activity/index.vue"),
      children: [
        { path: "", name: "activity-home", component: () => import("../views/activity/home.vue") },
        { path: "chat", name: "activity-chat", component: () => import("../views/activity/chat.vue") },
        { path: "me", name: "activity-me", component: () => import("../views/activity/me.vue") },
      ],
    },
    { path: "/:pathMatch(.*)*", redirect: "/" },
  ],
});

export default router;
