import json  # 导入json模块,作用是处理json数据
import base64  # 导入base64模块,作用是处理base64数据
import binascii  # 导入binascii模块,作用是处理二进制数据
import random  # 导入random模块,作用是生成随机数
import string  # 导入string模块,作用是生成随机字符串
import requests  # 导入requests库,作用是发送HTTP请求
import time  # 导入time模块,作用是控制时间间隔
from Crypto.Cipher import AES  # 导入AES模块,作用是加密解密
from Crypto.Util.Padding import pad  # 导入pad函数,作用是填充数据
from fake_useragent import UserAgent  # 导入UserAgent类,作用是生成随机的User-Agent


# 加密函数 - 模拟网易云音乐的加密过程
def encrypt_data(data):
    # 固定值
    aes_key1 = '0CoJUm6Qyw8W8jud'
    aes_iv = '0102030405060708'

    # 生成16位随机字符串作为第二次加密的密钥
    aes_key2 = ''.join(random.choices(string.ascii_letters + string.digits, k=16))

    # 第一次AES加密
    cipher1 = AES.new(aes_key1.encode('utf-8'), AES.MODE_CBC, aes_iv.encode('utf-8'))
    encrypted = cipher1.encrypt(pad(data.encode('utf-8'), AES.block_size))
    result1 = base64.b64encode(encrypted).decode('utf-8')

    # 第二次AES加密
    cipher2 = AES.new(aes_key2.encode('utf-8'), AES.MODE_CBC, aes_iv.encode('utf-8'))
    encrypted = cipher2.encrypt(pad(result1.encode('utf-8'), AES.block_size))
    params = base64.b64encode(encrypted).decode('utf-8')

    # RSA加密生成encSecKey
    public_key = '010001'
    modulus = '00e0b509f6259df8642dbc35662901477df22677ec152b5ff68ace615bb7b725152b3ab17a876aea8a5aa76d2e417629ec4ee341f56135fccf695280104e0312ecbda92557c93870114af6c9d05c4f7f0c3685b7a46bee255932575cce10b424d813cfe4875d3e82047b97ddef52741d546b8e289dc6935b3ece0462db0a22b8e7'

    # 反转密钥并转换为十六进制
    reversed_key = aes_key2[::-1].encode('utf-8')
    hex_key = binascii.hexlify(reversed_key).decode('utf-8')

    # 计算RSA加密
    rsa = int(hex_key, 16) ** int(public_key, 16) % int(modulus, 16)
    enc_sec_key = format(rsa, 'x').zfill(256)

    return params, enc_sec_key


