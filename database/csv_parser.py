import csv
from datetime import datetime
import logging
from decimal import Decimal, InvalidOperation

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Expected headers for WeChat and Alipay CSVs
WECHAT_EXPECTED_HEADERS = [
    "交易时间", "交易类型", "交易对方", "商品", "收/支", "金额(元)", "支付方式", "当前状态", "交易单号", "商户单号", "备注"
]
ALIPAY_EXPECTED_HEADERS = [
    "交易时间", "交易分类", "交易对方", "对方账号", "商品说明", "收/支", "金额", "收/付款方式", "交易状态", "交易订单号", "商家订单号", "备注"
] # Note: Alipay CSVs sometimes have leading spaces in headers, handled by stripping.

def _parse_datetime(datetime_str):
    """Parses a datetime string into ISO 8601 format YYYY-MM-DD HH:MM:SS."""
    if not datetime_str or datetime_str.strip() == '/': # Handle empty or placeholder values
        return None
    try:
        # Common formats: YYYY-MM-DD HH:MM:SS or YYYY/MM/DD HH:MM
        dt_obj = datetime.strptime(datetime_str.replace('/', '-'), '%Y-%m-%d %H:%M:%S')
    except ValueError:
        try:
            dt_obj = datetime.strptime(datetime_str.replace('/', '-'), '%Y-%m-%d %H:%M')
        except ValueError:
            logging.warning(f"Could not parse datetime string: {datetime_str}. Returning None.")
            return None
    return dt_obj.strftime('%Y-%m-%d %H:%M:%S')

def _clean_amount(amount_str, currency_symbol="元"):
    """Removes currency symbol and converts to positive Decimal."""
    if not amount_str:
        return None
    cleaned_str = amount_str.replace(currency_symbol, "").strip()
    try:
        amount_decimal = Decimal(cleaned_str)
        return abs(amount_decimal) # Ensure positive
    except InvalidOperation:
        logging.warning(f"Could not convert amount string to Decimal: {amount_str}. Returning None.")
        return None

def _get_row_value(row, header_map, key, default=''):
    """Safely get a value from a row using the header map, stripping whitespace."""
    value = row.get(header_map.get(key, ''), default).strip()
    # Alipay CSVs often have "\t" at the end of some fields, remove it
    if value.endswith('\t'):
        value = value[:-1].strip()
    return value

