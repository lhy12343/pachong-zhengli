"""
时间：2025/7/8  15:27
简单版图片下载器
功能：从网站下载图片到本地img文件夹
"""

import requests  # 用于发送网络请求
from bs4 import BeautifulSoup  # 用于解析网页
import os  # 用于操作文件和目录

# 创建图片保存目录（如果不存在）
if not os.path.exists('img_07'):  # 检查img文件夹是否存在
    os.mkdir('img_07')  # 不存在则创建

# 目标网站URL
url = 'https://www.umei.cc/weimeitupian/oumeitupian/'
domain = 'https://www.umei.cc'  # 网站主域名

# 1. 获取主页面内容
resp = requests.get(url)  # 发送GET请求
resp.encoding = 'utf-8'  # 设置编码为UTF-8

# 2. 解析主页面
main_page = BeautifulSoup(resp.text, 'html.parser')  # 创建BeautifulSoup对象
# 查找所有包含图片的a标签（根据class选择）
a_list = main_page.find_all('a', class_='img_album_btn')

# 3. 遍历每个图片链接
for a in a_list:
    # 构建子页面完整URL
    child_url = domain + a['href']  # 拼接完整URL

    # 获取子页面内容
    child_resp = requests.get(child_url)
    child_resp.encoding = 'utf-8'

    # 解析子页面
    child_page = BeautifulSoup(child_resp.text, 'html.parser')

    # 4. 查找子页面中的所有图片
    for img in child_page.find_all('img', alt=''):  # 查找没有alt属性的img标签
        img_url = img['src']  # 获取图片URL

        # 提取文件名：取URL最后部分作为文件名
        filename = img_url.split('/')[-1]  # 按/分割后取最后一段

        # 5. 下载图片数据
        img_data = requests.get(img_url).content  # 获取图片二进制数据

        # 6. 保存图片到本地
        with open(f'img_07/{filename}', 'wb') as f:  # 以二进制写入模式打开文件
            f.write(img_data)  # 写入图片数据

        print(f'已下载: {filename}')  # 打印下载信息

# 所有图片下载完成提示
print('所有图片下载完成！')
