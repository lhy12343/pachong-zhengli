import scrapy
import re
import json
import sys
from scrapy.http import Request
from scrapy.utils.project import get_project_settings
from zhihu.items import UserItem


class ZhihupcSpider(scrapy.Spider):
    name = "zhihupc"
    allowed_domains = ["www.zhihu.com"]
    start_urls = ["https://www.zhihu.com"]

    def __init__(self, username=None, max_users=None, *args, **kwargs):
        super(ZhihupcSpider, self).__init__(*args, **kwargs)
        # 方案B：优先使用 -a username=...，否则在控制台提示输入
        if username is None:
            try:
                sys.stderr.write("请输入要爬取的知乎用户昵称（如：luxenius）: ")
                sys.stderr.flush()
                username = input()
            except EOFError:
                username = ""

        self.username = (username or "").strip()

        # 处理max_users参数
        if max_users is None:
            try:
                sys.stderr.write("请输入要爬取的用户数量（默认20，最大200）: ")
                sys.stderr.flush()
                max_users_input = input().strip()
                if not max_users_input:
                    max_users = 20
                else:
                    max_users = int(max_users_input)
            except (EOFError, ValueError):
                max_users = 20
        else:
            try:
                max_users = int(max_users)
            except ValueError:
                max_users = 20

        # 限制最大数量
        self.max_users = min(max(max_users, 1), 200)  # 最少1个，最多200个
        self.total_users = 0  # 初始化总用户数
        self.collected_users = []  # 存储收集到的用户数据

        # 若仍为空，尝试从 settings.py 中读取默认用户名
        if not self.username:
            settings = get_project_settings()
            default_username = (settings.get('DEFAULT_ZHIHU_USERNAME') or "").strip()
            if default_username:
                self.username = default_username

        if not self.username:
            raise ValueError(
                "用户名不能为空。可使用：scrapy crawl zhihupc -a username=<昵称>；"
                "或在提示时输入；亦可在 settings.py 设置 DEFAULT_ZHIHU_USERNAME。"
            )

        print(f"搜索用户：{self.username}，预计爬取：{self.max_users}个用户")

    def build_search_url(self, offset, search_hash_id=None):
        """构建搜索URL，offset和lc_idx保持同步"""
        import urllib.parse
        encoded_username = urllib.parse.quote(self.username)

        # 基础URL
        url = f"https://www.zhihu.com/api/v4/search_v3?gk_version=gz-gaokao&t=people&q={encoded_username}&correction=1&offset={offset}&limit=20&filter_fields=&lc_idx={offset}&show_all_topics=0&search_source=Normal"

        # 如果有search_hash_id，则添加
        if search_hash_id:
            url += f"&search_hash_id={search_hash_id}"

        return url

    def extract_search_hash_id(self, response_data):
        """从响应数据中提取search_hash_id"""
        try:
            # 从paging.next字段中提取search_hash_id
            next_url = response_data.get('paging', {}).get('next', '')
            if not next_url:
                return None

            # 使用正则表达式提取search_hash_id参数
            import re
            match = re.search(r'search_hash_id=([a-f0-9]+)', next_url)
            if match:
                return match.group(1)
            return None
        except Exception as e:
            print(f"提取search_hash_id失败: {e}")
            return None

    def start_requests(self):
        """保持向后兼容性的start_requests方法"""
        print(f"开始搜索用户: {self.username}")

        # 只发起第一页请求，从响应中获取search_hash_id
        first_page_url = self.build_search_url(0)

        yield Request(
            url=first_page_url,
            callback=self.parse_search_results,
            errback=self.on_error,
            meta={
                'handle_httpstatus_all': True,
                'dont_redirect': True,
                'page_num': 1,
                'offset': 0,
                'is_first_page': True
            },
            dont_filter=True,
        )

    def parse(self, response):
        """原始parse方法保留但不使用"""
        pass

    def parse_search_results(self, response):
        """解析搜索API响应，提取用户信息"""
        page_num = response.meta.get('page_num', 1)
        offset = response.meta.get('offset', 0)
        is_first_page = response.meta.get('is_first_page', False)

        if response.status != 200:
            print(f"第{page_num}页搜索失败: HTTP {response.status}")
            return

        try:
            # 解析JSON响应
            data = json.loads(response.text)
            search_results = data.get('data', [])

            if not search_results:
                print(f"第{page_num}页没有找到用户数据")
                return

            print(f"第{page_num}页找到 {len(search_results)} 个用户")

            # 清理HTML标签的函数
            import re
            def clean_html(text):
                if not text:
                    return ""
                # 移除<em>和</em>标签
                return re.sub(r'<[^>]+>', '', text)

            # 处理这一页的用户数据
            page_users = []
            for result in search_results:
                # 检查是否已经收集够了用户
                if len(self.collected_users) >= self.max_users:
                    break

                # 提取数据
                highlight = result.get('highlight', {})
                obj = result.get('object', {})

                # 提取并格式化输出
                nickname = clean_html(highlight.get('title', ''))
                signature = clean_html(highlight.get('description', ''))
                answer_count = obj.get('answer_count', 0)
                articles_count = obj.get('articles_count', 0)
                follower_count = obj.get('follower_count', 0)
                url_token = obj.get('url_token', '')

                if url_token:
                    user_info = {
                        'nickname': nickname,
                        'signature': signature,
                        'answer_count': answer_count,
                        'articles_count': articles_count,
                        'follower_count': follower_count,
                        'url_token': url_token
                    }
                    self.collected_users.append(user_info)
                    page_users.append(user_info)

            # 更新总用户数
            self.total_users = len(self.collected_users)

            print(f"已收集 {self.total_users} 个用户，开始爬取详情页...")

            # 生成详情页请求
            for i, user_info in enumerate(page_users):
                detail_url = f"https://www.zhihu.com/people/{user_info['url_token']}"
                user_index = self.collected_users.index(user_info) + 1

                yield Request(
                    url=detail_url,
                    callback=self.parse_user_detail,
                    meta={
                        'user_basic_info': user_info,
                        'user_index': user_index
                    },
                    dont_filter=True
                )

            # 如果是第一页且还需要更多用户，处理分页
            if is_first_page and len(self.collected_users) < self.max_users:
                search_hash_id = self.extract_search_hash_id(data)

                if search_hash_id:
                    print(f"获取到search_hash_id: {search_hash_id}")

                    # 计算还需要多少页
                    remaining_users = self.max_users - len(self.collected_users)
                    import math
                    remaining_pages = math.ceil(remaining_users / 20)

                    # 生成后续分页请求
                    for page in range(2, remaining_pages + 2):  # 从第2页开始
                        offset = (page - 1) * 20
                        next_url = self.build_search_url(offset, search_hash_id)

                        yield Request(
                            url=next_url,
                            callback=self.parse_search_results,
                            errback=self.on_error,
                            meta={
                                'handle_httpstatus_all': True,
                                'dont_redirect': True,
                                'page_num': page,
                                'offset': offset,
                                'is_first_page': False
                            },
                            dont_filter=True,
                        )
                else:
                    print("未找到search_hash_id，只能爬取第一页数据")

        except json.JSONDecodeError as e:
            print(f"第{page_num}页JSON解析错误: {e}")
        except Exception as e:
            print(f"第{page_num}页数据提取错误: {e}")

    def on_error(self, failure):
        """请求错误回调，输出详细错误信息"""
        request = getattr(failure, 'request', None)
        url = request.url if request else 'unknown'
        print(f"请求失败: {url}")

    def parse_user_detail(self, response):
        """解析用户详情页HTML，提取详细信息"""
        user_basic_info = response.meta['user_basic_info']
        user_index = response.meta['user_index']

        print(f"第{user_index}个用户爬取成功: {user_basic_info['nickname']}")

        # 创建UserItem实例
        item = UserItem()

        # 填入基础信息
        item['name'] = user_basic_info['nickname']
        item['headline'] = user_basic_info['signature']
        item['answers_count'] = user_basic_info['answer_count']
        item['articles_count'] = user_basic_info['articles_count']
        item['followers_count'] = user_basic_info['follower_count']
        item['url_token'] = user_basic_info['url_token']
        item['url'] = response.url

        # 解析页面中的JSON数据
        def extract_json_data():
            try:
                # 提取js-initialData中的JSON数据
                json_script = response.xpath('//script[@id="js-initialData"]/text()').get()
                if json_script:
                    import json
                    data = json.loads(json_script)

                    # 获取用户信息，用url_token作为key
                    url_token = user_basic_info['url_token']
                    entities = data.get('initialState', {}).get('entities', {})
                    users = entities.get('users', {})
                    user_data = users.get(url_token, {})

                    return user_data
                return {}
            except Exception as e:
                print(f"JSON解析错误: {e}")
                return {}

        user_data = extract_json_data()

        # 安全提取函数
        def safe_get(data, key, default=""):
            return data.get(key, default) if data else default

        def safe_get_nested(data, *keys, default=""):
            try:
                result = data
                for key in keys:
                    if isinstance(result, list) and len(result) > 0:
                        result = result[0]
                    result = result.get(key, {})
                return result if result else default
            except:
                return default

        # 从JSON中提取详情信息
        item['location_detail'] = safe_get_nested(user_data, 'locations', 'name')

        # 职业经历：提取第一个工作经历
        employments = user_data.get('employments', [])
        if employments:
            job_name = safe_get_nested(employments[0], 'job', 'name')
            company_name = safe_get_nested(employments[0], 'company', 'name')
            item['career_info'] = f"{company_name} {job_name}".strip()
        else:
            item['career_info'] = ""

        # 教育经历：提取第一个教育经历
        educations = user_data.get('educations', [])
        if educations:
            school_name = safe_get_nested(educations[0], 'school', 'name')
            major_name = safe_get_nested(educations[0], 'major', 'name')
            item['education_info'] = f"{school_name} {major_name}".strip()
        else:
            item['education_info'] = ""

        # 个人简介
        item['personal_intro'] = safe_get(user_data, 'description')

        # 统计数据从JSON中提取
        item['collections_detail_count'] = safe_get(user_data, 'favoriteCount')
        item['ideas_count'] = safe_get(user_data, 'pinsCount')
        item['columns_count'] = safe_get(user_data, 'columnsCount')
        item['questions_count'] = safe_get(user_data, 'questionCount')
        item['videos_count'] = safe_get(user_data, 'zvideoCount')
        item['following_detail_count'] = safe_get(user_data, 'followingCount')

        # IP属地信息
        item['ip_location'] = safe_get(user_data, 'ipInfo')

        yield item

