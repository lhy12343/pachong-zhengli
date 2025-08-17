import requests
import json
import time
import os
import re
from urllib.parse import urljoin, urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed

# 禁用 urllib3 警告
requests.packages.urllib3.disable_warnings()

class HangzhouPublicResourceDataSpider:
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
    
    def extract_project_details(self, html_content):
        """
        从详细页面中提取项目详细信息
        """
        if not html_content:
            return {}
        
        # 初始化详细信息字典
        details = {
            # 基本信息
            '工程名称': '无',
            '建设单位': '无',
            '项目编号': '无',
            '公告登记日期': '无',
            '开标时间': '无',
            '报名地点': '无',
            '监管部门': '无',
            '招标联系人': '无',
            '招标联系电话': '无',
            '所属地区': '无',
            '工程分类': '无',
            '代理公司': '无',
            '代理联系人': '无',
            '代理联系电话': '无',
            '是否联合体投标': '无',
            
            # 工程概况
            '工程概况': {
                '工程地点': '无',
                '法定代表人': '无',
                '联系地址': '无',
                '招标方式': '无',
                '招标组织形式': '无',
                '资格审查方式': '无',
                '投资总额(万元)': '无',
                '本期概算(万元)': '无',
                '备注': '无'
            },
            
            # 技术规模指标
            '技术规模指标': [],
            
            # 企业及从业人员资格要求
            '企业及从业人员资格要求': {
                '对投标人的承包资质要求': '无',
                '从业人员资格要求': '无'
            }
        }
        
        # 辅助函数：清理HTML内容并检查是否为空
        def clean_content(content):
            if not content:
                return ''
            # 清理HTML标签
            clean_text = re.sub(r'<[^>]+>', '', content).strip()
            # 处理特殊空值字符
            if clean_text in ['&nbsp', '&nbsp;', '', ' ', '\t', '\n', '\r']:
                return ''
            return clean_text
        
        # 定义行模式，用于提取表格中的行
        row_pattern = re.compile(r'<tr[^>]*>(.*?)</tr>', re.DOTALL)
        # 定义单元格模式，用于提取行中的单元格
        cell_pattern = re.compile(r'<td[^>]*>(.*?)</td>', re.DOTALL)
        
        # 提取基础信息（第一个表格）
        # 查找第一个表格
        first_table_pattern = r'<div align=center >\s*<table class=MsoNormalTable[^>]*>.*?</table>'
        first_table_match = re.search(first_table_pattern, html_content, re.DOTALL)
        
        if first_table_match:
            first_table = first_table_match.group(0)
            # 提取表格中的所有行
            rows = row_pattern.findall(first_table)
            
            for row in rows:
                # 提取单元格，查找标题和内容配对
                cells = cell_pattern.findall(row)
                
                # 查找每行中的标题和内容单元格
                if len(cells) >= 2:
                    # 清理标题和内容
                    title = clean_content(cells[0]).rstrip('：').rstrip(':')
                    content = clean_content(cells[1])
                    
                    # 根据标题填充字段
                    field_mapping = {
                        '工程名称': '工程名称',
                        '建设单位': '建设单位',
                        '项目编号': '项目编号',
                        '公告登记日期': '公告登记日期',
                        '开标时间': '开标时间',
                        '报名地点': '报名地点',
                        '监管部门': '监管部门',
                        '招标联系人': '招标联系人',
                        '招标联系电话': '招标联系电话',
                        '所属地区': '所属地区',
                        '工程分类': '工程分类',
                        '代理公司': '代理公司',
                        '代理联系人': '代理联系人',
                        '代理联系电话': '代理联系电话',
                        '是否联合体投标': '是否联合体投标'
                    }
                    
                    if title in field_mapping and content:
                        details[field_mapping[title]] = content
                    
                    # 处理一行中包含多个字段的情况（如联系人和电话在同一行）
                    if len(cells) >= 4:
                        title2 = clean_content(cells[2]).rstrip('：').rstrip(':')
                        content2 = clean_content(cells[3])
                        if title2 in field_mapping and content2:
                            details[field_mapping[title2]] = content2
        
        # 提取工程概况（查找包含"工程概况"文本的段落后的表格）
        overview_section_pattern = r'工程概况.*?<table class=MsoNormalTable[^>]*>(.*?)</table>'
        overview_section_match = re.search(overview_section_pattern, html_content, re.DOTALL)
        
        if overview_section_match:
            overview_table = overview_section_match.group(1)
            # 提取工程概况表格中的行
            overview_rows = row_pattern.findall(overview_table)
            
            for row in overview_rows:
                cells = cell_pattern.findall(row)
                
                if len(cells) >= 2:
                    key = clean_content(cells[0]).rstrip('：').rstrip(':')
                    value = clean_content(cells[1])
                    
                    if key in details['工程概况'] and value:
                        details['工程概况'][key] = value
        
        # 提取技术规模指标（查找包含"技术规模指标"文本的段落后的表格）
        tech_section_pattern = r'技术规模指标.*?<table class=MsoNormalTable[^>]*>(.*?)</table>'
        tech_section_match = re.search(tech_section_pattern, html_content, re.DOTALL)
        
        if tech_section_match:
            tech_table = tech_section_match.group(1)
            # 提取技术指标表格中的行
            tech_rows = row_pattern.findall(tech_table)
            
            # 跳过表头，从第二行开始处理
            for row in tech_rows[1:]:
                cells = cell_pattern.findall(row)
                
                if len(cells) >= 3:
                    indicator = clean_content(cells[0])
                    value = clean_content(cells[1])
                    unit = clean_content(cells[2])
                    
                    # 只有当不是空行时才添加
                    if indicator or value or unit:
                        indicator_data = {
                            '指标项': indicator or '无',
                            '值': value or '无',
                            '指标单位': unit or '无'
                        }
                        details['技术规模指标'].append(indicator_data)
        
        # 提取企业及从业人员资格要求（查找包含"资格要求"文本的段落后的表格）
        qual_section_pattern = r'企业及从业人员资格要求.*?<table class=MsoNormalTable[^>]*>(.*?)</table>'
        qual_section_match = re.search(qual_section_pattern, html_content, re.DOTALL)
        
        if qual_section_match:
            qual_table = qual_section_match.group(1)
            # 提取资格要求表格中的行
            qual_rows = row_pattern.findall(qual_table)
            
            for row in qual_rows:
                cells = cell_pattern.findall(row)
                
                if len(cells) >= 2:
                    key = clean_content(cells[0]).rstrip('：').rstrip(':')
                    value = clean_content(cells[1])
                    
                    if '承包资质' in key and value:
                        details['企业及从业人员资格要求']['对投标人的承包资质要求'] = value
                    elif '从业人员' in key and value:
                        details['企业及从业人员资格要求']['从业人员资格要求'] = value
        
        return details
    
    def process_record(self, record):
        """
        处理单条记录：访问详情页面并提取详细信息
        """
        tender_name = record['标项名称']
        detail_url = record['详情链接']
        
        print(f"正在处理: {tender_name}")
        
        # 获取详细页面
        detail_html = self.fetch_detail_page(detail_url)
        
        if detail_html:
            # 提取详细信息
            project_details = self.extract_project_details(detail_html)
            
            # 合并基础信息和详细信息
            full_details = {**record, **project_details}
            
            return full_details
        else:
            print(f"  获取详细页面失败")
            return record
    
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
            return []
        
        # 解析数据
        parsed_data = self.parse_data_with_links(data)
        
        # 处理每条记录
        print(f"第 {page} 页有 {len(parsed_data)} 条记录")
        page_details = []
        for record in parsed_data:
            details = self.process_record(record)
            if details:
                page_details.append(details)
            # 添加延时，避免请求过于频繁
            time.sleep(0.5)
        
        print(f"第 {page} 页处理完成")
        return page_details
    
    def run_concurrent(self, max_workers=5, max_pages=None, rows=10):
        """
        并发运行爬虫，下载所有页面的数据
        """
        print("开始并发爬取详细信息...")
        
        # 获取总页数
        total_pages = self.get_total_pages(rows=rows)
        if total_pages <= 0:
            print("无法获取总页数")
            return []
        
        # 如果指定了最大页数，则使用较小的值
        if max_pages:
            total_pages = min(total_pages, max_pages)
        
        print(f"准备并发处理 {total_pages} 页数据，使用 {max_workers} 个工作线程")
        
        all_details = []
        
        # 使用线程池并发处理页面
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_page = {
                executor.submit(self.process_page, page, rows): page 
                for page in range(1, total_pages + 1)
            }
            
            # 处理完成的任务
            for future in as_completed(future_to_page):
                page = future_to_page[future]
                try:
                    page_details = future.result()
                    all_details.extend(page_details)
                    print(f"第 {page} 页处理完毕，共处理 {len(page_details)} 条记录")
                except Exception as e:
                    print(f"处理第 {page} 页时发生错误: {e}")
            
            print(f"\n所有页面处理完成，共处理 {len(all_details)} 条记录")
            
            # 保存详细信息到JSON文件，设置为代码文件所在目录中
            if all_details:
                # 获取脚本所在目录
                script_dir = os.path.dirname(os.path.abspath(__file__))
                filename = os.path.join(script_dir, '杭州公共资源交易完整数据.json')
                try:
                    with open(filename, 'w', encoding='utf-8') as f:
                        json.dump(all_details, f, ensure_ascii=False, indent=2)
                    print(f"\n详细信息已保存到 '{filename}' 文件中")
                except Exception as e:
                    print(f"保存详细信息文件时出错: {e}")
            
            return all_details

def main():
    spider = HangzhouPublicResourceDataSpider()
    # 并发处理所有页面
    details = spider.run_concurrent(max_workers=5, max_pages=84, rows=10)

if __name__ == "__main__":
    main()