<template>
  <main class="login-page">
    <section class="login-brand">
      <div class="brand-lockup brand-lockup--light">
        <span class="brand-mark">A</span>
        <div><strong>ACTIVE</strong><small>活动管理中心</small></div>
      </div>
      <div class="login-brand-copy">
        <p class="eyebrow">ACTIVITY OPERATIONS</p>
        <h1>让每一场活动<br>清晰运行。</h1>
        <div class="brand-rule"><span></span><span></span><span></span></div>
      </div>
      <small class="login-version">ADMIN CONSOLE · 2026</small>
    </section>
    <section class="login-form-area">
      <div class="login-panel">
        <p class="eyebrow">WELCOME BACK</p>
        <h2>管理员登录</h2>
        <p class="subtitle">使用超级管理员账号进入活动工作台。</p>
        <el-form ref="formRef" :model="form" :rules="rules" label-position="top" @submit.prevent="submit">
          <el-form-item label="用户名" prop="username">
            <el-input v-model="form.username" size="large" placeholder="请输入用户名" autocomplete="username" />
          </el-form-item>
          <el-form-item label="密码" prop="password">
            <el-input
              v-model="form.password"
              size="large"
              type="password"
              show-password
              placeholder="请输入密码"
              autocomplete="current-password"
              @keyup.enter="submit"
            />
          </el-form-item>
          <el-alert v-if="error" :title="error" type="error" show-icon :closable="false" />
          <el-button class="login-button" type="primary" size="large" :loading="loading" native-type="submit">
            登录工作台
          </el-button>
        </el-form>
        <p class="permission-note"><span aria-hidden="true">●</span> 仅限超级管理员访问</p>
      </div>
    </section>
  </main>
</template>

<script setup lang="ts">
import { reactive, ref } from "vue";
import type { FormInstance, FormRules } from "element-plus";
import { login } from "../../api/client";
import { useRouter } from "vue-router";

const router = useRouter();
const formRef = ref<FormInstance>();
const loading = ref(false);
const error = ref("");
const form = reactive({ username: "", password: "" });
const rules: FormRules = {
  username: [{ required: true, message: "请输入用户名", trigger: "blur" }],
  password: [{ required: true, message: "请输入密码", trigger: "blur" }],
};
const submit = async () => {
  if (!formRef.value || !(await formRef.value.validate().catch(() => false))) return;
  loading.value = true;
  error.value = "";
  try {
    const result = await login(form.username, form.password);
    localStorage.setItem("active_admin_token", result.access_token);
    localStorage.setItem("active_admin_username", result.username);
    router.push("/");
  } catch (err) { error.value = err instanceof Error ? err.message : "登录失败"; }
  finally { loading.value = false; }
};
</script>
