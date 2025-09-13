# 导入必要的库
from tqdm import tqdm  # 用于显示进度条
import time  # 用于时间延迟
import random  # 用于生成随机数
from datetime import datetime, timedelta  # 用于日期处理
import pandas as pd  # 用于数据处理和CSV导出
import requests  # 用于发送HTTP请求


def fetch_xinfadi_data(start_date, end_date, page=1, limit=20):
    """
    获取新发地价格数据的核心函数
    参数:
        start_date: 开始日期(格式:YYYY/MM/DD)
        end_date: 结束日期
        page: 页码(默认1)
        limit: 每页数据量(默认20)
    返回:
        JSON格式的响应数据或None(如果请求失败)
    """
    url = "http://www.xinfadi.com.cn/getPriceData.html"
    # 设置请求头，模拟浏览器访问
    headers = {
        "User-Agent": "Mozilla/5.0...",  # 浏览器标识
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",  # 表单编码
        "Origin": "http://www.xinfadi.com.cn",  # 请求来源
        "Referer": "http://www.xinfadi.com.cn/price.html"  # 引用页面
    }

    # 构造POST请求的表单数据
    payload = {
        "limit": limit,  # 每页数据量
        "current": page,  # 当前页码
        "pubDateStartTime": start_date,  # 查询开始日期
        "pubDateEndTime": end_date,  # 查询结束日期
        "prodPcatid": "",  # 产品大类ID(空表示不筛选)
        "prodCatid": "",  # 产品小类ID
        "prodName": ""  # 产品名称
    }

    try:
        # 发送POST请求
        response = requests.post(url, headers=headers, data=payload)
        response.raise_for_status()  # 检查请求是否成功
        return response.json()  # 返回JSON格式的响应数据
    except Exception as e:
        print(f"请求失败: {e}")  # 打印错误信息
        return None


def enhanced_crawler(start_date, end_date, max_workers=3):
    """
    支持多日期范围和多线程的增强版爬虫
    参数:
        start_date: 开始日期字符串(格式:YYYY/MM/DD)
        end_date: 结束日期字符串
        max_workers: 线程池最大线程数(默认3)
    返回:
        pandas.DataFrame格式的数据或None(如果没有数据)
    """
    from concurrent.futures import ThreadPoolExecutor  # 线程池执行器

    def date_range(start, end):
        """生成日期范围内的所有日期列表"""
        delta = end - start  # 计算日期差
        return [start + timedelta(days=i) for i in range(delta.days + 1)]  # 生成日期列表

    def fetch_single_day(day):
        """获取单日数据的函数"""
        day_str = day.strftime("%Y/%m/%d")  # 格式化日期
        try:
            # 随机延迟(0.5-1.5秒)，防止被封
            time.sleep(random.uniform(0.5, 1.5))

            # 获取当天数据(设置limit=1000获取尽可能多的数据)
            data = fetch_xinfadi_data(
                start_date=day_str,
                end_date=day_str,
                limit=1000
            )

            # 如果获取到数据，为每条数据添加日期字段
            if data and data.get('list'):
                for item in data['list']:
                    item['date'] = day_str  # 添加日期标记
                return data['list']  # 返回当天的数据列表
        except Exception as e:
            print(f"获取 {day_str} 数据失败: {e}")
        return []  # 发生错误返回空列表

    # 将字符串日期转换为datetime对象
    start_dt = datetime.strptime(start_date, "%Y/%m/%d")
    end_dt = datetime.strptime(end_date, "%Y/%m/%d")
    dates = date_range(start_dt, end_dt)  # 生成日期列表

    all_data = []  # 存储所有数据

    # 使用线程池并发获取数据
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 使用tqdm显示进度条，executor.map并行执行fetch_single_day
        results = list(tqdm(executor.map(fetch_single_day, dates), total=len(dates)))

    # 合并所有结果
    for result in results:
        all_data.extend(result)

    # 如果有数据，保存为CSV文件
    if all_data:
        df = pd.DataFrame(all_data)  # 转换为DataFrame
        # 生成文件名(去除日期中的斜杠)
        filename = f"xinfadi_{start_date.replace('/', '')}_{end_date.replace('/', '')}.csv"
        # 保存为CSV(使用utf_8_sig编码避免中文乱码)
        df.to_csv(filename, index=False, encoding='utf_8_sig')
        print(f"共获取 {len(all_data)} 条数据，已保存到 {filename}")
        return df
    return None  # 没有数据返回None


# 示例：爬取2025年1月1日至2025年1月31日数据
if __name__ == '__main__':
    enhanced_crawler("2025/01/01", "2025/01/31")
