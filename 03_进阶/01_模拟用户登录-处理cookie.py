import requests

session = requests.session()

# 设置请求头（基于您提供的完整信息）
headers = {
    "Accept": "*/*",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "Host": "user.17k.com",
    "Pragma": "no-cache",
    "Referer": "https://user.17k.com/www/bookshelf/",
    "Sec-Ch-Ua": '"Not)A;Brand";v="8", "Chromium";v="138", "Microsoft Edge";v="138"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36 Edg/138.0.0.0"
}
session.headers.update(headers)

# 设置Cookie（使用您提供的完整Cookie字符串）
cookies_str = (
    "GUID=66baebd9-e750-4529-810c-ced466f09532; "
    "sajssdk_2015_cross_new_user=1; "
    "c_channel=0; "
    "c_csc=web; "
    "accessToken=nickname%3D%25E6%25A5%2593783807222%26avatarUrl%3Dhttps%253A%252F%252Fcdn.static.17k.com%252Fuser%252Favatar%252F02%252F82%252F72%252F104177282.jpg-88x88%253Fv%253D1752480632000%26id%3D104177282%26e%3D1768034127%26s%3D5616756c7b3756ac; "
    "sensorsdata2015jssdkcross=%7B%22distinct_id%22%3A%22104177282%22%2C%22%24device_id%22%3A%2219807af6fd7704-0948593781466-4c657b58-2359296-19807af6fd8136a%22%2C%22props%22%3A%7B%22%24latest_traffic_source_type%22%3A%22%E7%9B%B4%E6%8E%A5%E6%B5%81%E9%87%8F%22%2C%22%24latest_referrer%22%3A%22%22%2C%22%24latest_referrer_host%22%3A%22%22%2C%22%24latest_search_keyword%22%3A%22%E6%9C%AA%E5%8F%96%E5%88%B0%E5%80%BC_%E7%9B%B4%E6%8E%A5%E6%89%93%E5%BC%80%22%7D%2C%22first_id%22%3A%2266baebd9-e750-4529-810c-ced466f09532%22%7D; "
    "acw_tc=0bdd342e17524825950741719eea7ccea84334cf0360a331853ccba74e1f38"
)

# 将Cookie字符串转换为字典
cookies_dict = {}
for item in cookies_str.split('; '):
    parts = item.split('=', 1)
    if len(parts) == 2:
        key, value = parts
        cookies_dict[key] = value

# 设置Cookie到会话
session.cookies.update(cookies_dict)

# 请求书架数据
url = "https://user.17k.com/ck/author2/shelf?page=1&appKey=2406394919"
resp = session.get(url)

# 打印响应内容
print("响应状态码:", resp.status_code)
print("响应内容:", resp.text)
