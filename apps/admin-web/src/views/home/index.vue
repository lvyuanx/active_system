<template>
  <div class="admin-shell">
    <header class="topbar">
      <div class="topbar-inner">
        <div class="brand-lockup">
          <span class="brand-mark">A</span>
          <div><strong>ACTIVE</strong><small>活动管理中心</small></div>
        </div>
        <div class="account-area">
          <span class="account-avatar">{{ username.slice(0, 1).toUpperCase() }}</span>
          <div class="account-copy"><strong>{{ username }}</strong><small>超级管理员</small></div>
          <el-button text class="logout-button" @click="logout">退出</el-button>
        </div>
      </div>
    </header>

    <main class="admin-page">
      <section class="page-heading">
        <div>
          <p class="eyebrow">ACTIVITY WORKSPACE</p>
          <h1>选择活动</h1>
          <p class="subtitle">在这里创建活动，并管理每个活动的运行状态。</p>
        </div>
        <el-button type="primary" size="large" class="create-button" @click="openCreateDialog">
          <span class="button-symbol">+</span>创建活动
        </el-button>
      </section>

      <section class="summary-band" aria-label="活动概览">
        <div class="summary-item"><span>全部活动</span><strong>{{ activities.length }}</strong></div>
        <div class="summary-item summary-running"><span>进行中</span><strong>{{ statusCounts.open }}</strong></div>
        <div class="summary-item summary-closed"><span>已关闭</span><strong>{{ statusCounts.closed }}</strong></div>
        <div class="summary-item summary-ended"><span>已结束</span><strong>{{ statusCounts.ended }}</strong></div>
      </section>

      <section class="list-heading">
        <div>
          <h2>活动列表</h2>
          <span>共 {{ activities.length }} 个活动</span>
        </div>
        <el-radio-group v-model="activeFilter" size="large" aria-label="筛选活动状态">
          <el-radio-button value="all">全部</el-radio-button>
          <el-radio-button value="open">进行中</el-radio-button>
          <el-radio-button value="closed">已关闭</el-radio-button>
          <el-radio-button value="ended">已结束</el-radio-button>
        </el-radio-group>
      </section>

      <el-alert
        v-if="error"
        class="page-alert"
        :title="error"
        type="error"
        show-icon
        closable
        @close="error = ''"
      />

      <section v-if="loading" class="activity-grid" aria-label="正在加载活动">
        <el-skeleton v-for="index in 3" :key="index" class="activity-skeleton" animated>
          <template #template>
            <el-skeleton-item variant="text" style="width: 28%" />
            <el-skeleton-item variant="h3" style="width: 66%; margin-top: 28px" />
            <el-skeleton-item variant="text" style="margin-top: 18px" />
            <el-skeleton-item variant="text" style="width: 82%" />
            <el-skeleton-item variant="rect" style="height: 72px; margin-top: 26px" />
          </template>
        </el-skeleton>
      </section>

      <section v-else-if="!filteredActivities.length" class="empty-state">
        <span class="empty-mark">A</span>
        <h2>{{ activities.length ? "当前筛选下没有活动" : "还没有活动" }}</h2>
        <p>{{ activities.length ? "切换状态筛选查看其他活动。" : "创建第一个活动，开始配置活动内容。" }}</p>
        <el-button v-if="!activities.length" type="primary" @click="openCreateDialog">创建活动</el-button>
      </section>

      <section v-else class="activity-grid">
        <article
          v-for="activity in filteredActivities"
          :key="activity.activity_id"
          class="activity-card"
          :class="`activity-card--${activity.status}`"
        >
          <div class="card-body">
            <div class="card-top">
              <span class="status-badge" :class="`status-badge--${activity.status}`">
                <i aria-hidden="true"></i>{{ statusLabel(activity.status) }}
              </span>
              <span class="activity-date">创建于 {{ formatDate(activity.created_at) }}</span>
            </div>
            <h3>{{ activity.name }}</h3>
            <p class="description">{{ activity.description || "暂无活动描述" }}</p>
            <dl class="time-list">
              <div><dt>开始时间</dt><dd>{{ formatDate(activity.start_time) }}</dd></div>
              <div><dt>结束时间</dt><dd>{{ formatDate(activity.end_time) }}</dd></div>
            </dl>
          </div>
          <footer class="card-actions">
            <span class="activity-code">ID {{ shortId(activity.activity_id) }}</span>
            <div>
              <el-button
                v-if="activity.status === 'closed'"
                type="success"
                @click="changeStatus(activity, 'open')"
              >开启</el-button>
              <el-button
                v-if="activity.status === 'open'"
                @click="changeStatus(activity, 'close')"
              >关闭</el-button>
              <el-button
                v-if="activity.status !== 'ended'"
                type="danger"
                plain
                @click="changeStatus(activity, 'end')"
              >结束</el-button>
              <span v-else class="ended-tip">不可恢复</span>
            </div>
          </footer>
        </article>
      </section>

      <el-dialog v-model="dialogVisible" class="create-dialog" width="520px" destroy-on-close>
        <template #header>
          <div class="dialog-heading">
            <span class="dialog-mark">+</span>
            <div><h2>创建活动</h2><p>填写基本信息，创建后默认为关闭状态。</p></div>
          </div>
        </template>
        <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
          <el-form-item label="活动名称" prop="name">
            <el-input v-model="form.name" maxlength="200" show-word-limit placeholder="例如：2026 夏季发布会" />
          </el-form-item>
          <el-form-item label="活动描述" prop="description">
            <el-input
              v-model="form.description"
              type="textarea"
              :rows="4"
              maxlength="2000"
              show-word-limit
              placeholder="简要说明活动主题，可选"
            />
          </el-form-item>
          <div class="form-row">
            <el-form-item label="开始时间" prop="start_time">
              <el-date-picker
                v-model="form.start_time"
                type="datetime"
                value-format="YYYY-MM-DDTHH:mm:ss"
                placeholder="可选"
              />
            </el-form-item>
            <el-form-item label="结束时间" prop="end_time">
              <el-date-picker
                v-model="form.end_time"
                type="datetime"
                value-format="YYYY-MM-DDTHH:mm:ss"
                placeholder="可选"
              />
            </el-form-item>
          </div>
        </el-form>
        <template #footer>
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="saving" @click="submitCreate">创建活动</el-button>
        </template>
      </el-dialog>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from "element-plus";
