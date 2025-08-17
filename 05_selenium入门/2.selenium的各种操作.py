"""
时间：2025/8/11  12:03
"""
import time
import sys

# 目标：拉钩网的招聘信息
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from urllib.parse import urljoin

# ---------------------- 辅助：窗口管理与登录控制 ----------------------
already_logged_in = False

def _safe_current_url(driver):
    try:
        return driver.current_url or ''
    except Exception:
        return ''

def switch_to_window_containing(driver, url_substring: str) -> bool:
    for handle in driver.window_handles:
        driver.switch_to.window(handle)
        if url_substring in _safe_current_url(driver):
            return True
    return False

def switch_to_main_site_window(driver) -> bool:
    for handle in driver.window_handles:
        driver.switch_to.window(handle)
        url_now = _safe_current_url(driver)
        if 'lagou.com' in url_now and 'passport' not in url_now:
            return True
    return False

def close_login_windows(driver):
    # 关闭所有登录页窗口（passport.lagou.com），但保留至少一个窗口
    for handle in list(driver.window_handles):
        if len(driver.window_handles) <= 1:
            break
        driver.switch_to.window(handle)
        if 'passport.lagou.com' in _safe_current_url(driver):
            try:
                driver.close()
            except Exception:
                pass
    # 切回最后一个窗口
    try:
        driver.switch_to.window(driver.window_handles[-1])
    except Exception:
        pass

def find_first_job_block(driver, max_wait_seconds: int = 12):
    candidates = [
        (By.XPATH, '//*[@id="jobList"]/div[1]'),
        (By.XPATH, '//*[@id="jobList"]//*[self::div or self::li][1]'),
        (By.XPATH, '//*[@id="s_position_list"]//ul/li[1]'),
        (By.XPATH, '//*[contains(@class,"s_position_list")]//ul/li[1]'),
        (By.XPATH, '//*[contains(@class,"job-list")]//*[self::div or self::li][1]'),
        (By.XPATH, '//*[contains(@class,"position-card")][1]'),
        (By.CSS_SELECTOR, '#jobList > div:first-child'),
        (By.CSS_SELECTOR, '#s_position_list ul > li:first-child'),
        (By.CSS_SELECTOR, '.job-list .list-item, .job-list li, .position-card, .position-card-content'),
    ]
    local_wait = WebDriverWait(driver, max_wait_seconds)
    for by, locator in candidates:
        try:
            elem = local_wait.until(EC.presence_of_element_located((by, locator)))
            if elem:
                return elem
        except Exception:
            continue
    return None

def trigger_search_submission(driver, wait: WebDriverWait, search_input_element=None):
    """优先点击搜索按钮；若未找到，则回车提交。并处理可能弹出的登录窗口。"""
    old_handles = list(driver.window_handles)
    locators_to_try = [
        (By.ID, 'search_button'),
        (By.XPATH, '//*[@id="search_button"]'),
        (By.XPATH, '//button[@id="search_button"]'),
        (By.CSS_SELECTOR, 'button.search-btn, button.search, .search-btn'),
        (By.XPATH, '//form[contains(@class,"search") or @id="searchForm"]//button[@type="submit" or contains(@class,"search")]'),
        (By.XPATH, '//div[contains(@class,"search")]/button'),
    ]

    clicked = False
    for locator in locators_to_try:
        try:
            btn = wait.until(EC.element_to_be_clickable(locator))
            btn.click()
            clicked = True
            break
        except Exception:
            continue

    if not clicked:
        try:
            if search_input_element is not None:
                search_input_element.send_keys(Keys.ENTER)
            else:
                driver.switch_to.active_element.send_keys(Keys.ENTER)
        except Exception:
            pass

    # 如果出现新窗口（通常是登录页），切过去方便后续登录
    try:
        WebDriverWait(driver, 5).until(
            lambda d: len(d.window_handles) >= len(old_handles)
        )
    except Exception:
        pass
    switch_to_window_containing(driver, 'passport.lagou.com')

