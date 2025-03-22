# auth_service.py
import base64
import datetime

import bcrypt
import jwt
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from flask import request, jsonify

# database.py
import pymysql
from contextlib import contextmanager

# app_config.py
import os
import secrets
from datetime import timedelta
import pymysql.cursors

from auth import password_service


# Configuration class with all application settings
class Config:
    # Application settings
    DEBUG = os.environ.get('DEBUG', 'False') == 'True'
    SECRET_KEY = os.environ.get('SECRET_KEY', secrets.token_hex(32))

    # JWT settings
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', secrets.token_hex(32))
    JWT_ALGORITHM = 'HS256'
    JWT_EXPIRATION = timedelta(hours=24)
    JWT_REFRESH_EXPIRATION = timedelta(days=30)

    # Database settings
    DB_HOST = os.environ.get('DB_HOST', 'localhost')
    DB_USER = os.environ.get('DB_USER', 'root')
    DB_PASSWORD = os.environ.get('DB_PASSWORD', '123456')
    DB_NAME = os.environ.get('DB_NAME', 'sam_gov_data')
    DB_CHARSET = 'utf8mb4'

    # Password policy settings
    PASSWORD_POLICY = os.environ.get('PASSWORD_POLICY', 'default')

    # Security settings
    BCRYPT_LOG_ROUNDS = 12
    CSRF_ENABLED = True
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'False') == 'True'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

    # Rate limiting
    RATELIMIT_DEFAULT = "100/hour"
    RATELIMIT_LOGIN = "5/minute"

    # Logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FILE = os.environ.get('LOG_FILE', 'app.log')

    @staticmethod
    def get_db_config():
        """Return database connection parameters as a dictionary"""
        return {
            'host': Config.DB_HOST,
            'user': Config.DB_USER,
            'password': Config.DB_PASSWORD,
            'database': Config.DB_NAME,
            'charset': Config.DB_CHARSET,
            'cursorclass': pymysql.cursors.DictCursor
        }


# For compatibility with existing code
active_config = Config


