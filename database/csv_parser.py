import csv
from datetime import datetime
import logging
from decimal import Decimal, InvalidOperation
from typing import List, Dict, Any
import re

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
    """Cleans and converts amount string to float."""
    if not amount_str or amount_str.strip() == '':
        return 0.0
    
    # Remove currency symbols and whitespace
    cleaned = amount_str.replace('¥', '').replace(currency_symbol, '').strip()
    try:
        return float(cleaned)
    except ValueError:
        logger.warning(f"Could not parse amount: {amount_str}")
        return 0.0

def _get_row_value(row, header_map, key, default=''):
    """Helper to get value from row using header mapping."""
    index = header_map.get(key, -1)
    if index >= 0 and index < len(row):
        return row[index].strip()
    return default

def parse_wechat_csv(file_path: str) -> List[Dict[str, Any]]:
    """
    解析微信账单 CSV 文件。
    微信CSV文件格式：前面有大量元数据，然后是"----------------------微信支付账单明细列表--------------------"分隔符，
    接着是表头，然后是实际数据行。数据行可能是制表符分隔或逗号分隔。
    """
    encodings_to_try = ['utf-8', 'gbk', 'utf-8-sig']
    
    for encoding in encodings_to_try:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                content = f.read()
                
            lines = content.split('\n')
            
            if len(lines) < 20:
                logger.error(f"WeChat CSV file too short: {file_path}")
                continue

            # 查找表头行（在"----------------------微信支付账单明细列表--------------------"之后）
            header_line_index = -1
            data_start_index = -1
            
            for i, line in enumerate(lines):
                line = line.strip()
                # 寻找包含所有必要字段的表头行
                if ('交易时间' in line and '交易对方' in line and '金额' in line and 
                    '收/支' in line and '当前状态' in line):
                    header_line_index = i
                    data_start_index = i + 1
                    break
                
            if header_line_index == -1:
                logger.error(f"Could not find header line in WeChat CSV: {file_path}")
                continue
            
            # 解析表头
            header_line = lines[header_line_index].strip()
            
            # 微信CSV表头通常是逗号分隔
            if ',' in header_line:
                # 使用CSV reader处理可能包含逗号的表头
                reader = csv.reader([header_line])
                headers = [h.strip().replace('"', '') for h in next(reader)]
            else:
                # 如果没有逗号，可能是制表符分隔
                headers = [h.strip().replace('"', '') for h in header_line.split('\t')]
            
            logger.info(f"Found WeChat headers at line {header_line_index + 1}: {headers}")
            
            # 创建表头映射
            header_map = {}
            for i, header in enumerate(headers):
                header_map[header] = i
            
            # 验证必要的表头
            required_headers = ['交易时间', '金额(元)', '收/支', '当前状态']
            missing_headers = [h for h in required_headers if h not in header_map]
            if missing_headers:
                logger.error(f"Missing required headers in WeChat CSV: {missing_headers}")
                continue
            
            records = []
            for line_num, line in enumerate(lines[data_start_index:], start=data_start_index + 1):
                line = line.strip()
                if not line or len(line) < 10:
                    continue
                    
                try:
                    # 解析数据行
                    row = []
                    
                    # 首先尝试使用CSV reader（处理逗号分隔和引号包围）
                    try:
                        reader = csv.reader([line])
                        row = next(reader)
                    except:
                        # 如果CSV reader失败，尝试制表符分隔
                        if '\t' in line:
                            row = [field.strip().replace('"', '') for field in line.split('\t')]
                        else:
                            # 最后尝试简单的逗号分隔
                            row = [field.strip().replace('"', '') for field in line.split(',')]
                    
                    # 过滤掉明显不完整的行
                    if len(row) < len(headers) - 2:  # 允许缺少最后几个字段
                        continue
                    
                    # 确保row有足够的元素
                    while len(row) < len(headers):
                        row.append('')
                    
                    # 获取关键字段
                    transaction_time = _get_row_value(row, header_map, '交易时间')
                    amount_str = _get_row_value(row, header_map, '金额(元)')
                    transaction_type = _get_row_value(row, header_map, '收/支')
                    status = _get_row_value(row, header_map, '当前状态')
                    merchant = _get_row_value(row, header_map, '交易对方')
                    product = _get_row_value(row, header_map, '商品')
                    payment_method = _get_row_value(row, header_map, '支付方式')
                    transaction_id = _get_row_value(row, header_map, '交易单号')
                    merchant_id = _get_row_value(row, header_map, '商户单号')
                    note = _get_row_value(row, header_map, '备注')
                    category = _get_row_value(row, header_map, '交易类型')
                    
                    # 过滤无效记录
                    if not transaction_time or not amount_str:
                        continue
                        
                    # 只处理成功的支出交易
                    if status not in ['支付成功', '已转账', '对方已收钱', '对方已退还']:
                        continue
                        
                    if transaction_type not in ['支出']:
                        continue
                    
                    # 解析时间
                    parsed_time = _parse_datetime(transaction_time)
                    if not parsed_time:
                        continue
                        
                    # 解析金额
                    amount = _clean_amount(amount_str)
                    if amount <= 0:
                        continue
                    
                    # 构建描述
                    description_parts = []
                    if merchant and merchant != '/':
                        description_parts.append(merchant)
                    if product and product != '/':
                        description_parts.append(product)
                    if note and note != '/':
                        description_parts.append(note)
                    
                    description = ' - '.join(description_parts) if description_parts else '微信支付'
                    
                    record = {
                        'transaction_time': parsed_time,
                        'amount': -amount,  # 支出为负数
                        'currency': 'CNY',
                        'channel': 'wechat',  # 统一使用小写
                        'source_raw_description': description,
                        'description_for_ai': description,
                        'external_transaction_id': transaction_id,
                        'external_merchant_id': merchant_id,
                        'source_provided_category': category,
                        'source_payment_method': payment_method,
                        'source_transaction_status': status
                    }
                    
                    records.append(record)
                    
                except Exception as e:
                    logger.warning(f"Error parsing WeChat line {line_num}: {str(e)}")
                    continue
            
            logger.info(f"Successfully parsed {len(records)} records from WeChat CSV")
            return records
            
        except UnicodeDecodeError:
            logger.warning(f"UnicodeDecodeError with {encoding} for file: {file_path}. Trying next encoding.")
            continue
        except Exception as e:
            logger.error(f"Error parsing WeChat CSV file {file_path} with {encoding}: {e}")
            continue

    logger.error(f"Could not parse WeChat CSV file {file_path} with any encoding.")
    return []

