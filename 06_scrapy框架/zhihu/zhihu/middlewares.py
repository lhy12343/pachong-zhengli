# Define here the models for your spider middleware
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/spider-middleware.html

from scrapy import signals

# useful for handling different item types with a single interface
from itemadapter import ItemAdapter


class ZhihuSpiderMiddleware:
    # Not all methods need to be defined. If a method is not defined,
    # scrapy acts as if the spider middleware does not modify the
    # passed objects.

    @classmethod
    def from_crawler(cls, crawler):
        # This method is used by Scrapy to create your spiders.
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_spider_input(self, response, spider):
        # 在进入 Spider 之前：提取 __NEXT_DATA__ 并精确解析用户对象
        try:
            # 只处理我们目标 Spider
            if getattr(spider, 'name', '') != 'zhihupc':
                return None

            # 仅处理用户主页
            url = response.url or ''
            # /people/<token>
            import re, json
            m = re.search(r"/people/([^/?#]+)", url)
            if not m:
                return None
            url_token = m.group(1)

            # 提取 __NEXT_DATA__
            sel = response.css('script#__NEXT_DATA__::text').get()
            init_data = None
            if sel:
                try:
                    data = json.loads(sel.strip())
                    if isinstance(data, dict):
                        if 'appInitialState' in data:
                            init_data = data
                        else:
                            props = data.get('props') or {}
                            page = props.get('pageProps') or {}
                            if 'appInitialState' in page:
                                init_data = {'appInitialState': page.get('appInitialState')}
                            else:
                                init_data = data
                except Exception:
                    init_data = None

            if not isinstance(init_data, dict):
                return None

            state = init_data.get('appInitialState') or init_data.get('initialState') or init_data
            if not isinstance(state, dict):
                return None

            user_obj = self._get_user_from_state(state, url_token)
            if not isinstance(user_obj, dict):
                return None

            # 标准化映射，产出扁平 dict
            mapped = self._map_user_fields(user_obj)
            mapped['url_token'] = url_token
            mapped['url'] = url

            # 放入 meta，供 Spider 直接使用
            response.meta['user_obj'] = mapped
        except Exception as e:
            try:
                import json
                print(json.dumps({'event': 'middleware_error', 'error': repr(e)}, ensure_ascii=False), flush=True)
            except Exception:
                pass
        return None

    def process_spider_output(self, response, result, spider):
        # Called with the results returned from the Spider, after
        # it has processed the response.

        # Must return an iterable of Request, or item objects.
        for i in result:
            yield i

    def process_spider_exception(self, response, exception, spider):
        # Called when a spider or process_spider_input() method
        # (from other spider middleware) raises an exception.

        # Should return either None or an iterable of Request or item objects.
        pass

    async def process_start(self, start):
        # Called with an async iterator over the spider start() method or the
        # maching method of an earlier spider middleware.
        async for item_or_request in start:
            yield item_or_request

    def spider_opened(self, spider):
        spider.logger.info("Spider opened: %s" % spider.name)

    # --- 内部工具 ---
    def _get_user_from_state(self, state, url_token):
        if not isinstance(state, dict):
            return None
        entities = state.get('entities') or {}
        users = None
        for key in ('users', 'usersById', 'people', 'user', 'userDict', 'usersDict'):
            if isinstance(entities.get(key), dict):
                users = entities.get(key)
                break
        if not isinstance(users, dict):
            for key in ('users', 'usersById', 'people'):
                if isinstance(state.get(key), dict):
                    users = state.get(key)
                    break
        if not isinstance(users, dict):
            return None
        if url_token in users and isinstance(users[url_token], dict):
            return users[url_token]
        for v in users.values():
            if isinstance(v, dict) and v.get('urlToken') == url_token:
                return v
        return None

    def _map_user_fields(self, u):
        def g(key, alt=None):
            if key in u:
                return u.get(key)
            if alt:
                return u.get(alt)
            return None
        def names(lst):
            if isinstance(lst, list):
                return [x.get('name') if isinstance(x, dict) else x for x in lst]
            return lst
        biz = g('business')
        return {
            'name': g('name'),
            'gender': g('gender'),
            'avatar_url': g('avatarUrl') or g('avatar_url'),
            'badge': g('badge') or g('badgeV2'),
            'answers_count': g('answerCount', 'answers'),
            'articles_count': g('articlesCount', 'articles'),
            'pins_count': g('pinsCount', 'pins'),
            'following_count': g('followingCount'),
            'followers_count': g('followerCount', 'followers'),
            'voteup_count': g('voteupCount'),
            'thanked_count': g('thankedCount'),
            'favorite_count': g('favoriteCount') or g('favoritedCount'),
            'business': (biz or {}).get('name') if isinstance(biz, dict) else biz,
            'locations': names(g('locations')),
            'educations': g('educations'),
            'employments': g('employments'),
        }


class ZhihuDownloaderMiddleware:
    # Not all methods need to be defined. If a method is not defined,
    # scrapy acts as if the downloader middleware does not modify the
    # passed objects.

    @classmethod
    def from_crawler(cls, crawler):
        # This method is used by Scrapy to create your spiders.
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_request(self, request, spider):
        # Called for each request that goes through the downloader
        # middleware.

        # Must either:
        # - return None: continue processing this request
        # - or return a Response object
        # - or return a Request object
        # - or raise IgnoreRequest: process_exception() methods of
        #   installed downloader middleware will be called
        return None

    def process_response(self, request, response, spider):
        # Called with the response returned from the downloader.

        # Must either;
        # - return a Response object
        # - return a Request object
        # - or raise IgnoreRequest
        return response

    def process_exception(self, request, exception, spider):
        # Called when a download handler or a process_request()
        # (from other downloader middleware) raises an exception.

        # Must either:
        # - return None: continue processing this exception
        # - return a Response object: stops process_exception() chain
        # - return a Request object: stops process_exception() chain
        pass

    def spider_opened(self, spider):
        spider.logger.info("Spider opened: %s" % spider.name)
