from pathlib import Path
import os
from urllib.parse import quote, urlparse, unquote, urlencode, parse_qs
import requests
from requests.adapters import HTTPAdapter, Retry
import json
import csv
import time
import re
import random
import string
from typing import List, Dict, Any, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Thread, Lock
from collections import deque

DOUYIN_SEARCH_URL_TMPL = "https://www.douyin.com/search/{}"
EXPORT_DIR_NAME = "export"
DOWNLOADS_DIR_NAME = "downloads"
DEBUG_DIR_NAME = "feed_debug"
STORAGE_STATE_FILE = "douyin_state.json"
COOKIES_FILE = "cookies.json"
HEADLESS = False
SCROLL_ROUNDS = 120
SCROLL_PAUSE_SEC = 1.2
REQUEST_TIMEOUT = 20
RETRY_TIMES = 2
MAX_PARSE_CONCURRENCY = 6
MAX_DOWNLOAD_CONCURRENCY = 3

PARSE_WORKERS = 3

# Web API 端点（纯 requests 使用）
SEARCH_API_URL = "https://www.douyin.com/aweme/v1/web/general/search/single/"
DETAIL_API_URL = "https://www.douyin.com/aweme/v1/web/aweme/detail/"
SEARCH_ITEM_API_URL = "https://www.douyin.com/aweme/v1/web/search/item/"
DEFAULT_UA = (
	"Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
	"AppleWebKit/537.36 (KHTML, like Gecko) "
	"Chrome/120.0 Safari/537.36"
)


def ensure_dir(path: Path) -> None:
	"""创建目录（若不存在）。
	参数:
	- path: 需要确保存在的目录路径
	返回:
	- None
	"""
	path.mkdir(parents=True, exist_ok=True)


def safe_json_parse(text: Optional[str]):
	"""安全解析JSON字符串。
	尝试直接json.loads；若失败，尝试解码类似URL编码的文本后再解析。
	参数:
	- text: 可能为None或包含JSON的字符串
	返回:
	- 解析后的对象或None
	"""
	if not text:
		return None
	try:
		return json.loads(text)
	except Exception:
		try:
			return json.loads(re.sub(r"%([0-9A-Fa-f]{2})", lambda m: bytes.fromhex(m.group(1)).decode('latin-1'), text))
		except Exception:
			return None


def build_requests_session() -> requests.Session:
	s = requests.Session()
	retries = Retry(total=RETRY_TIMES, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504])
	s.mount("http://", HTTPAdapter(max_retries=retries))
	s.mount("https://", HTTPAdapter(max_retries=retries))
	return s


def sanitize_filename(name: str, max_len: int = 80) -> str:
	name = re.sub(r"[\\/:*?\"<>|]", "_", name)
	name = re.sub(r"\s+", " ", name).strip()
	if len(name) > max_len:
		name = name[:max_len].rstrip()
	return name or "video"


def extract_aweme_id_from_url(url: str) -> Optional[str]:
	m = re.search(r"/video/(\d+)", url)
	return m.group(1) if m else None


def normalize_video_url(href: Optional[str]) -> Optional[str]:
	if not href:
		return None
	if href.startswith("//"):
		return "https:" + href
	if href.startswith("/video/"):
		return "https://www.douyin.com" + href
	if href.startswith("http"):
		return href
	return None


def parse_render_data_video_links(page) -> List[str]:
	data_text = page.evaluate('''() => {
		const rd = document.querySelector('#RENDER_DATA');
		if (rd && rd.textContent) return decodeURIComponent(rd.textContent);
		const ss = document.querySelector('#SIGI_STATE');
		if (ss && ss.textContent) return ss.textContent;
		return null;
	}''')
	parsed = safe_json_parse(data_text)
	if not parsed:
		return []
	links: List[str] = []
	def _walk(o: Any):
		if isinstance(o, dict):
			for k, v in o.items():
				if k == "aweme_id" and isinstance(v, str):
					links.append(f"https://www.douyin.com/video/{v}")
				_walk(v)
		elif isinstance(o, list):
			for it in o:
				_walk(it)
	_walk(parsed)
	# 去重保持顺序
	seen = set()
	res = []
	for u in links:
		vid = extract_aweme_id_from_url(u)
		if not vid or vid in seen:
			continue
		seen.add(vid)
		res.append(u)
	return res


def collect_video_links_from_search(page, target_count: int, max_rounds: int) -> List[str]:
	seen_ids = set()
	video_urls: List[str] = []
	# 先尝试等待首屏出现视频链接（兼容任意标签上的 href）
	try:
		page.wait_for_selector('[href*="/video/"]', timeout=8000)
	except Exception:
		pass
	for round_idx in range(max_rounds):
		hrefs = page.eval_on_selector_all('[href*="/video/"], a[href*="/video/"]', 'els => els.map(e => e.getAttribute("href"))')
		print(f"第{round_idx+1}轮，候选href数量: {len(hrefs)}")
		for href in hrefs:
			u = normalize_video_url(href)
			if not u:
				continue
			vid = extract_aweme_id_from_url(u)
			if not vid or vid in seen_ids:
				continue
			seen_ids.add(vid)
			video_urls.append(f"https://www.douyin.com/video/{vid}")
			print(f"发现视频: {vid}")
			if len(video_urls) >= target_count:
				return video_urls
		# 若还不够，尝试从RENDER_DATA提取
		if len(video_urls) < target_count:
			rd_links = parse_render_data_video_links(page)
			print(f"RENDER_DATA 解析链接数量: {len(rd_links)}")
			for u in rd_links:
				vid = extract_aweme_id_from_url(u)
				if not vid or vid in seen_ids:
					continue
				seen_ids.add(vid)
				video_urls.append(f"https://www.douyin.com/video/{vid}")
				print(f"发现视频(SSR): {vid}")
				if len(video_urls) >= target_count:
					return video_urls
		page.mouse.wheel(0, 2800)
		time.sleep(SCROLL_PAUSE_SEC)
	return video_urls


def collect_video_links_by_xpath(page, target_count: int, root_xpath: str = '//*[@id="semiTabPanel0"]') -> List[str]:
	seen_ids = set()
	video_urls: List[str] = []
	# 先找容器下所有指向 /video/ 的链接
	anchors = []
	try:
		anchors = page.query_selector_all(f'xpath={root_xpath}//a[contains(@href, "/video/")]')
	except Exception:
		anchors = []
	if not anchors:
		# 兜底：任何带 href 的节点
		try:
			anchors = page.query_selector_all(f'xpath={root_xpath}//*[@href]')
		except Exception:
			anchors = []
	for el in anchors:
		try:
			href = el.get_attribute('href')
			u = normalize_video_url(href)
			if not u:
				continue
			vid = extract_aweme_id_from_url(u)
			if not vid or vid in seen_ids:
				continue
			seen_ids.add(vid)
			video_urls.append(f"https://www.douyin.com/video/{vid}")
			print(f"XPath发现视频: {vid}")
			if len(video_urls) >= target_count:
				break
		except Exception:
			continue
	return video_urls


def deep_find_aweme(obj: Any) -> Optional[Dict]:
	try:
		stack = [obj]
		while stack:
			cur = stack.pop()
			if isinstance(cur, dict):
				if ("aweme_id" in cur or "aweme_id_str" in cur or "group_id" in cur) and isinstance(cur.get("video"), dict):
					return cur
				for v in cur.values():
					if isinstance(v, (dict, list)):
						stack.append(v)
			elif isinstance(cur, list):
				for v in cur:
					if isinstance(v, (dict, list)):
						stack.append(v)
	except Exception:
		return None
	return None