# 获取歌曲评论
def get_song_comments(song_id, page=1, limit=20):
    # 构造请求URL
    url = "https://music.163.com/weapi/comment/resource/comments/get?csrf_token="

    # 构造请求参数
    data = {
        "csrf_token": "",
        "cursor": (page - 1) * limit,
        "offset": 0,
        "orderType": 1,  # 1:推荐排序, 2:热度排序, 3:时间排序
        "pageNo": page,
        "pageSize": limit,
        "rid": f"R_SO_4_{song_id}",  # 歌曲ID格式
        "threadId": f"R_SO_4_{song_id}",
    }

    # 转换为JSON并加密
    data_json = json.dumps(data)
    params, enc_sec_key = encrypt_data(data_json)

    # 构造POST数据
    post_data = {
        "params": params,
        "encSecKey": enc_sec_key
    }

    # 使用随机User-Agent
    ua = UserAgent()

    # 请求头 - 添加必要的Cookie和Referer
    headers = {
        'User-Agent': ua.random,
        'Referer': f'https://music.163.com/song?id={song_id}',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Origin': 'https://music.163.com',
        'Cookie': 'NMTID=00OQ9w20FsUio83kEB0jgHG8BSlAUsAAAGVq-5u0A; _ntes_nnid=2bd87da3ac5d1feaf1a94d31556504c2,1742346308873; _ntes_nuid=2bd87da3ac5d1feaf1a94d31556504c2; WEVNSM=1.0.0; WNMCID=oeqwom.1742346309787.01.0; WM_TID=6jufv8TaT4JABQQVBVaDI5jL%2BagqN58H; sDeviceId=YD-IknBIAOn8VlFVxFEAFOSds2KvLwuKmIi; ntes_utid=tid._.MwYPbKNi6lJEElAQEEeDds3Pvb0uflOu._.0; timing_user_id=time_uru3yG1dzc; _ga=GA1.1.852828781.1750854200; _ga_EPDQHDTJH5=GS2.1.s1750854199$o1$g1$t1750854246$j13$l0$h0; __snaker__id=UiJlUsG1d5sNiLEg; _iuqxldmzr_=32; ntes_kaola_ad=1; WM_NI=Ut34U68N4ouN00l6JwP%2BGL3sTLN9Rj%2FOQ8bNcgyvGvjrmxImxpUQnV%2Bq4fpLavHTSy1u0i3O%2FTsZ48TgQG9S%2BNpp9e5RF1meomK5UOx%2Ff2VmqItSpOSYBt0k1faQAbhvS00%3D; WM_NIKE=9ca17ae2e6ffcda170e2e6eed6b239fb88baa3cf5d97968bb3c54f868a9e87d26d93bcf784e85d8e89bb94ce2af0fea7c3b92a97acfdd5d83efc92fc90f846f4f0a4d7c97d94f589adb279989482dad162ed919fd9e146a1b9b797c67eaaaea399cc67bcb09bb2ed5ee9affc87f348a3aa88b5d273f3ab008ab245ed8cbdbbb73498b99fa8bc59e992c091bc6ff78e8ad2f06fadb385d6d845bcf1aad3d567b397bcb4f34591878e95b361f3baafb2c46aacaa9dd1b337e2a3; gdxidpyhxdE=GKgxAWO6c0SPRH8fXcxYHQ8rUnIwY78n791XYegXy5W0Xt%2BggOv9ObudNgYHme1qVIHBzZeMQZbJHSUeEb71NHhPvPxa3ewc8VPgGA51Ay0XwPyP8vcRfuwmWAPYoHb3fDJJjeEebC68hwZmPJbDd1m5OnBQ%2B4QDhoYg6xDsnrSU1sso%3A1752721760728; NTES_P_UTID=tkIKJ4SqoDDVcOiyReWzVUwuzRswxmE4|1752721104; NTES_SESS=5zt_m3lQ5Jpp9r7cgZVGXXHkztmlfZgRmh6NOk2.bOdTbX4tbOxW2Sk5IVeteoj78wKr2k_phEzNA4wqeGSXkdKj7UjBY_y8tJWM6_0thRegZfAPcajFnE8ig4TmrJ_ZBmgr.ZCdTG7v1d2HbI1zGys8m59ES_zXKYmsXIQPu5L1iuYT__ZjUfFugAewIp0.gVR7sRBokSZ83phtTL6oWxcpVhsQ1wNhu; S_INFO=1752721104|0|3&80##|m18228224375; P_INFO=m18228224375@163.com|1752721104|0|music|00&99|zhj&1752721069&urs_mailaq#zhj&330300#10#0#0|182375&1|urs_mailaq|18228224375@163.com; MUSIC_U=0075ED0FABC7C0C238BE2CB65FAE3C768B9C5B7247653744884354E681FB6C709A8703DCA119741E4D2F8AB8A41A58EAAC914F2D8CAB38E1E88DBDCE2E420FC5EC153D3077BB4332CE7FDC07A2C25E69DB95A13B2257476C9DC006E4B1E63AE8807BF6B778037B2FB780811293A7D9132E2A1FD172B7B518E044B1849562CAEF349FEC3BEDE40874CFB7024685BFA0044A11579E10182105C79E94385DD380405FD084DAD92DD72E2612703519796BB87A62A22F3149F2D859C2B10DA8C37AD11C7C249A89F72CD7F7D4657F61D67D60FF1798060F4F698BDF3D287ED70ABBDAA2DE04201854C5BC660334F5AE7DB941E9F1B3FFAC400BA54D9213180C690645F67DAC4FF9706DAA7F85879D19672D4EA1E46EA604310DAEF174CB90A1D230C1AECA9A532144A13FD851E86B35A79BAF88E4C971756FA9DE255BDDBD5990F86287A0B7E19A6D5D1A423F6C5AF3046DCC7A38EBC4AE06AE7060B5213E3FBB8F94AF; __remember_me=true; __csrf=311c9566cbf79264ad92e6f11db7c642; playerid=58071944; JSESSIONID-WYYY=erXTsVJQ%2BvSas3nOFB20i%2BrNxq1RlI0hHt7yUrejY6u9RfehIgFB1EBpViVd7q8MsCrUwS1Q5QShGPsQDffUc82Uevz17DnT%2F4T1lVjFSK6AG4uGIDZJ8fF%5C5hySN6oB1EWj8e3BVt%5CAaPZHmEmGOE332lEguCQuVZk5gHBX5pAtv4iO%3A1752725635242'
    }

    # 随机延迟，避免请求过快
    time.sleep(random.uniform(1, 3))

    try:
        # 发送请求
        response = requests.post(url, data=post_data, headers=headers, timeout=10)
        response.raise_for_status()  # 检查HTTP错误
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"请求失败: {e}")
        return None
    except json.JSONDecodeError:
        print("解析JSON失败")
        return None


# 主程序
if __name__ == "__main__":
    # 歌曲ID（示例：https://music.163.com/#/song?id=1325905146）
    song_id = "1325905146"

    print("开始爬取网易云音乐评论...")

    # 获取第一页评论（每页20条）
    comments_data = get_song_comments(song_id)

    # 检查是否获取到数据
    if comments_data is None:
        print("未能获取评论数据")
        exit()

    # 检查返回状态码
    code = comments_data.get('code', -1)
    if code != 200:
        print(f"请求失败，错误代码: {code}, 错误信息: {comments_data.get('message', '未知错误')}")
        exit()

    # 检查是否有评论数据
    if 'data' in comments_data:
        # 获取热门评论和普通评论
        hot_comments = comments_data['data'].get('hotComments', [])
        normal_comments = comments_data['data'].get('comments', [])
        all_comments = hot_comments + normal_comments

        # 安全获取总评论数
        total = comments_data['data'].get('totalCount', len(all_comments))

        print(f"共获取到 {len(all_comments)} 条评论（总评论数：{total}）:\n")

        # 只输出昵称和内容
        for comment in all_comments:
            user = comment['user']['nickname']
            content = comment['content'].replace('\n', ' ')
            print(f"{user}: {content}")
    else:
        print("获取评论失败，返回数据中缺少必要字段")
