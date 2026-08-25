<template>
  <div class="activity-management">
    <aside class="app-sidebar">
      <div class="brand-lockup">
        <span class="brand-mark">A</span>
        <div><strong>ACTIVE</strong><small>活动管理中心</small></div>
      </div>
      <button class="back-button" type="button" @click="router.push('/')">
        <span class="back-icon">←</span>活动列表
      </button>
      <div v-if="activity" class="sidebar-context">
        <span class="sidebar-label">当前活动</span>
        <strong>{{ activity.name }}</strong>
        <span>ID {{ activity.activity_id.slice(0, 8).toUpperCase() }}</span>
      </div>
      <nav aria-label="活动管理导航">
        <button class="nav-item nav-item--active" type="button">
          <span class="nav-icon">⌂</span>首页
        </button>
        <button class="nav-item nav-item--disabled" type="button" disabled>
          <span class="nav-icon">◌</span>参与者
        </button>
        <button class="nav-item nav-item--disabled" type="button" disabled>
          <span class="nav-icon">▥</span>数据概览
        </button>
      </nav>
      <div class="sidebar-footer">
        <span class="account-avatar">{{ username.slice(0, 1).toUpperCase() }}</span>
        <div class="account-copy"><strong>{{ username }}</strong><small>超级管理员</small></div>
        <el-button text class="logout-button" @click="logout">退出</el-button>
      </div>
    </aside>

    <section class="workspace">
      <header class="workspace-topbar">
        <div class="breadcrumb"><span>活动管理</span><b>/</b><strong>{{ activity?.name || "加载中" }}</strong></div>
        <span class="workspace-status" :class="activity ? `workspace-status--${activity.status}` : ''">
          <i aria-hidden="true"></i>{{ activity ? statusLabel(activity.status) : "正在加载" }}
        </span>
      </header>

      <main class="management-page">
        <el-alert v-if="error" :title="error" type="error" show-icon class="page-alert" />
        <el-skeleton v-if="loading" :rows="8" animated />

        <template v-else-if="activity">
          <section class="activity-titlebar">
            <div>
              <p class="eyebrow">ACTIVITY MANAGEMENT</p>
              <h1>活动配置</h1>
              <p class="activity-meta">{{ activity.name }} · 更新于 {{ formatDate(activity.updated_at) }}</p>
            </div>
            <span class="status-badge" :class="`status-badge--${activity.status}`">
              <i aria-hidden="true"></i>{{ statusLabel(activity.status) }}
            </span>
          </section>

          <section class="content-surface">
            <div class="content-heading">
              <div><p class="eyebrow">ACTIVITY HOME</p><h2>活动入口</h2></div>
              <span class="content-hint">扫码即可进入移动端</span>
            </div>
            <div class="entry-grid">
              <article class="entry-panel entry-address-panel">
                <div class="panel-kicker">移动端地址</div>
                <h3>分享活动入口</h3>
                <p>将地址发送给参与者，或使用右侧二维码扫码进入。</p>
                <div class="address-box" aria-label="活动地址">{{ userUrl }}</div>
                <div class="panel-actions">
                  <el-button type="primary" @click="copyUrl">复制地址</el-button>
                  <el-button @click="openUserUrl">打开移动端</el-button>
                </div>
              </article>
              <article class="entry-panel qr-panel">
                <div class="panel-kicker">扫码进入</div>
                <div class="qr-frame">
                  <img v-if="qrDataUrl" :src="qrDataUrl" alt="活动移动端二维码" />
                  <span v-else class="qr-loading" aria-label="二维码生成中"></span>
                </div>
                <el-button text class="download-button" :disabled="!qrDataUrl" @click="downloadQr">
                  ↓ 下载二维码
                </el-button>
              </article>
            </div>
            <div class="entry-note"><span>●</span>首次进入需要完成注册；已登录用户会根据本机缓存 token 直接进入活动首页。</div>
          </section>
        </template>
      </main>
    </section>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import { ElMessage } from "element-plus";
import { useRoute, useRouter } from "vue-router";
import QRCode from "qrcode";
import { clearToken, getActivity, type Activity } from "../../api/client";

const route = useRoute();
const router = useRouter();
const activity = ref<Activity>();
const loading = ref(true);
const error = ref("");
const qrDataUrl = ref("");
const username = localStorage.getItem("active_admin_username") || "超级用户";
const userBaseUrl = (
  import.meta.env.VITE_USER_WEB_BASE_URL ?? "http://localhost:5175"
).replace(/\/$/, "");
const activityId = String(route.params.activityId);
const userUrl = `${userBaseUrl}/activity/${activityId}`;

const load = async () => {
  try {
    activity.value = await getActivity(activityId);
    qrDataUrl.value = await QRCode.toDataURL(userUrl, {
      width: 280,
      margin: 2,
      color: { dark: "#17211e", light: "#ffffff" },
    });
  } catch (err) {
    error.value = err instanceof Error ? err.message : "活动加载失败";
  } finally {
    loading.value = false;
  }
};
const copyUrl = async () => {
  await navigator.clipboard.writeText(userUrl);
  ElMessage.success("活动地址已复制");
};
const openUserUrl = () => window.open(userUrl, "_blank", "noopener,noreferrer");
const downloadQr = () => {
  const link = document.createElement("a");
  link.href = qrDataUrl.value;
  link.download = `${activity.value?.name || "活动"}-二维码.png`;
  link.click();
};
const logout = () => {
  clearToken();
  router.push("/login");
};
const statusLabel = (status: Activity["status"]) =>
  ({ closed: "已关闭", open: "进行中", ended: "已结束" })[status];
