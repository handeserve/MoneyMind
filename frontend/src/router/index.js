import { createRouter, createWebHistory } from 'vue-router'
import FinancialOverview from '@/views/FinancialOverview.vue'
import Expenses from '@/views/Expenses.vue'
import Import from '@/views/Import.vue'
import Settings from '@/views/Settings.vue'



const routes = [
  {
    path: '/',
    redirect: '/financial-overview'
  },
  {
    path: '/financial-overview',
    name: 'FinancialOverview',
    component: FinancialOverview,
    meta: {
      title: '财务概览'
    }
  },
  {
    path: '/expenses',
    name: 'Expenses',
    component: Expenses,
    meta: {
      title: '支出记录'
    }
  },
  {
    path: '/import',
    name: 'Import',
    component: Import,
    meta: {
      title: '数据导入'
    }
  },
  {
    path: '/settings',
    name: 'Settings',
    component: Settings,
    meta: {
      title: '系统设置'
    }
  },


]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 设置页面标题
router.beforeEach((to, from, next) => {
  document.title = to.meta.title ? `${to.meta.title} - MoneyMind` : 'MoneyMind'
  next()
})

export default router 