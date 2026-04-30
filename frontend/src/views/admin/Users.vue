<template>
  <section>
    <div class="toolbar">
      <div>
        <h1>用户管理</h1>
        <p class="meta">管理后台账号、状态和可查看仓库</p>
      </div>
      <el-button type="primary" :icon="UserPlus" @click="openCreate">新增用户</el-button>
    </div>

    <el-table :data="users" v-loading="loading" row-key="id">
      <el-table-column prop="username" label="账号" min-width="130" />
      <el-table-column label="用户信息" min-width="180">
        <template #default="{ row }">
          <div>{{ row.display_name || '-' }}</div>
          <div class="meta">{{ row.email || '-' }}</div>
        </template>
      </el-table-column>
      <el-table-column label="角色" width="110">
        <template #default="{ row }"><el-tag :type="row.role === 'admin' ? 'danger' : 'info'">{{ row.role }}</el-tag></template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }"><el-tag :type="row.is_active ? 'success' : 'info'">{{ row.is_active ? '启用' : '停用' }}</el-tag></template>
      </el-table-column>
      <el-table-column label="可查看仓库" min-width="240">
        <template #default="{ row }">
          <el-space wrap>
            <el-tag v-for="repo in row.repositories" :key="repo.id" type="primary">{{ repo.name }}</el-tag>
            <span v-if="!row.repositories.length" class="meta">未分配</span>
          </el-space>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="170" fixed="right">
        <template #default="{ row }">
          <el-button :icon="Edit" @click="openEdit(row)">编辑</el-button>
          <el-button :icon="Trash2" type="danger" @click="remove(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑用户' : '新增用户'" width="620px">
      <el-form :model="form" label-width="110px">
        <el-form-item label="账号"><el-input v-model="form.username" /></el-form-item>
        <el-form-item label="显示名称"><el-input v-model="form.display_name" /></el-form-item>
        <el-form-item label="邮箱"><el-input v-model="form.email" /></el-form-item>
        <el-form-item label="角色">
          <el-select v-model="form.role">
            <el-option label="管理员" value="admin" />
            <el-option label="普通用户" value="viewer" />
          </el-select>
        </el-form-item>
        <el-form-item :label="editingId ? '重置密码' : '密码'">
          <el-input
            v-model="form.password"
            type="password"
            show-password
            :placeholder="editingId ? '留空则不修改' : ''"
          />
        </el-form-item>
        <el-form-item label="启用"><el-switch v-model="form.is_active" /></el-form-item>
        <el-form-item label="可查看仓库">
          <el-select v-model="form.repository_ids" multiple filterable collapse-tags collapse-tags-tooltip style="width: 100%">
            <el-option
              v-for="repo in repositories"
              :key="repo.id"
              :label="`${repo.name} (${repo.provider})`"
              :value="repo.id"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </section>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Edit, Trash2, UserPlus } from 'lucide-vue-next'
import { adminApi } from '../../api/admin'

const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const editingId = ref(null)
const users = ref([])
const repositories = ref([])
const form = reactive(defaultForm())

function defaultForm() {
  return {
    username: '',
    display_name: '',
    email: '',
    role: 'viewer',
    password: '',
    is_active: true,
    repository_ids: []
  }
}

function resetForm(value = defaultForm()) {
  Object.assign(form, value)
}

async function load() {
  loading.value = true
  try {
    const [{ data: userData }, { data: repoData }] = await Promise.all([adminApi.users(), adminApi.repositories()])
    users.value = userData
    repositories.value = repoData
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editingId.value = null
  resetForm()
  dialogVisible.value = true
}

function openEdit(row) {
  editingId.value = row.id
  resetForm({
    username: row.username,
    display_name: row.display_name || '',
    email: row.email || '',
    role: row.role,
    password: '',
    is_active: row.is_active,
    repository_ids: [...row.repository_ids]
  })
  dialogVisible.value = true
}

async function save() {
  if (!form.username || (!editingId.value && !form.password)) {
    ElMessage.error('请填写账号和密码')
    return
  }
  saving.value = true
  try {
    const payload = { ...form }
    if (editingId.value && !payload.password) delete payload.password
    if (editingId.value) {
      await adminApi.updateUser(editingId.value, payload)
    } else {
      await adminApi.createUser(payload)
    }
    ElMessage.success('已保存')
    dialogVisible.value = false
    load()
  } finally {
    saving.value = false
  }
}

async function remove(row) {
  await ElMessageBox.confirm(`确认删除用户 ${row.username}？`, '删除用户', { type: 'warning' })
  await adminApi.deleteUser(row.id)
  ElMessage.success('已删除')
  load()
}

onMounted(load)
</script>
