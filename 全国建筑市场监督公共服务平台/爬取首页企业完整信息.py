import binascii
import json
import os
import re
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

# 加密参数
ENCRYPTION_KEY = "Dt8j9wGw%6HbxfFn".encode('utf-8')  # 16字节密钥
ENCRYPTION_IV = "0123456789ABCDEF".encode('utf-8')   # 16字节IV

# API请求头
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

# 字段映射
FIELD_MAPPING = {
    # 基本信息字段
    "QY_ID": "企业ID",
    "QY_SRC_TYPE": "企业来源类型",
    "QY_NAME": "企业名称",
    "QY_FR_NAME": "企业法定代表人",
    "QY_REGION_NAME": "企业注册属地",
    "QY_ORG_CODE": "统一社会信用代码",
    "QY_TYPE": "企业登记注册类型编码",
    "QY_TYPE_NAME": "企业登记注册类型",
    "QY_ADDRESS": "企业经营地址",
    "QY_TEL": "企业联系电话",
    "QY_EMAIL": "企业邮箱",
    "QY_ZCZJ": "企业注册资本（万元）",
    "QY_CL_TIME": "企业成立时间",
    "QY_JYFW": "企业经营范围",
    "QY_ZS": "企业住所",
    "QY_FR_IDCARD": "法定代表人身份证号",
    "QY_FR_PHONE": "法定代表人联系电话",
    "QY_STATUS": "企业状态编码",
    "QY_STATUS_NAME": "企业状态",
    "COLLECT_TIME": "数据收集时间",
    "IS_LIMIT": "是否受限",
    "APT_NAME": "资质名称",
    "APT_GET_DATE": "资质获取日期",
    "APT_GET_TYPE": "资质获取类型编码",
    "APT_TYPE_NAME": "资质类型名称",
    "APT_STATUS": "资质状态编码",
    "IS_LIMIT_NAME": "是否受限名称",
    "APT_STATUS_NAME": "资质状态名称",
    "APT_CHECK_ID": "资质检查ID",
    "OLD_CODE": "旧编码",
    "APT_GRANT_UNIT": "发证机关",
    "APT_LIMIT_CONTENT": "资质限制内容",
    "APT_EDATE": "资质有效期截止日期",
    "APT_ID": "资质ID",
    "APT_TYPE": "资质类型编码",
    "APT_GRANT_UNITID": "发证机关ID",
    "APT_CODE": "资质编码",
    "COLLECT_SOURCE": "数据来源",
    "APT_GET_TYPE_NAME": "资质获取类型名称",
    "RN": "序号",
    "APT_CERTNO": "资质证书编号",
    "total": "总数",
    "pageSize": "每页数量",
    "pageNum": "页码",
    "orderStr": "排序字段",
    "list": "数据列表",
    "pageList": "分页信息",
    "data": "数据",
    "code": "状态码",
    "message": "消息",
    "success": "是否成功",
    
    # 新增业绩、信用、处罚等相关字段
    "PRJNUM": "项目编号",
    "PRJNAME": "项目名称",
    "PRJTYPE": "项目类型",
    "BUIDPRJNUM": "施工项目编号",
    "BUIDPRJNAME": "施工项目名称",
    "PROVINCE": "省份",
    "CITY": "城市",
    "COUNTY": "区县",
    "ADDRESS": "地址",
    "LEVELNUM": "等级编号",
    "STUDYTYPE": "学习类型",
    "CATEGORY": "类别",
    "SUBJECT": "主题",
    "GRADE": "等级",
    "MAJOR": "专业",
    "PROJECTNATURE": "项目性质",
    "FINISHDATE": "完成日期",
    "YEAR": "年份",
    "MONTH": "月份",
    "SOURCE": "来源",
    "TITLE": "标题",
    "CONTENT": "内容",
    "UNITNAME": "单位名称",
    "CORPNAME": "企业名称",
    "CORPID": "企业ID",
    "NAME": "名称",
    "ID": "ID",
    "TYPE": "类型",
    "STATUS": "状态",
    "CREATEDATE": "创建日期",
    "UPDATEDATE": "更新日期",
    "DEPTNAME": "部门名称",
    "DEPTID": "部门ID",
    "REASON": "原因",
    "RESULT": "结果",
    "NOTICEID": "通知ID",
    "NOTICETITLE": "通知标题",
    "NOTICECONTENT": "通知内容",
    "NOTICEDATE": "通知日期",
    "CASEID": "案件ID",
    "CASENAME": "案件名称",
    "CASECONTENT": "案件内容",
    "CASEDATE": "案件日期",
    "LEGALPERSON": "法人",
    "LINKMAN": "联系人",
    "LINKTEL": "联系电话",
    "ECONOMICPROPERTY": "经济性质",
    "BUSINESSSCOPE": "经营范围",
    "REGISTCAPITAL": "注册资本",
    "REGISTDATE": "注册日期",
    "CERTID": "证书ID",
    "CERTTYPE": "证书类型",
    "CERTNAME": "证书名称",
    "CERTORG": "发证机关",
    "VALIDDATE": "有效期",
    "INVALIDDATE": "失效日期",
    "CHECKSTATUS": "检查状态",
    "CHECKDATE": "检查日期",
    "CHECKRESULT": "检查结果",
    "CHECKORG": "检查机关",
    "PUNISHID": "处罚ID",
    "PUNISHTYPE": "处罚类型",
    "PUNISHREASON": "处罚原因",
    "PUNISHRESULT": "处罚结果",
    "PUNISHDATE": "处罚日期",
    "PUNISHORG": "处罚机关",
    "BLACKID": "黑名单ID",
    "BLACKREASON": "黑名单原因",
    "BLACKDATE": "黑名单日期",
    "REMOVEBLACKDATE": "移出黑名单日期",
    "CHANGEID": "变更ID",
    "CHANGETYPE": "变更类型",
    "CHANGECONTENT": "变更内容",
    "CHANGEDATE": "变更日期",
    "CHANGEORG": "变更机关",
    
    # 证书详情相关字段
    "CERT_NO": "证书编号",
    "CERT_NAME": "证书名称",
    "ISSUE_DATE": "发证日期",
    "EXPIRY_DATE": "有效期至",
    "CERT_STATUS": "证书状态",
    "CERT_STATUS_NAME": "证书状态名称",
    "ISSUING_AUTHORITY": "发证机关",
    "QUALIFICATION_TYPE": "资质类型",
    "QUALIFICATION_LEVEL": "资质等级",
    "BUSINESS_SCOPE": "业务范围",
    "ECONOMIC_TYPE": "经济类型",
    "REGISTRATION_AUTHORITY": "登记机关",
    "CERTIFICATE_TYPE": "证书类型",
    "CERTIFICATE_CATEGORY": "证书类别"
}

