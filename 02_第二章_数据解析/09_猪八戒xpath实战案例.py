# 文档注释：说明脚本的基本信息
"""
时间：2025/7/10  16:16
目标：绕过猪八戒滑块验证码并爬取SAAS服务数据
优化：修复多窗口问题 + 自动刷新机制 + 增强稳定性
"""

# 导入必要的库
import time  # 用于添加时间延迟
from selenium import webdriver  # 自动化浏览器操作
from selenium.webdriver.common.by import By  # 元素定位方式
from selenium.webdriver.support.ui import WebDriverWait  # 显式等待
from selenium.webdriver.support import expected_conditions as EC  # 等待条件
from lxml import etree  # HTML解析库

# 配置Chrome浏览器选项（反反爬关键）
options = webdriver.ChromeOptions()  # 创建Chrome选项对象
# 添加各种反反爬参数
options.add_argument("--disable-blink-features=AutomationControlled")  # 禁用自动化控制特征
options.add_argument("--disable-popup-blocking")  # 禁用弹窗拦截
options.add_argument("--disable-extensions")  # 禁用扩展程序
options.add_argument("--disable-infobars")  # 禁用信息栏
options.add_argument("--disable-notifications")  # 禁用通知
options.add_argument("--disable-web-security")  # 禁用Web安全
options.add_argument("--no-sandbox")  # 禁用沙箱
options.add_argument("--disable-gpu")  # 禁用GPU加速
options.add_argument("--disable-dev-shm-usage")  # 禁用/dev/shm使用
options.add_argument("--ignore-certificate-errors")  # 忽略证书错误
options.add_argument("--disable-bundled-ppapi-flash")  # 禁用Flash
options.add_argument("--mute-audio")  # 静音
options.add_argument("--disable-logging")  # 禁用日志
options.add_argument("--log-level=3")  # 设置日志级别
options.add_argument("--disable-software-rasterizer")  # 禁用软件光栅化
# 设置用户代理，模拟真实浏览器
options.add_argument(
    "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36")

# 启动浏览器
driver = webdriver.Chrome(options=options)  # 使用配置的选项启动Chrome
driver.maximize_window()  # 最大化窗口，确保页面元素可见

# 记录主窗口句柄（用于窗口管理）
main_window = None  # 初始化主窗口句柄变量


# 定义窗口管理函数
def close_extra_windows():
    """关闭所有非主窗口并返回主窗口"""
    global main_window  # 声明使用全局变量main_window

    # 如果没有主窗口，设置第一个窗口为主窗口
    if main_window is None and driver.window_handles:  # 检查窗口句柄存在
        main_window = driver.window_handles[0]  # 将第一个窗口设为main_window

    if main_window is None:  # 如果没有主窗口
        return  # 直接返回

    # 关闭所有非主窗口
    for handle in driver.window_handles:  # 遍历所有窗口句柄
        if handle != main_window:  # 如果是非主窗口
            driver.switch_to.window(handle)  # 切换到该窗口
            driver.close()  # 关闭窗口

    # 切换回主窗口
    driver.switch_to.window(main_window)  # 切换回主窗口
    return main_window  # 返回主窗口句柄


# 访问目标页面
target_url = 'https://www.zbj.com/fw/?k=saas'  # 目标URL
print(f"访问目标页面: {target_url}")  # 打印访问信息
driver.get(target_url)  # 打开目标页面

# 初始关闭多余窗口
close_extra_windows()  # 调用函数关闭多余窗口


# 1. 添加自动刷新机制解决滑块显示问题
def check_and_refresh():
    """检查滑块是否存在，不存在则刷新页面"""
    try:
        # 快速检查滑块是否存在（0.5秒内）
        WebDriverWait(driver, 0.5).until(
            EC.presence_of_element_located((By.CLASS_NAME, "ver_box")))
        print("检测到滑块验证框")
        return True
    except:
        # 滑块不存在，刷新页面
        print("滑块未显示，自动刷新页面...")
        driver.refresh()
        close_extra_windows()  # 刷新后关闭可能弹出的新窗口
        time.sleep(2)  # 等待刷新完成
        return False


# 尝试最多3次刷新
max_refresh_attempts = 3
refresh_count = 0
slider_detected = False

