import scrapy


class XiaoSpider(scrapy.Spider):
    name = "xiao"  # 爬虫名称
    allowed_domains = ["4399.com"]  # 允许爬取的域名
    start_urls = ["https://www.4399.com/flash/"]  # 起始URL

    def parse(self, response):  # 解析函数
        # 分块提取数据
        li_list = response.xpath('//ul[@class="n-game cf"]/li')
        for li in li_list:
            name = li.xpath('./a/b/text()').extract_first()  # 提取一项内容
            category = li.xpath('./em/a/text()').extract_first()
            date = li.xpath('./em/text()').extract_first()

            dic = {
                'name': name,
                'category': category,
                'date': date,
            }
            # 需要用yield将数据传递给pipeline（管道）
            yield dic  # 传递数据给pipeline
