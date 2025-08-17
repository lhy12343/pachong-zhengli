"""
时间：2025/7/16  10:41
"""

# 代理，可以使用第三方的机器来代理你的请求
# 代理的弊端：
#           1.慢
#           2.代理ip不好找
import requests

url = 'https://www.baidu.com'

# 在代理URL中添加用户名和密码
proxy = {
    'http': 'http://fd3575241672:sw8tr2vb@116.208.203.60:21840',
    'https': 'http://fd3575241672:sw8tr2vb@116.208.203.60:21840',
}

try:
    resp = requests.get(url, proxies=proxy, timeout=10)
    resp.encoding = 'utf-8'
    print(resp.text)
except requests.exceptions.ProxyError:
    print("代理认证失败，请检查用户名/密码")
except requests.exceptions.Timeout:
    print("代理连接超时")


