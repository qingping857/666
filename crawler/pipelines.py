import custom_mysql
from scrapy.utils.project import get_project_settings
import pymysql
from datetime import datetime, timedelta
import pytz
import requests  # 新增调用本地大模型所需模块

from API.SiliconFlowApi import siliconflow, ModelType


class CrawlerPipeline:
    def process_item(self, item, spider):
        return item


def check_title_with_qwen2(title):
    question1 = '''请判断以下项目 title 是否与人工智能，计算机,软件工程，前后端开发，深度学习，大模型，机器学习等相关，仅返回 'yes' 或 'no'。
        示例：
        1. "AI-Powered Data Analytics Platform" → yes
        2. "Cloud Computing Infrastructure Upgrade" → yes
        3. "Cybersecurity Risk Assessment" → yes
        4. "Bridge Construction and Design" → no
        5. "Urban Traffic Flow Optimization" → no

        项目 title: '''

    try:
        response = siliconflow(ModelType.V3, question1 + title)
        print(response)
        if "yes" in response:
            return True
        elif "no" in response:
            return False
    except Exception as e:
        print(f"调用DeepSeekV3模型出错: {e}")

    return False


class MySQLPipeline(object):
    def __init__(self):
        # Get database connection info from settings
        settings = get_project_settings()
        self.host = settings.get('MYSQL_HOST', 'localhost')
        self.user = settings.get('MYSQL_USER', 'root')
        self.password = settings.get('MYSQL_PASSWORD', 'password')
        self.database = settings.get('MYSQL_DB', 'sam_gov_data')
        self.port = settings.get('MYSQL_PORT', 3306)

        # Connect to MySQL database
        self.connection = pymysql.connect(
            host=self.host,
            user=self.user,
            password=self.password,
            port=self.port,
            charset='utf8mb4'
        )

        # Create cursor
        self.cursor = self.connection.cursor()

        # Create database if it doesn't exist
        self.cursor.execute(f"CREATE DATABASE IF NOT EXISTS {self.database}")
        self.cursor.execute(f"USE {self.database}")

        # Create table if it doesn't exist
        self.create_table()

        # Set Denver timezone
        self.denver_tz = pytz.timezone('America/Denver')

    def create_table(self):
        # Create a table to store the data
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS sam_opportunities (
            id INT AUTO_INCREMENT PRIMARY KEY,
            publish_date VARCHAR(50),
            response_date VARCHAR(50),
            link VARCHAR(255),
            cot VARCHAR(100),
            osa VARCHAR(100),
            naics VARCHAR(50),
            department VARCHAR(255),
            title TEXT,
            notice_id VARCHAR(100),
            state VARCHAR(50),
            city VARCHAR(100),
            email VARCHAR(100),
            search_type VARCHAR(20),
            organization_id VARCHAR(100),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        self.cursor.execute(create_table_sql)
        self.connection.commit()

    def process_item(self, item, spider):
        # 跳过国防部相关的机会
        if self._is_defense_department(item['department']):
            spider.logger.info(f"跳过国防部项目: {item['title']}")
            return item

        # 跳过距离截止日期不足14天的机会
        if self._is_deadline_too_close(item['responseDate']):
            spider.logger.info(f"跳过截止日期临近的项目: {item['title']}, 截止日期: {item['responseDate']}")
            return item

        # 使用qwen2模型判断项目title是否为纯计算机相关
        if not check_title_with_qwen2(item['title']):
            spider.logger.info(f"跳过非计算机相关项目: {item['title']}")
            return item

        # Insert data into MySQL table
        insert_sql = """
        INSERT INTO sam_opportunities (
            publish_date, response_date, link, cot, osa, naics, 
            department, title, notice_id, state, city, email, 
            search_type, organization_id
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        values = (
            item['publishDate'],
            item['responseDate'],
            item['link'],
            item['cot'],
            item['osa'],
            item['naics'],
            item['department'],
            item['title'],
            item['noticeId'],
            item['state'],
            item['city'],
            item['email'],
            item['searchType'],
            item.get('organizationId', '-')
        )

        # Execute the query
        self.cursor.execute(insert_sql, values)
        self.connection.commit()

        # Log the successful insertion
        spider.logger.info(f"Saved item to MySQL database: {item['title']}")

        return item

    def _is_defense_department(self, department):
        """检查部门是否与国防部相关"""
        defense_keywords = [
            "Department of Defense",
            "DoD",
            "Defense",
            "Army",
            "Navy",
            "Air Force",
            "Marine Corps",
            "Space Force",
            "National Guard",
            "Pentagon"
        ]

        if department:
            for keyword in defense_keywords:
                if keyword.lower() in department.lower():
                    return True
        return False

    def _is_deadline_too_close(self, response_date_str):
        """
        检查截止日期是否距离当前丹佛时间不足14天

        参数:
        response_date_str (str): 响应截止日期的字符串表示，可能包含时间部分

        返回:
        bool: 如果截止日期距离当前丹佛时间不足14天则返回True，否则返回False
        """
        if not response_date_str or response_date_str.strip() == '':
            return False

        try:
            # 尝试多种常见日期格式解析响应日期，包括带时间的格式
            formats = [
                "%Y-%m-%d %H:%M:%S",  # 例如: 2025-03-21 14:00:00
                "%Y-%m-%d %H:%M",  # 例如: 2025-03-21 14:00
                "%m/%d/%Y %H:%M:%S",  # 例如: 03/21/2025 14:00:00
                "%m/%d/%Y %H:%M",  # 例如: 03/21/2025 14:00
                "%Y-%m-%d",  # 例如: 2025-03-21
                "%m/%d/%Y",  # 例如: 03/21/2025
                "%m-%d-%Y",  # 例如: 03-21-2025
                "%d/%m/%Y",  # 例如: 21/03/2025
                "%Y/%m/%d"  # 例如: 2025/03/21
            ]

            response_date = None

            for date_format in formats:
                try:
                    response_date = datetime.strptime(response_date_str, date_format)
                    break
                except ValueError:
                    continue

            if not response_date:
                # 如果无法解析日期，记录并假设截止日期不是太近
                print(f"无法解析日期格式: {response_date_str}")
                return False

            # 获取当前丹佛时区的时间（移除时区信息以便与response_date比较）
            now = datetime.now(self.denver_tz).replace(tzinfo=None)

            # 计算距离截止日期的天数
            days_until_deadline = (response_date - now).days

            # 记录计算结果用于调试
            print(f"项目截止日期: {response_date}, 当前丹佛时间: {now}, 剩余天数: {days_until_deadline}")

            # 如果剩余时间少于14天则返回True
            return days_until_deadline < 14

        except Exception as e:
            # 如果解析日期时出错，记录错误并假设截止日期不是太近
            print(f"解析响应日期出错: {e}, 日期字符串: {response_date_str}")
            return False

    def close_spider(self, spider):
        # Close the database connection when the spider is closed
        self.cursor.close()
        self.connection.close()


# Keep the original Excel pipeline for reference or if you want to switch back
class ExcelPipeline(object):
    def __init__(self):
        from openpyxl import Workbook
        self.wb = Workbook()
        self.ws = self.wb.active

        self.ws.append([
            'Publish Date',
            'Response Date',
            'Link',
            'Contract Opportunity Type',
            'Original Set Aside',
            'NAICS',
            'department',
            'title'
        ])

    def process_item(self, item, spider):
        # 直接保存所有项目，没有任何筛选条件
        line = [
            item['publishDate'],
            item['responseDate'],
            item['link'],
            item['cot'],
            item['osa'],
            item['naics'],
            item['department'],
            item['title']
        ]
        self.ws.append(line)

        # 根据爬虫类型保存到不同的Excel文件
        searchType = item['searchType']
        if searchType == '8A':
            searchType = '8a'
        elif searchType == 'RP':
            searchType = 'SourceSought'
        elif searchType == 'O':
            searchType = 'Solictation'
        elif searchType == 'WOSB':
            searchType = 'WOSB'

        self.wb.save('res{}.xlsx'.format(searchType))
        return item
