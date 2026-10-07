<!-- 数据表：卡片展示各表的表名 / 注释 / 列数 -->
<template>
  <div class="schema-page">
    <el-row :gutter="16" v-loading="loading">
      <el-col v-for="t in tables" :key="t.name" :xs="24" :sm="12" :md="8" :lg="6">
        <el-card class="table-card" shadow="hover" @click="$router.push('/dictionary')">
          <div class="table-name">🗂 {{ t.name }}</div>
          <div class="table-comment">{{ t.comment || '暂无注释' }}</div>
          <el-divider />
          <div class="table-meta">
            <el-tag size="small" type="info">{{ t.column_count }} 个字段</el-tag>
            <el-button link type="primary" size="small" @click.stop="$router.push('/dictionary')">
              查看字段 →
            </el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>
    <el-empty v-if="!loading && tables.length === 0" description="暂无数据表信息" />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import request from '@/utils/request'

const tables = ref([])
const loading = ref(false)

const loadOverview = async () => {
  loading.value = true
  try {
    const data = await request.get('/schema/overview')
    tables.value = data.tables || []
  } catch (e) {
    ElMessage.error('数据表信息加载失败')
  } finally {
    loading.value = false
  }
}

onMounted(loadOverview)
</script>

<style scoped>
.schema-page {
  max-width: 1200px;
  margin: 0 auto;
}
.table-card {
  margin-bottom: 16px;
  cursor: pointer;
}
.table-name {
  font-size: 16px;
  font-weight: 600;
  color: #1f2937;
  word-break: break-all;
}
.table-comment {
  font-size: 13px;
  color: #6b7280;
  margin-top: 6px;
  min-height: 36px;
}
.table-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
