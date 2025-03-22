# auth.py
# 基本认证功能

import jwt
import datetime
import logging
from functools import wraps
from flask import request, jsonify, g
from config import Config
from database import Database

# 配置日志
logger = logging.getLogger(__name__)

# 用户角色与权限
ROLES = {
    'admin': ['read', 'write', 'delete', 'manage_users'],
    'operator': ['read', 'write'],
    'viewer': ['read']
}


# 登录函数
def login(username, password, ip_address):
    """
    用户登录并生成JWT令牌，包含详细调试日志
    """
    try:
        logger.info(f"尝试登录用户: {username}")

        # 获取用户信息
        user = Database.execute_query_single(
            """
            SELECT id, username, password_method, password_hash, password_salt, role, status 
            FROM users WHERE username = %s
            """,
            (username,)
        )

        if not user or user['status'] != 'active':
            logger.warning(f"用户 {username} 不存在或状态不活跃")
            # 这里应该记录失败的登录尝试，但为简化暂时跳过
            return {
                'success': False,
                'message': '用户名或密码错误'
            }

        # 记录用户信息以便调试
        logger.debug(f"验证用户: {username}, 方法: {user['password_method']}")
        logger.debug(f"存储的密码哈希类型: {type(user['password_hash'])}")
        logger.debug(
            f"存储的密码哈希前20个字符: {str(user['password_hash'])[:20] if user['password_hash'] else 'None'}")

        # 密码验证部分
        is_password_valid = False


        # bcrypt验证
        # 在auth.py中修改login函数中的bcrypt验证部分
        if user['password_method'] == 'bcrypt':
            import bcrypt
            logger.info("使用bcrypt验证密码")

            # 确保密码是字节格式
            password_bytes = password.encode('utf-8') if isinstance(password, str) else password

            # 确保存储的哈希是字节格式
            stored_hash = user['password_hash']
            if isinstance(stored_hash, str):
                stored_hash_bytes = stored_hash.encode('utf-8')
            else:
                stored_hash_bytes = stored_hash

            logger.debug(f"密码类型: {type(password_bytes)}")
            logger.debug(f"哈希值类型: {type(stored_hash_bytes)}")
            logger.debug(f"哈希值前缀: {stored_hash_bytes[:20] if stored_hash_bytes else 'None'}")

            try:
                # 尝试验证
                is_password_valid = bcrypt.checkpw(password_bytes, stored_hash_bytes)
                logger.info(f"bcrypt验证结果: {is_password_valid}")
            except Exception as e:
                logger.error(f"bcrypt验证异常: {str(e)}")
                is_password_valid = False


        # 如果密码验证失败
        if not is_password_valid:
            logger.warning(f"用户 {username} 密码验证失败")
            # 这里应该记录失败的登录尝试
            return {
                'success': False,
                'message': '用户名或密码错误'
            }

        # 如果通过验证，创建JWT令牌
        logger.info(f"用户 {username} 验证成功，生成令牌")
        payload = {
            'user_id': user['id'],
            'username': user['username'],
            'role': user['role'],
            'exp': datetime.datetime.utcnow() + Config.JWT_EXPIRATION
        }
        token = jwt.encode(payload, Config.JWT_SECRET_KEY, algorithm=Config.JWT_ALGORITHM)

        # 更新最后登录时间
        try:
            Database.execute_update(
                "UPDATE users SET last_login = NOW() WHERE id = %s",
                (user['id'],)
            )
        except Exception as e:
            logger.warning(f"更新最后登录时间失败: {str(e)}")

        return {
            'success': True,
            'token': token,
            'role': user['role'],
            'username': user['username']
        }
    except Exception as e:
        logger.error(f"登录处理失败: {str(e)}")
        return {'success': False, 'message': f'登录失败: {str(e)}'}


# 权限验证装饰器
def requires_auth(f):
    """验证JWT令牌并将用户信息附加到请求的装饰器"""

    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')

        if not token:
            return jsonify({'message': '未提供认证令牌'}), 401

        try:
            # 去掉Bearer前缀
            if token.startswith('Bearer '):
                token = token[7:]

            payload = jwt.decode(token, Config.JWT_SECRET_KEY, algorithms=[Config.JWT_ALGORITHM])
            g.user = payload
        except jwt.ExpiredSignatureError:
            return jsonify({'message': '认证令牌已过期'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': '无效的认证令牌'}), 401
        except Exception as e:
            logger.error(f"Token验证失败: {str(e)}")
            return jsonify({'message': '认证处理失败'}), 401

        return f(*args, **kwargs)

    return decorated


# 权限检查装饰器
def requires_permission(permission):
    """检查用户是否有指定权限的装饰器"""

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not hasattr(g, 'user') or 'role' not in g.user:
                return jsonify({'message': '未授权'}), 403

            user_role = g.user['role']
            if user_role not in ROLES or permission not in ROLES[user_role]:
                return jsonify({'message': '权限不足'}), 403

            return f(*args, **kwargs)

        return decorated_function

    return decorator


# 以下是其他您可能需要的函数占位符
# 实际实现可能需要更多代码

def create_user(username, password, role, created_by):
    """创建新用户"""
    # 实现用户创建逻辑
    return {'success': True, 'message': '用户创建成功', 'user_id': 1}


def change_password(user_id, old_password, new_password):
    """修改用户密码"""
    # 实现密码修改逻辑
    return True, "密码修改成功"


def reset_password(admin_id, user_id, new_password):
    """管理员重置用户密码"""
    # 实现密码重置逻辑
    return {'success': True, 'message': '密码重置成功'}


def list_users():
    """获取所有用户列表"""
    # 实现用户列表获取逻辑
    users = Database.execute_query(
        """
        SELECT id, username, role, status, created_at, last_login 
        FROM users
        """
    )
    return {'success': True, 'users': users}


def toggle_user_status(admin_id, user_id, active):
    """激活或停用用户"""
    # 实现用户状态切换逻辑
    return {'success': True, 'message': '用户状态已更新'}