// 暂存一次问答/模板执行/历史重问的结果，供 Chat 页展示
// 用于"历史记录 → 重问"、"模板 → 执行"后跳转到 /chat 并直接渲染结果
import { defineStore } from 'pinia'

export const useAskStore = defineStore('ask', {
  state: () => ({
    pendingResult: null, // 待展示的问答结果
    pendingQuestion: '' // 触发该结果的问题文本
  }),
  actions: {
    setPending(result, question = '') {
      this.pendingResult = result
      this.pendingQuestion = question
    },
    // Chat 页消费后清空，避免重复渲染
    takePending() {
      const r = { result: this.pendingResult, question: this.pendingQuestion }
      this.pendingResult = null
      this.pendingQuestion = ''
      return r
    }
  }
})
