<template>
  <div class="activity-management">
    <ActivitySidebar
      :activity="activity"
      :activity-id="activityId"
      active="stickers"
      :username="username"
    />

    <section class="workspace">
      <header class="workspace-topbar">
        <div class="breadcrumb">
          <span>活动管理</span><b>/</b><span>聊天表情包</span><b>/</b>
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
        <el-skeleton v-if="loading" :rows="8" animated />

        <template v-else-if="activity">
          <section class="activity-titlebar">
            <div>
              <p class="eyebrow">CHAT STICKERS</p>
              <h1>聊天表情包</h1>
              <p class="activity-meta">当前活动独立维护，上传后移动端聊天即可使用</p>
            </div>
            <span class="status-badge" :class="`status-badge--${activity.status}`">
              <i aria-hidden="true"></i>{{ statusLabel(activity.status) }}
            </span>
          </section>

          <section class="content-surface sticker-surface">
            <header class="content-heading">
              <div><p class="eyebrow">STICKER LIBRARY</p><h2>表情库</h2></div>
              <span class="content-hint">{{ enabledCount }} 个启用</span>
            </header>

            <div class="upload-bar">
              <label class="upload-picker" :class="{ 'is-disabled': uploading }">
                <span>{{ uploading ? "正在上传" : "选择表情包" }}</span>
                <input
                  type="file"
                  multiple
                  accept=".jpg,.jpeg,.png,.webp,.gif,image/jpeg,image/png,image/webp,image/gif"
                  :disabled="uploading"
                  @change="handleFiles"
                />
              </label>
              <el-button :loading="refreshing" @click="loadStickers">刷新列表</el-button>
              <p>支持 PNG、JPG、WebP、GIF，单文件不超过 5 MiB；名称默认取文件名。</p>
            </div>

            <ul v-if="uploadItems.length" class="upload-results" aria-live="polite">
              <li v-for="item in uploadItems" :key="item.key" class="upload-result">
                <div class="upload-result-preview">
                  <img :src="item.previewUrl" :alt="`${item.name}预览`" />
                </div>
                <div class="upload-result-copy">
                  <strong>{{ item.name }}</strong>
                  <small>{{ item.file.name }} · {{ formatSize(item.file.size) }}</small>
                </div>
                <span class="upload-result-status" :class="`upload-result-status--${item.status}`">
                  {{ uploadStatusLabel(item) }}
                </span>
              </li>
            </ul>

            <el-empty v-if="stickers.length === 0 && !uploading" description="还没有表情包，请先上传" />
            <div v-else class="sticker-grid">
              <article v-for="sticker in stickers" :key="sticker.sticker_id" class="sticker-card">
                <div class="sticker-preview">
                  <img
                    v-if="!failedStickerIds.has(sticker.sticker_id)"
                    :src="mediaURL(sticker.image_url) || undefined"
                    :alt="`${sticker.name}预览`"
                    @error="markStickerError(sticker.sticker_id)"
                  />
                  <span v-else>图片无法预览</span>
                </div>
                <div class="sticker-copy">
                  <strong :title="sticker.name">{{ sticker.name }}</strong>
                  <small>{{ mimeLabel(sticker.mime) }} · {{ formatSize(sticker.size) }}</small>
                </div>
                <div class="sticker-actions">
                  <el-tag size="small" :type="sticker.is_enabled ? 'success' : 'info'">
                    {{ sticker.is_enabled ? "已启用" : "已下架" }}
                  </el-tag>
                  <el-button
                    text
                    :type="sticker.is_enabled ? 'danger' : 'primary'"
                    :loading="busyStickerIds.has(sticker.sticker_id)"
                    @click="toggleSticker(sticker)"
                  >
                    {{ sticker.is_enabled ? "下架" : "恢复" }}
                  </el-button>
                </div>
              </article>
            </div>
          </section>
        </template>
      </main>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { ElMessage } from "element-plus";
import { useRoute } from "vue-router";
import {
  disableChatSticker,
  getActivity,
  listChatStickers,
  mediaURL,
  restoreChatSticker,
  uploadChatSticker,
  type Activity,
  type AdminChatSticker,
} from "../../api/client";
import ActivitySidebar from "../../components/ActivitySidebar.vue";

