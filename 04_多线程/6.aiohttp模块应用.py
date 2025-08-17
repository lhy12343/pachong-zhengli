import aiohttp
import asyncio
import os
import socket
from urllib.parse import urlparse

urls = [
    'https://i1.huishahe.com/uploads/tu/201911/9999/90913e3f0d.jpg',
    'https://i1.huishahe.com/uploads/allimg/202205/9999/3cc281f1ea.jpg',
    'https://i1.huishahe.com/uploads/allimg/202206/9999/9783c7e78d.jpg'
]

headers = {
    'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Connection': 'keep-alive',
    'Referer': 'https://www.umeituku.com/',
    'Sec-Fetch-Dest': 'image',
    'Sec-Fetch-Mode': 'no-cors',
    'Sec-Fetch-Site': 'cross-site',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
}


# 获取图片域名对应的IP
def get_host_ip(host):
    try:
        return socket.gethostbyname(host)  # 获取域名对应的IP
    except:
        return host  # 如果解析失败，则返回原域名


# 修改URL为IP直连
def convert_to_ip_url(url):
    parsed = urlparse(url)
    host = parsed.netloc
    ip = get_host_ip(host)
    return url.replace(host, ip), host  # 返回新的URL和原始Host


async def aiodownload(session, url, semaphore):
    async with semaphore:
        # 转换为IP直连URL，并获取原始Host
        ip_url, original_host = convert_to_ip_url(url)
        filename = os.path.basename(urlparse(url).path)

        # 设置Host头为原始域名
        download_headers = headers.copy()
        download_headers['Host'] = original_host

        try:
            print(f'准备下载: {filename}...')

            # 使用IP直连URL，并添加Host头
            async with session.get(
                    ip_url,
                    headers=download_headers,
                    ssl=False  # 跳过SSL验证
            ) as resp:
                resp.raise_for_status()
                content = await resp.read()

                save_dir = os.path.join(os.path.dirname(__file__), "youmei")
                os.makedirs(save_dir, exist_ok=True)
                filepath = os.path.join(save_dir, filename)

                with open(filepath, 'wb') as f:
                    f.write(content)
                print(f'✅ 下载成功: {filename}')

        except Exception as e:
            print(f'❌ 下载失败: {filename}, 原因: {e}')


async def main():
    # 增加并发数（根据网络情况调整）
    semaphore = asyncio.Semaphore(5)

    # 创建TCP连接器并禁用SSL验证
    connector = aiohttp.TCPConnector(ssl=False)

    async with aiohttp.ClientSession(
            connector=connector,
            trust_env=True  # 信任系统环境设置
    ) as session:
        tasks = [aiodownload(session, url, semaphore) for url in urls]
        await asyncio.gather(*tasks)


if __name__ == '__main__':
    print("开始下载...")
    asyncio.run(main())
