# -*- coding: utf-8 -*-
"""
生成_douyin_cookies_selenium.py

功能：
- 启动 Chrome（可选 user-data-dir），打开 https://www.douyin.com/
- 引导用户扫码/登录
- 轮询检测登录态（检测 sessionid/sid_ucp_v1/sid_tt 等关键 Cookie）
- 将当前浏览器的所有 Cookie 导出为同目录 cookies.json（结构：{"cookies": [...] }）

使用示例：
python 生成_douyin_cookies_selenium.py --user-data-dir "../chrome_user_data" --no-headless

参数：
--user-data-dir 可选，指定 Chrome 用户数据目录，便于持久化登录
--headless / --no-headless 是否无头（默认可见窗口，便于扫码）
--wait-minutes 等待登录的最长分钟数（默认 10 分钟）

依赖：
- pip install selenium
- 系统具备 Chrome 浏览器
- 优先使用 Selenium Manager 自动管理驱动；若失败，脚本会回退尝试项目根目录 chromedriver.exe
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Optional, List, Dict

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import WebDriverException


DOUYIN_URL = "https://www.douyin.com/"
OUTPUT_FILE = "cookies.json"


def _find_project_root_chromedriver() -> Optional[Path]:
    """向上查找项目根目录是否存在 chromedriver.exe。"""
    cur = Path(__file__).resolve()
    for p in [cur.parent, cur.parent.parent, cur.parent.parent.parent]:
        if not p:
            continue
        cand = p / "chromedriver.exe"
        if cand.exists():
            return cand
    return None


def build_driver(user_data_dir: Optional[str], headless: bool) -> webdriver.Chrome:
    opts = Options()
    if user_data_dir:
        opts.add_argument(f"--user-data-dir={user_data_dir}")
    if headless:
        # 登录通常需要可视化，这里仍允许无头以兼容自动化场景
        opts.add_argument("--headless=new")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")

    # 优先尝试 Selenium Manager 默认路径
    try:
        return webdriver.Chrome(options=opts)
    except WebDriverException:
        # 回退：尝试项目根目录 chromedriver.exe
        drv_path = _find_project_root_chromedriver()
        if not drv_path:
            raise
        try:
            service = Service(executable_path=str(drv_path))
            return webdriver.Chrome(service=service, options=opts)
        except WebDriverException:
            raise


def _has_login_cookies(cookies: List[Dict]) -> bool:
    """粗略判断是否含有登录后的关键 Cookie。"""
    keys = {c.get("name", "") for c in cookies if isinstance(c, dict)}
    # 常见登录相关：sessionid/sid_ucp_v1/sid_tt/uid_tt/uid_tt_ss 等
    indicators = {"sessionid", "sid_ucp_v1", "sid_tt", "uid_tt", "uid_tt_ss"}
    return any(k in keys for k in indicators)


def _export_cookies(driver: webdriver.Chrome, out_path: Path) -> int:
    cookies = driver.get_cookies()  # List[Dict]
    # 规范化：确保 path/domain 字段存在
    normalized = []
    for c in cookies:
        if not isinstance(c, dict) or "name" not in c or "value" not in c:
            continue
        item = {
            "name": c.get("name"),
            "value": c.get("value"),
            "domain": c.get("domain", ".douyin.com"),
            "path": c.get("path", "/"),
        }
        # 可选字段带上，便于复用
        for k in ("expires", "httpOnly", "secure", "sameSite"):
            if k in c:
                item[k] = c[k]
        normalized.append(item)

    payload = {"cookies": normalized}
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return len(normalized)


def main():
    parser = argparse.ArgumentParser(description="登录抖音并导出 cookies.json")
    parser.add_argument("--user-data-dir", dest="user_data_dir", default=None, help="Chrome 用户数据目录，可选")
    parser.add_argument("--headless", dest="headless", action="store_true", help="启用无头模式")
    parser.add_argument("--no-headless", dest="headless", action="store_false", help="禁用无头模式（默认）")
    parser.add_argument("--wait-minutes", type=int, default=10, help="等待登录的最长分钟数，默认10")
    parser.set_defaults(headless=False)
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    out_file = script_dir / OUTPUT_FILE

    print("[1/4] 启动 Chrome ...")
    try:
        driver = build_driver(args.user_data_dir, args.headless)
    except Exception as e:
        print("启动 Chrome 失败：", e)
        sys.exit(1)

    try:
        print("[2/4] 打开抖音主页：", DOUYIN_URL)
        driver.get(DOUYIN_URL)

        # 指引提示
        deadline = time.time() + args.wait_minutes * 60
        last_report = 0.0
        print("请在浏览器中完成登录（如扫码/密码）。脚本会自动检测登录状态并导出 Cookie。")

        # 在等待期间，定期尝试导出一次 cookies（即便未登录，也可用于匿名态）
        while time.time() < deadline:
            time.sleep(3)
            try:
                cookies = driver.get_cookies()
            except Exception:
                cookies = []

            # 每隔 ~15s 输出一次检测摘要
            if time.time() - last_report > 15:
                names = [c.get("name", "") for c in cookies if isinstance(c, dict)]
                print(f"已检测到 Cookie {len(cookies)} 条：示例 {names[:5]} ...")
                last_report = time.time()

            if _has_login_cookies(cookies):
                print("检测到疑似登录态 Cookie，准备导出 ...")
                break
        else:
            print("未在限定时间内检测到明确登录态，将仍然导出当前 Cookie（可能为匿名态）。")

        print("[3/4] 导出 cookies.json ...")
        count = _export_cookies(driver, out_file)
        print(f"已导出 {count} 条 Cookie -> {out_file}")

        print("[4/4] 完成。你可以关闭浏览器窗口。")
    finally:
        try:
            driver.quit()
        except Exception:
            pass


if __name__ == "__main__":
    main()
