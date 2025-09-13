#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
直接启动 Scrapy 爬虫的脚本
无需使用终端命令行，直接运行此 Python 脚本即可启动爬虫
"""

import sys
import os
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

def run_spider(username=None):
    """运行知乎用户爬虫"""

    # 切换到项目目录
    project_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(project_dir)

    # 获取项目设置
    settings = get_project_settings()

    # 创建爬虫进程
    process = CrawlerProcess(settings)

    # 如果没有提供用户名，提示输入
    if not username:
        username = input("请输入要爬取的知乎用户昵称（如：luxenius）: ").strip()

    if not username:
        print("用户名不能为空！")
        return

    print(f"开始爬取用户: {username}")

    # 启动爬虫
    process.crawl('zhihupc', username=username)
    process.start()  # 这会阻塞直到爬虫完成

if __name__ == '__main__':
    # 支持命令行参数
    username = None
    if len(sys.argv) > 1:
        username = sys.argv[1]

    run_spider(username)