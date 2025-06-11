<template>
  <div class="financial-overview">
    <div class="overview-header">
      <h2>财务概览</h2>
      <div class="date-picker-wrapper">
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          format="YYYY-MM-DD"
          value-format="YYYY-MM-DD"
          @change="handleDateRangeChange"
        />
        <div class="quick-select">
          <el-button
            v-for="option in quickSelectOptions"
            :key="option.key"
            :type="selectedQuickOption === option.key ? 'primary' : 'default'"
            size="small"
            @click="selectQuickOption(option.key)"
          >
            {{ option.label }}
          </el-button>
        </div>
      </div>
    </div>

    <div class="overview-cards">
      <el-row :gutter="24" justify="start">
        <el-col :span="8">
          <el-card class="summary-card large-card">
            <div class="card-header">
              <span class="card-title">总支出</span>
              <span class="period-indicator">{{ getPeriodLabel() }}</span>
            </div>
            <div class="card-content">
              <div class="amount">¥{{ formatNumber(summary.totalExpense) }}</div>
              <div class="comparison">
                <span :class="summary.expenseChange >= 0 ? 'increase' : 'decrease'">
                  {{ summary.expenseChange >= 0 ? '↑' : '↓' }}
                  {{ Math.abs(summary.expenseChange).toFixed(1) }}%
                </span>
                较{{ getPreviousPeriodLabel() }}
              </div>
            </div>
          </el-card>
        </el-col>
        <el-col :span="8">
          <el-card class="summary-card large-card">
            <div class="card-header">
              <span class="card-title">日均支出</span>
              <span class="period-indicator">{{ getPeriodLabel() }}</span>
            </div>
            <div class="card-content">
              <div class="amount">¥{{ formatNumber(summary.avgDaily) }}</div>
              <div class="comparison">
                <span :class="summary.avgChange >= 0 ? 'increase' : 'decrease'">
                  {{ summary.avgChange >= 0 ? '↑' : '↓' }}
                  {{ Math.abs(summary.avgChange).toFixed(1) }}%
                </span>
                较{{ getPreviousPeriodLabel() }}
              </div>
            </div>
          </el-card>
        </el-col>
        <el-col :span="8">
          <el-card class="summary-card channel-card large-card">
            <div class="card-header">
              <span class="card-title">支付渠道分布</span>
            </div>
            <div ref="channelChart" class="large-chart-container"></div>
          </el-card>
        </el-col>
      </el-row>
    </div>

    <div class="chart-section">
      <el-card class="chart-card">
        <div class="card-header">
          <span class="card-title">支出趋势</span>
          <div class="trend-controls">
            <el-radio-group v-model="expenseTrendPeriod" @change="fetchExpenseTrends" size="small">
              <el-radio-button label="day" value="day">日</el-radio-button>
              <el-radio-button label="week" value="week">周</el-radio-button>
              <el-radio-button label="month" value="month">月</el-radio-button>
            </el-radio-group>
          </div>
        </div>
        <div ref="trendChart" class="chart-container"></div>
      </el-card>
    </div>

    <div class="chart-section">
      <el-card class="chart-card">
        <div class="card-header">
          <span class="card-title">分类支出排行</span>
        </div>
        <div ref="categoryChart" class="chart-container"></div>
      </el-card>
    </div>
  </div>
</template>

