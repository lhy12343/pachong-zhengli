# Scrapy settings for zhihu project
#
# For simplicity, this file contains only settings considered important or
# commonly used. You can find more settings consulting the documentation:
#
#     https://docs.scrapy.org/en/latest/topics/settings.html
#     https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
#     https://docs.scrapy.org/en/latest/topics/spider-middleware.html

BOT_NAME = "zhihu"

SPIDER_MODULES = ["zhihu.spiders"]
NEWSPIDER_MODULE = "zhihu.spiders"

LOG_LEVEL = "ERROR"  # 方案A：只显示错误，隐藏INFO/DEBUG等普通日志
# LOG_STDOUT = True

# 当控制台无法交互输入时，爬虫将回退使用此默认用户名（留空则仍会报错）
DEFAULT_ZHIHU_USERNAME = ""

ADDONS = {}

# Crawl responsibly by identifying yourself (and your website) on the user-agent
# USER_AGENT = "zhihu (+http://www.yourdomain.com)"

# Obey robots.txt rules
ROBOTSTXT_OBEY = False

# Concurrency and throttling settings
# CONCURRENT_REQUESTS = 16
CONCURRENT_REQUESTS_PER_DOMAIN = 1
DOWNLOAD_DELAY = 0.5
REDIRECT_ENABLED = False  # 禁用自动重定向，便于观察302/401/403等

# Disable cookies (enabled by default)
COOKIES_ENABLED = False  # 使用抓包Cookie，不让CookiesMiddleware干预

# Disable Telnet Console (enabled by default)
# TELNETCONSOLE_ENABLED = False

# Override the default request headers:
DEFAULT_REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Mobile Safari/537.36 Edg/140.0.0.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Sec-Ch-Ua": '"Chromium";v="140", "Not=A?Brand";v="24", "Microsoft Edge";v="140"',
    "Sec-Ch-Ua-Mobile": "?1",
    "Sec-Ch-Ua-Platform": '"Android"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Referer": "https://www.zhihu.com/",
    # 使用最新的Cookie（已更新）
    "Cookie": "_xsrf=esBbzKJYADaevrNVPcXce9ur4iJz6gPj; _zap=b7352cc3-2419-414f-a3e9-32142b8b1438; d_c0=HbbTaVMi8hqPTjzebW6BkE8hWRhqOCGlhZ4=|1755705942; captcha_session_v2=2|1:0|10:1755789474|18:captcha_session_v2|88:VXkzNW5rWHQwMlFpVTFsQVgrUHVPdVNrWDk0QTZ2a2JpUFFBQWtheFQwSERJR2RjVTVYVFJMN0RmRnVEODY3Tw==|114a81169566f4cdae8780bc82af49ddc24240a9469decae9fd7b0bdb5da636a; __snaker__id=lYhU4L9tAskVO6af; gdxidpyhxdE=P3k7DWuJAX8pyhpNJYg56RMnQ4qVdYE9offByzp0uV%2BWJtwCZSLQqEVGH6xJNJ9tH9AAvv%5CDUNRTZ%2BloTmDsQcYM8rn%2BqQYiuLnb%2B1jK%5CnprDj%2BfL%5C2egIZIfP%2BBK0X20Mi3k2KBn9sGen15LWCG%2Fnx%5C304y%5CDftL7kXssk2xf4klzHr%3A1755790449887; q_c1=dd8ea21d1583459398933d667f7ef1ac|1755789480000|1755789480000; z_c0=2|1:0|10:1756363471|4:z_c0|92:Mi4xLU1Tb0RnQUFBQUFkdHROcFV5THlHaGNBQUFCZ0FsVk5xSWFVYVFCaVRNcVRlZUt0eUJRakUxeldPTGZtdi1XT2dn|386d5d7082b30474558b09b097cbe9c124989f95e7aa91a4f9db737860870276; Hm_lvt_98beee57fd2ef70ccdd5ca52b9740c49=1756363546,1756563158,1756786417,1757735268; HMACCOUNT=BFEB8DCA30BB0151; __zse_ck=004_iFL0sHKZTEHifwksQv=tbQoAtcn38km5tFcQeRfhWf9pnrFy9xxfdZ1ske3AMafCqeJ45KO9IViyWOhuJCxDc3y8Z2lN40Yb9vbgLC79F6fgkTJ9EhYeZUb98vllvI8a-+b/EZ0aPmNNW0IZpNPJaLqk5mbx3/UOR464SMlevHFEG9NjLkIlvSmJbAjpwK8qztpt+cHDc/4LpSONIHGP7cP70LNLlgCir5ghQHfEZLP4qUdIzEIZeqY4gPgQ26S72; tst=r; SESSIONID=BbLkf6YMrgfM1YUXd2uakbcm4Jz3FiwDphpAkDd12rA; JOID=V1oQB0Iu8sg8-M1GTq4JW5ig7r9Ua5eFWpL8GAJQkqlwxJgUEYYYAFXzzUBClWPZDlG8ffZ_IWWrKTjYqUfEUkI=; osd=VloRAUMv8sk6-cxGT6gIWpih6L5Va5aDW5P8GQRRk6lxwpkVEYceAVTzzEZDlGPYCFC9ffd5IGSrKD7ZqEfFVEM=; BEC=6c53268835aec2199978cd4b4f988f8c; Hm_lpvt_98beee57fd2ef70ccdd5ca52b9740c49=1757736673",
}

