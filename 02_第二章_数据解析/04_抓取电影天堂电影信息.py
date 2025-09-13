import requests
import re
import csv

# 创建并打开CSV文件
with open('movie_info.csv', 'w', newline='', encoding='utf-8-sig') as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(['电影名称', '下载链接'])

    url = 'https://www.dytt8.com/'
    resp = requests.get(url)
    resp.encoding = 'gbk'

    obj = re.compile(r'最新电影推荐.*?<ul>(?P<html>.*?)</ul>', re.S)
    result1 = obj.search(resp.text)

    html = result1.group('html')
    obj1 = re.compile(r"<tr>.*?<a href='(?P<href>.*?)'>", re.S)
    result2 = obj1.finditer(html)

    # 修复正则表达式语法错误
    obj2 = re.compile(
        r'<div id="Zoom">.*?'
        r'(?:◎片\s*名\s*(?P<movie>.*?)<br />|'  # 匹配片名
        r'◎译\s*名\s*(?P<translation>.*?)<br />).*?'  # 或匹配译名
        r'.*?<a.*?href="(?P<download>magnet:\?xt=.*?)"',  # 下载链接
        re.S
    )

    for i, item in enumerate(result2, 1):
        try:
            href = item.group('href')
            child_url = 'https://www.dytt8.com' + href
            print(f"正在处理第 {i} 部电影: {child_url}")

            child_resp = requests.get(child_url, timeout=10)
            child_resp.encoding = 'gbk'

            result3 = obj2.search(child_resp.text)
            if result3:
                # 安全处理可能为None的值
                movie_name = result3.group('movie')
                translation = result3.group('translation')

                # 处理None值并清理空白
                movie_name = movie_name.strip() if movie_name else ""
                translation = translation.strip() if translation else ""

                download = result3.group('download')

                # 使用电影名称（优先）或译名
                movie = movie_name if movie_name else translation

                writer.writerow([movie, download])
                print(f"  成功保存: {movie}")
            else:
                print(f"  未找到电影信息")
                # 保存未匹配页面用于调试
                with open(f'no_match_page_{i}.html', 'w', encoding='gbk') as f:
                    f.write(child_resp.text)
        except Exception as e:
            print(f"  处理第 {i} 部电影时出错: {str(e)}")
            # 保存错误页面用于调试
            with open(f'error_page_{i}.html', 'w', encoding='gbk') as f:
                f.write(child_resp.text)

    print(f"抓取完成！结果已保存到 movie_info.csv")
