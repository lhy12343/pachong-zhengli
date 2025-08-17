import requests
from bs4 import BeautifulSoup
import json
import csv
from datetime import datetime

# 1. 获取HTML页面数据
url1 = 'http://www.xinfadi.com.cn/priceDetail.html'
resp1 = requests.get(url1)
page = BeautifulSoup(resp1.text, features="html.parser")

# 2. 获取API数据
url = 'http://www.xinfadi.com.cn/getPriceData.html'
form_data = {
    "current": 1,
    "limit": 20,
    "prodPcatid": "",
    "prodCatid": "",
    "prodName": ""
}
resp = requests.post(url, data=form_data)
json_data = json.loads(resp.text)

# 3. 准备CSV文件
filename = f'农产品价格_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
headers = ['一级分类', '二级分类', '品名', '最低价', '平均价', '最高价', '规格', '产地', '单位', '发布日期']

with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
    writer = csv.writer(f)

    # 写入表头
    writer.writerow(headers)

    # 写入数据
    for item in json_data['list']:
        row = [
            item.get('prodCat', ''),
            item.get('prodPcat', ''),
            item.get('prodName', ''),
            item.get('lowPrice', ''),
            item.get('avgPrice', ''),
            item.get('highPrice', ''),
            item.get('place', ''),
            item.get('specInfo', ''),
            item.get('unitInfo', ''),
            item.get('pubDate', '')[:10]  # 只取日期部分
        ]
        writer.writerow(row)

print(f"数据已成功保存到 {filename}")
