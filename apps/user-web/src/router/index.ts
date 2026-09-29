import { createRouter, createWebHistory } from "vue-router";

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: "/", component: () => import("../views/entry.vue") },
    {
      path: "/activity/:activityId",
      component: () => import("../views/activity/index.vue"),
      children: [
        { path: "", name: "activity-home", component: () => import("../views/activity/home.vue") },
        {
          path: "lottery-results",
          name: "activity-lottery-results",
          component: () => import("../views/activity/lottery-results.vue"),
        },
        { path: "lottery", name: "activity-lottery", component: () => import("../views/activity/lottery.vue") },
        { path: "chat", name: "activity-chat", component: () => import("../views/activity/chat.vue") },
        { path: "me", name: "activity-me", component: () => import("../views/activity/me.vue") },
      ],
    },
    { path: "/:pathMatch(.*)*", redirect: "/" },
  ],
});

export default router;
