# config.py
import os
import secrets
from datetime import timedelta
import pymysql.cursors


class Config:
    """应用程序配置类 - 所有配置的中央位置"""
    # 日志级别
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')

    # 应用程序设置
    DEBUG = os.environ.get('DEBUG', 'False') == 'True'
    SECRET_KEY = os.environ.get('SECRET_KEY', secrets.token_hex(32))

    # JWT 设置
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY',
                                    'bf730d1675acb6cba1b881dec7f61a6256bd05db21c531175797eab2429aa804')
    JWT_ALGORITHM = 'HS256'
    JWT_EXPIRATION = timedelta(hours=24)
    JWT_REFRESH_EXPIRATION = timedelta(days=30)

    # 数据库设置
    DB_HOST = os.environ.get('DB_HOST', 'localhost')
    DB_USER = os.environ.get('DB_USER', 'root')
    DB_PASSWORD = os.environ.get('DB_PASSWORD', '123456')  # 生产环境应使用环境变量
    DB_NAME = os.environ.get('DB_NAME', 'sam_gov_data')
    DB_CHARSET = 'utf8mb4'

    # 密码策略设置
    PASSWORD_POLICY = os.environ.get('PASSWORD_POLICY', 'default')

    # 安全设置
    BCRYPT_LOG_ROUNDS = 12
    CSRF_ENABLED = True
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'False') == 'True'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

    # 速率限制
    RATELIMIT_DEFAULT = "100/hour"
    RATELIMIT_LOGIN = "5/minute"

    # 日志
    LOG_FILE = os.environ.get('LOG_FILE', 'app.log')

    # API密钥
    SILICONFLOW_API_KEY = os.environ.get('SILICONFLOW_API_KEY',
                                         'sk-enfjemlyxzhytrzbdgxlaoeygtbpsnovzkqlhyrjzbtegvim')  # 生产环境应使用环境变量

    @staticmethod
    def get_db_config():
        """返回数据库连接参数作为字典"""
        return {
            'host': Config.DB_HOST,
            'user': Config.DB_USER,
            'password': Config.DB_PASSWORD,
            'database': Config.DB_NAME,
            'charset': Config.DB_CHARSET,
            'cursorclass': pymysql.cursors.DictCursor
        }