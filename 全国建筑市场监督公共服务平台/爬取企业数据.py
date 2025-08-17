import requests
import json
import time
import re
import base64
import binascii
import os
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

# 设置请求头，模拟浏览器访问
headers = {
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
    'Cache-Control': 'no-cache',
    'Connection': 'keep-alive',
    'Pragma': 'no-cache',
    'Referer': 'https://jzsc.mohurd.gov.cn/data/company',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'same-origin',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36 Edg/138.0.0.0',
    'sec-ch-ua': '"Not)A;Brand";v="8", "Chromium";v="138", "Microsoft Edge";v="138"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'timeout': '30000',
    'v': '231012',
    'accessToken': 'jkFXxgu9TcpocIyCKmJ+tfpxe/45B9dbWMUXhdY7vLW6BbNASzgAwDhiOaGEegUfhpUUKvcMtoMqfGfwdLCb8g=='
}

def decrypt_response(encrypted_data):
    """
    解密全国建筑市场监督公共服务平台的响应数据
    
    Args:
        encrypted_data (str): 从服务器获取的十六进制加密数据
        
    Returns:
        dict: 解密后的JSON数据
    """
    # 加密参数
    key = "Dt8j9wGw%6HbxfFn".encode('utf-8')  # 16字节密钥
    iv = "0123456789ABCDEF".encode('utf-8')   # 16字节IV
    
    try:
        # 1. 将十六进制字符串解析为字节数据
        hex_data = binascii.unhexlify(encrypted_data)
        
        # 2. 使用AES-CBC-PKCS7算法解密
        cipher = AES.new(key, AES.MODE_CBC, iv)
        decrypted = cipher.decrypt(hex_data)
        
        # 3. 去除PKCS7填充
        unpadded = unpad(decrypted, AES.block_size)
        
        # 4. 将结果解析为UTF-8字符串
        json_str = unpadded.decode('utf-8')
        
        # 5. 解析为JSON对象
        return json.loads(json_str)
        
    except Exception as e:
        print(f"解密失败: {e}")
        return None

# 初始访问主页，获取必要的Cookie和accessToken信息
def init_session():
    session = requests.Session()
    session.headers.update(headers)
    
    # 先访问主页，获取必要的cookies
    print("正在初始化会话...")
    try:
        response = session.get('https://jzsc.mohurd.gov.cn/data/company', timeout=15)
        print(f"主页访问状态码: {response.status_code}")
        print(f"主页Cookies: {dict(session.cookies)}")
        
        # 检查是否已有accessToken
        if 'accessToken' in session.headers:
            print(f"使用预设accessToken: {session.headers['accessToken']}")
        
        return session
    except Exception as e:
        print(f"初始化会话失败: {e}")
        return None