def parse_wechat_csv(file_path):
    """
    Parses a WeChat Pay CSV export file.

    Args:
        file_path (str): The path to the CSV file.

    Returns:
        list: A list of dictionaries, each representing a parsed expense.
              Returns an empty list if errors occur (e.g., file not found, critical parsing error).
    """
    expenses = []
    encodings_to_try = ['utf-8', 'gbk']
    file_content = None

    for encoding in encodings_to_try:
        try:
            with open(file_path, 'r', encoding=encoding, newline='') as f:
                # WeChat CSV often starts with metadata lines before the actual header
                lines = f.readlines()
                header_row_index = -1
                for i, line in enumerate(lines):
                    if "交易时间" in line and "交易对方" in line: # Heuristic to find header
                        header_row_index = i
                        break
                
                if header_row_index == -1:
                    logging.error(f"Could not find header row in WeChat CSV: {file_path}")
                    return []

                # Re-join lines from header onwards for CSV reader
                csv_content_lines = lines[header_row_index:]
                
                # Clean headers by removing BOM and stripping whitespace
                csv_content_lines[0] = csv_content_lines[0].lstrip('\ufeff').strip()
                
                reader = csv.DictReader(csv_content_lines, skipinitialspace=True)
                
                # Normalize header keys by stripping whitespace
                reader.fieldnames = [header.strip() for header in reader.fieldnames]
                
                # Create a map for current file headers to expected headers
                # This is less critical if we access by exact (stripped) names
                # but good for robustness if slight variations are expected.
                # For now, we assume exact match after stripping.

                # Validate essential headers
                missing_headers = [h for h in WECHAT_EXPECTED_HEADERS if h not in reader.fieldnames]
                if missing_headers:
                    logging.error(f"Missing expected columns in WeChat CSV {file_path} (encoding: {encoding}): {', '.join(missing_headers)}. Found headers: {reader.fieldnames}")
                    # If critical headers are missing, we might not be able to proceed
                    if any(h in missing_headers for h in ["交易时间", "金额(元)", "收/支", "当前状态", "交易单号"]):
                        continue # Try next encoding or fail

            file_content_ready = True # Flag to indicate successful read and header validation
            break # Successfully read the file
        except FileNotFoundError:
            logging.error(f"File not found: {file_path}")
            return []
        except UnicodeDecodeError:
            logging.warning(f"UnicodeDecodeError with {encoding} for file: {file_path}. Trying next encoding.")
            continue
        except Exception as e:
            logging.error(f"An unexpected error occurred while opening/reading WeChat CSV {file_path} with {encoding}: {e}")
            return [] # Or raise e if specific handling is not possible

    if not file_content_ready:
        logging.error(f"Could not read or process headers for WeChat CSV: {file_path} after trying all encodings.")
        return []

    for row_num, row in enumerate(reader, start=1): # reader defined in the encoding loop
        try:
            # Normalize row keys (some CSVs might have spaces in keys within data rows)
            # This is usually handled by DictReader if headers are clean.
            # For safety, one could strip keys from row if issues persist:
            # row = {k.strip(): v for k,v in row.items()}

            # Filtering
            if _get_row_value(row, {h:h for h in reader.fieldnames}, "收/支") != "支出":
                continue
            if _get_row_value(row, {h:h for h in reader.fieldnames}, "当前状态") != "支付成功":
                continue

            amount_val = _clean_amount(_get_row_value(row, {h:h for h in reader.fieldnames}, "金额(元)"))
            if amount_val is None:
                logging.warning(f"Skipping row {row_num} in {file_path} due to invalid amount.")
                continue
            
            transaction_time_str = _get_row_value(row, {h:h for h in reader.fieldnames}, "交易时间")
            parsed_time = _parse_datetime(transaction_time_str)
            if not parsed_time:
                logging.warning(f"Skipping row {row_num} in {file_path} due to unparseable transaction time: {transaction_time_str}")
                continue

            trade_partner = _get_row_value(row, {h:h for h in reader.fieldnames}, "交易对方")
            item_name = _get_row_value(row, {h:h for h in reader.fieldnames}, "商品")
            source_raw_description = f"{trade_partner} - {item_name}".strip()
            if source_raw_description == "-": source_raw_description = item_name or trade_partner # Avoid " - " if one is empty

            expense = {
                "transaction_time": parsed_time,
                "amount": amount_val,
                "currency": "CNY",
                "channel": "WeChat Pay",
                "source_raw_description": source_raw_description,
                "description_for_ai": source_raw_description, # Initially same as raw
                "notes": _get_row_value(row, {h:h for h in reader.fieldnames}, "备注"),
                "external_transaction_id": _get_row_value(row, {h:h for h in reader.fieldnames}, "交易单号"),
                "external_merchant_id": _get_row_value(row, {h:h for h in reader.fieldnames}, "商户单号"),
                "source_payment_method": _get_row_value(row, {h:h for h in reader.fieldnames}, "支付方式"),
                "source_transaction_status": _get_row_value(row, {h:h for h in reader.fieldnames}, "当前状态"),
                # Fields to be filled later or by user/AI
                "category_l1": None,
                "category_l2": None,
                "ai_suggestion_l1": None,
                "ai_suggestion_l2": None,
                "is_classified_by_ai": 0,
                "is_confirmed_by_user": 0,
                "is_hidden": 0,
                "source_provided_category": None, # WeChat doesn't have this directly
            }
            expenses.append(expense)
        except Exception as e:
            logging.error(f"Error processing row {row_num} in WeChat CSV {file_path}: {row}. Error: {e}")
            # Decide if one row error should stop all parsing or just skip the row
            continue 
    
    logging.info(f"Successfully parsed {len(expenses)} expenses from WeChat CSV: {file_path}")
    return expenses