class PasswordSecurity:
    """提供多种密码加密和验证方法的类"""

    @staticmethod
    def generate_salt(length=16):
        """生成随机盐值"""
        return os.urandom(length)

    @classmethod
    def hash_password_pbkdf2(cls, password, salt=None, iterations=390000):
        """
        使用PBKDF2算法哈希密码 (推荐用于新系统)

        参数:
            password: 要哈希的密码
            salt: 可选的盐值，如果未提供则生成新的
            iterations: 迭代次数，默认390000

        返回:
            (salt, hash) 元组，salt为bytes，hash为bytes
        """
        if salt is None:
            salt = cls.generate_salt()
        elif isinstance(salt, str):
            salt = salt.encode('utf-8')

        if isinstance(password, str):
            password = password.encode('utf-8')

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=iterations,
            backend=default_backend()
        )

        pw_hash = kdf.derive(password)

        # 将盐值、迭代次数和哈希一起存储
        return (
            base64.b64encode(salt),
            base64.b64encode(
                str(iterations).encode('utf-8') + b':' + pw_hash
            )
        )

    @classmethod
    def verify_password_pbkdf2(cls, password, stored_salt, stored_hash):
        """
        验证使用PBKDF2哈希的密码

        参数:
            password: 要验证的密码
            stored_salt: 存储的盐值 (base64编码的字符串)
            stored_hash: 存储的哈希值 (base64编码的字符串)

        返回:
            验证是否成功的布尔值
        """
        if isinstance(password, str):
            password = password.encode('utf-8')

        # 解码盐值
        salt = base64.b64decode(stored_salt)

        # 解码哈希值，提取迭代次数
        hash_data = base64.b64decode(stored_hash)
        parts = hash_data.split(b':', 1)
        iterations = int(parts[0].decode('utf-8'))
        stored_pw_hash = parts[1]

        # 创建相同的KDF
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=iterations,
            backend=default_backend()
        )

        # 对提供的密码进行哈希，然后比较
        try:
            kdf.verify(password, stored_pw_hash)
            return True
        except:
            return False

    @classmethod
    def hash_password_bcrypt(cls, password, rounds=12):
        """
        使用bcrypt算法哈希密码

        参数:
            password: 要哈希的密码
            rounds: 哈希轮数，默认12

        返回:
            哈希后的密码 (salt已内置在结果中)
        """
        if isinstance(password, str):
            password = password.encode('utf-8')

        # bcrypt会自动生成盐值并将其嵌入到哈希中
        return bcrypt.hashpw(password, bcrypt.gensalt(rounds=rounds))

    @classmethod
    def verify_password_bcrypt(cls, password, stored_hash):
        """
        验证使用bcrypt哈希的密码

        参数:
            password: 要验证的密码
            stored_hash: 存储的哈希值

        返回:
            验证是否成功的布尔值
        """
        if isinstance(password, str):
            password = password.encode('utf-8')

        if isinstance(stored_hash, str):
            stored_hash = stored_hash.encode('utf-8')

        return bcrypt.checkpw(password, stored_hash)

    @classmethod
    def hash_password_argon2(cls, password):
        """
        使用Argon2算法哈希密码 (如果安装了argon2-cffi)

        参数:
            password: 要哈希的密码

        返回:
            哈希后的密码
        """
        try:
            import argon2

            if isinstance(password, str):
                password = password.encode('utf-8')

            ph = argon2.PasswordHasher()
            return ph.hash(password)
        except ImportError:
            raise ImportError("请先安装argon2-cffi库: pip install argon2-cffi")

    @classmethod
    def verify_password_argon2(cls, password, stored_hash):
        """
        验证使用Argon2哈希的密码

        参数:
            password: 要验证的密码
            stored_hash: 存储的哈希值

        返回:
            验证是否成功的布尔值
        """
        try:
            import argon2

            if isinstance(password, str):
                password = password.encode('utf-8')

            ph = argon2.PasswordHasher()
            try:
                ph.verify(stored_hash, password)
                return True
            except:
                return False
        except ImportError:
            raise ImportError("请先安装argon2-cffi库: pip install argon2-cffi")

    @classmethod
    def get_recommended_method(cls):
        """获取推荐的密码哈希方法"""
        try:
            import argon2
            return "argon2"
        except ImportError:
            return "bcrypt" if bcrypt else "pbkdf2"

    @classmethod
    def hash_password(cls, password, method=None):
        """
        使用推荐方法哈希密码

        参数:
            password: 要哈希的密码
            method: 可选的哈希方法 ('argon2', 'bcrypt', 'pbkdf2')

        返回:
            方法标识符和哈希结果的字典
        """
        if method is None:
            method = cls.get_recommended_method()

        result = {
            'method': method
        }

        if method == 'argon2':
            result['hash'] = cls.hash_password_argon2(password)
        elif method == 'bcrypt':
            hash_bytes = cls.hash_password_bcrypt(password)
            result['hash'] = base64.b64encode(hash_bytes).decode('utf-8')
        elif method == 'pbkdf2':
            salt, pw_hash = cls.hash_password_pbkdf2(password)
            result['salt'] = salt.decode('utf-8')
            result['hash'] = pw_hash.decode('utf-8')
        else:
            raise ValueError(f"不支持的哈希方法: {method}")

        return result

    @classmethod
    def verify_password(cls, password, stored_data):
        """
        验证使用任何支持的方法哈希的密码

        参数:
            password: 要验证的密码
            stored_data: 存储的哈希数据字典 (包含method字段)

        返回:
            验证是否成功的布尔值
        """
        method = stored_data.get('method')

        if method == 'argon2':
            return cls.verify_password_argon2(password, stored_data['hash'])
        elif method == 'bcrypt':
            hash_bytes = base64.b64decode(stored_data['hash'])
            return cls.verify_password_bcrypt(password, hash_bytes)
        elif method == 'pbkdf2':
            return cls.verify_password_pbkdf2(
                password,
                stored_data['salt'],
                stored_data['hash']
            )
        else:
            raise ValueError(f"不支持的哈希方法: {method}")