# 创建浏览器对象（使用你提供的 chromedriver 绝对路径，且在脚本结束后不关闭浏览器）
service = Service(executable_path=r"C:\\Users\\Administrator\\Desktop\\pachong\\chromedriver.exe")
options = Options()
options.add_experimental_option("detach", True)
# 反自动化痕迹设置
options.add_experimental_option('excludeSwitches', ['enable-automation'])
options.add_experimental_option('useAutomationExtension', False)
options.add_argument('--disable-blink-features=AutomationControlled')
options.add_argument('--lang=zh-CN,zh;q=0.9,en;q=0.8')
options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36 Edg/139.0.0.0')
web = webdriver.Chrome(service=service, options=options)
try:
    web.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
        'source': 'Object.defineProperty(navigator, "webdriver", {get: () => undefined});'
    })
    web.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
        'source': 'window.chrome = { runtime: {} };'
    })
    web.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
        'source': 'Object.defineProperty(navigator, "languages", {get: () => ["zh-CN","zh","en"]});'
    })
    web.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
        'source': 'Object.defineProperty(navigator, "plugins", {get: () => [1, 2, 3, 4, 5]});'
    })
except Exception:
    pass

url = 'https://www.lagou.com'

# ------------- 直接跳转目标页 + 附加登录后所需请求头与 Cookie -------------
TRY_DIRECT_JUMP = True
if TRY_DIRECT_JUMP:
    TARGET_URL = 'https://www.lagou.com/wn/zhaopin?fromSearch=true&kd=python&city=%E5%85%A8%E5%9B%BD'
    # 你的登录后 Cookie（来自浏览器）。如需更新，替换下方字符串。
    COOKIE_STRING = (
        'sajssdk_2015_cross_new_user=1; '
        'sensorsdata2015session=%7B%7D; '
        'gate_login_token=v1####4ab49115d211c6bc4ce23e588c18288caa181722cab423ef5cfda969d10a2f52; '
        'LG_LOGIN_USER_ID=v1####d71b031084deb2582ffd2591956a3497269a7f5eb84e736949d0e16dc8ec3366; '
        'LG_HAS_LOGIN=1; '
        '_putrc=F9A21CD5FE76D1CE123F89F2B170EADC; '
        'login=true; '
        'unick=%E6%9D%8E%E9%B8%BF%E9%98%B3; '
        'privacyPolicyPopup=false; '
        'X_HTTP_TOKEN=42daf4b72327b2812842984571bf5e71415983ed09; '
        '__PWD_STRENGTH_CHECK__27821924=1; '
        'sensorsdata2015jssdkcross=%7B%22distinct_id%22%3A%2219897bedbec27b3-0e640779e3dc0b8-4c657b58-2359296-19897bedbed2cc0%22%2C%22first_id%22%3A%22%22%2C%22props%22%3A%7B%22%24latest_traffic_source_type%22%3A%22%E7%9B%B4%E6%8E%A5%E6%B5%81%E9%87%8F%22%2C%22%24latest_search_keyword%22%3A%22%E6%9C%AA%E5%8F%96%E5%88%B0%E5%80%BC_%E7%9B%B4%E6%8E%A5%E6%89%93%E5%BC%80%22%2C%22%24latest_referrer%22%3A%22%22%2C%22%24os%22%3A%22Windows%22%2C%22%24browser%22%3A%22Chrome%22%2C%22%24browser_version%22%3A%22139.0.0.0%22%7D%2C%22%24device_id%22%3A%2219897bedbec27b3-0e640779e3dc0b8-4c657b58-2359296-19897bedbed2cc0%22%7D'
    )

    EXTRA_HEADERS = {
        # 仅设置登录相关自定义头，避免影响页面导航 Accept/Referer 等默认头
        'X-K-HEADER': 'Nx0XWBiPTl7BsvWcq6BDSGEHpiIh1RboP+ouzQiFtDwKGToELAcCK2ywfY3LHke3',
        'X-S-HEADER': 'PspGNKVen9RY72rni4NGuWEuq1HHnS8glIFVl9rDkOoA4+hp+WwzVjsDId5wJrYXeiYFXkCeVWAVdXFsfsDXfu+bY4H0+l+nX49czXbw7aG+T+0WzI4S1aV1sLjPCowiLqBu7buMW2YqQQRxndBWyg==',
        'X-SS-REQ-HEADER': '{"secret":"Nx0XWBiPTl7BsvWcq6BDSGEHpiIh1RboP+ouzQiFtDwKGToELAcCK2ywfY3LHke3"}',
        'X-L-REQ-HEADER': '{"appVersion":"0","deviceType": 1,"reqVersion":0}',
    }

    # 启用 CDP 网络并设置额外请求头
    try:
        web.execute_cdp_cmd('Network.enable', {})
        web.execute_cdp_cmd('Network.setExtraHTTPHeaders', { 'headers': EXTRA_HEADERS })
    except Exception:
        pass

    # 先打开主域，写入 Cookie
    try:
        web.get('https://www.lagou.com')
        # 写 cookie 前必须处于同域页面
        for pair in [p.strip() for p in COOKIE_STRING.split(';') if p.strip()]:
            if '=' not in pair:
                continue
            name, value = pair.split('=', 1)
            name = name.strip()
            value = value.strip()
            if not name:
                continue
            try:
                web.add_cookie({ 'name': name, 'value': value, 'domain': '.lagou.com', 'path': '/' })
            except Exception:
                # 某些 cookie 可能被浏览器拒绝，忽略
                pass
    except Exception:
        pass

    # 跳转目标检索页
    web.get(TARGET_URL)

    # 简单容错：若出现“网络出错啦”或 "An unexpected error has occurred.", 尝试刷新并重载一次
    try:
        page_html = web.page_source
        if '网络出错啦' in page_html or 'An unexpected error has occurred' in page_html:
            time.sleep(1)
            web.refresh()
            time.sleep(1)
            if '网络出错啦' in web.page_source or 'An unexpected error has occurred' in web.page_source:
                web.get(TARGET_URL)
    except Exception:
        pass

    # 进一步容错：如仍异常，移除自定义请求头再重载一次
    try:
        page_html = web.page_source
        if '网络出错啦' in page_html or 'An unexpected error has occurred' in page_html:
            try:
                web.execute_cdp_cmd('Network.setExtraHTTPHeaders', { 'headers': {} })
            except Exception:
                pass
            web.get(TARGET_URL)
    except Exception:
        pass

    # 等待并抓取所需数据块（你给定的 XPath + 兜底）
    try:
        # 目标 XPath
        target_xpath = '//*[@id="jobsContainer"]/div[2]/div[3]'

        def try_scroll_then_find(max_wait=12):
            try:
                elem = WebDriverWait(web, max_wait).until(
                    EC.presence_of_element_located((By.XPATH, target_xpath))
                )
                return elem
            except Exception:
                try:
                    web.execute_script('arguments[0].scrollIntoView({behavior:"auto",block:"center"});',
                                       web.find_element(By.XPATH, '//*[@id="jobsContainer"]'))
                except Exception:
                    try:
                        web.execute_script('window.scrollTo(0, document.body.scrollHeight/2);')
                    except Exception:
                        pass
                time.sleep(0.8)
                try:
                    return WebDriverWait(web, max_wait).until(
                        EC.presence_of_element_located((By.XPATH, target_xpath))
                    )
                except Exception:
                    return None

        target_elem = try_scroll_then_find(max_wait=12)

        if target_elem is None:
            # 兜底方案：刷新后再次尝试
            web.refresh()
            time.sleep(1)
            target_elem = try_scroll_then_find(max_wait=12)

        if target_elem is not None:
            print(target_elem.text)
        else:
            print('未定位到指定 XPath 元素：//*[@id="jobsContainer"]/div[2]/div[3]')
    except Exception as e:
        print('抓取失败：', e)

    # 采集列表中前 15 个职位详情页，提取 //*[@id="job_detail"]
    try:
        # 尝试滚动以加载更多卡片
        try:
            web.execute_script('window.scrollTo(0, document.body.scrollHeight*0.6);')
            time.sleep(0.6)
            web.execute_script('window.scrollTo(0, document.body.scrollHeight*0.95);')
            time.sleep(0.6)
            web.execute_script('window.scrollTo(0, 0);')
        except Exception:
            pass

        # 按行优先、列次序（每行 div[1] 再 div[2]）收集职位链接，确保顺序为：
        # 第一个：//*[@id="jobList"]/div[1]/div[1] → 第二个：//*[@id="jobList"]/div[1]/div[2] → 依此类推
        seen = set()
        job_hrefs = []
        try:
            rows = web.find_elements(By.XPATH, '//*[@id="jobList"]/div')
        except Exception:
            rows = []
        for row_index in range(1, len(rows) + 1):
            for col_index in (1, 2):
                try:
                    a_in_cell = web.find_element(
                        By.XPATH,
                        f'//*[@id="jobList"]/div[{row_index}]/div[{col_index}]//a[contains(@href, "/wn/jobs/")]'
                    )
                    href = a_in_cell.get_attribute('href')
                    if not href:
                        continue
                    if href.startswith('/'):
                        href = urljoin('https://www.lagou.com', href)
                    if '/wn/jobs/' in href and href not in seen:
                        seen.add(href)
                        job_hrefs.append(href)
                except Exception:
                    continue

        # 兜底：如上述按行列未取到，则退回全局扫描
        if not job_hrefs:
            try:
                link_elems = web.find_elements(By.XPATH, '//*[@id="jobList"]//a[contains(@href, "/wn/jobs/")]')
            except Exception:
                link_elems = []
            for a in link_elems:
                try:
                    href = a.get_attribute('href')
                    if not href:
                        continue
                    if href.startswith('/'):
                        href = urljoin('https://www.lagou.com', href)
                    if '/wn/jobs/' in href and href not in seen:
                        seen.add(href)
                        job_hrefs.append(href)
                except Exception:
                    continue

        main_handle = web.current_window_handle

        # 并发近似：先批量打开新标签页（网络并发加载），再逐个切换提取
        max_total = min(15, len(job_hrefs))
        opened_handles = []
        known_handles = set(web.window_handles)
        for href in job_hrefs[:max_total]:
            try:
                web.execute_script('window.open(arguments[0], "_blank");', href)
                WebDriverWait(web, 8).until(
                    lambda d, kh=known_handles: len([h for h in d.window_handles if h not in kh]) >= 1
                )
                # 记录新打开的那个句柄
                new_handles = [h for h in web.window_handles if h not in known_handles]
                if new_handles:
                    opened_handles.append(new_handles[-1])
                    known_handles.update(new_handles)
                time.sleep(0.1)
            except Exception:
                continue

        def extract_job_detail_from_current_tab() -> str:
            # 处理可能的错误页，最多两轮
            for _ in range(2):
                try:
                    elem = WebDriverWait(web, 15).until(
                        EC.presence_of_element_located((By.XPATH, '//*[@id="job_detail"]'))
                    )
                    if elem:
                        return elem.text
                except Exception:
                    pass
                try:
                    if '网络出错啦' in web.page_source or 'An unexpected error has occurred' in web.page_source:
                        web.refresh()
                        time.sleep(1)
                except Exception:
                    pass
            try:
                elem2 = web.find_element(By.XPATH, '//*[@id="job_detail"]')
                return elem2.text
            except Exception:
                return ''

        for idx, handle in enumerate(opened_handles, start=1):
            try:
                web.switch_to.window(handle)
            except Exception:
                continue
            try:
                detail_text = extract_job_detail_from_current_tab()
                if detail_text:
                    print(f'===== 详情 {idx}/{len(opened_handles)} =====')
                    print(detail_text)
                else:
                    print(f'===== 详情 {idx}/{len(opened_handles)} 抓取失败（无内容） =====')
            except Exception as e:
                print(f'===== 详情 {idx}/{len(opened_handles)} 抓取异常：{e} =====')
            finally:
                # 关闭详情标签并回到主标签
                try:
                    if len(web.window_handles) > 1:
                        web.close()
                        web.switch_to.window(main_handle)
                except Exception:
                    try:
                        web.switch_to.window(main_handle)
                    except Exception:
                        pass
    except Exception as e:
        print('批量详情抓取出错：', e)

    # 完成后直接结束脚本（不关闭浏览器）
    sys.exit(0)

