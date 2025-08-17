"""
时间：2025/6/20  11:42
"""

from urllib.request import urlopen

url = "https://www.baidu.com"
resp = urlopen(url)
# print(resp.read().decode('utf-8'))  # 输出网页源码,并去除首尾空白
with open('mybaidu.html', mode='w', encoding='utf-8') as f:  # mode='w'表示写入文件, encoding='utf-8'表示编码格式为utf-8
    f.write(resp.read().decode('utf-8'))  # 将网页源码写入文件

"""

在Python中，urlopen(url).read()返回的是字节流（bytes类型），
而写入文件或打印时需要转换成字符串（str类型），
因此需要通过.decode('utf-8')进行解码。

"""
