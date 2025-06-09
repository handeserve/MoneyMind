# 个人支出分析器 - 数据库API文档 (Personal Expense Analyzer - Database API Documentation)

## 1. 概述 (Overview)

数据库层负责与SQLite数据库的所有交互。这包括建立连接、定义结构、创建表，以及提供支出数据的增删改查（CRUD）操作API。它还包含了用于解析支付平台（微信支付、支付宝）CSV文件并将数据导入数据库的模块，以及执行数据聚合以进行分析的功能。

数据库文件名为 `personal_expenses.db`，位于项目根目录。

(The database layer is responsible for all interactions with the SQLite database. This includes establishing connections, defining the schema, creating tables, and providing an API for Create, Read, Update, and Delete (CRUD) operations on the expense data. It also includes modules for parsing CSV files from payment platforms (WeChat Pay, Alipay), importing that data into the database, and performing data aggregations for analytics. The database file is named `personal_expenses.db` and is located in the project root directory.)

## 2. 数据库结构 (Database Schema)

数据库主要包含两个表：`expenses` 和 `import_sources`。(The database consists of two main tables: `expenses` and `import_sources`.)

### `expenses` 表 (Table)

存储单条支出记录。(Stores individual expense records.)

| Column (列名)            | Type (类型) | Description (描述)                                                                 | Constraints (约束)              |
|-------------------------|-----------|------------------------------------------------------------------------------------|---------------------------------|
| id                      | INTEGER   | 支出记录的唯一标识符 (Unique identifier for the expense record)                                    | PRIMARY KEY AUTOINCREMENT       |
| transaction_time        | TEXT      | 交易时间，ISO 8601格式 (YYYY-MM-DD HH:MM:SS) (Transaction time in ISO 8601 format)                   | NOT NULL                        |
| amount                  | TEXT      | 交易金额，以字符串存储以保持精度 (代表Decimal) (Transaction amount, stored as string for precision) | NOT NULL                        |
| currency                | TEXT      | 货币代码 (例如 'CNY') (Currency code (e.g., 'CNY'))                                                 | NOT NULL DEFAULT 'CNY'          |
| channel                 | TEXT      | 支出渠道 (例如 'WeChat Pay', 'Alipay', 'Manual Test') (Source channel of the expense) |                                 |
| source_raw_description  | TEXT      | 从导入源或手动输入的原始描述 (Raw description from source or manually entered)                |                                 |
| description_for_ai      | TEXT      | 清理/格式化后用于AI处理的描述 (Cleaned/formatted description for AI processing)                             |                                 |
| category_l1             | TEXT      | 分配给支出的一级分类 (例如 '餐饮', '交通') (Top-level category)    |                                 |
| category_l2             | TEXT      | 分配给支出的二级分类 (例如 '餐馆', '地铁') (Sub-category)          |                                 |
| ai_suggestion_l1        | TEXT      | AI建议的一级分类 (AI-suggested top-level category)                                             |                                 |
| ai_suggestion_l2        | TEXT      | AI建议的二级分类 (AI-suggested sub-category)                                                   |                                 |
| is_classified_by_ai     | INTEGER   | 布尔值 (0或1)，指示AI是否已分类此支出 (Boolean (0 or 1) if AI classified)              | NOT NULL DEFAULT 0              |
| is_confirmed_by_user    | INTEGER   | 布尔值 (0或1)，指示用户是否已确认分类 (Boolean (0 or 1) if user confirmed)  | NOT NULL DEFAULT 0              |
| is_hidden               | INTEGER   | 布尔值 (0或1)，指示此支出是否应在报告中隐藏 (Boolean (0 or 1) if hidden from reports)  | NOT NULL DEFAULT 0              |
| notes                   | TEXT      | 用户为支出添加的备注 (User-added notes)                                            |                                 |
| external_transaction_id | TEXT      | 源平台的唯一交易ID (例如微信、支付宝) (Unique transaction ID from source)     | UNIQUE                          |
| external_merchant_id    | TEXT      | 源平台的唯一商户ID (Unique merchant ID from source)                                 |                                 |
| source_provided_category| TEXT      | 源数据提供的分类信息 (例如支付宝的分类) (Category from source)  |                                 |
| source_payment_method   | TEXT      | 源数据中的支付方式详情 (例如 '花呗', '零钱') (Payment method from source)               |                                 |
| source_transaction_status| TEXT     | 源数据中的交易状态 (例如 '支付成功', '交易成功') (Transaction status from source)           |                                 |
| imported_at             | TEXT      | 记录导入或创建时的时间戳 (ISO 8601) (Timestamp of import/creation)                | NOT NULL                        |
| updated_at              | TEXT      | 记录最后更新时的时间戳 (ISO 8601) (Timestamp of last update)                       | NOT NULL                        |

