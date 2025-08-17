"""
时间：2025/6/24  18:23
"""

import requests

url = 'https://movie.douban.com/j/chart/top_list'

data = {"type": "13",
        'interval_id': '100:90',
        'action': '',
        'start': 0,
        'limit': 20}

headers = {
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36 Edg/137.0.0.0"}
resp = requests.get(url, params=data, headers=headers)

# print(resp.text) # 字符串格式的响应内容
print(resp.request.url)  # 请求的url
print(resp.json())  # 字典格式的响应内容
