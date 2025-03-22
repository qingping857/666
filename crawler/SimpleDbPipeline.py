# SimpleDbPipeline.py
import pymysql
import logging
from datetime import datetime, timedelta
import pytz
import traceback


class SimpleDbPipeline:
    """
    简单的数据库管道，将Spider提取的数据存储到MySQL
    包含数据筛选功能
    """

    def __init__(self):
        self.connection = None
        self.cursor = None
        self.logger = logging.getLogger(__name__)
        # 初始化丹佛时区
        self.denver_tz = pytz.timezone('America/Denver')

    def open_spider(self, spider):
        """当Spider启动时初始化数据库连接"""
        try:
            # 连接到MySQL
            self.connection = pymysql.connect(
                host='localhost',
                user='root',
                password='123456',
                charset='utf8mb4'
            )
            self.cursor = self.connection.cursor()

            # 创建数据库
            self.cursor.execute("CREATE DATABASE IF NOT EXISTS sam_gov_data")
            self.cursor.execute("USE sam_gov_data")

            # 创建表
            self.create_table()

            spider.logger.info("数据库连接成功，表已创建/验证")
        except Exception as e:
            spider.logger.error(f"连接数据库时出错: {str(e)}")
            spider.logger.error(traceback.format_exc())

    def create_table(self):
        """创建数据表（如果不存在）"""
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
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY unique_notice (notice_id)
        )
        """
        self.cursor.execute(create_table_sql)
        self.connection.commit()

    def process_item(self, item, spider):
        """处理每个Item并存储到数据库，包含筛选逻辑"""
        try:
            # 转换为字典格式
            item_dict = dict(item)

            # 记录收到的项目
            spider.logger.info(f"处理Item: {item_dict.get('title', '')[:50]}")

            # 1. 筛选条件1: 跳过国防部相关的机会
            if self._is_defense_department(item_dict.get('department', '')):
                spider.logger.info(f"跳过国防部项目: {item_dict.get('title', '')}")
                return item

            # 2. 筛选条件2: 跳过截止日期临近的机会
            if self._is_deadline_too_close(item_dict.get('responseDate', '')):
                spider.logger.info(
                    f"跳过截止日期临近的项目: {item_dict.get('title', '')}, 截止日期: {item_dict.get('responseDate', '')}")
                return item

            # 3. 筛选条件3: 使用关键词匹配判断项目title是否为计算机相关
            if not self.check_title_with_keywords(item_dict.get('title', '')):
                spider.logger.info(f"跳过非计算机相关项目: {item_dict.get('title', '')}")
                return item

            # 跳过没有ID的项目
            if not item_dict.get('noticeId') or item_dict.get('noticeId') == '-':
                spider.logger.warning(f"跳过无效的项目（没有noticeId）: {item_dict}")
                return item

            # 构建SQL
            sql = """
            INSERT INTO sam_opportunities (
                publish_date, response_date, link, cot, osa, naics, 
                department, title, notice_id, state, city, email, 
                search_type, organization_id
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                publish_date = VALUES(publish_date),
                response_date = VALUES(response_date),
                link = VALUES(link),
                cot = VALUES(cot),
                osa = VALUES(osa),
                naics = VALUES(naics),
                department = VALUES(department),
                title = VALUES(title),
                state = VALUES(state),
                city = VALUES(city),
                email = VALUES(email),
                search_type = VALUES(search_type),
                organization_id = VALUES(organization_id)
            """

            values = (
                item_dict.get('publishDate', ''),
                item_dict.get('responseDate', ''),
                item_dict.get('link', ''),
                item_dict.get('cot', ''),
                item_dict.get('osa', ''),
                item_dict.get('naics', ''),
                item_dict.get('department', ''),
                item_dict.get('title', ''),
                item_dict.get('noticeId', ''),
                item_dict.get('state', ''),
                item_dict.get('city', ''),
                item_dict.get('email', ''),
                item_dict.get('searchType', ''),
                item_dict.get('organizationId', '')
            )

            # 执行插入
            self.cursor.execute(sql, values)
            self.connection.commit()
            spider.logger.info(f"成功存储项目到数据库，ID: {self.cursor.lastrowid}")
        except pymysql.err.IntegrityError as e:
            # 处理唯一键冲突
            if e.args[0] == 1062:  # 唯一键冲突错误码
                spider.logger.info(f"项目已存在: {item_dict.get('noticeId', '')}")
            else:
                spider.logger.error(f"数据库完整性错误: {str(e)}")
                self.connection.rollback()
        except Exception as e:
            spider.logger.error(f"存储项目失败: {str(e)}")
            spider.logger.error(traceback.format_exc())
            self.connection.rollback()

        return item

    def check_title_with_keywords(self, title):
        """
        判断项目title是否与计算机相关，使用关键词匹配
        """
        if not title or title == '-':
            return False

        # 计算机相关关键词
        computer_keywords = [
            'software', 'hardware', 'computer', 'network', 'cloud', 'cyber', 'data',
            'server', 'programming', 'development', 'web', 'application', 'app', 'ai',
            'machine learning', 'algorithm', 'security', 'database', 'it ', ' it ', 'information technology',
            'digital', 'system', 'platform', 'infrastructure', 'technology', 'internet', 'computing',
            'programmer', 'developer', 'analyst', 'administrator', 'engineer', 'coding', 'code',
            'automation', 'automated', 'interface', 'api', 'website', 'online', 'electronic',
            'virtualization', 'virtual', 'storage', 'backup', 'recovery', 'disaster recovery',
            'firewall', 'vpn', 'encryption', 'authentication', 'authorization', 'cyber security'
        ]

        title_lower = title.lower()
        for keyword in computer_keywords:
            if keyword in title_lower:
                self.logger.info(f"项目与计算机相关: {title}")
                return True

        self.logger.info(f"项目与计算机无关: {title}")
        return False

    def _is_defense_department(self, department):
        """检查部门是否与国防部相关"""
        if not department or department == '-':
            return False

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

        department_lower = department.lower()
        for keyword in defense_keywords:
            if keyword.lower() in department_lower:
                return True
        return False

    def _is_deadline_too_close(self, response_date_str):
        """
        检查截止日期是否距离当前丹佛时间不足14天
        """
        if not response_date_str or response_date_str.strip() == '' or response_date_str == '-':
            return False

        try:
            # 尝试多种常见日期格式解析响应日期
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
                self.logger.warning(f"无法解析日期格式: {response_date_str}")
                return False

            # 获取当前丹佛时区的时间
            now = datetime.now(self.denver_tz).replace(tzinfo=None)

            # 计算距离截止日期的天数
            days_until_deadline = (response_date - now).days

            self.logger.info(f"项目截止日期: {response_date}, 当前时间: {now}, 剩余天数: {days_until_deadline}")

            # 如果剩余时间少于14天则返回True
            return days_until_deadline < 14

        except Exception as e:
            self.logger.error(f"解析响应日期出错: {str(e)}, 日期字符串: {response_date_str}")
            return False

    def close_spider(self, spider):
        """当Spider关闭时关闭数据库连接"""
        spider.logger.info("关闭数据库连接")
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()