# middleware.py
import time
import logging
import json
from flask import request, g
import jwt
from functools import wraps
from config import Config

# 配置日志记录器
logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(getattr(logging, Config.LOG_LEVEL))

# 角色权限映射（与auth.py中的定义保持一致）
ROLES = {
    'admin': ['read', 'write', 'delete', 'manage_users'],
    'operator': ['read', 'write'],
    'viewer': ['read']
}


def log_request():
    """记录每个进入的请求"""
    try:
        request_data = {
            'method': request.method,
            'path': request.path,
            'ip': request.remote_addr,
            'user_agent': request.user_agent.string if request.user_agent else 'unknown',
            'timestamp': time.time()
        }

        # 避免记录敏感数据
        if request.path not in ['/api/login', '/api/change-password', '/api/users', '/api/reset-password']:
            if request.is_json:
                request_data['data'] = request.get_json()

        logger.info(f"请求: {json.dumps(request_data)}")
    except Exception as e:
        logger.error(f"记录请求时出错: {str(e)}")


def requires_auth(f):
    """验证JWT令牌并将用户信息附加到请求的装饰器"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')

        if not token:
            return {'message': '未提供认证令牌'}, 401

        try:
            # 去掉Bearer前缀
            if token.startswith('Bearer '):
                token = token[7:]

            # 解码JWT令牌
            payload = jwt.decode(
                token,
                Config.JWT_SECRET_KEY,
                algorithms=[Config.JWT_ALGORITHM]
            )

            # 检查密码是否过期并在需要时重定向
            if payload.get('password_expired', False) and request.path != '/api/change-password':
                return {'message': '密码已过期，请先更改密码', 'password_expired': True}, 403

            # 将用户信息存储在Flask g对象中
            g.user = payload
        except jwt.ExpiredSignatureError:
            return {'message': '认证令牌已过期'}, 401
        except jwt.InvalidTokenError:
            return {'message': '无效的认证令牌'}, 401
        except Exception as e:
            logger.error(f"认证过程中发生错误: {str(e)}")
            return {'message': '认证过程中发生错误'}, 401

        return f(*args, **kwargs)

    return decorated


def requires_permission(permission):
    """检查用户是否有指定权限的装饰器"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not hasattr(g, 'user') or 'role' not in g.user:
                return {'message': '未授权'}, 403

            user_role = g.user['role']
            if user_role not in ROLES or permission not in ROLES[user_role]:
                return {'message': '权限不足'}, 403

            return f(*args, **kwargs)

        return decorated_function

    return decorator


def sanitize_input(f):
    """清理用户输入以防止XSS和注入攻击"""
    @wraps(f)
    def decorated(*args, **kwargs):
        try:
            # 处理JSON数据
            if request.is_json:
                sanitized_data = {}
                data = request.get_json()

                if data:
                    # 处理每个字段
                    for key, value in data.items():
                        if isinstance(value, str):
                            # 基本的HTML转义
                            value = value.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                            value = value.replace('"', '&quot;').replace("'", '&#x27;')
                        sanitized_data[key] = value

                    # 用清理过的数据替换请求数据
                    request._cached_json = (sanitized_data, request._cached_json[1])
        except Exception as e:
            logger.error(f"输入清理过程中发生错误: {str(e)}")

        return f(*args, **kwargs)

    return decorated


def rate_limit(f):
    """基本的速率限制装饰器"""
    @wraps(f)
    def decorated(*args, **kwargs):
        # 获取客户端 IP
        client_ip = request.remote_addr
        endpoint = request.endpoint

        # 在实际实现中，您应该检查 redis/memcached 中时间窗口内的请求数

        # 这里是示例实现
        # 在生产环境中，使用 Flask-Limiter 或类似的库

        return f(*args, **kwargs)

    return decorated


def register_middleware(app):
    """将所有中间件注册到 Flask 应用"""
    @app.before_request
    def before_request():
        # 对所有请求应用中间件
        log_request()

        # 存储请求开始时间以便记录性能
        g.start_time = time.time()

    @app.after_request
    def after_request(response):
        # 计算请求持续时间
        if hasattr(g, 'start_time'):
            duration = time.time() - g.start_time
            logger.info(f"响应时间: {duration:.2f}s, 状态: {response.status_code}")

        # 添加安全头
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'

        return response