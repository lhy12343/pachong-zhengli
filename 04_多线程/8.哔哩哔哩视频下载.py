"""
Bilibili 一键下载（极简版）
- 直接运行脚本 → 输入页面 URL → 自动下载到 `04_多线程/out`
- 若存在 `04_多线程/cookies.txt`（Netscape 格式），自动携带登录态
- 未检测到系统 ffmpeg 时，自动使用 imageio-ffmpeg 内置二进制完成合并

命令行等效：
  python 04_多线程/8.如何抓取一部视频.py auto --url <页面URL> --out 04_多线程/out --cookies-file 04_多线程/cookies.txt
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional


def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def run_yt_dlp(
    url: str,
    out_dir: Path,
    *,
    cookies_file: Optional[str],
    fmt: str = "bv*+ba/best",
) -> None:
    """调用 yt-dlp 解析并下载。若无系统 ffmpeg，自动尝试 imageio-ffmpeg 的 ffmpeg。"""
    exe = shutil.which("yt-dlp")
    if exe is None:
        print("未找到 yt-dlp，请先安装：pip install yt-dlp")
        return

    ensure_dir(out_dir)
    cmd = [exe, url, "-o", str(out_dir / "%(title)s.%(ext)s"), "-f", fmt]
    if cookies_file:
        cmd.extend(["--cookies", cookies_file])

    # 指定 ffmpeg 位置（若系统不存在则尝试 imageio-ffmpeg）
    ff = shutil.which("ffmpeg")
    if ff is None:
        try:
            import imageio_ffmpeg as iio  # type: ignore

            ff = iio.get_ffmpeg_exe()
            cmd.extend(["--ffmpeg-location", ff])
            print(f"yt-dlp 使用 imageio-ffmpeg 的 ffmpeg: {ff}")
        except Exception:
            pass

    print("执行 yt-dlp:", " ".join(cmd))
    try:
        subprocess.check_call(cmd)
    except subprocess.CalledProcessError as e:
        print("yt-dlp 执行失败：", e)


def interactive_main() -> None:
    print("\n=== Bilibili 抓取助手（自动模式）===")
    out_dir = Path("04_多线程/out")
    ensure_dir(out_dir)

    url = input("请输入页面 URL: ").strip()

    # 自动使用相对路径 cookies.txt（若存在）
    default_cookies = Path("04_多线程/cookies.txt")
    cookies_file = str(default_cookies) if default_cookies.exists() else None
    if cookies_file:
        print(f"检测到 cookies 文件：{cookies_file}，将自动使用")
    else:
        print("未检测到 04_多线程/cookies.txt，将在无登录态下尝试下载（可影响清晰度/可见性）。")

    run_yt_dlp(url, out_dir, cookies_file=cookies_file, fmt="bv*+ba/best")


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Bilibili 一键下载脚本（简化版）")
    sub = p.add_subparsers(dest="cmd", required=True)

    # 仅保留 auto 子命令（按你的需求）
    pa = sub.add_parser("auto", help="自动解析页面 URL 并下载（封装 yt-dlp）")
    pa.add_argument("--url", required=True, help="B站页面 URL")
    pa.add_argument("--out", default="04_多线程/out", help="输出目录（默认: 04_多线程/out）")
    pa.add_argument("--cookies-file", dest="cookies_file", default=None, help="cookies.txt（Netscape 格式）")
    pa.add_argument("--format", dest="format", default="bv*+ba/best", help="yt-dlp 格式选择（默认: bv*+ba/best）")
    pa.set_defaults(func=main_auto)

    return p


def main_auto(args: argparse.Namespace) -> None:
    run_yt_dlp(args.url, Path(args.out), cookies_file=args.cookies_file, fmt=args.format)


def main(argv: Optional[list[str]] = None) -> None:
    # 无参数时进入“自动模式”：仅询问 URL，cookies.txt 自动检测
    if argv is None and len(sys.argv) == 1:
        try:
            interactive_main()
        except KeyboardInterrupt:
            print("\n已取消")
        return

    parser = build_arg_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()


