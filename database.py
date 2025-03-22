# database.py
import pymysql
import logging
from contextlib import contextmanager
from config import Config

# 配置日志
logger = logging.getLogger(__name__)

class Database:
    """数据库连接管理器 - 提供统一的数据库访问方法"""

    @classmethod
    @contextmanager
    def get_db_connection(cls):
        """数据库连接的上下文管理器"""
        connection = None
        try:
            connection = pymysql.connect(**Config.get_db_config())
            yield connection
            connection.commit()
        except Exception as e:
            logger.error(f"数据库连接错误: {str(e)}")
            if connection:
                connection.rollback()
            raise e
        finally:
            if connection:
                connection.close()

    @classmethod
    @contextmanager
    def get_cursor(cls):
        """数据库游标的上下文管理器"""
        with cls.get_db_connection() as connection:
            cursor = connection.cursor()
            try:
                yield cursor
            finally:
                cursor.close()

    @classmethod
    def execute_query(cls, query, params=None):
        """执行查询并返回所有结果"""
        with cls.get_cursor() as cursor:
            cursor.execute(query, params or ())
            return cursor.fetchall()

    @classmethod
    def execute_query_single(cls, query, params=None):
        """执行查询并返回单个结果"""
        with cls.get_cursor() as cursor:
            cursor.execute(query, params or ())
            return cursor.fetchone()

    @classmethod
    def execute_update(cls, query, params=None):
        """执行更新查询并返回受影响的行数"""
        with cls.get_db_connection() as connection:
            with connection.cursor() as cursor:
                result = cursor.execute(query, params or ())
                return result

    @classmethod
    def execute_insert(cls, query, params=None):
        """执行插入查询并返回最后一行的ID"""
        with cls.get_db_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(query, params or ())
                return cursor.lastrowid