### `import_sources` 表 (Table)

存储导入文件的元数据。(Stores metadata about imported files.)

| Column (列名)      | Type (类型) | Description (描述)                                                        | Constraints (约束)        |
|--------------------|-----------|---------------------------------------------------------------------------|---------------------------|
| id                 | INTEGER   | 导入记录的唯一标识符 (Unique identifier for the import record)                            | PRIMARY KEY AUTOINCREMENT |
| file_name          | TEXT      | 导入的CSV文件名 (Name of the imported CSV file)                                      | NOT NULL                  |
| source_channel     | TEXT      | 文件所属渠道 (例如 "WeChat Pay", "Alipay") (Channel the file belongs to)     | NOT NULL                  |
| import_timestamp   | TEXT      | 导入过程运行的时间戳 (ISO 8601) (Timestamp when import was run)               | NOT NULL                  |
| records_imported   | INTEGER   | 从此文件成功导入的记录数 (Number of records successfully imported)             | NOT NULL                  |
| status             | TEXT      | 导入状态 (例如 "Success", "Partial", "Failed (Parsing)") (Status of the import) |                           |

## 3. 模块: `database.py` (Module)

此模块提供数据库连接、表创建以及`expenses`表的核心CRUD操作功能。(This module provides core functionalities for database connection, table creation, and CRUD operations on the `expenses` table.)

### `get_db_connection()`
- **用途 (Purpose):** 建立并返回与SQLite数据库的连接。设置 `row_factory` 为 `sqlite3.Row` 以便按列名进行类似字典的访问。(Establishes and returns a connection to the SQLite database. Sets `row_factory` to `sqlite3.Row` for dictionary-like access to columns.)
- **参数 (Parameters):** 无 (None)
- **返回 (Returns):** `sqlite3.Connection` 对象，如果连接失败则为 `None`。(`sqlite3.Connection` object, or `None` if connection fails.)

### `create_tables(db_connection)`
- **用途 (Purpose):** 如果数据库中尚不存在 `expenses` 和 `import_sources` 表，则创建它们。(Creates the `expenses` and `import_sources` tables in the database if they do not already exist.)
- **参数 (Parameters):**
  - `db_connection` (`sqlite3.Connection`): 一个活动的SQLite连接对象。(An active SQLite connection object.)
- **返回 (Returns):** 无 (None)

### `create_expense(db_connection, expense_data)`
- **用途 (Purpose):** 在 `expenses` 表中创建一条新的支出记录。(Creates a new expense record in the `expenses` table.)
- **参数 (Parameters):**
  - `db_connection` (`sqlite3.Connection`): 一个活动的SQLite连接对象。(An active SQLite connection object.)
  - `expense_data` (`dict`): 包含新支出数据的字典。(A dictionary containing the data for the new expense.)
    - 必需键 (示例) (Required keys (example)): `transaction_time` (str, ISO 8601), `amount` (str or Decimal), `channel` (str), `source_raw_description` (str).
    - `amount` 将被转换为字符串存储。(amount will be converted to a string for storage.)
- **返回 (Returns):** `int` (新创建支出的ID)，如果创建失败则为 `None`。(`int` (the ID of the newly created expense) or `None` if creation fails.)

### `get_expense_by_id(db_connection, expense_id)`
- **用途 (Purpose):** 通过ID检索特定的支出记录。(Retrieves a specific expense record by its ID.)
- **参数 (Parameters):**
  - `db_connection` (`sqlite3.Connection`): 一个活动的SQLite连接对象。(An active SQLite connection object.)
  - `expense_id` (`int`): 要检索的支出的ID。(The ID of the expense to retrieve.)
- **返回 (Returns):** `dict` (表示支出行，键为列名) 或如果未找到该ID的支出则为 `None`。(`dict` (representing the expense row) or `None` if no expense with that ID is found.)

### `get_expenses(db_connection, page=1, per_page=10, sort_by='transaction_time', sort_order='ASC', filters=None)`
- **用途 (Purpose):** 检索分页、排序和筛选后的支出列表。(Retrieves a paginated, sorted, and filtered list of expenses.)
- **参数 (Parameters):** (如前定义 / As previously defined)
- **返回 (Returns):** 包含键 `'expenses'` (`list` of `dict`) 和 `'total_count'` (`int`) 的字典。(`dict` with keys `'expenses'` (`list` of `dict`) and `'total_count'` (`int`).)

