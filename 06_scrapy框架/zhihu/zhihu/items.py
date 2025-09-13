# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class UserItem(scrapy.Item):
    # 基础
    url = scrapy.Field()
    url_token = scrapy.Field()
    name = scrapy.Field()
    headline = scrapy.Field()
    gender = scrapy.Field()
    avatar = scrapy.Field()
    avatar_url = scrapy.Field()
    badge = scrapy.Field()
    ip_location = scrapy.Field()

    # 统计
    following = scrapy.Field()
    followers = scrapy.Field()
    answers_count = scrapy.Field()
    articles_count = scrapy.Field()
    pins_count = scrapy.Field()
    collections_count = scrapy.Field()
    following_count = scrapy.Field()
    followers_count = scrapy.Field()
    voteup_count = scrapy.Field()
    thanked_count = scrapy.Field()
    favorite_count = scrapy.Field()

    # 履历
    business = scrapy.Field()
    locations = scrapy.Field()
    educations = scrapy.Field()
    employments = scrapy.Field()
    details = scrapy.Field()

    # 详情页新增字段
    location_detail = scrapy.Field()  # 居住地
    career_info = scrapy.Field()  # 职业经历
    education_info = scrapy.Field()  # 教育经历
    personal_intro = scrapy.Field()  # 个人简介
    collections_detail_count = scrapy.Field()  # 收藏夹数
    ideas_count = scrapy.Field()  # 想法
    columns_count = scrapy.Field()  # 专栏
    questions_count = scrapy.Field()  # 提问
    videos_count = scrapy.Field()  # 视频数
    following_detail_count = scrapy.Field()  # 关注人数
    ip_location = scrapy.Field()  # IP属地
