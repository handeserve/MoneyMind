<template>
  <div class="expenses">
    <div class="header">
      <h2>支出记录</h2>
      <div class="header-actions">
        <el-button type="primary" @click="handleAddExpense">
          <el-icon><Plus /></el-icon>
          添加支出
        </el-button>
        <el-button type="warning" @click="handleBatchClassify" :loading="batchClassifying && batchProgress.status === 'active'">
          <el-icon><MagicStick /></el-icon>
          {{ batchClassifying && batchProgress.total > 0 && batchProgress.completed < batchProgress.total ? '继续分类' : 'AI批量分类' }}
        </el-button>
        <el-dropdown>
          <el-button type="danger">
            批量操作
            <el-icon class="el-icon--right"><ArrowDown /></el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item @click="handleBatchDeleteAll">
                <el-icon><Delete /></el-icon>
                全部删除
              </el-dropdown-item>
              <el-dropdown-item @click="handleBatchClearCategories">
                <el-icon><Remove /></el-icon>
                全部取消分类
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </div>

    <div class="filter-section">
      <el-form :model="filters" inline>
        <el-form-item label="支付渠道:">
          <el-select
            v-model="filters.channel"
            placeholder="选择渠道"
            clearable
            style="width: 140px;"
          >
            <el-option label="支付宝" value="alipay" />
            <el-option label="微信支付" value="wechat" />
          </el-select>
        </el-form-item>
        <el-form-item label="分类:">
          <el-select
            v-model="filters.category"
            placeholder="选择分类"
            clearable
            style="width: 120px;"
          >
            <el-option
              v-for="category in categories"
              :key="category"
              :label="category"
              :value="category"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="日期范围:">
          <el-date-picker
            v-model="filters.dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            format="YYYY-MM-DD"
            value-format="YYYY-MM-DD"
            style="width: 240px;"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadExpenses">查询</el-button>
          <el-button @click="resetFilters">重置</el-button>
        </el-form-item>
        <el-form-item>
          <el-checkbox v-model="showHidden" @change="loadExpenses">
            显示隐藏记录
          </el-checkbox>
        </el-form-item>
      </el-form>
    </div>

    <!-- 批量分类进度 -->
    <div v-if="batchClassifying" class="batch-progress">
      <el-card>
        <div class="progress-header">
          <span>AI批量分类进行中...</span>
          <span>{{ batchProgress.completed }}/{{ batchProgress.total }}</span>
        </div>
        <el-progress
          :percentage="batchProgress.percentage"
          :status="batchProgress.status === 'active' ? '' : batchProgress.status"
        />
        <div class="progress-details">
          <span>成功: {{ batchProgress.success }}</span>
          <span>失败: {{ batchProgress.failed }}</span>
          <span v-if="batchProgress.estimatedTimeRemaining && batchProgress.estimatedTimeRemaining > 0">
            预计剩余: {{ Math.floor(batchProgress.estimatedTimeRemaining / 60) }}分{{ batchProgress.estimatedTimeRemaining % 60 }}秒
          </span>
        </div>
      </el-card>
    </div>

    <div class="table-section">
      <el-table
        :data="expenses"
        v-loading="loading"
        stripe
        style="width: 100%"
        @sort-change="handleSortChange"
      >
        <el-table-column prop="transaction_time" label="交易时间" width="160" sortable="custom">
          <template #default="{ row }">
            {{ formatDate(row.transaction_time) }}
          </template>
        </el-table-column>
        <el-table-column prop="amount" label="金额" width="120" sortable="custom">
          <template #default="{ row }">
            <span class="amount">¥{{ formatAmount(Math.abs(row.amount)) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="channel" label="支付渠道" width="120">
          <template #default="{ row }">
            <el-tag :type="getChannelTagType(row.channel)">
              {{ getChannelDisplayName(row.channel) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="category_l1" label="分类" width="180">
          <template #default="{ row }">
            <div v-if="row.category_l1">
              <el-tag type="success">{{ row.category_l1 }}</el-tag>
              <el-tag v-if="row.category_l2" type="success" size="small" style="margin-left: 4px;">{{ row.category_l2 }}</el-tag>
            </div>
            <div v-else-if="row.is_classified_by_ai">
              <el-tag type="warning" effect="light">{{ row.ai_suggestion_l1 }}</el-tag>
              <el-tag v-if="row.ai_suggestion_l2" type="warning" size="small" effect="light" style="margin-left: 4px;">{{ row.ai_suggestion_l2 }}</el-tag>
            </div>
            <el-tag v-else type="info">未分类</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="source_raw_description" label="描述" min-width="200">
          <template #default="{ row }">
            <div class="description-cell">
              <span :class="{ 'hidden-text': row.is_hidden }">{{ row.source_raw_description }}</span>
              <el-tag v-if="row.is_hidden" type="warning" size="small">已隐藏</el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <div class="action-buttons">
              <!-- 只对未分类的记录显示AI分类按钮 -->
              <el-button
                v-if="!row.category_l1"
                type="primary"
                size="small"
                @click="handleClassifyItem(row)"
                :loading="classifyingItems.has(row.id)"
              >
                AI分类
              </el-button>

              <el-button
                :type="row.is_hidden ? 'warning' : 'info'"
                size="small"
                @click="handleToggleHidden(row)"
              >
                {{ row.is_hidden ? '显示' : '隐藏' }}
              </el-button>
              <el-button type="primary" size="small" @click="handleEditExpense(row)">
                编辑
              </el-button>
              <el-button type="danger" size="small" @click="handleDeleteExpense(row)">
                删除
              </el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination">
        <el-pagination
          v-model:current-page="pagination.page"
          :page-size="pagination.size"
          :total="pagination.total"
          layout="total, prev, pager, next, jumper"
          @current-change="loadExpenses"
        />
      </div>
    </div>

    <!-- 编辑对话框 -->
    <el-dialog v-model="editDialogVisible" title="编辑支出记录" width="600px">
      <el-form :model="editForm" label-width="100px">
        <el-form-item label="交易时间">
          <el-date-picker
            v-model="editForm.transaction_time"
            type="datetime"
            placeholder="选择时间"
            format="YYYY-MM-DD HH:mm:ss"
            value-format="YYYY-MM-DD HH:mm:ss"
          />
        </el-form-item>
        <el-form-item label="金额">
          <el-input-number
            v-model="editForm.amount"
            :precision="2"
            :step="0.01"
            :max="999999"
          />
        </el-form-item>
        <el-form-item label="一级分类">
          <el-select 
            v-model="editForm.category_l1" 
            placeholder="选择一级分类"
            @change="editForm.category_l2 = ''"
          >
            <el-option
              v-for="category in categories"
              :key="category"
              :label="category"
              :value="category"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="二级分类" v-if="editForm.category_l1">
          <el-select 
            v-model="editForm.category_l2" 
            placeholder="选择二级分类(可选)"
            clearable
          >
            <el-option
              v-for="subCategory in getSubCategories()"
              :key="subCategory"
              :label="subCategory"
              :value="subCategory"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="描述">
          <el-input
            v-model="editForm.source_raw_description"
            type="textarea"
            :rows="3"
            placeholder="输入描述"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="editDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="handleUpdateExpense">保存</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, MagicStick, ArrowDown, Delete, Remove } from '@element-plus/icons-vue'
import { financialApi } from '@/api/financial'

export default {
  name: 'Expenses',
  components: {
    Plus,
    MagicStick,
    ArrowDown,
    Delete,
    Remove
  },
  setup() {
    const loading = ref(false)
    const expenses = ref([])
    const categories = ref([])
    const categoriesData = ref({}) // 完整的分类数据结构
    const showHidden = ref(false)
    const batchClassifying = ref(false)
    const classifyingItems = ref(new Set())
    const editDialogVisible = ref(false)

    const filters = reactive({
      channel: '',
      category: '',
      dateRange: []
    })

    const pagination = reactive({
      page: 1,
      size: 20,
      total: 0
    })

    const sorting = reactive({
      prop: 'transaction_time',
      order: 'descending'
    })

    const batchProgress = reactive({
      completed: 0,
      total: 0,
      success: 0,
      failed: 0,
      percentage: 0,
      status: ''
    })

    const editForm = reactive({
      id: null,
      transaction_time: '',
      amount: 0,
      category_l1: '',
      category_l2: '',
      source_raw_description: ''
    })

    const aiSettings = reactive({
      concurrency: 5, // Default value
      batchSize: 10   // Default value
    })

    // 渠道显示名称映射
    const channelMapping = {
      'alipay': '支付宝',
      'Alipay': '支付宝',
      'wechat': '微信支付',
      'WeChat': '微信支付',
      'Manual Test': '手动测试',
      'Other Test': '其他测试'
    }

    // 获取渠道显示名称
    const getChannelDisplayName = (channel) => {
      return channelMapping[channel] || channel
    }

    // 获取渠道标签类型
    const getChannelTagType = (channel) => {
      const typeMap = {
        'alipay': 'primary',
        'wechat': 'success'
      }
      return typeMap[channel] || 'info'
    }

    // 格式化日期
    const formatDate = (dateStr) => {
      if (!dateStr) return ''
      return new Date(dateStr).toLocaleString('zh-CN')
    }

    // 格式化金额
    const formatAmount = (amount) => {
      return Number(amount).toFixed(2)
    }

    // 获取当前选中一级分类的二级分类
    const getSubCategories = () => {
      if (!editForm.category_l1 || !categoriesData.value[editForm.category_l1]) {
        return []
      }
      return categoriesData.value[editForm.category_l1] || []
    }

    // 加载支出记录
    const loadExpenses = async () => {
      loading.value = true
      try {
        const params = {
          page: pagination.page,
          limit: pagination.size,
          sort_by: sorting.prop,
          sort_order: sorting.order === 'ascending' ? 'ASC' : 'DESC',
          include_hidden: showHidden.value
        }

        if (filters.channel) {
          params.channel = filters.channel
        }
        if (filters.category) {
          params.category_l1 = filters.category
        }
        if (filters.dateRange && filters.dateRange.length === 2) {
          params.start_date = filters.dateRange[0]
          params.end_date = filters.dateRange[1]
        }

        console.log('发送的筛选参数:', params)
        const response = await financialApi.getExpenses(params)
        console.log('支出记录API响应:', response)
        
        // 处理响应数据格式
        const data = response.data || response
        expenses.value = data.expenses || data.items || []
        pagination.total = data.total_count || data.total || 0
      } catch (error) {
        console.error('加载支出记录失败:', error)
        
        // 更详细的错误处理
        if (error.code === 'ECONNABORTED') {
          ElMessage.error('请求超时，请稍后重试')
        } else if (error.response?.status === 500) {
          ElMessage.error('服务器错误，请稍后重试')
        } else if (error.response?.status === 0 || !error.response) {
          ElMessage.error('网络连接失败，请检查网络')
        } else {
          ElMessage.error('加载支出记录失败，请刷新页面重试')
        }
        
        // 设置空数据，避免页面显示异常
        expenses.value = []
        pagination.total = 0
      } finally {
        loading.value = false
      }
    }

    // 重置筛选条件
    const resetFilters = () => {
      Object.assign(filters, {
        channel: '',
        category: '',
        dateRange: []
      })
      pagination.page = 1
      loadExpenses()
    }

    // 处理排序变化
    const handleSortChange = ({ prop, order }) => {
      sorting.prop = prop
      sorting.order = order
      pagination.page = 1
      loadExpenses()
    }

    // 单个AI分类
    const handleClassifyItem = async (row) => {
      classifyingItems.value.add(row.id)
      try {
        const updatedExpense = await financialApi.classifyExpense(row.id)
        ElMessage.success('AI分类建议已生成')
        // 用返回的数据更新行，实现即时刷新
        const index = expenses.value.findIndex(e => e.id === row.id)
        if (index !== -1) {
          expenses.value[index] = updatedExpense.data || updatedExpense;
        }
      } catch (error) {
        console.error('AI分类失败:', error)
        ElMessage.error('AI分类失败，请查看控制台日志')
      } finally {
        classifyingItems.value.delete(row.id)
      }
    }



    // 加载AI设置
    const loadAiSettings = async () => {
      try {
        const response = await financialApi.getSettings()
        const settings = response.data?.config || response.config || response
        if (settings.ai_services && settings.ai_services.classification_concurrency) {
          aiSettings.concurrency = settings.ai_services.classification_concurrency;
        }
        // 加载导入设置中的批次大小
        if (settings.import_settings && settings.import_settings.batch_size) {
          aiSettings.batchSize = settings.import_settings.batch_size;
        } else if (settings.import && settings.import.batch_size) {
          aiSettings.batchSize = settings.import.batch_size;
        } else {
          aiSettings.batchSize = 10; // 默认值
        }
      } catch (error) {
        console.error('加载AI设置失败:', error)
        // 使用默认值，无需提示用户
        aiSettings.concurrency = 5;
        aiSettings.batchSize = 10;
      }
    }

    // 带重试机制的单项分类
    const classifyWithRetry = async (itemId, maxRetries = 3) => {
      let attempt = 0;
      while (attempt < maxRetries) {
        try {
          await financialApi.classifyExpense(itemId);
          return; // Success
        } catch (error) {
          attempt++;
          const status = error.response?.status;
          if ((status === 429 || status === 503) && attempt < maxRetries) {
            const delay = Math.pow(2, attempt) * 1000; // Exponential backoff: 2s, 4s
            console.warn(`分类请求失败 (ID: ${itemId}, Status: ${status}), ${delay}ms后重试 (第${attempt}次)...`);
            await new Promise(resolve => setTimeout(resolve, delay));
          } else {
            throw error; // Non-retriable error or max retries reached
          }
        }
      }
    };

    // 批量AI分类 - 高效批次处理 + 模拟实时进度
    const handleBatchClassify = async () => {
      try {
        // 如果有进行中的任务，询问是否继续
        if (batchClassifying.value && batchProgress.total > 0) {
          const confirm = await ElMessageBox.confirm(
            `检测到有未完成的批量分类任务 (${batchProgress.completed}/${batchProgress.total})，要继续处理剩余的记录吗？`,
            '继续批量分类',
            {
              confirmButtonText: '继续处理',
              cancelButtonText: '取消',
              type: 'info'
            }
          )

          if (!confirm) return
        } else {
          // 新的批量分类任务
          const confirm = await ElMessageBox.confirm(
            '此操作将对所有未分类的记录进行AI分类。这可能需要一些时间，并且会消耗AI配额。确定要继续吗？',
            '批量AI分类确认',
            {
              confirmButtonText: '确定',
              cancelButtonText: '取消',
              type: 'warning'
            }
          )

          if (!confirm) return
        }

        batchClassifying.value = true
        
        // 如果不是继续任务，重置进度
        if (batchProgress.total === 0) {
          Object.assign(batchProgress, {
            completed: 0,
            total: 0,
            success: 0,
            failed: 0,
            percentage: 0,
            status: 'active',
            startTime: Date.now(),
            estimatedTimeRemaining: null
          })
        } else {
          // 继续任务，更新状态和开始时间
          batchProgress.status = 'active'
          if (!batchProgress.startTime) {
            batchProgress.startTime = Date.now()
          }
        }
        
        // 保存批量分类状态到本地存储
        localStorage.setItem('batchClassifying', 'true')
        localStorage.setItem('batchProgress', JSON.stringify(batchProgress))

        // 获取总的未分类记录数量
        if (batchProgress.total === 0) {
          ElMessage.info('正在获取所有未分类的记录...')
          
          const idsResponse = await financialApi.getUnclassifiedExpenseIds()
          const responseData = idsResponse.data || idsResponse
          const totalUnclassified = (responseData.expense_ids || []).length
          
          if (totalUnclassified === 0) {
            ElMessage.info('没有需要分类的记录')
            batchClassifying.value = false
            return
          }

          batchProgress.total = totalUnclassified
          ElMessage.info(`发现 ${totalUnclassified} 条未分类记录，开始高效批量分类...`)
        }
        
        // 从设置中读取批次大小和并发数
        const batchSize = aiSettings.batchSize || 50 // 每批次50条
        const maxWorkers = aiSettings.concurrency || 10 // 并发数10
        console.log(`🚀 开始批量分类，总记录数: ${batchProgress.total}, 批次大小: ${batchSize}, 并发数: ${maxWorkers}`)
        
        // 模拟实时进度更新
        let progressSimulator = null
        
        const simulateProgress = (batchStartCount, batchSize, processingTime) => {
          const intervalTime = Math.max(100, processingTime / batchSize * 1000 / 5) // 每个批次分5次更新
          let simulatedCount = 0
          
          progressSimulator = setInterval(() => {
            if (simulatedCount < batchSize && batchProgress.completed < batchProgress.total) {
              simulatedCount++
              batchProgress.completed = Math.min(batchStartCount + simulatedCount, batchProgress.total)
              batchProgress.percentage = Math.round((batchProgress.completed / batchProgress.total) * 100)
              
              // 计算剩余时间
              if (batchProgress.completed > 0 && batchProgress.completed < batchProgress.total) {
                const elapsed = Date.now() - batchProgress.startTime
                const avgTimePerItem = elapsed / batchProgress.completed
                const remaining = batchProgress.total - batchProgress.completed
                batchProgress.estimatedTimeRemaining = Math.max(0, Math.ceil(remaining * avgTimePerItem / 1000))
              }
              
              // 更新本地存储（减少频率）
              if (batchProgress.completed % 10 === 0) {
                localStorage.setItem('batchProgress', JSON.stringify(batchProgress))
              }
            } else {
              clearInterval(progressSimulator)
              progressSimulator = null
            }
          }, intervalTime)
        }
        
        // 批次处理循环
        const processingStartTime = Date.now()
        let totalProcessed = batchProgress.completed
        let totalSuccess = batchProgress.success
        let totalFailed = batchProgress.failed
        
        while (totalProcessed < batchProgress.total) {
          try {
            // 开始模拟这个批次的进度
            const batchStartCount = totalProcessed
            const expectedBatchSize = Math.min(batchSize, batchProgress.total - totalProcessed)
            simulateProgress(batchStartCount, expectedBatchSize, 10) // 假设每批次10秒
            
            // 调用后端批量分类API
            const batchResult = await financialApi.batchClassifyExpenses(expectedBatchSize, maxWorkers)
            const resultData = batchResult.data || batchResult
            
            // 停止进度模拟
            if (progressSimulator) {
              clearInterval(progressSimulator)
              progressSimulator = null
            }
            
            // 更新实际结果
            const actualProcessed = resultData.processed_count || expectedBatchSize
            const actualSuccess = resultData.success_count || 0
            const actualFailed = resultData.failed_count || 0
            
            totalProcessed += actualProcessed
            totalSuccess += actualSuccess
            totalFailed += actualFailed
            
            // 更新进度（真实数据）
            batchProgress.completed = Math.min(totalProcessed, batchProgress.total)
            batchProgress.success = totalSuccess
            batchProgress.failed = totalFailed
            batchProgress.percentage = Math.round((batchProgress.completed / batchProgress.total) * 100)
            
            // 计算剩余时间
            if (batchProgress.completed > 0 && batchProgress.completed < batchProgress.total) {
              const elapsed = Date.now() - batchProgress.startTime
              const avgTimePerItem = elapsed / batchProgress.completed
              const remaining = batchProgress.total - batchProgress.completed
              batchProgress.estimatedTimeRemaining = Math.max(0, Math.ceil(remaining * avgTimePerItem / 1000))
            } else if (batchProgress.completed >= batchProgress.total) {
              batchProgress.estimatedTimeRemaining = 0
            }
            
            // 显示进度消息
            const timeText = batchProgress.estimatedTimeRemaining && batchProgress.estimatedTimeRemaining > 0
              ? ` (预计剩余: ${Math.floor(batchProgress.estimatedTimeRemaining / 60)}分${batchProgress.estimatedTimeRemaining % 60}秒)`
              : ''
            
            ElMessage.info(`✅ 批次完成！已处理 ${batchProgress.completed}/${batchProgress.total} 条记录${timeText} (成功: ${batchProgress.success}, 失败: ${batchProgress.failed})`)
            
            // 保存进度
            localStorage.setItem('batchProgress', JSON.stringify(batchProgress))
            
            // 检查是否还有未处理的记录
            if (batchProgress.completed >= batchProgress.total) {
              break
            }
            
            // 短暂延迟，避免API过载
            await new Promise(resolve => setTimeout(resolve, 500))
            
          } catch (error) {
            // 停止进度模拟
            if (progressSimulator) {
              clearInterval(progressSimulator)
              progressSimulator = null
            }
            
            console.error('批次处理失败:', error)
            
            // 如果是网络错误，尝试继续
            if (error.response?.status >= 500 || error.code === 'ECONNABORTED') {
              ElMessage.warning('网络错误，3秒后继续尝试...')
              await new Promise(resolve => setTimeout(resolve, 3000))
              continue
            } else {
              throw error // 其他错误直接抛出
            }
          }
        }
        
        const processingEndTime = Date.now()
        const totalProcessingTime = (processingEndTime - processingStartTime) / 1000
        const avgTimePerItem = totalProcessingTime / batchProgress.total
        const itemsPerSecond = batchProgress.total / totalProcessingTime

        batchProgress.status = batchProgress.failed > 0 ? 'warning' : 'success'
        ElMessage.success(`🎉 批量分类完成！成功: ${batchProgress.success}，失败: ${batchProgress.failed}`)
        console.log(`🚀 性能统计: 总时间 ${totalProcessingTime.toFixed(1)}秒, 平均 ${avgTimePerItem.toFixed(2)}秒/条, 速度 ${itemsPerSecond.toFixed(1)}条/秒`)
        
        // 重新加载数据
        await loadExpenses()
        
      } catch (error) {
        if (error !== 'cancel') {
          console.error('批量分类失败:', error)
          ElMessage.error('批量分类操作失败，请查看控制台日志。')
          batchProgress.status = 'exception'
        }
      } finally {
        // 确保清理进度模拟器
        if (progressSimulator) {
          clearInterval(progressSimulator)
        }
        
        setTimeout(() => {
          batchClassifying.value = false
          // 清除本地存储
          localStorage.removeItem('batchClassifying')
          localStorage.removeItem('batchProgress')
        }, 3000)
      }
    }

    // 切换隐藏状态
    const handleToggleHidden = async (row) => {
      try {
        await financialApi.updateExpense(row.id, {
          is_hidden: !row.is_hidden
        })
        ElMessage.success(row.is_hidden ? '已显示记录' : '已隐藏记录')
        await loadExpenses()
      } catch (error) {
        console.error('更新隐藏状态失败:', error)
        ElMessage.error('操作失败')
      }
    }

    // 编辑支出
    const handleEditExpense = (row) => {
      Object.assign(editForm, {
        id: row.id,
        transaction_time: row.transaction_time,
        amount: Math.abs(row.amount),
        category_l1: row.category_l1 || '',
        category_l2: row.category_l2 || '',
        source_raw_description: row.source_raw_description
      })
      editDialogVisible.value = true
    }

    // 更新支出
    const handleUpdateExpense = async () => {
      try {
        const updateData = {
          transaction_time: editForm.transaction_time,
          amount: -Math.abs(editForm.amount), // 支出为负数
          category_l1: editForm.category_l1,
          source_raw_description: editForm.source_raw_description
        }
        
        // 只有在有二级分类时才添加
        if (editForm.category_l2) {
          updateData.category_l2 = editForm.category_l2
        }
        
        await financialApi.updateExpense(editForm.id, updateData)
        ElMessage.success('更新成功')
        editDialogVisible.value = false
        await loadExpenses()
      } catch (error) {
        console.error('更新失败:', error)
        ElMessage.error('更新失败')
      }
    }

    // 删除支出
    const handleDeleteExpense = async (row) => {
      try {
        await ElMessageBox.confirm(
          `确定要删除这条支出记录吗？`,
          '删除确认',
          {
            confirmButtonText: '确定',
            cancelButtonText: '取消',
            type: 'warning'
          }
        )

        await financialApi.deleteExpense(row.id)
        ElMessage.success('删除成功')
        await loadExpenses()
      } catch (error) {
        if (error === 'cancel') return
        console.error('删除失败:', error)
        ElMessage.error('删除失败')
      }
    }

    // 添加支出
    const handleAddExpense = () => {
      // TODO: 实现添加支出功能
      ElMessage.info('添加支出功能待实现')
    }

    // 批量删除所有符合当前筛选条件的支出
    const handleBatchDeleteAll = async () => {
      try {
        await ElMessageBox.confirm(
          '此操作将删除所有符合当前筛选条件的支出记录（不仅仅是当前页面），确定吗？',
          '批量删除确认',
          {
            confirmButtonText: '确定',
            cancelButtonText: '取消',
            type: 'warning'
          }
        )
        
        // 构建当前的筛选条件参数
        const filterParams = {
          channel: filters.channel || undefined,
          start_date: filters.dateRange && filters.dateRange.length === 2 ? filters.dateRange[0] : undefined,
          end_date: filters.dateRange && filters.dateRange.length === 2 ? filters.dateRange[1] : undefined,
          is_hidden: showHidden.value === true ? true : (showHidden.value === false ? false : undefined),
          category_l1: filters.category === 'is_null' ? 'is_null' : filters.category || undefined
        }

        // 移除值为undefined的属性
        Object.keys(filterParams).forEach(key => 
          filterParams[key] === undefined && delete filterParams[key]
        )

        await financialApi.batchDeleteAllExpenses(filterParams)
        ElMessage.success('批量删除成功')
        await loadExpenses()
      } catch (error) {
        if (error !== 'cancel') {
          console.error('批量删除失败:', error)
          ElMessage.error('批量删除失败')
        }
      }
    }

    // 批量取消所有符合当前筛选条件的分类
    const handleBatchClearCategories = async () => {
      try {
        await ElMessageBox.confirm(
          '此操作将清除所有符合当前筛选条件的记录的分类信息（不仅仅是当前页面），确定要继续吗？',
          '批量取消分类确认',
          {
            confirmButtonText: '确定',
            cancelButtonText: '取消',
            type: 'warning'
          }
        )

        // 构建当前的筛选条件参数
        const filterParams = {
          channel: filters.channel || undefined,
          start_date: filters.dateRange && filters.dateRange.length === 2 ? filters.dateRange[0] : undefined,
          end_date: filters.dateRange && filters.dateRange.length === 2 ? filters.dateRange[1] : undefined,
          is_hidden: showHidden.value === true ? true : (showHidden.value === false ? false : undefined),
          category_l1: filters.category === 'is_null' ? 'is_null' : filters.category || undefined
        }

        // 移除值为undefined的属性
        Object.keys(filterParams).forEach(key => 
          filterParams[key] === undefined && delete filterParams[key]
        )

        await financialApi.batchClearAllCategories(filterParams)
        ElMessage.success('批量取消分类成功')
        await loadExpenses()
      } catch (error) {
        if (error !== 'cancel') {
          console.error('批量取消分类失败:', error)
          ElMessage.error('批量取消分类失败')
        }
      }
    }

    // 加载分类列表
    const loadCategories = async () => {
      try {
        const response = await financialApi.getAllCategories()
        const data = response.data || response
        
        // 提取所有一级分类名称
        if (data.categories && typeof data.categories === 'object') {
          // 返回的是 { "餐饮美食": [...], "交通出行": [...] } 格式
          categoriesData.value = data.categories
          categories.value = Object.keys(data.categories)
        } else if (data.categories && Array.isArray(data.categories)) {
          // 如果是数组格式
          categories.value = data.categories.map(category => category.name || category)
          categoriesData.value = {}
        } else if (data && typeof data === 'object') {
          // 如果直接是对象形式的分类数据
          categoriesData.value = data
          categories.value = Object.keys(data)
        } else {
          categories.value = []
          categoriesData.value = {}
        }
        
        console.log('加载到的分类:', categories.value)
      } catch (error) {
        console.error('加载分类失败:', error)
        ElMessage.error('加载分类列表失败')
        
        // 备用方案：从设置中获取
        try {
          const settingsResponse = await financialApi.getSettings()
          const settings = settingsResponse.data?.config || settingsResponse.config || settingsResponse
          if (settings.preset_categories) {
            categories.value = Object.keys(settings.preset_categories);
            console.log('从设置中加载到的分类:', categories.value)
          }
        } catch (settingsError) {
          console.error('从设置加载分类也失败:', settingsError)
          categories.value = []
        }
      }
    }

    onMounted(async () => {
      // 先加载基础数据
      await Promise.all([
        loadExpenses(),
        loadCategories(),
        loadAiSettings()
      ])
      
      // 检查是否有进行中的批量分类
      const savedBatchClassifying = localStorage.getItem('batchClassifying')
      const savedBatchProgress = localStorage.getItem('batchProgress')
      
      if (savedBatchClassifying === 'true' && savedBatchProgress) {
        try {
          const savedProgress = JSON.parse(savedBatchProgress)
          
          // 检查是否真的有未完成的任务
          if (savedProgress.completed < savedProgress.total && savedProgress.total > 0) {
            Object.assign(batchProgress, savedProgress)
            // 重置状态为等待，避免按钮被锁定
            batchProgress.status = 'waiting'
            batchClassifying.value = true
            
            ElMessage.warning({
              message: '检测到未完成的批量分类任务，点击"继续分类"按钮继续处理',
              duration: 5000
            })
          } else {
            // 任务已完成，清除本地存储
            localStorage.removeItem('batchClassifying')
            localStorage.removeItem('batchProgress')
          }
        } catch (error) {
          console.error('恢复批量分类进度失败:', error)
          // 清除损坏的本地存储
          localStorage.removeItem('batchClassifying')
          localStorage.removeItem('batchProgress')
        }
      }
      
      if (!batchClassifying.value) {
        // 重置批量分类状态，防止页面刷新后状态残留
        Object.assign(batchProgress, {
          completed: 0,
          total: 0,
          success: 0,
          failed: 0,
          percentage: 0,
          status: '',
          startTime: null,
          estimatedTimeRemaining: null
        })
      }
    })

    return {
      loading,
      expenses,
      categories,
      categoriesData,
      showHidden,
      batchClassifying,
      classifyingItems,
      editDialogVisible,
      filters,
      pagination,
      batchProgress,
      editForm,
      getChannelDisplayName,
      getChannelTagType,
      formatDate,
      formatAmount,
      getSubCategories,
      loadExpenses,
      resetFilters,
      handleSortChange,
      handleClassifyItem,
      handleBatchClassify,
      handleToggleHidden,
      handleEditExpense,
      handleUpdateExpense,
      handleDeleteExpense,
      handleAddExpense,
      handleBatchDeleteAll,
      handleBatchClearCategories
    }
  }
}
</script>

<style scoped>
.expenses {
  padding: 24px;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.header h2 {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
  color: #1f2937;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.filter-section {
  margin-bottom: 24px;
  padding: 16px;
  background: #f9fafb;
  border-radius: 8px;
}

.batch-progress {
  margin-bottom: 24px;
}

.progress-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  font-weight: 500;
}

.progress-details {
  display: flex;
  gap: 16px;
  margin-top: 8px;
  font-size: 12px;
  color: #6b7280;
}

.table-section {
  background: white;
  border-radius: 8px;
  overflow: hidden;
}

.amount {
  font-weight: 500;
  color: #ef4444;
}

.description-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.hidden-text {
  opacity: 0.5;
  text-decoration: line-through;
}

.action-buttons {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}

.pagination {
  padding: 16px;
  display: flex;
  justify-content: center;
  background: #f9fafb;
}

/* 调整下拉选择框样式 */
:deep(.el-select) {
  width: auto;
  min-width: 120px;
}

:deep(.el-select .el-input) {
  width: auto;
}

:deep(.el-select .el-input__inner) {
  min-width: 100px;
}

/* 调整表格列宽 */
:deep(.el-table .cell) {
  padding: 0 8px;
}

:deep(.el-table-column--small .cell) {
  padding: 0 4px;
}
</style> 