def extract_video_info(aweme: Dict) -> Dict:
	aweme_id = aweme.get("aweme_id") or aweme.get("aweme_id_str") or aweme.get("group_id")
	title = aweme.get("desc") or aweme.get("title") or ""
	author = (aweme.get("author") or {}).get("nickname") if isinstance(aweme.get("author"), dict) else ""
	video = aweme.get("video") if isinstance(aweme.get("video"), dict) else None

	def _gear_rank(name: Optional[str]) -> int:
		if not name:
			return 0
		n = str(name).lower()
		mapping = {
			"uhd_4k": 4000,
			"uhd": 4000,
			"super_1080": 1090,
			"hd_1080": 1080,
			"fhd_1080": 1080,
			# 新增1080P相关的gear名称映射
			"1080": 1080,
			"1080p": 1080,
			"1080_1": 1080,
			"lowest_1080": 1080,
			"adapt_lowest_1080": 1080,
			"hd_720": 720,
			"normal_720": 720,
			"720": 720,
			"720p": 720,
			"normal_540": 540,
			"540": 540,
			"sd_480": 480,
			"480": 480,
		}
		for k, v in mapping.items():
			if k in n:
				return v
		return 0

	def _iter_bitrate_items(v: Dict) -> List[Dict]:
		items: List[Dict] = []
		for key in ["bit_rate", "bitrate", "bitrate_info"]:
			val = v.get(key)
			if isinstance(val, list):
				items.extend([x for x in val if isinstance(x, dict)])
		return items

	def _select_best(video_dict: Dict) -> Tuple[List[str], Dict[str, Any]]:
		best_urls: List[str] = []
		meta: Dict[str, Any] = {"codec": "", "gear_name": "", "bitrate": 0, "quality_label": ""}
		cands = []
		for it in _iter_bitrate_items(video_dict):
			play_addr = it.get("play_addr") if isinstance(it.get("play_addr"), dict) else None
			ul = play_addr.get("url_list") if isinstance(play_addr, dict) else None
			if not isinstance(ul, list) or not any(isinstance(u, str) for u in ul):
				continue
			is_h265 = bool(it.get("is_h265") or (str(it.get("codec_type", "")).upper().find("265") >= 0))
			gear = it.get("gear_name") or it.get("quality") or it.get("quality_type") or ""
			br = it.get("bitrate") or it.get("bit_rate") or 0
			cands.append({
				"urls": [u for u in ul if isinstance(u, str)],
				"is_h265": is_h265,
				"gear": str(gear),
				"br": int(br) if isinstance(br, int) or (isinstance(br, str) and br.isdigit()) else 0,
				"rank": _gear_rank(gear),
			})
		if cands:
			cands.sort(key=lambda x: (1 if x["is_h265"] else 0, x["rank"], x["br"]), reverse=True)
			chosen = cands[0]
			best_urls = chosen["urls"]
			meta["codec"] = "h265" if chosen["is_h265"] else "h264"
			meta["gear_name"] = chosen["gear"]
			meta["bitrate"] = chosen["br"]
			# 质量标签 - 改进识别逻辑
			r = chosen["rank"]
			gear_name = chosen["gear"].lower()
			
			# 优先根据gear_name判断，更准确
			if any(x in gear_name for x in ["4k", "uhd"]):
				meta["quality_label"] = "4K"
			elif any(x in gear_name for x in ["1080", "1080p", "1080_1", "lowest_1080", "adapt_lowest_1080"]):
				meta["quality_label"] = "1080P"
			elif any(x in gear_name for x in ["720", "720p"]):
				meta["quality_label"] = "720P"
			elif any(x in gear_name for x in ["540"]):
				meta["quality_label"] = "540P"
			elif any(x in gear_name for x in ["480"]):
				meta["quality_label"] = "480P"
			# 过滤掉480P以下的清晰度
			# elif any(x in gear_name for x in ["360"]):
			# 	meta["quality_label"] = "360P"
			# elif any(x in gear_name for x in ["240"]):
			# 	meta["quality_label"] = "240P"
			# elif any(x in gear_name for x in ["144"]):
			# 	meta["quality_label"] = "144P"
			# 如果gear_name无法识别，再根据rank判断
			elif r >= 4000:
				meta["quality_label"] = "4K"
			elif r >= 1080:
				meta["quality_label"] = "1080P"
			elif r >= 720:
				meta["quality_label"] = "720P"
			elif r >= 540:
				meta["quality_label"] = "540P"
			elif r >= 480:
				meta["quality_label"] = "480P"
			# 过滤掉480P以下的清晰度
			# elif r >= 360:
			# 	meta["quality_label"] = "360P"
			else:
				meta["quality_label"] = "SD"
			return best_urls[:5], meta
		# Fallback：无bit_rate列表，尝试全局play_addr_265 > play_addr
		urls: List[str] = []
		pa265 = video_dict.get("play_addr_265") if isinstance(video_dict.get("play_addr_265"), dict) else None
		if isinstance(pa265, dict):
			lst2 = pa265.get("url_list")
			if isinstance(lst2, list):
				urls.extend([u for u in lst2 if isinstance(u, str)])
		if not urls:
			pa = video_dict.get("play_addr") if isinstance(video_dict.get("play_addr"), dict) else None
			if isinstance(pa, dict):
				lst = pa.get("url_list")
				if isinstance(lst, list):
					urls.extend([u for u in lst if isinstance(u, str)])
		if urls:
			meta["codec"] = "h265" if pa265 else "h264"
			return urls[:5], meta
		return [], meta

	urls: List[str] = []
	meta: Dict[str, Any] = {"codec": "", "gear_name": "", "bitrate": 0, "quality_label": ""}
	if video:
		urls, meta = _select_best(video)

	page_url = f"https://www.douyin.com/video/{aweme_id}" if aweme_id else ""
	return {
		"aweme_id": aweme_id,
		"title": title,
		"author": author,
		"page_url": page_url,
		"download_urls": urls[:5],
		"codec": meta.get("codec", ""),
		"gear_name": meta.get("gear_name", ""),
		"bitrate": meta.get("bitrate", 0),
		"quality_label": meta.get("quality_label", ""),
	}


def parse_video_page(page) -> Optional[Dict]:
	data_text = page.evaluate('''() => {
		const rd = document.querySelector('#RENDER_DATA');
		if (rd && rd.textContent) return decodeURIComponent(rd.textContent);
		const ss = document.querySelector('#SIGI_STATE');
		if (ss && ss.textContent) return ss.textContent;
		return null;
	}''')
	parsed = safe_json_parse(data_text)
	if parsed is None:
		return None
	aweme = deep_find_aweme(parsed)
	if not aweme:
		return None
	return extract_video_info(aweme)


def download_video(session: requests.Session, url_list: List[str], out_dir: Path, aweme_id: str, title: str) -> Path:
	ensure_dir(out_dir)
	base = f"{aweme_id}_{sanitize_filename(title)}"
	out_path = out_dir / f"{base}.mp4"
	headers = {
		"Referer": "https://www.douyin.com/",
		"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
	}
	for u in url_list:
		try:
			with session.get(u, headers=headers, timeout=REQUEST_TIMEOUT, stream=True) as r:
				r.raise_for_status()
				with open(out_path, "wb") as f:
					for chunk in r.iter_content(chunk_size=1024 * 512):
						if chunk:
							f.write(chunk)
			print(f"已下载: {out_path.name}")
			return out_path
		except Exception as e:
			print(f"直链失败，切换下一个: {e}")
	raise RuntimeError("所有播放地址均下载失败")


def export_list(items: List[Dict], export_dir: Path, keyword: str) -> None:
	ensure_dir(export_dir)
	csv_path = export_dir / f"{keyword}_videos.csv"
	with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
		writer = csv.DictWriter(f, fieldnames=["aweme_id", "author", "title", "page_url", "download_path"])
		writer.writeheader()
		for r in items:
			writer.writerow({k: r.get(k, "") for k in ["aweme_id", "author", "title", "page_url", "download_path"]})
	print(f"清单已导出: {csv_path.name}")


def load_cookies_if_any(context) -> None:
	cookies_path = Path(__file__).with_name(COOKIES_FILE)
	if not cookies_path.exists():
		return
	try:
		cookies = json.load(cookies_path.open("r", encoding="utf-8"))
		if isinstance(cookies, dict) and "cookies" in cookies:
			cookies = cookies["cookies"]
		if not isinstance(cookies, list):
			return
		prepared = []
		for c in cookies:
			if not isinstance(c, dict) or "name" not in c or "value" not in c:
				continue
			cookie = dict(c)
			if "domain" not in cookie and "url" not in cookie:
				cookie["url"] = "https://www.douyin.com"
			if "path" not in cookie:
				cookie["path"] = "/"
			prepared.append(cookie)
		if prepared:
			context.add_cookies(prepared)
			print(f"已注入 {len(prepared)} 条Cookie")
	except Exception as e:
		print("注入Cookie失败:", e)


