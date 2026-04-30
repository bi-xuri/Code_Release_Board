<template>
  <section class="form-wrap">
    <div class="toolbar">
      <div>
        <h1>{{ isEdit ? '编辑仓库' : '新增仓库' }}</h1>
        <p class="meta">Access Token 只会加密保存，不会在页面回显</p>
      </div>
      <el-button :icon="ArrowLeft" @click="$router.push('/admin/repositories')">返回</el-button>
    </div>
    <el-card shadow="never">
      <el-form :model="form" label-width="140px">
        <el-form-item label="项目名称"><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="仓库类型">
          <el-select v-model="form.provider">
            <el-option label="GitHub" value="github" />
            <el-option label="GitLab" value="gitlab" />
            <el-option label="Tencent CNB" value="cnb" />
            <el-option label="Manual Upload" value="manual" />
          </el-select>
        </el-form-item>
        <el-form-item label="仓库地址"><el-input v-model="form.repo_url" :placeholder="repoPlaceholder" /></el-form-item>
        <el-form-item label="API Base URL"><el-input v-model="form.api_base_url" :placeholder="apiPlaceholder" /></el-form-item>
        <el-form-item label="Owner / Group"><el-input v-model="form.owner" /></el-form-item>
        <el-form-item label="Repo / Project"><el-input v-model="form.repo_name" /></el-form-item>
        <el-form-item label="GitLab Project ID"><el-input v-model="form.project_id" placeholder="可填数字 ID 或 group/project" /></el-form-item>
        <el-form-item label="Access Token"><el-input v-model="form.access_token" type="password" show-password placeholder="留空则保持原值" /></el-form-item>
        <el-form-item label="启用"><el-switch v-model="form.enabled" /></el-form-item>
        <el-form-item label="显示源码包">
          <el-switch v-model="form.show_source_archives" />
          <span class="meta" style="margin-left: 10px">显示 GitHub / CNB 默认 Source code 压缩包</span>
        </el-form-item>
        <el-form-item label="同步频率">
          <el-input-number v-model="form.sync_interval_minutes" :min="5" :step="5" />
          <span class="meta" style="margin-left: 10px">分钟</span>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="saving" @click="save">保存</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </section>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft } from 'lucide-vue-next'
import { adminApi } from '../../api/admin'

const route = useRoute()
const router = useRouter()
const isEdit = computed(() => Boolean(route.params.id))
const saving = ref(false)
const form = reactive({
  name: '',
  provider: 'github',
  repo_url: '',
  api_base_url: '',
  owner: '',
  repo_name: '',
  project_id: '',
  access_token: '',
  enabled: true,
  show_source_archives: false,
  sync_interval_minutes: 60
})
const apiPlaceholder = computed(() => {
  if (form.provider === 'gitlab') return 'https://gitlab.com/api/v4'
  if (form.provider === 'github') return 'https://api.github.com'
  if (form.provider === 'cnb') return 'CNB 模式下不需要填写'
  return ''
})
const repoPlaceholder = computed(() => {
  if (form.provider === 'cnb') return 'https://cnb.cool/<group>/<repo>.git'
  return ''
})

async function load() {
  if (!isEdit.value) return
  const { data } = await adminApi.repositories()
  const current = data.find((item) => item.id === Number(route.params.id))
  if (current) Object.assign(form, current, { access_token: '' })
}

async function save() {
  saving.value = true
  try {
    const payload = { ...form }
    if (!payload.access_token) delete payload.access_token
    if (isEdit.value) {
      await adminApi.updateRepository(route.params.id, payload)
    } else {
      await adminApi.createRepository(payload)
    }
    ElMessage.success('已保存')
    router.push('/admin/repositories')
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>
