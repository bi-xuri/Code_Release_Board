<template>
  <div class="page-shell">
    <header class="topbar">
      <router-link class="brand" to="/">
        <Boxes :size="22" />
        <span>多仓库版本看板</span>
      </router-link>
      <el-button text @click="$router.push('/admin/repositories')">
        <Lock :size="16" />
        管理后台
      </el-button>
    </header>
    <main class="content">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { Boxes, Lock } from 'lucide-vue-next'
</script>