class Database:
    """Database connection manager"""

    @classmethod
    @contextmanager
    def get_db_connection(cls):
        """Context manager for database connections"""
        connection = None
        try:
            connection = pymysql.connect(**Config.get_db_config())
            yield connection
            connection.commit()
        except Exception as e:
            if connection:
                connection.rollback()
            raise e
        finally:
            if connection:
                connection.close()

    @classmethod
    @contextmanager
    def get_cursor(cls):
        """Context manager for database cursors"""
        with cls.get_db_connection() as connection:
            cursor = connection.cursor()
            try:
                yield cursor
            finally:
                cursor.close()

    @classmethod
    def execute_query(cls, query, params=None):
        """Execute a query and return all results"""
        with cls.get_cursor() as cursor:
            cursor.execute(query, params or ())
            return cursor.fetchall()

    @classmethod
    def execute_query_single(cls, query, params=None):
        """Execute a query and return a single result"""
        with cls.get_cursor() as cursor:
            cursor.execute(query, params or ())
            return cursor.fetchone()

    @classmethod
    def execute_update(cls, query, params=None):
        """Execute an update query and return affected rows"""
        with cls.get_db_connection() as connection:
            with connection.cursor() as cursor:
                result = cursor.execute(query, params or ())
                return result

    @classmethod
    def execute_insert(cls, query, params=None):
        """Execute an insert query and return the last row id"""
        with cls.get_db_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(query, params or ())
                return cursor.lastrowid


class AuthService:
    """
    Authentication service to handle user login, token generation,
    and user management
    """

    @classmethod
    def generate_token(cls, user_data, password_expired=False):
        """Generate a JWT token for authenticated user"""
        now = datetime.datetime.utcnow()

        # Create payload
        payload = {
            'user_id': user_data['id'],
            'username': user_data['username'],
            'role': user_data['role'],
            'password_expired': password_expired,
            'iat': now,
            'exp': now + Config.JWT_EXPIRATION
        }

        # Encode token
        token = jwt.encode(
            payload,
            Config.JWT_SECRET_KEY,
            algorithm=Config.JWT_ALGORITHM
        )

        return token

    @classmethod
    def login(cls, username, password, ip_address):
        """
        Authenticate user and generate JWT token

        Args:
            username: User's username
            password: User's password
            ip_address: Client IP address

        Returns:
            Dictionary with login result and token if successful
        """
        # Check if account is locked
        password_service = PasswordService(Config.get_db_config())
        is_locked, remaining_minutes = password_service.check_account_lockout(username)

        if is_locked:
            return {
                'success': False,
                'message': f'账户已被锁定，请在{remaining_minutes}分钟后重试'
            }

        try:
            # Retrieve user data
            query = """
                SELECT id, username, password_method, password_hash, password_salt, role, status 
                FROM users WHERE username = %s
            """
            user = Database.execute_query_single(query, (username,))

            if not user or user['status'] != 'active':
                # Record failed login attempt
                is_locked = password_service.record_login_attempt(username, False, ip_address)
                return {
                    'success': False,
                    'message': '用户名或密码错误',
                    'locked': is_locked
                }

            # Verify password
            stored_data = {
                'method': user['password_method'],
                'hash': user['password_hash']
            }

            if user['password_salt']:
                stored_data['salt'] = user['password_salt']

            if not PasswordSecurity.verify_password(password, stored_data):
                # Record failed login attempt
                is_locked = password_service.record_login_attempt(username, False, ip_address)
                return {
                    'success': False,
                    'message': '用户名或密码错误',
                    'locked': is_locked
                }

            # Record successful login
            password_service.record_login_attempt(username, True, ip_address)

            # Check password expiration
            query = """
                SELECT MAX(created_at) as last_change 
                FROM password_history WHERE user_id = %s
            """
            result = Database.execute_query_single(query, (user['id'],))

            # Get password policy
            policy = password_service.get_password_policy()
            password_expired = False

            if policy and result and result['last_change']:
                max_age = datetime.timedelta(days=policy['max_age_days'])
                if datetime.datetime.now() - result['last_change'] > max_age:
                    password_expired = True

            # Generate token
            token = cls.generate_token(user, password_expired)

            # Update last login time
            Database.execute_update(
                "UPDATE users SET last_login = NOW() WHERE id = %s",
                (user['id'],)
            )

            return {
                'success': True,
                'token': token,
                'role': user['role'],
                'username': user['username'],
                'password_expired': password_expired
            }

        except Exception as e:
            return {'success': False, 'message': f'登录失败: {str(e)}'}

    # Other methods remain unchanged...
    # Following methods should be updated similarly to use Config directly:
    # - create_user
    # - list_users
    # - change_password
    # - reset_password
    # - toggle_user_status
    # - log_admin_action


