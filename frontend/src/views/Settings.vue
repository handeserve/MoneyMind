<template>
  <div class="settings">
    <div class="header">
      <h2>系统设置</h2>
    </div>

    <div class="settings-content">
      <el-tabs v-model="activeTab" tab-position="left" class="settings-tabs">
        
        <!-- AI服务设置 -->
        <el-tab-pane label="AI服务设置" name="ai">
          <el-card>
            <template #header>
              <span>AI服务配置</span>
            </template>
            <el-form v-if="settings.ai_services" :model="settings.ai_services" label-width="120px">
              <el-form-item label="默认服务:">
                <el-select 
                  v-model="settings.ai_services.active_service" 
                  placeholder="选择默认AI服务"
                  @change="value => saveSetting('ai_services.active_service', value)"
                >
                  <el-option 
                    v-for="(service, name) in settings.ai_services.services" 
                    :key="name" 
                    :label="name" 
                    :value="name" 
                  />
                </el-select>
              </el-form-item>
              <el-form-item label="分类并发数:">
                <el-input-number 
                  v-model="settings.ai_services.classification_concurrency" 
                  :min="1" :max="20" 
                  @change="value => saveSetting('ai_services.classification_concurrency', value)"
                />
              </el-form-item>
              
              <template v-for="(service, name) in settings.ai_services.services" :key="name">
                <el-divider content-position="left">{{ name }} 配置</el-divider>
                <el-form-item label="API Key:">
                  <el-input 
                    v-model="service.api_key" 
                    :placeholder="`输入 ${name} API Key`" 
                    type="password" 
                    show-password 
                    @blur="() => saveSetting(`ai_services.services.${name}.api_key`, service.api_key)"
                  />
                </el-form-item>
                <el-form-item label="Base URL:">
                  <el-input 
                    v-model="service.base_url" 
                    :placeholder="`输入 ${name} Base URL`"
                    @blur="() => saveSetting(`ai_services.services.${name}.base_url`, service.base_url)"
                  />
                </el-form-item>
                <el-form-item label="模型:">
                  <el-input 
                    v-model="service.model" 
                    :placeholder="`输入 ${name} 模型名称`"
                    @blur="() => saveSetting(`ai_services.services.${name}.model`, service.model)"
                  />
                </el-form-item>
              </template>

              <el-form-item>
                <el-button type="success" @click="testAiConnection" :loading="isTestingConnection">测试连接</el-button>
              </el-form-item>
            </el-form>
          </el-card>
        </el-tab-pane>
        
        <!-- 分类管理 -->
        <el-tab-pane label="分类管理" name="categories">
           <el-card>
            <template #header>
              <div class="card-header">
                <span>支出分类层级管理</span>
                <el-button type="primary" size="small" @click="openCategoryDialog(null, 'add_l1')">
                  <el-icon><Plus /></el-icon>
                  添加主分类
                </el-button>
              </div>
            </template>
            <el-table
              :data="categoryTree"
              style="width: 100%"
              row-key="id"
              border
              default-expand-all
              :tree-props="{ children: 'children', hasChildren: 'hasChildren' }"
            >
              <el-table-column prop="name" label="分类名称" />
              <el-table-column label="操作" width="250">
                <template #default="{ row }">
                  <template v-if="row.level === 1">
                    <el-button type="success" size="small" @click="openCategoryDialog(row, 'add_l2')">添加子分类</el-button>
                    <el-button type="primary" size="small" @click="openCategoryDialog(row, 'edit_l1')">编辑</el-button>
                    <el-button type="danger" size="small" @click="handleDeleteCategory(row)">删除</el-button>
                  </template>
                  <template v-else>
                    <el-button type="primary" size="small" @click="openCategoryDialog(row, 'edit_l2')">编辑</el-button>
                    <el-button type="danger" size="small" @click="handleDeleteCategory(row)">删除</el-button>
                  </template>
                </template>
              </el-table-column>
            </el-table>
          </el-card>
        </el-tab-pane>

        <!-- 提示词模板 -->
        <el-tab-pane label="提示词模板" name="prompts">
          <el-card>
            <template #header>
              <span>AI分类提示词模板</span>
            </template>
            <el-form v-if="settings.prompts" label-width="120px">
              <el-form-item label="系统提示词:">
                 <el-alert
                  title="系统提示词由'分类管理'动态生成，后端会自动处理。"
                  type="info"
                  show-icon
                  :closable="false"
                  style="margin-bottom: 10px;"
                />
                <el-input
                  :model-value="generatedSystemPrompt"
                  type="textarea"
                  :rows="12"
                  readonly
                />
              </el-form-item>
              <el-form-item label="用户提示词模板:">
                <el-input
                  v-model="settings.prompts.user_prompt_template"
                  type="textarea"
                  :rows="4"
                  placeholder="输入用户提示词模板..."
                  @blur="() => saveSetting('prompts.user_prompt_template', settings.prompts.user_prompt_template)"
                />
              </el-form-item>
            </el-form>
          </el-card>
        </el-tab-pane>

        <!-- 数据库设置 -->
        <el-tab-pane label="数据库设置" name="database">
          <el-card>
            <template #header>
              <span>数据库配置</span>
            </template>
            <el-form v-if="settings.database" :model="settings.database" label-width="120px">
              <el-form-item label="数据库路径:">
                <el-input 
                  v-model="settings.database.database_path" 
                  placeholder="输入数据库路径" 
                  @blur="() => saveSetting('database.database_path', settings.database.database_path)"
                />
              </el-form-item>
              <el-form-item label="备份路径:">
                <el-input 
                  v-model="settings.database.backup_path" 
                  placeholder="输入备份路径" 
                  @blur="() => saveSetting('database.backup_path', settings.database.backup_path)"
                />
              </el-form-item>
              <el-form-item label="自动备份:">
                <el-switch 
                  v-model="settings.database.auto_backup" 
                  @change="value => saveSetting('database.auto_backup', value)"
                />
              </el-form-item>
              <el-form-item label="备份间隔(小时):">
                <el-input-number 
                  v-model="settings.database.backup_interval" 
                  :min="1" :max="24"
                  @change="value => saveSetting('database.backup_interval', value)"
                />
              </el-form-item>
            </el-form>
          </el-card>
        </el-tab-pane>

         <!-- 应用设置 -->
        <el-tab-pane label="应用设置" name="app">
          <el-card>
            <template #header>
              <span>应用配置</span>
            </template>
            <el-form v-if="settings.app" :model="settings.app" label-width="120px">
              <el-form-item label="语言:">
                <el-select 
                  v-model="settings.app.language"
                  @change="value => saveSetting('app.language', value)"
                >
                  <el-option label="中文" value="zh-CN" />
                  <el-option label="English" value="en-US" />
                </el-select>
              </el-form-item>
              <el-form-item label="主题:">
                <el-select 
                  v-model="settings.app.theme"
                  @change="value => saveSetting('app.theme', value)"
                >
                  <el-option label="浅色" value="light" />
                  <el-option label="深色" value="dark" />
                  <el-option label="自动" value="auto" />
                </el-select>
              </el-form-item>
              <el-form-item label="货币符号:">
                <el-select 
                  v-model="settings.app.currency"
                  @change="value => saveSetting('app.currency', value)"
                >
                  <el-option label="人民币 (¥)" value="CNY" />
                  <el-option label="美元 ($)" value="USD" />
                  <el-option label="欧元 (€)" value="EUR" />
                </el-select>
              </el-form-item>
              <el-form-item label="日期格式:">
                <el-select 
                  v-model="settings.app.date_format"
                  @change="value => saveSetting('app.date_format', value)"
                >
                  <el-option label="YYYY-MM-DD" value="YYYY-MM-DD" />
                  <el-option label="MM/DD/YYYY" value="MM/DD/YYYY" />
                  <el-option label="DD/MM/YYYY" value="DD/MM/YYYY" />
                </el-select>
              </el-form-item>
            </el-form>
          </el-card>
        </el-tab-pane>

        <!-- 导入设置 -->
        <el-tab-pane label="导入设置" name="import">
          <el-card>
            <template #header>
              <span>数据导入配置</span>
            </template>
            <el-form v-if="settings.import" :model="settings.import" label-width="120px">
              <el-form-item label="跳过重复:">
                <el-switch 
                  v-model="settings.import.skip_duplicates"
                  @change="value => saveSetting('import.skip_duplicates', value)"
                />
              </el-form-item>
              <el-form-item label="批量大小:">
                <el-input-number 
                  v-model="settings.import.batch_size" 
                  :min="10" :max="1000"
                  @change="value => saveSetting('import.batch_size', value)"
                />
              </el-form-item>
              <el-form-item label="默认渠道:">
                <el-select 
                  v-model="settings.import.default_channel"
                  @change="value => saveSetting('import.default_channel', value)"
                >
                  <el-option label="支付宝" value="alipay" />
                  <el-option label="微信支付" value="wechat" />
                  <el-option label="银行卡" value="bank" />
                </el-select>
              </el-form-item>
            </el-form>
          </el-card>
        </el-tab-pane>

      </el-tabs>
    </div>

    <!-- 分类编辑对话框 -->
    <el-dialog v-model="categoryDialog.visible" :title="categoryDialog.title" width="500px">
      <el-form :model="categoryDialog.form" @submit.prevent="handleSaveCategory">
        <el-form-item :label="categoryDialog.formLabel" required>
          <el-input v-model="categoryDialog.form.name" placeholder="输入分类名称" autofocus @keyup.enter="handleSaveCategory"/>
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="categoryDialog.visible = false">取消</el-button>
          <el-button type="primary" @click="handleSaveCategory">确定</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, reactive } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { financialApi } from '@/api/financial';
