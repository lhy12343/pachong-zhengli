"""
时间：2025/7/9  16:20
"""

from lxml import etree

xml = """
<book>
    <id>1</id>
    <name>野花遍地香</name>
    <price>100</price>
    <nick>臭豆腐</nick>
    
    <author>
        <nick id='10086'>周大强</nick>
        <nick id='10010'>周芷若</nick>
        <nick class='jay'>周周杰伦</nick>
        <nick class='jolin'>蔡依林</nick>
        <div>
            <nick>惹了祸</nick>
        </div>
    </author>
    
    <partner>
        <nick id='ppc'>胖胖陈</nick>
        <nick id='ppbc'>胖胖不陈</nick>
    </partner>
    
</book>
"""

# 1. 解析xml字符串,此时练习的是xpath解析xml字符串
# et = etree.XML(xml)
# result = et.xpath('/book') # /book为根节点
# result = et.xpath('/book/name') # 在xpath中，/表示根节点，.表示当前节点，..表示父节点，//表示任意节点
# result = et.xpath('/book/name/text()')  # 获取name节点的文本内容
# result = et.xpath("/book//nick/text()")  # 获取book节点下的所有nick节点,并获取文本内容
# result = et.xpath('/book/*/nick/text()')  # 获取book节点下的子节点的所有nick节点,并获取文本内容
# result = et.xpath('/book/author/nick[@class="jay"]/text()')  # 获取book节点下的author节点下的nick节点,并获取文本内容,且只获取class属性为jay的节点
# result = et.xpath('/book/partner/nick/@id')  # 获取book节点下的partner节点下的nick节点,并获取id属性的值
# print(result)


html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>我的网页</title>
</head>
<body>
    <ul>
        <li><a href='http://www.baidu.com'>百度</a></li>
        <li><a href='http://www.google.com'>谷歌</a></li>
        <li><a href='http://www.sogou.com'>搜狗</a></li>
    </ul>
    <ol>
        <li><a href='http://www.taobao.com'>淘宝</a></li>
        <li><a href='http://www.jd.com'>京东</a></li>
        <li><a href='http://www.amazon.com'>亚马逊</a></li>
    </ol>
    <div class='job'>李嘉诚</div>
    <div class = "common'>胡辣汤</div>
</body>
</html>
"""


et = etree.HTML(html)
# li_list = et.xpath("/html/body/ul/li[2]/a/text()")  # 获取所有li节点
# print(li_list)

li_list = et.xpath("//li")
for li in li_list:
    href = li.xpath("./a/@href")[0]
    text = li.xpath("./a/text()")[0]
    print(href, text)