# Enable or disable spider middlewares
# See https://docs.scrapy.org/en/latest/topics/spider-middleware.html
# 方案B：在 SpiderMiddleware 中完成 __NEXT_DATA__ 解析与字段映射，产出 response.meta['user_obj']
SPIDER_MIDDLEWARES = {
    "zhihu.middlewares.ZhihuSpiderMiddleware": 543,
}

# Enable or disable downloader middlewares
# See https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
# 预留位：如需统一加请求头/代理/重试，可在此启用。
DOWNLOADER_MIDDLEWARES = {
    "zhihu.middlewares.ZhihuDownloaderMiddleware": 543,
}

# Enable or disable extensions
# See https://docs.scrapy.org/en/latest/topics/extensions.html
# EXTENSIONS = {
#    "scrapy.extensions.telnet.TelnetConsole": None,
# }

# Configure item pipelines
# See https://docs.scrapy.org/en/latest/topics/item-pipeline.html
ITEM_PIPELINES = {
    "zhihu.pipelines.ZhihuPipeline": 300,
    "zhihu.pipelines.UserDetailFilePipeline": 400,
}

# 用户详情数据输出文件路径
USER_DETAIL_OUTPUT_FILE = r'C:\Users\Administrator\Desktop\pachong\06_scrapy框架\zhihu\知乎详情用户数据.txt'

# Enable and configure the AutoThrottle extension (disabled by default)
# See https://docs.scrapy.org/en/latest/topics/autothrottle.html
AUTOTHROTTLE_ENABLED = True
# The initial download delay
AUTOTHROTTLE_START_DELAY = 1  # 开始延迟
# The maximum download delay to be set in case of high latencies
AUTOTHROTTLE_MAX_DELAY = 10  # 最大延迟
# The average number of requests Scrapy should be sending in parallel to
# each remote server
AUTOTHROTTLE_TARGET_CONCURRENCY = 5.0  # 目标并发数
# Enable showing throttling stats for every response received:
# AUTOTHROTTLE_DEBUG = False

# Enable and configure HTTP caching (disabled by default)
# See https://docs.scrapy.org/en/latest/topics/downloader-middleware.html#httpcache-middleware-settings
HTTPCACHE_ENABLED = True
HTTPCACHE_POLICY = 'scrapy.extensions.httpcache.DummyPolicy'
# HTTPCACHE_EXPIRATION_SECS = 0
# HTTPCACHE_DIR = "httpcache"
HTTPCACHE_IGNORE_HTTP_CODES = [403, 302, 401]
# HTTPCACHE_STORAGE = "scrapy.extensions.httpcache.FilesystemCacheStorage"

# Set settings whose default value is deprecated to a future-proof value
FEED_EXPORT_ENCODING = "utf-8"
