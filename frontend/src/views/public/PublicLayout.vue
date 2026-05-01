<template>
  <div class="page-shell">
    <header class="topbar">
      <router-link class="brand" to="/">
        <Boxes :size="22" />
        <span>多仓库版本看板</span>
      </router-link>
      <div class="topbar-actions">
        <div class="meta" v-if="user">{{ user.display_name || user.username }}</div>
        <el-button text @click="$router.push('/admin/login')">
          <Lock :size="16" />
          管理后台
        </el-button>
        <el-button text @click="logout">
          <LogOut :size="16" />
          退出登录
        </el-button>
      </div>
    </header>
    <main class="content">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { Boxes, Lock, LogOut } from 'lucide-vue-next'

const router = useRouter()
const user = computed(() => {
  const raw = localStorage.getItem('public_user')
  return raw ? JSON.parse(raw) : null
})

function logout() {
  localStorage.removeItem('public_token')
  localStorage.removeItem('public_user')
  router.push('/login')
}
</script>