<script>
import { ref, reactive, onMounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import { financialApi } from '@/api/financial'

export default {
  name: 'FinancialOverview',
  setup() {
    const dateRange = ref([])
    const selectedQuickOption = ref('recent_month')
    const expenseTrendPeriod = ref('day')
    const trendChart = ref(null)
    const channelChart = ref(null)
    const categoryChart = ref(null)
    const chartInstances = reactive({
      trend: null,
      channel: null,
      category: null
    })

    const summary = reactive({
      totalExpense: 0,
      avgDaily: 0,
      transactionCount: 0,
      expenseChange: 0,
      avgChange: 0,
      countChange: 0
    })

    const quickSelectOptions = [
      { key: 'recent_month', label: '近一个月' },
      { key: 'recent_3_months', label: '近三个月' },
      { key: 'this_year', label: '今年' },
      { key: 'last_year', label: '去年' }
    ]

    // 渠道名称映射
    const channelMapping = {
      'alipay': '支付宝',
      'Alipay': '支付宝',
      'wechat': '微信支付',
      'WeChat': '微信支付',
      'Manual Test': '手动测试',
      'Other Test': '其他测试'
    }

    // 获取时间段标签
    const getPeriodLabel = () => {
      return '本段时间'
    }

    const getPreviousPeriodLabel = () => {
      return '上一段时间'
    }

    // 格式化数字
    const formatNumber = (num) => {
      if (num >= 10000) {
        return (num / 10000).toFixed(1) + '万'
      }
      return num.toFixed(2)
    }

    // 获取月份的第一天和最后一天
    const getMonthRange = (date, monthsAgo = 0) => {
      const targetDate = new Date(date)
      targetDate.setMonth(targetDate.getMonth() - monthsAgo)
      
      const firstDay = new Date(targetDate.getFullYear(), targetDate.getMonth(), 1)
      const lastDay = new Date(targetDate.getFullYear(), targetDate.getMonth() + 1, 0)
      
      return [
        firstDay.toISOString().split('T')[0],
        lastDay.toISOString().split('T')[0]
      ]
    }

        // 获取从指定月数前到现在的日期范围
    const getRecentMonthsRange = (monthsAgo) => {
      const today = new Date()
      
      // 使用Date对象自动处理月份溢出
      const startDate = new Date(today)
      startDate.setMonth(startDate.getMonth() - monthsAgo)
      startDate.setDate(startDate.getDate() + 1)
      
      return [
        startDate.toISOString().split('T')[0],
        today.toISOString().split('T')[0]
      ]
    }

    // 选择快捷选项
    const selectQuickOption = (key) => {
      console.log('选择快捷选项:', key)
      selectedQuickOption.value = key
      const today = new Date()
      let startDate, endDate
      
      switch (key) {
        case 'recent_month':
          [startDate, endDate] = getRecentMonthsRange(1)
          break
        case 'recent_3_months':
          [startDate, endDate] = getRecentMonthsRange(3)
          break
        case 'this_year':
          // 今年1月1号到今天
          startDate = new Date(today.getFullYear(), 0, 1).toISOString().split('T')[0]
          endDate = today.toISOString().split('T')[0]
          break
        case 'last_year':
          // 去年1月1号到12月31号
          startDate = new Date(today.getFullYear() - 1, 0, 1).toISOString().split('T')[0]
          endDate = new Date(today.getFullYear() - 1, 11, 31).toISOString().split('T')[0]
          break
      }
      
      console.log(`${key} 时间范围:`, startDate, '到', endDate)
      dateRange.value = [startDate, endDate]
      loadData()
    }

    // 处理日期范围变化
    const handleDateRangeChange = () => {
      selectedQuickOption.value = null
      loadData()
    }

    // 处理趋势周期变化
    const fetchExpenseTrends = () => {
      loadTrendData()
    }

    // 加载数据
    const loadData = async () => {
      if (!dateRange.value || dateRange.value.length !== 2) return

      try {
        console.log('开始加载财务数据:', ...dateRange.value)

        // 确保图表已初始化
        if (!chartInstances.trend || !chartInstances.channel || !chartInstances.category) {
          initCharts()
          // 等待DOM更新和Echarts初始化
          await new Promise(resolve => setTimeout(resolve, 200)) 
        }

        // 并行加载所有数据
        await Promise.all([
          loadSummaryData(),
          loadTrendData(),
          loadChannelData(),
          loadCategoryData()
        ])
      } catch (error) {
        console.error('加载财务概览数据失败:', error)
      }
    }

    // 计算前一周期的日期范围
    const getPreviousPeriodRange = (startDate, endDate) => {
      const start = new Date(startDate)
      const end = new Date(endDate)
      const duration = end.getTime() - start.getTime()
      
      const prevEnd = new Date(start.getTime() - 24 * 60 * 60 * 1000) // 当前开始日期的前一天
      const prevStart = new Date(prevEnd.getTime() - duration)
      
      return [
        prevStart.toISOString().split('T')[0],
        prevEnd.toISOString().split('T')[0]
      ]
    }

    // 加载汇总数据
    const loadSummaryData = async () => {
      if (!dateRange.value || dateRange.value.length !== 2) return
      try {
        const [startDate, endDate] = dateRange.value
        console.log('加载汇总数据:', startDate, endDate)
        
        // 并行获取当前周期和前一周期的数据
        const [prevStartDate, prevEndDate] = getPreviousPeriodRange(startDate, endDate)
        console.log('前一周期:', prevStartDate, prevEndDate)
        
        const [currentResponse, previousResponse] = await Promise.all([
          financialApi.getSummaryStats({ start_date: startDate, end_date: endDate }),
          financialApi.getSummaryStats({ start_date: prevStartDate, end_date: prevEndDate })
        ])
        
        const currentData = currentResponse.data
        const previousData = previousResponse.data
        console.log('当前周期数据:', currentData)
        console.log('前一周期数据:', previousData)
        
        // 处理不同的字段名映射
        const totalExpense = Math.abs(
          currentData.total_expense || 
          currentData.total_expenses || 
          currentData.totalExpense || 
          0
        )
        
        const avgDaily = Math.abs(
          currentData.avg_daily || 
          currentData.average_daily_expenses || 
          currentData.avgDaily || 
          0
        )
        
        const prevTotalExpense = Math.abs(
          previousData.total_expense || 
          previousData.total_expenses || 
          previousData.totalExpense || 
          0
        )
        
        const prevAvgDaily = Math.abs(
          previousData.avg_daily || 
          previousData.average_daily_expenses || 
          previousData.avgDaily || 
          0
        )
        
        // 计算变化百分比
        const expenseChange = prevTotalExpense > 0 
          ? ((totalExpense - prevTotalExpense) / prevTotalExpense) * 100 
          : 0
        
        const avgChange = prevAvgDaily > 0 
          ? ((avgDaily - prevAvgDaily) / prevAvgDaily) * 100 
          : 0
        
        Object.assign(summary, {
          totalExpense,
          avgDaily,
          transactionCount: currentData.transaction_count || currentData.transactionCount || 0,
          expenseChange,
          avgChange,
          countChange: 0 // 暂时不计算交易数量变化
        })
        
        console.log('处理后的汇总数据:', summary)
      } catch (error) {
        console.error('加载汇总数据失败:', error)
      }
    }

    // 加载趋势数据
    const loadTrendData = async () => {
      if (!dateRange.value || dateRange.value.length !== 2) return

      try {
        const [startDate, endDate] = dateRange.value
        const trendResponse = await financialApi.getExpenseTrends(startDate, endDate, expenseTrendPeriod.value)
        const trendData = trendResponse.data
        
        if (chartInstances.trend) {
          const option = {
            tooltip: {
              trigger: 'axis',
              axisPointer: { type: 'cross' }
            },
            xAxis: {
              type: 'category',
              data: trendData.dates || []
            },
            yAxis: {
              type: 'value',
              axisLabel: {
                formatter: (value) => '¥' + formatNumber(Math.abs(value))
              }
            },
            series: [{
              name: '支出金额',
              type: 'line',
              smooth: true,
              data: (trendData.amounts || []).map(amount => Math.abs(amount)),
              lineStyle: { color: '#409EFF' },
              areaStyle: { 
                color: {
                  type: 'linear',
                  x: 0, y: 0, x2: 0, y2: 1,
                  colorStops: [
                    { offset: 0, color: 'rgba(64, 158, 255, 0.3)' },
                    { offset: 1, color: 'rgba(64, 158, 255, 0.1)' }
                  ]
                }
              }
            }]
          }
          chartInstances.trend.setOption(option)
        }
      } catch (error) {
        console.error('加载趋势数据失败:', error)
      }
    }

    // 加载渠道数据
    const loadChannelData = async () => {
      if (!dateRange.value || dateRange.value.length !== 2) return

      try {
        const [startDate, endDate] = dateRange.value
        const channelResponse = await financialApi.getChannelDistribution(startDate, endDate)
        const channelData = channelResponse.data
        
        if (chartInstances.channel) {
          const data = (channelData || []).map(item => {
            const channelName = channelMapping[item.channel] || item.channel
            let color = '#409EFF' // 默认颜色
            
            // 设置渠道特定颜色
            if (channelName === '支付宝') {
              color = '#1890ff' // 蓝色
            } else if (channelName === '微信支付') {
              color = '#52c41a' // 绿色
            }
            
            return {
              name: channelName,
              value: Math.abs(item.total_amount || item.amount || 0),
              itemStyle: { color }
            }
          })
          
          const option = {
            tooltip: {
              trigger: 'item',
              formatter: '{b}: ¥{c} ({d}%)',
              valueFormatter: (value) => formatNumber(value)
            },
            legend: {
              show: false
            },
            series: [{
              name: '支付渠道',
              type: 'pie',
              radius: ['30%', '60%'],
              center: ['50%', '50%'],
              data: data,
              emphasis: {
                itemStyle: {
                  shadowBlur: 10,
                  shadowOffsetX: 0,
                  shadowColor: 'rgba(0, 0, 0, 0.5)'
                }
              },
              label: {
                show: true,
                position: 'outside',
                formatter: (params) => `${params.name}: ¥${formatNumber(params.value)}`
              },
              labelLine: {
                show: true
              }
            }]
          }
          chartInstances.channel.setOption(option)
        }
      } catch (error) {
        console.error('加载渠道数据失败:', error)
      }
    }

    // 加载分类数据
    const loadCategoryData = async () => {
      if (!dateRange.value || dateRange.value.length !== 2) return

      try {
        const [startDate, endDate] = dateRange.value
        console.log('加载分类数据:', startDate, endDate)
        const categoryResponse = await financialApi.getCategorySpending(startDate, endDate)
        const categoryData = categoryResponse.data
        console.log('分类数据响应:', categoryData)
        
        if (chartInstances.category) {
          // 确保有数据且不为空
          if (!categoryData || categoryData.length === 0) {
            console.log('没有分类数据，显示空图表')
            const option = {
              title: {
                text: '暂无分类数据',
                left: 'center',
                top: 'middle',
                textStyle: { color: '#999', fontSize: 16 }
              },
              grid: { show: false },
              xAxis: { show: false },
              yAxis: { show: false },
              series: []
            }
            chartInstances.category.setOption(option)
            return
          }
          
          const categories = (categoryData || []).map(item => item.category || item.category_l1 || '未分类')
          const values = (categoryData || []).map(item => Math.abs(item.amount || item.total_amount || 0))
          
          console.log('处理后的分类数据:', { categories, values })
          
          const option = {
            tooltip: {
              trigger: 'axis',
              axisPointer: { type: 'shadow' },
              formatter: (params) => {
                if (params && params.length > 0) {
                  const data = params[0]
                  return `${data.name}<br/>支出金额: ¥${formatNumber(data.value)}`
                }
                return ''
              },
              backgroundColor: 'rgba(50, 50, 50, 0.8)',
              borderColor: '#777',
              borderWidth: 1,
              textStyle: {
                color: '#fff'
              }
            },
            grid: {
              left: '10%',
              right: '10%',
              bottom: '15%',
              top: '10%',
              containLabel: true
            },
            xAxis: {
              type: 'category',
              data: categories,
              axisLabel: {
                interval: 0,
                rotate: categories.length > 6 ? 45 : 0,
                fontSize: 12
              }
            },
            yAxis: {
              type: 'value',
              axisLabel: {
                formatter: (value) => '¥' + formatNumber(value)
              }
            },
            series: [{
              name: '支出金额',
              type: 'bar',
              data: values,
              itemStyle: {
                color: {
                  type: 'linear',
                  x: 0, y: 0, x2: 0, y2: 1,
                  colorStops: [
                    { offset: 0, color: '#409EFF' },
                    { offset: 1, color: '#66B1FF' }
                  ]
                }
              },
              barWidth: '60%'
            }]
          }
          chartInstances.category.setOption(option, true) // 第二个参数为true表示不合并，直接替换
        }
      } catch (error) {
        console.error('加载分类数据失败:', error)
      }
    }

    // 初始化图表
    const initCharts = () => {
      nextTick(() => {
        console.log('初始化图表...')
        
        // 检查并初始化趋势图表
        if (trendChart.value) {
          console.log('初始化趋势图表')
          if (chartInstances.trend) {
            chartInstances.trend.dispose()
          }
          chartInstances.trend = echarts.init(trendChart.value)
        } else {
          console.warn('趋势图表容器未找到')
        }
        
        // 检查并初始化渠道图表
        if (channelChart.value) {
          console.log('初始化渠道图表')
          if (chartInstances.channel) {
            chartInstances.channel.dispose()
          }
          chartInstances.channel = echarts.init(channelChart.value)
        } else {
          console.warn('渠道图表容器未找到')
        }
        
        // 检查并初始化分类图表
        if (categoryChart.value) {
          console.log('初始化分类图表')
          if (chartInstances.category) {
            chartInstances.category.dispose()
          }
          chartInstances.category = echarts.init(categoryChart.value)
        } else {
          console.warn('分类图表容器未找到')
        }
        
        // 窗口大小变化时重新调整图表
        window.addEventListener('resize', () => {
          Object.values(chartInstances).forEach(chart => {
            if (chart) chart.resize()
          })
        })
      })
    }

    onMounted(() => {
      console.log('FinancialOverview组件已挂载')
      // 延迟初始化，确保DOM完全渲染
      nextTick(() => {
        setTimeout(() => {
          initCharts()
          // 再次延迟加载数据，确保图表已初始化
          setTimeout(() => {
            selectQuickOption('recent_month')
          }, 200)
        }, 100)
      })
    })

    return {
      dateRange,
      selectedQuickOption,
      expenseTrendPeriod,
      trendChart,
      channelChart,
      categoryChart,
      summary,
      quickSelectOptions,
      getPeriodLabel,
      getPreviousPeriodLabel,
      formatNumber,
      selectQuickOption,
      handleDateRangeChange,
      fetchExpenseTrends
    }
  }
}
</script>

<style scoped>
.financial-overview {
  padding: 20px;
}

.overview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.overview-header h2 {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
  color: #1f2937;
}

.date-picker-wrapper {
  display: flex;
  align-items: center;
}

.quick-select {
  margin-left: 16px;
}

.overview-cards {
  margin-bottom: 24px;
}

.summary-card {
  height: 250px;
  margin: 0 auto;
}

.large-card {
  height: 320px;
}

.channel-card {
  margin: 0 auto;
}

.small-chart-container {
  height: 160px;
  width: 100%;
  padding: 10px;
}

.large-chart-container {
  height: 220px;
  width: 100%;
  padding: 15px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-content {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  height: 160px;
  padding: 20px;
}

.card-title {
  font-size: 18px;
  font-weight: 600;
  color: #1f2937;
}

.period-indicator {
  font-size: 12px;
  color: #6b7280;
}

.amount {
  font-size: 32px;
  font-weight: 600;
  color: #1f2937;
  margin-bottom: 8px;
}

.comparison {
  display: flex;
  align-items: center;
  gap: 8px;
}

.increase {
  color: #10b981;
}

.decrease {
  color: #ef4444;
}

.chart-section {
  margin-top: 24px;
}

.chart-card {
  margin-bottom: 24px;
}

.chart-container {
  height: 400px;
}

.trend-controls {
  display: flex;
  align-items: center;
  gap: 8px;
}
</style> 