class SessionManager:
    """
    会话管理器，用于复用浏览器会话，避免重复验证码验证
    """
    def __init__(self):
        self.driver = None
        self.access_token = None
        self.is_verified = False
    
    def get_driver(self):
        if not self.driver:
            self.driver = setup_driver()
        return self.driver
    
    def verify_once(self):
        """
        只验证一次验证码
        """
        if not self.is_verified:
            driver = self.get_driver()
            if driver:
                detail_url = "https://jzsc.mohurd.gov.cn/data/company/detail?compId=002105291239451311"
                print(f"正在访问详情页: {detail_url}")
                driver.get(detail_url)
                
                # 等待页面加载
                time.sleep(5)
                
                # 等待并手动完成验证码验证
                if wait_for_captcha_and_manual_verify(driver):
                    print("验证码验证成功，等待页面完全加载...")
                    time.sleep(5)
                    self.is_verified = True
                else:
                    print("验证码验证失败或超时")
                    return False
                
                # 获取accessToken
                self.access_token = get_access_token_from_localstorage(driver)
                if not self.access_token:
                    print("无法获取accessToken")
                    return False
        return self.is_verified
    
    def get_access_token(self):
        return self.access_token
    
    def close(self):
        if self.driver:
            self.driver.quit()

def decrypt_response(encrypted_data):
    """
    解密全国建筑市场监督公共服务平台的响应数据
    
    Args:
        encrypted_data (str): 从服务器获取的十六进制加密数据
        
    Returns:
        dict: 解密后的JSON数据
    """
    try:
        # 1. 将十六进制字符串解析为字节数据
        hex_data = binascii.unhexlify(encrypted_data)
        
        # 2. 使用AES-CBC-PKCS7算法解密
        cipher = AES.new(ENCRYPTION_KEY, AES.MODE_CBC, ENCRYPTION_IV)
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

def convert_field_names(data):
    """
    递归地将数据中的英文字段名转换为中文字段名
    
    Args:
        data: 需要转换的数据（字典、列表或其他类型）
        
    Returns:
        转换后的数据
    """
    if isinstance(data, dict):
        new_dict = {}
        for key, value in data.items():
            # 转换字段名
            new_key = FIELD_MAPPING.get(key, key)
            # 递归处理值
            new_value = convert_field_names(value)
            new_dict[new_key] = new_value
        return new_dict
    elif isinstance(data, list):
        # 递归处理列表中的每个元素
        return [convert_field_names(item) for item in data]
    else:
        # 其他类型直接返回
        return data