# --- 辅助：验证码/就绪/接口等待（提前定义，避免未定义） ---

def maybe_wait_for_verify(page) -> None:
	try:
		text = page.evaluate('() => document.body ? document.body.innerText || "" : ""') or ""
		if any(k in text for k in ["验证", "安全验证", "captcha", "verify"]):
			print("检测到安全验证，请在浏览器中完成验证，完成后回到终端按回车继续…")
			try:
				input()
			except Exception:
				pass
	except Exception:
		pass


def wait_for_prerender_ready(page, timeout_ms: int = 15000) -> bool:
	try:
		page.wait_for_function(
			"() => { const rd = document.querySelector('#RENDER_DATA'); if (rd && rd.textContent) return true; const ss = document.querySelector('#SIGI_STATE'); if (ss && ss.textContent) return true; return false; }",
			timeout=timeout_ms,
		)
		return True
	except Exception:
		return False


def wait_for_aweme_detail_json(page, timeout_ms: int = 15000) -> Optional[Dict]:
	try:
		resp = page.wait_for_response(lambda r: "/aweme/" in r.url and "/aweme/detail" in r.url and r.status == 200, timeout=timeout_ms)
		text = resp.text()
		parsed = safe_json_parse(text)
		return parsed if isinstance(parsed, dict) else None
	except Exception:
		return None


# --- 播放与网络捕获兜底 ---

def try_click_play(page) -> None:
	try:
		# 常见播放按钮
		locators = [
			'button[aria-label*="播"]',
			'.xgplayer-play',
			'.xgplayer .xgplayer-icon-play',
			'[class*="play"]',
		]
		for sel in locators:
			els = page.query_selector_all(sel)
			if els:
				try:
					els[0].click(timeout=1000)
					break
				except Exception:
					pass
		# 直接调video.play()
		page.evaluate('''() => {
			const v = document.querySelector('video');
			if (v) { try { v.muted = true; v.play(); } catch(e) {} }
		}''')
	except Exception:
		pass


def capture_play_urls_via_network(page, wait_ms: int = 12000) -> List[str]:
	urls: List[str] = []
	end = time.time() + (wait_ms / 1000)
	seen = set()
	patterns = ["douyinvod.com", "/aweme/v1/play", "/play/dash/"]
	while time.time() < end:
		try:
			resp = page.wait_for_response(lambda r: any(p in r.url for p in patterns) and r.status == 200, timeout=1000)
			u = resp.url
			if u and u not in seen:
				seen.add(u)
				urls.append(u)
		except Exception:
			pass
	return urls


def get_video_element_srcs(page) -> List[str]:
	try:
		return page.evaluate('''() => {
			const out = [];
			const v = document.querySelector('video');
			if (v && v.src) out.push(v.src);
			const sources = v ? v.querySelectorAll('source') : [];
			sources && sources.forEach(s => { if (s.src) out.push(s.src); });
			return out;
		}''') or []
	except Exception:
		return []


# --- 从 storage_state.json 构造 requests 会话 ---

def session_from_storage_state(state_path: Path) -> requests.Session:
	s = build_requests_session()
	headers = {
		"User-Agent": DEFAULT_UA,
		"Referer": "https://www.douyin.com/",
		"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
	}
	s.headers.update(headers)

	def _load_requests_cookies_from_file(cookies_path: Path) -> int:
		try:
			obj = json.load(cookies_path.open("r", encoding="utf-8"))
			cookies = obj.get("cookies") if isinstance(obj, dict) else obj
			if not isinstance(cookies, list):
				return 0
			count = 0
			for c in cookies:
				if not isinstance(c, dict):
					continue
				name = c.get("name"); value = c.get("value")
				if not name or value is None:
					continue
				domain = c.get("domain") or ".douyin.com"
				path = c.get("path") or "/"
				s.cookies.set(name, value, domain=domain, path=path)
				count += 1
			return count
		except Exception:
			return 0

	loaded = 0
	if state_path.exists():
		try:
			data = json.loads(state_path.read_text(encoding="utf-8"))
			cookies = data.get("cookies") or []
			for c in cookies:
				name = c.get("name"); value = c.get("value")
				if not name or value is None:
					continue
				domain = c.get("domain") or ".douyin.com"
				path = c.get("path") or "/"
				s.cookies.set(name, value, domain=domain, path=path)
			loaded = len(cookies)
			print(f"已从 storage_state 注入 {loaded} 条Cookie到requests会话")
		except Exception as e:
			print("解析 storage_state 失败:", e)

	if loaded == 0:
		cookies_path = Path(__file__).with_name(COOKIES_FILE)
		if cookies_path.exists():
			cnt = _load_requests_cookies_from_file(cookies_path)
			if cnt > 0:
				print(f"已从 cookies.json 注入 {cnt} 条Cookie到requests会话")
				loaded = cnt

	if loaded == 0:
		print("未发现可用Cookie，将使用匿名会话")

	return s


# --- requests 解析视频页 ---

def requests_fetch_page(session: requests.Session, url: str) -> Optional[str]:
	try:
		headers = {
			"User-Agent": session.headers.get("User-Agent", DEFAULT_UA),
			"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
			"Accept-Language": "zh-CN,zh;q=0.9",
			"Cache-Control": "no-cache",
			"Pragma": "no-cache",
			"Referer": "https://www.douyin.com/",
			"Sec-Fetch-Mode": "navigate",
			"Sec-Fetch-Site": "same-origin",
			"Sec-Fetch-Dest": "document",
		}
		r = session.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
		r.raise_for_status()
		return r.text
	except Exception as e:
		print(f"请求失败 {url}: {e}")
		return None


def parse_aweme_from_html(html: str) -> Optional[Dict]:
	if not html:
		return None
	# 尝试定位 RENDER_DATA 或 SIGI_STATE 脚本
	m = re.search(r'id="RENDER_DATA">(.+?)</script>', html, re.S)
	data_text = None
	if m:
		data_text = unquote(m.group(1))
	else:
		m2 = re.search(r'id="SIGI_STATE">(.+?)</script>', html, re.S)
		if m2:
			data_text = m2.group(1)
	parsed = safe_json_parse(data_text)
	if not parsed:
		return None
	return deep_find_aweme(parsed)


# --- 纯 requests 搜索：X-Bogus 可选、msToken、API 分页 ---

def _random_ms_token(length: int = 107) -> str:
	alphabet = string.ascii_letters + string.digits
	return ''.join(random.choice(alphabet) for _ in range(length))


def ensure_ms_token_cookie(session: requests.Session) -> None:
	"""确保session中有msToken cookie，若不存在则生成一个。"""
	try:
		if not session.cookies.get('msToken'):
			val = _random_ms_token()
			session.cookies.set('msToken', val, domain='.douyin.com', path='/')
			print('已设置 msToken Cookie')
	except Exception:
		pass