def parse_alipay_csv(file_path):
    """
    Parses an Alipay CSV export file.

    Args:
        file_path (str): The path to the CSV file.

    Returns:
        list: A list of dictionaries, each representing a parsed expense.
              Returns an empty list if errors occur.
    """
    expenses = []
    encodings_to_try = ['utf-8', 'gbk']
    file_content_ready = False

    for encoding in encodings_to_try:
        try:
            with open(file_path, 'r', encoding=encoding, newline='') as f:
                lines = f.readlines()
                
                # Alipay CSVs often have comment lines at the start and end.
                # Find the actual data block.
                data_start_index = -1
                data_end_index = len(lines)

                for i, line in enumerate(lines):
                    line_stripped = line.strip()
                    if line_stripped.startswith("支付宝交易记录明细查询"): # Skip this informational header
                        continue
                    if line_stripped.startswith("----------------------"): # Delimiter line
                        if data_start_index == -1: # First delimiter is before headers
                            data_start_index = i + 1 
                        else: # Second delimiter is after data
                            data_end_index = i
                            break 
                
                if data_start_index == -1:
                    # Fallback: try to find header row directly if no delimiters
                    for i, line in enumerate(lines):
                         if "交易号" in line and "商家订单号" in line: # Alipay specific header names
                            data_start_index = i
                            break
                    if data_start_index == -1:
                        logging.error(f"Could not find data block or header row in Alipay CSV: {file_path} with {encoding}")
                        continue


                csv_content_lines = lines[data_start_index:data_end_index]
                
                if not csv_content_lines:
                    logging.error(f"No data lines found between delimiters/header in Alipay CSV: {file_path}")
                    continue

                # Clean headers: remove BOM, strip whitespace
                csv_content_lines[0] = csv_content_lines[0].lstrip('\ufeff').strip()
                
                # Alipay headers often have leading/trailing spaces AND sometimes internal spaces
                # Standard csv.DictReader handles leading/trailing spaces in headers if skipinitialspace=True.
                # For internal spaces or if headers are not perfectly clean, manual cleaning is better.
                
                # Manually parse the header line to clean it thoroughly
                header_line = csv_content_lines[0]
                cleaned_headers = [h.strip() for h in header_line.split(',')]

                # Use the rest of the lines for the DictReader, but pass the cleaned headers
                reader = csv.DictReader(csv_content_lines[1:], fieldnames=cleaned_headers, skipinitialspace=True)

                # Create a map of original (stripped) header to itself, useful for _get_row_value
                header_map = {h: h for h in cleaned_headers}

                # Validate essential headers
                # Alipay uses "交易订单号", "商家订单号" for its IDs.
                # "交易状态" for status, "金额" for amount, "收/支" for direction.
                # "商品说明" for item name.
                
                # Check for a few key headers to ensure it's a valid Alipay file
                # Note: Alipay header names can vary slightly based on export version.
                # Common names: '交易号', '商家订单号', '交易对方', '商品名称', '金额（元）', '收/支', '交易状态'
                # The provided list is: "交易时间", "交易分类", "交易对方", "对方账号", "商品说明", "收/支", "金额", "收/付款方式", "交易状态", "交易订单号", "商家订单号", "备注"
                
                # Adapt ALIPAY_EXPECTED_HEADERS to what's typically found or use a more flexible check
                current_headers_set = set(cleaned_headers)
                missing_headers = [h for h in ALIPAY_EXPECTED_HEADERS if h not in current_headers_set]

                if missing_headers:
                    # Flexible check: if a few key headers are present, proceed.
                    # This is a simplified check. A more robust one might map aliases.
                    core_alipay_headers = ["交易时间", "金额", "收/支", "交易状态", "交易订单号"]
                    if not all(h in current_headers_set for h in core_alipay_headers):
                        logging.error(f"Missing some core columns in Alipay CSV {file_path} (encoding: {encoding}): {missing_headers}. Found: {cleaned_headers}")
                        continue
                    else:
                        logging.warning(f"Some expected columns missing in Alipay CSV {file_path} (encoding: {encoding}): {missing_headers}. Proceeding as core headers found.")


            file_content_ready = True
            break # Successfully read and prepared the file
        except FileNotFoundError:
            logging.error(f"File not found: {file_path}")
            return []
        except UnicodeDecodeError:
            logging.warning(f"UnicodeDecodeError with {encoding} for file: {file_path}. Trying next encoding.")
            continue
        except Exception as e:
            logging.error(f"An unexpected error occurred while opening/reading Alipay CSV {file_path} with {encoding}: {e}")
            return []

    if not file_content_ready:
        logging.error(f"Could not read or process headers for Alipay CSV: {file_path} after trying all encodings.")
        return []

    for row_num, row in enumerate(reader, start=1): # reader defined in the encoding loop
        try:
            # Alipay specific filtering
            # Column names for Alipay: "收/支", "交易状态"
            # Values: "支出", "交易成功"
            
            # _get_row_value expects a map of "logical_name" to "actual_header_name_in_file"
            # Since we normalized headers, logical_name and actual_header_name_in_file are the same.
            
            if _get_row_value(row, header_map, "收/支") != "支出":
                continue
            # Alipay status can be "交易成功", "等待付款", etc.
            # Sometimes "已关闭" for refunds not covered here.
            status_val = _get_row_value(row, header_map, "交易状态")
            if status_val != "交易成功": # Add other success-like statuses if necessary
                # e.g. if "退款成功" should be parsed as income, that's a different logic.
                # For expenses, "交易成功" is the primary one.
                continue

            amount_val = _clean_amount(_get_row_value(row, header_map, "金额"), currency_symbol="") # Alipay doesn't use '元' in amount field
            if amount_val is None:
                logging.warning(f"Skipping row {row_num} in {file_path} due to invalid amount.")
                continue
            
            transaction_time_str = _get_row_value(row, header_map, "交易时间")
            parsed_time = _parse_datetime(transaction_time_str)
            if not parsed_time:
                logging.warning(f"Skipping row {row_num} in {file_path} due to unparseable transaction time: {transaction_time_str}")
                continue

            trade_partner = _get_row_value(row, header_map, "交易对方")
            item_name = _get_row_value(row, header_map, "商品说明") # Alipay uses "商品说明"
            source_raw_description = f"{trade_partner} - {item_name}".strip()
            if source_raw_description == "-": source_raw_description = item_name or trade_partner


            expense = {
                "transaction_time": parsed_time,
                "amount": amount_val,
                "currency": "CNY",
                "channel": "Alipay",
                "source_raw_description": source_raw_description,
                "description_for_ai": source_raw_description, # Initially same as raw
                "notes": _get_row_value(row, header_map, "备注"),
                "external_transaction_id": _get_row_value(row, header_map, "交易订单号"), # Alipay: "交易订单号" or "交易号"
                "external_merchant_id": _get_row_value(row, header_map, "商家订单号"), # Alipay: "商家订单号" or "商户订单号"
                "source_provided_category": _get_row_value(row, header_map, "交易分类"), # Alipay has "交易分类"
                "source_payment_method": _get_row_value(row, header_map, "收/付款方式"),
                "source_transaction_status": status_val,
                # Fields to be filled later or by user/AI
                "category_l1": None,
                "category_l2": None,
                "ai_suggestion_l1": None,
                "ai_suggestion_l2": None,
                "is_classified_by_ai": 0,
                "is_confirmed_by_user": 0,
                "is_hidden": 0,
            }
            expenses.append(expense)
        except Exception as e:
            logging.error(f"Error processing row {row_num} in Alipay CSV {file_path}: {row}. Error: {e}")
            continue
            
    logging.info(f"Successfully parsed {len(expenses)} expenses from Alipay CSV: {file_path}")
    return expenses

