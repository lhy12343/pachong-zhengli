"""
时间：2025/6/23  21:03
"""

import requests

# 爬取百度的页面源代码
url = 'https://www.baidu.com/'
resp = requests.get(url)
resp.encoding = 'utf-8'
# 打印响应内容
print(resp.text)