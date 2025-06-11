# MoneyMind - 智能个人财务管理系统

> 基于AI的现代化个人支出分析与管理平台

## 🌟 项目简介

MoneyMind 是一个现代化的个人财务管理系统，结合了AI智能分类和直观的数据可视化。支持微信支付、支付宝账单导入，通过大语言模型自动分类支出，提供全面的财务分析和洞察。

## ✨ 主要功能

### 📊 财务概览
- **实时财务仪表板**：总支出、日均支出、环比变化等核心指标
- **多维度数据分析**：按渠道、分类、时间趋势的可视化图表
- **智能对比分析**：本期与上期数据对比，变化趋势一目了然

### 🤖 AI智能分类
- **自动分类**：基于LLM的智能支出分类，支持二级分类体系
- **批量处理**：高效的批量分类功能，支持并发处理
- **手动调整**：用户可随时修改AI分类结果
- **学习优化**：支持自定义分类体系和提示词模板

### 📁 数据管理
- **多平台导入**：支持微信支付、支付宝CSV文件导入
- **记录管理**：完整的CRUD操作，支持批量删除、批量清除分类
- **数据过滤**：强大的筛选功能，按时间、金额、分类、渠道等维度过滤
- **智能去重**：自动识别并跳过重复记录

### ⚙️ 系统设置
- **AI服务配置**：支持多种LLM服务商（DeepSeek、Claude等）
- **分类管理**：可视化的分类体系管理，支持两级分类
- **系统偏好**：主题、语言、货币、日期格式等个性化设置
- **导入设置**：批量大小、默认渠道等导入参数配置

## 🚀 技术栈

### 后端技术
- **Python 3.8+** - 核心运行环境
- **FastAPI** - 现代化Web框架，自动API文档
- **SQLite** - 轻量级数据库，支持复杂查询
- **PyYAML** - 配置文件管理
- **Requests** - HTTP客户端，AI API调用

### 前端技术
- **Vue 3** - 渐进式前端框架
- **Element Plus** - 现代化UI组件库
- **ECharts** - 专业数据可视化
- **Vite** - 下一代前端构建工具
- **JavaScript ES6+** - 现代化前端开发

### AI集成
- **DeepSeek API** - 主推LLM服务
- **Claude API** - 备选AI服务
- **自定义提示词** - 优化分类准确性

## 📦 快速开始

### 环境要求
- Python 3.8 或更高版本
- Node.js 16+ (用于前端构建)
- Git

### 1. 克隆项目
```bash
git clone https://github.com/your-username/MoneyMind.git
cd MoneyMind
```

### 2. 后端设置
```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 3. 配置文件
复制配置模板并填入你的API密钥：
```bash
cp config.example.yaml config.yaml
```

编辑 `config.yaml` 文件，设置你的AI服务API密钥：
```yaml
ai_services:
  active_service: deepseek
  services:
    deepseek:
      api_key: "你的_API_密钥"  # 在此填入真实API密钥
```

### 4. 前端设置
```bash
cd frontend
npm install
cd ..
```

### 5. 启动应用

需要同时启动后端和前端服务：

**启动后端服务 (端口8000)：**
```bash
# 推荐方式：直接使用 uvicorn
uvicorn presentation_layer.main:app --reload --host 0.0.0.0 --port 8000

# 注意：run.py 文件可能已过时，建议使用上面的命令
```

**启动前端开发服务器 (端口5173)：**
```bash
cd frontend
npm run dev
```

启动完成后：
- **前端访问**：`http://localhost:5173` (用户界面)

## 📁 项目结构

```
MoneyMind/
├── ai_layer/                    # AI服务层
│   ├── config_manager.py       # 配置管理
│   ├── expense_classifier.py   # 支出分类器
│   └── llm_interface.py        # LLM接口
├── database/                    # 数据层
│   ├── db.py                   # 数据库连接
│   ├── csv_parser.py           # CSV解析器
│   ├── data_importer.py        # 数据导入
│   └── analytics.py            # 数据分析
├── presentation_layer/          # 表现层
│   ├── routers/                # API路由
│   │   ├── financial_router.py # 财务API
│   │   ├── ai_router.py        # AI功能API
│   │   ├── import_router.py    # 导入API
│   │   └── settings_router.py  # 设置API
│   ├── dependencies.py         # 依赖注入
│   └── main.py                 # FastAPI应用
├── frontend/                    # Vue前端应用
│   ├── src/
│   │   ├── views/              # 页面组件
│   │   ├── components/         # 公共组件
│   │   ├── api/                # API调用
│   │   └── utils/              # 工具函数
│   ├── public/                 # 静态资源
│   └── dist/                   # 构建输出
├── data/                        # 数据目录
│   └── moneymind.db            # SQLite数据库
├── config.yaml                  # 应用配置(需要创建)
├── config.example.yaml          # 配置模板
├── requirements.txt             # Python依赖
└── README.md                   # 项目说明
```

## 📊 使用指南

### 数据导入
1. 导出微信支付或支付宝的CSV账单文件
2. 在"数据导入"页面选择对应的支付渠道
3. 上传CSV文件，系统会自动解析和导入
4. 使用"批量AI分类"功能自动分类所有支出

### 财务分析
- **概览页面**：查看总体财务状况和趋势
- **支出记录**：管理具体支出条目，支持搜索筛选
- **图表分析**：多种可视化图表展示支出分布

### 系统配置
- **AI设置**：配置LLM服务和分类参数
- **分类管理**：自定义分类体系
- **系统偏好**：个性化设置

## 🔧 高级配置

### AI服务配置
支持多种AI服务商，在 `config.yaml` 中配置：

```yaml
ai_services:
  active_service: deepseek
  classification_concurrency: 10
  services:
    deepseek:
      api_key: "your-api-key"
      base_url: "https://api.deepseek.com"
      model: "deepseek-chat"
    anthropic:
      api_key: "your-claude-key"
      model: "claude-3-sonnet-20240229"
```

### 自定义分类
可以在设置页面或配置文件中自定义分类体系：

```yaml
preset_categories:
  餐饮美食:
    - 日常三餐
    - 外卖
    - 聚餐
  交通出行:
    - 公共交通
    - 打车
    - 加油
```

## 🤝 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add some amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 🙏 致谢

- [FastAPI](https://fastapi.tiangolo.com/) - 现代化的Web框架
- [Vue.js](https://vuejs.org/) - 渐进式前端框架
- [Element Plus](https://element-plus.org/) - Vue 3 组件库
- [ECharts](https://echarts.apache.org/) - 数据可视化库
- [DeepSeek](https://www.deepseek.com/) - AI服务支持

---

**MoneyMind** - 让财务管理更智能 💰✨
