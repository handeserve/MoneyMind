import sqlite3
import logging
from datetime import datetime, timezone
from decimal import Decimal
import os
import re # Added for _generate_cleaned_description
from dataclasses import dataclass
from typing import List, Optional

from .csv_parser import parse_wechat_csv, parse_alipay_csv

# Configure basic logging
logger = logging.getLogger(__name__) # Use module-level logger for consistency

class ImportSummary:
    def __init__(self):
        self.total = 0
        self.imported = 0
        self.skipped = 0
        self.failed = 0
        self.channel = None
        self.file_name = None
        self.import_time = None
    
    def __str__(self):
        return (
            f"Import Summary:\n"
            f"Total Records: {self.total}\n"
            f"Imported: {self.imported}\n"
            f"Skipped: {self.skipped}\n"
            f"Failed: {self.failed}\n"
            f"Channel: {self.channel}\n"
            f"File: {self.file_name}\n"
            f"Import Time: {self.import_time}"
        )

def _generate_cleaned_description(source_raw_description: str, channel: str) -> str:
    """
    Cleans the raw expense description to make it more suitable for AI processing.
    """
    if not source_raw_description:
        return ""

    cleaned = source_raw_description
    
    # Common generic prefixes/suffixes and patterns to remove or normalize
    # Order matters here: more specific or aggressive rules might go first or last.
    
    # Phase 1: Remove common clutter prefixes (case-insensitive for some)
    # These are often added by payment platforms and are redundant.
    generic_prefixes_to_remove = [
        r"^(微信支付-)+",
        r"^(支付宝-)+",
        r"^(付款-)+",
        r"^(支付-)+",
        r"^(转账给-)+",
        r"^(收款方-)+",
        r"^(花呗扣款-)+", 
        r"^(花呗-)+",      # Simplified from "花呗扣款-" to catch more variations
        r"^(余额宝-)+",   
        r"^(零钱通-)+",   
        r"^(零钱-)+",     # For WeChat "零钱"
        r"^(扫码付款-)+",
        r"^(扫码支付-)+",
        r"^(消费-)+",
        r"^(购物消费-)+",
        r"^(交易类型：消费，备注：)+", # Very specific example of clutter
        r"^(交易类型：扫码支付，备注：)+",
    ]
    for prefix_pattern in generic_prefixes_to_remove:
        # Using re.IGNORECASE for broader matching of prefixes like "Wechat Pay-" etc.
        # Some prefixes are case-sensitive in Chinese, but good to be flexible.
        cleaned = re.sub(prefix_pattern, '', cleaned, flags=re.IGNORECASE)

    # Phase 2: Remove common clutter suffixes or internal patterns
    # (Currently none defined, but could be added, e.g., trailing transaction IDs if they slip in)

    # Phase 3: Specific common replacements or normalizations
    cleaned = cleaned.replace("付款给", "") # Remove "付款给" if it's internal after prefix removal
    
    # Phase 4: Normalize separators if possible (e.g., "美团-" vs "美团 - ")
    # This is tricky; for now, focus on stripping.
    # Example: "美团-单车" might be better as "美团 - 单车" for some LLMs.
    # cleaned = re.sub(r'(?<=[^\s])-?(?=[^\s])', ' - ', cleaned) # Careful with this, might be too aggressive

    # Phase 5: Strip leading/trailing hyphens, spaces, and other non-alphanumeric characters
    # that might have resulted from replacements.
    cleaned = cleaned.strip()
    # Remove leading/trailing hyphens that are standalone or surrounded by spaces
    cleaned = re.sub(r"^\s*-\s*", "", cleaned) 
    cleaned = re.sub(r"\s*-\s*$", "", cleaned)
    # Remove other common leading/trailing noise characters (e.g., colons, slashes if they are truly noise)
    # cleaned = cleaned.strip(' :/') # Example, be cautious with this

    # Phase 6: Consolidate multiple spaces into one
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    
    # If cleaning results in an empty string, or a string that's just a separator,
    # it might be better to revert to original or a placeholder.
    if not cleaned or cleaned == "-" or cleaned == "/":
        logger.debug(f"Cleaning resulted in empty or minimal string for '{source_raw_description}'. Reverting to original or keeping as is if original was also minimal.")
        # Decide whether to return original or the (empty/minimal) cleaned version.
        # For AI, an empty string is often better than a meaningless one if it means "no useful info".
        # If the original was also empty/minimal, then cleaned is fine.
        return source_raw_description if (not cleaned and source_raw_description) else cleaned

    logger.debug(f"Cleaned description: '{source_raw_description}' -> '{cleaned}' (Channel: {channel})")
    return cleaned