import { Plus } from '@element-plus/icons-vue';

const activeTab = ref('ai');
const settings = ref({
  ai_services: {
    active_service: '',
    classification_concurrency: 5,
    services: {}
  },
  preset_categories: {},
  prompts: {
    user_prompt_template: ''
  },
  database: {
    database_path: '',
    backup_path: '',
    auto_backup: true,
    backup_interval: 24
  },
  app: {
    language: 'zh-CN',
    theme: 'light',
    currency: 'CNY',
    date_format: 'YYYY-MM-DD'
  },
  import: {
    skip_duplicates: true,
    batch_size: 100,
    default_channel: 'alipay'
  }
});
const isTestingConnection = ref(false);

// --- Load Initial Settings ---
const loadSettings = async () => {
  try {
    const response = await financialApi.getSettings();
    // Deep merge to avoid losing structure if a key is missing from backend
    Object.assign(settings.value, response.data);
    ElMessage.success('设置加载成功！');
  } catch (error) {
    console.error('加载设置失败:', error);
    ElMessage.error('加载设置失败，请检查后端服务是否可用。');
  }
};

onMounted(loadSettings);

// --- Generic Save Function ---
const saveSetting = async (keyPath, value) => {
  try {
    // For numeric inputs that might return null on clear
    const valueToSave = value === null ? 0 : value;
    await financialApi.updateSetting(keyPath, valueToSave);
    ElMessage.success({
      message: `设置 '${keyPath}' 已保存！`,
      duration: 1500
    });
  } catch (error) {
    console.error(`保存设置 '${keyPath}' 失败:`, error);
    ElMessage.error(`保存设置 '${keyPath}' 失败。`);
    // Revert optimistic UI update on failure
    await loadSettings();
  }
};

