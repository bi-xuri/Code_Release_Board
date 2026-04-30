import { createRouter, createWebHistory } from 'vue-router'
import PublicLayout from '../views/public/PublicLayout.vue'
import ProjectList from '../views/public/ProjectList.vue'
import ProjectReleases from '../views/public/ProjectReleases.vue'
import ReleaseDetail from '../views/public/ReleaseDetail.vue'
import AdminLayout from '../views/admin/AdminLayout.vue'
import Login from '../views/admin/Login.vue'
import Repositories from '../views/admin/Repositories.vue'
import RepositoryForm from '../views/admin/RepositoryForm.vue'
import SyncLogs from '../views/admin/SyncLogs.vue'
import DownloadLogs from '../views/admin/DownloadLogs.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      component: PublicLayout,
      children: [
        { path: '', component: ProjectList },
        { path: 'projects/:id', component: ProjectReleases },
        { path: 'releases/:id', component: ReleaseDetail },
        {
          path: 'download/:assetId',
          beforeEnter: (to) => {
            window.location.href = `/api/public/assets/${to.params.assetId}/download`
            return false
          }
        }
      ]
    },
    { path: '/admin/login', component: Login },
    {
      path: '/admin',
      component: AdminLayout,
      meta: { requiresAuth: true },
      children: [
        { path: '', redirect: '/admin/repositories' },
        { path: 'repositories', component: Repositories },
        { path: 'repositories/create', component: RepositoryForm },
        { path: 'repositories/:id/edit', component: RepositoryForm },
        { path: 'sync-logs', component: SyncLogs },
        { path: 'download-logs', component: DownloadLogs }
      ]
    }
  ]
})

router.beforeEach((to) => {
  if (to.meta.requiresAuth && !localStorage.getItem('admin_token')) {
    return '/admin/login'
  }
})

export default router
