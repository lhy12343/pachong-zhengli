import requests
import json
import time
import os
import re
from urllib.parse import urljoin, urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed

# 禁用 urllib3 警告
requests.packages.urllib3.disable_warnings()

class HangzhouPublicResourcePDFFetcher:
    def __init__(self):
        self.session = requests.Session()
        # 设置请求头，模拟浏览器访问
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36 Edg/138.0.0.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Referer': 'https://ggzy.hzctc.hangzhou.gov.cn/',
            'Upgrade-Insecure-Requests': '1'
        })
        
        # 创建保存PDF的目录，设置为代码文件所在目录内的pdf文件夹
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.pdf_dir = os.path.join(script_dir, "pdf")
        if not os.path.exists(self.pdf_dir):
            os.makedirs(self.pdf_dir)
    
    def get_initial_page(self):
        """
        访问初始页面，获取Cookie等信息
        """
        url = "https://ggzy.hzctc.hangzhou.gov.cn/SecondPage/SecondPage?ModuleID=17&ViewID=22"
        try:
            response = self.session.get(url, verify=False, timeout=10)
            print(f"访问初始页面状态码: {response.status_code}")
            return response.status_code == 200
        except Exception as e:
            print(f"访问初始页面出错: {e}")
            return False
    
    def fetch_data(self, page=1, rows=10):
        """
        发送POST请求获取数据
        """
        url = "https://ggzy.hzctc.hangzhou.gov.cn/SecondPage/GetNotice"
        
        # 构造表单数据
        form_data = {
            'area': '',
            'afficheType': '22',
            'IsToday': '',
            'title': '',
            'proID': '',
            'number': '',
            'IsHistory': '0',
            'TenderNo': '',
            '_search': 'false',
            'nd': str(int(time.time() * 1000)),  # 当前时间戳
            'rows': str(rows),
            'page': str(page),
            'sidx': 'PublishStartTime',
            'sord': 'desc'
        }
        
        try:
            response = self.session.post(url, data=form_data, verify=False, timeout=10)
            print(f"获取第{page}页数据状态码: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    return response.json()
                except json.JSONDecodeError:
                    print("响应不是有效的JSON格式")
                    print("响应内容:", response.text[:500])  # 打印前500个字符
                    return None
            else:
                print(f"获取第{page}页数据失败，状态码: {response.status_code}")
                print("响应内容:", response.text[:500])  # 打印前500个字符
                return None
        except Exception as e:
            print(f"获取第{page}页数据出错: {e}")
            return None
    
    def parse_data_with_links(self, data):
        """
        解析获取到的数据，包含超链接信息
        """
        if not data:
            return []
        
        records = data.get('rows', [])
        parsed_records = []
        
        for record in records:
            # 构造详细页面链接
            affiche_id = record.get('ID')
            detail_url = f"https://ggzy.hzctc.hangzhou.gov.cn/AfficheShow/Home?AfficheID={affiche_id}&IsInner=0&IsHistory=0&ModuleID=22"
            
            parsed_record = {
                '所属地区': record.get('CodeName'),
                '项目编号': record.get('TenderNo'),
                '标项名称': record.get('TenderName'),
                '开始时间': record.get('PublishStartTime'),
                '结束时间': record.get('PublishEndTime'),
                '详情链接': detail_url,
                'ID': affiche_id
            }
            parsed_records.append(parsed_record)
        
        return parsed_records
    
    def fetch_detail_page(self, detail_url):
        """
        获取详细页面内容
        """
        try:
            # 为详细页面请求设置更完整的请求头
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36 Edg/138.0.0.0',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
                'Accept-Encoding': 'gzip, deflate, br, zstd',
                'Referer': 'https://ggzy.hzctc.hangzhou.gov.cn/SecondPage/SecondPage?ModuleID=17&ViewID=22',
                'Upgrade-Insecure-Requests': '1',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache'
            }
            
            response = self.session.get(detail_url, headers=headers, verify=False, timeout=15)
            print(f"获取详细页面状态码: {response.status_code}")
            
            if response.status_code == 200:
                # 尝试使用正确的编码解码内容
                response.encoding = 'utf-8'
                content = response.text
                
                # 检查是否返回了错误页面或者重定向页面
                if '<html' in content[:100].lower() and 'login' in content.lower():
                    print("  警告：可能返回了登录页面")
                    return None
                elif '<html' in content[:100].lower() and 'error' in content.lower():
                    print("  警告：可能返回了错误页面")
                    return None
                else:
                    return content
            else:
                print(f"获取详细页面失败，状态码: {response.status_code}")
                return None
        except Exception as e:
            print(f"获取详细页面出错: {e}")
            return None
    
    def extract_tender_announcement_pdf(self, html_content, tender_name):
        """
        从详细页面中提取招标公告PDF链接
        只查找包含"招标公告"的DownLoad函数调用
        """
        if not html_content:
            return None, None
        
        # 使用正则表达式查找包含"招标公告"的DownLoad函数调用
        download_pattern = r"DownLoad\('招标公告',\s*'([^']*)'\)"
        matches = re.findall(download_pattern, html_content)
        
        if not matches:
            print("  未找到招标公告PDF")
            return None, None
        
        # 使用第一个匹配的文件（招标公告）
        filename = matches[0]
        # 构造完整的PDF下载URL
        pdf_url = f"https://ggzy.hzctc.hangzhou.gov.cn:20001/UService/DownloadAndShow.aspx?dirtype=3&filepath={filename}"
        
        # 构造保存的文件名
        safe_tender_name = tender_name.replace(" ", "_").replace("/", "_").replace("\\", "_")
        if len(safe_tender_name) > 80:
            safe_tender_name = safe_tender_name[:80]
        save_filename = f"{safe_tender_name}_招标公告.pdf"
        
        return pdf_url, save_filename
    
    def download_pdf(self, pdf_url, filename):
        """
        下载PDF文件
        """
        try:
            # 为PDF下载设置专门的请求头
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36 Edg/138.0.0.0',
                'Accept': 'application/pdf,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
                'Accept-Encoding': 'gzip, deflate, br, zstd',
                'Referer': 'https://ggzy.hzctc.hangzhou.gov.cn/',
                'Upgrade-Insecure-Requests': '1'
            }
            
            # 如果URL包含端口号20001，需要特殊处理
            if ':20001' in pdf_url:
                parsed_url = urlparse(pdf_url)
                headers['Host'] = parsed_url.hostname + ':20001'
            
            response = self.session.get(pdf_url, headers=headers, verify=False, timeout=30)
            
            # 检查响应内容类型
            content_type = response.headers.get('Content-Type', '')
            if 'application/pdf' not in content_type and 'pdf' not in content_type:
                print(f"  警告：响应内容类型不是PDF: {content_type}")
                # 检查是否是重定向到错误页面
                if response.status_code == 200 and '<html' in response.text[:100].lower():
                    print(f"  响应看起来是HTML页面，不是PDF文件")
                    print(f"  响应前200字符: {response.text[:200]}")
                    return None
            
            if response.status_code == 200:
                filepath = os.path.join(self.pdf_dir, filename)
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                print(f"  招标公告PDF文件已下载: {filename}")
                return filepath
            else:
                print(f"  下载招标公告PDF失败，状态码: {response.status_code}")
                return None
        except Exception as e:
            print(f"  下载招标公告PDF出错: {e}")
            return None
    
    def process_record(self, record):
        """
        处理单条记录：访问详情页面并下载招标公告PDF
        """
        tender_name = record['标项名称']
        detail_url = record['详情链接']
        
        print(f"正在处理: {tender_name}")
        
        # 获取详细页面
        detail_html = self.fetch_detail_page(detail_url)
        
        if detail_html:
            # 提取招标公告PDF链接
            pdf_url, save_filename = self.extract_tender_announcement_pdf(detail_html, tender_name)
            
            if pdf_url and save_filename:
                # 下载招标公告PDF文件
                self.download_pdf(pdf_url, save_filename)
            else:
                print("  未找到招标公告PDF文件")
        else:
            print(f"  获取详细页面失败")
    
    def get_total_pages(self, rows=10):
        """
        获取总页数
        """
        print("正在获取总页数...")
        
        # 访问初始页面
        if not self.get_initial_page():
            print("无法访问初始页面")
            return 0
        
        # 获取第一页数据以确定总页数
        data = self.fetch_data(page=1, rows=rows)
        if not data:
            print("无法获取数据")
            return 0
        
        total_records = data.get('records', 0)
        total_pages = data.get('total', 0)
        
        print(f"总记录数: {total_records}, 总页数: {total_pages}")
        return total_pages
    
    def process_page(self, page, rows=10):
        """
        处理单个页面的数据
        """
        print(f"开始处理第 {page} 页...")
        
        # 获取页面数据
        data = self.fetch_data(page=page, rows=rows)
        if not data:
            print(f"无法获取第 {page} 页数据")
            return 0
        
        # 解析数据
        parsed_data = self.parse_data_with_links(data)
        
        # 处理每条记录
        print(f"第 {page} 页有 {len(parsed_data)} 条记录")
        for record in parsed_data:
            self.process_record(record)
            # 添加延时，避免请求过于频繁
            time.sleep(0.5)
        
        print(f"第 {page} 页处理完成")
        return len(parsed_data)
    
    def run_concurrent(self, max_workers=5, max_pages=None, rows=10):
        """
        并发运行PDF下载器，下载所有页面的数据
        """
        print("开始并发下载招标公告PDF文件...")
        
        # 获取总页数
        total_pages = self.get_total_pages(rows=rows)
        if total_pages <= 0:
            print("无法获取总页数")
            return
        
        # 如果指定了最大页数，则使用较小的值
        if max_pages:
            total_pages = min(total_pages, max_pages)
        
        print(f"准备并发处理 {total_pages} 页数据，使用 {max_workers} 个工作线程")
        
        # 使用线程池并发处理页面
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_page = {
                executor.submit(self.process_page, page, rows): page 
                for page in range(1, total_pages + 1)
            }
            
            # 处理完成的任务
            total_records = 0
            for future in as_completed(future_to_page):
                page = future_to_page[future]
                try:
                    records_count = future.result()
                    total_records += records_count
                    print(f"第 {page} 页处理完毕，共处理 {records_count} 条记录")
                except Exception as e:
                    print(f"处理第 {page} 页时发生错误: {e}")
            
            print(f"\n所有页面处理完成，共处理 {total_records} 条记录")
    
    def run(self, rows=10):
        """
        运行PDF下载器，只下载招标公告PDF
        """
        print("开始下载招标公告PDF文件...")
        
        # 访问初始页面
        if not self.get_initial_page():
            print("无法访问初始页面")
            return
        
        # 获取第一页数据
        data = self.fetch_data(page=1, rows=rows)
        if not data:
            print("无法获取数据")
            return
        
        # 解析数据
        parsed_data = self.parse_data_with_links(data)
        
        # 处理每条记录
        print(f"\n开始处理第一页的 {len(parsed_data)} 条记录...")
        for i, record in enumerate(parsed_data):
            print(f"\n处理第 {i+1}/{len(parsed_data)} 条记录:")
            self.process_record(record)
            # 添加延时，避免请求过于频繁
            time.sleep(1)
        
        print("\n所有记录处理完成")

def main():
    downloader = HangzhouPublicResourcePDFFetcher()
    # downloader.run(rows=10)  # 处理第一页的10条记录
    downloader.run_concurrent(max_workers=5, max_pages=84, rows=10)  # 并发处理最多84页

if __name__ == "__main__":
    main()