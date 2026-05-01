<template>
  <div class="page-shell public-login-shell">
    <el-card shadow="never" class="public-login-card">
      <template #header>
        <div class="brand">
          <Boxes :size="20" />
          前台用户登录
        </div>
      </template>
      <el-form :model="form" label-position="top" @submit.prevent="login">
        <el-form-item label="用户名">
          <el-input v-model="form.username" autocomplete="username" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="form.password" type="password" show-password autocomplete="current-password" @keyup.enter="login" />
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
import { Boxes } from 'lucide-vue-next'
import { publicApi } from '../../api/public'

const router = useRouter()
const loading = ref(false)
const form = reactive({ username: '', password: '' })

async function login() {
  loading.value = true
  try {
    const { data } = await publicApi.login(form)
    localStorage.setItem('public_token', data.access_token)
    localStorage.setItem('public_user', JSON.stringify(data.user))
    router.push('/')
  } catch {
    ElMessage.error('登录失败')
  } finally {
    loading.value = false
  }
}
</script>
