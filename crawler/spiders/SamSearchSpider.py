#!/usr/bin/python
# -*- coding: utf-8 -*-

import json
from ..items import SamItem
import scrapy
from datetime import datetime, timezone, timedelta
import random
import time
import traceback


class SamSearchSpider(scrapy.Spider):
    name = 'SamSearch'
    allowed_domains = ['sam.gov']
    handle_httpstatus_list = [404]
    is_200 = True

    def __init__(self, *args, **kwargs):
        super(SamSearchSpider, self).__init__(*args, **kwargs)
        self.page = 0
        try:
            self.page = kwargs.get('page')
        except:
            self.page = 0
        try:
            self.size = kwargs.get('size')
        except:
            self.size = 25
        try:
            self.param = kwargs.get('param', 'software')
        except:
            # 使用更具体的关键词作为默认值
            self.param = 'software'
        self.searchType = '8A'
        try:
            self.searchType = kwargs.get('searchType')
        except:
            self.searchType = '8A'
        self.logger.info("-------------------------------")
        self.logger.info("page: {}, size: {}, param: {}, searchType: {}".format(
            self.page, self.size, self.param, self.searchType))
        self.logger.info("-------------------------------")

    def start_requests(self):
        # 构建请求URL - 使用更有可能返回结果的查询
        if self.searchType == '8A':
            url = r'https://sam.gov/api/prod/sgs/v1/search/?random={}&index=opp&page={}&sort=-modifiedDate&size={}&mode=search&responseType=json&is_active=true&q={}&set_aside=8A,8AN'.format(
                random.randint(1e13, 2e13), self.page, self.size, self.param)
        elif self.searchType == 'WOSB':
            url = r'https://sam.gov/api/prod/sgs/v1/search/?random={}&index=opp&page={}&sort=-modifiedDate&size={}&mode=search&responseType=json&is_active=true&q={}&set_aside=WOSB,EDWOSB'.format(
                random.randint(1e13, 2e13), self.page, self.size, self.param)
        elif self.searchType == 'RP':
            url = r'https://sam.gov/api/prod/sgs/v1/search/?random={}&index=opp&page={}&sort=-modifiedDate&size={}&mode=search&responseType=json&is_active=true&q={}&notice_type=r,p'.format(
                random.randint(1e13, 2e13), self.page, self.size, self.param)
        elif self.searchType == 'O':
            url = r'https://sam.gov/api/prod/sgs/v1/search/?random={}&index=opp&page={}&sort=-modifiedDate&size={}&mode=search&responseType=json&is_active=true&q={}&notice_type=o'.format(
                random.randint(1e13, 2e13), self.page, self.size, self.param)
        else:
            url = r'https://sam.gov/api/prod/sgs/v1/search/?random={}&index=opp&page={}&sort=-modifiedDate&size={}&mode=search&responseType=json&is_active=true&q={}'.format(
                random.randint(1e13, 2e13), self.page, self.size, self.param)

        self.logger.info(f"Request URL: {url}")

        yield scrapy.Request(
            url=url,
            method='get',
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.77 Safari/537.36'
            },
            callback=self.parse
        )

    def parse(self, response):
        """爬取搜索结果页面"""
        try:
            html = response.text
            self.logger.info(f"收到API响应，长度: {len(html)}")

            json_str = json.loads(html)
            self.logger.info(f"API响应结构: {list(json_str.keys())}")

            # 确定结果集位置
            results = []

            # 检查是否有结果
            if '_embedded' in json_str and 'results' in json_str['_embedded']:
                # 标准路径
                results = json_str['_embedded']['results']
                self.logger.info(f"从 '_embedded.results' 找到 {len(results)} 个结果")
            elif 'page' in json_str and 'content' in json_str['page'] and isinstance(json_str['page']['content'], list):
                # 备用路径 - page.content
                results = json_str['page']['content']
                self.logger.info(f"从 'page.content' 找到 {len(results)} 个结果")
            elif 'data' in json_str and isinstance(json_str['data'], list):
                # 备用路径 - data
                results = json_str['data']
                self.logger.info(f"从 'data' 找到 {len(results)} 个结果")
            elif 'opportunities' in json_str and isinstance(json_str['opportunities'], list):
                # 备用路径 - opportunities
                results = json_str['opportunities']
                self.logger.info(f"从 'opportunities' 找到 {len(results)} 个结果")
            else:
                # 无法识别的响应结构，可能是空结果
                if 'page' in json_str and json_str['page'].get('totalElements', 0) == 0:
                    self.logger.info("API没有返回匹配结果，尝试减少过滤条件")
                else:
                    self.logger.warning(f"无法识别的API响应结构: {json_str.keys()}")
                    # 记录完整响应以便分析
                    with open(f'api_response_{int(time.time())}.json', 'w') as f:
                        json.dump(json_str, f, indent=2)
                    self.logger.info("已保存完整响应以供分析")
                return

            # 检查结果是否为空
            if not results:
                self.logger.info("解析后的结果集为空")
                return

            self.logger.info(f"总共找到 {len(results)} 个结果")

            # 处理每个结果项
            for item in results:
                # 尝试获取项目 ID
                item_id = None
                for id_field in ['_id', 'id', 'opportunityId', 'noticeId']:
                    if id_field in item:
                        item_id = item[id_field]
                        break

                if not item_id:
                    self.logger.warning(f"项目缺少 ID 字段: {item}")
                    continue

                # 构建详情页URL
                url = f'https://sam.gov/api/prod/opps/v2/opportunities/{item_id}?random={random.randint(1e13, 2e13)}'

                self.logger.info(f"获取详情页: {url}")

                # 爬取详情页
                yield scrapy.Request(
                    url=url,
                    method='get',
                    headers={
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.77 Safari/537.36'
                    },
                    callback=self.parse_detail,
                    errback=self.handle_error,
                    meta={'item_id': item_id}
                )
        except json.JSONDecodeError as e:
            self.logger.error(f"无法解析 JSON 响应: {e}")
            self.logger.debug(f"原始响应内容: {response.text[:500]}...")
        except Exception as e:
            self.logger.error(f"处理搜索结果时出错: {str(e)}")
            self.logger.error(traceback.format_exc())

    def handle_error(self, failure):
        """处理请求失败的情况"""
        self.logger.error(f"请求失败: {failure.value}")
        request = failure.request
        self.logger.error(f"失败的请求: {request.url}")

    def parse_detail(self, response):
        """处理详情页面"""
        self.logger.info(f"处理详情页: {response.url}")
        try:
            html = response.text
            json_str = json.loads(html)
            item = SamItem()
            item['searchType'] = self.searchType
            item['title'] = '-'
            try:
                item['title'] = json_str['data2']['title']
                self.logger.info(f"标题: {item['title']}")
            except Exception as e:
                self.logger.warning(f"无法提取标题: {str(e)}")

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
                item['responseDate'] = self.timezoneTransform(
                    json_str['data2']['solicitation']['deadlines']['response'])
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

            item['link'] = f'https://sam.gov/opp/{json_str["id"]}/view'

            # 提取组织ID
            item['organizationId'] = '-'
            try:
                item['organizationId'] = json_str['data2']['organizationId']
                # 只有在获取到组织ID时才获取更多详情
                url = f'https://sam.gov/api/prod/federalorganizations/v1/organizations/{item["organizationId"]}?random={random.randint(1e13, 2e13)}&sort=name'

                self.logger.info(f"获取组织详情: {url}")

                yield scrapy.Request(
                    url=url,
                    method='get',
                    headers={
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.77 Safari/537.36'
                    },
                    callback=self.parse_more,
                    cb_kwargs=dict(item=item)
                )
            except Exception as e:
                # 如果没有组织ID，直接返回Item
                self.logger.info(f"没有组织ID，直接返回Item: {str(e)}")
                item['department'] = '-'
                yield item
        except Exception as e:
            self.logger.error(f"解析详情页面时出错: {str(e)}")
            self.logger.error(traceback.format_exc())

    def parse_more(self, response, item):
        """处理组织详情页面"""
        self.logger.info(f"处理组织详情: {response.url}")
        try:
            html = response.text
            json_str = json.loads(html)
            item['department'] = '-'
            try:
                item['department'] = json_str['_embedded'][0]['org']['l1Name']
                self.logger.info(f"部门: {item['department']}")
            except Exception as e:
                self.logger.warning(f"无法解析部门信息: {str(e)}")
        except Exception as e:
            self.logger.error(f"解析组织详情时出错: {str(e)}")

        # 始终在处理后返回item
        self.logger.info(f"返回完整item，部门: {item['department']}")
        yield item

    def shortToFull(self, abbr):
        """将缩写转换为全称"""
        abbr_dict = {
            "p": "Presolicitation",
            "a": "Award Notice",
            "m": "Modification/Amendment",
            "r": "Sources Sought",
            "s": "Special Notice",
            "f": "Foreign Government Standard",
            "g": "Sale of Surplus Property",
            "k": "Combined Synopsis/Solicitation",
            "j": "Justification and Approval (J&A)",
            "i": "Intent to Bundle Requirements",
            "l": "Fair Opportunity / Limited Sources Justification",
            "o": "Solicitation",
            "u": "Justification"
        }
        return abbr_dict.get(abbr, abbr)

    def timezoneTransform(self, time_str):
        """第一种日期时间格式的时区转换"""
        try:
            start_time_str = time_str[:-6]
            deltahour = -4
            try:
                deltahour = int(time_str[-6:].split(':')[0])
            except:
                deltahour = -4

            start = datetime.strptime(start_time_str, '%Y-%m-%dT%H:%M:%S')
            tz_utc__delta = timezone(timedelta(hours=deltahour))
            start_time = start.replace(tzinfo=tz_utc__delta)
            start_time_trans = start_time.astimezone(timezone(timedelta(hours=-7)))
            return datetime.strftime(start_time_trans, '%Y-%m-%d %H:%M:%S')
        except Exception as e:
            self.logger.error(f"时区转换1失败: {str(e)}, 时间字符串: {time_str}")
            return time_str

    def timezoneTransform2(self, time_str):
        """第二种日期时间格式的时区转换"""
        try:
            start_time_str = time_str.split('.')[0]
            deltahour = -4
            try:
                deltahour = int(time_str[-6:].split(':')[0])
            except:
                deltahour = -4

            start = datetime.strptime(start_time_str, '%Y-%m-%dT%H:%M:%S')
            tz_utc__delta = timezone(timedelta(hours=deltahour))
            start_time = start.replace(tzinfo=tz_utc__delta)
            start_time_trans = start_time.astimezone(timezone(timedelta(hours=-7)))
            return datetime.strftime(start_time_trans, '%Y-%m-%d %H:%M:%S')
        except Exception as e:
            self.logger.error(f"时区转换2失败: {str(e)}, 时间字符串: {time_str}")
            return time_str