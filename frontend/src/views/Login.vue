<!-- 登录页：居中卡片，用户名/密码 + 一键填入测试账号 -->
<template>
  <div class="login-page">
    <el-card class="login-card" shadow="hover">
      <div class="login-title">📊 askdata</div>
      <div class="login-subtitle">员工问数 AI 智能体 · 登录后开始</div>
      <el-form :model="form" label-width="70px" @submit.prevent="handleLogin">
        <el-form-item label="用户名">
          <el-input v-model="form.username" placeholder="请输入用户名" clearable />
        </el-form-item>
        <el-form-item label="密码">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="请输入密码"
            show-password
            clearable
            @keyup.enter="handleLogin"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="loading" style="width: 100%" @click="handleLogin">
            登录
          </el-button>
        </el-form-item>
      </el-form>
      <el-divider>测试账号一键填入（密码均为 Admin@2024）</el-divider>
      <div class="quick-accounts">
        <el-button
          v-for="acc in testAccounts"
          :key="acc.username"
          size="small"
          @click="fillAccount(acc)"
        >
          {{ acc.label }}
        </el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

const form = ref({ username: '', password: '' })
const loading = ref(false)

// 5 个测试账号，点击后填入用户名和密码
const testAccounts = [
  { username: 'superadmin', label: '超级管理员' },
  { username: 'hradmin', label: 'HR总监' },
  { username: 'techadmin', label: '技术总监' },
  { username: 'operator01', label: '操作员' },
  { username: 'auditor', label: '审计员' }
]

const fillAccount = (acc) => {
  form.value.username = acc.username
  form.value.password = 'Admin@2024'
}

// 登录：成功后跳回原目标页（默认 /chat）
const handleLogin = async () => {
  if (!form.value.username || !form.value.password) {
    ElMessage.warning('请输入用户名和密码')
    return
  }
  loading.value = true
  try {
    await userStore.login(form.value.username, form.value.password)
    ElMessage.success('登录成功')
    router.push(route.query.redirect || '/chat')
  } catch (e) {
    ElMessage.error((e.response && e.response.data && e.response.data.detail) || '登录失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}
.login-card {
  width: 420px;
  padding: 10px 6px;
}
.login-title {
  font-size: 22px;
  font-weight: 700;
  text-align: center;
  color: #1f2937;
}
.login-subtitle {
  font-size: 13px;
  text-align: center;
  color: #9ca3af;
  margin: 8px 0 20px;
}
.quick-accounts {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
}
</style>
