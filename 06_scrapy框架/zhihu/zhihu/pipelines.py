# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
from itemadapter import ItemAdapter
from zhihu.items import UserItem


class ZhihuPipeline:  
    def process_item(self, item, spider):
        """
        处理从爬虫获取的用户数据项，进行数据清洗和标准化
        
        Args:
            item: 从爬虫获取的数据项，可能是UserItem或其他类型的项
            spider: 当前运行的爬虫实例
            
        Returns:
            item: 处理后的数据项，如果是UserItem则进行标准化处理，否则直接返回
        """
        adapter = ItemAdapter(item)

        # 仅处理 UserItem，其它类型直接透传
        if not isinstance(item, UserItem):
            return item

        def to_int(v):
            """
            将值转换为整数，支持处理包含中文单位的数值字符串
            
            Args:
                v: 需要转换的值
                
            Returns:
                转换后的整数值，如果转换失败则返回None
            """
            if v is None:
                return None
            try:
                if isinstance(v, bool):
                    return int(v)
                if isinstance(v, (int,)):
                    return v
                s = str(v).strip().replace(',', '')
                # 去除中文单位，如 1,234 或 1.2万
                import re
                m = re.match(r"^(\d+)$", s)
                if m:
                    return int(m.group(1))
                m = re.match(r"^(\d+)(万|w)$", s, re.I)
                if m:
                    return int(m.group(1)) * 10000
                m = re.match(r"^(\d+\.\d+)(万|w)$", s, re.I)
                if m:
                    return int(float(m.group(1)) * 10000)
                return int(float(s))
            except Exception:
                return None

        def strip_str(v):
            """
            去除字符串两端的空白字符
            
            Args:
                v: 需要处理的值
                
            Returns:
                如果是字符串则返回去除两端空白的字符串，否则返回原值
            """
            return v.strip() if isinstance(v, str) else v

        # 规范化基础字符串
        for key in (
            'url', 'url_token', 'name', 'headline', 'avatar', 'avatar_url', 'business', 'ip_location'
        ):
            if key in adapter:
                adapter[key] = strip_str(adapter.get(key))

        # 性别标准化：0/1/None or 'male'/'female'
        gender = adapter.get('gender')
        if isinstance(gender, str):
            g = gender.lower()
            if g in ('male', 'm', '男'):
                adapter['gender'] = 1
            elif g in ('female', 'f', '女'):
                adapter['gender'] = 0
            else:
                adapter['gender'] = None
        elif isinstance(gender, (int,)):
            adapter['gender'] = 1 if gender == 1 else (0 if gender == 0 else None)
        else:
            adapter['gender'] = None if gender is None else adapter['gender']

        # 计数字段转 int
        for key in (
            'following', 'followers', 'answers_count', 'articles_count', 'pins_count', 'collections_count',
            'following_count', 'followers_count', 'voteup_count', 'thanked_count', 'favorite_count'
        ):
            if key in adapter:
                adapter[key] = to_int(adapter.get(key))

        # 列表字段标准化
        def ensure_list(v):
            """
            确保值是列表类型
            
            Args:
                v: 需要处理的值
                
            Returns:
                如果原值为None则返回None，如果原值为列表则直接返回，否则将值包装成列表返回
            """
            if v is None:
                return None
            if isinstance(v, list):
                return v
            return [v]

        for key in ('locations', 'educations', 'employments', 'details'):
            if key in adapter:
                adapter[key] = ensure_list(adapter.get(key))

        return item


class UserDetailFilePipeline:
    """用户详情数据文件保存Pipeline"""

    def __init__(self):
        self.file = None
        self.output_file = None
        self.search_username = None
        self.user_count = 0

    @classmethod
    def from_crawler(cls, crawler):
        return cls()

    def open_spider(self, spider):
        """开启爬虫时动态生成文件名"""
        try:
            # 获取搜索的用户名
            self.search_username = getattr(spider, 'username', 'unknown')
            # 文件名格式：用户昵称-{数量}位用户的详情数据.txt
            # 先创建临时文件名，稍后在第一个item时更新
            base_path = r'C:\Users\Administrator\Desktop\pachong\06_scrapy框架\zhihu'
            self.temp_filename = f"{base_path}\\{self.search_username}-详情数据.txt"
            # 不在这里打开文件，等到知道用户数量后再打开
        except Exception as e:
            spider.logger.error(f"初始化文件名失败: {e}")

    def close_spider(self, spider):
        """关闭爬虫时关闭文件"""
        if self.file:
            self.file.close()

    def process_item(self, item, spider):
        """处理UserItem，格式化并保存到文件"""
        if not isinstance(item, UserItem):
            return item

        # 如果还没有打开文件，现在打开
        if not self.file:
            try:
                # 获取实际用户数和预期用户数
                actual_users = getattr(spider, 'total_users', len(getattr(spider, 'collected_users', [])))
                intended_users = getattr(spider, 'max_users', actual_users)

                # 动态生成最终文件名
                base_path = r'C:\Users\Administrator\Desktop\pachong\06_scrapy框架\zhihu'

                # 根据实际用户数与预期用户数是否相等来决定文件名格式
                if actual_users == intended_users:
                    self.output_file = f"{base_path}\\{self.search_username}-{intended_users}位用户的详情数据.txt"
                else:
                    self.output_file = f"{base_path}\\{self.search_username}-{intended_users}位用户（实际只有{actual_users}位）用户的详情数据.txt"

                # 打开文件（覆盖模式，确保每次运行都是新文件）
                self.file = open(self.output_file, 'w', encoding='utf-8')
                spider.logger.info(f"创建输出文件: {self.output_file}")
            except Exception as e:
                spider.logger.error(f"无法创建输出文件: {e}")
                return item

        try:
            # 格式化用户数据
            lines = []
            lines.append(f"昵称：{item.get('name', '')}")
            lines.append(f"用户签名：{item.get('headline', '')}")
            lines.append(f"回答数：{item.get('answers_count', '')}")
            lines.append(f"文章数：{item.get('articles_count', '')}")
            lines.append(f"关注者：{item.get('followers_count', '')}")
            lines.append(f"居住地：{item.get('location_detail', '')}")
            lines.append(f"职业经历：{item.get('career_info', '')}")
            lines.append(f"教育经历：{item.get('education_info', '')}")
            lines.append(f"个人简介：{item.get('personal_intro', '')}")
            lines.append(f"收藏夹数：{item.get('collections_detail_count', '')}")
            lines.append(f"想法：{item.get('ideas_count', '')}")
            lines.append(f"专栏：{item.get('columns_count', '')}")
            lines.append(f"提问：{item.get('questions_count', '')}")
            lines.append(f"视频数：{item.get('videos_count', '')}")
            lines.append(f"关注人数：{item.get('following_detail_count', '')}")
            lines.append(f"IP属地：{item.get('ip_location', '')}")

            # 写入文件
            for line in lines:
                self.file.write(line + '\n')

            # 添加空行分隔下一个用户
            self.file.write('\n')

            # 立即刷新到磁盘
            self.file.flush()

            spider.logger.info(f"成功保存用户数据: {item.get('name', 'Unknown')}")

        except Exception as e:
            spider.logger.error(f"保存用户数据失败: {e}")

        return item