// --- AI Settings ---
const testAiConnection = async () => {
  isTestingConnection.value = true;
  try {
    // Ensure the latest API key is saved before testing
    const activeService = settings.value.ai_services.active_service;
    const apiKey = settings.value.ai_services.services[activeService].api_key;
    await saveSetting(`ai_services.services.${activeService}.api_key`, apiKey);

    const response = await financialApi.testAiConnection();
    if (response.data.success) {
      ElMessage.success(response.data.message);
    } else {
      ElMessage.error(response.data.message);
    }
  } catch (error) {
    console.error('测试AI连接失败:', error);
    ElMessage.error('测试AI连接失败，请查看控制台获取更多信息。');
  } finally {
    isTestingConnection.value = false;
  }
};

// --- Category Management ---
const categoryDialog = reactive({
  visible: false,
  title: '',
  form: { name: '' },
  formLabel: '',
  mode: '', // 'add_l1', 'edit_l1', 'add_l2', 'edit_l2'
  originalData: null
});

const categoryTree = computed(() => {
  const cats = settings.value.preset_categories || {};
  return Object.keys(cats).map((l1Name, index) => ({
    id: `l1-${index}`,
    name: l1Name,
    level: 1,
    children: (cats[l1Name] || []).map((l2Name, subIndex) => ({
      id: `l2-${index}-${subIndex}`,
      name: l2Name,
      level: 2,
      parentName: l1Name
    }))
  }));
});

