<template>
  <section v-loading="loading">
    <div class="toolbar">
      <div>
        <h1>{{ release?.title || release?.version || '版本详情' }}</h1>
        <p class="meta">
          {{ release?.repository_name || '-' }}
          <span v-if="release?.released_at"> · {{ formatDate(release.released_at) }}</span>
        </p>
      </div>
      <el-button :icon="ArrowLeft" @click="$router.back()">返回</el-button>
    </div>

    <el-space v-if="release" wrap style="margin-bottom: 18px">
      <el-tag v-if="release.is_latest" type="success">latest</el-tag>
      <el-tag :type="release.release_type === 'beta' ? 'warning' : 'primary'">{{ release.release_type }}</el-tag>
      <el-tag v-if="release.tag_name" type="info">Tag: {{ release.tag_name }}</el-tag>
      <el-link v-if="release.source_url" :href="release.source_url" target="_blank">来源页面</el-link>
    </el-space>

    <el-card shadow="never" style="margin-bottom: 18px">
      <template #header>发布说明</template>
      <div class="release-text">{{ release?.description || '暂无发布说明' }}</div>
    </el-card>

    <el-card shadow="never">
      <template #header>固件文件</template>
      <el-table :data="release?.assets || []" row-key="id">
        <el-table-column prop="name" label="名称" min-width="220" />
        <el-table-column prop="content_type" label="类型" min-width="140" />
        <el-table-column label="大小" width="120">
          <template #default="{ row }">{{ formatSize(row.file_size) }}</template>
        </el-table-column>
        <el-table-column label="下载" width="110">
          <template #default="{ row }">
            <el-button type="primary" :icon="Download" @click="download(row.id)">下载</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </section>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ArrowLeft, Download } from 'lucide-vue-next'
import { publicApi } from '../../api/public'

const route = useRoute()
const loading = ref(false)
const release = ref(null)
const formatDate = (value) => new Date(value).toLocaleString()
const formatSize = (value) => {
  if (!value) return '-'
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`
  return `${(value / 1024 / 1024).toFixed(1)} MB`
}

async function load() {
  loading.value = true
  try {
    const { data } = await publicApi.release(route.params.id)
    release.value = data
  } finally {
    loading.value = false
  }
}

function download(assetId) {
  window.location.href = publicApi.downloadUrl(assetId)
}

onMounted(load)
</script>
