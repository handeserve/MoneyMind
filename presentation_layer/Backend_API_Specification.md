# 个人支出分析器 - 后端API规范 (Personal Expense Analyzer - Backend API Specification)

## 1. 概述 (Overview)

本文档概述了个人智能支出分析器的后端API。该API允许管理支出记录、从CSV文件导入数据、触发基于AI的支出分类、检索聚合的仪表盘数据以及管理应用程序设置。

所有API端点均以 `/api/v1` 为前缀。

(This document outlines the backend API for the Personal Smart Expense Analyzer. The API allows for managing expense records, importing data from CSV files, triggering AI-based classification of expenses, retrieving aggregated dashboard data, and managing application settings. All API endpoints are prefixed with `/api/v1`.)

## 2. 认证 (Authentication)

目前，访问API端点**不需要认证**。如果应用程序部署在非私有环境中，则应解决此问题。
(Currently, **no authentication is required** to access the API endpoints. This should be addressed if the application is exposed in a non-private environment.)

## 3. 错误响应 (Error Responses)

API的错误响应通常遵循以下JSON格式：
(Error responses from the API generally follow a JSON format:)
```json
{
  "detail": "A descriptive error message."
}
```
将使用特定的HTTP状态码 (例如 400, 404, 422, 500, 501) 来指示错误的性质。
(Specific HTTP status codes (e.g., 400, 404, 422, 500, 501) will be used to indicate the nature of the error.)

## 4. 端点组: 支出管理 (`/api/v1/expenses`) (Endpoint Group: Expenses Management)

此组端点处理与单个支出记录相关的操作。
(This group of endpoints handles operations related to individual expense records.)

### 4.1 列出支出 (List Expenses)
- **Endpoint:** `GET /api/v1/expenses`
- **描述 (Description):** 检索分页的支出列表，可选择排序和筛选。 (Retrieves a paginated list of expenses, with options for sorting and filtering.)
- **查询参数 (Query Parameters):** (page, per_page, sort_by, sort_order, various filters)
- **成功响应 (Success Response) (200 OK):** `PaginatedExpensesResponse` (包含 `ExpenseResponse` 列表和分页详情 / contains list of `ExpenseResponse` and pagination details).
    - **`ExpenseResponse` 模型 (Model):** (字段包括 `id`, `transaction_time`, `amount`, `currency`, `channel`, `category_l1`, `category_l2`, `ai_suggestion_l1`, `ai_suggestion_l2`, `is_classified_by_ai`, `is_confirmed_by_user`, `is_hidden`, `notes`, `imported_at`, `updated_at`, 等。)

### 4.2 分类支出 (Classify Expense)
- **Endpoint:** `POST /api/v1/expenses/{expense_id}/classify`
- **描述 (Description):** 触发对指定支出的AI分类。 (Triggers AI classification for a specified expense.)
- **路径参数 (Path Parameter):** `expense_id` (int, required).
- **成功响应 (Success Response) (200 OK):** `ExpenseResponse` (更新后的支出对象 / the updated expense object).
- **错误响应 (Error Responses):** 404 (Not Found), 400 (Bad Request, e.g., already confirmed), 500 (Server Error).

