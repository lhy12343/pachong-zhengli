"""
时间：2025/7/7  17:11
"""

# 安装bs4
# pip install beautifulsoup4

from bs4 import BeautifulSoup

html = """
<ul>
    <li><a href="zhangwuji.com">张无忌</a></li>
    <li id='abc'><a href="zhouxingchi.com">周星驰</a></li>
    <li><a href="liubei.com">刘备</a></li>
    <li><a href="wuzetian.com">武则天</a></li>
    <a href="jinmaoshiwang.com">金毛狮王</a></li>
</ul>
"""

# 1.初始化BeautifulSoup对象
page = BeautifulSoup(html, 'html.parser')
# page.find("标签名", attrs={"属性名": "值"})  # 查找某个元素,返回第一个符合条件的元素
li = page.find("li", attrs={"id": "abc"})  # 查找id为abc的li元素
# page.find_all()  # 查找所有符合条件的元素,返回列表
print(li.find())  # 查找第一个子元素,返回第一个符合条件的元素
a = li.find("a")  # 查找li元素的第一个a元素
print(a)  # 输出a标签
print(a.text)  # 输出a标签的文本内容
print(a.get("href"))  # 输出a标签的href属性值


li_list = page.find_all("li")
for li in li_list:
    a = li.find("a")  # 查找li元素的第一个a元素
    text = a.text
    href = a.get("href")
    print(text, href)