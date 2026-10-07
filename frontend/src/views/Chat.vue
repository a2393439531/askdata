<!-- 智能问数：核心问答页 -->
<!-- 模型选择 → 快捷模板 → 提问 → 解读 + 图表 + 数据表 + SQL -->
<template>
  <div class="chat-page">
    <!-- 提问区 -->
    <el-card class="ask-card" shadow="never">
      <el-row :gutter="12" class="ask-row">
        <el-col :span="6">
          <el-select v-model="model" placeholder="选择模型" style="width: 100%">
            <el-option
              v-for="m in models"
              :key="m.id"
              :value="m.id"
              :disabled="!m.configured"
              :label="m.configured ? m.name : `${m.name}（未配置 Key）`"
            />
          </el-select>
        </el-col>
        <el-col :span="6">
          <el-select v-model="chartPref" placeholder="图表偏好" style="width: 100%">
            <el-option label="自动选择" value="auto" />
            <el-option label="柱状图" value="bar" />
            <el-option label="折线图" value="line" />
            <el-option label="饼图" value="pie" />
            <el-option label="仅表格" value="table" />
          </el-select>
        </el-col>
        <el-col :span="4">
          <el-input-number v-model="limit" :min="1" :max="5000" placeholder="行数上限" style="width: 100%" />
        </el-col>
      </el-row>

      <!-- 快捷模板：各分组第一条 -->
      <div v-if="quickTemplates.length" class="quick-row">
        <span class="quick-label">快捷提问：</span>
        <el-tag
          v-for="t in quickTemplates"
          :key="t.id"
          class="quick-chip"
          effect="plain"
          @click="askWith(t.question)"
        >
          {{ t.title }}
        </el-tag>
      </div>

      <el-input
        v-model="question"
        type="textarea"
        :rows="3"
        placeholder="例如：各部门在职人数是多少？（Ctrl + Enter 发送）"
        class="question-input"
        @keydown.ctrl.enter="askWith()"
      />
      <div class="ask-actions">
        <el-button type="primary" :loading="loading" @click="askWith()">
          {{ loading ? 'AI 分析中…' : '发送提问' }}
        </el-button>
      </div>
    </el-card>

    <!-- 错误提示：后端返回 status=error 时友好展示（如未配置 Key） -->
    <el-alert
      v-if="errorMsg"
      :title="errorMsg"
      type="error"
      show-icon
      closable
      class="error-alert"
      @close="errorMsg = ''"
    />

    <!-- 结果区 -->
    <el-card v-if="result" class="result-card" shadow="never">
      <template #header>
        <div class="result-header">
          <span class="result-question">Q：{{ result.question }}</span>
          <el-space>
            <el-tag size="small">{{ modelName(result.model) }}</el-tag>
            <el-tag size="small" type="success">{{ result.row_count }} 行</el-tag>
            <el-tag size="small" type="info">{{ formatElapsed(result.elapsed_ms) }}</el-tag>
            <el-button size="small" type="primary" plain @click="exportCsv">导出 CSV</el-button>
            <el-button
              size="small"
              :type="isFavorite ? 'warning' : 'default'"
              plain
              @click="toggleFavorite"
            >
              {{ isFavorite ? '★ 已收藏' : '☆ 收藏' }}
            </el-button>
          </el-space>
        </div>
      </template>

      <!-- 一句话解读 -->
      <el-alert
        v-if="result.interpretation"
        :title="result.interpretation"
        type="success"
        :closable="false"
        show-icon
        class="interpretation"
      />

      <!-- 图表手动切换 -->
      <div class="chart-switch">
        <span class="switch-label">图表类型：</span>
        <el-radio-group v-model="viewChartType" size="small">
          <el-radio-button label="bar">柱状图</el-radio-button>
          <el-radio-button label="line">折线图</el-radio-button>
          <el-radio-button label="pie">饼图</el-radio-button>
          <el-radio-button label="table">表格</el-radio-button>
        </el-radio-group>
      </div>

      <ChartView
        :chart-type="viewChartType"
        :columns="result.columns"
        :rows="result.rows"
      />

      <!-- 数据表 -->
      <el-divider>数据明细</el-divider>
      <el-table :data="tableRows" border stripe style="width: 100%" max-height="400">
        <el-table-column type="index" label="#" width="55" />
        <el-table-column
          v-for="col in result.columns"
          :key="col"
          :prop="col"
          :label="col"
          show-overflow-tooltip
          min-width="120"
        />
      </el-table>

      <!-- 查看 SQL -->
      <el-collapse class="sql-collapse">
        <el-collapse-item title="查看生成的 SQL" name="sql">
          <pre class="sql-text">{{ result.sql }}</pre>
        </el-collapse-item>
      </el-collapse>
    </el-card>

    <!-- 空状态 -->
    <el-empty v-if="!result && !loading" description="在上方输入问题，开始智能问数" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import request from '@/utils/request'
import ChartView from '@/components/ChartView.vue'
import { useAskStore } from '@/stores/ask'

const askStore = useAskStore()

const question = ref('')
const model = ref('deepseek')
const chartPref = ref('auto')
const limit = ref(100)
const models = ref([])
const quickTemplates = ref([])
const loading = ref(false)
const result = ref(null)
const errorMsg = ref('')
const viewChartType = ref('bar')
const isFavorite = ref(false)

