// 路由：登录页公开，其余需 token；用户管理/审计日志仅管理员可见
import { createRouter, createWebHistory } from 'vue-router'
import Login from '@/views/Login.vue'
import Chat from '@/views/Chat.vue'
import Schema from '@/views/Schema.vue'
import History from '@/views/History.vue'
import Dictionary from '@/views/Dictionary.vue'
import Templates from '@/views/Templates.vue'
import Users from '@/views/Users.vue'
import Audit from '@/views/Audit.vue'

const routes = [
  { path: '/login', component: Login, meta: { public: true, title: '登录' } },
  { path: '/', redirect: '/chat' },
  { path: '/chat', component: Chat, meta: { title: '智能问数' } },
  { path: '/schema', component: Schema, meta: { title: '数据表' } },
  { path: '/history', component: History, meta: { title: '历史记录' } },
  { path: '/dictionary', component: Dictionary, meta: { title: '数据字典' } },
  { path: '/templates', component: Templates, meta: { title: '查询模板' } },
  { path: '/users', component: Users, meta: { title: '用户管理', admin: true } },
  { path: '/audit', component: Audit, meta: { title: '审计日志', admin: true } },
  { path: '/:pathMatch(.*)*', redirect: '/chat' }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 全局守卫：无 token 跳登录；非管理员访问 admin 页面跳回问数页
router.beforeEach((to) => {
  if (to.meta.public) return true
  const token = localStorage.getItem('hr_token')
  if (!token) return '/login'
  if (to.meta.admin) {
    const user = JSON.parse(localStorage.getItem('hr_user') || 'null')
    if (!['super_admin', 'admin'].includes(user && user.role)) return '/chat'
  }
  return true
})

export default router
