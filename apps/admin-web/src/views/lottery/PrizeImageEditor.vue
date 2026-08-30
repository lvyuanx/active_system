<template>
  <div class="prize-image-editor">
    <div v-if="prize.previewUrl || prize.image_url" class="prize-image-preview">
      <img
        v-if="!prize.imageError"
        :src="prize.previewUrl || mediaURL(prize.image_url) || undefined"
        alt="奖品图片预览"
        @error="markImageError"
      />
      <span v-else>图片无法预览</span>
    </div>
    <label class="image-picker" :class="{ 'is-disabled': !prize.prize_id }">
      <span>{{ prize.imageLoading ? "处理中" : "选择图片" }}</span>
      <input
        type="file"
        accept=".jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp"
        :disabled="!prize.prize_id || prize.imageLoading"
        @change="selectImage"
      />
    </label>
    <el-button
      v-if="prize.image_url || prize.pendingImage"
      text
      type="danger"
      :disabled="prize.imageLoading"
      @click="removeImage"
    >移除图片</el-button>
    <small v-if="prize.imageError" class="prize-image-error">{{ prize.imageError }}</small>
    <small v-else-if="prize.pendingImage" class="prize-image-pending">待保存</small>
    <small v-else-if="!prize.prize_id">保存奖品后可上传图片</small>
  </div>
</template>

<script setup lang="ts">
import { mediaURL } from "../../api/client";
import type { FormPrize } from "./lottery-config-form";

const props = defineProps<{ prize: FormPrize }>();

const selectImage = (event: Event) => {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  input.value = "";
  if (!file) return;
  if (!["image/jpeg", "image/png", "image/webp"].includes(file.type)
    || !/\.(jpe?g|png|webp)$/i.test(file.name)) {
    props.prize.imageError = "仅支持 JPEG、PNG 或 WebP 图片";
    return;
  }
  if (file.size > 5 * 1024 * 1024) {
    props.prize.imageError = "图片大小不能超过 5 MiB";
    return;
  }
  if (props.prize.previewUrl) URL.revokeObjectURL(props.prize.previewUrl);
  props.prize.pendingImage = file;
  props.prize.previewUrl = URL.createObjectURL(file);
  props.prize.imageRemoved = false;
  props.prize.imageError = undefined;
};

const removeImage = () => {
  if (props.prize.previewUrl) URL.revokeObjectURL(props.prize.previewUrl);
  props.prize.pendingImage = undefined;
  props.prize.previewUrl = undefined;
  props.prize.imageRemoved = Boolean(props.prize.image_url);
  props.prize.imageError = undefined;
};

const markImageError = () => {
  props.prize.imageError = "图片加载失败，请重新选择图片";
};
</script>

<style scoped>
.prize-image-editor {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  min-height: 34px;
}

.prize-image-preview {
  display: grid;
  width: 40px;
  height: 40px;
  place-items: center;
  overflow: hidden;
  color: #849089;
  background: #eef4f1;
  border: 1px solid #d5e3dd;
  border-radius: 6px;
  font-size: 10px;
  text-align: center;
}

.prize-image-preview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.image-picker {
  display: inline-flex;
  align-items: center;
  min-height: 30px;
  padding: 0 9px;
  color: #147d64;
  background: #fff;
  border: 1px solid #b9d8cd;
  border-radius: 5px;
  cursor: pointer;
  font-size: 12px;
}

.image-picker input {
  display: none;
}

.image-picker.is-disabled {
  color: #aabbb4;
  border-color: #dfe5e2;
  cursor: not-allowed;
}

.prize-image-editor small {
  color: #849089;
  font-size: 11px;
}

.prize-image-editor .prize-image-error {
  color: #b33c35;
}

.prize-image-editor .prize-image-pending {
  color: #b16c2b;
  font-weight: 650;
}
</style>
