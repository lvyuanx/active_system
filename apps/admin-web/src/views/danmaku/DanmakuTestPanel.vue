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
      开启后会通过真实聊天室发送模拟消息，弹幕投屏器和聊天室都会收到；消息发送者会标记为“弹幕测试用户”。
    </p>
    <div class="test-actions">
      <el-button
        type="primary"
        :loading="starting"
        :disabled="loading || running"
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
    <p v-if="error" class="test-error">{{ error }}</p>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import { ElMessage } from "element-plus";
import {
  getDanmakuTestStatus,
  startDanmakuTest,
  stopDanmakuTest,
} from "../../api/client";

const props = defineProps<{ activityId: string }>();
const loading = ref(true);
const running = ref(false);
const starting = ref(false);
const stopping = ref(false);
const error = ref("");

const loadStatus = async () => {
  loading.value = true;
  error.value = "";
  try {
    running.value = (await getDanmakuTestStatus(props.activityId)).running;
  } catch (err) {
    error.value = err instanceof Error ? err.message : "无法读取弹幕测试状态";
  } finally {
    loading.value = false;
  }
};
const startTest = async () => {
  starting.value = true;
  error.value = "";
  try {
    const response = await startDanmakuTest(props.activityId);
    running.value = response.running;
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
    running.value = response.running;
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

.test-actions {
  display: flex;
  gap: 10px;
  margin-top: 18px;
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

  .test-actions .el-button {
    width: 100%;
  }
}
</style>