### `get_unclassified_expenses(db_connection, limit=None)`
- **用途 (Purpose):** 检索尚未被AI分类 (`is_classified_by_ai = 0`) 且未被用户确认 (`is_confirmed_by_user = 0`) 的支出。(Retrieves expenses not yet classified by AI AND not confirmed by user.)
- **参数 (Parameters):** (如前定义 / As previously defined)
- **返回 (Returns):** `list` of `dict` (支出行列表 / list of expense rows).

### `update_expense(db_connection, expense_id, update_data)`
- **用途 (Purpose):** 更新现有的支出记录。`updated_at` 字段会自动设置为当前时间戳。(Updates an existing expense record. `updated_at` is automatically set.)
- **参数 (Parameters):** (如前定义 / As previously defined)
- **返回 (Returns):** `bool` (`True` 如果成功, `False` 否则 / `True` if successful, `False` otherwise).

### `delete_expense(db_connection, expense_id)`
- **用途 (Purpose):** 通过ID删除支出记录。(Deletes an expense record by its ID.)
- **参数 (Parameters):** (如前定义 / As previously defined)
- **返回 (Returns):** `bool` (`True` 如果成功, `False` 否则 / `True` if successful, `False` otherwise).


## 4. 模块: `csv_parser.py` (Module)

此模块负责解析从微信支付和支付宝导出的CSV文件。(This module is responsible for parsing CSV files exported from WeChat Pay and Alipay.)

### `parse_wechat_csv(file_path)`
- **用途 (Purpose):** 解析微信支付CSV导出文件。(Parses a WeChat Pay CSV export file.)
- **参数 (Parameters):** `file_path` (str).
- **返回 (Returns):** `list` of `dict` (解析后的支出列表 / list of parsed expenses). 结构包括 `transaction_time`, `amount` (Decimal), `channel` ("WeChat Pay"), `source_raw_description`, `external_transaction_id`, 等。(Structure includes `transaction_time`, `amount` (Decimal), `channel` ("WeChat Pay"), `source_raw_description`, `external_transaction_id`, etc.)

### `parse_alipay_csv(file_path)`
- **用途 (Purpose):** 解析支付宝CSV导出文件。(Parses an Alipay CSV export file.)
- **参数 (Parameters):** `file_path` (str).
- **返回 (Returns):** `list` of `dict` (解析后的支出列表 / list of parsed expenses). 结构包括 `transaction_time`, `amount` (Decimal), `channel` ("Alipay"), `source_raw_description`, `external_transaction_id`, `source_provided_category`, 等。(Structure includes `transaction_time`, `amount` (Decimal), `channel` ("Alipay"), `source_raw_description`, `external_transaction_id`, `source_provided_category`, etc.)


## 5. 模块: `data_importer.py` (Module)

此模块处理将 `csv_parser.py` 解析的数据导入数据库的过程。(This module handles the process of importing data parsed by `csv_parser.py` into the database.)

### `import_data(db_connection, file_path, channel)`
- **用途 (Purpose):** 将CSV文件中的支出数据导入 `expenses` 表。处理重复数据并在 `import_sources` 表中记录导入尝试。(Imports expense data from a CSV file into the `expenses` table. Handles duplicates and records import in `import_sources`.)
- **参数 (Parameters):**
  - `db_connection` (`sqlite3.Connection`): 活动的SQLite连接。(Active SQLite connection.)
  - `file_path` (`str`): CSV文件的路径。(Path to the CSV file.)
  - `channel` (`str`): "WeChat Pay" 或 "Alipay".("WeChat Pay" or "Alipay".)
- **返回 (Returns):** `dict` 总结导入操作 (总记录数，已导入，已跳过，错误，状态消息)。(`dict` summarizing the import (total records, imported, skipped, errors, status message).)


## 6. 模块: `analytics.py` - 仪表盘聚合函数 (Dashboard Aggregation Functions)

此模块提供查询和聚合支出数据以用于仪表盘可视化的功能。除非另有说明，所有聚合函数都排除 `is_hidden = 1` 的记录。金额以浮点数形式返回，并四舍五入到两位小数。
(This module provides functions to query and aggregate expense data for dashboard visualizations. All aggregation functions exclude records where `is_hidden = 1`, unless specified otherwise. Amounts are returned as floats, rounded to 2 decimal places.)

