<!-- 历史记录：表格展示问答历史，支持全部/收藏页签与重问/收藏/删除 -->
<template>
  <div class="history-page">
    <el-card shadow="never">
      <el-tabs v-model="activeTab" @tab-change="loadHistory">
        <el-tab-pane label="全部记录" name="all" />
        <el-tab-pane label="我的收藏" name="fav" />
      </el-tabs>

      <el-table :data="records" v-loading="loading" border stripe style="width: 100%">
        <el-table-column prop="question" label="问题" min-width="260" show-overflow-tooltip />
        <el-table-column label="模型" width="120">
          <template #default="{ row }">{{ modelName(row.model) }}</template>
        </el-table-column>
        <el-table-column prop="row_count" label="行数" width="80" />
        <el-table-column label="图表" width="90">
          <template #default="{ row }">{{ chartLabel(row.chart_type) }}</template>
        </el-table-column>
        <el-table-column label="耗时" width="100">
          <template #default="{ row }">{{ formatElapsed(row.elapsed_ms) }}</template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.status === 'success' ? 'success' : 'danger'" size="small">
              {{ row.status === 'success' ? '成功' : '失败' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="收藏" width="70" align="center">
          <template #default="{ row }">
            <span class="star" :class="{ on: row.is_favorite }">★</span>
          </template>
        </el-table-column>
        <el-table-column label="时间" width="170">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="rerun(row)">重问</el-button>
            <el-button link type="warning" size="small" @click="toggleFavorite(row)">
              {{ row.is_favorite ? '取消收藏' : '收藏' }}
            </el-button>
            <el-button link type="danger" size="small" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-empty v-if="!loading && records.length === 0" description="暂无历史记录" />
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import request from '@/utils/request'
import { useAskStore } from '@/stores/ask'

const router = useRouter()
const askStore = useAskStore()

const activeTab = ref('all')
const records = ref([])
const loading = ref(false)

const formatElapsed = (ms) => {
  if (ms === null || ms === undefined) return '-'
  return ms < 1000 ? `${ms} ms` : `${(ms / 1000).toFixed(2)} s`
}

const formatTime = (t) => (t ? String(t).replace('T', ' ').slice(0, 19) : '-')

const modelName = (id) => ({ deepseek: 'DeepSeek', qwen: '通义千问' }[id] || id)
const chartLabel = (t) => ({ bar: '柱状图', line: '折线图', pie: '饼图', table: '表格' }[t] || t || '-')

// 加载历史：收藏页签传 favorite_only=1
const loadHistory = async () => {
  loading.value = true
  try {
    const params = { limit: 100 }
    if (activeTab.value === 'fav') params.favorite_only = 1
    records.value = await request.get('/chat/history', { params })
  } catch (e) {
    ElMessage.error('历史记录加载失败')
  } finally {
    loading.value = false
  }
}

// 重问：调 rerun 接口，把完整结果暂存后跳到问数页展示
const rerun = async (row) => {
  try {
    const res = await request.post(`/chat/history/${row.id}/rerun`)
    if (res.status === 'error') {
      ElMessage.error(res.error || '重问失败')
      return
    }
    askStore.setPending(res, row.question)
    router.push('/chat')
  } catch (e) {
    ElMessage.error('重问失败')
  }
}

// 收藏 / 取消收藏：就地更新星标
const toggleFavorite = async (row) => {
  try {
    const res = await request.patch(`/chat/history/${row.id}/favorite`)
    row.is_favorite = res.is_favorite
    ElMessage.success(res.is_favorite ? '已收藏' : '已取消收藏')
    if (activeTab.value === 'fav' && !res.is_favorite) loadHistory()
  } catch (e) {
    ElMessage.error('操作失败')
  }
}

// 删除：二次确认
const remove = async (row) => {
  try {
    await ElMessageBox.confirm('确定删除这条历史记录吗？', '提示', { type: 'warning' })
  } catch {
    return
  }
  try {
    await request.delete(`/chat/history/${row.id}`)
    ElMessage.success('已删除')
    loadHistory()
  } catch (e) {
    ElMessage.error('删除失败')
  }
}

onMounted(loadHistory)
</script>

<style scoped>
.history-page {
  max-width: 1200px;
  margin: 0 auto;
}
.star {
  color: #d1d5db;
  font-size: 16px;
}
.star.on {
  color: #f59e0b;
}
</style>
