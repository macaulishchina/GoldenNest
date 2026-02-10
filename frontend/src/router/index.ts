import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { fetchUnshownAchievements } from '@/utils/achievement'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'Login',
      component: () => import('@/views/Login.vue'),
      meta: { requiresAuth: false }
    },
    {
      path: '/register',
      name: 'Register',
      component: () => import('@/views/Login.vue'),
      meta: { requiresAuth: false }
    },
    {
      path: '/',
      component: () => import('@/views/Layout.vue'),
      meta: { requiresAuth: true },
      children: [
        {
          path: '',
          name: 'Dashboard',
          component: () => import('@/views/Dashboard.vue')
        },
        {
          path: 'equity',
          name: 'Equity',
          component: () => import('@/views/Equity.vue')
        },
        {
          path: 'deposit',
          name: 'Deposit',
          component: () => import('@/views/Deposit.vue')
        },
        {
          path: 'asset',
          name: 'Asset',
          component: () => import('@/views/Asset.vue')
        },
        {
          path: 'investment',
          name: 'Investment',
          component: () => import('@/views/Investment.vue')
        },
        {
          path: 'expense',
          name: 'Expense',
          component: () => import('@/views/Expense.vue')
        },
        {
          path: 'transaction',
          name: 'Transaction',
          component: () => import('@/views/Transaction.vue')
        },
        {
          path: 'family',
          name: 'Family',
          component: () => import('@/views/Family.vue')
        },
        {
          path: 'achievement',
          name: 'Achievement',
          component: () => import('@/views/Achievement.vue')
        },
        {
          path: 'gift',
          name: 'Gift',
          component: () => import('@/views/Gift.vue')
        },
        {
          path: 'vote',
          name: 'Vote',
          component: () => import('@/views/Vote.vue')
        },
        {
          path: 'pet',
          name: 'Pet',
          component: () => import('@/views/Pet.vue')
        },
        {
          path: 'announcement',
          name: 'Announcement',
          component: () => import('@/views/Announcement.vue')
        },
        {
          path: 'report',
          name: 'Report',
          component: () => import('@/views/Report.vue')
        },
        {
          path: 'approval',
          name: 'Approval',
          component: () => import('@/views/Approval.vue')
        },
        {
          path: 'approvals',
          redirect: '/approval'
        },
        {
          path: 'todo',
          name: 'Todo',
          component: () => import('@/views/Todo.vue')
        },
        {
          path: 'calendar',
          name: 'Calendar',
          component: () => import('@/views/Calendar.vue')
        },
        {
          path: 'settings',
          name: 'Settings',
          component: () => import('@/views/Settings.vue')
        }
      ]
    },
    // 404 捕获 - 所有未匹配的路由重定向到首页
    {
      path: '/:pathMatch(.*)*',
      redirect: '/'
    }
  ]
})

// 路由守卫
router.beforeEach(async (to, _from, next) => {
  const userStore = useUserStore()
  
  // 如果需要认证
  if (to.meta.requiresAuth) {
    if (!userStore.isLoggedIn) {
      // 未登录，跳转到登录页并保存原始路径
      next({
        path: '/login',
        query: { redirect: to.fullPath }
      })
      return
    }
    
    // 已登录但用户信息未加载，先加载用户信息
    if (!userStore.user) {
      try {
        await userStore.fetchUser()
      } catch (error) {
        console.error('Failed to load user:', error)
        // 如果加载失败，跳转到登录页
        next('/login')
        return
      }
    }
  }
  
  if (!to.meta.requiresAuth && userStore.isLoggedIn && (to.name === 'Login' || to.name === 'Register')) {
    // 已登录用户访问登录/注册页，重定向到首页
    next('/')
  } else {
    next()
  }
})

// 路由切换后检查未展示的成就
router.afterEach((to) => {
  const userStore = useUserStore()
  
  // 只在用户已登录且不是登录页时检查成就
  if (userStore.isLoggedIn && to.name !== 'Login') {
    // 延迟执行，确保页面已加载
    setTimeout(() => {
      fetchUnshownAchievements()
    }, 300)
  }
})

export default router
