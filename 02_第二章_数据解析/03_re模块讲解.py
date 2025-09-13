"""
时间：2025/6/27  15:04
"""

import re

# result = re.findall('a', '我是一个abcdeafg')  # 匹配所有a字符
# print(result)

# result = re.findall(r'\d+', '我是一个abcdeafg,我的电话号码是13812345678')  # 匹配所有数字
# print(result)

# 重点
# result = re.finditer(r'\d+', '我是一个abcdeafg,我的电话号码是13812345678') # 匹配所有数字，返回迭代器
# print(result)
# for match in result:
#     print(match.group())  # 输出迭代器中每一个匹配的数字,group()方法返回匹配的字符串

# search()方法，只匹配第一个匹配的结果，返回一个Match对象，如果没有匹配到，返回None
# result = re.search(r'\d+', '我叫周结论，今年32岁，班级是3年2班')
# print(result.group())

# match()方法，只匹配字符串的开始位置，返回一个Match对象，如果没有匹配到，返回None
# result = re.match(r'\d+', '我叫周结论，今年32岁，班级是3年2班')
# print(result)

# 预加载模式
# obj = re.compile(r'\d+')
# result = obj.findall('我叫周结论，今年32岁，班级是3年2班')
# print(result)


s = """
<div class='西游记'><span id='10010'>中国联通</span></div>
<div class='西游记'><span id='10086'>中国移动</span></div>
"""
# 想要提取数据必须用（）包裹起来，可以单独曲起名字
# (?P<名字>正则)
# 提取数据的时候，需要用group("名字")来提取)
obj = re.compile(r"<span id='(?P<id>\d+)'>(?P<name>.*?)</span>")  # 匹配所有span标签,并返回span标签中的内容
result = obj.finditer(s)
for item in result:
    print(item.group('id'), item.group('name'))
