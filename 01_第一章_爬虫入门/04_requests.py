"""
时间：2025/6/24  17:25
"""

import requests

url = 'https://fanyi.baidu.com/sug'  # 百度翻译API

hehe = {'kw': input('请输入一个单词:')}  # 输入单词

# 设置请求头，模拟浏览器访问
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36 Edg/137.0.0.0"
}

# 解析提供的Cookie字符串
cookie_str = "BDUSS=mx5ZXFRWWJpaEdtc1ZqSHp1TVJvWjZZR09WclJlempGcllWaTh4THJsc0V5Y2xuSVFBQUFBJCQAAAAAAAAAAAEAAAB0-lwzb2vC8G1lb2sAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAQ8omcEPKJna; BDUSS_BFESS=mx5ZXFRWWJpaEdtc1ZqSHp1TVJvWjZZR09WclJlempGcllWaTh4THJsc0V5Y2xuSVFBQUFBJCQAAAAAAAAAAAEAAAB0-lwzb2vC8G1lb2sAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAQ8omcEPKJna; BIDUPSID=EF9684D07E0F5F0EA663081CD012E35B; PSTM=1741004571; MAWEBCUID=web_GUQoDlWgUbkmMsyfOaJjMKcwydZQsktdyRbBzPrdnyCwAlRKhG; BAIDUID=3587BCCC26E8A6836A964ADC194A9190:FG=1; H_WISE_SIDS_BFESS=61027_62325_62336_62347_62373_62427_62468_62475_62457_62454_62453_62451_62541_62619_62638_62675_62687; MCITY=-179%3A; BAIDUID_BFESS=3587BCCC26E8A6836A964ADC194A9190:FG=1; BAIDU_WISE_UID=wapp_1749270061466_139; ZFY=MKSN978frTg0T5wfcae71BGNIovfO7gZPOf0Xo7rY8c:C; H_WISE_SIDS=62325_63140_63327_63402_63442_63568_63564_63584_63576_63637_63630_63647_63655_63677; H_PS_PSSID=62325_63140_63327_63402_63568_63564_63584_63576_63637_63630_63647_63655_63677_63725_63715; ab_sr=1.0.1_N2E2Y2RkZmQ5ZTE2YzEyYjQ0MWYzMzQyMjg0M2M2MzcwZTMyMDEwYTM4ZWNiMzU2ZGNkNzYwNGNjMjIyODUzZmQwNThiMTYxOGI0M2JhMmE1YzZlMzQ4NzdiMzI2YWU1ZWNlN2VkNmM4MmNiMzY5YTY1MTE1MDkzMDkzYTBjNmU0ODk0ZTM1Njc3YzkyNTU0ZjU1MzU5NDc3ZmEwODUwNQ==; RT=\"z=1&dm=baidu.com&si=7d4ce26c-2ea5-43c3-b9b3-56ae12b38b8b&ss=mcabllqy&sl=d&tt=fiw&bcn=https%3A%2F%2Ffclog.baidu.com%2Flog%2Fweirwood%3Ftype%3Dperf&ld=1f1mn\""

# 将Cookie字符串转换为字典
cookies = {}
for item in cookie_str.split(';'):
    # 处理可能的空格和空项
    item = item.strip()
    if not item:
        continue
    # 分割键值对（只分割第一个等号）
    key_value = item.split('=', 1)
    if len(key_value) == 2:
        key, value = key_value
        cookies[key.strip()] = value.strip()

# 发送POST请求（添加headers和cookies）
resp = requests.post(url, data=hehe, headers=headers, cookies=cookies)

# print(resp.text)  # 拿到的是文本字符串
print(resp.json())  # 拿到的是json数据
