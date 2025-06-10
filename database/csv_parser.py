import csv
from datetime import datetime
import logging
from decimal import Decimal, InvalidOperation
from typing import List, Dict, Any

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Expected headers for WeChat and Alipay CSVs
WECHAT_EXPECTED_HEADERS = [
    "交易时间", "交易类型", "交易对方", "商品", "收/支", "金额(元)", "支付方式", "当前状态", "交易单号", "商户单号", "备注"
]
ALIPAY_EXPECTED_HEADERS = [
    "交易时间", "交易分类", "交易对方", "对方账号", "商品说明", "收/支", "金额", "收/付款方式", "交易状态", "交易订单号", "商家订单号", "备注"
] # Note: Alipay CSVs sometimes have leading spaces in headers, handled by stripping.

# 配置日志记录器
logger = logging.getLogger(__name__)

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

def parse_wechat_csv(file_path: str) -> List[Dict[str, Any]]:
    """
    解析微信账单 CSV 文件。
    微信账单从第 17 行开始是数据。
    """
    encodings_to_try = ['utf-8', 'gbk']
    for encoding in encodings_to_try:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                lines = f.readlines()
            
            if len(lines) < 17:
                logging.error(f"WeChat CSV file too short: {file_path}")
                return []
            
            # 从第 17 行开始读取数据
            data_start_line = 16  # 0-based index
            headers = [h.strip() for h in lines[data_start_line].strip().split(',')]
            
            # 验证必要的表头
            required_headers = ['交易时间', '商品', '金额', '收/支', '交易状态']
            if not all(h in headers for h in required_headers):
                logging.error(f"Missing required headers in WeChat CSV: {file_path}")
                return []
            
            expenses = []
            for line in lines[data_start_line + 1:]:
                if not line.strip():
                    continue
                values = [v.strip() for v in line.strip().split(',')]
                if len(values) != len(headers):
                    continue
                
                record = dict(zip(headers, values))
                if record['交易状态'] != '支付成功':
                    continue
                
                try:
                    amount = float(record['金额'])
                    if record['收/支'] == '支出':
                        amount = -amount
                    
                    expenses.append({
                        'date': record['交易时间'],
                        'amount': amount,
                        'category': record['商品'],
                        'description': record['商品'],
                        'channel': 'WeChat'
                    })
                except (ValueError, KeyError) as e:
                    logging.error(f"Error parsing WeChat record: {e}")
                    continue
            
            return expenses
        except UnicodeDecodeError:
            logging.warning(f"UnicodeDecodeError with {encoding} for file: {file_path}. Trying next encoding.")
            continue
        except Exception as e:
            logging.error(f"Error parsing WeChat CSV file {file_path}: {e}")
            return []
    
    logging.error(f"Could not parse WeChat CSV file {file_path} with any encoding.")
    return []

def parse_alipay_csv(file_path: str) -> List[Dict[str, Any]]:
    """
    Parse Alipay CSV file.
    """
    logger.info(f"Parsing Alipay CSV file: {file_path}")
    records = []
    
    # 尝试不同的编码
    encodings = ['utf-8', 'gbk', 'gb2312', 'gb18030']
    
    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                # 读取所有行
                lines = f.readlines()
                
                # 打印实际读取到的表头
                if len(lines) > 0:
                    headers = [h.strip() for h in lines[0].strip().split(',')]
                    logger.info(f"Actual headers in Alipay CSV: {headers}")
                
                # 从第25行开始读取数据
                for line in lines[24:]:  # 跳过前24行
                    if not line.strip():  # 跳过空行
                        continue
                        
                    values = [v.strip() for v in line.strip().split(',')]
                    if len(values) != len(headers):
                        logger.warning(f"Skipping malformed line: {line}")
                        continue
                        
                    record = dict(zip(headers, values))
                    
                    # 验证必要字段
                    if not all(key in record for key in ['交易时间', '商品说明', '金额', '收/支', '交易状态']):
                        logger.warning(f"Skipping record with missing required fields: {record}")
                        continue
                    
                    # 处理金额
                    try:
                        amount = float(record['金额'])
                        if record['收/支'] == '支出':
                            amount = -amount
                        record['金额'] = amount
                    except ValueError:
                        logger.warning(f"Invalid amount format: {record['金额']}")
                        continue
                    
                    # 处理时间
                    try:
                        record['交易时间'] = datetime.strptime(record['交易时间'], '%Y-%m-%d %H:%M:%S')
                    except ValueError:
                        logger.warning(f"Invalid date format: {record['交易时间']}")
                        continue
                    
                    # 转换为标准格式
                    expense = {
                        'date': record['交易时间'],
                        'amount': record['金额'],
                        'category': record['商品说明'],
                        'description': record['商品说明'],
                        'channel': 'Alipay'
                    }
                    records.append(expense)
                
                logger.info(f"Successfully parsed {len(records)} records from Alipay CSV")
                return records
                
        except UnicodeDecodeError:
            logger.warning(f"UnicodeDecodeError with {encoding} for file: {file_path}. Trying next encoding.")
            continue
        except Exception as e:
            logger.error(f"Error parsing Alipay CSV: {e}")
            return []
    
    logger.error(f"Failed to parse Alipay CSV with any encoding")
    return []

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