const openCategoryDialog = (row, mode) => {
  categoryDialog.mode = mode;
  categoryDialog.originalData = row;
  if (mode === 'add_l1') {
    categoryDialog.title = '添加主分类';
    categoryDialog.formLabel = '主分类名称';
    categoryDialog.form.name = '';
  } else if (mode === 'edit_l1') {
    categoryDialog.title = '编辑主分类';
    categoryDialog.formLabel = '新名称';
    categoryDialog.form.name = row.name;
  } else if (mode === 'add_l2') {
    categoryDialog.title = `在 [${row.name}] 下添加子分类`;
    categoryDialog.formLabel = '子分类名称';
    categoryDialog.form.name = '';
  } else if (mode === 'edit_l2') {
    categoryDialog.title = '编辑子分类';
    categoryDialog.formLabel = '新名称';
    categoryDialog.form.name = row.name;
  }
  categoryDialog.visible = true;
};

const handleSaveCategory = async () => {
  const { mode, form, originalData } = categoryDialog;
  if (!form.name) {
    ElMessage.warning('分类名称不能为空。');
    return;
  }
  
  try {
    let response;
    switch (mode) {
      case 'add_l1':
        response = await financialApi.createL1Category({ name: form.name });
        break;
      case 'edit_l1':
        response = await financialApi.updateL1Category(originalData.name, { new_name: form.name });
        break;
      case 'add_l2':
        response = await financialApi.createL2Category(originalData.name, { name: form.name });
        break;
      case 'edit_l2':
        response = await financialApi.updateL2Category(originalData.parentName, originalData.name, { new_name: form.name });
        break;
    }
    ElMessage.success(response.data.message || '操作成功！');
    categoryDialog.visible = false;
    await loadSettings(); // Reload all settings to reflect changes
  } catch (error) {
    console.error('保存分类失败:', error);
    ElMessage.error(error.response?.data?.detail || '保存分类失败。');
  }
};

const handleDeleteCategory = async (row) => {
  await ElMessageBox.confirm(`确定要删除分类 "${row.name}" 吗？`, '警告', {
    confirmButtonText: '确定删除',
    cancelButtonText: '取消',
    type: 'warning',
  });

  try {
    let response;
    if (row.level === 1) {
      response = await financialApi.deleteL1Category(row.name);
    } else {
      response = await financialApi.deleteL2Category(row.parentName, row.name);
    }
    ElMessage.success(response.data.message || '删除成功！');
    await loadSettings();
  } catch (error) {
    console.error('删除分类失败:', error);
    ElMessage.error(error.response?.data?.detail || '删除分类失败。');
  }
};

// --- Prompts ---
const generatedSystemPrompt = computed(() => {
  const cats = settings.value.preset_categories || {};
  const parts = [
    '你是一个专业的财务助手。你的任务是根据用户提供的支出描述，将其分类到预定义的类别中。',
    '请严格按照以下JSON格式返回结果: {"category_l1": "主分类", "category_l2": "子分类"}',
    '\n可用主分类和子分类如下:\n'
  ];
  for (const l1 in cats) {
    const l2_list = cats[l1];
    if (l2_list && l2_list.length > 0) {
      parts.push(`- ${l1} (包含子分类: ${l2_list.join(', ')})`);
    } else {
      parts.push(`- ${l1} (无子分类)`);
    }
  }
  parts.push('\n## 注意事项：');
  parts.push('- category_l1 必须是可用主分类中的一个，完全匹配分类名称。');
  parts.push('- category_l2 必须是对应主分类下的一个子分类。如果无法或无需细分到子分类, 或者该主分类下没有定义子分类, 请返回空字符串 ""。');
  parts.push('- 只返回JSON格式，不要添加其他说明文字或代码块标记。');
  return parts.join('\n');
});
</script>

<style scoped>
.settings {
  padding: 20px;
}
.header {
  margin-bottom: 20px;
}
.settings-content {
  margin-top: 20px;
}
.settings-tabs {
  min-height: 400px;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style> 