### 4.3 更新支出 (用户确认/编辑/隐藏) (Update Expense (User Confirmation/Edit/Hide))
- **Endpoint:** `PUT /api/v1/expenses/{expense_id}`
- **描述 (Description):** 允许用户手动更新支出的类别、备注或隐藏状态。此端点支持部分更新；仅发送您希望更改的字段。
  (Allows a user to manually update an expense's categories, notes, or hidden status. This endpoint supports partial updates; only include the fields you wish to change.)
- **路径参数 (Path Parameter):** `expense_id` (int, required): 要更新的支出的ID。(The ID of the expense to update.)
- **请求体 (Request Body):** `ExpenseUpdateByUser` (所有字段均为可选 / All fields are optional)
    ```json
    // 示例 1: 确认/更新类别并添加备注
    // Example 1: Confirming/updating categories and adding a note
    {
      "category_l1": "Food & Drinks",
      "category_l2": "Restaurants & Dining",
      "notes": "Dinner with client."
    }
    // 示例 2: 隐藏支出
    // Example 2: Hiding an expense
    {
      "is_hidden": true
    }
    ```
    - **`ExpenseUpdateByUser` 模型字段 (全部可选) (Model Fields (all optional)):**
        | Field (字段)  | Type (类型)     | Description (描述)                                                        |
        |---------------|-----------------|--------------------------------------------------------------------|
        | `category_l1` | `Optional[str]` | 用户确认或分配的L1类别。(User-confirmed or assigned L1 category.)                            |
        | `category_l2` | `Optional[str]` | 用户确认或分配的L2类别。(User-confirmed or assigned L2 category.)                            |
        | `notes`       | `Optional[str]` | 支出的可选备注。(Optional notes for the expense.)                                    |
        | `is_hidden`   | `Optional[bool]`| 隐藏/取消隐藏支出的标志。(Flag to hide/unhide the expense from reports.)                      |
    - **行为说明 (Behavior Note)**: 如果提供了 `category_l1` 和 `category_l2` 且为非空字符串，则此支出的 `is_confirmed_by_user` 将自动设置为 `1` (true)。如果仅提供其他字段（如 `notes` 或 `is_hidden`），则此更新不会更改 `is_confirmed_by_user` 状态。在尝试确认类别时，如果仅提供一个类别字段或类别字段为空字符串，将导致400错误。
      (If `category_l1` and `category_l2` are provided and are non-empty strings, `is_confirmed_by_user` will be automatically set to `1` (true) for this expense. If only other fields (like `notes` or `is_hidden`) are provided, `is_confirmed_by_user` status will not be changed by this update. Providing only one category field or an empty string for a category when attempting to confirm categories will result in a 400 error.)
- **成功响应 (Success Response) (200 OK):** `ExpenseResponse` (更新后的支出对象 / the updated expense object).
- **错误响应 (Error Responses):** 400, 404, 422, 500.

### 4.4 删除支出 (Delete Expense)
- **Endpoint:** `DELETE /api/v1/expenses/{expense_id}`
- **描述 (Description):** 删除指定的支出。(Deletes a specified expense.)
- **路径参数 (Path Parameter):** `expense_id` (int, required).
- **成功响应 (Success Response) (200 OK):** `{"message": "Expense with ID {expense_id} successfully deleted."}`.
- **错误响应 (Error Responses):** 404, 500.


## 5. 端点组: 数据导入 (`/api/v1/import`) (Endpoint Group: Data Import)

### 5.1 上传CSV文件 (Upload CSV File)
- **Endpoint:** `POST /api/v1/import/csv`
- **描述 (Description):** 从CSV文件导入支出数据。(Imports expense data from a CSV file.)
- **请求格式 (Request Format):** `multipart/form-data` (字段 / Fields: `channel` (str, required), `file` (UploadFile, required)).
- **成功响应 (Success Response) (200 OK):** 包含导入摘要的JSON对象。(JSON object with import summary.)
- **错误响应 (Error Responses):** 400, 422, 500.


## 6. 端点组: 仪表盘 (`/api/v1/dashboard`) (Endpoint Group: Dashboard)

此组端点提供用于仪表盘可视化的聚合数据。
(This group of endpoints provides aggregated data for dashboard visualizations.)

### 6.1 概要统计 (Summary Statistics)
- **Endpoint:** `GET /api/v1/dashboard/summary_stats`
- **查询参数 (Query Parameters):** `start_date` (date, required), `end_date` (date, required).
- **成功响应 (Success Response) (200 OK):** `SummaryStats` 模型。(model.)

### 6.2 渠道分布 (Channel Distribution)
- **Endpoint:** `GET /api/v1/dashboard/channel_distribution`
- **查询参数 (Query Parameters):** `start_date` (date, required), `end_date` (date, required).
- **成功响应 (Success Response) (200 OK):** `List[ChannelDistributionItem]` 模型。(model.)

### 6.3 支出趋势 (Expense Trend)
- **Endpoint:** `GET /api/v1/dashboard/expense_trend`
- **查询参数 (Query Parameters):** `start_date` (date, required), `end_date` (date, required), `granularity` (str, optional, default: "daily").
- **成功响应 (Success Response) (200 OK):** `List[ExpenseTrendItem]` 模型。(model.)

### 6.4 分类支出 (Category Spending)
- **Endpoint:** `GET /api/v1/dashboard/category_spending`
- **查询参数 (Query Parameters):** `start_date` (date, required), `end_date` (date, required).
- **成功响应 (Success Response) (200 OK):** `List[CategorySpendingItem]` 模型。(model.)


## 7. 端点组: 设置 (`/api/v1/settings`) (Endpoint Group: Settings)

此组端点管理应用程序设置，主要与存储在 `config.yaml` 中的类别和AI配置相关。
(This group of endpoints manages application settings, primarily related to categories and AI configurations stored in `config.yaml`.)

### 子组: 类别管理 (Sub-Group: Category Management)
#### 7.1 获取所有类别 (Get All Categories)
- **Endpoint:** `GET /api/v1/settings/categories`
- **成功响应 (Success Response) (200 OK):** `AllCategoriesResponse`

#### 7.2 创建L1类别 (Create L1 Category)
- **Endpoint:** `POST /api/v1/settings/categories/l1`
- **请求体 (Request Body):** `CategoryL1Create`
- **成功响应 (Success Response) (201 Created):** `ResponseMessage`

#### 7.3 更新L1类别 (Update L1 Category)
- **Endpoint:** `PUT /api/v1/settings/categories/l1/{l1_name}`
- **请求体 (Request Body):** `CategoryL1Update`
- **成功响应 (Success Response) (200 OK):** `ResponseMessage`

#### 7.4 删除L1类别 (Delete L1 Category)
- **Endpoint:** `DELETE /api/v1/settings/categories/l1/{l1_name}`
- **成功响应 (Success Response) (200 OK):** `ResponseMessage`

#### 7.5 创建L2类别 (Create L2 Category)
- **Endpoint:** `POST /api/v1/settings/categories/l1/{l1_name}/l2`
- **请求体 (Request Body):** `CategoryL2Create`
- **成功响应 (Success Response) (201 Created):** `ResponseMessage`

#### 7.6 更新L2类别 (Update L2 Category)
- **Endpoint:** `PUT /api/v1/settings/categories/l2/{l1_name}/{l2_name}`
- **请求体 (Request Body):** `CategoryL2Update`
- **成功响应 (Success Response) (200 OK):** `ResponseMessage`

#### 7.7 删除L2类别 (Delete L2 Category)
- **Endpoint:** `DELETE /api/v1/settings/categories/l2/{l1_name}/{l2_name}`
- **成功响应 (Success Response) (200 OK):** `ResponseMessage`

### 子组: AI配置管理 (Sub-Group: AI Configuration Management)
#### 7.8 获取AI配置 (Get AI Configuration)
- **Endpoint:** `GET /api/v1/settings/ai_config`
- **成功响应 (Success Response) (200 OK):** `AIConfigResponse` (API密钥已屏蔽 / API keys masked)

#### 7.9 更新AI配置 (Update AI Configuration)
- **Endpoint:** `PUT /api/v1/settings/ai_config`
- **请求体 (Request Body):** `AIConfigUpdate`
- **成功响应 (Success Response) (200 OK):** `ResponseMessage`


## 8. 端点组: AI处理 (`/api/v1/ai`) (Endpoint Group: AI Processing)

此组端点处理直接的AI处理任务。(This group of endpoints handles direct AI processing tasks.)

### 8.1 触发批量支出分类 (Trigger Batch Expense Classification)
- **Endpoint:** `POST /api/v1/ai/batch_classify_expenses`
- **描述 (Description):** 启动一个批处理过程，对尚未被AI分类或用户确认的支出进行分类。(Initiates a batch process to classify expenses that have not yet been classified by AI or confirmed by the user.)
- **请求体 (可选) (Request Body (Optional)):** 基于 `BatchClassifyRequest` 模型的JSON对象。(JSON object based on `BatchClassifyRequest` model.)
    ```json
    // 示例: 处理最多100条支出
    // Example: Process up to 100 expenses
    {
      "limit": 100 
    }
    // 如果请求体不存在、为空JSON {}，或者limit为null/未提供，
    // 后端将根据其默认行为处理支出 (例如，所有符合条件的或预定义的批处理大小)。
    // If body is absent, empty JSON {}, or limit is null/not provided, 
    // the backend will process expenses based on its default behavior (e.g., all eligible or a predefined batch size).
    ```
    - **`BatchClassifyRequest` 模型 (Model):**
        | Field (字段) | Type (类型)    | Description (描述)                                                                |
        |--------------|----------------|-----------------------------------------------------------------------------------|
        | `limit`      | int (Optional) | (可选) 正整数，限制此批处理中处理的支出数量。(Optional positive integer to limit the number of expenses processed in this batch.) |
- **成功响应 (Success Response) (200 OK):** 总结批处理操作的JSON对象。(JSON object summarizing the batch operation.)
    ```json
    // 示例 (Example)
    {
      "total_matching_criteria": 50, 
      "processed_in_this_batch": 20, 
      "successfully_classified": 18, 
      "failed_to_classify": 2,       
      "message": "Batch classification process completed." // 可选的服务器消息 (Optional server message)
    }
    ```
    - **响应键描述 (Response Keys Description):**
        - `total_matching_criteria`: 本次运行前数据库中符合批量分类条件的总支出数。
        - `processed_in_this_batch`: 本次运行中实际选择并尝试分类的支出数量（如果提供了`limit`则遵循该限制）。
        - `successfully_classified`: 被LLM成功分类并在数据库中更新记录的支出数量。
        - `failed_to_classify`: 已处理但由于LLM错误、解析问题或数据库更新失败而无法分类或更新的支出数量。
        - `message`: 来自服务器的可选消息，提供有关批处理运行的更多上下文或特定信息。
- **错误响应 (Error Responses):**
    - `422 Unprocessable Entity`: 如果请求体 (`limit`) 存在但无效 (例如，非正整数)。
    - `500 Internal Server Error`: 如果批处理过程中遇到意外问题。
```
