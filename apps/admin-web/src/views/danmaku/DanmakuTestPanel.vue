<template>
  <section class="test-section" aria-labelledby="danmaku-test-title">
    <header class="test-heading">
      <div>
        <p class="eyebrow">CHATROOM TEST</p>
        <h2 id="danmaku-test-title">真实弹幕测试</h2>
      </div>
      <span class="test-status" :class="{ 'test-status--running': running }">
        <i aria-hidden="true"></i>{{ running ? "测试运行中" : "测试已关闭" }}
      </span>
    </header>
    <p class="test-description">
      可设置测试人员数量和每条弹幕的随机延迟范围。开启后每个测试用户会独立通过真实聊天室发送模拟消息，
      弹幕投屏器和聊天室都会收到；消息发送者会标记为“弹幕测试用户”。
    </p>
    <el-form label-position="top" class="test-form" @submit.prevent="startTest">
      <div class="test-config-grid">
        <el-form-item label="测试人员数量">
          <el-input-number
            v-model="config.user_count"
            :min="1"
            :step="1"
            :disabled="loading || running || starting || stopping"
            controls-position="right"
          >
            <template #suffix>人</template>
          </el-input-number>
        </el-form-item>
        <el-form-item label="每条弹幕最小延迟">
          <el-input-number
            v-model="config.min_delay_seconds"
            :min="0"
            :max="60"
            :step="0.05"
            :precision="2"
            :disabled="loading || running || starting || stopping"
            controls-position="right"
          >
            <template #suffix>秒</template>
          </el-input-number>
        </el-form-item>
        <el-form-item label="每条弹幕最大延迟">
          <el-input-number
            v-model="config.max_delay_seconds"
            :min="0"
            :max="60"
            :step="0.05"
            :precision="2"
            :disabled="loading || running || starting || stopping"
            controls-position="right"
          >
            <template #suffix>秒</template>
          </el-input-number>
        </el-form-item>
      </div>
    </el-form>
    <div class="test-actions">
      <el-button
        type="primary"
        :loading="starting"
        :disabled="loading || running || stopping"
        @click="startTest"
      >
        开启弹幕测试
      </el-button>
      <el-button
        :loading="stopping"
        :disabled="loading || !running"
        @click="stopTest"
      >
        关闭弹幕测试
      </el-button>
    </div>
    <p class="test-runtime">
      当前配置：{{ config.user_count }} 人，每条弹幕间隔 {{ delayRangeLabel }}
    </p>
    <p v-if="error" class="test-error">{{ error }}</p>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import {
  getDanmakuTestStatus,
  startDanmakuTest,
  stopDanmakuTest,
  type DanmakuTestConfig,
} from "../../api/client";

const props = defineProps<{ activityId: string }>();
const loading = ref(true);
const running = ref(false);
const starting = ref(false);
const stopping = ref(false);
const error = ref("");
const config = reactive<DanmakuTestConfig>({
  user_count: 6,
  min_delay_seconds: 0.85,
  max_delay_seconds: 0.85,
});
const delayRangeLabel = computed(() => {
  if (config.min_delay_seconds === config.max_delay_seconds) return `${config.min_delay_seconds} 秒`;
  return `${config.min_delay_seconds} - ${config.max_delay_seconds} 秒`;
});

const applyStatus = (status: Awaited<ReturnType<typeof getDanmakuTestStatus>>) => {
  running.value = status.running;
  Object.assign(config, {
    user_count: status.user_count,
    min_delay_seconds: status.min_delay_seconds,
    max_delay_seconds: status.max_delay_seconds,
  });
};

const loadStatus = async () => {
  loading.value = true;
  error.value = "";
  try {
    applyStatus(await getDanmakuTestStatus(props.activityId));
  } catch (err) {
    error.value = err instanceof Error ? err.message : "无法读取弹幕测试状态";
  } finally {
    loading.value = false;
  }
};
const startTest = async () => {
  if (config.max_delay_seconds < config.min_delay_seconds) {
    error.value = "最大延迟必须大于或等于最小延迟";
    return;
  }
  starting.value = true;
  error.value = "";
  try {
    const response = await startDanmakuTest(props.activityId, { ...config });
    applyStatus(response);
    ElMessage.success("已开启真实聊天室弹幕测试");
  } catch (err) {
    error.value = err instanceof Error ? err.message : "开启弹幕测试失败";
  } finally {
    starting.value = false;
  }
};
const stopTest = async () => {
  stopping.value = true;
  error.value = "";
  try {
    const response = await stopDanmakuTest(props.activityId);
    applyStatus(response);
    ElMessage.success("已关闭真实聊天室弹幕测试");
  } catch (err) {
    error.value = err instanceof Error ? err.message : "关闭弹幕测试失败";
  } finally {
    stopping.value = false;
  }
};

onMounted(loadStatus);
</script>

<style scoped>
.test-section {
  margin-top: 38px;
  padding-top: 26px;
  border-top: 1px solid #dfe5e2;
}

.test-heading {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 12px;
}

.test-heading h2 {
  margin: 0;
  font-size: 22px;
}

.test-status {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  color: #849089;
  font-size: 12px;
  font-weight: 650;
}

.test-status i {
  width: 7px;
  height: 7px;
  background: #a5aea9;
  border-radius: 50%;
}

.test-status--running {
  color: #0f7656;
}

.test-status--running i {
  background: #159a70;
}

.test-description {
  max-width: 720px;
  margin: 0;
  color: #718078;
  font-size: 13px;
  line-height: 1.7;
}

.test-form {
  margin-top: 18px;
}

.test-config-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px 18px;
}

.test-config-grid :deep(.el-input-number) {
  width: 100%;
}

.test-actions {
  display: flex;
  gap: 10px;
  margin-top: 18px;
}

.test-runtime {
  margin: 12px 0 0;
  color: #849089;
  font-size: 12px;
}

.test-error {
  margin: 10px 0 0;
  color: #b53d37;
  font-size: 12px;
}

@media (max-width: 800px) {
  .test-heading {
    align-items: flex-start;
    flex-direction: column;
  }

  .test-actions {
    flex-direction: column;
  }

  .test-config-grid {
    grid-template-columns: 1fr;
  }

  .test-actions .el-button {
    width: 100%;
  }
}
</style>