### `get_summary_stats(db_conn: sqlite3.Connection, start_date: date, end_date: date) -> Dict[str, Any]`
- **用途 (Purpose):** 计算指定日期范围内的总支出和日均支出。(Calculates total expenses and average daily expenses within a specified date range.)
- **参数 (Parameters):**
    - `db_conn` (`sqlite3.Connection`): 活动的SQLite数据库连接。(Active SQLite database connection.)
    - `start_date` (`datetime.date`): 时期的开始日期 (包含)。(The start date of the period (inclusive).)
    - `end_date` (`datetime.date`): 时期的结束日期 (包含)。(The end date of the period (inclusive).)
- **返回值 (Return Value):** `Dict[str, Any]`
    ```python
    {
        "total_expenses": float,  # 期间总支出 (Total sum of expenses in the period)
        "average_daily_expenses": float, # 日均支出 (Average daily expenses)
        "start_date": date,       # 提供的开始日期 (The provided start_date)
        "end_date": date          # 提供的结束日期 (The provided end_date)
    }
    ```
    - 如果未找到支出或发生错误，则金额返回0.0。(Returns 0.0 for amounts if no expenses are found or in case of error.)

### `get_spending_by_channel(db_conn: sqlite3.Connection, start_date: date, end_date: date) -> List[Dict[str, Any]]`
- **用途 (Purpose):** 计算指定日期范围内每个支付渠道的总支出。过滤掉渠道值为空或空字符串的记录。(Calculates the total spending for each payment channel within the specified date range. Filters out records with null or empty channel values.)
- **参数 (Parameters):** (同上 / Same as above)
- **返回值 (Return Value):** `List[Dict[str, Any]]`
    ```python
    [
        {"channel": "ChannelName1", "total_amount": float},
        {"channel": "ChannelName2", "total_amount": float},
        # ...
    ]
    ```
    - 列表按 `total_amount` 降序排列。如果无相关支出或出错，则返回空列表。(List is ordered by `total_amount` in descending order. Returns an empty list if no relevant expenses or on error.)

### `get_expense_trend(db_conn: sqlite3.Connection, start_date: date, end_date: date, granularity: str) -> List[Dict[str, Any]]`
- **用途 (Purpose):** 按指定的时间粒度（日、周、月）计算总支出的趋势。(Calculates the trend of total expenses over time, grouped by the specified granularity (daily, weekly, or monthly).)
- **参数 (Parameters):**
    - `db_conn`, `start_date`, `end_date`: (同上 / Same as above)
    - `granularity` (`str`): 分组的时间单位。接受的值："daily", "weekly", "monthly"。(The time unit for grouping. Accepted values: "daily", "weekly", "monthly".)
- **返回值 (Return Value):** `List[Dict[str, Any]]`
    ```python
    [
        {"date_period": "YYYY-MM-DD", "total_amount": float}, # 日粒度 (For daily)
        # {"date_period": "YYYY-WW", "total_amount": float},    # 周粒度 (WW 是周数) (For weekly (WW is week number))
        # {"date_period": "YYYY-MM", "total_amount": float},    # 月粒度 (For monthly)
        # ...
    ]
    ```
    - 列表按 `date_period` 升序排列。如果无相关支出或出错，则返回空列表。(List is ordered by `date_period` in ascending order. Returns an empty list if no relevant expenses or on error.)

### `get_spending_by_l1_category(db_conn: sqlite3.Connection, start_date: date, end_date: date) -> List[Dict[str, Any]]`
- **用途 (Purpose):** 计算指定日期范围内每个L1类别的总支出。此函数仅考虑用户已确认 (`is_confirmed_by_user = 1`) 的支出，并过滤掉 `category_l1` 为空或空字符串的记录。(Calculates the total spending for each L1 category within the specified date range. This function only considers expenses that are user-confirmed (`is_confirmed_by_user = 1`) and filters out records with null or empty `category_l1` values.)
- **参数 (Parameters):** (同上 / Same as above)
- **返回值 (Return Value):** `List[Dict[str, Any]]`
    ```python
    [
        {"category_l1": "L1CategoryName1", "total_amount": float},
        {"category_l1": "L1CategoryName2", "total_amount": float},
        # ...
    ]
    ```
    - 列表按 `total_amount` 降序排列。如果无相关支出或出错，则返回空列表。(List is ordered by `total_amount` in descending order. Returns an empty list if no relevant expenses or on error.)
```