# 获取数据（带重试机制）
def fetch_data(session, page=0, region='330100', page_size=15, total=0, max_retries=3):
    url = f"https://jzsc.mohurd.gov.cn/APi/webApi/dataservice/query/comp/list"
    params = {
        'qy_region': region,
        'pg': page,
        'pgsz': page_size,
        'total': total
    }
    
    for attempt in range(max_retries):
        try:
            print(f"正在获取第 {page+1} 页数据... (尝试 {attempt+1}/{max_retries})")
            # 增加超时时间到60秒
            response = session.get(url, params=params, timeout=60)
            print(f"请求URL: {response.url}")
            print(f"响应状态码: {response.status_code}")
            print(f"响应头部: {dict(response.headers)}")
            
            if response.status_code == 200:
                # 检查响应内容是否为十六进制字符串（加密数据）
                response_text = response.text.strip()
                
                # 判断是否为十六进制字符串
                if re.match(r'^[0-9a-fA-F]+$', response_text):
                    print("检测到加密数据，正在进行解密...")
                    # 解密响应数据
                    decrypted_data = decrypt_response(response_text)
                    if decrypted_data:
                        print("数据解密成功")
                        return decrypted_data
                    else:
                        print("数据解密失败")
                        return None
                else:
                    # 尝试直接解析JSON数据
                    try:
                        data = response.json()
                        print(f"成功获取数据，数据结构: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                        return data
                    except json.JSONDecodeError as e:
                        print(f"JSON解析失败: {e}")
                        print(f"响应内容预览: {response_text[:500]}")
                        return None
            else:
                print(f"请求失败，状态码: {response.status_code}")
                print(f"响应内容: {response.text[:500]}")
                if attempt < max_retries - 1:
                    print(f"等待5秒后重试...")
                    time.sleep(5)
                    
        except Exception as e:
            print(f"请求异常: {e}")
            if attempt < max_retries - 1:
                print(f"等待5秒后重试...")
                time.sleep(5)
    
    print(f"第 {page+1} 页数据获取失败，已达到最大重试次数")
    return None

def process_company_data(company_data):
    """
    处理公司数据，只保留需要的字段并重命名
    
    Args:
        company_data (dict): 原始公司数据
        
    Returns:
        dict: 处理后的公司数据
    """
    processed_data = {
        "序号": company_data.get("RN", ""),
        "统一社会信用代码": company_data.get("QY_ORG_CODE", ""),
        "企业名称": company_data.get("QY_NAME", ""),
        "企业法定代表人": company_data.get("QY_FR_NAME", ""),
        "企业注册属地": company_data.get("QY_REGION_NAME", "")
    }
    return processed_data

def fetch_all_pages(session, total_pages=30, region='330100', page_size=15):
    """
    获取所有页面的数据
    
    Args:
        session: requests session对象
        total_pages: 总页数
        region: 地区代码
        page_size: 每页数据量
        
    Returns:
        list: 所有页面的数据列表
    """
    all_data = []
    failed_pages = []  # 记录失败的页面
    
    # 获取第一页数据以确定total参数
    print("正在获取第1页数据以确定total参数...")
    first_page_data = fetch_data(session, page=0, region=region, page_size=page_size, total=0)
    
    if not first_page_data:
        print("第一页数据获取失败，无法继续")
        return all_data, failed_pages
    
    # 处理第一页数据
    if isinstance(first_page_data, dict) and 'data' in first_page_data:
        data_section = first_page_data['data']
        if isinstance(data_section, dict) and 'list' in data_section:
            for company in data_section['list']:
                processed_company = process_company_data(company)
                all_data.append(processed_company)
    
    # 从第一页数据中获取total值（如果存在）
    total = 0
    if isinstance(first_page_data, dict) and 'data' in first_page_data:
        data_section = first_page_data['data']
        if isinstance(data_section, dict) and 'total' in data_section:
            total = data_section['total']
            print(f"从第一页数据中获取total参数: {total}")
    
    # 等待一段时间，避免请求过于频繁
    time.sleep(3)
    
    # 获取剩余页面的数据
    for page in range(1, total_pages):
        print(f"\n正在获取第{page+1}页数据...")
        page_data = fetch_data(session, page=page, region=region, page_size=page_size, total=total)
        
        if page_data and isinstance(page_data, dict) and 'data' in page_data:
            data_section = page_data['data']
            if isinstance(data_section, dict) and 'list' in data_section:
                for company in data_section['list']:
                    processed_company = process_company_data(company)
                    all_data.append(processed_company)
                print(f"第{page+1}页数据处理完成，当前共{len(all_data)}条记录")
            else:
                print(f"第{page+1}页数据格式不符合预期")
                failed_pages.append(page+1)
        else:
            print(f"第{page+1}页数据获取失败")
            failed_pages.append(page+1)
        
        # 等待更长时间（5秒），避免请求过于频繁
        time.sleep(5)
    
    return all_data, failed_pages

def main():
    # 创建目录用于存储数据，路径在当前目录下
    data_dir = os.path.join(os.path.dirname(__file__), "企业数据表面基本信息json")
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        print(f"已创建目录: {data_dir}")
    
    # 初始化会话
    session = init_session()
    if not session:
        print("会话初始化失败，程序退出")
        return
    
    # 等待一段时间，确保会话建立完成
    time.sleep(2)
    
    # 获取所有30页数据
    print("开始获取所有30页数据...")
    all_data, failed_pages = fetch_all_pages(session, total_pages=30)
    
    print(f"\n数据获取完成，总共获取到 {len(all_data)} 条记录")
    if failed_pages:
        print(f"以下页面获取失败: {failed_pages}")
    
    # 保存所有数据的汇总文件
    if all_data:
        summary_file = os.path.join(data_dir, '企业数据表面基本信息.json')
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(all_data, f, ensure_ascii=False, indent=2)
        print(f"所有数据已汇总保存到 {summary_file}")
        
        # 保存失败页面信息
        if failed_pages:
            failed_file = os.path.join(data_dir, '失败页面列表.json')
            with open(failed_file, 'w', encoding='utf-8') as f:
                json.dump(failed_pages, f, ensure_ascii=False, indent=2)
            print(f"失败页面列表已保存到 {failed_file}")

if __name__ == "__main__":
    main()