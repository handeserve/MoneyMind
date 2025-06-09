# 个人智能支出分析系统 (Personal Smart Expense Analyzer)

## 1. 项目概述 (Project Overview)

本项目旨在开发一个个人支出管理与分析系统。用户可以导入微信支付和支付宝的支出数据（CSV格式），系统将利用大语言模型（LLM）API 对支出进行自动分类。通过动态且交互友好的网页图形化界面，用户可以查看支出概览、管理数据库记录、以及配置系统参数，从而更好地理解和控制个人财务状况。

## 2. 主要功能 (Key Features)

*   **数据导入**: 支持导入微信支付和支付宝的CSV格式账单文件。
*   **自动分类**: 利用大语言模型 (LLM) API 自动为支出记录建议一级和二级分类。
*   **手动调整**: 用户可以手动修改或确认AI建议的分类。
*   **数据管理**: 提供支出记录的增删改查界面，包括隐藏不计入统计的条目。
*   **支出概览**:
    *   总支出、日均支出等核心指标卡片。
    *   渠道支出占比图 (饼图/环形图)。
    *   支出趋势折线图 (按日、周、月切换)。
    *   分类支出直方图/条形图。
*   **系统设置**:
    *   AI模型配置 (选择模型服务商, API Key 管理)。
    *   AI参数调整 (如温度等)。
    *   分类体系管理 (查看、添加、编辑、删除预设分类)。
    *   提示词编辑 (修改用于AI分类的提示词模板)。
*   **数据持久化**: 使用 SQLite 数据库存储所有数据。
*   **用户友好界面**: 动态、交互式的Web用户界面。

## 3. 技术栈 (Technology Stack)

*   **后端 (Backend)**:
    *   Python 3.x
    *   FastAPI (Web框架)
    *   Uvicorn (ASGI服务器)
    *   SQLite (数据库)
    *   PyYAML (配置文件处理)
    *   Requests (HTTP请求库)
*   **前端 (Frontend)**:
    *   HTML5
    *   CSS3
    *   Vanilla JavaScript (ES6+)
    *   Chart.js (图表库)
*   **AI (AI Integration)**:
    *   通过API调用外部大语言模型服务 (例如 DeepSeek API)。
*   **版本控制 (Version Control)**:
    *   Git

## 4. 项目安装与配置 (Setup and Installation)

1.  **克隆仓库 (Clone Repository)**:
    ```bash
    # 替换为您的仓库URL (Replace with your repository URL)
    git clone https://github.com/your-username/personal-expense-analyzer.git
    cd personal-expense-analyzer
    ```

2.  **创建虚拟环境 (Create Virtual Environment)**:
    (推荐使用 Python 3.8 或更高版本 / Recommended Python 3.8+)
    ```bash
    python -m venv venv
    ```
    激活虚拟环境 (Activate the virtual environment):
    *   Windows: `venv\Scripts\activate`
    *   macOS/Linux: `source venv/bin/activate`

3.  **安装依赖 (Install Dependencies)**:
    ```bash
    pip install -r requirements.txt
    ```