def parse_alipay_csv(file_path: str) -> List[Dict[str, Any]]:
    """
    解析支付宝CSV文件
    """
    logger.info(f"Parsing Alipay CSV file: {file_path}")
    records = []

    # 尝试不同的编码
    encodings_to_try = ['gbk', 'utf-8', 'utf-8-sig']
    
    for encoding in encodings_to_try:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                lines = f.readlines()
                
            # 查找表头行
            header_line_index = -1
            for i, line in enumerate(lines):
                if '交易时间' in line and '交易分类' in line and '金额' in line:
                    header_line_index = i
                    break 
                
            if header_line_index == -1:
                logger.error("Could not find header line in Alipay CSV file")
                continue
            
            # 获取表头
            header_line = lines[header_line_index].strip()
            headers = [h.strip() for h in header_line.split(',')]
            logger.info(f"Found Alipay headers at line {header_line_index + 1}: {headers}")
            
            # 创建表头映射
            header_map = {}
            for i, header in enumerate(headers):
                header_map[header] = i
            
            # 验证必要的表头
            required_headers = ['交易时间', '金额', '收/支', '交易状态']
            missing_headers = [h for h in required_headers if h not in header_map]
            if missing_headers:
                logger.error(f"Missing required headers in Alipay CSV: {missing_headers}")
                continue
            
            # 从表头后开始读取数据
            for line_num, line in enumerate(lines[header_line_index + 1:], start=header_line_index + 2):
                line = line.strip()
                if not line or line.startswith('-') or ',' not in line:
                    continue

                try:
                    # 使用CSV reader处理可能包含逗号的字段
                    reader = csv.reader([line])
                    row = next(reader)
                    
                    if len(row) < len(headers):
                        logger.warning(f"Skipping malformed line {line_num}: insufficient fields")
                        continue
                    
                    # 获取关键字段
                    transaction_time = _get_row_value(row, header_map, '交易时间')
                    amount_str = _get_row_value(row, header_map, '金额')
                    transaction_type = _get_row_value(row, header_map, '收/支')
                    status = _get_row_value(row, header_map, '交易状态')
                    merchant = _get_row_value(row, header_map, '交易对方')
                    product = _get_row_value(row, header_map, '商品说明')
                    category = _get_row_value(row, header_map, '交易分类')
                    payment_method = _get_row_value(row, header_map, '收/付款方式')
                    transaction_id = _get_row_value(row, header_map, '交易订单号')
                    merchant_id = _get_row_value(row, header_map, '商家订单号')
                    note = _get_row_value(row, header_map, '备注')
                    
                    # 过滤无效记录
                    if not transaction_time or not amount_str:
                        continue
                        
                    # 只处理成功的支出交易
                    if status not in ['交易成功', '还款成功', '已付款']:
                        continue
                        
                    if transaction_type not in ['支出']:
                        continue
                    
                    # 解析时间
                    parsed_time = _parse_datetime(transaction_time)
                    if not parsed_time:
                        continue
                        
                    # 解析金额
                    amount = _clean_amount(amount_str)
                    if amount <= 0:
                        continue
                    
                    # 构建描述
                    description_parts = []
                    if merchant:
                        description_parts.append(merchant)
                    if product:
                        description_parts.append(product)
                    if note and note != '/':
                        description_parts.append(note)
                    
                    description = ' - '.join(description_parts) if description_parts else '支付宝支付'
                    
                    record = {
                        'transaction_time': parsed_time,
                        'amount': -amount,  # 支出为负数
                        'currency': 'CNY',
                        'channel': 'Alipay',
                        'source_raw_description': description,
                        'description_for_ai': description,
                        'external_transaction_id': transaction_id,
                        'external_merchant_id': merchant_id,
                        'source_provided_category': category,
                        'source_payment_method': payment_method,
                        'source_transaction_status': status
                    }
                    
                    records.append(record)
                    
                except Exception as e:
                    logger.warning(f"Error parsing Alipay line {line_num}: {str(e)}")
                    continue
            
            logger.info(f"Successfully parsed {len(records)} records from Alipay CSV")
            return records
                
        except UnicodeDecodeError:
            logger.warning(f"UnicodeDecodeError with {encoding} for file: {file_path}. Trying next encoding.")
            continue
        except Exception as e:
            logger.error(f"Error parsing Alipay CSV file {file_path} with {encoding}: {e}")
            continue

    logger.error(f"Could not parse Alipay CSV file {file_path} with any encoding.")
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