while refresh_count < max_refresh_attempts and not slider_detected:
    slider_detected = check_and_refresh()
    refresh_count += 1
    if not slider_detected:
        print(f"刷新后仍未显示滑块，尝试次数: {refresh_count}/{max_refresh_attempts}")

# 2. 修改滑块验证等待逻辑 - 修复缩进错误并优化逻辑
try:
    if slider_detected:
        print("检测到滑块验证，请手动完成验证...")
        # 确保滑块在可视区域（通过JavaScript滚动）
        slider = driver.find_element(By.CLASS_NAME, "ver_box")
        driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", slider)
    else:
        # 如果自动刷新失败，尝试显式等待滑块
        print("尝试最终等待滑块验证...")
        try:
            slider = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "ver_box")))
            print("检测到滑块验证，请手动完成验证...")
            slider_detected = True
            # 确保滑块在可视区域
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", slider)
        except:
            print("未检测到滑块验证，继续执行...")
            slider_detected = False

    if slider_detected:
        # 简化用户交互：等待用户手动完成验证
        print("请手动完成滑块验证...")
        print("完成后请按回车键继续...")
        input("按回车键继续 >>> ")  # 等待用户确认完成

        # 验证后检查滑块是否消失
        if driver.find_elements(By.CLASS_NAME, "ver_box"):
            print("警告：滑块验证似乎未完成！")
        else:
            print("滑块验证已完成")

except Exception as e:  # 捕获滑块检测异常
    print(f"滑块检测异常: {e}")
    print("未检测到滑块验证，继续执行...")

# 确保在主窗口（验证后再次确认）
close_extra_windows()  # 关闭可能出现的多余窗口

# 等待页面加载完成
print("等待页面加载...")
time.sleep(3)  # 等待3秒确保页面加载

# 获取页面源码
html = driver.page_source  # 获取当前页面的HTML源码

# 解析HTML数据
et = etree.HTML(html)  # 创建lxml解析器对象

# 定位商品容器（使用XPath）
# 查找包含"search-result-list-service"类的div下的所有div子元素
divs = et.xpath('//div[contains(@class, "search-result-list-service")]/div')

# 创建CSV文件保存结果
with open("猪八戒SAAS服务数据.csv", "w", encoding="utf-8-sig") as f:  # 使用utf-8-sig解决Excel中文乱码
    f.write("商品价格,商品名称,企业名称\n")  # 写入CSV表头

    if not divs:  # 如果没有找到商品元素
        print("未找到商品数据")  # 提示未找到数据
        # 保存页面用于调试
        with open("zbj_debug.html", "w", encoding="utf-8") as debug_file:
            debug_file.write(html)  # 保存HTML源码
        print("已保存页面到 zbj_debug.html 用于调试")  # 提示保存调试文件
    else:  # 找到商品元素
        print(f"找到 {len(divs)} 个商品")  # 打印商品数量

        # 遍历每个商品元素
        for i, div in enumerate(divs, 1):  # 从1开始计数
            try:
                # 提取价格数据
                price_list = div.xpath('.//div[@class="bot-content"]/div/span/text()')  # XPath定位价格
                price = price_list[0].strip() if price_list else "价格未知"  # 处理空值

                # 提取商品名称
                commodity_list = div.xpath('.//div[@class="bot-content"]/div[@class="name-pic-box"]/div/span/text()')
                commodity = commodity_list[0].strip() if commodity_list else "名称未知"

                # 提取企业名称
                enterprise_list = div.xpath('.//div[@class="name-address"]/div/div/div/text()')
                enterprise = enterprise_list[0].strip() if enterprise_list else "企业未知"

                # 构建数据行
                data = f"{price},{commodity},{enterprise}"  # 格式化为CSV行

                # 打印到控制台
                print(f"{i}. {data}")  # 显示带序号的数据

                # 写入CSV文件
                f.write(data + "\n")  # 写入一行数据

            except Exception as e:  # 捕获单条数据处理异常
                print(f"处理第 {i} 个商品时出错: {e}")  # 打印错误信息
                # 写入错误标记行
                f.write(f"错误数据,错误数据,错误数据\n")

# 关闭浏览器
driver.quit()  # 退出浏览器
print("\n爬取完成！结果已保存到 猪八戒SAAS服务数据.csv")  # 最终完成提示
