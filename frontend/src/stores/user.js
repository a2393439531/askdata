// 用户状态：token、当前用户、登录/登出
// token 与用户信息持久化到 localStorage，刷新页面不丢失
import { defineStore } from 'pinia'
import request from '@/utils/request'

export const useUserStore = defineStore('user', {
  state: () => ({
    token: localStorage.getItem('hr_token') || '',
    user: JSON.parse(localStorage.getItem('hr_user') || 'null')
  }),
  getters: {
    // 是否为管理员（可见用户管理 / 审计日志菜单）
    isAdmin: (state) => ['super_admin', 'admin'].includes(state.user && state.user.role),
    // 角色中文名
    roleLabel: (state) => {
      const map = {
        super_admin: '超级管理员',
        admin: '管理员',
        operator: '操作员',
        readonly: '只读用户'
      }
      return (state.user && map[state.user.role]) || state.user?.role || ''
    }
  },
  actions: {
    // 登录：成功后保存 token 与用户信息
    async login(username, password) {
      const data = await request.post('/auth/login', { username, password })
      this.token = data.access_token
      this.user = data.user
      localStorage.setItem('hr_token', this.token)
      localStorage.setItem('hr_user', JSON.stringify(this.user))
    },
    // 拉取最新用户信息（刷新页面后补数据）
    async fetchMe() {
      const data = await request.get('/auth/me')
      this.user = data
      localStorage.setItem('hr_user', JSON.stringify(this.user))
    },
    // 登出：调后端接口并清理本地状态
    async logout() {
      try {
        await request.post('/auth/logout')
      } catch (e) {
        // 后端登出失败也不阻塞本地清理
      }
      this.token = ''
      this.user = null
      localStorage.removeItem('hr_token')
      localStorage.removeItem('hr_user')
    }
  }
})