# 打开网址
web.get(url)

# 找到页面中的x，点击它（适配 Selenium 4 的写法，并加入显式等待）
wait = WebDriverWait(web, 10)
try:
    x_btn = wait.until(
        EC.presence_of_element_located(
            (By.XPATH, '/html/body/div[3]/div/div[2]/div/div[2]/button/span/i')
        )
    )
    x_btn.click()
except Exception:
    # 如果没有这个弹窗或定位失败，则忽略
    pass

# 找到输入框，输入关键字
# 休息一下
try:
    search_input = wait.until(
        EC.presence_of_element_located((By.XPATH, '//*[@id="search_input"]'))
    )
    old_handles = list(web.window_handles)
    search_input.send_keys('python')
    # 提交搜索（优先点击按钮，其次回车）
    trigger_search_submission(web, wait, search_input)
except Exception:
    pass


# 数据提取阶段
# 登录页（如出现）——输入手机号与密码并登录（仅尝试一次）
try:
    if not already_logged_in and switch_to_window_containing(web, 'passport.lagou.com'):
        phone_input = wait.until(
            EC.presence_of_element_located(
                (By.XPATH, '//*[@id="lg-passport-box"]/div/div[2]/div/div[2]/div/div[1]/div[1]/input')
            )
        )
        phone_input.clear()
        phone_input.send_keys('18228224375')

        pwd_input = wait.until(
            EC.presence_of_element_located(
                (By.XPATH, '//*[@id="lg-passport-box"]/div/div[2]/div/div[2]/div/div[1]/div[2]/input')
            )
        )
        pwd_input.clear()
        pwd_input.send_keys('Lhy2420087414..')

        login_btn = wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, '//*[@id="lg-passport-box"]/div/div[2]/div/div[3]/button')
            )
        )
        login_btn.click()
        already_logged_in = True
