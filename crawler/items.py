# Define here the models for your scraped items

import scrapy

class SamItem(scrapy.Item):
    searchType = scrapy.Field()
    title = scrapy.Field()
    noticeId = scrapy.Field()
    cot = scrapy.Field()
    state = scrapy.Field()
    city = scrapy.Field()
    publishDate = scrapy.Field()
    responseDate = scrapy.Field()
    email = scrapy.Field()
    link = scrapy.Field()
    osa = scrapy.Field()
    naics = scrapy.Field()
    organizationId = scrapy.Field()
    department = scrapy.Field()
    
    
