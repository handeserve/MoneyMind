import request from '@/utils/request'

// 财务概览相关API
export function getFinancialOverview(startDate, endDate) {
  return request({
    url: '/api/v1/financial-overview',
    method: 'get',
    params: {
      start_date: startDate,
      end_date: endDate
    }
  })
}

export function getSummaryStats(params) {
  return request({
    url: '/api/v1/financial-overview/summary',
    method: 'get',
    params
  })
}

export function getCategorySpending(startDate, endDate) {
  return request({
    url: '/api/v1/financial-overview/category-spending',
    method: 'get',
    params: {
      start_date: startDate,
      end_date: endDate
    }
  })
}

export function getChannelDistribution(startDate, endDate) {
  return request({
    url: '/api/v1/financial-overview/channel-distribution',
    method: 'get',
    params: {
      start_date: startDate,
      end_date: endDate
    }
  })
}

export function getExpenseTrends(startDate, endDate, period = 'day') {
  return request({
    url: '/api/v1/financial-overview/expense-trends',
    method: 'get',
    params: {
      start_date: startDate,
      end_date: endDate,
      period: period
    }
  })
}

// 支出记录相关API
export function getExpenses(params) {
  return request({
    url: '/api/v1/expenses/',
    method: 'get',
    params
  })
}

export function createExpense(data) {
  return request({
    url: '/api/v1/expenses/',
    method: 'post',
    data
  })
}

export function updateExpense(id, data) {
  return request({
    url: `/api/v1/expenses/${id}`,
    method: 'put',
    data
  })
}

export function deleteExpense(id) {
  return request({
    url: `/api/v1/expenses/${id}`,
    method: 'delete'
  })
}

export function classifyExpense(id) {
  return request({
    url: `/api/v1/expenses/${id}/classify`,
    method: 'post'
  })
}

export function batchClassifyExpenses(limit = 5, max_workers = 5) {
  return request({
    url: '/api/v1/ai/batch_classify_expenses',
    method: 'post',
    data: { limit, max_workers },
    timeout: 120000 // 2分钟超时，给批量分类更多时间
  })
}

// 获取未分类记录ID列表
export function getUnclassifiedExpenseIds() {
  return request({
    url: '/api/v1/ai/unclassified_expense_ids',
    method: 'get'
  })
}

// 分类单个记录
export function classifyExpenseById(expense_id) {
  return request({
    url: '/api/v1/ai/classify_single_expense',
    method: 'post',
    data: { expense_id },
    timeout: 60000 // 60秒超时，给单个分类足够时间
  })
}

// 批量删除支出记录
export function batchDeleteExpenses(data) {
  return request({
    url: '/api/v1/expenses/batch/delete',
    method: 'post',
    data
  })
}

// 批量取消分类
export function batchClearCategories(data) {
  return request({
    url: '/api/v1/expenses/batch/clear-categories',
    method: 'post',
    data
  })
}

// 批量删除所有符合条件的支出记录
export function batchDeleteAllExpenses(params) {
  return request({
    url: '/api/v1/expenses/batch/delete-all',
    method: 'post',
    params
  })
}

// 批量取消所有符合条件的分类
export function batchClearAllCategories(params) {
  return request({
    url: '/api/v1/expenses/batch/clear-all-categories',
    method: 'post',
    params
  })
}

// 数据导入相关API
export function importCSV(formData) {
  return request({
    url: '/api/v1/import/csv',
    method: 'post',
    data: formData,
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}



// 设置相关API
export function getSettings() {
  return request({
    url: '/api/v1/settings',
    method: 'get'
  })
}

export function updateSetting(keyPath, value) {
  return request({
    url: `/api/v1/settings/${keyPath}`,
    method: 'put',
    data: { value }
  });
}

export function testAiConnection() {
  return request({
    url: '/api/v1/settings/test-ai',
    method: 'get'
  })
}

export function testPrompt(data) {
  return request({
    url: '/api/v1/settings/test-prompt',
    method: 'post',
    data
  })
}

// 分类管理
export function getAllCategories() {
  return request({ url: '/api/v1/settings/categories', method: 'get' });
}

export function createL1Category(data) {
  return request({ url: '/api/v1/settings/categories/l1', method: 'post', data });
}

export function updateL1Category(oldName, data) {
  return request({ url: `/api/v1/settings/categories/l1/${oldName}`, method: 'put', data });
}

export function deleteL1Category(name) {
  return request({ url: `/api/v1/settings/categories/l1/${name}`, method: 'delete' });
}

export function createL2Category(l1Name, data) {
  return request({ url: `/api/v1/settings/categories/l1/${l1Name}/l2`, method: 'post', data });
}

export function updateL2Category(l1Name, oldL2Name, data) {
  return request({ url: `/api/v1/settings/categories/l2/${l1Name}/${oldL2Name}`, method: 'put', data });
}

export function deleteL2Category(l1Name, l2Name) {
  return request({ url: `/api/v1/settings/categories/l2/${l1Name}/${l2Name}`, method: 'delete' });
}

// 创建统一的API对象
export const financialApi = {
  // 财务概览
  getFinancialOverview,
  getSummaryStats,
  getCategorySpending,
  getChannelDistribution,
  getExpenseTrends,
  
  // 支出记录
  getExpenses,
  createExpense,
  updateExpense,
  deleteExpense,
  classifyExpense,
  batchClassifyExpenses,
  getUnclassifiedExpenseIds,
  classifyExpenseById,
  batchDeleteExpenses,
  batchClearCategories,
  batchDeleteAllExpenses,
  batchClearAllCategories,
  
  // 数据导入
  importCSV,
  
  // 设置管理
  getSettings,
  updateSetting,
  testAiConnection,
  testPrompt,

  // 分类管理
  getAllCategories,
  createL1Category,
  updateL1Category,
  deleteL1Category,
  createL2Category,
  updateL2Category,
  deleteL2Category,
} 