4.  **配置 `config.yaml`**:
    *   复制或重命名项目根目录下的 `config.yaml`（如果它作为模板提供且被`.gitignore`忽略）或根据以下结构自行创建。(Copy or rename `config.yaml` in the project root, or create it based on the structure below if it's missing.)
    *   **重要**: 在 `config.yaml` 文件中填入您自己的LLM API Key。(**Important**: Fill in your own LLM API Key in `config.yaml`.)
    *   `config.yaml` 文件结构示例 (File structure example):
        ```yaml
        default_llm_service: "deepseek"
        llm_services:
          deepseek:
            api_key: "YOUR_DEEPSEEK_API_KEY_HERE" # <--- 在此处填入您的API Key (Fill in your API Key here)
            model_params:
              model_name: "deepseek-chat"
              temperature: 0.7
              max_tokens: 150 # 根据需要调整 (Adjust as needed)
        prompts:
          classification_prompt_template: |
            请分析以下支出描述，并将其归类到一个主要类别和一个次要类别。
            支出描述: "{description_for_ai}"
            金额: {amount} (可选)
            渠道: {channel} (可选)
            原始分类: {source_provided_category} (可选)
            请从此列表中选择一个主要类别: {available_categories_l1_list_str}
            然后，根据您选择的主要类别，从相关选项中选择一个次要类别。
            可用的主要和次要类别结构如下:
            {full_category_structure_str}
            请严格按照以下格式回复:
            L1 Category: <选择的主要类别名称>
            L2 Category: <选择的次要类别名称>
        preset_categories:
          # ... (预设分类 / Preset categories e.g., "Food & Drinks": ["Groceries", "Restaurants"]) ...
          "Food & Drinks": ["Groceries", "Restaurants & Dining", "Coffee Shops", "Food Delivery", "Snacks & Beverages"]
          # (Other categories as defined in the default config)
        ```

5.  **初始化数据库 (Initialize Database)**:
    *   如果数据库文件 (`personal_expenses.db`) 不存在，运行以下命令创建数据库和表结构 (If the database file `personal_expenses.db` does not exist, run the following command to create the database and tables):
    ```bash
    python database/database.py
    ```
    *   (注意: 此脚本配置为在项目根目录下创建 `personal_expenses.db` / Note: This script is configured to create `personal_expenses.db` in the project root directory)

## 5. 运行应用 (Running the Application)

1.  确保您的虚拟环境已激活。(Ensure your virtual environment is activated.)
2.  启动 FastAPI 后端服务 (Start the FastAPI backend service):
    ```bash
    python presentation_layer/main.py
    ```
3.  服务启动后，通常会在 `http://localhost:8000` (或 `http://127.0.0.1:8000`) 提供访问。(The service will typically be available at `http://localhost:8000` or `http://127.0.0.1:8000`.)
4.  在浏览器中打开上述地址即可使用本应用。(Open this address in your browser to use the application.)

## 6. 项目结构 (Project Structure)

```
personal_expense_analyzer/
├── ai_layer/                  # AI相关逻辑 (配置管理, LLM接口, 分类器)
│   ├── config_manager.py
│   ├── expense_classifier.py
│   └── llm_interface.py
├── database/                  # 数据库交互 (连接, CRUD, CSV解析, 导入, 分析函数)
│   ├── analytics.py
│   ├── csv_parser.py
│   ├── data_importer.py
│   └── database.py
├── presentation_layer/        # Web表现层 (FastAPI后端, 前端静态文件)
│   ├── frontend/
│   │   └── static/
│   │       ├── css/
│   │       ├── js/
│   │       └── *.html
│   ├── routers/               # API路由模块
│   │   ├── ai_router.py
│   │   ├── dashboard_router.py
│   │   ├── expenses_router.py
│   │   ├── import_router.py
│   │   └── settings_router.py
│   └── main.py                # FastAPI应用入口
├── tests/                     # (可选) 测试文件目录 (Optional: Directory for test files)
├── .gitignore                 # Git忽略配置文件
├── config.yaml                # 应用配置文件 (需用户自行配置API Key)
├── personal_expenses.db       # SQLite数据库文件 (Will be created in project root)
├── requirements.txt           # Python依赖包
└── README.md                  # 项目说明文件
```

## 7. 注意事项 (Notes)

*   确保 `config.yaml` 中的 API Key 配置正确，否则AI分类功能将无法正常工作。(Ensure the API Key in `config.yaml` is correctly configured, otherwise the AI classification feature will not work.)
*   导入CSV文件时，请确保文件格式与微信支付或支付宝导出的标准格式一致。(When importing CSV files, please ensure the file format matches the standard export format from WeChat Pay or Alipay.)

```
