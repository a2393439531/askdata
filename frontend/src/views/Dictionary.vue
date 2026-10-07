<!-- 数据字典：按表分组的折叠面板，展示字段名/类型/主键/非空/默认值 -->
<template>
  <div class="dict-page">
    <el-input
      v-model="keyword"
      placeholder="搜索表名 / 字段名 / 注释"
      clearable
      class="search-input"
    />
    <el-collapse v-model="activeTables" v-loading="loading">
      <el-collapse-item
        v-for="t in filteredTables"
        :key="t.name"
        :name="t.name"
      >
        <template #title>
          <span class="table-title">🗂 {{ t.name }}</span>
          <span class="table-title-comment">{{ t.comment }}</span>
          <el-tag size="small" type="info" class="ml8">{{ t.column_count }} 字段</el-tag>
        </template>
        <el-table :data="t.columns" border stripe style="width: 100%">
          <el-table-column prop="name" label="字段名" min-width="160" />
          <el-table-column prop="type" label="类型" min-width="120" />
          <el-table-column label="主键" width="80" align="center">
            <template #default="{ row }">
              <el-tag v-if="row.pk" type="danger" size="small">PK</el-tag>
              <span v-else class="dash">-</span>
            </template>
          </el-table-column>
          <el-table-column label="非空" width="80" align="center">
            <template #default="{ row }">
              <span v-if="row.notnull" class="yes">是</span>
              <span v-else class="dash">-</span>
            </template>
          </el-table-column>
          <el-table-column label="默认值" min-width="140">
            <template #default="{ row }">
              <code v-if="row.default !== null && row.default !== undefined">{{ row.default }}</code>
              <span v-else class="dash">-</span>
            </template>
          </el-table-column>
        </el-table>
      </el-collapse-item>
    </el-collapse>
    <el-empty v-if="!loading && filteredTables.length === 0" description="没有匹配的数据表" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import request from '@/utils/request'

const tables = ref([])
const loading = ref(false)
const keyword = ref('')
const activeTables = ref([])

// 关键词过滤：匹配表名、表注释、字段名
const filteredTables = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  if (!kw) return tables.value
  return tables.value.filter(
    (t) =>
      t.name.toLowerCase().includes(kw) ||
      (t.comment && t.comment.toLowerCase().includes(kw)) ||
      (t.columns || []).some((c) => c.name.toLowerCase().includes(kw))
  )
})

const loadOverview = async () => {
  loading.value = true
  try {
    const data = await request.get('/schema/overview')
    tables.value = data.tables || []
    // 默认展开第一张表
    if (tables.value.length) activeTables.value = [tables.value[0].name]
  } catch (e) {
    ElMessage.error('数据字典加载失败')
  } finally {
    loading.value = false
  }
}

onMounted(loadOverview)
</script>

<style scoped>
.dict-page {
  max-width: 1100px;
  margin: 0 auto;
}
.search-input {
  margin-bottom: 16px;
  max-width: 400px;
}
.table-title {
  font-weight: 600;
  font-size: 15px;
}
.table-title-comment {
  color: #6b7280;
  font-size: 13px;
  margin-left: 10px;
}
.ml8 {
  margin-left: 8px;
}
.dash {
  color: #d1d5db;
}
.yes {
  color: #16a34a;
  font-weight: 600;
}
code {
  background: #f3f4f6;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 12px;
}
</style>