def generate_signature(qs: str, ua: str) -> str:
	"""生成简单的签名，用于API调用。"""
	try:
		import hashlib
		import base64
		import time
		import random
		
		# 生成时间戳和随机字符串
		timestamp = int(time.time() * 1000)
		random_str = ''.join(random.choices('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=8))
		
		# 组合签名输入
		signature_input = f"{qs}|{ua}|{timestamp}|{random_str}"
		
		# 生成MD5哈希
		md5_hash = hashlib.md5(signature_input.encode('utf-8')).hexdigest()
		
		# 取前16位作为签名
		signature = md5_hash[:16]
		
		# 转换为base64格式（Douyin风格）
		bogus = base64.b64encode(signature.encode('utf-8')).decode('utf-8')
		bogus = bogus.replace('+', '-').replace('/', '_').replace('=', '')
		
		return bogus
	except Exception as e:
		print(f'签名生成失败: {e}')
		return ''


def preheat_session(session: requests.Session) -> None:
	try:
		ua = session.headers.get('User-Agent', DEFAULT_UA)
		headers = {
			'User-Agent': ua,
			'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
			'Accept-Language': 'zh-CN,zh;q=0.9',
			'Referer': 'https://www.douyin.com/',
		}
		r = session.get('https://www.douyin.com/', headers=headers, timeout=REQUEST_TIMEOUT)
		r.raise_for_status()
		if session.cookies.get('ttwid') or session.cookies.get('s_v_web_id'):
			print('已预热会话，获取环境Cookie')
	except Exception as e:
		print('预热失败:', e)


def log_cookie_diagnostics(session: requests.Session) -> None:
	try:
		flags = {
			'ttwid': bool(session.cookies.get('ttwid')),
			's_v_web_id': bool(session.cookies.get('s_v_web_id')),
			'msToken': bool(session.cookies.get('msToken')),
		}
		fmt = lambda b: '√' if b else '×'
		print(f"Cookie检查: ttwid={fmt(flags['ttwid'])}, s_v_web_id={fmt(flags['s_v_web_id'])}, msToken={fmt(flags['msToken'])}")
	except Exception:
		pass


def _build_search_params(keyword: str, cursor: int, count: int = 20, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
	# 这些参数基于 web 端调用，可能随时间调整；若签名可用，命中率更高
	params = {
		'aid': '6383',
		'device_platform': 'webapp',
		'channel': 'channel_pc_web',
		'keyword': keyword,
		'q_tab': 'video',
		'from_page': 'search_result',
		'search_source': 'guide_search',
		# 排序类型：0=综合排序, 1=最新发布, 2=最多点赞, 3=最多评论, 4=最多分享
		'sort_type': 0,
		# 发布时间：0=不限, 1=一天内, 7=一周内, 182=半年内
		'publish_time': 0,
		# 视频时长：0=不限, 1=1分钟以下, 2=1-3分钟, 3=3-5分钟, 4=5分钟以上
		'duration': 0,
		'count': count,
		'offset': cursor,
		'insert_ads': 0,
		'pc_client_type': 1,
		'version_code': '180800',
	}
	if isinstance(extra, dict):
		for k, v in extra.items():
			if v is not None and v != '':
				params[k] = v
	return params


def _append_x_bogus_if_any(url: str, params: Dict[str, Any], ua: str, signer) -> str:
	try:
		qs = urlencode(params, doseq=True)
		# 直接生成签名
		xb = generate_signature(qs, ua)
		if xb:
			sep = '&' if ('?' in url) else '?'
			return f"{url}{sep}{qs}&X-Bogus={xb}"
		# 无签名直接拼接
		sep = '&' if ('?' in url) else '?'
		return f"{url}{sep}{qs}"
	except Exception:
		sep = '&' if ('?' in url) else '?'
		return f"{url}{sep}{urlencode(params, doseq=True)}"


def _append_a_bogus_if_any(url: str, params: Dict[str, Any], ua: str, signer) -> str:
	try:
		qs = urlencode(params, doseq=True)
		if signer:
			ab = signer(qs, ua)
			if ab:
				sep = '&' if ('?' in url) else '?'
				return f"{url}{sep}{qs}&a_bogus={ab}"
		sep = '&' if ('?' in url) else '?'
		return f"{url}{sep}{qs}"
	except Exception:
		sep = '&' if ('?' in url) else '?'
		return f"{url}{sep}{urlencode(params, doseq=True)}"


def api_search_item_once(session: requests.Session, keyword: str, offset: int, count: int, signer, extra_params: Optional[Dict[str, Any]] = None, include_filters: bool = False) -> Optional[Dict]:
	params: Dict[str, Any] = {
		'device_platform': 'webapp',
		'aid': '6383',
		'channel': 'channel_pc_web',
		'search_channel': 'aweme_video_web',
		'enable_history': 1,
		'keyword': keyword,
		'search_source': 'guide_search',
		'query_correct_type': 1,
		'is_filter_search': 0,
		'from_group_id': '',
		'offset': offset,
		'count': count,
		'need_filter_settings': 1 if include_filters else 0,
		'list_type': 'single',
		'pc_client_type': 1,
		'support_h265': 1,
		'support_dash': 1,
		'update_version_code': '170400',
		'version_code': '170400',
		'version_name': '17.4.0',
		'pc_libra_divert': 'Windows',
		'cpu_core_num': str(os.cpu_count() or 8),
		# 补充浏览器环境参数，提升返回过滤器概率
		'cookie_enabled': 'true',
		'screen_width': '2048',
		'screen_height': '1152',
		'browser_language': 'zh-CN',
		'browser_platform': 'Win32',
		'browser_name': 'Edge',
		'browser_version': '139.0.0.0',
		'browser_online': 'true',
		'engine_name': 'Blink',
		'engine_version': '139.0.0.0',
		'os_name': 'Windows',
		'os_version': '10',
		'device_memory': '8',
		'platform': 'PC',
		'downlink': '10',
		'effective_type': '4g',
		'round_trip_time': '50',
	}
	if isinstance(extra_params, dict):
		for k, v in extra_params.items():
			if v is not None and v != '':
				params[k] = v
	# 注入 cookies 衍生参数（若存在）
	ms = session.cookies.get('msToken')
	if ms:
		params['msToken'] = ms
	uif = session.cookies.get('UIFID') or session.cookies.get('UIFID_TEMP')
	if uif:
		params['uifid'] = uif
	ua = session.headers.get('User-Agent', DEFAULT_UA)
	full_url = _append_a_bogus_if_any(SEARCH_ITEM_API_URL, params, ua, signer)
	
	headers = {
		'Accept': 'application/json, text/plain, */*',
		'User-Agent': ua,
		'Referer': f"https://www.douyin.com/search/{quote(keyword)}?q_tab=video&type=video",
	}
	try:
		r = session.get(full_url, headers=headers, timeout=REQUEST_TIMEOUT)
		r.raise_for_status()
		parsed = safe_json_parse(r.text)
		return parsed if isinstance(parsed, dict) else None
	except Exception as e:
		print('search/item 接口失败:', e)
		return None


def extract_categories_from_item_response(resp: Dict[str, Any]) -> List[Dict[str, Any]]:
	"""从 /search/item 响应中提取分类选项，返回 [{name, extra_params}]。"""
	choices: List[Dict[str, Any]] = []
	keep_param_names = {"type", "category", "cate", "sort_type", "publish_time", "duration", "filter_duration"}

	def add_choice(label: str, param_name: str, value: Any):
		if not label or not param_name:
			return
		if param_name not in keep_param_names:
			return
		choices.append({"name": str(label), "extra_params": {param_name: value}})

	def walk(o: Any):
		if isinstance(o, dict):
			# 常见结构：{"param": "category", "values": [{"text":"美食","value":"food"}, ...]}
			param_name = None
			if isinstance(o.get('param'), str):
				param_name = o.get('param')
			elif isinstance(o.get('key'), str):
				param_name = o.get('key')
			elif isinstance(o.get('filter_key'), str):
				param_name = o.get('filter_key')
			vals = o.get('values') or o.get('options') or o.get('list') or o.get('items')
			if param_name and isinstance(vals, list):
				for it in vals:
					if not isinstance(it, dict):
						continue
					label = it.get('text') or it.get('name') or it.get('label') or it.get('desc')
					val = it.get('value') or it.get('val') or it.get('id') or it.get('option_value') or it.get('param_value')
					add_choice(label, param_name, val)
			for v in o.values():
				if isinstance(v, (dict, list)):
					walk(v)
		elif isinstance(o, list):
			for it in o:
				if isinstance(it, (dict, list)):
					walk(it)

	walk(resp)
	# 去重
	seen = set()
	result: List[Dict[str, Any]] = []
	for c in choices:
		key = (c.get('name'), tuple(sorted(c.get('extra_params', {}).items())))
		if key in seen:
			continue
		seen.add(key)
		result.append(c)
	return result


def extract_categories_from_doodle_config(resp: Dict[str, Any]) -> List[Dict[str, Any]]:
	"""优先从 resp.global_doodle_config 精准提取分类。
	常见结构：
	- global_doodle_config.filter_settings / filters / chips / tabs
	- 每项包含 filter_key/param/key + values/options/list/items
	- guide_search_words 包含推荐的内容分类
	"""
	root = resp.get('global_doodle_config') if isinstance(resp, dict) else None
	if not isinstance(root, dict):
		return []
	
	
	
	keep_param_names = {"type", "category", "cate", "sort_type", "publish_time", "duration", "filter_duration"}
	choices: List[Dict[str, Any]] = []

	def add_choice(label: Any, p: Any, val: Any):
		try:
			name = (label or '').strip() if isinstance(label, str) else str(label)
			param = str(p) if p is not None else ''
			if not name or not param or param not in keep_param_names:
				return
			choices.append({"name": name, "extra_params": {param: val}})
		except Exception as e:
			return

	# 新增：专门解析 filter_settings 结构
	def parse_filter_settings(filter_settings: Any):
		if not isinstance(filter_settings, list):
			return
		
		
		
		for idx, filter_item in enumerate(filter_settings):
			if not isinstance(filter_item, dict):
				continue
			
			
			
			# 查找 filter_key 或 param 作为参数名
			param_name = filter_item.get('filter_key') or filter_item.get('param') or filter_item.get('key')
			if not param_name:
				# 如果没有找到标准参数名，尝试从其他字段推断
				if 'name' in filter_item:
					param_name = filter_item['name']
				elif 'type' in filter_item:
					param_name = filter_item['type']
				else:
					
					continue
			
			
			
			# 查找 items 列表
			items = filter_item.get('items')
			if not isinstance(items, list):
				# 尝试其他可能的字段名
				items = filter_item.get('values') or filter_item.get('options') or filter_item.get('list') or filter_item.get('tabs') or filter_item.get('chips')
				if not isinstance(items, list):
					
					continue
			
			
			
			# 遍历 items 中的选项
			for item_idx, item in enumerate(items):
				if not isinstance(item, dict):
					continue
				
				
				
				# 获取标签和值
				label = item.get('title') or item.get('text') or item.get('name') or item.get('label') or item.get('desc')
				val = item.get('value') or item.get('val') or item.get('id') or item.get('option_value') or item.get('param_value')
				
				# 修复：对于时长筛选，即使值为None或空字符串也要添加（表示"不限"）
				if label:
					if val is not None or param_name == 'filter_duration':
						# 如果值为None且是时长筛选，使用特殊值
						if val is None and param_name == 'filter_duration':
							val = '0'  # 使用'0'表示"不限"
						
					add_choice(label, param_name, val)
					
				else:
					continue
			else:
				continue

	def walk(o: Any, path: str = ""):
		if isinstance(o, dict):
			param_name = None
			# 按优先级查找参数名
			if isinstance(o.get('name'), str):
				param_name = o.get('name')
			elif isinstance(o.get('filter_key'), str):
				param_name = o.get('filter_key')
			elif isinstance(o.get('param'), str):
				param_name = o.get('param')
			elif isinstance(o.get('key'), str):
				param_name = o.get('key')
			elif isinstance(o.get('type'), str):
				param_name = o.get('type')
			
			# 查找选项列表
			vals = o.get('items') or o.get('values') or o.get('options') or o.get('list') or o.get('tabs') or o.get('chips')
			if param_name and isinstance(vals, list):
				for it in vals:
					if not isinstance(it, dict):
						continue
					# 按优先级查找标签
					label = it.get('title') or it.get('text') or it.get('name') or it.get('label') or it.get('desc')
					# 按优先级查找值
					val = it.get('value') or it.get('val') or it.get('id') or it.get('option_value') or it.get('param_value')
					if label and val is not None:
						add_choice(label, param_name, val)
			
			# 递归遍历其他字段
			for k, v in o.items():
				if isinstance(v, (dict, list)):
					walk(v, f"{path}.{k}" if path else k)
		elif isinstance(o, list):
			for i, it in enumerate(o):
				if isinstance(it, (dict, list)):
					walk(it, f"{path}[{i}]")

	# 首先专门解析 filter_settings
	if 'filter_settings' in root:
	
		parse_filter_settings(root['filter_settings'])
	
	# 然后进行通用递归解析
	walk(root)
	
	# 新增：解析 guide_search_words 作为内容分类
	guide_words = resp.get('guide_search_words', [])
	if isinstance(guide_words, list) and guide_words:
		for item in guide_words:
			if isinstance(item, dict):
				word = item.get('word', '').strip()
				if word:
					# 这些是内容分类，不是排序/时间过滤
					choices.append({
						"name": word, 
						"extra_params": {"keyword": word},  # 用新的关键词替换
						"type": "content_category"
					})
	
	# 去重
	seen = set()
	res: List[Dict[str, Any]] = []
	for c in choices:
		key = (c.get('name'), tuple(sorted(c.get('extra_params', {}).items())))
		if key in seen:
			continue
		seen.add(key)
		res.append(c)
	
	
	return res


def requests_fetch_awemes_via_item_api(session: requests.Session, keyword: str, target_count: int, extra_params: Optional[Dict[str, Any]] = None) -> Tuple[List[Dict], List[Dict]]:
	"""返回 (awemes, categories)。第一次调用包含 need_filter_settings=1，后续分页不带。"""
	ensure_ms_token_cookie(session)
	# 不再需要signer，直接传递None
	awemes: List[Dict] = []
	categories: List[Dict] = []
	seen_ids = set()
	offset = 0
	page_size = 20
	first = True
	no_progress_rounds = 0
	while len(awemes) < target_count and no_progress_rounds < 3:
		resp = api_search_item_once(session, keyword, offset, page_size, None, extra_params=extra_params, include_filters=first)
		added = 0
		if isinstance(resp, dict):
			if first:
				try:
					categories = extract_categories_from_item_response(resp) or []
				except Exception:
					categories = []
			for a in extract_awemes_from_parsed(resp):
				if isinstance(a, dict):
					aweme_id = a.get('aweme_id') or a.get('aweme_id_str') or a.get('group_id')
					if aweme_id and aweme_id not in seen_ids:
						seen_ids.add(aweme_id)
						awemes.append(a)
						added += 1
		if added == 0:
			no_progress_rounds += 1
		else:
			no_progress_rounds = 0
		offset += page_size
		first = False
		time.sleep(0.4)
	return awemes[:target_count], categories


def api_search_once(session: requests.Session, keyword: str, cursor: int, count: int, signer, extra_params: Optional[Dict[str, Any]] = None) -> Optional[Dict]:
	params = _build_search_params(keyword, cursor, count, extra=extra_params)
	ua = session.headers.get('User-Agent', DEFAULT_UA)
	full_url = _append_x_bogus_if_any(SEARCH_API_URL, params, ua, signer)
	headers = {
		'Accept': 'application/json, text/plain, */*',
		'User-Agent': ua,
		'Referer': f"https://www.douyin.com/search/{quote(keyword)}?q_tab=video&type=video",
	}
	try:
		r = session.get(full_url, headers=headers, timeout=REQUEST_TIMEOUT)
		r.raise_for_status()
		parsed = safe_json_parse(r.text)
		return parsed if isinstance(parsed, dict) else None
	except Exception as e:
		print('搜索接口失败:', e)
		return None


def requests_fetch_awemes_via_api(session: requests.Session, keyword: str, target_count: int, extra_params: Optional[Dict[str, Any]] = None) -> List[Dict]:
	ensure_ms_token_cookie(session)
	# 不再需要signer，直接传递None
	awemes: List[Dict] = []
	seen_ids = set()
	cursor = 0
	page_size = 20
	no_progress_rounds = 0
	while len(awemes) < target_count and no_progress_rounds < 3:
		resp = api_search_once(session, keyword, cursor, page_size, None, extra_params=extra_params)
		added = 0
		if isinstance(resp, dict):
			for a in extract_awemes_from_parsed(resp):
				if isinstance(a, dict):
					aweme_id = a.get('aweme_id') or a.get('aweme_id_str') or a.get('group_id')
					if aweme_id and aweme_id not in seen_ids:
						seen_ids.add(aweme_id)
						awemes.append(a)
						added += 1
		if added == 0:
			no_progress_rounds += 1
		else:
			no_progress_rounds = 0
		cursor += page_size
		time.sleep(0.5)
	return awemes[:target_count]


def api_aweme_detail(session: requests.Session, aweme_id: str, signer) -> Optional[Dict]:
	params = {
		'aid': '6383',
		'device_platform': 'webapp',
		'aweme_id': aweme_id,
	}
	ua = session.headers.get('User-Agent', DEFAULT_UA)
	full_url = _append_x_bogus_if_any(DETAIL_API_URL, params, ua, signer)
	headers = {
		'Accept': 'application/json, text/plain, */*',
		'User-Agent': ua,
		'Referer': f"https://www.douyin.com/video/{aweme_id}",
	}
	try:
		r = session.get(full_url, headers=headers, timeout=REQUEST_TIMEOUT)
		r.raise_for_status()
		parsed = safe_json_parse(r.text)
		return parsed if isinstance(parsed, dict) else None
	except Exception as e:
		print('详情接口失败:', e)
		return None


def extract_aweme_ids_from_search_html(html: str) -> List[str]:
	if not html:
		return []
	m = re.search(r'id="RENDER_DATA">(.+?)</script>', html, re.S)
	data_text = None
	if m:
		data_text = unquote(m.group(1))
	else:
		m2 = re.search(r'id="SIGI_STATE">(.+?)</script>', html, re.S)
		if m2:
			data_text = m2.group(1)
	parsed = safe_json_parse(data_text)
	if not parsed:
		return []
	ids: List[str] = []
	def _walk(o: Any):
		if isinstance(o, dict):
			vid = o.get('aweme_id') or o.get('aweme_id_str') or o.get('group_id')
			if isinstance(vid, str):
				ids.append(vid)
			for v in o.values():
				if isinstance(v, (dict, list)):
					_walk(v)
		elif isinstance(o, list):
			for it in o:
				if isinstance(it, (dict, list)):
					_walk(it)
	_walk(parsed)
	# 去重
	seen = set()
	res = []
	for i in ids:
		if i and i not in seen:
			seen.add(i)
			res.append(i)
	return res


def extract_search_categories_from_html(html: str) -> List[Dict[str, str]]:
	"""从搜索页 HTML 的 RENDER_DATA/SIGI_STATE 中解析分类 chips。
	返回：[{"name": 名称, "href": url}]
	"""
	if not html:
		return []
	
	chips: List[Dict[str, str]] = []
	
	# 方法1: 从RENDER_DATA/SIGI_STATE解析
	m = re.search(r'id="RENDER_DATA">(.+?)</script>', html, re.S)
	data_text = None
	if m:
		data_text = unquote(m.group(1))
	else:
		m2 = re.search(r'id="SIGI_STATE">(.+?)</script>', html, re.S)
		if m2:
			data_text = m2.group(1)
	
	if data_text:
		parsed = safe_json_parse(data_text)
		if parsed:
			def _walk(o: Any):
				if isinstance(o, dict):
					# 经验：可能存在形如 tabs/chips 节点，含 name/title 与 href/link/url
					name = o.get('name') or o.get('title') or o.get('tab_name')
					href = o.get('href') or o.get('link') or o.get('url')
					if isinstance(name, str) and isinstance(href, str):
						chips.append({"name": name.strip(), "href": href})
					for v in o.values():
						if isinstance(v, (dict, list)):
							_walk(v)
				elif isinstance(o, list):
					for it in o:
						if isinstance(it, (dict, list)):
							_walk(it)
			_walk(parsed)
	
	# 方法2: 直接从HTML中查找分类chips（针对内容类型分类）
	# 查找类似 <div class="...">跳舞</div> 或 <span>图片</span> 等分类标签
	category_patterns = [
		r'<[^>]*class="[^"]*tab[^"]*"[^>]*>([^<]+)</[^>]*>',  # 查找tab类
		r'<[^>]*class="[^"]*chip[^"]*"[^>]*>([^<]+)</[^>]*>',  # 查找chip类
		r'<[^>]*class="[^"]*category[^"]*"[^>]*>([^<]+)</[^>]*>',  # 查找category类
		r'<[^>]*class="[^"]*filter[^"]*"[^>]*>([^<]+)</[^>]*>',  # 查找filter类
		r'<[^>]*class="[^"]*btn[^"]*"[^>]*>([^<]+)</[^>]*>',  # 查找btn类
	]
	
	# 常见的内容类型关键词
	content_keywords = [
		'跳舞', '舞蹈', '热舞', '街舞', '民族舞', '现代舞',
		'图片', '照片', '壁纸', '头像', '写真',
		'电影', '视频', '短片', 'MV', '音乐',
		'变装', 'cosplay', '角色扮演',
		'动漫', '二次元', '卡通',
		'美食', '旅游', '时尚', '美妆',
		'全部', '综合', '推荐'
	]
	
	for pattern in category_patterns:
		matches = re.findall(pattern, html, re.I)
		for match in matches:
			match = match.strip()
			if match and any(keyword in match for keyword in content_keywords):
				# 构造对应的URL参数
				if '跳舞' in match or '舞蹈' in match:
					href = '?type=video&q_tab=video&category=dance'
				elif '图片' in match or '照片' in match:
					href = '?type=image&q_tab=image'
				elif '电影' in match or '视频' in match:
					href = '?type=video&q_tab=video'
				elif '壁纸' in match:
					href = '?type=image&q_tab=image&category=wallpaper'
				elif '变装' in match or 'cosplay' in match:
					href = '?type=video&q_tab=video&category=cosplay'
				elif '动漫' in match or '二次元' in match:
					href = '?type=video&q_tab=video&category=anime'
				elif '美食' in match:
					href = '?type=video&q_tab=video&category=food'
				elif '旅游' in match:
					href = '?type=video&q_tab=video&category=travel'
				elif '时尚' in match or '美妆' in match:
					href = '?type=video&q_tab=video&category=fashion'
				else:
					href = '?type=video&q_tab=video'
				
				chips.append({"name": match, "href": href})
	
	# 去重并过滤明显非分类的链接
	seen = set()
	res: List[Dict[str, str]] = []
	for c in chips:
		name = c.get('name') or ''
		href = c.get('href') or ''
		if not name or not href:
			continue
		key = (name, href)
		if key in seen:
			continue
		seen.add(key)
		# 仅保留与搜索相关的 tab/chip（包含 q_tab/type/category 等参数较多）
		if any(k in href for k in ['q_tab', 'type', 'category', 'cate', 'tab']):
			res.append({"name": name, "href": href})
	
	print(f'HTML分类解析结果: 找到 {len(chips)} 个原始分类，过滤后 {len(res)} 个有效分类')
	return res


def normalize_category_hyperlink(base_search_url: str, href: str) -> str:
	"""将 chip 的 href 归一化为绝对 URL。
	base_search_url: 原始搜索页 URL（https://www.douyin.com/search/xxx?...）
	"""
	if not href:
		return base_search_url
	if href.startswith('http'):
		return href
	if href.startswith('/'):
		return 'https://www.douyin.com' + href
	# 形如 ?q_tab=video 之类
	sep = '&' if ('?' in base_search_url) else '?'
	return f"{base_search_url}{sep}{href.lstrip('?')}"


def parse_category_params_from_url(url: str) -> Dict[str, Any]:
	"""从分类 URL 中解析我们关心的参数（q_tab/type/category等）。"""
	try:
		qs = url.split('?', 1)[1] if '?' in url else ''
		params = {k: v[0] if isinstance(v, list) and v else v for k, v in parse_qs(qs).items()}
		return params
	except Exception:
		return {}


def build_csv_writer(csv_path: Path):
	ensure_dir(csv_path.parent)
	f = csv_path.open("w", newline="", encoding="utf-8-sig")
	writer = csv.DictWriter(
		f,
		fieldnames=[
			"aweme_id",
			"author",
			"title",
			"page_url",
			"download_path",
			"codec",
			"gear_name",
			"bitrate",
			"quality_label",
		],
	)
	writer.writeheader()
	return f, writer


def parse_one_with_page(page, url: str) -> Optional[Dict]:
	"""使用已登录的浏览器页解析单个视频页，返回包含直链的info。"""
	try:
		page.goto(url, wait_until="domcontentloaded", timeout=60000)
		maybe_wait_for_verify(page)
		ready = wait_for_prerender_ready(page, timeout_ms=12000)
		info = None
		if ready:
			info = parse_video_page(page)
		if not info or not info.get("download_urls"):
			parsed_detail = wait_for_aweme_detail_json(page, timeout_ms=12000)
			if isinstance(parsed_detail, dict):
				aweme = deep_find_aweme(parsed_detail)
				if aweme:
					info = extract_video_info(aweme)
		if not info or not info.get("download_urls"):
			try_click_play(page)
			net_urls = capture_play_urls_via_network(page, wait_ms=12000)
			if net_urls:
				info = info or {"aweme_id": extract_aweme_id_from_url(url), "title": "", "author": "", "page_url": url, "download_urls": []}
				info["download_urls"] = (info.get("download_urls") or []) + net_urls
		if not info or not info.get("download_urls"):
			el_srcs = get_video_element_srcs(page)
			if el_srcs:
				info = info or {"aweme_id": extract_aweme_id_from_url(url), "title": "", "author": "", "page_url": url, "download_urls": []}
				info["download_urls"] = (info.get("download_urls") or []) + el_srcs
		if info:
			info["page_url"] = url
		return info
	except Exception:
		return None


# --- 从网络响应捕获搜索结果 ---

def extract_awemes_from_parsed(parsed: Any) -> List[Dict]:
	"""从任意JSON对象中提取 aweme 列表（aweme_list 或 aweme_info）。"""
	awemes: List[Dict] = []
	if isinstance(parsed, dict):
		if isinstance(parsed.get("aweme_list"), list):
			awemes.extend([x for x in parsed.get("aweme_list") if isinstance(x, dict)])
		data = parsed.get("data")
		if isinstance(data, dict) and isinstance(data.get("aweme_list"), list):
			awemes.extend([x for x in data.get("aweme_list") if isinstance(x, dict)])
		# 递归包含 aweme_info
		stack = [parsed]
		while stack:
			cur = stack.pop()
			if isinstance(cur, dict):
				ai = cur.get("aweme_info")
				if isinstance(ai, dict):
					awemes.append(ai)
				for v in cur.values():
					if isinstance(v, (dict, list)):
						stack.append(v)
			elif isinstance(cur, list):
				for v in cur:
					if isinstance(v, (dict, list)):
						stack.append(v)
	return awemes


def capture_awemes_via_network(page, target_count: int, max_rounds: int = 30) -> List[Dict]:
	"""在搜索页监听网络响应，收集 general/search 的 aweme 列表；达到数量立即停止。"""
	collected: List[Dict] = []
	seen_ids = set()
	done = {"v": False}

	def on_response(resp):
		try:
			if done["v"]:
				return
			url = resp.url
			if "/aweme/" not in url:
				return
			if not any(k in url for k in ["general/search", "module/feed", "tab", "category", "recommend"]):
				return
			if resp.status != 200:
				return
			text = resp.text()
			parsed = safe_json_parse(text)
			if parsed is None:
				return
			for a in extract_awemes_from_parsed(parsed):
				aweme_id = a.get("aweme_id") or a.get("aweme_id_str") or a.get("group_id")
				if not aweme_id or aweme_id in seen_ids:
					continue
				seen_ids.add(aweme_id)
				collected.append(a)
				if len(seen_ids) >= target_count:
					done["v"] = True
					return
		except Exception:
			return

	page.on("response", on_response)
	try:
		for _ in range(max(1, max_rounds)):
			if done["v"] or len(seen_ids) >= target_count:
				break
			page.mouse.wheel(0, 2400)
			time.sleep(0.6)
	finally:
		try:
			page.remove_listener("response", on_response)
		except Exception:
			pass
	# 截断到目标数量
	return collected[:target_count]


def run(keyword: str) -> None:
	export_dir = Path(__file__).with_name(EXPORT_DIR_NAME)
	download_dir = Path(__file__).with_name(DOWNLOADS_DIR_NAME) / sanitize_filename(keyword)
	debug_dir = Path(__file__).with_name(DEBUG_DIR_NAME)
	ensure_dir(export_dir)
	ensure_dir(download_dir)
	ensure_dir(debug_dir)

	state_path = Path(__file__).with_name(STORAGE_STATE_FILE)
	rq = session_from_storage_state(state_path)
	# A) 会话预热，获取 ttwid/s_v_web_id 等 Cookie
	preheat_session(rq)
	# 补充 msToken（部分接口依赖）
	ensure_ms_token_cookie(rq)
	# B) 运行时Cookie自检（便于确认 cookies.json 是否被加载）
	log_cookie_diagnostics(rq)

	# 1) 先拉取分类（不确定数量时只取1条以便拿到过滤器），再提示选择
	parse_results: List[Dict] = []
	awemes: List[Dict] = []
	chosen_extra: Optional[Dict[str, Any]] = None
	# 不再需要signer，直接传递None
	initial_resp = api_search_item_once(rq, keyword, 0, 10, None, extra_params=None, include_filters=True)
	categories: List[Dict] = []
	if isinstance(initial_resp, dict):
		cats1: List[Dict[str, Any]] = []
		cats2: List[Dict[str, Any]] = []
		try:
			cats1 = extract_categories_from_doodle_config(initial_resp) or []
		except Exception:
			cats1 = []
		try:
			cats2 = extract_categories_from_item_response(initial_resp) or []
		except Exception:
			cats2 = []
		# 优先 doodle_config，其次通用扫描，合并去重
		merge_seen = set()
		for lst in (cats1, cats2):
			for c in lst:
				key = (c.get('name'), tuple(sorted((c.get('extra_params') or {}).items())))
				if key in merge_seen:
					continue
				merge_seen.add(key)
				categories.append(c)
	# 如果接口未给出分类，回退 HTML 解析分类 chips
	if not categories:
		search_url_for_cats = DOUYIN_SEARCH_URL_TMPL.format(quote(keyword)) + "?type=video&q_tab=video"
		html_for_cats = requests_fetch_page(rq, search_url_for_cats)
		# 调试日志
		if not html_for_cats:
			print("HTML 分类请求失败或为空")
		else:
			print(f"HTML 长度: {len(html_for_cats)}")
		html_cats = extract_search_categories_from_html(html_for_cats) if html_for_cats else []
		if html_cats:
			built: List[Dict[str, Any]] = []
			for c in html_cats[:20]:
				full_url = normalize_category_hyperlink(search_url_for_cats, c.get('href',''))
				params = parse_category_params_from_url(full_url)
				keys_keep = {"q_tab", "type", "category", "cate", "sort_type", "publish_time", "duration", "filter_duration"}
				extra = {k: v for k, v in params.items() if k in keys_keep}
				if extra:
					built.append({"name": c.get('name',''), "extra_params": extra})
			categories = built
		else:
			print("未从 HTML 解析到分类 chips")
	if categories:
		# 分离内容分类和排序分类
		content_categories = [c for c in categories if c.get('type') == 'content_category']
		filter_categories = [c for c in categories if c.get('type') != 'content_category']
		
		# 第一步：循环选择内容分类，关键词会不断组合
		if content_categories:
			print("发现以下内容分类，可以多次选择组合关键词（输入-1结束选择）：")
			while True:
				print(f"\n当前关键词: {keyword}")
				print("可选内容分类:")
				for idx, c in enumerate(content_categories[:10]):
					print(f"[{idx}] {c.get('name','')}")
				print("[-1] 完成内容分类选择，进入排序选择")
				
				sel = input("内容分类序号: ").strip()
				if sel == "-1":
					break
				elif sel.isdigit():
					si = int(sel)
					if 0 <= si < len(content_categories[:10]):
						chosen_content = content_categories[si]
						new_keyword_part = chosen_content.get('name', '')
						# 组合关键词：原关键词 + 新分类
						if keyword == "美女":  # 初始关键词
							keyword = f"{keyword} {new_keyword_part}"
						else:
							keyword = f"{keyword} {new_keyword_part}"
						print(f"已选择内容分类: {new_keyword_part}")
						print(f"当前组合关键词: {keyword}")
						
						# 重新获取新组合关键词的分类选项
						print(f"正在获取 '{keyword}' 的更多分类选项...")
						content_resp = api_search_item_once(rq, keyword, 0, 10, None, extra_params=None, include_filters=True)
						if isinstance(content_resp, dict):
							content_cats = extract_categories_from_doodle_config(content_resp) or []
							# 更新内容分类列表，排除已选择的
							existing_parts = keyword.split()
							content_categories = []
							filter_categories = []  # 重置筛选分类
							for c in content_cats:
								if c.get('type') == 'content_category':
									word = c.get('name', '')
									# 只添加还未包含的分类
									if word not in existing_parts:
										content_categories.append(c)
								else:
									# 添加筛选分类
									filter_categories.append(c)
							
						
			
							print(f"  总categories: {len(content_cats)} 个")
							print(f"  内容分类: {len(content_categories)} 个")
							print(f"  筛选分类: {len(filter_categories)} 个")
							
							if not content_categories:
								print("没有更多可用的内容分类了")
								break
					else:
						print("序号超出范围，请重新选择")
				else:
					print("请输入有效的序号或-1")
		
		# 第二步：选择排序/过滤分类
		if filter_categories:
			# 按类型分组显示筛选选项
			sort_options = [c for c in filter_categories if 'sort_type' in str(c.get('extra_params', {}))]
			time_options = [c for c in filter_categories if 'publish_time' in str(c.get('extra_params', {}))]
			duration_options = [c for c in filter_categories if 'filter_duration' in str(c.get('extra_params', {}))]
			other_options = [c for c in filter_categories if not any(x in str(c.get('extra_params', {})) for x in ['sort_type', 'publish_time', 'filter_duration'])]
			
						
			
			# 调试统计输出移除
			
			chosen_extra = {}
			
			# 选择排序类型
			if sort_options:
				print(f"\n=== 排序类型选择 ===")
				for idx, c in enumerate(sort_options[:10]):
					param = c.get('extra_params', {})
					sort_type = param.get('sort_type', '')
					print(f"[{idx}] {c.get('name','')} (sort_type={sort_type})")
				sel = input("排序类型序号 (直接回车跳过): ").strip()
				if sel.isdigit():
					si = int(sel)
					if 0 <= si < len(sort_options[:10]):
						chosen_sort = sort_options[si]
						chosen_extra.update(chosen_sort.get('extra_params', {}))
						print(f"已选择排序: {chosen_sort.get('name','')}")
			
			# 选择发布时间
			if time_options:
				print(f"\n=== 发布时间选择 ===")
				for idx, c in enumerate(time_options[:10]):
					param = c.get('extra_params', {})
					publish_time = param.get('publish_time', '')
					print(f"[{idx}] {c.get('name','')} (publish_time={publish_time})")
				sel = input("发布时间序号 (直接回车跳过): ").strip()
				if sel.isdigit():
					si = int(sel)
					if 0 <= si < len(time_options[:10]):
						chosen_time = time_options[si]
						chosen_extra.update(chosen_time.get('extra_params', {}))
						print(f"已选择时间: {chosen_time.get('name','')}")
			
			
			
			# 选择视频时长
			if duration_options:
				print(f"\n=== 视频时长选择 ===")
				for idx, c in enumerate(duration_options[:10]):
					param = c.get('extra_params', {})
					duration = param.get('filter_duration', '')
					print(f"[{idx}] {c.get('name','')} (filter_duration={duration})")
				sel = input("视频时长序号 (直接回车跳过): ").strip()
				if sel.isdigit():
					si = int(sel)
					if 0 <= si < len(duration_options[:10]):
						chosen_duration = duration_options[si]
						chosen_extra.update(chosen_duration.get('extra_params', {}))
						print(f"已选择时长: {chosen_duration.get('name','')}")
			
			# 其他筛选选项
			if other_options:
				print(f"\n=== 其他筛选选项 ===")
				for idx, c in enumerate(other_options[:10]):
					print(f"[{idx}] {c.get('name','')} -> {c.get('extra_params',{})}")
				sel = input("其他选项序号 (直接回车跳过): ").strip()
				if sel.isdigit():
					si = int(sel)
					if 0 <= si < len(other_options[:10]):
						chosen_other = other_options[si]
						chosen_extra.update(chosen_other.get('extra_params', {}))
						print(f"已选择其他: {chosen_other.get('name','')}")
			
			if chosen_extra:
				print(f"最终筛选参数: {chosen_extra}")
			else:
				chosen_extra = None
		else:
			chosen_extra = None
	else:
		print("未获取到可选分类，将直接进入数量输入与抓取流程…")
		chosen_extra = None

	# 2) 选择分类后，再提示输入数量
	cnt_str = input("请输入需要下载的视频数量(整数): ").strip()
	target_count = int(cnt_str) if cnt_str.isdigit() and int(cnt_str) > 0 else 5

	# 3) 按选择的分类与数量抓取
	awemes, _ = requests_fetch_awemes_via_item_api(rq, keyword, target_count, extra_params=chosen_extra)

	# 4) 如果 API 返回的 aweme 带有直链，直接抽取；否则尝试详情接口补齐
	if awemes:
		# 不再需要signer，直接传递None
		for a in awemes:
			info = extract_video_info(a)
			if not info.get('download_urls') and info.get('aweme_id'):
				# 详情接口补齐
				detail = api_aweme_detail(rq, str(info['aweme_id']), None)
				if isinstance(detail, dict):
					aw = deep_find_aweme(detail)
					if isinstance(aw, dict):
						info = extract_video_info(aw)
			if info.get('download_urls'):
				info['page_url'] = f"https://www.douyin.com/video/{info.get('aweme_id','')}"
				# 打印质量信息
				ql = info.get('quality_label') or ''
				codec = info.get('codec') or ''
				gear = info.get('gear_name') or ''
				br = info.get('bitrate') or 0
				print(f"选用清晰度: {ql} codec={codec} gear={gear} bitrate={br}")
				parse_results.append(info)

	# 5) 若不足数量，回退到 HTML 解析（仅首屏/部分）
	if len(parse_results) < target_count:
		remaining = target_count - len(parse_results)
		search_url = DOUYIN_SEARCH_URL_TMPL.format(quote(keyword)) + "?type=video"
		html = requests_fetch_page(rq, search_url)
		ids = extract_aweme_ids_from_search_html(html)[:remaining]
		for vid in ids:
			if len(parse_results) >= target_count:
				break
			page_url = f"https://www.douyin.com/video/{vid}"
			html2 = requests_fetch_page(rq, page_url)
			aw = parse_aweme_from_html(html2) if html2 else None
			if isinstance(aw, dict):
				info = extract_video_info(aw)
				if info.get('download_urls'):
					info['page_url'] = page_url
					parse_results.append(info)

	# 6) 并发下载并写 CSV
	csv_path = export_dir / f"{sanitize_filename(keyword)}_videos.csv"
	csv_file, writer = build_csv_writer(csv_path)
	try:
		def _download_one(i: Dict) -> Optional[Dict]:
			try:
				aweme_id = i.get("aweme_id") or extract_aweme_id_from_url(i.get("page_url", "")) or ""
				path = download_video(rq, i.get("download_urls", []), download_dir, aweme_id, i.get("title") or aweme_id)
				i["download_path"] = str(path)
				return i
			except Exception as e:
				print(f"下载失败: {i.get('page_url')}: {e}")
				return None

		with ThreadPoolExecutor(max_workers=MAX_DOWNLOAD_CONCURRENCY) as ex:
			futs = {ex.submit(_download_one, i): i for i in parse_results[:target_count]}
			for fut in as_completed(futs):
				res = fut.result()
				if not res:
					continue
				writer.writerow({
					"aweme_id": res.get("aweme_id", ""),
					"author": res.get("author", ""),
					"title": res.get("title", ""),
					"page_url": res.get("page_url", ""),
					"download_path": res.get("download_path", ""),
					"codec": res.get("codec", ""),
					"gear_name": res.get("gear_name", ""),
					"bitrate": res.get("bitrate", ""),
					"quality_label": res.get("quality_label", ""),
				})
	finally:
		csv_file.close()
	print(f"CSV导出完成: {csv_path}")


if __name__ == "__main__":
	kw = input("请输入关键词: ").strip()
	run(kw)
	print("完成。")
