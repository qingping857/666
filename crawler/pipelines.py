import pymysql
from datetime import datetime, timedelta
import pytz
import logging
from API.SiliconFlowApi import siliconflow, ModelType
from crawler.storage import CrawlerStorage
from scrapy.utils.project import get_project_settings


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


class MySQLPipeline:
    """已弃用。请使用 SimpleDbPipeline 类替代"""

    def __init__(self):
        pass

    def process_item(self, item, spider):
        spider.logger.warning("使用了已弃用的 MySQLPipeline 类，该类不再执行任何操作")
        return item
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


class SamStoragePipeline:
    """已弃用。请使用 SimpleDbPipeline 类替代"""

    @classmethod
    def from_crawler(cls, crawler):
        return cls()

    def __init__(self, *args, **kwargs):
        pass

    def process_item(self, item, spider):
        spider.logger.warning("使用了已弃用的 SamStoragePipeline 类，该类不再执行任何操作")
        return item
    @classmethod
    def from_crawler(cls, crawler):
        """从Scrapy Crawler创建Pipeline实例"""
        return cls(
            mysql_host=crawler.settings.get('MYSQL_HOST', 'localhost'),
            mysql_user=crawler.settings.get('MYSQL_USER', 'root'),
            mysql_password=crawler.settings.get('MYSQL_PASSWORD', '123456'),
            mysql_db=crawler.settings.get('MYSQL_DB', 'sam_gov_data'),
            mysql_port=crawler.settings.get('MYSQL_PORT', 3306),
        )

    def open_spider(self, spider):
        """当Spider启动时初始化存储连接"""
        self.logger.info("初始化SamStoragePipeline...")
        try:
            self.storage = CrawlerStorage(
                host=self.mysql_host,
                user=self.mysql_user,
                password=self.mysql_password,
                database=self.mysql_db,
                port=self.mysql_port
            )
            # 验证数据库连接是否正常工作
            self.logger.info("数据库连接成功")
        except Exception as e:
            self.logger.error(f"数据库连接失败: {str(e)}")
            spider.logger.error(f"数据库连接失败: {str(e)}")

    def process_item(self, item, spider):
        """处理爬取到的每个项目"""
        try:
            # 转换为字典格式
            item_dict = dict(item)

            # 跳过国防部相关的机会
            if self._is_defense_department(item_dict.get('department', '')):
                spider.logger.info(f"跳过国防部项目: {item_dict.get('title', '')}")
                return item

            # 跳过截止日期临近的机会
            if self._is_deadline_too_close(item_dict.get('responseDate', '')):
                spider.logger.info(
                    f"跳过截止日期临近的项目: {item_dict.get('title', '')}, 截止日期: {item_dict.get('responseDate', '')}")
                return item

            # 使用qwen2模型判断项目title是否为纯计算机相关
            if not check_title_with_qwen2(item_dict.get('title', '')):
                spider.logger.info(f"跳过非计算机相关项目: {item_dict.get('title', '')}")
                return item

            # 记录处理开始
            self.logger.info(f"处理机会: {item_dict.get('title', '未知标题')[:30]}...")

            # 插入数据
            result = self.storage.insert_opportunity(item_dict)

            # 记录处理结果
            if result > 0:
                self.logger.info(f"成功存储机会: {item_dict.get('title', '未知标题')[:30]}")
            else:
                self.logger.info(f"机会可能已存在: {item_dict.get('title', '未知标题')[:30]}")

            return item

        except Exception as e:
            self.logger.error(f"处理项目时发生错误: {str(e)}")
            spider.logger.error(f"存储机会数据时出错: {str(e)}")
            # 仍然返回item，让其他pipeline继续处理
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
        """当Spider关闭时关闭连接"""
        self.logger.info("关闭SamStoragePipeline...")
        if hasattr(self, 'storage'):
            self.storage.close()