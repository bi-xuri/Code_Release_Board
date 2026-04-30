<template>
  <section>
    <div class="toolbar">
      <div>
        <h1>仓库配置</h1>
        <p class="meta">配置 GitHub / GitLab / CNB 仓库并手动同步发布版本</p>
      </div>
      <el-button type="primary" :icon="Plus" @click="$router.push('/admin/repositories/create')">新增仓库</el-button>
    </div>
    <el-table :data="repositories" v-loading="loading" row-key="id">
      <el-table-column prop="name" label="项目名称" min-width="160" />
      <el-table-column prop="provider" label="类型" width="110" />
      <el-table-column label="仓库" min-width="220">
        <template #default="{ row }">{{ row.owner && row.repo_name ? `${row.owner}/${row.repo_name}` : row.project_id || row.repo_url }}</template>
      </el-table-column>
      <el-table-column label="Token" width="100">
        <template #default="{ row }"><el-tag :type="row.access_token_set ? 'success' : 'info'">{{ row.access_token_set ? '已配置' : '未配置' }}</el-tag></template>
      </el-table-column>
      <el-table-column label="启用" width="90">
        <template #default="{ row }"><el-tag :type="row.enabled ? 'success' : 'info'">{{ row.enabled ? '是' : '否' }}</el-tag></template>
      </el-table-column>
      <el-table-column label="操作" width="260" fixed="right">
        <template #default="{ row }">
          <el-button :icon="RefreshCw" :loading="syncing === row.id" @click="sync(row.id)">同步</el-button>
          <el-button :icon="Edit" @click="$router.push(`/admin/repositories/${row.id}/edit`)">编辑</el-button>
          <el-button :icon="Trash2" type="danger" @click="remove(row.id)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
  </section>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Edit, Plus, RefreshCw, Trash2 } from 'lucide-vue-next'
import { adminApi } from '../../api/admin'

const loading = ref(false)
const syncing = ref(null)
const repositories = ref([])

async function load() {
  loading.value = true
  try {
    const { data } = await adminApi.repositories()
    repositories.value = data
  } finally {
    loading.value = false
  }
}

async function sync(id) {
  syncing.value = id
  try {
    const { data } = await adminApi.syncRepository(id)
    data.status === 'success' ? ElMessage.success(data.message) : ElMessage.error(data.message)
  } finally {
    syncing.value = null
  }
}

async function remove(id) {
  await ElMessageBox.confirm('确认删除该仓库配置？', '删除仓库', { type: 'warning' })
  await adminApi.deleteRepository(id)
  ElMessage.success('已删除')
  load()
}

onMounted(load)
</script>
