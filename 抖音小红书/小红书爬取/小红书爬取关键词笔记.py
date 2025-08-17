#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
小红书Selenium集成方案
结合Selenium登录状态保持 + API请求头获取 + 现有爬取逻辑
核心目标：只需登录一次，后续所有操作都保持登录状态
"""

import os
import time
import json
import requests
from urllib.parse import urlencode
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from typing import Dict, List, Any, Tuple
import urllib.parse
import sys
import warnings
import re
import threading
from collections import deque
from concurrent.futures import ThreadPoolExecutor, as_completed

# 禁用所有警告信息
warnings.filterwarnings("ignore")

# 禁用urllib3的SSL警告
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 移除针对 absl/voice 的特殊抑制逻辑，保留默认输出

class XHSIntegratedCrawler:
    """小红书集成爬虫：Selenium登录状态保持 + API请求"""
    
    def __init__(self):
        self.driver = None
        self.headers: Dict[str, str] = {}
        self.cookies: Dict[str, str] = {}
        self.last_signed_headers: Dict[str, str] = {}
        self.filter_signed_headers: Dict[str, str] = {}
        # 方案B：仅当命中 /search/filter 时，记录同源 search_id 与 keyword
        self.filter_search_id: str = ''
        self.filter_keyword: str = ''
        self.filter_captured_at: float = 0.0
        self.user_data_dir = os.path.join(os.getcwd(), "chrome_user_data")
        self.official_search_id = None
        self.cached_filter_groups: List[Dict[str, Any]] = []
        self._printed_search_id: bool = False
        
        # API相关配置
        self.search_url = "https://edith.xiaohongshu.com/api/sns/web/v1/search/notes"
        
        
    def _setup_browser(self):
        """配置并启动Chrome浏览器，保持登录状态"""
        chrome_options = Options()
        
        # 核心：设置用户数据目录，保存登录状态
        chrome_options.add_argument(f'--user-data-dir={self.user_data_dir}')
        chrome_options.add_argument('--profile-directory=Default')
        
        # 基本设置
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--disable-software-rasterizer')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-plugins')
        chrome_options.add_argument('--disable-images')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # 禁用各种日志和错误信息
        chrome_options.add_argument('--disable-logging')
        chrome_options.add_argument('--disable-log-file')
        chrome_options.add_argument('--log-level=3')  # 只显示致命错误
        chrome_options.add_argument('--silent')
        chrome_options.add_argument('--disable-background-networking')
        chrome_options.add_argument('--disable-background-timer-throttling')
        chrome_options.add_argument('--disable-backgrounding-occluded-windows')
        chrome_options.add_argument('--disable-renderer-backgrounding')
        chrome_options.add_argument('--disable-features=TranslateUI')
        chrome_options.add_argument('--disable-ipc-flooding-protection')
        chrome_options.add_argument('--disable-component-update')
        chrome_options.add_argument('--disable-default-apps')
        chrome_options.add_argument('--disable-domain-reliability')
        chrome_options.add_argument('--disable-features=VizDisplayCompositor')
        
        # 禁用DevTools和更多日志
        # 保持DevTools可用以稳定产生 *ExtraInfo 事件
        chrome_options.add_argument('--no-first-run')
        chrome_options.add_argument('--disable-infobars')
        # 不再禁用web security，避免影响凭证/策略
        chrome_options.add_argument('--disable-features=VizDisplayCompositor,AudioServiceOutOfProcess,VoiceTranscription')
        chrome_options.add_argument('--disable-speech-api')
        chrome_options.add_argument('--disable-background-mode')
        chrome_options.add_argument('--disable-background-downloads')
        chrome_options.add_argument('--disable-client-side-phishing-detection')
        chrome_options.add_argument('--disable-sync')
        chrome_options.add_argument('--disable-voice-input')
        chrome_options.add_argument('--disable-speech-synthesis-api')
        chrome_options.add_argument('--disable-media-session-api')
        
        # 启用性能日志以捕获网络请求
        chrome_options.add_experimental_option('perfLoggingPrefs', {
            'enableNetwork': True,
            'enablePage': False,
        })
        chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
        
        # 设置用户代理
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        try:
            # 指定chromedriver路径
            chromedriver_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "chromedriver.exe")
            if not os.path.exists(chromedriver_path):
                chromedriver_path = os.path.join(os.getcwd(), "chromedriver.exe")
            
            if os.path.exists(chromedriver_path):
                from selenium.webdriver.chrome.service import Service
                service = Service(chromedriver_path, log_path=os.devnull)
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
            else:
                self.driver = webdriver.Chrome(options=chrome_options)
            
            # 启用CDP网络/页面事件，确保可以捕获完整请求头（包含 ExtraInfo 事件）
            try:
                self.driver.execute_cdp_cmd('Network.enable', {
                    'maxTotalBufferSize': 10000000,
                    'maxResourceBufferSize': 10000000,
                    'includeExtraInfo': True  # 关键：确保能收到 *ExtraInfo 事件以获取完整请求头
                })
                self.driver.execute_cdp_cmd('Page.enable', {})
            except Exception:
                pass

            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            print("✅ Chrome浏览器启动成功")
            print(f"📁 用户数据目录: {self.user_data_dir}")
            return True
        
        except Exception as e:
            print(f"❌ 浏览器启动失败: {e}")
            return False
    
    def _ensure_login(self):
        """检查登录状态，如果未登录则引导登录"""
        try:
            # 导航到小红书首页
            print("🌐 检查登录状态...")
            self.driver.get("https://www.xiaohongshu.com")
            time.sleep(3)
            
            # 仅使用 UI 元素存在性作为登录判定：//*[@id="global"]/div[2]/div[1]/ul/div[1]/div[1]
            if self._is_logged_in_ui(timeout=3.0):
                print("✅ 检测到已有登录状态，无需重新登录")
                return True

            # 未检测到登录元素：提示登录并等待至检测通过
            print("ℹ️ 需要登录：请在浏览器中完成登录，完成后回到控制台继续")
            input("\n按回车键确认已完成登录...")

            # 轮询等待该元素出现
            for _ in range(60):  # 最多约30秒
                if self._is_logged_in_ui(timeout=0.5):
                    print("✅ 登录成功，会话已持久化至用户数据目录 chrome_user_data/")
                    return True
                time.sleep(0.5)

            # 兜底：刷新一次再短轮询
            try:
                self.driver.refresh()
            except Exception:
                pass
            time.sleep(1.0)
            for _ in range(20):
                if self._is_logged_in_ui(timeout=0.5):
                    print("✅ 登录成功，会话已持久化至用户数据目录 chrome_user_data/")
                    return True
                time.sleep(0.5)

            # 放行但提示
            print("⚠️ 仍未检测到登录元素，继续执行（若后续失败请完成登录后重试）")
            return True
        
        except Exception as e:
            print(f"❌ 登录检查失败: {e}")
            return False

    def _is_logged_in_ui(self, timeout: float = 2.0) -> bool:
        """根据新规则判断是否已登录：
        - 存在 XPath //*[@id='app']/div[1]/div/i => 未登录
        - 不存在该元素 => 已登录
        返回 True 表示“已登录”。
        """
        xpath_marker = '//*[@id="app"]/div[1]/div/i'
        try:
            # 使用短等待查找元素是否出现；出现则未登录
            elems = self.driver.find_elements(By.XPATH, xpath_marker)
            if elems and len(elems) > 0:
                return False  # 未登录
            # 若未立即找到，等待一小段时间再次确认
            end = time.time() + timeout
            while time.time() < end:
                elems = self.driver.find_elements(By.XPATH, xpath_marker)
                if elems and len(elems) > 0:
                    return False
                time.sleep(0.1)
            return True  # 超时仍未发现该元素，视为已登录
        except Exception:
            # 异常时保守返回 False（未登录），避免误放行
            return False
    
    def _perform_search_via_ui(self, keyword: str) -> bool:
        """在首页通过UI执行搜索，确保与站内流程一致（生成正确的search_id与签名绑定）。"""
        try:
            self.driver.get("https://www.xiaohongshu.com")
            time.sleep(1.2)

            # 常见输入框选择器集合，逐一尝试
            selectors = [
                "input[placeholder*='搜索']",
                "input[type='search']",
                "input[role='searchbox']",
                "input[name='keyword']",
            ]
            elem = None
            for css in selectors:
                try:
                    elem = WebDriverWait(self.driver, 3).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, css))
                    )
                    if elem:
                        break
                except Exception:
                    continue
            if not elem:
                # 退而求其次：用JS在页面内查找第一个input再尝试
                try:
                    elem = self.driver.execute_script("return document.querySelector('input,textarea')")
                except Exception:
                    elem = None
            if not elem:
                print("⚠️ 未找到搜索框，改为直接导航到搜索结果页")
                self.driver.get(f"https://www.xiaohongshu.com/search_result?keyword={urllib.parse.quote(keyword)}")
                time.sleep(1.2)
                return True

            try:
                elem.clear()
            except Exception:
                pass
            elem.send_keys(keyword)
            try:
                from selenium.webdriver.common.keys import Keys
                elem.send_keys(Keys.ENTER)
            except Exception:
                # 回退：点击搜索按钮
                try:
                    btn = self.driver.find_element(By.CSS_SELECTOR, "button, [role='button']")
                    btn.click()
                except Exception:
                    pass

            time.sleep(1.5)
            return True
        except Exception as e:
            print(f"⚠️ UI搜索触发失败: {e}")
            return False

    def _extract_headers_from_browser(self):
        """从浏览器中提取请求头和Cookie"""
        try:
            # 获取所有Cookie
            browser_cookies = self.driver.get_cookies()
            self.cookies = {cookie['name']: cookie['value'] for cookie in browser_cookies}
            
            # 获取真实UA
            try:
                real_ua = self.driver.execute_script("return navigator.userAgent") or ""
            except Exception:
                real_ua = ""
            if not real_ua:
                real_ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

            # 构建基础请求头（剔除动态签名头与伪首部）
            self.headers = {
                "accept": "application/json, text/plain, */*",
                "accept-encoding": "gzip, deflate, br, zstd",
                "accept-language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
                "cache-control": "no-cache",
                "content-type": "application/json;charset=UTF-8",
                "origin": "https://www.xiaohongshu.com",
                "pragma": "no-cache",
                "priority": "u=1, i",
                "referer": "https://www.xiaohongshu.com/",
                # 保留sec-*系列；具体值以浏览器为准，若需更精准可后续从CDP取
                "sec-ch-ua": '"Not;A=Brand";v="99", "Microsoft Edge";v="139", "Chromium";v="139"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"Windows"',
                "sec-fetch-dest": "empty",
                "sec-fetch-mode": "cors",
                "sec-fetch-site": "same-site",
                "user-agent": real_ua,
            }
            
            # 添加Cookie到请求头
            cookie_string = '; '.join([f"{name}={value}" for name, value in self.cookies.items()])
            self.headers['cookie'] = cookie_string
            
            print(f"✅ 成功提取 {len(self.cookies)} 个Cookie")
            return True
            
        except Exception as e:
            print(f"❌ 提取请求头失败: {e}")
            return False
    
    def _make_api_request(self, url, method='GET', data=None, params=None, override_headers: Dict[str, str] = None):
        """使用提取的请求头进行API请求"""
        try:
            # 让requests自动处理URL编码，不手动编码
            # 发送前安全过滤：剔除非法头
            safe_headers = {k: v for k, v in self.headers.items() if isinstance(k, str) and not k.strip().startswith(":")}
            
            # 合并最近捕获的签名头（白名单覆盖）
            try:
                if isinstance(self.last_signed_headers, dict) and self.last_signed_headers:
                    # 签名头白名单
                    signature_keys = ['x-s', 'x-t', 'x-s-common', 'x-b3-traceid', 'x-xray-traceid']
                    for k in signature_keys:
                        v = self.last_signed_headers.get(k)
                        if isinstance(v, str) and v:
                            if not k.strip().startswith(':'):
                                safe_headers[k] = v
            except Exception as e:
                pass

            # 覆盖头（用于严格指定来源于 /search/filter 的头）
            if isinstance(override_headers, dict) and override_headers:
                for k, v in override_headers.items():
                    if isinstance(k, str) and isinstance(v, str) and k and not k.strip().startswith(':'):
                        safe_headers[k] = v
            
            if method.upper() == 'POST':
                response = requests.post(url, headers=safe_headers, json=data, params=params, timeout=20)
            else:
                response = requests.get(url, headers=safe_headers, params=params, timeout=20)
            return response.json()
            
        except Exception as e:
            print(f"❌ API请求失败: {e}")
            return None
    
    # 以下是原有的爬取逻辑，适配新的请求头系统
    def _extract_token_id_pairs(self, node: Any) -> List[Tuple[str, str]]:
        """递归遍历 JSON，提取包含 xsec_token 与 id 的对象对"""
        results: List[Tuple[str, str]] = []

        def walk(n: Any):
            if isinstance(n, dict):
                has_token = "xsec_token" in n and isinstance(n["xsec_token"], str)
                has_id = "id" in n and isinstance(n["id"], str)
                if has_token and has_id:
                    results.append((n["xsec_token"], n["id"]))
                for v in n.values():
                    walk(v)
            elif isinstance(n, list):
                for it in n:
                    walk(it)

        walk(node)
        return results

    def _sanitize_note_id(self, nid: Any) -> str:
        """清洗 ID：转字符串，去除 # 或 ? 之后的片段，转小写并去除首尾空白"""
        s = str(nid)
        if '#' in s:
            s = s.split('#', 1)[0]
        if '?' in s:
            s = s.split('?', 1)[0]
        return s.strip().lower()

    def _is_valid_note_id(self, nid: str) -> bool:
        """校验是否为 24 位十六进制 note_id（小红书常见）"""
        note_id_re = re.compile(r"^[0-9a-f]{24}$")
        return bool(note_id_re.fullmatch(nid))

    
    def _extract_master_streams_from_text(self, text: str) -> List[Dict[str, Any]]:
        """从页面源码/JSON文本中提取视频流信息（masterUrl、backupUrls、streamType）。
        适配形如 1.txt 中的片段：包含 "masterUrl": "http:\\u002F...mp4"，并在邻近区域有 "streamType": 114/115/259。
        返回列表元素示例：{"streamType": 114, "masterUrl": "http://..._114.mp4", "backupUrls": ["http://...", ...]}
        """
        streams: List[Dict[str, Any]] = []
        if not isinstance(text, str) or not text:
            return streams

        # 解码常见的 \u002F -> /
        safe = text.replace("\\u002F", "/")

        # 基于对象片段的粗提取：以 masterUrl 为锚点，向前后窗口查找 streamType 和 backupUrls
        pattern_master = re.compile(r'"masterUrl"\s*:\s*"([^"]+?\.mp4)"', re.IGNORECASE)
        for m in pattern_master.finditer(safe):
            url = m.group(1)
            start, end = m.start(), m.end()
            # 在附近 800 字符窗口内搜索 streamType 与 backupUrls（经验足够覆盖 1.txt 的结构）
            window_l = max(0, start - 800)
            window_r = min(len(safe), end + 800)
            window = safe[window_l:window_r]

            # streamType（取就近的一个数值）
            st_match = re.search(r'"streamType"\s*:\s*(\d+)', window, re.IGNORECASE)
            try:
                stream_type = int(st_match.group(1)) if st_match else -1
            except Exception:
                stream_type = -1

            # backupUrls（可选）
            bu_list: List[str] = []
            bu_block = re.search(r'"backupUrls"\s*:\s*\[(.*?)\]', window, re.IGNORECASE | re.DOTALL)
            if bu_block:
                # 提取数组内的所有 URL
                for bu in re.findall(r'"(http[s]?:[^"\s]+?\.mp4)"', bu_block.group(1), re.IGNORECASE):
                    bu_list.append(bu)

            streams.append({
                "streamType": stream_type,
                "masterUrl": url,
                "backupUrls": bu_list
            })

        # 去重：按 masterUrl 唯一
        uniq: Dict[str, Dict[str, Any]] = {}
        for s in streams:
            u = s.get("masterUrl")
            if isinstance(u, str) and u and u not in uniq:
                uniq[u] = s
        return list(uniq.values())

    def _select_video_urls_by_rules(self, streams: List[Dict[str, Any]]) -> List[str]:
        """应用下载选择规则：
        - 多个且包含 259 -> 不下载（返回空列表）
        - 多个且不包含 259 -> 全部下载（返回所有 masterUrl）
        - 只有一个 -> 直接下载（返回该 masterUrl）
        """
        if not isinstance(streams, list) or not streams:
            return []

        # 规范化并收集
        urls: List[str] = []
        types: List[int] = []
        for s in streams:
            u = s.get("masterUrl")
            t = s.get("streamType")
            if isinstance(u, str) and u:
                urls.append(u)
            if isinstance(t, int):
                types.append(t)

        urls = list(dict.fromkeys(urls))  # 去重保序
        tset = set([t for t in types if isinstance(t, int)])

        if len(urls) >= 2:
            if 259 in tset:
                # 存在 259 -> 不下载
                return []
            # 无 259 -> 全部下载
            return urls
        elif len(urls) == 1:
            return urls
        return []

    def get_selected_video_urls_from_page(self) -> List[str]:
        """对当前页面进行源码级解析并根据规则返回应下载的视频URL集合。
        步骤：page_source -> 提取 streams -> 规则筛选 -> 返回URL列表。
        """
        try:
            html = self.driver.page_source or ""
        except Exception:
            html = ""
        streams = self._extract_master_streams_from_text(html)
        return self._select_video_urls_by_rules(streams)

    def _capture_api_headers_from_browser(self, keyword: str) -> Dict[str, str]:
        """在浏览器中执行搜索，捕获API请求头和search_id"""
        try:
            # 1) 通过UI触发搜索，贴近官网流程
            ok = self._perform_search_via_ui(keyword)
            if not ok:
                print("ℹ️ 已回退为直接导航到搜索结果页")
                pass

            
            # 轮询获取性能日志（在搜索触发后持续一段时间）
            captured_filter = False  # 是否已捕获 /search/filter 的签名头
            req_map: Dict[str, Dict[str, Any]] = {}

            def _is_target(u: str) -> bool:
                return isinstance(u, str) and (
                    '/api/sns/web/v1/search/notes' in u or '/api/sns/web/v1/search/filter' in u
                )

            # 恢复外层轮询结构，安全处理 performance 日志
            for _ in range(30):
                try:
                    logs = self.driver.get_log('performance') or []
                    for entry in logs:
                        try:
                            msg = json.loads(entry.get('message', '{}'))
                            message = msg.get('message', {})
                            method_type = message.get('method')
                            if not method_type:
                                continue

                            # 仅处理感兴趣的事件
                            if method_type not in [
                                'Network.requestWillBeSent',
                                'Network.requestWillBeSentExtraInfo',
                                'Network.responseReceived',
                                'Network.responseReceivedExtraInfo'
                            ]:
                                continue

                            params = message.get('params', {})
                            request_id = params.get('requestId') or params.get('requestId'.lower())

                            if method_type == 'Network.requestWillBeSent':
                                # 调试计数已移除
                                try:
                                    req = params.get('request', {})
                                    url = req.get('url', '')
                                    req_method = req.get('method', '')
                                    post_data = req.get('postData')
                                    if request_id:
                                        item = req_map.setdefault(request_id, {})
                                        item['url'] = url
                                        item['method'] = req_method
                                        if isinstance(post_data, str):
                                            item['postData'] = post_data
                                        item['ts'] = time.time()
                                        # 方案B：命中 /search/filter 时提取 keyword/search_id
                                        if isinstance(url, str) and '/search/filter' in url:
                                            try:
                                                parsed = urllib.parse.urlparse(url)
                                                qd = urllib.parse.parse_qs(parsed.query)
                                                kw = qd.get('keyword', [None])[0]
                                                sid = qd.get('search_id', [None])[0]
                                                # 若为POST则尝试从 body 提取
                                                if (not kw or not sid) and isinstance(post_data, str):
                                                    try:
                                                        body = json.loads(post_data)
                                                        if isinstance(body, dict):
                                                            kw = kw or body.get('keyword')
                                                            sid = sid or body.get('search_id')
                                                    except Exception:
                                                        pass
                                                if isinstance(kw, str) and isinstance(sid, str) and kw and sid:
                                                    self.filter_keyword = kw
                                                    self.filter_search_id = sid
                                                    self.filter_captured_at = time.time()
                                            except Exception:
                                                pass
                                except Exception:
                                    pass

                            elif method_type == 'Network.requestWillBeSentExtraInfo':
                                # 调试计数已移除
                                try:
                                    headers = params.get('headers', {})
                                    if headers and isinstance(headers, dict):
                                        # 合并到req_map
                                        if request_id:
                                            item = req_map.setdefault(request_id, {})
                                            ih = item.get('headers', {})
                                            # 仅保留非伪首部
                                            ih.update({k: v for k, v in headers.items() if isinstance(k, str) and isinstance(v, str) and not k.strip().startswith(':')})
                                            item['headers'] = ih
                                            u = item.get('url', '')
                                            if isinstance(u, str) and _is_target(u):
                                                # 仅在命中目标URL时更新最近签名头
                                                self.last_signed_headers = dict(ih)
                                                if '/search/filter' in u:
                                                    # 方案B：仅在命中 /search/filter 时缓存其签名头
                                                    self.filter_signed_headers = dict(ih)
                                                    captured_filter = True
                                except Exception:
                                    pass

                            elif method_type == 'Network.responseReceived':
                                # 调试计数已移除
                                try:
                                    url = params.get('response', {}).get('url', '')
                                    if not isinstance(url, str) or not url:
                                        continue

                                    # 官方 search_id 优先从URL
                                    try:
                                        parsed = urllib.parse.urlparse(url)
                                        q = urllib.parse.parse_qs(parsed.query)
                                        sid_url = q.get('search_id', [None])[0]
                                        if isinstance(sid_url, str) and sid_url and not self.official_search_id:
                                            self.official_search_id = sid_url
                                            if not self._printed_search_id:
                                                self._printed_search_id = True
                                    except Exception:
                                        pass

                                    # 兜底：若URL未取到且当前为notes且有postData
                                    try:
                                        if ('/search/notes' in url) and not self.official_search_id:
                                            candidate = req_map.get(request_id) or {}
                                            if candidate and candidate.get('postData'):
                                                body_candidate = candidate.get('postData')
                                                if isinstance(body_candidate, str) and body_candidate.strip():
                                                    bd_json = json.loads(body_candidate)
                                                    sid_body2 = bd_json.get('search_id') if isinstance(bd_json, dict) else None
                                                    if isinstance(sid_body2, str) and sid_body2:
                                                        self.official_search_id = sid_body2
                                                        if not self._printed_search_id:
                                                            self._printed_search_id = True
                                    except Exception:
                                        pass
                                except Exception:
                                    pass

                            elif method_type == 'Network.responseReceivedExtraInfo':
                                # 可选：补全headers
                                try:
                                    headers = params.get('headers', {})
                                    if headers and request_id:
                                        item = req_map.setdefault(request_id, {})
                                        ih = item.get('headers', {})
                                        ih.update({k: v for k, v in headers.items() if isinstance(k, str) and isinstance(v, str)})
                                        item['headers'] = ih
                                except Exception:
                                    pass
                        except Exception:
                            continue

                    # 若已捕获 /search/filter 的签名，且已有最近签名头，结束轮询
                    if captured_filter and self.last_signed_headers:
                        break
                except Exception:
                    continue

                time.sleep(0.3)

            # 删除调试模式下的统计输出
            if self.official_search_id and not self._printed_search_id:
                self._printed_search_id = True

            if self.cached_filter_groups:
                pass
            
            # 方案S2：不再返回或合并headers
            return {}
            
        except Exception as e:
            print(f"❌ 捕获API请求头失败: {e}")
            return {}
    
    def _request_filters_via_api(self, keyword: str, search_id: str) -> List[Dict[str, Any]]:
        """方案A：局部直连调试，不做解析，仅打印原始响应。
        行为：
        - 不走 make_api_request，直接 requests.get()
        - 打印状态码、关键签名头预览、响应体前 2000 字符
        - 不返回 filters，仅用于调试阶段
        注意：仅用于调试，生产逻辑不依赖该方法。
        """
        try:
            # 仍保留同源校验，避免误请求
            if not isinstance(self.filter_signed_headers, dict) or not self.filter_signed_headers:
                print("ℹ️ 未捕获 /search/filter 签名头，跳过直连（调试）")
                return []
            if not (isinstance(self.filter_keyword, str) and self.filter_keyword and isinstance(self.filter_search_id, str) and self.filter_search_id):
                print("ℹ️ 未捕获 /search/filter 的 keyword/search_id，跳过直连（调试）")
                return []
            if keyword and self.filter_keyword and keyword != self.filter_keyword:
                print(f"ℹ️ 当前关键词与 /search/filter 同源关键词不一致：current='{keyword}' vs captured='{self.filter_keyword}'，跳过直连（调试）")
                return []

            # 组装安全请求头：基础头 + 同源签名头（filter 专用优先）
            safe_headers = {k: v for k, v in self.headers.items() if isinstance(k, str) and not k.strip().startswith(':')}
            for k in ['x-s', 'x-t', 'x-s-common', 'x-b3-traceid', 'x-xray-traceid', 'referer', 'origin', 'user-agent']:
                v = self.filter_signed_headers.get(k) or self.last_signed_headers.get(k) if isinstance(self.last_signed_headers, dict) else None
                if isinstance(v, str) and v:
                    safe_headers[k] = v

            # 构建 GET URL（严格同源参数）
            filters_url = "https://edith.xiaohongshu.com/api/sns/web/v1/search/filter"
            qs = urlencode([("keyword", self.filter_keyword), ("search_id", self.filter_search_id)])
            url_qs = f"{filters_url}?{qs}"

            resp = requests.get(url_qs, headers=safe_headers, timeout=20)
            print(f"✅ 状态码: {resp.status_code}")

            try:
                full_text = (resp.text or '')
            except Exception:
                full_text = ''

            # 最小解析：只解析 data.filters，并映射为 {id,name,filter_tags[{id,name}]} 结构
            try:
                raw = json.loads(full_text)
            except Exception:
                raw = None

            groups: List[Dict[str, Any]] = []
            try:
                if isinstance(raw, dict):
                    node = raw.get('data') if isinstance(raw.get('data'), dict) else raw
                    filters = node.get('filters') if isinstance(node, dict) else None
                    if isinstance(filters, list):
                        for g in filters:
                            if not isinstance(g, dict):
                                continue
                            gid = g.get('id') or ''
                            gname = g.get('name') or ''
                            tags = g.get('filter_tags') if isinstance(g.get('filter_tags'), list) else []
                            norm_tags = []
                            for t in tags:
                                if isinstance(t, dict):
                                    tid = t.get('id') or ''
                                    tname = t.get('name') or ''
                                    if tid and tname:
                                        norm_tags.append({'id': tid, 'name': tname})
                            if gid and gname and norm_tags:
                                groups.append({'id': gid, 'name': gname, 'filter_tags': norm_tags})

                print(f"✅ 解析到 {len(groups)} 个分组（最小解析）")
            except Exception as parse_err:
                print(f"⚠️ 解析 data.filters 失败：{parse_err}")
                groups = []

            return groups
        except Exception as e:
            print(f"❌ 调试直连失败: {e}")
            return []

    def _choose(self, prompt: str, options: List[str], default_idx: int = 0) -> str:
        """简单的交互式选择器，返回所选项字符串。"""
        if not options:
            return ""
        while True:
            print(prompt)
            for i, opt in enumerate(options):
                tag = "(默认)" if i == default_idx else ""
                print(f"  {i}. {opt} {tag}")
            s = input("请输入序号（回车默认）：").strip()
            if not s:
                return options[default_idx]
            if s.isdigit():
                idx = int(s)
                if 0 <= idx < len(options):
                    return options[idx]
            print("输入无效，请重试。")
    
    def _choose_tag_from_group(self, group: Dict[str, Any], default_idx: int = 0) -> str:
        """从分组里选择一个 tag，返回其 id。"""
        tags = group.get("filter_tags", [])
        if not tags:
            return ""
        gid = (group.get("id") or "").strip()

        # 计算默认索引：按规则为各分组定位默认项
        def find_index_by(pred_name: str = None, pred_id: str = None) -> int:
            for i, t in enumerate(tags):
                tid = (t.get('id') or '').strip()
                tname = (t.get('name') or '').strip()
                if pred_id and tid == pred_id:
                    return i
                if pred_name and tname == pred_name:
                    return i
            return -1

        # 规则：
        # - sort_type: 默认 综合(general)
        # - filter_note_type / filter_note_time / filter_note_range: 默认 不限
        # - filter_hot: 默认不选择（提供虚拟项“（不选择）”）
        # 若找不到匹配项则保留传入的 default_idx
        computed_default = default_idx
        if gid == 'sort_type':
            idx = find_index_by(pred_id='general')
            if idx < 0:
                idx = find_index_by(pred_name='综合')
            if idx >= 0:
                computed_default = idx
        elif gid in ('filter_note_type', 'filter_note_time', 'filter_note_range'):
            idx = find_index_by(pred_name='不限')
            if idx < 0:
                idx = find_index_by(pred_id='不限')
            if idx >= 0:
                computed_default = idx

        # 仅显示名称；为热门词加入“（不选择）”并默认不选
        names = [(t.get('name') or '').strip() for t in tags]
        skip_hot = (gid == 'filter_hot')
        if skip_hot:
            options = ['（不选择）'] + names
            # 覆盖默认索引到 0
            computed_default = 0
        else:
            options = names

        choice = self._choose(f"选择{group.get('name','筛选项')}：", options, default_idx=computed_default)

        # 解析返回id
        if skip_hot and choice == '（不选择）':
            return ""
        # 映射显示名称到对应id
        chosen_name = choice
        for t in tags:
            if (t.get('name') or '').strip() == chosen_name:
                return (t.get('id') or '').strip()
        # 未找到匹配则返回空，避免误加
        return ""
    
    def _build_filters_interactive(self, keyword: str, search_id: str) -> Tuple[List[Dict[str, Any]], str, int]:
        """基于动态接口交互构造 filters，包含 sort_type、note_type、time、range、hot，排除位置距离。"""
        # 方案B：优先直连 /search/filter（仅当已捕获该接口签名头），失败回退CDP缓存，再回退默认分组
        groups: List[Dict[str, Any]] = []
        if isinstance(self.filter_signed_headers, dict) and self.filter_signed_headers:
            groups = self._request_filters_via_api(keyword, search_id)
            if isinstance(groups, list) and groups:
                self.cached_filter_groups = groups
        if not groups and isinstance(self.cached_filter_groups, list) and self.cached_filter_groups:
            groups = self.cached_filter_groups
            print(f"📦 使用缓存的 filter_groups（{len(groups)} 组）")
        wanted = {"sort_type", "filter_note_type", "filter_note_time", "filter_note_range", "filter_hot"}
        exclude = {"filter_pos_distance"}

        selected: List[Dict[str, Any]] = []
        chosen_sort = "general"  # 默认值
        chosen_note_type = 0     # 默认值

        print(f"\n🎯 开始交互式分类选择...")
        
        for g in groups:
            gid = g.get("id")
            group_name = g.get("name", "未知分类")
            
            # 跳过排除的分类
            if gid in exclude:
                print(f"⏭️ 跳过分类: {group_name} ({gid})")
                continue
            
            # 只处理需要的分类，但显示所有分类供参考
            if gid not in wanted:
                print(f"ℹ️ 可选分类: {group_name} ({gid}) - 暂不支持交互选择")
                continue
            
            print(f"\n📋 当前分类: {group_name}")
            tag_id = self._choose_tag_from_group(g, default_idx=0)
            if not tag_id:
                continue
                
            selected.append({"tags": [tag_id], "type": gid})
            print(f"✅ 已选择: {tag_id}")
            
            # 处理特殊逻辑
            if gid == "sort_type":
                chosen_sort = tag_id
            elif gid == "filter_note_type":
                # 对齐顶层 note_type（0 不限，1 视频，2 图文）
                if tag_id == "视频笔记":
                    chosen_note_type = 1
                elif tag_id == "普通笔记":
                    chosen_note_type = 2
                else:
                    chosen_note_type = 0

        print(f"\n🎉 分类选择完成！共选择了 {len(selected)} 个筛选条件")
        return selected, chosen_sort, chosen_note_type

    def _request_page(self, keyword: str, page: int, search_id: str, sort: str = "general", note_type: int = 0, filters: List[Dict[str, Any]] = None, page_size: int = 20) -> List[Tuple[str, str]]:
        """按页请求并返回 (token, cleaned_id) 列表"""
        payload = {
            "keyword": keyword,
            "page": page,
            "page_size": page_size,
            "search_id": search_id,
            "sort": sort,
            "note_type": note_type,
            "filters": filters or [],
            "ext_flags": [],
            "geo": "",
            "image_formats": ["jpg", "webp", "avif"],
        }
        
        # 尝试最多3次请求
        for attempt in range(3):
            data = self._make_api_request(self.search_url, method='POST', data=payload)
            if data:
                pairs = self._extract_token_id_pairs(data)
                cleaned: List[Tuple[str, str]] = []
                for token, nid in pairs:
                    cid = self._sanitize_note_id(nid)
                    if self._is_valid_note_id(cid):
                        cleaned.append((token, cid))
                return cleaned
            else:
                print(f"⚠️ 第 {attempt+1} 次请求失败，等待后重试...")
                time.sleep(2 ** attempt)  # 指数退避
                
        print(f"❌ 第 {page} 页请求最终失败")
        return []
    
    def _crawl_notes(self, keyword: str, total_pages: int = 1, search_id: str = None, filters: List[Dict[str, Any]] = None, sort: str = "general", note_type: int = 0):
        """爬取笔记链接的主要逻辑"""
        print(f"\n🔍 开始爬取关键词: {keyword}")
        print(f"📄 计划爬取页数: {total_pages}")
        print(f"📊 排序方式: {sort}")
        
        # 仅首次打印 Search ID，避免与捕获阶段重复
        if isinstance(search_id, str) and search_id and not self._printed_search_id:
            print(f"🔑 Search ID: {search_id}")
            self._printed_search_id = True
        
        # 汇总与去重
        seen: set[Tuple[str, str]] = set()
        unique_pairs: List[Tuple[str, str]] = []

        for p in range(1, total_pages + 1):
            try:
                print(f"📄 正在爬取第 {p} 页...")
                page_pairs = self._request_page(keyword, p, search_id, sort, note_type, filters)
                
                for token, nid in page_pairs:
                    key = (token, nid)
                    if key not in seen:
                        seen.add(key)
                        unique_pairs.append(key)
                        
                time.sleep(1)  # 避免请求过快
                
            except Exception as page_err:
                print(f"❌ 第 {p} 页请求失败：{page_err}")

        # 输出结果
        print(f"\n🎉 爬取完成！")
        print("="*50)
        base = "https://www.xiaohongshu.com/explore/{id}?xsec_token={token}&xsec_source=pc_search&source=web_search"
        
        for token, nid in unique_pairs:
            print(base.format(id=nid, token=token))
            
        print("="*50)
        print(f"📊 总计去重后：{len(unique_pairs)} 条")
        print(f"🔍 关键词：{keyword}")
        print(f"📊 排序方式：{sort}")
        print(f"📄 请求页数：{total_pages}")
        
        return unique_pairs
    
    def _format_results(self, results: List[Tuple[str, str]]) -> List[str]:
        """格式化爬取结果为URL列表"""
        base = "https://www.xiaohongshu.com/explore/{id}?xsec_token={token}&xsec_source=pc_search&source=web_search"
        return [base.format(id=nid, token=token) for token, nid in results]
    
    def run_interactive(self):
        """交互式运行主程序"""
        print("=== 小红书Selenium集成爬虫 ===")
        print("保持登录状态 + API请求头获取 + 链接爬取\n")
        
        # 1. 启动浏览器 - 让所有Chrome日志在这里输出完毕
        if not self._setup_browser():
            return False
        
        try:
            # 2. 检查并确保登录
            if not self._ensure_login():
                return False
            
            # 3. 等待一下让所有异步日志输出完毕
            time.sleep(1)
            
            # 4. 输入关键词 - 现在所有日志都应该已经输出完了
            keyword = input("请输入要爬取的关键词: ").strip()
                
            if not keyword:
                print("❌ 关键词不能为空")
                return False
            
            # 5. 先进入搜索页，并在该页上下文捕获官方 search_id
            if not self.official_search_id:
                # 强制要求官方 search_id，不再使用本地生成
                try:
                    _ = self._capture_api_headers_from_browser(keyword)
                except Exception:
                    pass
            if not self.official_search_id:
                print("❌ 未能捕获官方 search_id，请在搜索结果页尝试轻滚动或切换一次排序后重试。")
                return False
            search_id = self.official_search_id
            print(f"🆔 使用官方 search_id: {search_id}")
            
            # 6. 在搜索结果页提取请求头和 Cookie（符合你的时机要求）
            if not self._extract_headers_from_browser():
                return False
            
            # 7. 获取并选择动态分类
            print(f"\n📊 正在获取关键词 '{keyword}' 的动态分类选项...")
            filters, sort_type, note_type = self._build_filters_interactive(keyword, search_id)
            
            # 8. 输入页数
            pages_input = input("\n请输入要爬取的页数（每页20条，默认1页）: ").strip()
            total_pages = int(pages_input) if pages_input.isdigit() else 1
            
            # 9. 开始爬取
            results = self._crawl_notes(keyword, total_pages, search_id, filters, sort_type, note_type)
            
            # 10. 返回结果
            if results:
                urls = self._format_results(results)
                print("\n✅ 爬取任务完成！")
                print(f"📋 获取到 {len(urls)} 个链接")
                # 10.1 询问是否并发抓取详情页
                try:
                    do_detail = input("是否并发抓取这些详情页内容并下载图片/视频？(Y/n，默认Y): ").strip().lower()
                except Exception:
                    do_detail = 'y'
                if do_detail in ('', 'y', 'yes', '1'):  # 默认执行
                    # 采集并发与限速参数
                    try:
                        mw_s = input("并发线程数（默认10）: ").strip()
                        max_workers = int(mw_s) if mw_s.isdigit() and int(mw_s) > 0 else 10
                    except Exception:
                        max_workers = 10
                    try:
                        rp_s = input("每秒最大请求数（默认50）: ").strip()
                        rate_per_sec = int(rp_s) if rp_s.isdigit() and int(rp_s) > 0 else 50
                    except Exception:
                        rate_per_sec = 50
                    # 默认同时下载图片与视频；若无对应资源则自动跳过
                    dl_images = True
                    dl_videos = True

                    # 询问是否仅下载前 N 条用于测试
                    try:
                        n_input = input("仅下载前 N 条详情页用于测试（回车=全部）：").strip()
                        n_limit = int(n_input) if n_input.isdigit() and int(n_input) > 0 else None
                    except Exception:
                        n_limit = None
                    urls_to_fetch = urls[:n_limit] if n_limit else urls

                    downloader = XHSDetailDownloader(headers=self.headers,
                                                     max_workers=max_workers,
                                                     rate_per_sec=rate_per_sec,
                                                     dl_images=dl_images,
                                                     dl_videos=dl_videos)
                    summary = downloader.scrape_many(urls_to_fetch)
                    print(f"\n📦 详情抓取完成：成功 {summary.get('ok',0)} 条，失败 {summary.get('fail',0)} 条")

                return {
                    'urls': urls,
                    'results': results,
                    'keyword': keyword,
                    'sort': sort_type,
                    'note_type': note_type,
                    'filters': filters
                }
            else:
                print("\n⚠️ 未获取到有效数据")
                return None
            
            return True
            
        except Exception as e:
            print(f"❌ 执行过程中出现错误: {e}")
            return False
            
        finally:
            # 运行结束后自动关闭浏览器（按方案一：不再询问）
            try:
                if self.driver:
                    self.driver.quit()
                    print("🔒 浏览器已关闭")
            except Exception:
                pass
    

