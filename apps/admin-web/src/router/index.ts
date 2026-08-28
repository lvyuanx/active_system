import { createRouter, createWebHistory } from "vue-router";
import { getToken } from "../api/client";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/login", component: () => import("../views/login/index.vue") },
    { path: "/", component: () => import("../views/home/index.vue"), meta: { requiresAuth: true } },
    {
      path: "/activities/:activityId",
      component: () => import("../views/activity/index.vue"),
      meta: { requiresAuth: true },
    },
    {
      path: "/activities/:activityId/danmaku",
      component: () => import("../views/danmaku/index.vue"),
      meta: { requiresAuth: true },
    },
    {
      path: "/activities/:activityId/participants",
      component: () => import("../views/participants/index.vue"),
      meta: { requiresAuth: true },
    },
    { path: "/:pathMatch(.*)*", redirect: "/" },
  ],
});

router.beforeEach((to) => {
  if (to.meta.requiresAuth && !getToken()) return "/login";
  if (to.path === "/login" && getToken()) return "/";
  return true;
});

export default router;