import re
import datetime
import pymysql
from .password_security import PasswordSecurity


class PasswordService:
    """密码管理服务，包括密码策略验证、历史记录和账户锁定功能"""

    def __init__(self, db_config):
        """
        初始化密码服务

        参数:
            db_config: 数据库连接配置
        """
        self.db_config = db_config

    def get_db_connection(self):
        """获取数据库连接"""
        return pymysql.connect(
            **self.db_config,
            cursorclass=pymysql.cursors.DictCursor
        )

    def get_password_policy(self, policy_name='default'):
        """获取密码策略"""
        conn = self.get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM password_policies WHERE name = %s AND active = TRUE",
                    (policy_name,)
                )
                policy = cursor.fetchone()

                if not policy:
                    # 如果找不到指定策略，尝试获取默认策略
                    cursor.execute(
                        "SELECT * FROM password_policies WHERE name = 'default' AND active = TRUE"
                    )
                    policy = cursor.fetchone()

                return policy
        finally:
            conn.close()

    def validate_password_strength(self, password, policy_name='default'):
        """
        验证密码强度是否符合策略

        参数:
            password: 要验证的密码
            policy_name: 策略名称

        返回:
            (是否有效, 错误消息) 元组
        """
        policy = self.get_password_policy(policy_name)

        if not policy:
            return False, "无法获取密码策略"

        # 检查密码长度
        if len(password) < policy['min_length']:
            return False, f"密码长度必须至少为{policy['min_length']}个字符"

        # 检查大写字母
        if policy['require_uppercase'] and not re.search(r'[A-Z]', password):
            return False, "密码必须包含至少一个大写字母"

        # 检查小写字母
        if policy['require_lowercase'] and not re.search(r'[a-z]', password):
            return False, "密码必须包含至少一个小写字母"

        # 检查数字
        if policy['require_numbers'] and not re.search(r'\d', password):
            return False, "密码必须包含至少一个数字"

        # 检查特殊字符
        if policy['require_special_chars'] and not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            return False, "密码必须包含至少一个特殊字符"

        return True, ""

    def check_password_history(self, user_id, password, policy_name='default'):
        """
        检查密码是否在历史记录中

        参数:
            user_id: 用户ID
            password: 要检查的密码
            policy_name: 策略名称

        返回:
            (是否可用, 错误消息) 元组
        """
        policy = self.get_password_policy(policy_name)

        if not policy:
            return False, "无法获取密码策略"

        conn = self.get_db_connection()
        try:
            with conn.cursor() as cursor:
                # 获取最近的N个密码历史
                cursor.execute(
                    """
                    SELECT * FROM password_history 
                    WHERE user_id = %s 
                    ORDER BY created_at DESC 
                    LIMIT %s
                    """,
                    (user_id, policy['prevent_reuse_count'])
                )

                password_records = cursor.fetchall()

                # 检查是否与任何历史密码匹配
                for record in password_records:
                    stored_data = {
                        'method': record['password_method'],
                        'hash': record['password_hash'],
                    }

                    if record['password_salt']:
                        stored_data['salt'] = record['password_salt']

                    if PasswordSecurity.verify_password(password, stored_data):
                        return False, f"密码不能与最近{policy['prevent_reuse_count']}个使用过的密码相同"

                return True, ""
        finally:
            conn.close()

    def save_password_history(self, user_id, password_data):
        """
        保存密码历史记录

        参数:
            user_id: 用户ID
            password_data: 密码数据字典

        返回:
            操作是否成功
        """
        conn = self.get_db_connection()
        try:
            with conn.cursor() as cursor:
                salt = password_data.get('salt', None)

                cursor.execute(
                    """
                    INSERT INTO password_history 
                    (user_id, password_method, password_hash, password_salt, created_at) 
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        user_id,
                        password_data['method'],
                        password_data['hash'],
                        salt,
                        datetime.datetime.now()
                    )
                )
                conn.commit()
                return True
        except Exception as e:
            print(f"保存密码历史记录失败: {str(e)}")
            return False
        finally:
            conn.close()

    def check_account_lockout(self, username):
        """
        检查账户是否被锁定

        参数:
            username: 用户名

        返回:
            (是否锁定, 剩余锁定时间分钟数) 元组
        """
        policy = self.get_password_policy()

        if not policy:
            return False, 0

        conn = self.get_db_connection()
        try:
            with conn.cursor() as cursor:
                # 检查用户状态
                cursor.execute(
                    "SELECT status FROM users WHERE username = %s",
                    (username,)
                )
                user = cursor.fetchone()

                if not user:
                    # 不存在的用户，但不透露这一信息
                    return False, 0

                if user['status'] == 'locked':
                    # 获取最近一次锁定时间
                    cursor.execute(
                        """
                        SELECT MAX(attempt_time) as lock_time FROM login_logs 
                        WHERE username = %s AND lockout_action = 'lock' 
                        """,
                        (username,)
                    )
                    result = cursor.fetchone()

                    if result and result['lock_time']:
                        lock_time = result['lock_time']
                        now = datetime.datetime.now()
                        lockout_period = datetime.timedelta(minutes=policy['lockout_duration_minutes'])

                        if now - lock_time < lockout_period:
                            remaining_minutes = (lockout_period - (now - lock_time)).total_seconds() / 60
                            return True, int(remaining_minutes)
                        else:
                            # 锁定时间已过，自动解锁
                            cursor.execute(
                                "UPDATE users SET status = 'active' WHERE username = %s",
                                (username,)
                            )
                            conn.commit()

                return False, 0
        finally:
            conn.close()

    def record_login_attempt(self, username, success, ip_address):
        """
        记录登录尝试并处理账户锁定

        参数:
            username: 用户名
            success: 是否成功
            ip_address: IP地址

        返回:
            是否被锁定
        """
        policy = self.get_password_policy()

        if not policy:
            return False

        conn = self.get_db_connection()
        try:
            with conn.cursor() as cursor:
                # 记录尝试
                lockout_action = None

                if not success:
                    # 检查最近的失败尝试次数
                    cursor.execute(
                        """
                        SELECT COUNT(*) as fail_count FROM login_logs 
                        WHERE username = %s 
                        AND success = FALSE 
                        AND attempt_time > DATE_SUB(NOW(), INTERVAL 1 HOUR)
                        """,
                        (username,)
                    )
                    result = cursor.fetchone()
                    fail_count = result['fail_count'] + 1  # +1 包括当前失败

                    if fail_count >= policy['lockout_threshold']:
                        # 锁定账户
                        cursor.execute(
                            "UPDATE users SET status = 'locked' WHERE username = %s",
                            (username,)
                        )
                        lockout_action = 'lock'

                # 记录尝试
                cursor.execute(
                    """
                    INSERT INTO login_logs 
                    (username, success, ip_address, attempt_time, lockout_action) 
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (username, success, ip_address, datetime.datetime.now(), lockout_action)
                )

                if success:
                    # 成功登录时更新用户最后登录时间
                    cursor.execute(
                        "UPDATE users SET last_login = NOW() WHERE username = %s",
                        (username,)
                    )

                conn.commit()
                return lockout_action == 'lock'
        finally:
            conn.close()

    def change_password(self, user_id, old_password, new_password, policy_name='default'):
        """
        修改用户密码

        参数:
            user_id: 用户ID
            old_password: 旧密码
            new_password: 新密码
            policy_name: 策略名称

        返回:
            (是否成功, 消息) 元组
        """
        # 验证密码强度
        valid, message = self.validate_password_strength(new_password, policy_name)
        if not valid:
            return False, message

        conn = self.get_db_connection()
        try:
            with conn.cursor() as cursor:
                # 获取用户信息
                cursor.execute(
                    """
                    SELECT id, username, password_method, password_hash, password_salt 
                    FROM users WHERE id = %s
                    """,
                    (user_id,)
                )
                user = cursor.fetchone()

                if not user:
                    return False, "用户不存在"

                # 验证旧密码
                stored_data = {
                    'method': user['password_method'],
                    'hash': user['password_hash']
                }

                if user['password_salt']:
                    stored_data['salt'] = user['password_salt']

                if not PasswordSecurity.verify_password(old_password, stored_data):
                    return False, "旧密码不正确"

                # 检查密码历史
                valid, message = self.check_password_history(user_id, new_password, policy_name)
                if not valid:
                    return False, message

                # 哈希新密码
                password_data = PasswordSecurity.hash_password(new_password)

                # 更新用户密码
                cursor.execute(
                    """
                    UPDATE users 
                    SET password_method = %s, 
                        password_hash = %s, 
                        password_salt = %s
                    WHERE id = %s
                    """,
                    (
                        password_data['method'],
                        password_data['hash'],
                        password_data.get('salt'),
                        user_id
                    )
                )

                # 保存密码历史
                self.save_password_history(user_id, password_data)

                conn.commit()
                return True, "密码修改成功"
        except Exception as e:
            return False, f"修改密码失败: {str(e)}"
        finally:
            conn.close()
