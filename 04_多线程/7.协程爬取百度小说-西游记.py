"""
时间：2025/8/8  12:02
"""

import requests
import json
import asyncio
import aiohttp
import aiofiles
import re
import os

# 章节列表请求url,不需要异步（注意：双花括号用于转义，避免 str.format 误解析）
url1 = 'https://dushu.baidu.com/api/pc/getCatalog?data={{%22book_id%22:%22{}%22}}'

# 章节内部内容请求基础地址（异步）
BASE_CHAPTER = 'https://dushu.baidu.com/api/pc/getChapterContent'

"""
1.同步操作：访问getcatalog，拿到所有章节的cid和名称
2.异步操作：访问getchaptercontent，拿到每一章节的正文内容：content
"""

headers = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "Content-Type": "application/x-www-form-urlencoded",
    "Cookie": "BDUSS=mx5ZXFRWWJpaEdtc1ZqSHp1TVJvWjZZR09WclJlempGcllWaTh4THJsc0V5Y2xuSVFBQUFBJCQAAAAAAAAAAAEAAAB0-lwzb2vC8G1lb2sAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAQ8omcEPKJna; BDUSS_BFESS=mx5ZXFRWWJpaEdtc1ZqSHp1TVJvWjZZR09WclJlempGcllWaTh4THJsc0V5Y2xuSVFBQUFBJCQAAAAAAAAAAAEAAAB0-lwzb2vC8G1lb2sAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAQ8omcEPKJna; BIDUPSID=EF9684D07E0F5F0EA663081CD012E35B; PSTM=1741004571; MAWEBCUID=web_GUQoDlWgUbkmMsyfOaJjMKcwydZQsktdyRbBzPrdnyCwAlRKhG; BAIDUID=3587BCCC26E8A6836A964ADC194A9190:FG=1; H_WISE_SIDS=62325_63584_63778_63824_63918_63894_63936_63949_63948_63963; BAIDUID_BFESS=3587BCCC26E8A6836A964ADC194A9190:FG=1; H_PS_PSSID=62325_63140_63327_63725_63778_63824_63881_63918_63894_63936_63949_63948_63963_63977_63987_63274_64011; BAIDU_WISE_UID=wapp_1752291979911_339; MCITY=-179%3A; ZFY=cDY8bBojTUUD6lN48Hu1UiwsISl3fv1zV96NBcHoCDU:C; H_WISE_SIDS_BFESS=62325_63584_63778_63824_63918_63894_63936_63949_63948_63963; RT=\"z=1&dm=baidu.com&si=d82cf474-23fa-468d-b1fd-530182cc3c37&ss=mdsownw1&sl=a&tt=cgu&bcn=https%3A%2F%2Ffclog.baidu.com%2Flog%2Fweirwood%3Ftype%3Dperf&ld=35pa&nu=q1y2tuax&cl=385p&ul=3mvx&hd=3mw2\"; Hm_lvt_bf1e478a71b02a743ab42bcfed9d1ff1=1754623520; HMACCOUNT=44B8B49F6F06BBD8; Hm_lpvt_bf1e478a71b02a743ab42bcfed9d1ff1=1754626280",
    "Pragma": "no-cache",
    "Referer": "https://dushu.baidu.com/pc/reader?gid=4306063500&cid=1569782244",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36 Edg/138.0.0.0",
    "sec-ch-ua": "\"Not)A;Brand\";v=\"8\", \"Chromium\";v=\"138\", \"Microsoft Edge\";v=\"138\"",
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": "\"Windows\"",
}


def wrap_to_width(text: str, width: int = 40) -> str:
    """将文本按行换行，保证每行不超过 width 个字符，保留原有空行。"""
    # 标准化换行
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    lines = text.split('\n')
    wrapped = []
    for line in lines:
        # 保留纯空行
        if line == '':
            wrapped.append('')
            continue
        # 对非空行进行定宽切分（不破坏中文）
        start = 0
        n = len(line)
        while start < n:
            wrapped.append(line[start:start + width])
            start += width
    return '\n'.join(wrapped)


async def aiodownload(session: aiohttp.ClientSession, book_id: str, cid: str, title: str, save_dir: str):
    """下载单章内容，返回 (cid, title, content) 并将内容落盘。"""
    params = {
        "data": json.dumps({
            "book_id": book_id,
            "cid": f"{book_id}|{cid}",
            "need_bookinfo": 1
        }, ensure_ascii=True)
    }
    async with session.get(BASE_CHAPTER, params=params) as resp:
        resp.raise_for_status()
        dic = await resp.json(content_type=None)
        content = dic.get('data', {}).get('novel', {}).get('content', '')
        content = wrap_to_width(content, 40)
        # 安全化文件名
        safe_title = re.sub(r'[\\/:*?"<>|\r\n]+', '_', title).strip() or cid
        filename = f"{cid}-{safe_title}.txt"
        filepath = os.path.join(save_dir, filename)
        async with aiofiles.open(filepath, mode='w', encoding='utf-8') as f:
            await f.write(content)
        return cid, title, content


async def getCatalog(url, save_dir: str):
    # 同步获取目录列表
    resp = requests.get(url, headers=headers)
    dic = resp.json()
    items = dic['data']['novel']['items']
    timeout = aiohttp.ClientTimeout(total=120)
    async with aiohttp.ClientSession(headers=headers, timeout=timeout) as session:
        tasks = []
        for item in items:
            title = item.get('title')
            cid = item.get('cid')
            tasks.append(asyncio.create_task(aiodownload(session, book_id, cid, title, save_dir)))
        results = await asyncio.gather(*tasks, return_exceptions=False)
        return results


if __name__ == '__main__':
    book_id = '4306063500'
    url = url1.format(book_id)
    # 目标保存目录
    SAVE_PARENT = r'C:\Users\Administrator\Desktop\pachong\04_多线程'
    SAVE_DIRNAME = '西游记全章节爬取'
    SAVE_DIR = os.path.join(SAVE_PARENT, SAVE_DIRNAME)
    os.makedirs(SAVE_DIR, exist_ok=True)
    asyncio.run(getCatalog(url, SAVE_DIR))
