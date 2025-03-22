# Scrapy settings for crawler project

BOT_NAME = 'crawler'

SPIDER_MODULES = ['crawler.spiders']
NEWSPIDER_MODULE = 'crawler.spiders'

# Obey robots.txt rules
ROBOTSTXT_OBEY = False

# 本地图片存储位置
IMAGES_STORE = 'D:\\scrapyImage'

# 设置日志级别
LOG_LEVEL = 'INFO'

# 添加更多调试信息
LOG_ENABLED = True

# 启用存储Pipeline - 使用简化的管道
ITEM_PIPELINES = {
    'crawler.SimpleDbPipeline.SimpleDbPipeline': 300,
}

# MySQL连接设置
MYSQL_HOST = 'localhost'
MYSQL_USER = 'root'
MYSQL_PASSWORD = '123456'
MYSQL_DB = 'sam_gov_data'
MYSQL_PORT = 3306

# 设置下载延迟以避免被封
DOWNLOAD_DELAY = 0.01

# 设置下载超时
DOWNLOAD_TIMEOUT = 20

# 设置并发请求数
CONCURRENT_REQUESTS = 10

# 配置重试
RETRY_ENABLED = True
RETRY_TIMES = 3
RETRY_HTTP_CODES = [500, 502, 503, 504, 522, 524, 408, 429]