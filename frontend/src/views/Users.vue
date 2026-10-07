<!-- 用户管理（super_admin）：用户表格 + 新增/编辑弹窗 + 启用禁用 + 删除 -->
<template>
  <div class="users-page">
    <el-card shadow="never">
      <div class="page-actions">
        <el-button type="primary" @click="openDialog()">+ 新增用户</el-button>
      </div>
      <el-table :data="users" v-loading="loading" border stripe style="width: 100%">
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="username" label="用户名" min-width="120" />
        <el-table-column label="角色" width="120">
          <template #default="{ row }">
            <el-tag :type="roleTagType(row.role)" size="small">{{ roleLabel(row.role) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="data_scope" label="数据范围" min-width="140" show-overflow-tooltip />
        <el-table-column prop="employee_id" label="关联员工ID" width="120" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-switch
              v-model="row.is_active"
              @change="toggleStatus(row)"
              :disabled="row.username === 'superadmin'"
            />
          </template>
        </el-table-column>
        <el-table-column label="创建时间" width="170">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="openDialog(row)">编辑</el-button>
            <el-button
              link
              type="danger"
              size="small"
              :disabled="row.username === 'superadmin'"
              @click="remove(row)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 新增 / 编辑弹窗 -->
    <el-dialog v-model="dialogVisible" :title="form.id ? '编辑用户' : '新增用户'" width="560px">
      <el-form :model="form" label-width="110px">
        <el-form-item label="用户名">
          <el-input v-model="form.username" :disabled="!!form.id" placeholder="登录用户名" />
        </el-form-item>
        <el-form-item :label="form.id ? '新密码（留空不改）' : '密码'">
          <el-input v-model="form.password" type="password" show-password placeholder="请输入密码" />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="form.role" style="width: 100%">
            <el-option label="超级管理员" value="super_admin" />
            <el-option label="管理员" value="admin" />
            <el-option label="操作员" value="operator" />
            <el-option label="只读用户" value="readonly" />
          </el-select>
        </el-form-item>
        <el-form-item label="数据范围">
          <el-input v-model="form.data_scope" placeholder="如：all / dept:销售部" />
        </el-form-item>
        <el-form-item label="关联员工ID">
          <el-input v-model="form.employee_id" placeholder="关联的员工编号（可选）" />
        </el-form-item>
        <el-form-item label="允许表白名单">
          <el-input
            v-model="form.allowed_tables"
            type="textarea"
            :rows="2"
            placeholder='JSON 数组，如 ["employees","departments"]，留空表示不限制'
          />
        </el-form-item>
        <el-form-item label="允许字段白名单">
          <el-input
            v-model="form.allowed_columns"
            type="textarea"
            :rows="2"
            placeholder='JSON 对象，如 {"employees":["name","dept"]}，留空表示不限制'
          />
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="form.is_active" />
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
import { ElMessage, ElMessageBox } from 'element-plus'
import request from '@/utils/request'

const users = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const saving = ref(false)
const form = ref({
  id: null,
  username: '',
  password: '',
  role: 'operator',
  data_scope: '',
  employee_id: '',
  allowed_tables: '',
  allowed_columns: '',
  is_active: true
})

const roleLabel = (r) =>
  ({ super_admin: '超级管理员', admin: '管理员', operator: '操作员', readonly: '只读用户' }[r] || r)
const roleTagType = (r) =>
  ({ super_admin: 'danger', admin: 'warning', operator: 'primary', readonly: 'info' }[r] || '')
const formatTime = (t) => (t ? String(t).replace('T', ' ').slice(0, 19) : '-')

const loadUsers = async () => {
  loading.value = true
  try {
    users.value = await request.get('/users')
  } catch (e) {
    ElMessage.error('用户列表加载失败')
  } finally {
    loading.value = false
  }
}

// 白名单字段：数组/对象与 JSON 字符串互转
const stringifyJson = (v) => (v === null || v === undefined || v === '' ? '' : JSON.stringify(v))
const parseJsonField = (text, fieldName) => {
  const t = (text || '').trim()
  if (!t) return null
  try {
    return JSON.parse(t)
  } catch {
    throw new Error(`${fieldName} 不是合法的 JSON`)
  }
}

const openDialog = (row) => {
  if (row) {
    form.value = {
      id: row.id,
      username: row.username,
      password: '',
      role: row.role,
      data_scope: row.data_scope || '',
      employee_id: row.employee_id || '',
      allowed_tables: stringifyJson(row.allowed_tables),
      allowed_columns: stringifyJson(row.allowed_columns),
      is_active: row.is_active
    }
  } else {
    form.value = {
      id: null,
      username: '',
      password: '',
      role: 'operator',
      data_scope: '',
      employee_id: '',
      allowed_tables: '',
      allowed_columns: '',
      is_active: true
    }
  }
  dialogVisible.value = true
}

const save = async () => {
  if (!form.value.username.trim()) {
    ElMessage.warning('请填写用户名')
    return
  }
  if (!form.value.id && !form.value.password) {
    ElMessage.warning('新增用户请设置密码')
    return
  }
  let allowedTables, allowedColumns
  try {
    allowedTables = parseJsonField(form.value.allowed_tables, '允许表白名单')
    allowedColumns = parseJsonField(form.value.allowed_columns, '允许字段白名单')
  } catch (e) {
    ElMessage.warning(e.message)
    return
  }
  saving.value = true
  try {
    const payload = {
      username: form.value.username.trim(),
      role: form.value.role,
      data_scope: form.value.data_scope.trim() || null,
      employee_id: form.value.employee_id.trim() || null,
      allowed_tables: allowedTables,
      allowed_columns: allowedColumns,
      is_active: form.value.is_active
    }
    if (form.value.password) payload.password = form.value.password
    if (form.value.id) {
      await request.put(`/users/${form.value.id}`, payload)
      ElMessage.success('已更新')
    } else {
      await request.post('/users', payload)
      ElMessage.success('已新增')
    }
    dialogVisible.value = false
    loadUsers()
  } catch (e) {
    ElMessage.error((e.response && e.response.data && e.response.data.detail) || '保存失败')
  } finally {
    saving.value = false
  }
}

// 启用 / 禁用
const toggleStatus = async (row) => {
  try {
    await request.patch(`/users/${row.id}/status`, { is_active: row.is_active })
    ElMessage.success(row.is_active ? '已启用' : '已禁用')
  } catch (e) {
    row.is_active = !row.is_active // 失败时回滚开关
    ElMessage.error((e.response && e.response.data && e.response.data.detail) || '操作失败')
  }
}

// 删除：后端做保护校验（如不能删自己/最后一个超管），前端直接展示错误
const remove = async (row) => {
  try {
    await ElMessageBox.confirm(`确定删除用户「${row.username}」吗？`, '提示', { type: 'warning' })
  } catch {
    return
  }
  try {
    await request.delete(`/users/${row.id}`)
    ElMessage.success('已删除')
    loadUsers()
  } catch (e) {
    ElMessage.error((e.response && e.response.data && e.response.data.detail) || '删除失败')
  }
}

onMounted(loadUsers)
</script>

<style scoped>
.users-page {
  max-width: 1200px;
  margin: 0 auto;
}
.page-actions {
  margin-bottom: 16px;
  text-align: right;
}
</style>
