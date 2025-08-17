"""
时间：2025/7/12  14:41
"""

import requests
import json
import csv
from datetime import datetime


def get_page_source(url, headers):
    resp = requests.get(url, headers=headers)
    resp.encoding = 'utf-8'
    return resp.text


def extract_data(item):
    """从单条数据中提取所需信息"""
    # 用户名
    username = item.get('username', '')

    # 车辆类型
    specname = item.get('specname', '')

    # 行驶里程
    distance = item.get('distance', '')

    # 百公里油耗
    oil_consumption = f"{item.get('actual_oil_consumption', '')}L"

    # 裸车购买价
    buyprice = item.get('buyprice', '')

    # 购买时间
    bought_date = item.get('boughtDate', '')

    # 购买地点
    buyplace = item.get('buyplace', '')

    # 评价口碑
    average_score = item.get('averageScore', '')

    # 各项评分
    score_list = []
    for score in item.get('scoreList', []):
        score_list.append(f"{score.get('name', '')}:{score.get('value', '')}")
    scores_str = "，".join(score_list)

    # 购车目的
    purposes = [purpose['name'] for purpose in item.get('purposes', [])]
    purposes_str = " ".join(purposes)

    # 满意和不满意评价
    satisfied = ""
    unsatisfied = ""
    for content in item.get('contents', []):
        if content.get('structuredid') == 1:  # 满意
            satisfied = content.get('content', '')
        elif content.get('structuredid') == 2:  # 不满意
            unsatisfied = content.get('content', '')

    return {
        "用户名": username,
        "车辆类型": specname,
        "行驶里程": distance,
        "百公里油耗": oil_consumption,
        "裸车购买价": buyprice,
        "购买时间": bought_date,
        "购买地点": buyplace,
        "评价口碑": average_score,
        "各项评分": scores_str,
        "购车目的": purposes_str,
        "满意": satisfied,
        "不满意": unsatisfied
    }


def save_to_csv(data, filename):
    """将数据保存为CSV文件"""
    with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
    print(f"数据已保存到{filename}，共{len(data)}条记录")


def main():
    url = 'https://koubeiipv6.app.autohome.com.cn/pc/series/list?pm=3&seriesId=146&pageIndex=1&pageSize=20&yearid=0&ge=0&seriesSummaryKey=0&order=0'

    headers = {
        'authority': 'koubeiipv6.app.autohome.com.cn',
        'method': 'GET',
        'path': '/pc/series/list?pm=3&seriesId=146&pageIndex=1&pageSize=20&yearid=0&ge=0&seriesSummaryKey=0&order=0',
        'scheme': 'https',
        'accept': 'application/json, text/plain, */*',
        'accept-encoding': 'gzip, deflate, br, zstd',
        'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'cache-control': 'no-cache',
        'cookie': '_ac=XyD4zz6bmo8F4VYFQsJeqG51ATEZDchM-yNygzKnXMUmCPvSD1ed; sessionid=74E49DE7-9455-46E7-9C40-0EA25A0F46F3%7C%7C2025-07-12+14%3A41%3A01.954%7C%7Cwww.bing.com; autoid=122a23d9bcc4c288c450c12ff42e73bb; sessionvid=8B5EE519-D7F0-45DF-9A73-3867E6E3E2BD; cookieCityId=330100; __ah_uuid_ng=c_74E49DE7-9455-46E7-9C40-0EA25A0F46F3; sessionip=117.147.119.196; area=330105; historyseries=146; fvlid=1752304481876etili5ta; mmb__cuif=0AAE4085-EA18-4B20-8F7D-F9309BDCEB06.1.1752304517677.1752304517677.1752304517677; mmb__vif=0AAE4085-EA18-4B20-8F7D-F9309BDCEB06.1.1752304517677; pvidchain=3311224,100124,3454440; v_no=17; visit_info_ad=74E49DE7-9455-46E7-9C40-0EA25A0F46F3||8B5EE519-D7F0-45DF-9A73-3867E6E3E2BD||-1||-1||17; ref=www.bing.com%7C0%7C0%7C0%7C2025-07-12+15%3A29%3A31.452%7C2025-07-12+14%3A41%3A01.954; ahpvno=18',
        'origin': 'https://k.autohome.com.cn',
        'pragma': 'no-cache',
        'priority': 'u=1, i',
        'referer': 'https://k.autohome.com.cn/',
        'sec-ch-ua': '"Not)A;Brand";v="8", "Chromium";v="138", "Microsoft Edge";v="138"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-site',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36 Edg/138.0.0.0'
    }

    # 1. 获取页面源代码
    html = get_page_source(url, headers)

    # 2. 解析JSON数据
    try:
        data = json.loads(html)
        if data.get('result') and data['result'].get('list'):
            items = data['result']['list']
            print(f"成功获取{len(items)}条数据")

            # 3. 提取所需数据
            extracted_data = []
            for i, item in enumerate(items, 1):
                extracted = extract_data(item)
                extracted_data.append(extracted)
                print(f"第{i}条数据提取完成: {extracted['用户名']}")

            # 4. 保存为CSV文件
            filename = '汽车之家爬取用户口碑数据.csv'
            save_to_csv(extracted_data, filename)

            # 5. 打印第一条数据作为示例
            if extracted_data:
                print("\n第一条数据示例:")
                first = extracted_data[0]
                print(f"用户名：{first['用户名']}，车辆类型：{first['车辆类型']}，行驶里程：{first['行驶里程']}，"
                      f"百公里油耗：{first['百公里油耗']}，裸车购买价：{first['裸车购买价']}，"
                      f"购买时间：{first['购买时间']}，购买地点：{first['购买地点']}，"
                      f"评价口碑：{first['评价口碑']}（{first['各项评分']}），"
                      f"购车目的：{first['购车目的']}，满意：{first['满意']}，"
                      f"不满意：{first['不满意']}")
        else:
            print("未获取到有效数据")
    except json.JSONDecodeError:
        print("JSON解析失败")


if __name__ == '__main__':
    main()