def _check_duplicate(cursor, parsed_record, channel):
    """
    Checks if a substantially similar record already exists in the expenses table.
    (Content from previous implementation)
    """
    query = """
    SELECT id FROM expenses
    WHERE channel = ? AND transaction_time = ? AND amount = ? AND external_transaction_id = ?
    """
    try:
        cursor.execute(query, (
            channel,
            parsed_record['transaction_time'], 
            str(parsed_record['amount']),      
            parsed_record['external_transaction_id']
        ))
        return cursor.fetchone() is not None
    except sqlite3.Error as e:
        logger.error(f"Error checking for duplicates for external_id {parsed_record.get('external_transaction_id', 'N/A')}: {e}")
        return False 


def _insert_expense(cursor, parsed_record, channel, current_time_iso):
    """
    Inserts a single parsed expense record into the expenses table.
    (Content from previous implementation, with description_for_ai updated)
    """
    sql = """
    INSERT INTO expenses (
        transaction_time, amount, currency, channel, source_raw_description,
        description_for_ai, notes, external_transaction_id, external_merchant_id,
        source_provided_category, source_payment_method, source_transaction_status,
        is_classified_by_ai, is_confirmed_by_user, is_hidden,
        imported_at, updated_at,
        category_l1, category_l2, ai_suggestion_l1, ai_suggestion_l2
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    try:
        # Generate cleaned description for AI
        # source_raw_description is already in parsed_record from csv_parser
        cleaned_description_for_ai = _generate_cleaned_description(
            parsed_record.get('source_raw_description', ''),
            channel # Pass channel to cleaning function
        )

        data_tuple = (
            parsed_record['transaction_time'],
            str(parsed_record['amount']), 
            parsed_record.get('currency', 'CNY'),
            channel, 
            parsed_record.get('source_raw_description'),
            cleaned_description_for_ai, # Use the cleaned description
            parsed_record.get('notes'),
            parsed_record.get('external_transaction_id'),
            parsed_record.get('external_merchant_id'),
            parsed_record.get('source_provided_category'),
            parsed_record.get('source_payment_method'),
            parsed_record.get('source_transaction_status'),
            0, 0, 0, # is_classified_by_ai, is_confirmed_by_user, is_hidden
            current_time_iso, current_time_iso, # imported_at, updated_at
            None, None, None, None # category_l1, category_l2, ai_suggestion_l1, ai_suggestion_l2
        )
        cursor.execute(sql, data_tuple)
        return True
    except sqlite3.Error as e:
        if "UNIQUE constraint failed: expenses.external_transaction_id" in str(e):
            logger.warning(f"Record with external_transaction_id '{parsed_record.get('external_transaction_id')}' already exists. Skipping.")
            return "duplicate_external_id"
        logger.error(f"Error inserting expense record with external_id {parsed_record.get('external_transaction_id', 'N/A')}: {e}")
        return False
    except KeyError as e:
        logger.error(f"Missing expected key in parsed_record for external_id {parsed_record.get('external_transaction_id', 'N/A')}: {e}")
        return False


def _record_import_source(db: sqlite3.Connection, channel: str, file_path: str) -> int:
    """
    记录导入来源信息到 import_sources 表。
    
    Args:
        db: 数据库连接
        channel: 数据来源渠道
        file_path: 导入文件路径
    
    Returns:
        int: 导入记录ID
    """
    try:
        cursor = db.cursor()
        cursor.execute("""
            INSERT INTO import_sources (
                file_name,
                source_channel,
                import_timestamp,
                records_imported,
                status
            ) VALUES (?, ?, ?, ?, ?)
        """, (
            os.path.basename(file_path),
            channel,
            datetime.now(timezone.utc).isoformat(),
            0,  # 初始值，后续更新
            'In Progress'
        ))
        db.commit()
        return cursor.lastrowid
    except Exception as e:
        logger.error(f"Error recording import source: {str(e)}")
        raise


def import_data(file_path: str, channel: str, db: sqlite3.Connection) -> ImportSummary:
    """
    导入数据到数据库
    
    Args:
        file_path: CSV文件路径
        channel: 数据来源渠道（'alipay', 'wechat', 'Alipay', 'WeChat'）
        db: 数据库连接对象
    
    Returns:
        ImportSummary: 导入结果摘要
    """
    logger.info(f"Starting import from {file_path} for channel {channel}")
    
    # 统一渠道名称映射
    channel_mapping = {
        'alipay': 'alipay',
        'wechat': 'wechat',
        'Alipay': 'alipay',
        'WeChat': 'wechat'
    }
    
    normalized_channel = channel_mapping.get(channel)
    if not normalized_channel:
        raise ValueError(f"Unsupported channel: {channel}")
    
    summary = ImportSummary()
    summary.channel = normalized_channel
    summary.file_name = os.path.basename(file_path)
    summary.import_time = datetime.now(timezone.utc).isoformat()
    
    try:
        # 解析CSV文件
        if normalized_channel == 'alipay':
            records = parse_alipay_csv(file_path)
        else:  # wechat
            records = parse_wechat_csv(file_path)
        
        if not records:
            logger.warning(f"No records found in {file_path}")
            return summary
        
        summary.total = len(records)
        
        # 记录导入来源
        import_id = _record_import_source(db, normalized_channel, file_path)
        
        # 导入数据
        for record in records:
            try:
                result = _insert_expense(db.cursor(), record, normalized_channel, summary.import_time)
                if result == True:
                    summary.imported += 1
                elif result == "duplicate_external_id":
                    summary.skipped += 1
                else:
                    summary.failed += 1
            except Exception as e:
                logger.error(f"Error importing record: {str(e)}")
                summary.failed += 1
        
        # 提交所有更改
        db.commit()
        
        logger.info(f"Import completed: {summary.imported} records imported, {summary.skipped} skipped, {summary.failed} failed")
        return summary
        
    except Exception as e:
        logger.error(f"Error during import: {str(e)}")
        raise


def _import_alipay_record(db: sqlite3.Connection, record: dict, import_id: int) -> None:
    """
    导入单条支付宝记录
    
    Args:
        db: 数据库连接
        record: 记录数据
        import_id: 导入记录ID
    """
    cursor = db.cursor()
    
    # 检查是否已存在相同的外部ID
    cursor.execute("SELECT id FROM expenses WHERE external_id = ?", (record['external_id'],))
    if cursor.fetchone():
        return
    
    # 插入新记录
    cursor.execute("""
        INSERT INTO expenses (
            transaction_time,
            amount,
            description,
            category,
            channel,
            external_id,
            import_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        record['transaction_time'],
        record['amount'],
        record['description'],
        record['category'],
        'Alipay',
        record['external_id'],
        import_id
    ))
    db.commit()

