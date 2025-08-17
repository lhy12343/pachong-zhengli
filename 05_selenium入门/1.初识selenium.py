# selenum是一个开源的自动化测试工具，它可以用来测试浏览器、移动端、桌面端的应用。
# 输入网址，
# 能从页面里提取东西
# 先确定打开的是哪个浏览器 -》 chrome、firefox、safari、IE
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

# 创建浏览器对象（使用你提供的 chromedriver 绝对路径，且在脚本结束后不关闭浏览器）
service = Service(executable_path=r"C:\\Users\\Administrator\\Desktop\\pachong\\chromedriver.exe")
options = Options()
options.add_experimental_option("detach", True)
web = webdriver.Chrome(service=service, options=options)

url = 'https://www.baidu.com'

# 打开网址
web.get(url)

# 获取网站的标题
print(web.title)