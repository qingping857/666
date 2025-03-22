# -*- coding: utf-8 -*-
# @Time    : 25/12/2016 5:35 PM
# @Author  : ddvv
# @Site    :
# @File    : run.py
# @Software: PyCharm

from scrapy.utils.project import get_project_settings
from scrapy.crawler import CrawlerProcess

import custom_mysql
pymysql.install_as_MySQLdb()

def main():
    setting = get_project_settings()
    process = CrawlerProcess(setting)
    didntWorkSpider = ['sample']

    for spider_name in process.spiders.list():
        if spider_name in didntWorkSpider :
            continue
        print("Running spider %s" % (spider_name))
        process.crawl(spider_name)
    process.start()


if __name__ == 'main':
    main()