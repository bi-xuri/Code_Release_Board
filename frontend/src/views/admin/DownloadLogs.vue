<template>
  <section>
    <div class="toolbar">
      <div>
        <h1>下载日志</h1>
        <p class="meta">下载接口会记录 IP 与 User-Agent</p>
      </div>
      <el-button :icon="RefreshCw" @click="load">刷新</el-button>
    </div>
    <el-table :data="logs" v-loading="loading" row-key="id">
      <el-table-column prop="asset_name" label="文件" min-width="180" />
      <el-table-column prop="ip_address" label="IP" width="150" />
      <el-table-column prop="user_agent" label="User-Agent" min-width="260" show-overflow-tooltip />
      <el-table-column label="下载时间" width="190"><template #default="{ row }">{{ formatDate(row.downloaded_at) }}</template></el-table-column>
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
    const { data } = await adminApi.downloadLogs()
    logs.value = data
  } finally {
    loading.value = false
  }
}
onMounted(load)
</script>