if __name__ == '__main__':
    # Basic test cases (requires creating dummy CSV files)
    # Create dummy personal_expense_analyzer/test_data directory if it doesn't exist
    import os
    test_data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "test_data")
    if not os.path.exists(test_data_dir):
        os.makedirs(test_data_dir)

    # Dummy WeChat CSV
    wechat_test_file = os.path.join(test_data_dir, "wechat_test.csv")
    with open(wechat_test_file, 'w', newline='', encoding='utf-8') as f:
        f.write("微信支付账单明细列表\n")
        f.write("导出时间：2024-01-15 10:00:00\n")
        f.write("----------------------\n")
        writer = csv.writer(f)
        writer.writerow(WECHAT_EXPECTED_HEADERS)
        writer.writerow(["2024-01-01 12:30:00", "餐饮美食", "美味小吃店", "午餐", "支出", "¥25.50", "微信支付", "支付成功", "WXTX123456789", "MCHT987654321", "工作餐"])
        writer.writerow(["2024-01-02 10:00:00", "其他", "某某公司", "退款", "收入", "¥10.00", "微信支付", "退款成功", "WXTXREFUND001", "MCHTREF001", "商品退货"])
        writer.writerow(["2024-01-03 18:45:15", "购物", "电子商城", "耳机", "支出", "¥199.00", "微信支付", "支付成功", "WXTXABCDE123", "MCHTUYXWV456", ""])
        writer.writerow(["2024-01-04 09:00:00", "交通出行", "公交公司", "公交卡充值", "支出", "¥50.00", "零钱", "支付成功", "WXTXCHARGE789", "MCHTCHARGE101", "月度充值"])
        writer.writerow(["2024-01-05 15:20:30", "红包", "朋友A", "微信红包", "支出", "¥88.00", "微信红包", "已发送", "WXTXHB001", "MCHTHB002", "生日快乐"]) # This should be filtered by status
        writer.writerow(["2024-01-06 11:11:11", "餐饮美食", "咖啡店", "拿铁", "支出", "¥30.00", "微信支付", "支付失败", "WXTXFAIL001", "MCHTFAIL002", "网络问题"]) # Filtered by status
        writer.writerow(["2024-01-07 12:00:00", "转账", "朋友B", "转账", "/", "¥200.00", "微信转账", "已转账", "WXTXTRANSFER01", "MCHTTRANSFER02", ""]) # Should be filtered by 收/支 = /
        writer.writerow(["2024-01-08 14:35:00", "生活缴费", "电力公司", "电费", "支出", "¥150.75", "微信支付", "支付成功", "WXTXUTILITY001", "MCHTUTILITY002", "账单"])
        writer.writerow([" ", " ", " ", " ", " ", " ", " ", " ", " ", " ", " "]) # Empty row test
        writer.writerow(["2024-01-09 16:00:00", "医疗健康", "药店", "感冒药", "支出", "¥45.30", "微信支付", "支付成功", "WXTXMED001", "MCHTMED002", ""])
        # Test case for missing amount
        writer.writerow(["2024-01-10 10:00:00", "餐饮美食", "早餐铺", "包子", "支出", "", "微信支付", "支付成功", "WXTXEMPTYAMT", "MCHTEMPTYAMT", ""])
        # Test case for unparseable date
        writer.writerow(["INVALID DATE", "餐饮美食", "早餐铺", "豆浆", "支出", "¥2.00", "微信支付", "支付成功", "WXTXINVALIDDATE", "MCHTINVALIDDATE", ""])


    logging.info(f"Created dummy WeChat test file: {wechat_test_file}")
    wechat_expenses = parse_wechat_csv(wechat_test_file)
    print(f"\n--- Parsed WeChat Expenses ({len(wechat_expenses)} items) ---")
    for exp in wechat_expenses:
        print(exp)

    # Dummy Alipay CSV
    alipay_test_file = os.path.join(test_data_dir, "alipay_test.csv")
    with open(alipay_test_file, 'w', newline='', encoding='gbk') as f: # Alipay often GBK
        f.write("支付宝交易记录明细查询\n")
        f.write("起始日期：2024-01-01 00:00:00    终止日期：2024-01-15 23:59:59\n")
        f.write("------------------------------------交易记录明细列表------------------------------------\n")
        # Write headers with potential leading/trailing spaces to simulate real files
        writer = csv.writer(f)
        writer.writerow([' ' + h + ' ' for h in ALIPAY_EXPECTED_HEADERS])
        writer.writerow(["2024-01-01 10:20:30", "数码产品", "网络商城", "user@example.com", "智能手表", "支出", "1299.00", "花呗", "交易成功", "ALITX123456", "ALIMCHT654321", "新年礼物"])
        writer.writerow(["2024-01-02 15:00:00", "餐饮美食", "快餐店", "shop@example.com", "套餐A", "收入", "35.00", "余额宝", "交易成功", "ALITXINCOME01", "ALIMCHTINCOME01", "误操作退款"]) # Filtered by 收/支
        writer.writerow(["2024-01-03 20:05:00", "服饰装扮", "品牌服装店", "cloth@example.com", "冬季外套", "支出", "599.50", "银行卡(招商银行)", "交易成功", "ALITXABCDEF", "ALIMCHTUVWXYZ", ""])
        writer.writerow(["2024-01-04 08:15:45", "交通出行", "地铁", "metro@example.com", "地铁票", "支出", "4.00", "支付宝余额", "交易成功", "ALITXMETRO01", "ALIMCHTMETRO02", "上班"])
        writer.writerow(["2024-01-05 17:30:00", "生活日用", "超市", "supermarket@example.com", "食品和饮料", "支出", "120.80", "信用卡(建设银行)", "已关闭", "ALITXCLOSED01", "ALIMCHTCLOSED01", "订单取消"]) # Filtered by status
        writer.writerow(["2024-01-06 22:00:10", "转账收款", "朋友C", "friend_c@example.com", "转账", "不计收支", "100.00", "支付宝", "转账成功", "ALITXTRANSFER01", "ALIMCHTTRANSFER02", "还款"]) # Filtered by 收/支
        writer.writerow(["2024-01-07 13:40:00", "充值提现", "某游戏", "game@example.com", "游戏点券", "支出", "50.00", "余额宝", "交易成功", "ALITXGAME001", "ALIMCHTGAME002", ""])
        writer.writerow([" ", " ", " ", " ", " ", " ", " ", " ", " ", " ", " ", " "]) # Empty row test
        writer.writerow(["2024-01-08 19:00:00", "餐饮美食", "特色餐厅", "restaurant@example.com", "晚餐聚会", "支出", "350.00", "花呗分期", "交易成功", "ALITXDINE001", "ALIMCHTDINE002", "朋友生日"])
        # Test case for missing amount
        writer.writerow(["2024-01-09 10:00:00", "生活日用", "便利店", "store@example.com", "零食", "支出", " ", "支付宝余额", "交易成功", "ALITXEMPTYAMT", "ALIMCHTEMPTYAMT", ""])
        # Test case for unparseable date
        writer.writerow(["INVALID DATE", "生活日用", "便利店", "store@example.com", "饮料", "支出", "5.00", "支付宝余额", "交易成功", "ALITXINVALIDDATE", "ALIMCHTINVALIDDATE", ""])
        f.write("--------------------------------------支付宝业务咨询专线：95188--------------------------------------\n")
        f.write("总交易笔数：XX,收入总金额：XX,支出总金额：XX\n")

    logging.info(f"Created dummy Alipay test file: {alipay_test_file}")
    alipay_expenses = parse_alipay_csv(alipay_test_file)
    print(f"\n--- Parsed Alipay Expenses ({len(alipay_expenses)} items) ---")
    for exp in alipay_expenses:
        print(exp)

    # Test non-existent file
    print("\n--- Testing non-existent file ---")
    non_existent_expenses = parse_wechat_csv("non_existent_file.csv")
    print(f"Non-existent WeChat file result: {non_existent_expenses} (Expected: [])")
    non_existent_alipay = parse_alipay_csv("non_existent_file.csv")
    print(f"Non-existent Alipay file result: {non_existent_alipay} (Expected: [])")

    # Test empty file
    empty_file_path = os.path.join(test_data_dir, "empty.csv")
    open(empty_file_path, 'w').close()
    print("\n--- Testing empty file ---")
    empty_wechat_expenses = parse_wechat_csv(empty_file_path)
    print(f"Empty WeChat file result: {empty_wechat_expenses} (Expected: [])")
    empty_alipay_expenses = parse_alipay_csv(empty_file_path)
    print(f"Empty Alipay file result: {empty_alipay_expenses} (Expected: [])")
    os.remove(empty_file_path)

    # Test CSV with only headers
    header_only_path = os.path.join(test_data_dir, "header_only.csv")
    with open(header_only_path, 'w', newline='', encoding='utf-8') as f:
         writer = csv.writer(f)
         writer.writerow(WECHAT_EXPECTED_HEADERS) # Use WeChat for this generic test
    print("\n--- Testing header-only file ---")
    header_only_wechat = parse_wechat_csv(header_only_path)
    print(f"Header-only WeChat result: {header_only_wechat} (Expected: [])")
    os.remove(header_only_path)

    # Test CSV with incorrect/missing critical headers
    bad_header_path = os.path.join(test_data_dir, "bad_header.csv")
    with open(bad_header_path, 'w', newline='', encoding='utf-8') as f:
         writer = csv.writer(f)
         writer.writerow(["Some", "Random", "Headers", "Not", "Useful"])
         writer.writerow(["data1", "data2", "data3", "data4", "data5"])
    print("\n--- Testing bad header file ---")
    bad_header_wechat = parse_wechat_csv(bad_header_path)
    print(f"Bad header WeChat result: {bad_header_wechat} (Expected: [])")
    os.remove(bad_header_path)


    # Clean up dummy files
    # os.remove(wechat_test_file)
    # os.remove(alipay_test_file)
    # logging.info("Cleaned up dummy test files.")
    logging.info(f"Dummy test files are located at: {wechat_test_file} and {alipay_test_file}")
    logging.info("Please inspect them and the output above for correctness.")
    logging.info("To re-run, execute `python personal_expense_analyzer/database/csv_parser.py`")