// 毫秒耗时格式化
const formatElapsed = (ms) => {
  if (ms === null || ms === undefined) return '-'
  return ms < 1000 ? `${ms} ms` : `${(ms / 1000).toFixed(2)} s`
}

// 模型 id 转中文名
const modelName = (id) => {
  const m = models.value.find((x) => x.id === id)
  return m ? m.name : id
}

// 结果表格行对象
const tableRows = computed(() => {
  if (!result.value) return []
  return result.value.rows.map((row) => {
    const obj = {}
    result.value.columns.forEach((col, i) => {
      obj[col] = row[i]
    })
    return obj
  })
})

// 拉取可用模型：未 configured 的置灰并提示"未配置 Key"
const loadModels = async () => {
  try {
    const data = await request.get('/models')
    models.value = data
    const firstOk = data.find((m) => m.configured)
    if (firstOk) model.value = firstOk.id
    else if (data.length) model.value = data[0].id
  } catch (e) {
    // 模型列表拉取失败时保留默认 deepseek，不阻塞提问
  }
}

// 拉取模板：每组取第一条作为快捷提问
const loadTemplates = async () => {
  try {
    const data = await request.get('/templates')
    const chips = []
    for (const g of data.groups || []) {
      if (g.items && g.items.length) chips.push(g.items[0])
    }
    quickTemplates.value = chips.slice(0, 8)
  } catch (e) {
    // 模板拉取失败不阻塞主流程
  }
}

// 发送提问（可直接传入问题文本，快捷模板用）
const askWith = async (q) => {
  const text = (q || question.value || '').trim()
  if (!text) {
    ElMessage.warning('请先输入问题')
    return
  }
  question.value = text
  loading.value = true
  errorMsg.value = ''
  result.value = null
  try {
    const res = await request.post('/chat/ask', {
      question: text,
      model: model.value,
      chart: chartPref.value,
      limit: limit.value
    })
    if (res.status === 'error') {
      // 后端业务错误（如模型 Key 未配置）：友好展示文案
      errorMsg.value = res.error || '查询失败，请稍后重试'
      return
    }
    result.value = res
    isFavorite.value = !!res.is_favorite
    viewChartType.value = res.chart_type || 'bar'
  } catch (e) {
    errorMsg.value =
      (e.response && e.response.data && e.response.data.detail) || '请求失败，请检查网络或稍后重试'
  } finally {
    loading.value = false
  }
}

// 导出 CSV：后端返回文件流，前端触发下载
const exportCsv = async () => {
  if (!result.value || !result.value.id) {
    ElMessage.warning('暂无可导出的结果')
    return
  }
  try {
    const blob = await request.post(
      '/export/csv',
      { history_id: result.value.id },
      { responseType: 'blob' }
    )
    const url = URL.createObjectURL(new Blob([blob], { type: 'text/csv' }))
    const a = document.createElement('a')
    a.href = url
    a.download = `问数结果_${result.value.id}.csv`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
    ElMessage.success('已开始下载')
  } catch (e) {
    ElMessage.error('导出失败')
  }
}

// 收藏 / 取消收藏
const toggleFavorite = async () => {
  if (!result.value || !result.value.id) return
  try {
    const res = await request.patch(`/chat/history/${result.value.id}/favorite`)
    isFavorite.value = res.is_favorite
    ElMessage.success(isFavorite.value ? '已收藏' : '已取消收藏')
  } catch (e) {
    ElMessage.error('操作失败')
  }
}

onMounted(() => {
  loadModels()
  loadTemplates()
  // 承接"历史重问 / 模板执行"跳转过来的待展示结果
  const { result: pending, question: pq } = askStore.takePending()
  if (pending) {
    result.value = pending
    isFavorite.value = !!pending.is_favorite
    viewChartType.value = pending.chart_type || 'bar'
    if (pq) question.value = pq
  }
})
</script>

<style scoped>
.chat-page {
  max-width: 1100px;
  margin: 0 auto;
}
.ask-card {
  margin-bottom: 16px;
}
.ask-row {
  margin-bottom: 12px;
}
.quick-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}
.quick-label {
  font-size: 13px;
  color: #6b7280;
}
.quick-chip {
  cursor: pointer;
}
.quick-chip:hover {
  border-color: #409eff;
  color: #409eff;
}
.question-input {
  margin-bottom: 12px;
}
.ask-actions {
  text-align: right;
}
.error-alert {
  margin-bottom: 16px;
}
.result-card {
  margin-bottom: 16px;
}
.result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}
.result-question {
  font-weight: 600;
  font-size: 15px;
}
.interpretation {
  margin-bottom: 16px;
}
.chart-switch {
  display: flex;
  align-items: center;
  margin-bottom: 12px;
}
.switch-label {
  font-size: 13px;
  color: #6b7280;
  margin-right: 8px;
}
.sql-collapse {
  margin-top: 12px;
}
.sql-text {
  background: #f6f8fa;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  padding: 12px;
  font-family: Consolas, monospace;
  font-size: 13px;
  white-space: pre-wrap;
  word-break: break-all;
}
</style>
