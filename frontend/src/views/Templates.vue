<!-- 查询模板：按分组展示；执行跳问数页；新增/编辑/删除仅管理员可见 -->
<template>
  <div class="templates-page">
    <div class="page-actions" v-if="userStore.isAdmin">
      <el-button type="primary" @click="openDialog()">+ 新增模板</el-button>
    </div>

    <div v-loading="loading">
      <div v-for="g in groups" :key="g.group" class="group-block">
        <h3 class="group-title">📁 {{ g.group }}</h3>
        <el-row :gutter="16">
          <el-col v-for="item in g.items" :key="item.id" :xs="24" :sm="12" :md="8">
            <el-card class="tpl-card" shadow="hover">
              <div class="tpl-title">{{ item.title }}</div>
              <div class="tpl-question">{{ item.question }}</div>
              <div class="tpl-footer">
                <el-tag size="small" type="info">{{ chartLabel(item.chart_type) }}</el-tag>
                <el-space>
                  <el-button type="primary" size="small" @click="execute(item)">执行</el-button>
                  <template v-if="userStore.isAdmin">
                    <el-button size="small" @click="openDialog(item, g.group)">编辑</el-button>
                    <el-button type="danger" size="small" @click="remove(item)">删除</el-button>
                  </template>
                </el-space>
              </div>
            </el-card>
          </el-col>
        </el-row>
      </div>
    </div>
    <el-empty v-if="!loading && groups.length === 0" description="暂无模板" />

    <!-- 新增 / 编辑弹窗 -->
    <el-dialog
      v-model="dialogVisible"
      :title="form.id ? '编辑模板' : '新增模板'"
      width="520px"
    >
      <el-form :model="form" label-width="90px">
        <el-form-item label="分组">
          <el-input v-model="form.group" placeholder="如：人员结构" />
        </el-form-item>
        <el-form-item label="标题">
          <el-input v-model="form.title" placeholder="模板标题" />
        </el-form-item>
        <el-form-item label="问题">
          <el-input
            v-model="form.question"
            type="textarea"
            :rows="3"
            placeholder="模板对应的自然语言问题"
          />
        </el-form-item>
        <el-form-item label="图表类型">
          <el-select v-model="form.chart_type" style="width: 100%">
            <el-option label="自动" value="auto" />
            <el-option label="柱状图" value="bar" />
            <el-option label="折线图" value="line" />
            <el-option label="饼图" value="pie" />
            <el-option label="表格" value="table" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import request from '@/utils/request'
import { useUserStore } from '@/stores/user'
import { useAskStore } from '@/stores/ask'

const router = useRouter()
const userStore = useUserStore()
const askStore = useAskStore()

const groups = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const saving = ref(false)
const form = ref({ id: null, group: '', title: '', question: '', chart_type: 'auto' })

const chartLabel = (t) =>
  ({ auto: '自动', bar: '柱状图', line: '折线图', pie: '饼图', table: '表格' }[t] || t || '自动')

const loadTemplates = async () => {
  loading.value = true
  try {
    const data = await request.get('/templates')
    groups.value = data.groups || []
  } catch (e) {
    ElMessage.error('模板加载失败')
  } finally {
    loading.value = false
  }
}

// 执行模板：调 execute 接口，结果暂存后跳问数页展示
const execute = async (item) => {
  try {
    const res = await request.post(`/templates/${item.id}/execute`)
    if (res.status === 'error') {
      ElMessage.error(res.error || '执行失败')
      return
    }
    askStore.setPending(res, item.question)
    router.push('/chat')
  } catch (e) {
    ElMessage.error('执行失败')
  }
}

// 打开新增 / 编辑弹窗（编辑时带入原分组）
const openDialog = (item, groupName) => {
  if (item) {
    form.value = {
      id: item.id,
      group: groupName || '',
      title: item.title,
      question: item.question,
      chart_type: item.chart_type || 'auto'
    }
  } else {
    form.value = { id: null, group: '', title: '', question: '', chart_type: 'auto' }
  }
  dialogVisible.value = true
}

const save = async () => {
  if (!form.value.title.trim() || !form.value.question.trim()) {
    ElMessage.warning('请填写标题和问题')
    return
  }
  saving.value = true
  try {
    const payload = {
      group: form.value.group.trim() || '默认分组',
      title: form.value.title.trim(),
      question: form.value.question.trim(),
      chart_type: form.value.chart_type
    }
    if (form.value.id) {
      await request.put(`/templates/${form.value.id}`, payload)
      ElMessage.success('已更新')
    } else {
      await request.post('/templates', payload)
      ElMessage.success('已新增')
    }
    dialogVisible.value = false
    loadTemplates()
  } catch (e) {
    ElMessage.error((e.response && e.response.data && e.response.data.detail) || '保存失败')
  } finally {
    saving.value = false
  }
}

const remove = async (item) => {
  try {
    await ElMessageBox.confirm(`确定删除模板「${item.title}」吗？`, '提示', { type: 'warning' })
  } catch {
    return
  }
  try {
    await request.delete(`/templates/${item.id}`)
    ElMessage.success('已删除')
    loadTemplates()
  } catch (e) {
    ElMessage.error('删除失败')
  }
}

onMounted(loadTemplates)
</script>

<style scoped>
.templates-page {
  max-width: 1200px;
  margin: 0 auto;
}
.page-actions {
  margin-bottom: 16px;
  text-align: right;
}
.group-block {
  margin-bottom: 24px;
}
.group-title {
  font-size: 16px;
  margin: 0 0 12px;
  color: #1f2937;
}
.tpl-card {
  margin-bottom: 16px;
}
.tpl-title {
  font-size: 15px;
  font-weight: 600;
  margin-bottom: 8px;
}
.tpl-question {
  font-size: 13px;
  color: #6b7280;
  min-height: 38px;
  margin-bottom: 12px;
}
.tpl-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