def _import_wechat_record(db: sqlite3.Connection, record: dict, import_id: int) -> None:
    """
    导入单条微信记录
    
    Args:
        db: 数据库连接
        record: 记录数据
        import_id: 导入记录ID
    """
    cursor = db.cursor()
    
    # 检查是否已存在相同的外部ID
    cursor.execute("SELECT id FROM expenses WHERE external_id = ?", (record['external_id'],))
    if cursor.fetchone():
        return
    
    # 插入新记录
    cursor.execute("""
        INSERT INTO expenses (
            transaction_time,
            amount,
            description,
            category,
            channel,
            external_id,
            import_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        record['transaction_time'],
        record['amount'],
        record['description'],
        record['category'],
        'WeChat',
        record['external_id'],
        import_id
    ))
    db.commit()


if __name__ == '__main__':
    import csv 
    from .database import get_db_connection, create_tables, DATABASE_PATH, get_expense_by_id # Added get_expense_by_id for testing
    
    # Setup basic config for logger in __main__ if not already configured by module-level basicConfig
    if not logging.getLogger().hasHandlers(): # Check if root logger has handlers
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    logger.info(f"Data Importer Test: Using database for test: {DATABASE_PATH}")

    conn = get_db_connection()
    if not conn:
        logger.error("Data Importer Test: Failed to get DB connection. Exiting.")
        exit(1)
    
    create_tables(conn) 

    test_data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "test_data")
    os.makedirs(test_data_dir, exist_ok=True)

    # Updated test data with examples for cleaning
    wechat_test_file_main = os.path.join(test_data_dir, "wechat_import_test_main.csv")
    alipay_test_file_main = os.path.join(test_data_dir, "alipay_import_test_main.csv")
    
    WECHAT_HEADERS = ["交易时间", "交易类型", "交易对方", "商品", "收/支", "金额(元)", "支付方式", "当前状态", "交易单号", "商户单号", "备注"]
    ALIPAY_HEADERS = ["交易时间", "交易分类", "交易对方", "对方账号", "商品说明", "收/支", "金额", "收/付款方式", "交易状态", "交易订单号", "商家订单号", "备注"]

    # Sample data for WeChat CSV including cases for cleaning
    wechat_test_records = [
        WECHAT_HEADERS,
        ["2024-07-01 12:30:00", "餐饮美食", "美味小吃店", "午餐", "支出", "¥25.50", "微信支付", "支付成功", "WXTX_CLEAN_001", "MCHT_CLEAN_001", "工作餐"],
        ["2024-07-02 10:00:00", "购物", "微信支付-Apple Store", "iPhone配件", "支出", "¥199.00", "零钱", "支付成功", "WXTX_CLEAN_002", "MCHT_CLEAN_002", "配件"],
        ["2024-07-03 15:00:00", "交通", "付款-滴滴出行", "快车", "支出", "¥35.00", "银行卡", "支付成功", "WXTX_CLEAN_003", "MCHT_CLEAN_003", ""],
        ["2024-07-04 18:00:00", "餐饮", "扫码付款-星巴克（静安店）", "咖啡", "支出", "¥32.00", "零钱通", "支付成功", "WXTX_CLEAN_004", "MCHT_CLEAN_004", "下午茶"],
        ["2024-07-05 09:00:00", "购物", "微信支付-付款给淘宝卖家-小明", "运动鞋", "支出", "¥280.00", "微信支付", "支付成功", "WXTX_CLEAN_005", "MCHT_CLEAN_005", ""]
    ]
    with open(wechat_test_file_main, 'w', newline='', encoding='utf-8') as f:
        f.write("微信支付账单明细列表\n----------------------\n")
        csv.writer(f).writerows(wechat_test_records)

    # Sample data for Alipay CSV including cases for cleaning
    alipay_test_records = [
        [' ' + h + ' ' for h in ALIPAY_HEADERS], # Simulate Alipay's spaced headers
        ["2024-07-01 10:20:30", "数码产品", "网络商城", "user@example.com", "智能手表", "支出", "1299.00", "花呗", "交易成功", "ALITX_CLEAN_001", "ALIMCHT_CLEAN_001", "新年礼物"],
        ["2024-07-02 14:00:00", "餐饮美食", "支付宝-肯德基宅急送", "外卖", "支出", "58.50", "余额宝", "交易成功", "ALITX_CLEAN_002", "ALIMCHT_CLEAN_002", "午餐"],
        ["2024-07-03 16:30:00", "生活缴费", "花呗扣款-中国移动", "手机充值", "支出", "100.00", "花呗", "交易成功", "ALITX_CLEAN_003", "ALIMCHT_CLEAN_003", ""],
        ["2024-07-04 19:00:00", "购物", "消费-UNIQLO（南京路店）", "T恤", "支出", "99.00", "银行卡(招行)", "交易成功", "ALITX_CLEAN_004", "ALIMCHT_CLEAN_004", "夏季促销"]
    ]
    with open(alipay_test_file_main, 'w', newline='', encoding='utf-8') as f:
        f.write("支付宝交易记录明细查询\n------------------------------------交易记录明细列表------------------------------------\n")
        csv.writer(f).writerows(alipay_test_records)
        f.write("--------------------------------------支付宝业务咨询专线：95188--------------------------------------\n")

    logger.info(f"Data Importer Test: Created dummy WeChat import test file: {wechat_test_file_main}")
    logger.info(f"Data Importer Test: Created dummy Alipay import test file: {alipay_test_file_main}")

    # Test Imports and Check Cleaned Descriptions
    test_ids_to_check = []

    logger.info("\n--- Data Importer Test: Testing WeChat Import with Cleaning ---")
    wechat_result = import_data(wechat_test_file_main, "WeChat", conn)
    logger.info(f"WeChat Import Result: {wechat_result}")
    if wechat_result.imported > 0:
        # Fetch last N imported records for verification (assuming IDs are sequential)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM expenses WHERE channel='WeChat' ORDER BY id DESC LIMIT ?", (wechat_result.imported,))
        test_ids_to_check.extend([row[0] for row in cursor.fetchall()])


    logger.info("\n--- Data Importer Test: Testing Alipay Import with Cleaning ---")
    alipay_result = import_data(alipay_test_file_main, "Alipay", conn)
    logger.info(f"Alipay Import Result: {alipay_result}")
    if alipay_result.imported > 0:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM expenses WHERE channel='Alipay' ORDER BY id DESC LIMIT ?", (alipay_result.imported,))
        test_ids_to_check.extend([row[0] for row in cursor.fetchall()])
    
    logger.info("\n--- Data Importer Test: Verifying Cleaned Descriptions ---")
    if test_ids_to_check:
        for expense_id in reversed(test_ids_to_check): # Show in order of insertion if possible
            expense_details = get_expense_by_id(conn, expense_id) # Assuming this now returns a dict
            if expense_details:
                logger.info(f"  ID: {expense_id}, Channel: {expense_details['channel']}")
                logger.info(f"    Raw Desc: '{expense_details['source_raw_description']}'")
                logger.info(f"    AI Desc:  '{expense_details['description_for_ai']}'")
            else:
                logger.warning(f"  Could not retrieve expense ID {expense_id} for verification.")
    else:
        logger.info("  No expenses were imported to verify.")

    # Clean up test files (optional, keep them for inspection if needed)
    # os.remove(wechat_test_file_main)
    # os.remove(alipay_test_file_main)
    
    conn.close()
    logger.info("Data Importer Test: Test script finished.")