import { useRouter } from "vue-router";
import {
  changeActivityStatus,
  clearToken,
  createActivity,
  getToken,
  listActivities,
  type Activity,
} from "../../api/client";

type ActivityFilter = "all" | Activity["status"];

const router = useRouter();
const activities = ref<Activity[]>([]);
const activeFilter = ref<ActivityFilter>("all");
const loading = ref(true);
const saving = ref(false);
const error = ref("");
const dialogVisible = ref(false);
const formRef = ref<FormInstance>();
const username = localStorage.getItem("active_admin_username") || "超级用户";
const form = reactive({ name: "", description: "", start_time: "", end_time: "" });
const rules: FormRules = {
  name: [{ required: true, message: "请输入活动名称", trigger: "blur" }],
  end_time: [{
    validator: (_rule, value, callback) => {
      if (value && form.start_time && new Date(value) <= new Date(form.start_time)) {
        callback(new Error("结束时间必须晚于开始时间"));
      } else callback();
    },
    trigger: "change",
  }],
};

const statusCounts = computed(() => ({
  open: activities.value.filter((item) => item.status === "open").length,
  closed: activities.value.filter((item) => item.status === "closed").length,
  ended: activities.value.filter((item) => item.status === "ended").length,
}));
const filteredActivities = computed(() => activeFilter.value === "all"
  ? activities.value
  : activities.value.filter((item) => item.status === activeFilter.value));

const loadActivities = async () => {
  loading.value = true;
  error.value = "";
  try { activities.value = await listActivities(); }
  catch (err) { error.value = err instanceof Error ? err.message : "活动加载失败"; }
  finally { loading.value = false; }
};
const openCreateDialog = () => {
  Object.assign(form, { name: "", description: "", start_time: "", end_time: "" });
  dialogVisible.value = true;
};
const submitCreate = async () => {
  if (!formRef.value || !(await formRef.value.validate().catch(() => false))) return;
  saving.value = true;
  try {
    await createActivity({
      name: form.name.trim(),
      description: form.description.trim() || null,
      start_time: form.start_time || null,
      end_time: form.end_time || null,
    });
    ElMessage.success("活动创建成功");
    dialogVisible.value = false;
    activeFilter.value = "all";
    await loadActivities();
  } catch (err) { ElMessage.error(err instanceof Error ? err.message : "活动创建失败"); }
  finally { saving.value = false; }
};
const changeStatus = async (activity: Activity, action: "open" | "close" | "end") => {
  try {
    if (action === "end") {
      await ElMessageBox.confirm(
        `确定结束活动“${activity.name}”吗？结束后不能再次开启。`,
        "确认结束",
        { type: "warning" },
      );
    }
    await changeActivityStatus(activity.activity_id, action);
    ElMessage.success("操作成功");
    await loadActivities();
  } catch (err) {
    if (err instanceof Error && err.message !== "cancel") ElMessage.error(err.message);
  }
};
const logout = () => { clearToken(); router.push("/login"); };
const statusLabel = (status: Activity["status"]) => ({ closed: "已关闭", open: "进行中", ended: "已结束" })[status];
const formatDate = (value: string | null) => value
  ? new Date(value).toLocaleString("zh-CN", { hour12: false })
  : "未设置";
const shortId = (id: string) => id.slice(0, 8).toUpperCase();
onMounted(() => { if (getToken()) loadActivities(); });
</script>
