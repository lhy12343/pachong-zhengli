import re
import requests
import os
import hashlib
from urllib.parse import urlparse

# 创建存储视频的目录
video_dir = "video"
os.makedirs(video_dir, exist_ok=True)

# 1. 获取视频播放页
detail_url = input('请输入梨视频详情页URL: ')

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36 Edg/138.0.0.0",
    "Referer": "https://www.pearvideo.com/"
}

try:
    # 请求视频详情页
    response = requests.get(detail_url, headers=headers)
    response.raise_for_status()  # 检查HTTP错误
    response.encoding = 'utf-8'
    html_content = response.text

    # 2. 从URL中提取视频ID
    video_id_match = re.search(r'detail_(\d+)', detail_url)
    video_id = video_id_match.group(1) if video_id_match else "unknown"

    print(f"正在处理视频ID: {video_id}...")

    # 3. 正则提取视频链接
    pattern = r'(hd|sd|ld)Url="(https?://[^"]+\.mp4)"'
    match = re.search(pattern, html_content)

    if not match:
        print("未找到视频链接，尝试备选方案...")
        # 备选方案：直接搜索mp4链接
        alt_pattern = r'(https?://video\.pearvideo\.com/mp4/third/[^"]+\.mp4)'
        alt_match = re.search(alt_pattern, html_content)
        if alt_match:
            video_url = alt_match.group(1)
            quality = "unknown"
            print(f"通过备选方案找到视频链接: {video_url}")
        else:
            raise ValueError("无法提取视频链接")
    else:
        quality, video_url = match.groups()
        print(f"提取到视频链接({quality}): {video_url}")

    # 4. 创建基于URL的唯一文件名
    # 使用URL的MD5哈希作为唯一标识
    url_hash = hashlib.md5(video_url.encode()).hexdigest()[:8]
    # 从URL中提取文件名
    parsed_url = urlparse(video_url)
    filename = os.path.basename(parsed_url.path)
    # 组合最终文件名：视频ID_清晰度_哈希值_原文件名
    safe_filename = f"{video_id}_{quality}_{url_hash}_{filename}"
    save_path = os.path.join(video_dir, safe_filename)

    # 5. 检查文件是否已存在
    if os.path.exists(save_path):
        print(f"视频已存在，跳过下载: {save_path}")
        exit(0)

    print(f"开始下载视频，将保存到: {save_path}")

    # 6. 下载视频（带防盗链处理）
    video_headers = {
        "User-Agent": headers["User-Agent"],
        "Referer": detail_url,
        "Sec-Fetch-Dest": "video",
        "Sec-Fetch-Mode": "no-cors",
        "Sec-Fetch-Site": "same-site",
        "Range": "bytes=0-"
    }

    # 下载视频
    with requests.get(video_url, headers=video_headers, stream=True) as video_response:
        video_response.raise_for_status()

        # 检查文件大小
        total_size = int(video_response.headers.get('content-length', 0))
        if total_size == 0:
            print("警告: 无法获取文件大小，可能是流媒体视频")

        # 保存视频
        with open(save_path, 'wb') as f:
            downloaded = 0
            for chunk in video_response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    # 显示下载进度
                    if total_size > 0:
                        percent = downloaded / total_size * 100
                        print(f"下载进度: {percent:.1f}% ({downloaded}/{total_size} bytes)", end='\r')

        print(f"\n视频下载完成! 保存为: {save_path}")
        print(f"文件大小: {os.path.getsize(save_path)} bytes")

except requests.exceptions.RequestException as e:
    print(f"网络请求失败: {str(e)}")
    # 保存错误页面内容
    if 'html_content' in locals():
        with open("error_page.html", "w", encoding="utf-8") as f:
            f.write(html_content)
        print("已保存错误页面内容到 error_page.html")
except Exception as e:
    print(f"发生错误: {str(e)}")
