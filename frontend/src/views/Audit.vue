<!-- 审计日志：按用户名/动作筛选 + 分页表格，详情过长截断并 tooltip 展示 -->
<template>
  <div class="audit-page">
    <el-card shadow="never">
      <!-- 筛选区 -->
      <el-form :inline="true" :model="filters" class="filter-form">
        <el-form-item label="用户名">
          <el-input v-model="filters.username" placeholder="按用户名筛选" clearable />
        </el-form-item>
        <el-form-item label="动作">
          <el-select
            v-model="filters.action"
            placeholder="按动作筛选"
            clearable
            filterable
            allow-create
            style="width: 200px"
          >
            <el-option v-for="a in actionOptions" :key="a" :label="a" :value="a" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="query">查询</el-button>
          <el-button @click="reset">重置</el-button>
        </el-form-item>
      </el-form>

      <!-- 日志表格 -->
      <el-table :data="items" v-loading="loading" border stripe style="width: 100%">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="username" label="用户" width="130" />
        <el-table-column prop="action" label="动作" width="150" show-overflow-tooltip />
        <el-table-column label="详情" min-width="240">
          <template #default="{ row }">
            <el-tooltip :content="String(row.detail || '')" placement="top" :disabled="!row.detail || String(row.detail).length <= 60">
              <span class="detail-text">{{ truncate(row.detail) }}</span>
            </el-tooltip>
          </template>
        </el-table-column>
        <el-table-column prop="ip" label="IP" width="130" />
        <el-table-column label="耗时" width="100">
          <template #default="{ row }">{{ formatElapsed(row.elapsed_ms) }}</template>
        </el-table-column>
        <el-table-column label="结果" width="90">
          <template #default="{ row }">
            <el-tag :type="row.result === 'success' ? 'success' : 'danger'" size="small">
              {{ resultLabel(row.result) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="时间" width="170">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[20, 50, 100]"
        layout="total, sizes, prev, pager, next, jumper"
        class="pagination"
        @size-change="query"
        @current-change="query"
      />
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import request from '@/utils/request'

const filters = ref({ username: '', action: '' })
const items = ref([])
const loading = ref(false)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)

// 常见审计动作候选（支持手动输入任意动作）
const actionOptions = [
  'login',
  'logout',
  'chat_ask',
  'chat_rerun',
  'export_csv',
  'favorite',
  'template_execute',
  'template_create',
  'template_update',
  'template_delete',
  'user_create',
  'user_update',
  'user_delete',
  'user_status'
]

const truncate = (text, len = 60) => {
  const s = String(text || '')
  return s.length > len ? s.slice(0, len) + '…' : s || '-'
}
const formatElapsed = (ms) => {
  if (ms === null || ms === undefined) return '-'
  return ms < 1000 ? `${ms} ms` : `${(ms / 1000).toFixed(2)} s`
}
const formatTime = (t) => (t ? String(t).replace('T', ' ').slice(0, 19) : '-')
const resultLabel = (r) => (r === 'success' ? '成功' : r === 'fail' ? '失败' : r || '-')

const query = async () => {
  loading.value = true
  try {
    const params = { page: page.value, page_size: pageSize.value }
    if (filters.value.username.trim()) params.username = filters.value.username.trim()
    if (filters.value.action) params.action = filters.value.action
    const data = await request.get('/audit', { params })
    items.value = data.items || []
    total.value = data.total || 0
  } catch (e) {
    ElMessage.error('审计日志加载失败')
  } finally {
    loading.value = false
  }
}

const reset = () => {
  filters.value = { username: '', action: '' }
  page.value = 1
  query()
}

onMounted(query)
</script>

<style scoped>
.audit-page {
  max-width: 1300px;
  margin: 0 auto;
}
.filter-form {
  margin-bottom: 8px;
}
.detail-text {
  font-size: 13px;
  color: #4b5563;
  cursor: default;
}
.pagination {
  margin-top: 16px;
  justify-content: flex-end;
}
</style>