const formatDate = (value: string) =>
  new Date(value).toLocaleString("zh-CN", { hour12: false });
onMounted(load);
</script>

<style scoped>
.activity-management {
  min-height: 100dvh;
  background: #f3f5f4;
}
.management-page {
  width: min(100% - 48px, 1280px);
  margin: 0 auto;
  padding: 24px 0 72px;
}
.back-button {
  padding-left: 0;
  color: #64716b;
}
.activity-titlebar {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 24px;
  margin: 26px 0 30px;
}
.activity-titlebar h1 {
  margin: 0;
  font-size: 32px;
}
.activity-meta {
  margin: 9px 0 0;
  color: #849089;
  font:
    12px Consolas,
    monospace;
}
.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: #21588f;
  font-size: 12px;
  font-weight: 650;
  white-space: nowrap;
}
.status-badge i {
  width: 7px;
  height: 7px;
  background: #2e73b8;
  border-radius: 50%;
}
.status-badge--open {
  color: #0f7656;
}
.status-badge--open i {
  background: #159a70;
}
.status-badge--ended {
  color: #a8403b;
}
.status-badge--ended i {
  background: #d35c55;
}
.management-layout {
  display: grid;
  grid-template-columns: 232px minmax(0, 1fr);
  min-height: 520px;
  background: #fff;
  border: 1px solid #dfe5e2;
  border-radius: 6px;
  overflow: hidden;
}
.management-sidebar {
  padding: 22px 14px;
  background: #f8faf9;
  border-right: 1px solid #e4e9e6;
}
.sidebar-activity {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 4px 10px 24px;
  border-bottom: 1px solid #e4e9e6;
}
.sidebar-label,
.panel-kicker {
  color: #147d64;
  font-size: 11px;
  font-weight: 750;
  letter-spacing: 1.2px;
}
.sidebar-activity strong {
  color: #17211e;
  font-size: 15px;
  line-height: 1.4;
}
.sidebar-activity span:last-child {
  color: #849089;
  font-size: 12px;
  line-height: 1.5;
}
.management-sidebar nav {
  display: grid;
  gap: 4px;
  padding-top: 18px;
}
.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 11px 10px;
  color: #53615a;
  background: transparent;
  border: 0;
  border-radius: 4px;
  text-align: left;
  font-size: 13px;
  cursor: pointer;
}
.nav-item--active {
  color: #0f6652;
  background: #e4f3ee;
  font-weight: 650;
}
.nav-item--disabled {
  color: #a5aea9;
  cursor: not-allowed;
}
.nav-icon {
  width: 18px;
  color: currentColor;
  font-size: 17px;
  text-align: center;
}
.management-content {
  padding: 30px 34px;
}
.content-heading {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 16px;
  margin-bottom: 24px;
}
.content-heading h2 {
  margin: 0;
  font-size: 22px;
}
.content-hint {
  color: #849089;
  font-size: 12px;
}
.entry-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 280px;
  gap: 18px;
}
.entry-panel {
  min-height: 330px;
  padding: 25px;
  border: 1px solid #dfe5e2;
  border-radius: 5px;
}
.entry-panel h3 {
  margin: 16px 0 8px;
  font-size: 20px;
}
.entry-panel p {
  margin: 0;
  color: #718078;
  font-size: 13px;
  line-height: 1.7;
}
.address-box {
  overflow-wrap: anywhere;
  margin-top: 28px;
  padding: 15px;
  color: #0f6652;
  background: #edf7f4;
  border: 1px solid #c7e3db;
  border-radius: 4px;
  font:
    12px Consolas,
    monospace;
  line-height: 1.6;
}
.panel-actions {
  display: flex;
  gap: 10px;
  margin-top: 18px;
}
.qr-panel {
  display: flex;
  flex-direction: column;
  align-items: center;
}
.qr-panel .panel-kicker {
  align-self: flex-start;
}
.qr-frame {
  display: grid;
  place-items: center;
  width: 220px;
  height: 220px;
  margin: 20px 0 12px;
  background: #fff;
}
.qr-frame img {
  display: block;
  width: 100%;
  height: 100%;
}
.qr-loading {
  width: 28px;
  height: 28px;
  border: 3px solid #d9ebe6;
  border-top-color: #147d64;
  border-radius: 50%;
  animation: spin 800ms linear infinite;
}
.download-button {
  color: #0f6652;
}
.entry-note {
  margin-top: 18px;
  color: #849089;
  font-size: 12px;
}
.entry-note span {
  margin-right: 6px;
  color: #159a70;
  font-size: 8px;
}
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
@media (max-width: 800px) {
  .management-page {
    width: min(100% - 32px, 1280px);
  }
  .management-layout {
    grid-template-columns: 1fr;
  }
  .management-sidebar {
    border-right: 0;
    border-bottom: 1px solid #e4e9e6;
  }
  .management-sidebar nav {
    grid-template-columns: repeat(3, 1fr);
  }
  .entry-grid {
    grid-template-columns: 1fr;
  }
  .qr-panel {
    min-height: 300px;
  }
  .activity-titlebar {
    align-items: flex-start;
    flex-direction: column;
  }
}
@media (max-width: 480px) {
  .management-content {
    padding: 24px 18px;
  }
  .entry-panel {
    padding: 20px;
  }
  .panel-actions {
    flex-direction: column;
  }
  .panel-actions .el-button {
    width: 100%;
    min-height: 44px;
  }
  .management-sidebar nav {
    grid-template-columns: 1fr;
  }
  .nav-item {
    min-height: 44px;
  }
}
</style>
