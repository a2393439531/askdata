// axios 实例：统一 baseURL、鉴权头、401 跳转登录
import axios from 'axios'

const request = axios.create({
  baseURL: '/api',
  timeout: 120000 // AI 问答可能耗时较长，给 2 分钟
})

// 请求拦截器：带上登录 token
request.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('hr_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// 响应拦截器：直接返回 data；401 清理登录态并跳登录页
request.interceptors.response.use(
  (response) => response.data,
  (error) => {
    if (error.response && error.response.status === 401) {
      localStorage.removeItem('hr_token')
      localStorage.removeItem('hr_user')
      if (window.location.pathname !== '/login') {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

export default request
