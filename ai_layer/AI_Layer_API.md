# 个人支出分析器 - AI层API文档 (Personal Expense Analyzer - AI Layer API Documentation)

## 1. 概述 (Overview)

AI层负责支出分析中的智能方面。这包括：
- 管理与AI模型、API密钥和提示词相关的配置 (`config_manager.py`)。
- 与外部大语言模型 (LLM) API交互以执行支出分类等任务 (`llm_interface.py`)。
- 协调单个支出的整体分类工作流程 (`expense_classifier.py`)。

(The AI Layer is responsible for the intelligent aspects of expense analysis. This includes:
- Managing configuration related to AI models, API keys, and prompts (`config_manager.py`).
- Interacting with external Large Language Model (LLM) APIs for tasks like expense categorization (`llm_interface.py`).
- Orchestrating the overall classification workflow for individual expenses (`expense_classifier.py`).)


## 2. 模块: `config_manager.py` (Module)

**用途 (Purpose):** 管理应用程序的配置，从位于项目根目录的 `config.yaml` 文件加载设置。它提供了一种集中的方式来访问配置参数，并在文件或特定设置缺失时回退到默认值。
(Manages the application's configuration, loading settings from `config.yaml` located in the project root. It provides a centralized way to access configuration parameters with fallbacks to default values if the file or specific settings are missing.)

### 主要功能 (Key Function)

#### `get_config() -> dict`
- **描述 (Description):** 检索应用程序配置。它在首次调用时从 `config.yaml` 加载配置，然后缓存结果以供后续调用，从而提高性能。如果找不到 `config.yaml`，文件为空，或主要部分缺失，则回退到该部分的默认配置结构。
  (Retrieves the application configuration. It loads the configuration from `config.yaml` on its first call and then caches the result for subsequent calls to improve performance. If `config.yaml` is not found, empty, or a primary section is missing, it falls back to a default configuration structure for the missing parts.)
- **返回 (Returns):** 一个包含整个应用程序配置的字典。(A dictionary containing the entire application configuration.)

### 辅助函数 (Helper Functions)

这些函数提供了便捷的方式来访问通过 `get_config()` 获取的配置的特定部分。
(These functions provide convenient access to specific parts of the configuration obtained via `get_config()`.)

#### `get_default_llm_service() -> Optional[str]`
- **描述 (Description):** 返回配置中指定的默认LLM服务名称。 (Returns the name of the default LLM service specified in the configuration.)
- **返回 (Returns):** 服务名称 (例如 "deepseek") 或 `None` (如果未设置)。(The service name (e.g., "deepseek") or `None` if not set.)

#### `get_api_key(service_name: Optional[str] = None) -> Optional[str]`
- **描述 (Description):** 检索指定 `service_name` 的API密钥。如果 `service_name` 为 `None`，则尝试使用默认LLM服务。
  (Retrieves the API key for the specified `service_name`. If `service_name` is `None`, it attempts to use the default LLM service.)
- **参数 (Parameters):**
    - `service_name` (Optional[str]): LLM服务的名称 (例如 "deepseek")。(The name of the LLM service (e.g., "deepseek").)
- **返回 (Returns):** API密钥字符串，如果未找到或密钥似乎是占位符，则为 `None`。(The API key string or `None` if not found or if the key appears to be a placeholder.)

#### `get_prompt_template(template_name: str = 'classification_prompt_template') -> Optional[str]`
- **描述 (Description):** 按名称检索特定的提示词模板。(Retrieves a specific prompt template by its name.)
- **参数 (Parameters):**
    - `template_name` (str): 提示词模板的逻辑名称 (例如 "classification_prompt_template")。(The logical name of the prompt template (e.g., "classification_prompt_template").)
- **返回 (Returns):** 提示词模板字符串，如果未找到则为 `None`。(The prompt template string or `None` if not found.)

#### `get_preset_categories() -> dict`
- **描述 (Description):** 检索预设类别的字典。(Retrieves the dictionary of preset categories.)
- **返回 (Returns):** 一个字典，其中键是L1类别名称，值是L2类别字符串列表 (例如 `{"Food & Drinks": ["Groceries", "Restaurants"]}`)。如果未找到则返回空字典。
  (A dictionary where keys are L1 category names and values are lists of L2 category strings (e.g., `{"Food & Drinks": ["Groceries", "Restaurants"]}`). Returns an empty dict if not found.)

#### `get_l1_categories() -> List[str]`
- **描述 (Description):** 从预设类别中提取并返回所有L1类别名称的列表。(Extracts and returns a list of all L1 category names from the preset categories.)
- **返回 (Returns):** L1类别字符串列表。(A list of L1 category strings.)

#### `get_l2_categories(l1_category_name: str) -> List[str]`
- **描述 (Description):** 返回给定L1类别名称的L2类别列表。(Returns the list of L2 categories for a given L1 category name.)
- **参数 (Parameters):**
    - `l1_category_name` (str): L1类别的名称。(The name of the L1 category.)
- **返回 (Returns):** 指定L1类别的L2类别字符串列表，如果L1类别未找到或没有L2类别，则返回空列表。
  (A list of L2 category strings for the specified L1 category, or an empty list if the L1 category is not found or has no L2 categories.)

#### `get_model_params(service_name: Optional[str] = None) -> dict`
- **描述 (Description):** 检索指定 `service_name` 的模型参数 (例如 temperature, max_tokens, model_name)。如果 `service_name` 为 `None`，则使用默认LLM服务。
  (Retrieves model parameters (e.g., temperature, max_tokens, model_name) for the specified `service_name`. If `service_name` is `None`, it uses the default LLM service.)
- **参数 (Parameters):**
    - `service_name` (Optional[str]): LLM服务的名称。(The name of the LLM service.)
- **返回 (Returns):** 模型参数的字典，如果未找到则返回空字典。(A dictionary of model parameters or an empty dict if not found.)

### `config.yaml` 结构预期 (Structure Expectation)

`config_manager.py` 模块期望项目根目录中的 `config.yaml` 文件具有类似以下的结构（如果部分缺失，则提供默认值）：
(The `config_manager.py` module expects `config.yaml` in the project root to have a structure similar to this (with defaults provided if sections are missing):)

```yaml
default_llm_service: "deepseek"
llm_services:
  deepseek:
    api_key: "YOUR_DEEPSEEK_API_KEY_HERE"
    model_params:
      model_name: "deepseek-chat"
      temperature: 0.7
      max_tokens: 150
  # other_service: { ... }

prompts:
  classification_prompt_template: |
    请分析以下支出描述... (The Chinese prompt as set previously)
    L1 Category: <选择的主要类别名称>
    L2 Category: <选择的次要类别名称>
  # another_prompt: "..."

preset_categories:
  "Food & Drinks":
    - "Groceries"
    - "Restaurants & Dining"
  # other L1 categories...
```
(Note: The configuration functions for modifying categories and AI settings, and for saving the configuration (`save_config`), are also part of `config_manager.py` and would be documented here in a complete specification. They were detailed in Subtask 15's documentation updates.)

## 3. 模块: `llm_interface.py` (Module)

**用途 (Purpose):** 此模块负责与外部大语言模型 (LLM) API的直接通信，特别是用于支出分类。
(This module is responsible for the direct communication with external Large Language Model (LLM) APIs, specifically for expense classification.)

### 函数 (Function)

#### `get_llm_classification(description_for_ai: str, config: dict, amount: Optional[Union[float, str]] = None, channel: Optional[str] = None, source_provided_category: Optional[str] = None) -> Optional[dict]`
- **描述 (Description):** 调用配置的默认LLM API（当前默认为DeepSeek兼容API）以根据支出描述和其他可选详细信息对支出进行分类。它处理提示词格式化、API调用执行（包括重试）和解析LLM的响应。
  (Calls the configured default LLM API (currently defaults to a DeepSeek-compatible API structure) to classify an expense based on its description and other optional details. It handles prompt formatting, API call execution (including retries), and parsing the LLM's response.)
- **动态LLM服务使用 (Dynamic LLM Service Usage)**: 此函数现在根据传递的 `config` 字典中的 `default_llm_service` 键动态确定要使用的LLM服务。然后，它从 `config` 的 `llm_services` 部分使用该默认服务的特定API密钥、模型名称和模型参数。因此，`config` 参数至关重要，应为完整的应用程序配置字典。
  (This function now dynamically determines the LLM service to use based on the `default_llm_service` key within the passed `config` dictionary. It then uses the API key, model name, and model parameters specific to that default service from the `llm_services` section of the `config`. The `config` parameter is crucial and should be the complete application configuration dictionary.)
- **参数 (Parameters):**
    - `description_for_ai` (str): 用于分类的主要支出文本描述。(The primary text description of the expense used for classification.)
    - `config` (dict): 从 `config_manager.get_config()` 获取的应用程序配置字典。这提供了API密钥、提示词模板、类别列表和模型参数。
      (The application configuration dictionary obtained from `config_manager.get_config()`. This provides API keys, prompt templates, category lists, and model parameters.)
    - `amount` (Optional[Union[float, str]]): 交易金额 (可选)。(The transaction amount (optional).)
    - `channel` (Optional[str]): 支付渠道 (例如 "WeChat Pay", "Credit Card") (可选)。(The payment channel (e.g., "WeChat Pay", "Credit Card") (optional).)
    - `source_provided_category` (Optional[str]): 数据源提供的任何类别信息 (例如支付宝的类别) (可选)。(Any category information provided by the data source (e.g., Alipay's category) (optional).)
- **返回 (Returns):**
    - 如果分类成功，则返回字典 `{"ai_suggestion_l1": "L1_Category", "ai_suggestion_l2": "L2_Category"}`。
      (A dictionary `{"ai_suggestion_l1": "L1_Category", "ai_suggestion_l2": "L2_Category"}` if classification is successful.)
    - 如果分类失败、配置缺失、API密钥无效/为占位符或无法解析响应，则返回 `None`。
      (`None` if classification fails, configuration is missing, API key is invalid/placeholder, or the response cannot be parsed.)
- **注意 (Notes):**
    - 特定的LLM服务 (例如 DeepSeek) 及其参数 (模型名称) 由 `config` 字典确定。API端点URL当前在此版本中并非每个服务动态配置，但多数其他方面是动态的。
      (The specific LLM service (e.g., DeepSeek) and its parameters (model name) are determined by the `config` dictionary. The API endpoint URL itself is currently not dynamic per service in this version, but most other aspects are.)
    - 需要在 `config.yaml` 中为所选服务提供有效的API密钥。(Requires a valid API key for the selected service in `config.yaml`.)
    - 自动为LLM格式化详细的提示词，包括可用的L1和L2类别以指导响应。(Automatically formats a detailed prompt for the LLM, including available L1 and L2 categories to guide the response.)
    - 为API调用实现重试机制，以处理临时的网络问题或服务器错误。(Implements a retry mechanism for API calls to handle transient network issues or server errors.)
    - 使用正则表达式解析LLM的文本响应以提取L1和L2类别建议。(Parses the LLM's text response using regular expressions to extract L1 and L2 category suggestions.)

## 4. 模块: `expense_classifier.py` (Module)

**用途 (Purpose):** 此模块协调支出分类的过程。它使用来自数据库层（获取和更新支出记录）和其他AI层模块（`config_manager`, `llm_interface`）的功能。
(This module orchestrates the process of classifying an expense. It uses functionality from both the `database` layer (to fetch and update expense records) and other `ai_layer` modules (`config_manager`, `llm_interface`).)

### 函数 (Functions)

#### `classify_single_expense(db_conn: sqlite3.Connection, expense_id: int) -> bool`
- **描述 (Description):** 从数据库中获取特定支出，调用LLM接口获取类别建议，然后使用这些建议更新数据库中的支出记录。
  (Fetches a specific expense from the database, calls the LLM interface to get category suggestions, and then updates the expense record in the database with these suggestions.)
- **参数 (Parameters):**
    - `db_conn` (sqlite3.Connection): 活动的SQLite数据库连接对象。(An active SQLite database connection object.)
    - `expense_id` (int): 要分类的支出记录的唯一ID。(The unique ID of the expense record to be classified.)
- **返回 (Returns):**
    - `True` 如果支出成功被LLM分类并且数据库记录已更新AI建议和 `is_classified_by_ai = 1`。
      (`True` if the expense was successfully classified by the LLM and the database record was updated with the AI suggestions and `is_classified_by_ai = 1`.)
    - `False` 如果未找到支出、用户已确认、没有描述、LLM分类失败或数据库更新失败。
      (`False` if the expense is not found, already confirmed by the user, has no description, LLM classification fails, or the database update fails.)
- **注意 (Notes):**
    - **工作流程 (Workflow):**
        1. 使用 `expense_id` 从数据库检索支出详细信息。(Retrieves the expense details from the database using `expense_id`.)
        2. 检查支出是否需要分类 (例如，尚未被用户确认)。(Checks if the expense needs classification (e.g., not already confirmed by the user).)
        3. 通过 `config_manager.get_config()` 加载应用程序配置。(Loads application configuration via `config_manager.get_config()`.)
        4. 使用支出描述和其他相关详细信息调用 `llm_interface.get_llm_classification()`。(Calls `llm_interface.get_llm_classification()` with the expense description and other relevant details.)
        5. 如果LLM提供有效建议，则使用 `ai_suggestion_l1`、`ai_suggestion_l2` 更新 `expenses` 表，并将 `is_classified_by_ai` 设置为 `1`。
           (If LLM provides valid suggestions, updates the `expenses` table with `ai_suggestion_l1`, `ai_suggestion_l2`, and sets `is_classified_by_ai` to `1`.)
    - 记录分类过程的各个阶段和结果。(Logs various stages and outcomes of the classification process.)

#### `classify_batch_expenses(db_conn: Connection, limit: Optional[int] = None) -> Dict[str, Any]`
- **用途 (Purpose):** 获取并分类一批未分类/未确认的支出。(Fetches and classifies a batch of unclassified/unconfirmed expenses.)
- **参数 (Parameters):**
    - `db_conn` (sqlite3.Connection): 活动的数据库连接。(Active DB connection.)
    - `limit` (Optional[int]): (可选) 本次批处理中要处理的最大支出数量。(Optional max number of expenses to process in this batch.)
- **返回 (Returns):** 总结操作的字典 (例如，已处理、成功、失败的计数)。
  (A dictionary summarizing the operation (e.g., counts of processed, successful, failed).)
- **注意 (Notes):** 遍历支出，为每个支出调用 `llm_interface.get_llm_classification`，并更新数据库。
  (Mentions it iterates through expenses, calls `llm_interface.get_llm_classification` for each, and updates the database.)
```
