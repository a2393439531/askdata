<!-- 应用外壳：登录页只显示内容；其余页面显示顶栏导航 -->
<template>
  <div class="app-root">
    <!-- 登录页：无导航，居中内容 -->
    <router-view v-if="$route.path === '/login'" />
    <!-- 业务页：顶栏 + 内容区 -->
    <el-container v-else class="layout">
      <el-header class="topbar">
        <div class="brand">
          <span class="brand-icon">📊</span>
          <span class="brand-main">askdata</span>
          <span class="brand-sub">员工问数 AI 智能体</span>
        </div>
        <el-menu
          :default-active="$route.path"
          mode="horizontal"
          router
          class="nav-menu"
          background-color="transparent"
        >
          <el-menu-item v-for="item in navItems" :key="item.path" :index="item.path">
            {{ item.label }}
          </el-menu-item>
        </el-menu>
        <div class="user-area">
          <el-tag type="info">{{ userStore.roleLabel }}</el-tag>
          <span class="username">{{ userStore.user && userStore.user.username }}</span>
          <el-button link type="danger" @click="handleLogout">退出</el-button>
        </div>
      </el-header>
      <el-main class="content">
        <router-view />
      </el-main>
    </el-container>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()

// 顶部导航：用户管理 / 审计日志仅管理员可见
const navItems = computed(() => {
  const items = [
    { path: '/chat', label: '智能问数' },
    { path: '/schema', label: '数据表' },
    { path: '/history', label: '历史记录' },
    { path: '/dictionary', label: '数据字典' },
    { path: '/templates', label: '查询模板' }
  ]
  if (userStore.isAdmin) {
    items.push({ path: '/users', label: '用户管理' })
    items.push({ path: '/audit', label: '审计日志' })
  }
  return items
})

// 退出：二次确认后清理登录态并跳登录页
const handleLogout = async () => {
  try {
    await ElMessageBox.confirm('确定要退出登录吗？', '提示', { type: 'warning' })
  } catch {
    return
  }
  await userStore.logout()
  router.push('/login')
}
</script>

<style scoped>
.app-root {
  min-height: 100vh;
}
.layout {
  min-height: 100vh;
}
.topbar {
  display: flex;
  align-items: center;
  background: #fff;
  border-bottom: 1px solid #e5e7eb;
  padding: 0 20px;
  height: 60px;
}
.brand {
  display: flex;
  align-items: center;
  margin-right: 24px;
  white-space: nowrap;
}
.brand-icon {
  font-size: 22px;
  margin-right: 8px;
}
.brand-main {
  font-size: 17px;
  font-weight: 700;
  color: #1f2937;
  letter-spacing: 0.5px;
}
.brand-sub {
  font-size: 12px;
  color: #9ca3af;
  margin-left: 8px;
  white-space: nowrap;
}
.nav-menu {
  flex: 1;
  border-bottom: none;
}
.user-area {
  display: flex;
  align-items: center;
  gap: 10px;
}
.username {
  font-size: 14px;
  color: #4b5563;
}
.content {
  background: #f3f4f6;
  padding: 20px;
}
</style>

<style>
/* 全局：去掉默认边距 */
html,
body {
  margin: 0;
  padding: 0;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC',
    'Microsoft YaHei', sans-serif;
}
</style>