except Exception:
    # 如果当前没有出现登录框，则忽略
    pass

# 等待你手动完成图形验证（最长 180 秒）
long_wait = WebDriverWait(web, 180)
try:
    # 等待直到出现任意一个可用页面：主站搜索框或职位列表
    long_wait.until(
        lambda d: switch_to_main_site_window(d) or switch_to_window_containing(d, 'www.lagou.com')
    )
except Exception:
    pass

# 关闭多余的登录页窗口，并确保回到主站
try:
    close_login_windows(web)
    if not switch_to_main_site_window(web):
        web.get('https://www.lagou.com')
except Exception:
    pass

# 重新搜索 python 并回车（避免重复输入，仅在必要时设置为 python）
try:
    search_input2 = wait.until(
        EC.presence_of_element_located((By.XPATH, '//*[@id="search_input"]'))
    )
    # 如果已有值且就是 python，则不再重复输入；如果为空或不是 python（例如 pythonpython），则重置为 python
    current_value = ''
    try:
        current_value = (search_input2.get_attribute('value') or '').strip().lower()
    except Exception:
        current_value = ''

    if current_value != 'python':
        try:
            search_input2.clear()
        except Exception:
            # 使用 Ctrl+A + Delete 强制清空
            try:
                search_input2.send_keys(Keys.CONTROL, 'a')
                search_input2.send_keys(Keys.DELETE)
            except Exception:
                pass
        search_input2.send_keys('python')

    # 提交搜索（优先点击按钮，其次回车），并处理可能的登录弹窗
    trigger_search_submission(web, wait, search_input2)
    # 关闭多余登录窗口并切回主站
    close_login_windows(web)
    switch_to_main_site_window(web)
except Exception:
    pass

# 抓取职位列表首个区块并打印（增强版容错）
try:
    print('当前页面:', _safe_current_url(web))
    print('页面标题:', end=' ')
    try:
        print(web.title)
    except Exception:
        print('未知')

    job_first_block = find_first_job_block(web, max_wait_seconds=20)
    if job_first_block is None:
        # 回退到搜索结果页直链
        try:
            web.get('https://www.lagou.com/jobs/list_python')
            # 可能重定向到城市页，这里等到列表或搜索框
            WebDriverWait(web, 15).until(
                lambda d: find_first_job_block(d, max_wait_seconds=5) is not None or d.find_element(By.XPATH, '//*[@id="search_input"]')
            )
            job_first_block = find_first_job_block(web, max_wait_seconds=10)
        except Exception:
            job_first_block = None

    if job_first_block is not None:
        print(job_first_block.text)
    else:
        print('未定位到职位列表首项，可能未登录或页面结构变化。')
except Exception as e:
    print('抓取失败：', e)
