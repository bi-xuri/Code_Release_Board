<template>
  <section>
    <div class="toolbar">
      <div>
        <h1>版本列表</h1>
        <p class="meta">按发布时间排序，包含 stable / beta / latest 标识</p>
      </div>
      <el-button :icon="ArrowLeft" @click="$router.push('/')">返回项目</el-button>
    </div>
    <el-input v-model="q" clearable placeholder="搜索版本号或标题" style="max-width: 420px; margin-bottom: 16px" @keyup.enter="load">
      <template #append>
        <el-button :icon="Search" @click="load" />
      </template>
    </el-input>
    <el-table :data="releases" v-loading="loading" row-key="id" @row-click="openRelease">
      <el-table-column prop="version" label="版本号" min-width="140" />
      <el-table-column prop="title" label="标题" min-width="180" />
      <el-table-column label="标识" width="170">
        <template #default="{ row }">
          <el-tag v-if="row.is_latest" type="success" size="small">latest</el-tag>
          <el-tag :type="row.release_type === 'beta' ? 'warning' : 'primary'" size="small" style="margin-left: 6px">
            {{ row.release_type }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="repository_name" label="来源仓库" min-width="160" />
      <el-table-column label="发布时间" width="190">
        <template #default="{ row }">{{ row.released_at ? formatDate(row.released_at) : '-' }}</template>
      </el-table-column>
    </el-table>
  </section>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, Search } from 'lucide-vue-next'
import { publicApi } from '../../api/public'

const route = useRoute()
const router = useRouter()
const loading = ref(false)
const releases = ref([])
const q = ref('')
const formatDate = (value) => new Date(value).toLocaleString()

async function load() {
  loading.value = true
  try {
    const { data } = await publicApi.releases(route.params.id, { q: q.value })
    releases.value = data
  } finally {
    loading.value = false
  }
}

function openRelease(row) {
  router.push(`/releases/${row.id}`)
}

onMounted(load)
</script>
