"""
时间：2025/7/11  15:38
"""

from pyquery import PyQuery

# html = """
#
# <ul>
#     <li class='aaa'><a href="http://www.baidu.com">百度</a></li>
#     <li class='bbb'><a href="http://www.sina.com">新浪</a></li>
#     <li class='ccc' id='qq'><a href="http://www.qq.com">腾讯</a></li>
#     <li class='ddd'><a href="http://www.yuanlai.com">缘来</a></li>
# </ul>
#
# """

# 加载html内容
# p = PyQuery(html)

# print(p)
# print(html)
# print(type(p))
# pyquery对象直接（css选择器）
# li = p("a")
# print(li)

# # 链式操作
# a = p('li')('a')  # 等价于 p('li').children('a'), 选取所有li下的a标签
# print(a)


# a = p("li a")  # 等价于 p('li').children('a'), 选取所有li下的a标签
# print(a)

# a = p('.aaa a')  # class='aaa'的li标签
# print(a)

# a = p('#qq a')  # id='qq'的a标签
# print(a)

# a = p('#qq a').attr('href')  # 获取id='qq'的a标签的href属性
# b = p('#qq a').text()  # 获取id='qq'的a标签的文本内容
# print(a, b)

# 坑
# href = p('li a').attr('href')  # 错误，返回的是第一个a标签的href属性，而不是所有a标签的href属性
# print(href)

# # 多个标签拿属性
# it = p('li a').items()  # 多个标签拿属性,items()返回一个迭代器
# print(it)
# for item in it:  # 遍历多个标签
#     href = item.attr('href')  # 获取每个标签的href属性
#     text = item.text()
#     print(href, text)

# 快速总结
# 1. PyQuery对象可以直接使用css选择器进行选择
# 2.items()方法可以获取多个标签的属性
# 3.attr(属性名)方法可以获取标签的属性值
# 4.text()方法可以获取标签的文本内容

# div = """
#
# <div><span>我爱你</span></div>
#
# """
# p = PyQuery(div)
# html = p('div').html()  # 获取div标签的html内容 全都要
# text = p('div').text()  # 获取div标签的文本内容（只要文本）
# print(html)
# print(text)


html = """
<html>
    <div class='aaa'>哒哒哒</div>
    <div class='bbb'>嘟嘟嘟</div>
    <div class='ccc'>哈哈哈</div>
    <div class='ddd'>噢噢噢</div>
    </html>
"""

p = PyQuery(html)
# p('div.aaa').after("""<div class='fff'>吼吼吼</div>""")  # 在div标签后面插入新的div, 能够换行
# p('div.aaa').append("""<span>我爱你</span>""")  # 在div内部插入新的span, 不能换行
# p('div.bbb').attr('class', 'eee')  # 修改div标签的class属性
# p('div.bbb').attr('id', '12306')  # 添加div标签的id属性,前提是没有id属性
# p('div.bbb').remove_attr('id')  # 删除id标签
# p('div.ddd').text('嘿嘿嘿')  # 修改div标签的文本内容

dic = {}
dic['jay'] = "周杰伦"
print(dic)
print(p)