def filter_chinese_fields_only(data):
    """
    过滤数据，只保留中文字段名的数据
    
    Args:
        data: 已经转换过字段名的数据
        
    Returns:
        只包含中文字段的数据
    """
    if isinstance(data, dict):
        new_dict = {}
        for key, value in data.items():
            # 只保留中文字段（判断key是否在FIELD_MAPPING的值中，或者key本身就是中文）
            if key in FIELD_MAPPING.values() or (not any(c in key for c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ_')) or key in ['数据', '分页信息']:
                new_value = filter_chinese_fields_only(value)
                new_dict[key] = new_value
        return new_dict
    elif isinstance(data, list):
        # 递归处理列表中的每个元素
        return [filter_chinese_fields_only(item) for item in data]
    else:
        # 其他类型直接返回
        return data

def init_session():
    """
    初始化requests会话
    """
    session = requests.Session()
    session.headers.update(headers)
    
    # 先访问主页，获取必要的cookies
    print("正在初始化会话...")
    try:
        response = session.get('https://jzsc.mohurd.gov.cn/data/company', timeout=5)
        print(f"主页访问状态码: {response.status_code}")
        return session
    except Exception as e:
        print(f"初始化会话失败: {e}")
        return None

def fetch_data_with_driver(driver, access_token, url, referer_url):
    """
    使用已打开的浏览器和token获取数据
    
    Args:
        driver: 已打开的浏览器驱动
        access_token: 有效的访问令牌
        url: 请求的URL
        referer_url: Referer URL
        
    Returns:
        dict: 解密后的数据
    """
    try:
        print(f"正在请求API: {url}")
        
        # 使用浏览器执行JavaScript来发送请求
        js_script = f"""
        return new Promise((resolve, reject) => {{
            var xhr = new XMLHttpRequest();
            xhr.open('GET', '{url}', true);  // 使用异步请求
            xhr.setRequestHeader('accessToken', '{access_token}');
            xhr.setRequestHeader('Referer', '{referer_url}');
            xhr.setRequestHeader('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36 Edg/138.0.0.0');
            xhr.setRequestHeader('Accept', 'application/json, text/plain, */*');
            xhr.setRequestHeader('v', '231012');
            xhr.timeout = 30000; // 设置30秒超时
            
            xhr.onload = function() {{
                if (xhr.status === 200) {{
                    resolve([xhr.status, xhr.responseText]);
                }} else {{
                    resolve([xhr.status, xhr.responseText]);
                }}
            }};
            
            xhr.onerror = function() {{
                reject(new Error('Network error'));
            }};
            
            xhr.ontimeout = function() {{
                reject(new Error('Request timeout'));
            }};
            
            try {{
                xhr.send();
            }} catch (e) {{
                reject(e);
            }}
        }});
        """
        
        # 执行JavaScript请求
        result = driver.execute_async_script(f"""
        var done = arguments[0];
        (function() {{
            {js_script}
        }})().then(function(result) {{
            done([true, result]);
        }}).catch(function(error) {{
            done([false, error.message]);
        }});
        """)
        
        # 检查执行结果
        if isinstance(result, list) and len(result) == 2:
            success, response_data = result
            if success and isinstance(response_data, list) and len(response_data) == 2:
                status_code, response_text = response_data
                print(f"API请求完成，状态码: {status_code}")
                
                # 检查是否token失效
                if status_code == 408:
                    print("检测到token失效 (状态码408)")
                    return {"code": 408, "message": "token失效"}
                
                # 检查响应内容是否为十六进制字符串（加密数据）
                response_text = response_text.strip()
                
                # 判断是否为十六进制字符串
                if re.match(r'^[0-9a-fA-F]+$', response_text):
                    print("检测到加密数据，正在进行解密...")
                    # 解密响应数据
                    decrypted_data = decrypt_response(response_text)
                    if decrypted_data:
                        print("数据解密成功")
                        # 检查解密后的数据是否包含token失效信息
                        if isinstance(decrypted_data, dict) and decrypted_data.get("code") == 408:
                            print("检测到token失效 (解密后数据中code=408)")
                            return decrypted_data
                        return decrypted_data
                    else:
                        print("数据解密失败")
                        return None
                else:
                    print("响应数据未加密或格式不符")
                    print(f"响应内容预览: {response_text[:200]}")
                    # 尝试解析为JSON
                    try:
                        parsed_data = json.loads(response_text)
                        # 检查是否包含token失效信息
                        if isinstance(parsed_data, dict) and parsed_data.get("code") == 408:
                            print("检测到token失效 (响应数据中code=408)")
                            return parsed_data
                        return parsed_data
                    except:
                        return None
            else:
                print(f"请求失败: {response_data}")
                return None
        else:
            print("请求返回格式不正确")
            return None
            
    except Exception as e:
        print(f"获取数据时出错: {e}")
        return None

def fetch_data_with_retry(session_manager, fetch_function, *args, max_retries=3, **kwargs):
    """
    带重试机制的数据获取函数，处理token失效情况
    
    Args:
        session_manager: 会话管理器
        fetch_function: 数据获取函数
        max_retries: 最大重试次数
        *args, **kwargs: 传递给fetch_function的参数
        
    Returns:
        dict: 获取到的数据
    """
    driver = session_manager.get_driver()
    access_token = session_manager.get_access_token()
    
    for attempt in range(max_retries):
        print(f"第{attempt + 1}次尝试获取数据...")
        result = fetch_function(driver, access_token, *args, **kwargs)
        
        # 检查是否token失效
        if result and isinstance(result, dict):
            code = result.get("code")
            message = result.get("message", "")
            
            # 检查code为408或消息中包含"token失效"
            if code == 408 or "token失效" in message:
                print(f"第{attempt + 1}次尝试失败：token失效")
                if attempt < max_retries - 1:  # 不是最后一次尝试
                    print("正在重新验证会话以刷新token...")
                    # 重新验证会话
                    session_manager.is_verified = False
                    if session_manager.verify_once():
                        access_token = session_manager.get_access_token()
                        print("会话重新验证成功，使用新token重试...")
                        continue  # 使用新token重试
                    else:
                        print("会话重新验证失败")
                        return None
                else:
                    print("已达到最大重试次数，token刷新失败")
                    return None
            else:
                # 成功获取数据
                return result
        else:
            # 成功获取数据或者出现其他错误
            return result
    
    print("数据获取失败，已达到最大重试次数")
    return None

def setup_driver():
    """
    设置Chrome浏览器驱动
    """
    # 获取项目根目录下的chromedriver路径
    project_root = os.path.dirname(os.path.dirname(__file__))
    chromedriver_path = os.path.join(project_root, 'chromedriver.exe')
    
    # 检查chromedriver是否存在
    if not os.path.exists(chromedriver_path):
        print(f"未找到ChromeDriver: {chromedriver_path}")
        print("请确保chromedriver.exe文件已放置在项目根目录中")
        return None
    
    print(f"使用ChromeDriver路径: {chromedriver_path}")
    
    chrome_options = Options()
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    # 创建Service对象并指定ChromeDriver路径
    service = Service(chromedriver_path)
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": """
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            })
        """
    })
    
    return driver

def wait_for_captcha_and_manual_verify(driver):
    """
    等待验证码出现并提示用户手动验证
    """
    print("正在等待验证码出现...")
    try:
        # 等待验证码元素出现（最多等待30秒）
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CLASS_NAME, "geetest_holder"))
        )
        print("检测到验证码，请手动完成验证...")
        print("验证完成后，程序将自动继续执行")
        
        # 等待验证码验证完成（最多等待120秒）
        WebDriverWait(driver, 120).until(
            EC.presence_of_element_located((By.CLASS_NAME, "geetest_success"))
        )
        print("验证码验证完成！")
        return True
    except Exception as e:
        print(f"等待验证码时出错: {e}")
        return False

def get_access_token_from_localstorage(driver):
    """
    从localStorage中获取accessToken
    """
    try:
        token = driver.execute_script("return localStorage.getItem('accessToken');")
        if token:
            print(f"获取到accessToken: {token}")
            return token
        else:
            print("未找到accessToken")
            return None
    except Exception as e:
        print(f"从localStorage获取token时出错: {e}")
        return None

def fetch_first_page_data_with_driver(driver, access_token, region='330100', page_size=5):
    """
    使用浏览器会话获取第一页的企业数据
    
    Args:
        driver: 已打开的浏览器驱动
        access_token: 有效的访问令牌
        region: 地区代码
        page_size: 每页数据量（改为5条记录用于测试）
        
    Returns:
        list: 第一页的企业数据列表
    """
    # 构造API URL
    url = f"https://jzsc.mohurd.gov.cn/APi/webApi/dataservice/query/comp/list"
    params = f"qy_region={region}&pg=0&pgsz={page_size}"  # 确保使用传入的page_size参数
    full_url = f"{url}?{params}"
    
    # 访问企业列表页
    list_url = "https://jzsc.mohurd.gov.cn/data/company"
    
    try:
        print("正在访问企业列表页...")
        driver.get(list_url)
        time.sleep(3)
        
        print(f"正在获取第1页数据，每页{page_size}条记录...")
        print(f"请求URL: {full_url}")
        print(f"传入的page_size参数: {page_size}")
        
        return fetch_data_with_driver(driver, access_token, full_url, list_url)
            
    except Exception as e:
        print(f"请求异常: {e}")
        import traceback
        traceback.print_exc()
        return None

def fetch_company_basic_info_with_driver(driver, access_token, comp_id):
    """
    使用已打开的浏览器和token获取企业基本信息
    
    Args:
        driver: 已打开的浏览器驱动
        access_token: 有效的访问令牌
        comp_id: 企业ID
        
    Returns:
        dict: 解密后的数据
    """
    # 访问详情页
    detail_url = f"https://jzsc.mohurd.gov.cn/data/company/detail?compId={comp_id}"
    
    # 构造API请求URL
    api_url = f"https://jzsc.mohurd.gov.cn/APi/webApi/dataservice/query/comp/compDetail"
    params = f"compId={comp_id}"
    full_url = f"{api_url}?{params}"
    
    print(f"正在获取企业 {comp_id} 的基本信息...")
    print(f"详情页URL: {detail_url}")
    print(f"API请求URL: {full_url}")
    
    result = fetch_data_with_driver(driver, access_token, full_url, detail_url)
    print(f"基本信息请求结果: {result}")
    return result

def fetch_company_detail_data_automated_with_driver(driver, access_token, qy_id, page=0, page_size=5):
    """
    使用已打开的浏览器和token获取企业详情数据
    
    Args:
        driver: 已打开的浏览器驱动
        access_token: 有效的访问令牌
        qy_id: 企业ID
        page: 页码
        page_size: 每页数据量（改为5条记录用于测试）
        
    Returns:
        dict: 解密后的数据
    """
    # 访问详情页
    detail_url = f"https://jzsc.mohurd.gov.cn/data/company/detail?id={qy_id}"
    
    # 构造API请求URL
    api_url = f"https://jzsc.mohurd.gov.cn/APi/webApi/dataservice/query/comp/caDetailList"
    params = f"qyId={qy_id}&pg={page}&pgsz={page_size}"
    full_url = f"{api_url}?{params}"
    
    return fetch_data_with_driver(driver, access_token, full_url, detail_url)

def fetch_company_cert_detail_with_driver(driver, access_token, qy_id, certno):
    """
    使用已打开的浏览器和token获取企业证书详情数据
    
    Args:
        driver: 已打开的浏览器驱动
        access_token: 有效的访问令牌
        qy_id: 企业ID
        certno: 证书编号
        
    Returns:
        dict: 解密后的数据
    """
    try:
        # 访问详情页
        detail_url = f"https://jzsc.mohurd.gov.cn/data/company/detail?id={qy_id}"
        
        # 构造API请求URL
        api_url = f"https://jzsc.mohurd.gov.cn/APi/webApi/dataservice/query/comp/caCertDetail"
        params = f"qyId={qy_id}&certno={certno}"
        full_url = f"{api_url}?{params}"
        
        print(f"正在请求API: {full_url}")
        
        # 使用浏览器执行JavaScript来发送请求
        js_script = f"""
        var xhr = new XMLHttpRequest();
        xhr.open('GET', '{full_url}', false);
        xhr.setRequestHeader('accessToken', '{access_token}');
        xhr.setRequestHeader('Referer', '{detail_url}');
        xhr.setRequestHeader('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36 Edg/138.0.0.0');
        xhr.setRequestHeader('Accept', 'application/json, text/plain, */*');
        xhr.setRequestHeader('v', '231012');
        xhr.send();
        return xhr.responseText;
        """
        
        # 执行JavaScript请求
        response_text = driver.execute_script(js_script)
        print("API请求完成")
        print(f"响应文本长度: {len(response_text)} 字符")
        
        # 检查响应内容是否为十六进制字符串（加密数据）
        response_text = response_text.strip()
        print(f"响应文本预览: {response_text[:100]}...")
        
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
            print("响应数据未加密或格式不符")
            print(f"响应内容预览: {response_text[:200]}")
            # 尝试解析为JSON
            try:
                return json.loads(response_text)
            except:
                return None
            
    except Exception as e:
        print(f"获取数据时出错: {e}")
        import traceback
        traceback.print_exc()
        return None

def fetch_cert_details(driver, access_token, qy_id, cert_list):
    """
    获取证书详情数据
    
    Args:
        driver: 浏览器驱动
        access_token: 访问令牌
        qy_id: 企业ID
        cert_list: 证书列表
        
    Returns:
        list: 证书详情数据列表
    """
    cert_details = []
    
    # 遍历证书列表，获取每个证书的详情
    for i, cert in enumerate(cert_list):
        # 尝试多种可能的证书编号字段
        certno = (cert.get('资质证书编号') or 
                 cert.get('APT_CERTNO') or 
                 cert.get('证书编号') or 
                 cert.get('CERT_NO') or
                 cert.get('apt_certno'))
        
        if certno:
            print(f"\n正在获取第{i+1}个证书详情，证书编号: {certno}")
            cert_detail = fetch_company_cert_detail_with_driver(driver, access_token, qy_id, certno)
            
            if cert_detail:
                # 注意：对于证书详情数据，我们不进行字段名转换，以保持原始数据结构
                # 这是因为证书详情数据结构特殊，转换可能导致数据丢失
                cert_details.append({
                    '证书编号': certno,
                    '数据': cert_detail
                })
                print(f"证书 {certno} 详情获取成功")
            else:
                print(f"证书 {certno} 详情获取失败")
                
            # 等待一段时间，避免请求过于频繁
            time.sleep(3)
        else:
            print(f"第{i+1}个证书缺少证书编号，跳过")
            # 打印证书信息用于调试
            print(f"证书信息: {cert}")
    
    return cert_details

def extract_cert_list_from_detail_data(detail_data_list):
    """
    从详情数据中提取证书列表
    
    Args:
        detail_data_list: 详情数据列表
        
    Returns:
        list: 证书列表
    """
    cert_list = []
    
    # 遍历所有详情数据页面
    for page_index, page_data in enumerate(detail_data_list):
        print(f"处理第{page_index+1}页详情数据")
        if isinstance(page_data, dict) and '数据' in page_data:
            data_section = page_data['数据']
            # 检查标准的数据结构: 数据 -> 数据 -> 分页信息 -> 数据列表
            if isinstance(data_section, dict) and '数据' in data_section:
                inner_data = data_section['数据']
                if isinstance(inner_data, dict) and '分页信息' in inner_data:
                    pagination = inner_data['分页信息']
                    if isinstance(pagination, dict) and '数据列表' in pagination:
                        data_list = pagination['数据列表']
                        if isinstance(data_list, list):
                            print(f"第{page_index+1}页包含 {len(data_list)} 个证书")
                            for item_index, item in enumerate(data_list):
                                if isinstance(item, dict):
                                    # 尝试多种可能的证书编号字段
                                    certno = (item.get('资质证书编号') or 
                                             item.get('APT_CERTNO') or 
                                             item.get('证书编号') or 
                                             item.get('CERT_NO') or
                                             item.get('apt_certno'))
                                    
                                    if certno:
                                        if certno not in cert_list:
                                            cert_list.append(item)
                                            print(f"  发现资质证书编号: {certno}")
                                            
                                            # 打印该条记录的部分信息用于调试
                                            debug_info = {}
                                            for key in ['资质名称', 'APT_NAME', '资质类型名称', 'APT_TYPE_NAME']:
                                                if key in item:
                                                    debug_info[key] = item[key]
                                            if debug_info:
                                                print(f"    相关信息: {debug_info}")
                                    else:
                                        print(f"  第 {item_index+1} 条记录缺少资质证书编号，记录内容: { {k:v for k,v in item.items() if '证书' in k or 'CERT' in k or '资质' in k or 'APT' in k} }")
                        else:
                            print(f"第 {page_index+1} 页数据列表不是列表类型: {type(data_list)}")
                    else:
                        print(f"第 {page_index+1} 页缺少分页信息或数据列表字段")
                else:
                    print(f"第 {page_index+1} 页数据结构不符合预期")
            else:
                print(f"第 {page_index+1} 页缺少内层数据字段")
                # 检查是否有其他可能包含数据的字段
                if isinstance(data_section, dict):
                    print(f"数据字段包含: {list(data_section.keys())}")
                    # 尝试查找可能包含证书列表的其他字段
                    for key, value in data_section.items():
                        if isinstance(value, list) and len(value) > 0:
                            # 检查列表中的第一个元素是否可能是证书数据
                            if isinstance(value[0], dict) and ('证书编号' in value[0] or '资质证书编号' in value[0] or 'CERT_NO' in value[0] or 'APT_CERTNO' in value[0]):
                                print(f"发现可能的证书列表字段: {key}")
                                for item in value:
                                    certno = (item.get('资质证书编号') or 
                                             item.get('APT_CERTNO') or 
                                             item.get('证书编号') or 
                                             item.get('CERT_NO') or
                                             item.get('apt_certno'))
                                    if certno and item not in cert_list:
                                        cert_list.append(item)
        else:
            print(f"第{page_index+1}页数据格式不正确")
            # 打印调试信息
            if isinstance(page_data, dict):
                print(f"页面数据包含: {list(page_data.keys())}")
                # 检查是否有直接的数据列表
                for key, value in page_data.items():
                    if isinstance(value, list) and len(value) > 0:
                        # 检查列表中的第一个元素是否可能是证书数据
                        if isinstance(value[0], dict) and ('证书编号' in value[0] or '资质证书编号' in value[0] or 'CERT_NO' in value[0] or 'APT_CERTNO' in value[0]):
                            print(f"在页面数据中发现可能的证书列表字段: {key}")
                            for item in value:
                                certno = (item.get('资质证书编号') or 
                                         item.get('APT_CERTNO') or 
                                         item.get('证书编号') or 
                                         item.get('CERT_NO') or
                                         item.get('apt_certno'))
                                if certno and item not in cert_list:
                                    cert_list.append(item)
    
    print(f"总共提取到 {len(cert_list)} 个证书")
    
    # 打印前几个证书的信息用于调试
    if cert_list:
        print("前3个证书的信息:")
        for i, cert in enumerate(cert_list[:3]):
            certno = (cert.get('资质证书编号') or 
                     cert.get('APT_CERTNO') or 
                     cert.get('证书编号') or 
                     cert.get('CERT_NO') or
                     cert.get('apt_certno'))
            print(f"  证书 {i+1} 编号: {certno}")
            # 打印相关资质信息
            debug_info = {}
            for key in ['资质名称', 'APT_NAME', '资质类型名称', 'APT_TYPE_NAME']:
                if key in cert:
                    debug_info[key] = cert[key]
            if debug_info:
                print(f"    相关信息: {debug_info}")
    
    return cert_list

def fetch_company_performance_list_sys_with_driver(driver, access_token, qy_id, page=0, page_size=5):
    """
    使用已打开的浏览器和token获取企业业绩列表（系统）
    
    Args:
        driver: 已打开的浏览器驱动
        access_token: 有效的访问令牌
        qy_id: 企业ID
        page: 页码
        page_size: 每页数据量（改为5条记录用于测试）
        
    Returns:
        dict: 解密后的数据
    """
    # 访问详情页
    detail_url = f"https://jzsc.mohurd.gov.cn/data/company/detail?id={qy_id}"
    
    # 构造API请求URL
    api_url = f"https://jzsc.mohurd.gov.cn/APi/webApi/dataservice/query/comp/compPerformanceListSys"
    params = f"qy_id={qy_id}&pg={page}&pgsz={page_size}"
    full_url = f"{api_url}?{params}"
    
    return fetch_data_with_driver(driver, access_token, full_url, detail_url)

def fetch_company_biz_perf_list_with_driver(driver, access_token, qy_id, page=0, page_size=5):
    """
    使用已打开的浏览器和token获取企业业务业绩列表
    
    Args:
        driver: 已打开的浏览器驱动
        access_token: 有效的访问令牌
        qy_id: 企业ID
        page: 页码
        page_size: 每页数据量（改为5条记录用于测试）
        
    Returns:
        dict: 解密后的数据
    """
    # 访问详情页
    detail_url = f"https://jzsc.mohurd.gov.cn/data/company/detail?id={qy_id}"
    
    # 构造API请求URL
    api_url = f"https://jzsc.mohurd.gov.cn/APi/webApi/dataservice/query/comp/getCompBizPerfList"
    params = f"qyId={qy_id}&pg={page}&pgsz={page_size}"
    full_url = f"{api_url}?{params}"
    
    return fetch_data_with_driver(driver, access_token, full_url, detail_url)

def fetch_company_credit_record_list_with_driver(driver, access_token, comp_id, mark, page=0, page_size=5):
    """
    使用已打开的浏览器和token获取企业信用记录列表
    
    Args:
        driver: 已打开的浏览器驱动
        access_token: 有效的访问令牌
        comp_id: 企业ID
        mark: 标记（0或1）
        page: 页码
        page_size: 每页数据量（改为5条记录用于测试）
        
    Returns:
        dict: 解密后的数据
    """
    # 访问详情页
    detail_url = f"https://jzsc.mohurd.gov.cn/data/company/detail?id={comp_id}"
    
    # 构造API请求URL
    api_url = f"https://jzsc.mohurd.gov.cn/APi/webApi/dataservice/query/comp/compCreditRecordList"
    params = f"compId={comp_id}&mark={mark}&pg={page}&pgsz={page_size}"
    full_url = f"{api_url}?{params}"
    
    return fetch_data_with_driver(driver, access_token, full_url, detail_url)

def fetch_company_credit_black_list_with_driver(driver, access_token, comp_id, page=0, page_size=5):
    """
    使用已打开的浏览器和token获取企业黑名单记录
    
    Args:
        driver: 已打开的浏览器驱动
        access_token: 有效的访问令牌
        comp_id: 企业ID
        page: 页码
        page_size: 每页数据量（改为5条记录用于测试）
        
    Returns:
        dict: 解密后的数据
    """
    # 访问详情页
    detail_url = f"https://jzsc.mohurd.gov.cn/data/company/detail?id={comp_id}"
    
    # 构造API请求URL
    api_url = f"https://jzsc.mohurd.gov.cn/APi/webApi/dataservice/query/comp/compCreditBlackList"
    params = f"compId={comp_id}&pg={page}&pgsz={page_size}"
    full_url = f"{api_url}?{params}"
    
    return fetch_data_with_driver(driver, access_token, full_url, detail_url)

def fetch_company_punish_list_with_driver(driver, access_token, corp_id, page=0, page_size=5):
    """
    使用已打开的浏览器和token获取企业处罚记录
    
    Args:
        driver: 已打开的浏览器驱动
        access_token: 有效的访问令牌
        corp_id: 企业ID
        page: 页码
        page_size: 每页数据量（改为5条记录用于测试）
        
    Returns:
        dict: 解密后的数据
    """
    # 访问详情页
    detail_url = f"https://jzsc.mohurd.gov.cn/data/company/detail?id={corp_id}"
    
    # 构造API请求URL
    api_url = f"https://jzsc.mohurd.gov.cn/APi/webApi/dataservice/query/comp/compPunishList"
    params = f"corpId={corp_id}&pg={page}&pgsz={page_size}"
    full_url = f"{api_url}?{params}"
    
    return fetch_data_with_driver(driver, access_token, full_url, detail_url)

def fetch_company_apt_change_with_driver(driver, access_token, qy_id):
    """
    使用已打开的浏览器和token获取企业资质变更记录
    
    Args:
        driver: 已打开的浏览器驱动
        access_token: 有效的访问令牌
        qy_id: 企业ID
        
    Returns:
        dict: 解密后的数据
    """
    # 访问详情页
    detail_url = f"https://jzsc.mohurd.gov.cn/data/company/detail?id={qy_id}"
    
    # 构造API请求URL
    api_url = f"https://jzsc.mohurd.gov.cn/APi/webApi/dataservice/query/comp/aptChange"
    params = f"qyId={qy_id}"
    full_url = f"{api_url}?{params}"
    
    return fetch_data_with_driver(driver, access_token, full_url, detail_url)

def fetch_paginated_data(driver, access_token, fetch_function, *args, max_pages=10, **kwargs):
    """
    获取分页数据的通用函数
    
    Args:
        driver: 浏览器驱动
        access_token: 访问令牌
        fetch_function: 获取数据的函数
        max_pages: 最大页数
        *args, **kwargs: 传递给fetch_function的参数
        
    Returns:
        list: 所有页面的数据列表
    """
    all_data = []
    
    # 获取第一页数据
    print(f"\n正在获取第1页数据...")
    page_data = fetch_function(driver, access_token, *args, page=0, **kwargs)
    
    if page_data:
        # 检查是否token失效
        if isinstance(page_data, dict):
            code = page_data.get("code")
            message = page_data.get("message", "")
            if code == 408 or "token失效" in message:
                print("第1页数据获取失败：token失效")
                return [{"页码": 1, "数据": page_data}]  # 返回包含错误信息的数据
        
        # 转换字段名为中文
        page_data = convert_field_names(page_data)
        # 过滤只保留中文字段
        page_data = filter_chinese_fields_only(page_data)
        all_data.append({
            '页码': 1,
            '数据': page_data
        })
        print("第1页数据获取成功")
        
        # 获取数据总数以确定总页数
        total = 0
        if isinstance(page_data, dict) and '数据' in page_data:
            data_section = page_data['数据']
            if isinstance(data_section, dict) and '分页信息' in data_section and '总数' in data_section['分页信息']:
                total = data_section['分页信息']['总数']
                print(f"数据总数: {total}")
                
                # 计算总页数（每页5条）
                total_pages = min((total + 4) // 5, max_pages)  # 向上取整，但不超过最大页数
                print(f"总页数: {total_pages}")
                
                # 获取剩余页面的数据
                for page in range(1, total_pages):
                    print(f"\n正在获取第{page+1}页数据...")
                    page_data = fetch_function(driver, access_token, *args, page=page, **kwargs)
                    
                    # 检查是否token失效
                    if page_data and isinstance(page_data, dict):
                        code = page_data.get("code")
                        message = page_data.get("message", "")
                        if code == 408 or "token失效" in message:
                            print(f"第{page+1}页数据获取失败：token失效")
                            all_data.append({
                                '页码': page + 1,
                                '数据': page_data  # 保留错误信息
                            })
                            continue  # 继续获取下一页
                    
                    if page_data:
                        # 转换字段名为中文
                        page_data = convert_field_names(page_data)
                        # 过滤只保留中文字段
                        page_data = filter_chinese_fields_only(page_data)
                        all_data.append({
                            '页码': page + 1,
                            '数据': page_data
                        })
                        print(f"第{page+1}页数据获取成功")
                    else:
                        print(f"第{page+1}页数据获取失败")
                        all_data.append({
                            '页码': page + 1,
                            '数据': None
                        })
                    
                    # 等待一段时间，避免请求过于频繁
                    time.sleep(3)
            else:
                print("无法获取数据总数")
    else:
        print("第1页数据获取失败")
        all_data.append({
            '页码': 1,
            '数据': None
        })
        
    return all_data

def fetch_company_complete_info(comp_id, session_manager, max_detail_pages=10):
    """
    使用浏览器自动化获取企业完整信息（基本信息+详情数据）
    
    Args:
        comp_id: 企业ID
        session_manager: 会话管理器
        max_detail_pages: 详情数据最大获取页数
        
    Returns:
        dict: 包含基本信息和详情数据的完整数据
    """
    # 确保会话已验证
    if not session_manager.verify_once():
        print("会话验证失败")
        return None
    
    driver = session_manager.get_driver()
    access_token = session_manager.get_access_token()
    
    if not driver or not access_token:
        print("无法获取浏览器驱动或访问令牌")
        return None
    
    complete_info = {
        '企业ID': comp_id,
        '基本信息': None,
        '详情数据': [],
        '证书详情数据': [],
        '业绩数据_系统': [],
        '业绩数据_业务': [],
        '信用记录_0': [],
        '信用记录_1': [],
        '黑名单记录': [],
        '处罚记录': [],
        '资质变更记录': []
    }
    
    try:
        # 获取企业基本信息
        print(f"\n正在获取企业 {comp_id} 的基本信息...")
        basic_info = fetch_data_with_retry(
            session_manager, fetch_company_basic_info_with_driver, comp_id)
        
        print(f"获取到的原始基本信息: {basic_info}")
        
        if basic_info:
            # 检查是否包含有效数据
            if isinstance(basic_info, dict):
                # 检查是否有错误信息
                if basic_info.get("code") == 408 or "token失效" in basic_info.get("message", ""):
                    print("获取基本信息时token失效")
                    return complete_info
                
                # 转换字段名为中文
                basic_info = convert_field_names(basic_info)
                print(f"转换字段名后的基本信息: {basic_info}")
                
                # 过滤只保留中文字段
                basic_info = filter_chinese_fields_only(basic_info)
                print(f"过滤中文字段后的基本信息: {basic_info}")
                
                complete_info['基本信息'] = basic_info
                print("企业基本信息获取成功")
            else:
                print(f"基本信息格式不正确: {type(basic_info)}")
                return complete_info
        else:
            print("企业基本信息获取失败")
            return complete_info
            
        # 获取详情数据
        print(f"\n正在获取企业详情数据...")
        complete_info['详情数据'] = fetch_paginated_data(
            driver, access_token, fetch_company_detail_data_automated_with_driver, 
            comp_id, max_pages=max_detail_pages)
        
        # 从详情数据中提取证书列表并获取证书详情
        cert_list = extract_cert_list_from_detail_data(complete_info['详情数据'])
        if cert_list:
            print(f"\n从详情数据中提取到 {len(cert_list)} 个证书，正在获取证书详情...")
            complete_info['证书详情数据'] = fetch_cert_details(driver, access_token, comp_id, cert_list)
            print(f"证书详情数据获取完成，共获取到 {len(complete_info['证书详情数据'])} 个证书详情")
        else:
            print("未从详情数据中提取到证书列表")
        
        # 获取业绩数据（系统）
        print(f"\n正在获取企业业绩数据（系统）...")
        complete_info['业绩数据_系统'] = fetch_paginated_data(
            driver, access_token, fetch_company_performance_list_sys_with_driver, 
            comp_id, max_pages=max_detail_pages)
        
        # 获取业务业绩数据
        print(f"\n正在获取企业业务业绩数据...")
        complete_info['业绩数据_业务'] = fetch_paginated_data(
            driver, access_token, fetch_company_biz_perf_list_with_driver, 
            comp_id, max_pages=max_detail_pages)
        
        # 获取信用记录（mark=0）
        print(f"\n正在获取企业信用记录（mark=0）...")
        complete_info['信用记录_0'] = fetch_paginated_data(
            driver, access_token, fetch_company_credit_record_list_with_driver, 
            comp_id, 0, max_pages=max_detail_pages)
        
        # 获取信用记录（mark=1）
        print(f"\n正在获取企业信用记录（mark=1）...")
        complete_info['信用记录_1'] = fetch_paginated_data(
            driver, access_token, fetch_company_credit_record_list_with_driver, 
            comp_id, 1, max_pages=max_detail_pages)
        
        # 获取黑名单记录
        print(f"\n正在获取企业黑名单记录...")
        complete_info['黑名单记录'] = fetch_paginated_data(
            driver, access_token, fetch_company_credit_black_list_with_driver, 
            comp_id, max_pages=max_detail_pages)
        
        # 获取处罚记录
        print(f"\n正在获取企业处罚记录...")
        complete_info['处罚记录'] = fetch_paginated_data(
            driver, access_token, fetch_company_punish_list_with_driver, 
            comp_id, max_pages=max_detail_pages)
        
        # 获取资质变更记录（不分页）
        print(f"\n正在获取企业资质变更记录...")
        apt_change_data = fetch_data_with_retry(
            session_manager, fetch_company_apt_change_with_driver, comp_id)
        if apt_change_data:
            # 转换字段名为中文
            apt_change_data = convert_field_names(apt_change_data)
            # 过滤只保留中文字段
            apt_change_data = filter_chinese_fields_only(apt_change_data)
            complete_info['资质变更记录'] = apt_change_data
            print("企业资质变更记录获取成功")
        else:
            print("企业资质变更记录获取失败")
            
    except Exception as e:
        print(f"自动化获取数据时出错: {e}")
        import traceback
        traceback.print_exc()
    
    return complete_info

def main():
    # 创建json目录用于存储数据
    json_dir = os.path.join(os.path.dirname(__file__), "企业完整信息json")
    if not os.path.exists(json_dir):
        os.makedirs(json_dir)
        print(f"已创建目录: {json_dir}")
    
    # 创建会话管理器
    session_manager = SessionManager()
    
    # 确保会话已验证
    if not session_manager.verify_once():
        print("会话验证失败，程序退出")
        session_manager.close()
        return
    
    driver = session_manager.get_driver()
    access_token = session_manager.get_access_token()
    
    if not driver or not access_token:
        print("无法获取浏览器驱动或访问令牌，程序退出")
        session_manager.close()
        return
    
    # 获取第一页数据（只获取5条记录用于测试）
    page_size_for_test = 5
    print(f"设置page_size为: {page_size_for_test}")
    first_page_data = fetch_first_page_data_with_driver(driver, access_token, page_size=page_size_for_test)  # 明确传入page_size=5
    if not first_page_data:
        print("获取第一页数据失败")
        session_manager.close()
        return
    
    # 从第一页数据中提取企业ID列表
    company_ids = []
    try:
        data_section = first_page_data['data']
        if isinstance(data_section, dict) and 'list' in data_section:
            companies_list = data_section['list']
            print(f"API返回的企业列表长度: {len(companies_list)}")
            # 只取前5个企业ID，即使API返回了更多
            for i, company in enumerate(companies_list):
                if i >= 5:  # 只处理前5个
                    break
                company_id = company.get('QY_ID')
                if company_id:
                    company_ids.append(company_id)
            print(f"从第一页数据中提取到 {len(company_ids)} 个企业ID")
            print(f"实际要处理的企业ID列表: {company_ids}")
        else:
            print("第一页数据格式不符合预期")
            print(f"数据结构: {data_section.keys() if isinstance(data_section, dict) else type(data_section)}")
            session_manager.close()
            return
    except Exception as e:
        print(f"提取企业ID时出错: {e}")
        session_manager.close()
        return
    
    # 获取每个企业的完整信息
    all_companies_complete_info = []
    for i, comp_id in enumerate(company_ids):
        print(f"\n[{i+1}/{len(company_ids)}] 正在获取企业 {comp_id} 的完整信息...")
        complete_info = fetch_company_complete_info(comp_id, session_manager)
        if complete_info:
            # 添加序号标识
            complete_info['序号'] = i + 1
            complete_info['记录标识'] = f"第{i+1}条记录"
            all_companies_complete_info.append(complete_info)
            print(f"企业 {comp_id} 的完整信息获取成功")
        else:
            print(f"企业 {comp_id} 的完整信息获取失败")
        
        # �避兔请求过于频繁
        if i < len(company_ids) - 1:  # 最后一个企业不需要等待
            print("等待5秒后继续获取下一个企业信息...")
            time.sleep(5)
    
    # 关闭会话
    session_manager.close()
    
    # 保存所有企业的完整信息到一个JSON文件
    if all_companies_complete_info:
        # 按照要求在数据上方添加分类标识
        categorized_data = {
            "数据说明": "首页前5家企业完整信息",
            "数据总数": len(all_companies_complete_info),
            "数据列表": all_companies_complete_info
        }
        
        summary_file = os.path.join(json_dir, '首页15家企业完整信息.json')
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(categorized_data, f, ensure_ascii=False, indent=2)
        print(f"\n首页 {len(all_companies_complete_info)} 家企业的完整信息已保存到 {summary_file}")
    else:
        print("未能获取到任何企业的完整信息")

if __name__ == "__main__":
    main()