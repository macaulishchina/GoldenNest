import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/stores/user'

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
        }
      ]
    }
  ]
})

// 路由守卫
router.beforeEach((to, _from, next) => {
  const userStore = useUserStore()
  
  if (to.meta.requiresAuth && !userStore.isLoggedIn) {
    next('/login')
  } else if (!to.meta.requiresAuth && userStore.isLoggedIn && (to.name === 'Login' || to.name === 'Register')) {
    next('/')
  } else {
    next()
  }
})

export default router
