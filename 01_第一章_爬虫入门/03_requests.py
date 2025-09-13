"""
时间：2025/6/24  17:07
"""

import requests  # 导入requests库，用于发送HTTP请求

# 提示用户输入要搜索的内容，并将输入的内容存储在变量content中
content = input('请输入要搜索的内容：')

# 构建Bing搜索的URL，将用户输入的内容作为查询参数
url = f'https://www.sogou.com/web?query={content}'

# # 设置请求头，模拟浏览器访问‘
headers = {"user-agent":
               "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36 Edg/137.0.0.0"}

# # 发送GET请求到Bing搜索URL，并携带请求头
resp = requests.get(url, headers=headers)

# 打印响应的文本内容，即搜索结果页面的HTML代码

# resp = requests.get(url)
# print(resp.text)

print(resp.request.headers)  # 打印请求头信息
