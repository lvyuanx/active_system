<template>
  <div class="activity-management">
    <ActivitySidebar
      :activity="activity"
      :activity-id="activityId"
      active="danmaku"
      :username="username"
    />

    <section class="workspace">
      <header class="workspace-topbar">
        <div class="breadcrumb">
          <span>活动管理</span><b>/</b><span>弹幕工具</span><b>/</b>
          <strong>{{ activity?.name || "加载中" }}</strong>
        </div>
        <span
          class="workspace-status"
          :class="activity ? `workspace-status--${activity.status}` : ''"
        >
          <i aria-hidden="true"></i>{{ activity ? statusLabel(activity.status) : "正在加载" }}
        </span>
      </header>

      <main class="management-page">
        <el-alert v-if="error" :title="error" type="error" show-icon class="page-alert" />
        <el-skeleton v-if="loading" :rows="10" animated />

        <template v-else-if="activity && danmaku">
          <section class="activity-titlebar">
            <div>
              <p class="eyebrow">DANMAKU CONTROL</p>
              <h1>弹幕工具</h1>
              <p class="activity-meta">
                {{ activity.name }} · 设置变更会实时推送到已运行的投屏器
              </p>
            </div>
            <span class="status-badge" :class="`status-badge--${activity.status}`">
              <i aria-hidden="true"></i>{{ statusLabel(activity.status) }}
            </span>
          </section>

          <section class="content-surface danmaku-surface">
            <header class="content-heading">
              <div><p class="eyebrow">DISPLAY SETTINGS</p><h2>播放设置</h2></div>
              <span class="content-hint">保存后即时同步</span>
            </header>

            <el-form
              label-position="top"
              class="danmaku-form"
              @submit.prevent="saveSettings"
            >
              <div class="setting-grid">
                <el-form-item label="轨道数量">
                  <el-input-number
                    v-model="form.track_count"
                    :min="1"
                    :max="12"
                    :step="1"
                    controls-position="right"
                  />
                </el-form-item>
                <el-form-item label="字体大小">
                  <el-input-number
                    v-model="form.font_size"
                    :min="16"
                    :max="96"
                    :step="1"
                    controls-position="right"
                  >
                    <template #suffix>px</template>
                  </el-input-number>
                </el-form-item>
                <el-form-item label="不透明度">
                  <div class="range-control">
                    <el-slider v-model="form.opacity" :min="0.1" :max="1" :step="0.05" />
                    <output>{{ opacityLabel }}</output>
                  </div>
                </el-form-item>
                <el-form-item label="飞行时长">
                  <el-input-number
                    v-model="form.duration_seconds"
                    :min="5"
                    :max="30"
                    :step="1"
                    controls-position="right"
                  >
                    <template #suffix>秒</template>
                  </el-input-number>
                </el-form-item>
                <el-form-item label="显示区域顶部">
                  <div class="range-control">
                    <el-slider v-model="form.display_top" :min="0" :max="80" :step="1" />
                    <output>{{ form.display_top }}%</output>
                  </div>
                </el-form-item>
                <el-form-item label="显示区域底部">
                  <div class="range-control">
                    <el-slider v-model="form.display_bottom" :min="20" :max="100" :step="1" />
                    <output>{{ form.display_bottom }}%</output>
                  </div>
                </el-form-item>
                <el-form-item label="文字颜色">
                  <div class="color-control">
                    <el-color-picker v-model="form.text_color" show-alpha="false" />
                    <code>{{ form.text_color }}</code>
                  </div>
                </el-form-item>
              </div>
              <div class="form-actions">
                <el-button native-type="submit" type="primary" :loading="saving">保存播放设置</el-button>
              </div>
            </el-form>

            <section class="token-section" aria-labelledby="danmaku-token-title">
              <header class="token-heading">
                <div><p class="eyebrow">DESKTOP ACCESS</p><h2 id="danmaku-token-title">投屏器 token</h2></div>
                <el-tooltip content="重新生成 token" placement="top">
                  <el-button
                    :icon="Refresh"
                    :loading="rotating"
                    aria-label="重新生成 token"
                    @click="rotateToken"
                  />
                </el-tooltip>
              </header>
              <el-input
                :model-value="danmaku.token"
                readonly
                aria-label="弹幕工具 token"
              >
                <template #append>
                  <el-tooltip content="复制 token" placement="top">
                    <el-button
                      :icon="CopyDocument"
                      aria-label="复制 token"
                      @click="copyToken"
                    />
                  </el-tooltip>
                </template>
              </el-input>
              <p class="token-meta">当前 token 生成于 {{ formatDate(danmaku.token_created_at) }}</p>
              <el-alert
                title="在弹幕桌面工具中粘贴此 token 并选择投屏显示器；重新生成会立即断开已运行的工具。"
                type="warning"
                :closable="false"
                show-icon
              />
            </section>
          </section>
        </template>
      </main>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { CopyDocument, Refresh } from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { useRoute } from "vue-router";
import {
  getActivity,
  getDanmaku,
  regenerateDanmakuToken,
  updateDanmaku,
  type Activity,
  type DanmakuAdminResponse,
  type DanmakuSettings,
} from "../../api/client";
import ActivitySidebar from "../../components/ActivitySidebar.vue";

