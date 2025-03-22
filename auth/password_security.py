import base64
import os
import bcrypt
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import logging

logger = logging.getLogger(__name__)

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
        try:
            if isinstance(password, str):
                password = password.encode('utf-8')

            # 解码盐值
            if isinstance(stored_salt, str):
                salt = base64.b64decode(stored_salt)
            else:
                salt = stored_salt

            # 解码哈希值，提取迭代次数
            if isinstance(stored_hash, str):
                hash_data = base64.b64decode(stored_hash)
            else:
                hash_data = stored_hash

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
            except Exception as e:
                logger.debug(f"PBKDF2验证失败: {str(e)}")
                return False
        except Exception as e:
            logger.error(f"PBKDF2验证过程中出现异常: {str(e)}")
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
        try:
            if isinstance(password, str):
                password = password.encode('utf-8')

            if isinstance(stored_hash, str):
                # 检查是否是Base64编码的bcrypt哈希
                if not stored_hash.startswith('$2'):
                    try:
                        stored_hash = base64.b64decode(stored_hash)
                    except Exception as e:
                        logger.error(f"无法解码哈希值，可能不是Base64格式: {str(e)}")
                        return False
                else:
                    stored_hash = stored_hash.encode('utf-8')

            logger.debug(f"验证bcrypt密码, 哈希前缀: {stored_hash[:10] if isinstance(stored_hash, bytes) else 'N/A'}")
            return bcrypt.checkpw(password, stored_hash)
        except Exception as e:
            logger.error(f"bcrypt验证失败: {str(e)}")
            return False

    @classmethod
    def hash_password(cls, password, method=None):
        """
        使用推荐方法哈希密码

        参数:
            password: 要哈希的密码
            method: 可选的哈希方法 ('bcrypt', 'pbkdf2')

        返回:
            方法标识符和哈希结果的字典
        """
        if method is None:
            method = 'bcrypt'  # 默认使用bcrypt

        result = {
            'method': method
        }

        if method == 'bcrypt':
            hash_bytes = cls.hash_password_bcrypt(password)
            # 重要: 不要Base64编码bcrypt哈希，直接存储为字符串
            result['hash'] = hash_bytes.decode('utf-8')
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

        try:
            if method == 'bcrypt':
                return cls.verify_password_bcrypt(password, stored_data['hash'])
            elif method == 'pbkdf2':
                return cls.verify_password_pbkdf2(
                    password,
                    stored_data['salt'],
                    stored_data['hash']
                )
            else:
                logger.warning(f"不支持的哈希方法: {method}")
                return False
        except Exception as e:
            logger.error(f"密码验证过程中出现异常: {str(e)}")
            return False