<template>
  <div class="import-container">
    <h2>数据导入</h2>
    
    <el-card class="upload-card">
      <el-form :model="uploadForm" label-width="120px">
        <el-form-item label="支付渠道" required>
          <el-select v-model="uploadForm.channel" placeholder="请选择支付渠道">
            <el-option label="微信支付" value="WeChat" />
            <el-option label="支付宝" value="Alipay" />
            <el-option label="其他" value="Other" />
          </el-select>
        </el-form-item>
      </el-form>
      
      <el-upload
        class="upload-area"
        drag
        :action="uploadAction"
        :data="uploadData"
        :on-success="handleSuccess"
        :on-error="handleError"
        :before-upload="beforeUpload"
        :disabled="!uploadForm.channel"
        accept=".csv"
      >
        <el-icon class="el-icon--upload"><upload-filled /></el-icon>
        <div class="el-upload__text">
          将文件拖到此处，或<em>点击上传</em>
        </div>
        <template #tip>
          <div class="el-upload__tip">
            只能上传 CSV 文件，且必须先选择支付渠道
          </div>
        </template>
      </el-upload>
    </el-card>



    <!-- 导入结果对话框 -->
    <el-dialog
      v-model="resultDialogVisible"
      title="导入结果"
      width="500px"
    >
      <div v-if="importResult">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="总记录数">{{ importResult.total }}</el-descriptions-item>
          <el-descriptions-item label="成功导入">{{ importResult.imported }}</el-descriptions-item>
          <el-descriptions-item label="跳过记录">{{ importResult.skipped }}</el-descriptions-item>
          <el-descriptions-item label="失败记录">{{ importResult.failed }}</el-descriptions-item>
        </el-descriptions>
        
        <div v-if="importResult.failed > 0" class="mt-4">
          <el-alert
            title="部分记录导入失败"
            type="warning"
            description="请检查CSV文件格式是否正确，或查看详细错误信息。"
            show-icon
          />
        </div>
      </div>
      <template #footer>
        <el-button type="primary" @click="resultDialogVisible = false">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'
const resultDialogVisible = ref(false)
const importResult = ref(null)

const uploadForm = ref({
  channel: ''
})

const uploadAction = computed(() => {
  return `${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}/api/v1/import/csv`
})

const uploadData = computed(() => {
  return {
    channel: uploadForm.value.channel
  }
})

const beforeUpload = (file) => {
  if (!uploadForm.value.channel) {
    ElMessage.error('请先选择支付渠道！')
    return false
  }
  
  const isCSV = file.type === 'text/csv' || file.name.endsWith('.csv')
  if (!isCSV) {
    ElMessage.error('只能上传 CSV 文件！')
    return false
  }
  
  const isLt10M = file.size / 1024 / 1024 < 10
  if (!isLt10M) {
    ElMessage.error('文件大小不能超过 10MB!')
    return false
  }
  
  return true
}

const handleSuccess = (response) => {
  console.log('导入成功响应:', response)
  
  // 检查响应是否有message，说明导入完成
  if (response.message === 'Import completed' || response.summary) {
    ElMessage.success(`文件导入成功！共导入 ${response.summary?.imported || 0} 条记录`)
    
    if (response.summary) {
      importResult.value = response.summary
      resultDialogVisible.value = true
    }
  } else {
    ElMessage.warning('文件上传成功，但处理状态不明')
  }
  

}

const handleError = (error) => {
  console.error('导入失败:', error)
  
  let errorMessage = '导入失败，请检查文件格式'
  if (error.response && error.response.data && error.response.data.detail) {
    errorMessage = error.response.data.detail
  } else if (error.message) {
    errorMessage = error.message
  }
  
  ElMessage.error(errorMessage)
}


</script>

<style scoped>
.import-container {
  padding: 20px;
}

.upload-card {
  margin-bottom: 20px;
}

.upload-area {
  width: 100%;
  margin-top: 20px;
}



.el-upload__tip {
  color: #909399;
  font-size: 12px;
  margin-top: 7px;
}

.mt-4 {
  margin-top: 16px;
}
</style> 