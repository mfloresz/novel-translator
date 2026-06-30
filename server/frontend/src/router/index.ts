import { createRouter, createWebHistory } from "vue-router";
import { authState } from "@/app/auth";
import DashboardPage from "@/pages/DashboardPage.vue";
import SettingsPage from "@/pages/SettingsPage.vue";
import OperationsPage from "@/pages/OperationsPage.vue";
import NovelDetailPage from "@/pages/NovelDetailPage.vue";
import ChapterPage from "@/pages/ChapterPage.vue";
import ReaderPage from "@/pages/ReaderPage.vue";
import LoginPage from "@/pages/LoginPage.vue";
import RegisterPage from "@/pages/RegisterPage.vue";

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/login",
      name: "login",
      component: LoginPage,
      meta: { guestOnly: true },
    },
    {
      path: "/register",
      name: "register",
      component: RegisterPage,
      meta: { guestOnly: true },
    },
    {
      path: "/",
      name: "dashboard",
      component: DashboardPage,
      meta: { requiresAuth: true },
    },
    {
      path: "/settings",
      name: "settings",
      component: SettingsPage,
      meta: { requiresAuth: true },
    },
    {
      path: "/operations",
      name: "operations",
      component: OperationsPage,
      meta: { requiresAuth: true },
    },
    {
      path: "/novels/:novelId",
      name: "novel-detail",
      component: NovelDetailPage,
      meta: { requiresAuth: true },
    },
    {
      path: "/novels/:novelId/chapters/:chapterId",
      name: "chapter-detail",
      component: ChapterPage,
      meta: { requiresAuth: true },
    },
    {
      path: "/novels/:novelId/read",
      name: "reader",
      component: ReaderPage,
      meta: { requiresAuth: true },
    },
    { path: "/:pathMatch(.*)*", redirect: "/" },
  ],
  scrollBehavior() {
    return { top: 0 };
  },
});

router.beforeEach((to) => {
  if (!authState.ready.value) {
    return true;
  }
  if (to.meta.requiresAuth && !authState.isAuthenticated.value) {
    return { name: "login", query: { redirect: to.fullPath } };
  }
  if (to.meta.guestOnly && authState.isAuthenticated.value) {
    return { name: "dashboard" };
  }
  return true;
});
