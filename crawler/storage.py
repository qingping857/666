import pymysql
import datetime
from typing import Dict, List, Any, Optional


class CrawlerStorage:
    """用于存储爬虫任务信息到sam_opportunities表中的类"""

    def __init__(self, host='localhost', user='root', password='123456', database='sam_gov_data', port=3306):
        """
        初始化MySQL连接

        Args:
            host: MySQL服务器地址
            user: 数据库用户名
            password: 数据库密码
            database: 数据库名称
            port: 数据库端口
        """
        self.connection = pymysql.connect(
            host=host,
            user=user,
            password=password,
            database=database,
            port=port,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )

    def insert_opportunity(self, opportunity_data: Dict[str, Any]) -> int:
        """
        插入新的机会数据到sam_opportunities表

        Args:
            opportunity_data: 机会数据字典

        Returns:
            插入的记录ID
        """
        # 重新格式化数据以匹配表结构 (根据pipelines.py中现有的字段)
        formatted_data = {
            'notice_id': opportunity_data.get('noticeId', ''),
            'publish_date': opportunity_data.get('publishDate', ''),
            'response_date': opportunity_data.get('responseDate', ''),
            'link': opportunity_data.get('link', ''),
            'cot': opportunity_data.get('cot', ''),
            'osa': opportunity_data.get('osa', ''),
            'naics': opportunity_data.get('naics', ''),
            'department': opportunity_data.get('department', ''),
            'title': opportunity_data.get('title', ''),
            'state': opportunity_data.get('state', ''),
            'city': opportunity_data.get('city', ''),
            'email': opportunity_data.get('email', ''),
            'search_type': opportunity_data.get('searchType', ''),
            'organization_id': opportunity_data.get('organizationId', '')
        }

        # 构建SQL语句
        fields = ', '.join(formatted_data.keys())
        placeholders = ', '.join(['%s'] * len(formatted_data))
        values = tuple(formatted_data.values())

        insert_sql = f"INSERT INTO sam_opportunities ({fields}) VALUES ({placeholders})"

        with self.connection.cursor() as cursor:
            try:
                cursor.execute(insert_sql, values)
                self.connection.commit()
                return cursor.lastrowid
            except pymysql.MySQLError as e:
                self.connection.rollback()
                error_code = e.args[0]
                if error_code == 1062:  # 重复键错误
                    print(f"记录已存在: {opportunity_data.get('noticeId', '')}")
                    return 0
                else:
                    print(f"插入数据时出错: {e}")
                    raise

    def update_opportunity(self, notice_id: str, update_data: Dict[str, Any]) -> bool:
        """
        更新已有的机会数据

        Args:
            notice_id: 通知ID
            update_data: 要更新的数据

        Returns:
            更新是否成功
        """
        # 构建SQL语句
        update_fields = []
        values = []

        for key, value in update_data.items():
            update_fields.append(f"{key} = %s")
            values.append(value)

        values.append(notice_id)

        update_sql = f"UPDATE sam_opportunities SET {', '.join(update_fields)} WHERE notice_id = %s"

        with self.connection.cursor() as cursor:
            try:
                result = cursor.execute(update_sql, tuple(values))
                self.connection.commit()
                return result > 0
            except pymysql.MySQLError as e:
                self.connection.rollback()
                print(f"更新数据时出错: {e}")
                raise

    def bulk_insert(self, opportunities: List[Dict[str, Any]]) -> int:
        """
        批量插入多个机会数据

        Args:
            opportunities: 机会数据列表

        Returns:
            插入的记录数量
        """
        if not opportunities:
            return 0

        success_count = 0
        for opp in opportunities:
            try:
                result = self.insert_opportunity(opp)
                if result > 0:
                    success_count += 1
            except Exception as e:
                print(f"批量插入中的单条记录出错: {e}")

        return success_count

    def close(self):
        """关闭数据库连接"""
        if hasattr(self, 'connection') and self.connection:
            self.connection.close()