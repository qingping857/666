# Scrapy settings for crawler project

BOT_NAME = 'crawler'

SPIDER_MODULES = ['crawler.spiders']
NEWSPIDER_MODULE = 'crawler.spiders'


# Obey robots.txt rules
ROBOTSTXT_OBEY = False


# 本地图片存储位置
IMAGES_STORE = 'D:\\scrapyImage'
# 启动MySQL数据库中间件
ITEM_PIPELINES = {
    'crawler.pipelines.MySQLPipeline': 5,
}

# MySQL connection settings
MYSQL_HOST = 'localhost'
MYSQL_USER = 'root'
MYSQL_PASSWORD = '123456'  # Replace with your MySQL password
MYSQL_DB = 'sam_gov_data'
MYSQL_PORT = 3306