import re
import datetime
import pymysql
from .password_security import PasswordSecurity


class PasswordService:
    """密码管理服务，包括密码策略验证、历史记录和账户锁定功能"""

    def __init__(self, db_config):
        """
        初始化密码服务

        参数:
            db_config: 数据库连接配置
        """
        self.db_config = db_config

    def get_db_connection(self):
        """获取数据库连接"""
        # 使用硬编码的凭据（临时解决方案）
        db_config = {
            'host': 'localhost',
            'user': 'root',  # 替换为您的实际MySQL用户名
            'password': '123456',  # 替换为您的实际MySQL密码
            'database': 'sam_gov_data',
            'charset': 'utf8mb4',
            'cursorclass': pymysql.cursors.DictCursor
        }
        return pymysql.connect(**db_config)

    def get_password_policy(self, policy_name='default'):
        """获取密码策略"""
        conn = self.get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM password_policies WHERE name = %s AND active = TRUE",
                    (policy_name,)
                )
                policy = cursor.fetchone()

                if not policy:
                    # 如果找不到指定策略，尝试获取默认策略
                    cursor.execute(
                        "SELECT * FROM password_policies WHERE name = 'default' AND active = TRUE"
                    )
                    policy = cursor.fetchone()

                return policy
        finally:
            conn.close()

    def validate_password_strength(self, password, policy_name='default'):
        """
        验证密码强度是否符合策略

        参数:
            password: 要验证的密码
            policy_name: 策略名称

        返回:
            (是否有效, 错误消息) 元组
        """
        policy = self.get_password_policy(policy_name)

        if not policy:
            return False, "无法获取密码策略"

        # 检查密码长度
        if len(password) < policy['min_length']:
            return False, f"密码长度必须至少为{policy['min_length']}个字符"

        # 检查大写字母
        if policy['require_uppercase'] and not re.search(r'[A-Z]', password):
            return False, "密码必须包含至少一个大写字母"

        # 检查小写字母
        if policy['require_lowercase'] and not re.search(r'[a-z]', password):
            return False, "密码必须包含至少一个小写字母"

        # 检查数字
        if policy['require_numbers'] and not re.search(r'\d', password):
            return False, "密码必须包含至少一个数字"

        # 检查特殊字符
        if policy['require_special_chars'] and not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            return False, "密码必须包含至少一个特殊字符"

        return True, ""

    def check_password_history(self, user_id, password, policy_name='default'):
        """
        检查密码是否在历史记录中

        参数:
            user_id: 用户ID
            password: 要检查的密码
            policy_name: 策略名称

        返回:
            (是否可用, 错误消息) 元组
        """
        policy = self.get_password_policy(policy_name)

        if not policy:
            return False, "无法获取密码策略"

        conn = self.get_db_connection()
        try:
            with conn.cursor() as cursor:
                # 获取最近的N个密码历史
                cursor.execute(
                    """
                    SELECT * FROM password_history 
                    WHERE user_id = %s 
                    ORDER BY created_at DESC 
                    LIMIT %s
                    """,
                    (user_id, policy['prevent_reuse_count'])
                )

                password_records = cursor.fetchall()

                # 检查是否与任何历史密码匹配
                for record in password_records:
                    stored_data = {
                        'method': record['password_method'],
                        'hash': record['password_hash'],
                    }

                    if record['password_salt']:
                        stored_data['salt'] = record['password_salt']

                    if PasswordSecurity.verify_password(password, stored_data):
                        return False, f"密码不能与最近{policy['prevent_reuse_count']}个使用过的密码相同"

                return True, ""
        finally:
            conn.close()

    def save_password_history(self, user_id, password_data):
        """
        保存密码历史记录

        参数:
            user_id: 用户ID
            password_data: 密码数据字典

        返回:
            操作是否成功
        """
        conn = self.get_db_connection()
        try:
            with conn.cursor() as cursor:
                salt = password_data.get('salt', None)

                cursor.execute(
                    """
                    INSERT INTO password_history 
                    (user_id, password_method, password_hash, password_salt, created_at) 
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        user_id,
                        password_data['method'],
                        password_data['hash'],
                        salt,
                        datetime.datetime.now()
                    )
                )
                conn.commit()
                return True
        except Exception as e:
            print(f"保存密码历史记录失败: {str(e)}")
            return False
        finally:
            conn.close()

    def check_account_lockout(self, username):
        """
        检查账户是否被锁定

        参数:
            username: 用户名

        返回:
            (是否锁定, 剩余锁定时间分钟数) 元组
        """
        policy = self.get_password_policy()

        if not policy:
            return False, 0

        conn = self.get_db_connection()
        try:
            with conn.cursor() as cursor:
                # 检查用户状态
                cursor.execute(
                    "SELECT status FROM users WHERE username = %s",
                    (username,)
                )
                user = cursor.fetchone()

                if not user:
                    # 不存在的用户，但不透露这一信息
                    return False, 0

                if user['status'] == 'locked':
                    # 获取最近一次锁定时间
                    cursor.execute(
                        """
                        SELECT MAX(attempt_time) as lock_time FROM login_logs 
                        WHERE username = %s AND lockout_action = 'lock' 
                        """,
                        (username,)
                    )
                    result = cursor.fetchone()

                    if result and result['lock_time']:
                        lock_time = result['lock_time']
                        now = datetime.datetime.now()
                        lockout_period = datetime.timedelta(minutes=policy['lockout_duration_minutes'])

                        if now - lock_time < lockout_period:
                            remaining_minutes = (lockout_period - (now - lock_time)).total_seconds() / 60
                            return True, int(remaining_minutes)
                        else:
                            # 锁定时间已过，自动解锁
                            cursor.execute(
                                "UPDATE users SET status = 'active' WHERE username = %s",
                                (username,)
                            )
                            conn.commit()

                return False, 0
        finally:
            conn.close()

    def record_login_attempt(self, username, success, ip_address):
        """
        记录登录尝试并处理账户锁定

        参数:
            username: 用户名
            success: 是否成功
            ip_address: IP地址

        返回:
            是否被锁定
        """
        policy = self.get_password_policy()

        if not policy:
            return False

        conn = self.get_db_connection()
        try:
            with conn.cursor() as cursor:
                # 记录尝试
                lockout_action = None

                if not success:
                    # 检查最近的失败尝试次数
                    cursor.execute(
                        """
                        SELECT COUNT(*) as fail_count FROM login_logs 
                        WHERE username = %s 
                        AND success = FALSE 
                        AND attempt_time > DATE_SUB(NOW(), INTERVAL 1 HOUR)
                        """,
                        (username,)
                    )
                    result = cursor.fetchone()
                    fail_count = result['fail_count'] + 1  # +1 包括当前失败

                    if fail_count >= policy['lockout_threshold']:
                        # 锁定账户
                        cursor.execute(
                            "UPDATE users SET status = 'locked' WHERE username = %s",
                            (username,)
                        )
                        lockout_action = 'lock'

                # 记录尝试
                cursor.execute(
                    """
                    INSERT INTO login_logs 
                    (username, success, ip_address, attempt_time, lockout_action) 
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (username, success, ip_address, datetime.datetime.now(), lockout_action)
                )

                if success:
                    # 成功登录时更新用户最后登录时间
                    cursor.execute(
                        "UPDATE users SET last_login = NOW() WHERE username = %s",
                        (username,)
                    )

                conn.commit()
                return lockout_action == 'lock'
        finally:
            conn.close()

    def change_password(self, user_id, old_password, new_password, policy_name='default'):
        """
        修改用户密码

        参数:
            user_id: 用户ID
            old_password: 旧密码
            new_password: 新密码
            policy_name: 策略名称

        返回:
            (是否成功, 消息) 元组
        """
        # 验证密码强度
        valid, message = self.validate_password_strength(new_password, policy_name)
        if not valid:
            return False, message

        conn = self.get_db_connection()
        try:
            with conn.cursor() as cursor:
                # 获取用户信息
                cursor.execute(
                    """
                    SELECT id, username, password_method, password_hash, password_salt 
                    FROM users WHERE id = %s
                    """,
                    (user_id,)
                )
                user = cursor.fetchone()

                if not user:
                    return False, "用户不存在"

                # 验证旧密码
                stored_data = {
                    'method': user['password_method'],
                    'hash': user['password_hash']
                }

                if user['password_salt']:
                    stored_data['salt'] = user['password_salt']

                if not PasswordSecurity.verify_password(old_password, stored_data):
                    return False, "旧密码不正确"

                # 检查密码历史
                valid, message = self.check_password_history(user_id, new_password, policy_name)
                if not valid:
                    return False, message

                # 哈希新密码
                password_data = PasswordSecurity.hash_password(new_password)

                # 更新用户密码
                cursor.execute(
                    """
                    UPDATE users 
                    SET password_method = %s, 
                        password_hash = %s, 
                        password_salt = %s
                    WHERE id = %s
                    """,
                    (
                        password_data['method'],
                        password_data['hash'],
                        password_data.get('salt'),
                        user_id
                    )
                )

                # 保存密码历史
                self.save_password_history(user_id, password_data)

                conn.commit()
                return True, "密码修改成功"
        except Exception as e:
            return False, f"修改密码失败: {str(e)}"
        finally:
            conn.close()