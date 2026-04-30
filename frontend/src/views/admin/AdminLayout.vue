<template>
  <div class="admin-layout">
    <aside class="sidebar">
      <div class="brand"><Boxes :size="22" /> 发布后台</div>
      <el-menu router :default-active="$route.path">
        <el-menu-item index="/admin/repositories"><Database :size="16" /> 仓库配置</el-menu-item>
        <el-menu-item index="/admin/users"><Users :size="16" /> 用户管理</el-menu-item>
        <el-menu-item index="/admin/sync-logs"><History :size="16" /> 同步日志</el-menu-item>
        <el-menu-item index="/admin/download-logs"><Download :size="16" /> 下载日志</el-menu-item>
      </el-menu>
      <el-button text style="margin: 16px 10px" @click="logout">退出登录</el-button>
    </aside>
    <main class="admin-main">
      <div class="content">
        <router-view />
      </div>
    </main>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { Boxes, Database, Download, History, Users } from 'lucide-vue-next'

const router = useRouter()
function logout() {
  localStorage.removeItem('admin_token')
  router.push('/admin/login')
}
</script>
