<template>
  <section>
    <div class="toolbar">
      <div>
        <h1>同步日志</h1>
        <p class="meta">记录每次手动或定时同步的结果</p>
      </div>
      <el-button :icon="RefreshCw" @click="load">刷新</el-button>
    </div>
    <el-table :data="logs" v-loading="loading" row-key="id">
      <el-table-column prop="repository_name" label="仓库" min-width="160" />
      <el-table-column label="状态" width="110">
        <template #default="{ row }"><el-tag :type="row.status === 'success' ? 'success' : row.status === 'failed' ? 'danger' : 'warning'">{{ row.status }}</el-tag></template>
      </el-table-column>
      <el-table-column prop="message" label="消息" min-width="260" show-overflow-tooltip />
      <el-table-column label="开始时间" width="190"><template #default="{ row }">{{ formatDate(row.started_at) }}</template></el-table-column>
      <el-table-column label="结束时间" width="190"><template #default="{ row }">{{ row.finished_at ? formatDate(row.finished_at) : '-' }}</template></el-table-column>
    </el-table>
  </section>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { RefreshCw } from 'lucide-vue-next'
import { adminApi } from '../../api/admin'

const loading = ref(false)
const logs = ref([])
const formatDate = (value) => new Date(value).toLocaleString()
async function load() {
  loading.value = true
  try {
    const { data } = await adminApi.syncLogs()
    logs.value = data
  } finally {
    loading.value = false
  }
}
onMounted(load)
</script>
