"""
时间：2025/6/29  10:03
"""

# 思路：
# 1.拿到页面源代码
# 2.编写正则表达式提取数据
# 3.保存数据

import requests
import re

# 正则表达式保持不变
obj = re.compile(
    r'<div class="item">.*?<span class="title">(?P<name>.*?)</span>.*?'
    r'导演: (?P<dao>.*?)&nbsp;.*?'
    r'主演: (?P<zhu>.*?)<br>.*?'
    r'(?P<year>\d{4})&nbsp;.*?'
    r'<span class="rating_num".*?>(?P<score>.*?)</span>.*?'
    r'<span>(?P<num>.*?)人评价</span>',
    re.S
)

headers = {'user-agent':
               'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36 Edg/138.0.0.0'}

# 使用追加模式打开文件
f = open('top250.csv', 'a', encoding='utf-8')

# 循环处理10页数据
for page in range(0, 10):
    start = page * 25
    url = f"https://movie.douban.com/top250?start={start}&filter="
    print(f"正在抓取第{page+1}页: {url}")

    resp = requests.get(url, headers=headers)
    pageSource = resp.text

    result = obj.finditer(pageSource)

    # 进行正则匹配
    for i, item in enumerate(result, 1):  # 遍历匹配结果，并输出序号
        print(f"第{page+1}页电影 {i}: {item.group('name').strip()}")
        f.write(
            f'{item.group("name")}, {item.group("dao")}, {item.group("zhu")}, {item.group("year")}, {item.group("score")}, {item.group("num")}\n')

    resp.close()
    print(f"第{page+1}页数据保存完成！")

f.close()
print('所有数据保存成功！')
