import time
from pathlib import Path
from typing import Dict, List, Tuple

import requests
import sys

UC_AVAILABLE = True
try:
    import undetected_chromedriver as uc  # type: ignore
    # 修复 uc 在退出阶段偶发 WinError 6：用安全的 __del__ 替换
    try:
        def _safe_del(self):
            try:
                self.quit()
            except Exception:
                pass
        # 全局替换一次，避免解释器关闭阶段触发原实现的 sleep 导致 OSError
        if getattr(uc, "Chrome", None) and getattr(uc.Chrome, "__del__", None):
            uc.Chrome.__del__ = _safe_del  # type: ignore[attr-defined]
    except Exception:
        pass
except Exception as exc:
    # 在 Py 3.12 上常见 distutils 缺失导致导入失败；自动降级为原生 Selenium
    UC_AVAILABLE = False
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options as ChromeOptions


OUTPUT_PATH = Path(__file__).parent / "cookies.txt"
RELATED_DOMAINS = {"bilibili.com", ".bilibili.com", "hdslb.com", ".hdslb.com"}


CRITICAL_COOKIE_NAMES = {"SESSDATA", "DedeUserID", "bili_jct"}


def _cookies_list_to_dict(cookies: List[Dict]) -> Dict[str, str]:
    cookie_map: Dict[str, str] = {}
    for c in cookies:
        name = c.get("name")
        value = c.get("value")
        if not name:
            continue
        cookie_map[name] = value or ""
    return cookie_map


def _to_netscape_rows(cookies: List[Dict]) -> List[Tuple[str, str, str, str, int, str, str]]:
    rows: List[Tuple[str, str, str, str, int, str, str]] = []
    for c in cookies:
        domain = (c.get("domain") or "").strip()
        if not domain:
            continue
        host = domain.lower()
        if not any(host == d or host.endswith(d) for d in RELATED_DOMAINS):
            continue
        include_subdomains = "TRUE" if domain.startswith(".") else "FALSE"
        path = c.get("path") or "/"
        secure = "TRUE" if c.get("secure") else "FALSE"
        expires = int(c.get("expiry", 0) or 0)
        name = c.get("name") or ""
        value = c.get("value") or ""
        rows.append((domain, include_subdomains, path, secure, expires, name, value))
    # 去重
    dedup = {}
    for r in rows:
        k = (r[0], r[2], r[5])
        dedup[k] = r
    return list(dedup.values())


def _write_netscape(rows: List[Tuple[str, str, str, str, int, str, str]], output_path: Path) -> None:
    header = [
        "# Netscape HTTP Cookie File",
        "# Generated via Selenium (undetected-chromedriver)",
        f"# {time.strftime('%Y-%m-%d %H:%M:%S')}",
        "",
    ]
    lines = header + [
        f"{d}\t{sub}\t{p}\t{sec}\t{exp}\t{name}\t{val}" for d, sub, p, sec, exp, name, val in rows
    ]
    output_path.write_text("\n".join(lines), encoding="utf-8")


def _check_is_login(cookie_dict: Dict[str, str], user_agent: str | None = None) -> Tuple[bool, int | None]:
    # 首先基于关键 Cookie 名进行快速判断
    if any(name in cookie_dict for name in CRITICAL_COOKIE_NAMES):
        # 进一步用接口确认（如果接口异常，也视作已登录以避免误判）
        pass

    headers = {
        "User-Agent": user_agent or (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
        ),
        "Referer": "https://www.bilibili.com/",
        "Origin": "https://www.bilibili.com",
        "Accept": "application/json, text/plain, */*",
    }

    with requests.Session() as s:
        for k, v in cookie_dict.items():
            s.cookies.set(k, v, domain=".bilibili.com")
        try:
            resp = s.get("https://api.bilibili.com/x/web-interface/nav", timeout=10, headers=headers)
            data = resp.json()
            flag = bool(data.get("data", {}).get("isLogin"))
            uid = data.get("data", {}).get("mid")
            if flag:
                return True, uid
            # 接口未返回登录，但存在关键 Cookie，视作登录成功（兼容风控拦截场景）
            if any(name in cookie_dict for name in CRITICAL_COOKIE_NAMES):
                return True, uid
            return False, None
        except Exception:
            # 接口异常但已有关键 Cookie，视作已登录
            if any(name in cookie_dict for name in CRITICAL_COOKIE_NAMES):
                return True, None
            return False, None


def _launch_driver() -> "object":
    if UC_AVAILABLE:
        # undetected-chromedriver 分支
        driver = uc.Chrome(use_subprocess=True)
        return driver
    # 原生 Selenium 分支（Selenium Manager 自动管理驱动）
    chrome_options = ChromeOptions()
    # 如需复用你本机已登录的 Chrome 配置，可取消注释并设置路径
    # user_data_dir = os.environ.get("USER_DATA_DIR")
    # if user_data_dir:
    #     chrome_options.add_argument(f"--user-data-dir={user_data_dir}")
    driver = webdriver.Chrome(options=chrome_options)
    return driver


def main() -> None:
    # 若同级已存在 cookies.txt，则不重复导出
    if OUTPUT_PATH.exists():
        print(f"检测到已存在: {OUTPUT_PATH}。如需重新导出，请先删除该文件后再运行。")
        return

    print("将启动一个自动化浏览器，请在页面中完成 B 站登录（推荐扫码）。脚本会自动检测登录成功后导出 Cookies。")

    driver = _launch_driver()
    try:
        driver.maximize_window()
    except Exception:
        pass
    driver.get("https://www.bilibili.com/")

    deadline = time.time() + 600
    last_report = 0
    while time.time() < deadline:
        time.sleep(3)
        try:
            cookies = driver.get_cookies()
        except Exception:
            continue
        cookie_map = _cookies_list_to_dict(cookies)
        try:
            ua = driver.execute_script("return navigator.userAgent")
        except Exception:
            ua = None
        ok, uid = _check_is_login(cookie_map, user_agent=ua)
        now = time.time()
        if now - last_report > 9:
            print("等待登录中…（可在页面扫码/账号登录），将自动检测登录状态…")
            last_report = now
        if ok:
            print(f"检测到已登录，UID: {uid}")
            rows = _to_netscape_rows(cookies)
            if not rows:
                print("未采集到与 bilibili 相关的 Cookies，请确认已在主站完成登录。")
                break
            _write_netscape(rows, OUTPUT_PATH)
            print(f"已生成: {OUTPUT_PATH}，共 {len(rows)} 条")
            critical = {r[5] for r in rows}
            missing = {"SESSDATA", "bili_jct"} - critical
            if missing:
                print(f"提示: 缺少关键 Cookie: {', '.join(sorted(missing))}，部分接口可能不可用。")
            break

    try:
        driver.quit()
    except Exception:
        pass


if __name__ == "__main__":
    main()


