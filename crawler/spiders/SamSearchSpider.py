#!/usr/bin/python
# -*- coding: utf-8 -*-

import json
from ..items import SamItem
import scrapy

from datetime import datetime, timezone, timedelta

from urllib import parse

import random

import time


class SamSearchSpider(scrapy.Spider):
    name = 'SamSearch'
    allowed_domains = ['sam.gov']
    handle_httpstatus_list = [404]
    is_200 = True

    def __init__(self, *args, **kwargs):
        super(SamSearchSpider, self).__init__(*args, **kwargs)
        self.page = 0
        # 方式一: 在init方法中获取参数
        try:
            self.page = kwargs.get('page')
        except:
            self.page = 0
        try:
            self.size = kwargs.get('size')
        except:
            self.size = 25
        try:
            self.param = kwargs.get('param')
        except:
            self.param = r'%22lease%20office%22%20rental%20lease%20warehouse%20retail'
        self.searchType = '8A'
        try:
            self.searchType = kwargs.get('searchType')
        except:
            self.searchType = '8A'
        self.logger.info("-------------------------------")
        self.logger.info("page: {}, size: {}".format(self.page, self.size))
        self.logger.info("-------------------------------")

    # 页数迭代
    def start_requests(self):
        # 把所有的URL地址统一扔给调度器入队列

        # &response_date.to=2023-07-22+08:00&response_date.from=2022-07-22+08:00
        url = ''
        if self.searchType == '8A':
            url = r'https://sam.gov/api/prod/sgs/v1/search/?random={}&index=opp&page={}&sort=-modifiedDate&size={}&mode=search&responseType=json&is_active=true&q={}&qMode=EXACT&set_aside=8A,8AN&response_date.to={}+08:00&response_date.from={}+08:00'.format(
                random.randint(1e13, 2e13), self.page, self.size, self.param,
                time.strftime('%Y-%m-%d', time.localtime(time.time() + 3600 * 24 * 365)),
                time.strftime('%Y-%m-%d', time.localtime(time.time())))
        elif self.searchType == 'RP':
            url = r'https://sam.gov/api/prod/sgs/v1/search/?random={}&index=opp&page={}&sort=-modifiedDate&size={}&mode=search&responseType=json&is_active=true&q={}&qMode=EXACT&notice_type=r,p&response_date.to={}+08:00&response_date.from={}+08:00'.format(
                random.randint(1e13, 2e13), self.page, self.size, self.param,
                time.strftime('%Y-%m-%d', time.localtime(time.time() + 3600 * 24 * 365)),
                time.strftime('%Y-%m-%d', time.localtime(time.time())))
        elif self.searchType == 'O':
            url = r'https://sam.gov/api/prod/sgs/v1/search/?random={}&index=opp&page={}&sort=-modifiedDate&size={}&mode=search&responseType=json&is_active=true&q={}&qMode=EXACT&notice_type=o&response_date.to={}+08:00&response_date.from={}+08:00'.format(
                random.randint(1e13, 2e13), self.page, self.size, self.param,
                time.strftime('%Y-%m-%d', time.localtime(time.time() + 3600 * 24 * 365)),
                time.strftime('%Y-%m-%d', time.localtime(time.time())))
        elif self.searchType == 'WOSB':
            url = r'https://sam.gov/api/prod/sgs/v1/search/?random={}&index=opp&page={}&sort=-modifiedDate&size={}&mode=search&responseType=json&is_active=true&q={}&qMode=EXACT&set_aside=WOSB,EDWOSB&response_date.to={}+08:00&response_date.from={}+08:00'.format(
                random.randint(1e13, 2e13), self.page, self.size, self.param,
                time.strftime('%Y-%m-%d', time.localtime(time.time() + 3600 * 24 * 365)),
                time.strftime('%Y-%m-%d', time.localtime(time.time())))
        else:
            url = r'https://sam.gov/api/prod/sgs/v1/search/?random={}&index=opp&page={}&sort=-modifiedDate&size={}&mode=search&responseType=json&is_active=true&q={}&qMode=EXACT&response_date.to={}+08:00&response_date.from={}+08:00'.format(
                random.randint(1e13, 2e13), self.page, self.size, self.param,
                time.strftime('%Y-%m-%d', time.localtime(time.time() + 3600 * 24 * 365)),
                time.strftime('%Y-%m-%d', time.localtime(time.time())))

        # 交给调度器
        yield scrapy.Request(
            url=url,
            method='get',
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.77 Safari/537.36'
            },
            callback=self.parse
        )

    # 具体的爬取函数，根据不同网站，本函数不同
    def parse(self, response):
        html = response.text
        json_str = json.loads(html)
        res = json_str['_embedded']['results']
        self.logger.info(f"Found {len(res)} results")

        for item in res:
            url = 'https://sam.gov/api/prod/opps/v2/opportunities/{}?random={}'.format(item['_id'],
                                                                                       random.randint(1e13, 2e13))
            # 爬取详情页
            yield scrapy.Request(
                url=url,
                method='get',
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.77 Safari/537.36'
                },
                callback=self.parse_detail
            )

    def parse_detail(self, response):
        html = response.text
        json_str = json.loads(html)
        item = SamItem()
        item['searchType'] = self.searchType
        item['title'] = '-'
        try:
            item['title'] = json_str['data2']['title']
        except Exception as _:
            pass
        item['noticeId'] = '-'
        try:
            item['noticeId'] = json_str['data2']['solicitationNumber']
        except Exception as _:
            pass
        item['naics'] = '-'
        try:
            item['naics'] = json_str['data2']['naics'][0]['code'][0]
        except Exception as _:
            pass
        item['cot'] = '-'
        try:
            item['cot'] = self.shortToFull(json_str['data2']['type'])
        except Exception as _:
            pass
        item['state'] = '-'
        try:
            item['state'] = json_str['data2']['placeOfPerformance']['state']['code']
        except:
            pass
        item['city'] = '-'
        try:
            item['city'] = json_str['data2']['placeOfPerformance']['city']['name']
        except:
            pass
        item['osa'] = '-'
        try:
            setAside = json_str['data2']['solicitation']['setAside']
            if setAside == '8A':
                item['osa'] = '8(a) Set-Aside (FAR 19.8)'
            elif setAside == '8AN':
                item['osa'] = '8(a) Sole Source (FAR 19.8)'
            else:
                item['osa'] = setAside
        except:
            pass
        item['responseDate'] = '-'
        try:
            item['responseDate'] = self.timezoneTransform(json_str['data2']['solicitation']['deadlines']['response'])
        except:
            pass
        if item['responseDate'] == '-':
            try:
                item['responseDate'] = json_str['data2']['solicitation']['deadlines']['response']
            except:
                pass
        item['publishDate'] = '-'
        try:
            item['publishDate'] = self.timezoneTransform2(json_str['postedDate'])
        except:
            pass
        if item['publishDate'] == '-':
            try:
                item['publishDate'] = json_str['postedDate']
            except:
                pass
        item['email'] = '-'
        try:
            item['email'] = json_str['data2']['pointOfContact'][0]['email']
        except:
            pass
        item['link'] = 'https://sam.gov/opp/{}/view'.format(json_str['id'])
        self.logger.info('{}-{}-{}-{}-{}-{}-{}'.format(item['noticeId'], item['cot'], item['state'], item['city'],
                                                       item['responseDate'], item['email'], item['link']))

        # Check if organizationId exists
        try:
            item['organizationId'] = json_str['data2']['organizationId']
            # Only proceed to get more details if organizationId is available
            url = 'https://sam.gov/api/prod/federalorganizations/v1/organizations/{}?random={}&sort=name'.format(
                item['organizationId'], random.randint(1e13, 2e13))
            yield scrapy.Request(
                url=url,
                method='get',
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.77 Safari/537.36'
                },
                callback=self.parse_more,
                cb_kwargs=dict(item=item)
            )
        except:
            # If no organizationId, just yield the item directly
            self.logger.info("No organizationId found, yielding item directly")
            yield item

    def parse_more(self, response, item):
        html = response.text
        json_str = json.loads(html)
        item['department'] = '-'
        try:
            item['department'] = json_str['_embedded'][0]['org']['l1Name']
        except:
            self.logger.info("Could not parse department information")

        # Always yield the item after processing
        self.logger.info(f"Yielding complete item with department: {item['department']}")
        yield item

    def shortToFull(self, abbr):
        if abbr == "p":
            return "Presolicitation"
        elif abbr == "a":
            return "Award Notice"
        elif abbr == "m":
            return "Modification/Amendment"
        elif abbr == "r":
            return "Sources Sought"
        elif abbr == "s":
            return "Special Notice"
        elif abbr == "f":
            return "Foreign Government Standard"
        elif abbr == "g":
            return "Sale of Surplus Property"
        elif abbr == "k":
            return "Combined Synopsis/Solicitation"
        elif abbr == "j":
            return "Justification and Approval (J&A)"
        elif abbr == "i":
            return "Intent to Bundle Requirements"
        elif abbr == "l":
            return "Fair Opportunity / Limited Sources Justification"
        elif abbr == "o":
            return "Solicitation"
        elif abbr == "u":
            return "Justification"
        else:
            return abbr

    def timezoneTransform(self, time_str):
        # "2022-04-08T16:00:00-04:00"
        start_time_str = time_str[:-6]
        end_time_str = time_str.split(':')[0] + ':' + time_str[-5:]
        start = datetime.strptime(start_time_str, '%Y-%m-%dT%H:%M:%S')
        deltahour = -4
        try:
            deltahour = int(time_str[-6:].split(':')[0])
        except:
            deltahour = -4

        end = datetime.strptime(end_time_str, '%Y-%m-%dT%H:%M:%S')

        tz_utc__delta = timezone(timedelta(hours=deltahour))  # 网站上的时候均用的是时区UTC-4:00

        start_time = start.replace(tzinfo=tz_utc__delta)  # 设置时间的时区信息

        start_time_trans = start_time.astimezone(timezone(timedelta(hours=-7)))  # 将时区转化为utc-7区的时间

        return datetime.strftime(start_time_trans, '%Y-%m-%d %H:%M:%S')

    def timezoneTransform2(self, time_str):
        # "2022-07-22T21:50:57.483+00:00"
        start_time_str = time_str.split('.')[0]
        start = datetime.strptime(start_time_str, '%Y-%m-%dT%H:%M:%S')
        deltahour = -4
        try:
            deltahour = int(time_str[-6:].split(':')[0])
        except:
            deltahour = -4

        tz_utc__delta = timezone(timedelta(hours=deltahour))  # 网站上的时候均用的是时区UTC-4:00

        start_time = start.replace(tzinfo=tz_utc__delta)  # 设置时间的时区信息

        start_time_trans = start_time.astimezone(timezone(timedelta(hours=-7)))  # 将时区转化为utc-7区的时间

        return datetime.strftime(start_time_trans, '%Y-%m-%d %H:%M:%S')

    def after_404(self, response):
        self.is_200 = False