const MAX_FILE_SIZE = 5 * 1024 * 1024;
const ACCEPTED_MIME_TYPES = new Set(["image/jpeg", "image/png", "image/webp", "image/gif"]);
const ACCEPTED_EXTENSIONS = /\.(jpe?g|png|webp|gif)$/i;
const route = useRoute();
const activityId = String(route.params.activityId);
const username = localStorage.getItem("active_admin_username") || "超级用户";
const activity = ref<Activity>();
const stickers = ref<AdminChatSticker[]>([]);
const loading = ref(true);
const refreshing = ref(false);
const uploading = ref(false);
const error = ref("");
const failedStickerIds = ref(new Set<number>());
const busyStickerIds = ref(new Set<number>());

type UploadStatus = "pending" | "uploading" | "success" | "error";
type UploadItem = {
  key: string;
  file: File;
  name: string;
  previewUrl: string;
  status: UploadStatus;
  message?: string;
};
const uploadItems = ref<UploadItem[]>([]);

const statusLabel = (status: Activity["status"]) =>
  ({ closed: "已关闭", open: "进行中", ended: "已结束" })[status];
const enabledCount = computed(() => stickers.value.filter((sticker) => sticker.is_enabled).length);
const uploadStatusLabel = (item: UploadItem) => ({
  pending: "等待上传",
  uploading: "上传中",
  success: "已上传",
  error: item.message || "上传失败",
}[item.status]);
const formatSize = (size: number) => {
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KiB`;
  return `${(size / (1024 * 1024)).toFixed(1)} MiB`;
};
const fileStem = (filename: string) => filename.replace(/\.[^.]+$/, "").trim();
const mimeLabel = (mime: string) => ({
  "image/jpeg": "JPG",
  "image/png": "PNG",
  "image/webp": "WebP",
  "image/gif": "GIF",
}[mime] || mime);
const loadStickers = async () => {
  refreshing.value = true;
  error.value = "";
  try {
    stickers.value = await listChatStickers(activityId);
  } catch (err) {
    error.value = err instanceof Error ? err.message : "表情包列表加载失败";
  } finally {
    refreshing.value = false;
  }
};
const load = async () => {
  loading.value = true;
  error.value = "";
  try {
    const currentActivity = await getActivity(activityId);
    activity.value = currentActivity;
    await loadStickers();
  } catch (err) {
    error.value = err instanceof Error ? err.message : "聊天表情包加载失败";
  } finally {
    loading.value = false;
  }
};
const validateFile = (file: File) => {
  if (!ACCEPTED_EXTENSIONS.test(file.name)
    || (file.type && !ACCEPTED_MIME_TYPES.has(file.type))) {
    return "仅支持 JPG、PNG、WebP 或 GIF 图片";
  }
  if (file.size > MAX_FILE_SIZE) return "图片大小不能超过 5 MiB";
  return "";
};
const uploadOne = async (item: UploadItem) => {
  const validationError = validateFile(item.file);
  if (validationError) {
    item.status = "error";
    item.message = validationError;
    return;
  }
  item.status = "uploading";
  item.message = undefined;
  try {
    await uploadChatSticker(activityId, item.file, item.name);
    item.status = "success";
  } catch (err) {
    item.status = "error";
    item.message = err instanceof Error ? err.message : "上传失败，请重试";
  }
};
const handleFiles = async (event: Event) => {
  const input = event.target as HTMLInputElement;
  const files = [...(input.files || [])];
  input.value = "";
  if (!files.length) return;
  const items = files.map((file, index) => ({
    key: `${Date.now()}-${index}-${file.name}`,
    file,
    name: fileStem(file.name) || "未命名表情",
    previewUrl: URL.createObjectURL(file),
    status: "pending" as UploadStatus,
  }));
  uploadItems.value = items;
  uploading.value = true;
  for (const item of items) await uploadOne(item);
  uploading.value = false;
  if (items.some((item) => item.status === "success")) await loadStickers();
  if (items.some((item) => item.status === "error")) ElMessage.warning("部分表情包上传失败，请查看逐项结果");
  else ElMessage.success(`已上传 ${items.length} 个表情包`);
};
const toggleSticker = async (sticker: AdminChatSticker) => {
  busyStickerIds.value = new Set(busyStickerIds.value).add(sticker.sticker_id);
  try {
    const updated = sticker.is_enabled
      ? await disableChatSticker(activityId, sticker.sticker_id)
      : await restoreChatSticker(activityId, sticker.sticker_id);
    stickers.value = stickers.value.map((item) => (
      item.sticker_id === updated.sticker_id ? updated : item
    ));
    ElMessage.success(updated.is_enabled ? "表情包已恢复" : "表情包已下架，历史消息仍会保留");
  } catch (err) {
    ElMessage.error(err instanceof Error ? err.message : "表情状态更新失败");
  } finally {
    const next = new Set(busyStickerIds.value);
    next.delete(sticker.sticker_id);
    busyStickerIds.value = next;
  }
};
const markStickerError = (stickerId: number) => {
  failedStickerIds.value = new Set(failedStickerIds.value).add(stickerId);
};

onMounted(load);
onBeforeUnmount(() => uploadItems.value.forEach((item) => URL.revokeObjectURL(item.previewUrl)));
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
.content-heading h2 {
  margin: 0;
}

.activity-titlebar h1 { font-size: 27px; }
.content-heading h2 { font-size: 22px; }

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

.status-badge--open { color: #0f7656; }
.status-badge--open i { background: #159a70; }
.status-badge--ended { color: #a8403b; }
.status-badge--ended i { background: #d35c55; }

.sticker-surface {
  min-height: 540px;
  padding: 28px 30px 30px;
  background: #fff;
  border: 1px solid #dfe5e2;
  border-radius: 12px;
  box-shadow: 0 8px 26px rgb(31 48 41 / 5%);
}

.content-heading {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 24px;
}

.content-hint,
.upload-bar p {
  color: #849089;
  font-size: 12px;
}

.upload-bar {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  padding-bottom: 20px;
  border-bottom: 1px solid #e7ece9;
}

.upload-bar p { flex: 1 1 100%; margin: 0; }

.upload-picker {
  display: inline-flex;
  align-items: center;
  min-height: 32px;
  padding: 0 12px;
  color: #fff;
  background: #147d64;
  border-radius: 5px;
  cursor: pointer;
  font-size: 13px;
}

.upload-picker input { display: none; }
.upload-picker.is-disabled { opacity: 0.6; cursor: not-allowed; }

.upload-results {
  display: grid;
  gap: 8px;
  margin: 18px 0 24px;
  padding: 0;
  list-style: none;
}

.upload-result {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  padding: 8px 10px;
  border: 1px solid #e7ece9;
  border-radius: 8px;
  background: #fbfcfb;
}

.upload-result-preview {
  display: grid;
  flex: 0 0 42px;
  width: 42px;
  height: 42px;
  place-items: center;
  overflow: hidden;
  border-radius: 6px;
  background: #eef4f1;
}

.upload-result-preview img { width: 100%; height: 100%; object-fit: contain; }
.upload-result-copy { display: grid; min-width: 0; gap: 3px; }
.upload-result-copy strong { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.upload-result-copy small { color: #849089; font-size: 11px; }
.upload-result-status { margin-left: auto; font-size: 12px; white-space: nowrap; }
.upload-result-status--success { color: #0f7656; }
.upload-result-status--error { color: #b33c35; }
.upload-result-status--uploading { color: #b16c2b; }

.sticker-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
}

.sticker-card {
  display: grid;
  grid-template-columns: 72px minmax(0, 1fr);
  gap: 10px;
  padding: 12px;
  border: 1px solid #e1e9e5;
  border-radius: 9px;
  background: #fbfcfb;
}

.sticker-preview {
  display: grid;
  grid-row: span 2;
  width: 72px;
  height: 72px;
  place-items: center;
  overflow: hidden;
  color: #849089;
  background: #eef4f1;
  border-radius: 7px;
  font-size: 10px;
  text-align: center;
}

.sticker-preview img { width: 100%; height: 100%; object-fit: contain; }
.sticker-copy { display: grid; min-width: 0; gap: 5px; align-content: center; }
.sticker-copy strong { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.sticker-copy small { color: #849089; font-size: 11px; }
.sticker-actions { display: flex; align-items: center; justify-content: space-between; gap: 6px; }

@media (max-width: 1100px) {
  .sticker-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
}

@media (max-width: 800px) {
  .activity-titlebar { align-items: flex-start; flex-direction: column; }
  .sticker-surface { padding: 22px 18px; }
  .sticker-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .workspace-status { display: none; }
}

@media (max-width: 520px) {
  .sticker-grid { grid-template-columns: 1fr; }
}
</style>
