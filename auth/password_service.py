# auth/password_service.py
import re
import datetime
import logging
from database import Database
from .password_security import PasswordSecurity

logger = logging.getLogger(__name__)

class PasswordService:
    """密码管理服务，包括密码策略验证、历史记录和账户锁定功能"""

    def get_password_policy(self, policy_name='default'):
        """获取密码策略"""
        try:
            policy = Database.execute_query_single(
                "SELECT * FROM password_policies WHERE name = %s AND active = TRUE",
                (policy_name,)
            )

            if not policy:
                # 如果找不到指定策略，尝试获取默认策略
                policy = Database.execute_query_single(
                    "SELECT * FROM password_policies WHERE name = 'default' AND active = TRUE"
                )

            return policy
        except Exception as e:
            logger.error(f"获取密码策略失败: {str(e)}")
            return None

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
        try:
            policy = self.get_password_policy(policy_name)

            if not policy:
                return False, "无法获取密码策略"

            # 获取最近的N个密码历史
            password_records = Database.execute_query(
                """
                SELECT * FROM password_history 
                WHERE user_id = %s 
                ORDER BY created_at DESC 
                LIMIT %s
                """,
                (user_id, policy['prevent_reuse_count'])
            )

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
        except Exception as e:
            logger.error(f"检查密码历史记录失败: {str(e)}")
            return False, f"检查密码历史时出错: {str(e)}"

    def save_password_history(self, user_id, password_data):
        """
        保存密码历史记录

        参数:
            user_id: 用户ID
            password_data: 密码数据字典

        返回:
            操作是否成功
        """
        try:
            salt = password_data.get('salt', None)

            Database.execute_insert(
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
            return True
        except Exception as e:
            logger.error(f"保存密码历史记录失败: {str(e)}")
            return False

    def check_account_lockout(self, username):
        """
        检查账户是否被锁定

        参数:
            username: 用户名

        返回:
            (是否锁定, 剩余锁定时间分钟数) 元组
        """
        try:
            policy = self.get_password_policy()

            if not policy:
                return False, 0

            # 检查用户状态
            user = Database.execute_query_single(
                "SELECT status FROM users WHERE username = %s",
                (username,)
            )

            if not user:
                # 不存在的用户，但不透露这一信息
                return False, 0

            if user['status'] == 'locked':
                # 获取最近一次锁定时间
                result = Database.execute_query_single(
                    """
                    SELECT MAX(attempt_time) as lock_time FROM login_logs 
                    WHERE username = %s AND lockout_action = 'lock' 
                    """,
                    (username,)
                )

                if result and result['lock_time']:
                    lock_time = result['lock_time']
                    now = datetime.datetime.now()
                    lockout_period = datetime.timedelta(minutes=policy['lockout_duration_minutes'])

                    if now - lock_time < lockout_period:
                        remaining_minutes = (lockout_period - (now - lock_time)).total_seconds() / 60
                        return True, int(remaining_minutes)
                    else:
                        # 锁定时间已过，自动解锁
                        Database.execute_update(
                            "UPDATE users SET status = 'active' WHERE username = %s",
                            (username,)
                        )

            return False, 0
        except Exception as e:
            logger.error(f"检查账户锁定状态失败: {str(e)}")
            return False, 0

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
        try:
            policy = self.get_password_policy()

            if not policy:
                return False

            # 记录尝试
            lockout_action = None

            if not success:
                # 检查最近的失败尝试次数
                result = Database.execute_query_single(
                    """
                    SELECT COUNT(*) as fail_count FROM login_logs 
                    WHERE username = %s 
                    AND success = FALSE 
                    AND attempt_time > DATE_SUB(NOW(), INTERVAL 1 HOUR)
                    """,
                    (username,)
                )
                fail_count = result['fail_count'] + 1  # +1 包括当前失败

                if fail_count >= policy['lockout_threshold']:
                    # 锁定账户
                    Database.execute_update(
                        "UPDATE users SET status = 'locked' WHERE username = %s",
                        (username,)
                    )
                    lockout_action = 'lock'

            # 记录尝试
            Database.execute_insert(
                """
                INSERT INTO login_logs 
                (username, success, ip_address, attempt_time, lockout_action) 
                VALUES (%s, %s, %s, %s, %s)
                """,
                (username, success, ip_address, datetime.datetime.now(), lockout_action)
            )

            if success:
                # 成功登录时更新用户最后登录时间
                Database.execute_update(
                    "UPDATE users SET last_login = NOW() WHERE username = %s",
                    (username,)
                )

            return lockout_action == 'lock'
        except Exception as e:
            logger.error(f"记录登录尝试失败: {str(e)}")
            return False

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
        try:
            # 验证密码强度
            valid, message = self.validate_password_strength(new_password, policy_name)
            if not valid:
                return False, message

            # 获取用户信息
            user = Database.execute_query_single(
                """
                SELECT id, username, password_method, password_hash, password_salt 
                FROM users WHERE id = %s
                """,
                (user_id,)
            )

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
            Database.execute_update(
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

            return True, "密码修改成功"
        except Exception as e:
            logger.error(f"修改密码失败: {str(e)}")
            return False, f"修改密码失败: {str(e)}"