# =============== 详情页并发下载（方案B：同文件轻量类） ===============

class XHSDetailDownloader:
    """
    轻量详情下载器：并发抓取多个详情页，解析标题/作者/文本/图片/视频并保存。
    - 复用登录态 headers（含 Cookie/UA）
    - 线程安全限速，默认每秒最多 50 次请求
    - 图片命名：img_001.jpg；视频命名：video_001.mp4
    - 目录命名：笔记（<标题>）
    """

    class _RateLimiter:
        def __init__(self, rate_per_sec: int):
            self.rate = max(1, int(rate_per_sec) if isinstance(rate_per_sec, int) else 50)
            self.lock = threading.Lock()
            self.q = deque()

        def wait(self):
            while True:
                now = time.time()
                with self.lock:
                    while self.q and now - self.q[0] >= 1.0:
                        self.q.popleft()
                    if len(self.q) < self.rate:
                        self.q.append(now)
                        return
                    sleep_for = 1.0 - (now - self.q[0])
                if sleep_for > 0:
                    time.sleep(min(sleep_for, 0.05))

    def __init__(self, headers: Dict[str, str], max_workers: int = 10, rate_per_sec: int = 50, dl_images: bool = True, dl_videos: bool = True, video_strategy: str | None = None):
        self.headers = headers or {}
        self.max_workers = max(1, int(max_workers) if isinstance(max_workers, int) else 10)
        self.rate_limiter = self._RateLimiter(rate_per_sec=rate_per_sec)
        self.dl_images = bool(dl_images)
        self.dl_videos = bool(dl_videos)
        self.video_strategy = video_strategy

        self.session = requests.Session()
        try:
            from requests.adapters import HTTPAdapter
            adapter = HTTPAdapter(pool_connections=self.max_workers, pool_maxsize=self.max_workers)
            self.session.mount('http://', adapter)
            self.session.mount('https://', adapter)
        except Exception:
            pass

    def _get(self, url: str, *, headers: dict = None, timeout: int = 20, stream: bool = False):
        self.rate_limiter.wait()
        return self.session.get(url, headers=headers or self.headers, timeout=timeout, stream=stream)

    @staticmethod
    def _ensure_dir(path: str):
        if not os.path.exists(path):
            os.makedirs(path, exist_ok=True)

    @staticmethod
    def _sanitize_dirname(name: str) -> str:
        if not name:
            return "未命名"
        name = re.sub(r'[<>:"/\\|?*\n\r\t]', '_', name)
        name = name.strip().strip('.')
        return name[:100] if len(name) > 100 else name

    @staticmethod
    def _guess_ext_from_url(url: str) -> str:
        path = urllib.parse.urlsplit(url).path.lower()
        for ext in ('.jpg', '.jpeg', '.png', '.webp', '.gif'):
            if path.endswith(ext):
                return ext
        return '.jpg'

    def _fetch_html(self, url: str) -> str:
        resp = self._get(url, timeout=20)
        resp.raise_for_status()
        try:
            resp.encoding = resp.apparent_encoding or resp.encoding
        except Exception:
            pass
        return resp.text

    @staticmethod
    def _parse_title(html: str) -> str:
        m = re.search(r'<meta[^>]+(?:property|name)=["\']og:title["\'][^>]+content=["\'](.*?)["\']', html, flags=re.I | re.S)
        return m.group(1).strip() if m else ""

    @staticmethod
    def _parse_author(html: str) -> str:
        m = re.search(r'<span[^>]*class=["\']username["\'][^>]*>(.*?)</span>', html, flags=re.I | re.S)
        return m.group(1).strip() if m else ""

    @staticmethod
    def _parse_text_and_images(html: str):
        m = re.search(r'<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']', html, flags=re.I | re.S)
        text = m.group(1).strip() if m else ""
        imgs = re.findall(r'<meta[^>]+(?:property|name)=["\']og:image["\'][^>]+content=["\'](.*?)["\']', html, flags=re.I | re.S)
        seen = set()
        img_list = []
        for u in imgs:
            if u not in seen:
                seen.add(u)
                img_list.append(u)
        return text, img_list

    @staticmethod
    def _parse_video_urls(html: str):
        """
        从详情页HTML中提取所有视频masterUrl候选。
        与参考脚本保持一致：仅正则抓取，不做网络请求。
        """
        urls = re.findall(r'"masterUrl"\s*:\s*"(.*?)"', html, flags=re.I | re.S)
        return [XHSDetailDownloader._unescape_master_url(u) for u in urls if u]

    @staticmethod
    def _unescape_master_url(s: str) -> str:
        if not s:
            return s
        s = s.replace("\\u002F", "/").replace("\\u003d", "=").replace("\\u0026", "&")
        s = s.replace("\\/", "/")
        return s

    @staticmethod
    def _select_best_video_url(candidates: List[str]) -> str:
        """
        从 candidates 中选择单一最佳候选：
        1) 先过滤明显水印（更严格）：watermark/wm 参数、典型水印路径关键词
        2) 在非水印集合中按“实际清晰度线索”择优：
           - 优先从 URL 中解析分辨率（如 2160/1440/1080/720 等数值）进行排序
           - 若无分辨率数值，再按关键词优先级：nowm/no_watermark/origin/src/uhd/4k/2k/1080/hd/720/540/480/360
        3) 不做网络请求（不探测 Content-Length），保持轻量
        4) 若全部为水印或未能解析，则回退为原候选中的最优关键词
        """
        if not candidates:
            return ''
        # 去重保序
        seen = set()
        uniq = []
        for u in candidates:
            if u and u not in seen:
                seen.add(u)
                uniq.append(u)
        if not uniq:
            return ''

        def is_watermark(u: str) -> bool:
            s = u.lower()
            # 参数/关键词判断
            if ('watermark' in s) or ('wm=1' in s) or re.search(r'[?&#]watermark=1(?!\d)', s):
                return True
            # 常见路径/关键词（保守加入，避免误判过多）
            wm_keywords = ['mark=', 'logo=', '/watermark', 'withwm', 'wmvideo']
            return any(k in s for k in wm_keywords)

        def parse_resolution(u: str) -> int:
            """从 URL 猜测清晰度，返回像素高度，未知返回 -1"""
            s = u.lower()
            # 常见形式：1080p、720p、_1080、/1080/ 等
            m = re.search(r'(?:(?<=_)|(?<=/)|(?<=-)|(?<=\.)|^)(2160|1440|1080|960|720|540|480|360)(?:p)?(?=\D|$)', s)
            if m:
                try:
                    return int(m.group(1))
                except Exception:
                    pass
            return -1

        priority = [
            'nowm', 'no_watermark', 'origin', 'src', 'uhd', '4k', '2160', '2k',
            '1440', '1080', 'hd', '960', '720', '540', '480', '360'
        ]
        def kw_score(u: str) -> int:
            s = u.lower()
            for i, kw in enumerate(priority):
                if kw in s:
                    return len(priority) - i
            return 0

        # 1) 过滤水印
        non_wm = [u for u in uniq if not is_watermark(u)]

        def pick_best(pool: List[str]) -> str:
            if not pool:
                return ''
            # 先按分辨率数值排序（大优先），再按关键词得分，再按出现顺序
            return max(pool, key=lambda x: (parse_resolution(x), kw_score(x), -pool.index(x)))
        
        # 先在非水印集合中选择
        best_non_wm = pick_best(non_wm)
        if best_non_wm:
            return best_non_wm
        # 回退：在原集合中按关键词/分辨率选一个
        return pick_best(uniq)

    def _download_video(self, video_url: str, folder: str, *, filename: str | None = None, max_retries: int = 2):
        path = urllib.parse.urlsplit(video_url).path
        default_name = os.path.basename(path) or "video.mp4"
        if not default_name.lower().endswith('.mp4'):
            default_name = default_name + '.mp4'
        name = filename or default_name
        filepath = os.path.join(folder, name)
        for attempt in range(max_retries + 1):
            try:
                resp = self._get(video_url, timeout=30, stream=True)
                resp.raise_for_status()
                with open(filepath, 'wb') as f:
                    for chunk in resp.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                return filepath
            except Exception:
                if attempt >= max_retries:
                    return None
                time.sleep(0.5 * (attempt + 1))

    def _download_images_concurrent(self, image_urls: List[str], folder: str):
        if not image_urls:
            return []
        self._ensure_dir(folder)

        def _task(u, idx):
            try:
                resp = self._get(u, timeout=20)
                resp.raise_for_status()
                ext = self._guess_ext_from_url(u)
                filename = f"img_{idx:03d}{ext}"
                with open(os.path.join(folder, filename), 'wb') as f:
                    f.write(resp.content)
                return filename
            except Exception as e:
                return f"ERR:{idx}:{e}"

        results = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as ex:
            futs = [ex.submit(_task, u, i + 1) for i, u in enumerate(image_urls)]
            for fu in as_completed(futs):
                try:
                    results.append(fu.result())
                except Exception:
                    results.append("ERR")
        return results

    def _download_videos_concurrent(self, video_urls: List[str], folder: str):
        if not video_urls:
            return []
        # 去重保序
        seen = set()
        uniq = []
        for u in video_urls:
            if u and u not in seen:
                seen.add(u)
                uniq.append(u)
        if not uniq:
            return []
        self._ensure_dir(folder)

        def _task(u, idx):
            fname = f"video_{idx:03d}.mp4"
            path = self._download_video(u, folder, filename=fname, max_retries=2)
            return path if path else f"ERR:{idx}"

        results = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as ex:
            futs = [ex.submit(_task, u, i + 1) for i, u in enumerate(uniq)]
            for fu in as_completed(futs):
                try:
                    results.append(fu.result())
                except Exception:
                    results.append("ERR")
        return results

    def _save_content(self, out_dir: str, author: str, title: str, text: str) -> str:
        base_dir = os.path.dirname(__file__)
        note_dir = os.path.join(base_dir, out_dir)
        self._ensure_dir(note_dir)
        content_path = os.path.join(note_dir, "内容.txt")
        with open(content_path, 'w', encoding='utf-8') as f:
            f.write(f"作者：{author}\n")
            f.write(f"标题：{title}\n")
            f.write("文本：\n")
            f.write(text or "")
        return note_dir

    def _scrape_one(self, url: str) -> bool:
        try:
            html = self._fetch_html(url)
            title = self._parse_title(html)
            author = self._parse_author(html)
            text, images = self._parse_text_and_images(html)
            videos = self._parse_video_urls(html)

            safe_title = self._sanitize_dirname(title)
            out_dir = f"笔记（{safe_title}）" if safe_title else "笔记（未命名）"
            note_dir = self._save_content(out_dir, author, title, text)
            img_ok = 0
            vid_ok = 0
            if self.dl_images and images:
                img_results = self._download_images_concurrent(images, note_dir)
                img_ok = sum(1 for r in img_results if r and not str(r).startswith('ERR:'))
            if self.dl_videos and videos:
                # 统一去重保序
                seen_v = set()
                uniq_v = []
                for u in videos:
                    if u and u not in seen_v:
                        seen_v.add(u)
                        uniq_v.append(u)

                # 新规则：
                # - 多个且包含 259 -> 仅下载非 _259 的所有视频
                # - 多个且不包含 259 -> 全部下载
                # - 仅一个 -> 直接下载
                def _is_259(u: str) -> bool:
                    s = (u or '').lower()
                    # 仅在存在下划线前缀时认定为 259 清晰度，避免误判 query/id 中的“259”
                    # 例如：..._259.mp4 或 ..._259?...
                    return re.search(r'(?<=_)259(?=\D|$)', s) is not None

                if len(uniq_v) >= 2:
                    if any(_is_259(u) for u in uniq_v):
                        # 含 _259：仅下载非 _259 的所有视频
                        non_259 = [u for u in uniq_v if not _is_259(u)]
                        if non_259:
                            v_results = self._download_videos_concurrent(non_259, note_dir)
                            vid_ok = sum(1 for r in v_results if r and not str(r).startswith('ERR:'))
                        else:
                            vid_ok = 0
                    else:
                        v_results = self._download_videos_concurrent(uniq_v, note_dir)
                        vid_ok = sum(1 for r in v_results if r and not str(r).startswith('ERR:'))
                elif len(uniq_v) == 1:
                    path = self._download_video(uniq_v[0], note_dir, filename="video_001.mp4", max_retries=2)
                    vid_ok = 1 if path and os.path.exists(path) else 0

            abs_dir = os.path.abspath(note_dir)
            # 输出精简为“对应笔记下载成功”，不再打印“视频成功”相关字样
            print(f"✅ 笔记下载成功：{title or '未命名'}")
            print(f"📂 保存路径：{abs_dir}")
            return True
        except Exception as e:
            print(f"❌ 详情抓取失败：{url} -> {e}")
            return False

    def scrape_many(self, urls: List[str]) -> Dict[str, int]:
        if not urls:
            return {'ok': 0, 'fail': 0}
        ok = 0
        fail = 0
        with ThreadPoolExecutor(max_workers=self.max_workers) as ex:
            futs = {ex.submit(self._scrape_one, u): u for u in urls}
            for fu in as_completed(futs):
                try:
                    if fu.result():
                        ok += 1
                    else:
                        fail += 1
                except Exception:
                    fail += 1
        return {'ok': ok, 'fail': fail}


def main():
    """主函数"""
    # 在程序开始时就重定向stderr，彻底屏蔽所有Chrome日志
    original_stderr = sys.stderr
    try:
        # 创建一个自定义的stderr过滤器，只允许我们的程序输出
        class FilteredStderr:
            def __init__(self, original):
                self.original = original
                
            def write(self, text):
                # 过滤掉Chrome相关的日志
                if any(keyword in text for keyword in [
                    'WARNING: All log messages before absl::InitializeLog()',
                    'voice_transcription.cc',
                    'DevTools listening on',
                    'Registering VoiceTranscriptionCapability'
                ]):
                    return  # 不输出这些日志
                return self.original.write(text)
                
            def flush(self):
                return self.original.flush()
        
        # 应用过滤器
        sys.stderr = FilteredStderr(original_stderr)
        
        crawler = XHSIntegratedCrawler()
        crawler.run_interactive()
        
    finally:
        # 恢复原始stderr
        sys.stderr = original_stderr

if __name__ == "__main__":
    main()
 
