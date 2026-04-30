<template>
  <section>
    <div class="toolbar">
      <div>
        <h1>项目列表</h1>
        <p class="meta">查看各仓库同步出的发布版本与固件资产</p>
      </div>
    </div>

    <div class="search-row">
      <el-input v-model="filters.q" clearable placeholder="搜索项目名称" @keyup.enter="load" />
      <el-input v-model="filters.device_model" clearable placeholder="设备型号" @keyup.enter="load" />
      <el-input v-model="filters.version" clearable placeholder="版本号" @keyup.enter="load" />
    </div>
    <div style="margin: 12px 0 20px">
      <el-button type="primary" :icon="Search" @click="load">搜索</el-button>
      <el-button :icon="RefreshCw" @click="reset">重置</el-button>
    </div>

    <el-empty v-if="!loading && projects.length === 0" description="暂无项目，请在后台配置仓库并同步" />
    <div class="grid" v-loading="loading">
      <el-card v-for="project in projects" :key="project.id" shadow="never">
        <div class="title-line">
          <h3>{{ project.name }}</h3>
          <el-tag v-if="project.latest_release" type="success">latest</el-tag>
        </div>
        <p class="meta">{{ project.device_model || '未设置设备型号' }}</p>
        <p>{{ project.description || '暂无项目描述' }}</p>
        <el-divider />
        <div v-if="project.latest_release" class="meta">
          最新版本：{{ project.latest_release.version }}
          <span v-if="project.latest_release.released_at"> · {{ formatDate(project.latest_release.released_at) }}</span>
        </div>
        <template #footer>
          <el-button type="primary" :icon="ChevronRight" @click="$router.push(`/projects/${project.id}`)">
            查看版本
          </el-button>
        </template>
      </el-card>
    </div>
  </section>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ChevronRight, RefreshCw, Search } from 'lucide-vue-next'
import { publicApi } from '../../api/public'

const loading = ref(false)
const projects = ref([])
const filters = reactive({ q: '', device_model: '', version: '' })

const formatDate = (value) => new Date(value).toLocaleString()

async function load() {
  loading.value = true
  try {
    const { data } = await publicApi.projects(filters)
    projects.value = data
  } finally {
    loading.value = false
  }
}

function reset() {
  filters.q = ''
  filters.device_model = ''
  filters.version = ''
  load()
}

onMounted(load)
</script>