const route = useRoute();
const activityId = String(route.params.activityId);
const activity = ref<Activity>();
const danmaku = ref<DanmakuAdminResponse>();
const loading = ref(true);
const saving = ref(false);
const rotating = ref(false);
const error = ref("");
const username = localStorage.getItem("active_admin_username") || "超级用户";
const form = reactive<DanmakuSettings>({
  track_count: 6,
  font_size: 36,
  opacity: 0.9,
  duration_seconds: 12,
  display_top: 10,
  display_bottom: 90,
  text_color: "#FFFFFF",
});

const opacityLabel = computed(() => `${Math.round(form.opacity * 100)}%`);
const statusLabel = (status: Activity["status"]) =>
  ({ closed: "已关闭", open: "进行中", ended: "已结束" })[status];
const formatDate = (value: string) => new Date(value).toLocaleString("zh-CN", { hour12: false });
const applyResponse = (response: DanmakuAdminResponse) => {
  danmaku.value = response;
  Object.assign(form, response.settings);
};
const load = async () => {
  loading.value = true;
  error.value = "";
  try {
    const [currentActivity, currentDanmaku] = await Promise.all([getActivity(activityId), getDanmaku(activityId)]);
    activity.value = currentActivity;
    applyResponse(currentDanmaku);
  } catch (err) {
    error.value = err instanceof Error ? err.message : "弹幕工具加载失败";
  } finally {
    loading.value = false;
  }
};
const saveSettings = async () => {
  if (form.display_bottom <= form.display_top) {
    ElMessage.error("显示区域底部必须大于顶部");
    return;
  }
  saving.value = true;
  try {
    applyResponse(await updateDanmaku(activityId, { ...form }));
    ElMessage.success("弹幕设置已实时同步");
  } catch (err) {
    ElMessage.error(err instanceof Error ? err.message : "保存失败，请稍后重试");
  } finally {
    saving.value = false;
  }
};
const copyToken = async () => {
  if (!danmaku.value) return;
  try {
    await navigator.clipboard.writeText(danmaku.value.token);
    ElMessage.success("token 已复制");
  } catch {
    ElMessage.error("无法访问剪贴板，请手动复制");
  }
};
const rotateToken = async () => {
  try {
    await ElMessageBox.confirm("重新生成后，已运行的弹幕工具会立即断开。", "重新生成 token", {
      confirmButtonText: "重新生成",
      cancelButtonText: "取消",
      type: "warning",
    });
  } catch {
    return;
  }
  rotating.value = true;
  try {
    applyResponse(await regenerateDanmakuToken(activityId));
    ElMessage.success("已生成新的 token");
  } catch (err) {
    ElMessage.error(err instanceof Error ? err.message : "重新生成失败，请稍后重试");
  } finally {
    rotating.value = false;
  }
};

onMounted(load);
</script>

<style scoped>

.activity-titlebar {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24px;
  margin: 0 8px 22px;
}

.activity-titlebar h1,
.content-heading h2,
.token-heading h2 {
  margin: 0;
}

.activity-titlebar h1 {
  font-size: 27px;
}

.content-heading h2,
.token-heading h2 {
  font-size: 22px;
}

.activity-meta {
  margin: 9px 0 0;
  color: #849089;
  font: 12px Consolas, monospace;
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

.danmaku-surface {
  min-height: 540px;
  padding: 28px 30px 30px;
  background: #fff;
  border: 1px solid #dfe5e2;
  border-radius: 12px;
  box-shadow: 0 8px 26px rgb(31 48 41 / 5%);
}

.content-heading,
.token-heading {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
}

.content-heading {
  margin-bottom: 26px;
}

.content-hint {
  color: #849089;
  font-size: 12px;
}

.setting-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px 24px;
}

.setting-grid :deep(.el-input-number) {
  width: 100%;
}

.range-control {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 48px;
  align-items: center;
  gap: 12px;
  width: 100%;
}

.range-control output,
.color-control code {
  color: #53615a;
  font: 12px Consolas, monospace;
}

.range-control output {
  text-align: right;
}

.color-control {
  display: flex;
  align-items: center;
  gap: 12px;
  min-height: 32px;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 14px;
  padding-top: 20px;
  border-top: 1px solid #e7ece9;
}

.token-section {
  margin-top: 38px;
  padding-top: 26px;
  border-top: 1px solid #dfe5e2;
}

.token-heading {
  margin-bottom: 16px;
}

.token-section :deep(.el-input-group__append) {
  padding: 0;
}

.token-section :deep(.el-input-group__append .el-button) {
  min-width: 42px;
  margin: 0;
  border: 0;
}

.token-meta {
  margin: 10px 0 16px;
  color: #849089;
  font-size: 12px;
}

@media (max-width: 800px) {
  .activity-titlebar,
  .content-heading {
    align-items: flex-start;
    flex-direction: column;
  }

  .danmaku-surface {
    padding: 22px 18px;
  }

  .setting-grid {
    grid-template-columns: 1fr;
  }

  .workspace-status {
    display: none;
  }
}
</style>
