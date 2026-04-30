<template>
  <div class="page-shell" style="display: grid; place-items: center; padding: 24px">
    <el-card shadow="never" style="width: min(420px, 100%)">
      <template #header>
        <div class="brand"><Lock :size="20" /> 管理员登录</div>
      </template>
      <el-form :model="form" label-position="top" @submit.prevent="login">
        <el-form-item label="用户名">
          <el-input v-model="form.username" autocomplete="username" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="form.password" type="password" autocomplete="current-password" show-password @keyup.enter="login" />
        </el-form-item>
        <el-button type="primary" style="width: 100%" :loading="loading" @click="login">登录</el-button>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Lock } from 'lucide-vue-next'
import { adminApi } from '../../api/admin'

const router = useRouter()
const loading = ref(false)
const form = reactive({ username: 'admin', password: 'admin123' })

async function login() {
  loading.value = true
  try {
    const { data } = await adminApi.login(form)
    localStorage.setItem('admin_token', data.access_token)
    router.push('/admin/repositories')
  } catch {
    ElMessage.error('登录失败')
  } finally {
    loading.value = false
  }
}
</script>
