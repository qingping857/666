# interceptors.py
import time
import logging
import json
import traceback
from functools import wraps
from flask import request, g, jsonify, current_app
import jwt
from config import Config

# 配置日志
logger = logging.getLogger(__name__)


class RouteInterceptor:
    """路由拦截器类，用于管理各种Flask请求拦截器"""

    @staticmethod
    def log_request():
        """记录每个请求的详细信息"""
        try:
            # 获取请求信息
            request_info = {
                'method': request.method,
                'path': request.path,
                'ip': request.remote_addr,
                'user_agent': request.user_agent.string if request.user_agent else 'unknown',
                'timestamp': time.time()
            }

            # 对于敏感路径，不记录请求体
            sensitive_paths = ['/api/login', '/api/change-password', '/api/reset-password']
            if request.path not in sensitive_paths and request.is_json:
                request_info['data'] = request.get_json()

            # 记录请求详情
            logger.info(f"请求: {json.dumps(request_info, ensure_ascii=False)}")

            # 在请求上下文中保存开始时间，用于后续计算处理时间
            g.request_start_time = time.time()
        except Exception as e:
            logger.error(f"记录请求时出错: {str(e)}")

    @staticmethod
    def log_response(response):
        """记录响应信息和请求处理时间"""
        try:
            # 计算请求处理时间
            if hasattr(g, 'request_start_time'):
                duration = time.time() - g.request_start_time
                logger.info(f"响应: {request.path} - 状态: {response.status_code} - 耗时: {duration:.3f}秒")

            # 添加安全响应头
            response.headers['X-Content-Type-Options'] = 'nosniff'
            response.headers['X-Frame-Options'] = 'DENY'
            response.headers['X-XSS-Protection'] = '1; mode=block'
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'

            return response
        except Exception as e:
            logger.error(f"记录响应时出错: {str(e)}")
            return response

    @staticmethod
    def handle_options_request():
        """处理CORS预检请求"""
        if request.method == 'OPTIONS':
            response = jsonify({})
            # 添加CORS响应头
            response.headers.add('Access-Control-Allow-Origin', '*')
            response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
            response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
            response.headers.add('Access-Control-Max-Age', '86400')  # 24小时
            return response
        return None

    @staticmethod
    def authenticate_token(exempt_paths=None):
        """
        验证JWT令牌并将用户信息附加到g对象

        Args:
            exempt_paths: 豁免认证的路径列表
        """
        if exempt_paths is None:
            exempt_paths = ['/api/login', '/api/health']

        # 检查是否是豁免路径
        if request.path in exempt_paths:
            return

        # 检查是否是OPTIONS请求
        if request.method == 'OPTIONS':
            return

        # 获取认证令牌
        token = request.headers.get('Authorization')

        if not token:
            return jsonify({'success': False, 'message': '未提供认证令牌'}), 401

        try:
            # 去掉Bearer前缀
            if token.startswith('Bearer '):
                token = token[7:]

            # 验证并解码令牌
            payload = jwt.decode(
                token,
                Config.JWT_SECRET_KEY,
                algorithms=[Config.JWT_ALGORITHM]
            )

            # 将用户信息附加到g对象
            g.user = {
                'user_id': payload.get('user_id'),
                'username': payload.get('username'),
                'role': payload.get('role'),
                'exp': payload.get('exp')
            }

            # 检查密码是否已过期
            if payload.get('password_expired', False) and request.path != '/api/change-password':
                return jsonify({
                    'success': False,
                    'message': '密码已过期，请先更改密码',
                    'password_expired': True
                }), 403

        except jwt.ExpiredSignatureError:
            return jsonify({'success': False, 'message': '认证令牌已过期'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'success': False, 'message': '无效的认证令牌'}), 401
        except Exception as e:
            logger.error(f"令牌验证失败: {str(e)}")
            return jsonify({'success': False, 'message': '认证处理失败'}), 401

    @staticmethod
    def check_permission(permission=None):
        """
        检查用户是否拥有指定权限

        Args:
            permission: 所需的权限
        """
        if permission is None:
            return

        # 检查用户信息是否存在
        if not hasattr(g, 'user'):
            return jsonify({'success': False, 'message': '未授权访问'}), 403

        # 角色权限映射
        ROLES = {
            'admin': ['read', 'write', 'delete', 'manage_users'],
            'operator': ['read', 'write'],
            'viewer': ['read']
        }

        user_role = g.user.get('role')

        # 检查用户角色是否有权限
        if user_role not in ROLES or permission not in ROLES[user_role]:
            return jsonify({'success': False, 'message': '权限不足'}), 403


def register_interceptors(app):
    """注册所有拦截器到Flask应用"""

    # 请求前处理
    @app.before_request
    def before_request():
        # 记录请求信息
        RouteInterceptor.log_request()

        # 处理CORS预检请求
        options_response = RouteInterceptor.handle_options_request()
        if options_response:
            return options_response

        # 免认证路径
        exempt_paths = [
            '/api/login',
            '/api/health',
            '/api/docs',
            '/api/swagger'
        ]

        # 认证拦截
        auth_result = RouteInterceptor.authenticate_token(exempt_paths)
        if auth_result:
            return auth_result

        # 权限检查由路由装饰器处理

    # 响应后处理
    @app.after_request
    def after_request(response):
        return RouteInterceptor.log_response(response)

    # 错误处理
    @app.errorhandler(Exception)
    def handle_exception(e):
        logger.error(f"未处理的异常: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'message': '服务器内部错误',
            'error': str(e) if app.config.get('DEBUG', False) else None
        }), 500

    logger.info("拦截器已注册")


# 权限检查装饰器
def requires_permission(permission):
    """用于路由的权限检查装饰器"""

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not hasattr(g, 'user') or 'role' not in g.user:
                return jsonify({'success': False, 'message': '未授权访问'}), 403

            # 角色权限映射
            ROLES = {
                'admin': ['read', 'write', 'delete', 'manage_users'],
                'operator': ['read', 'write'],
                'viewer': ['read']
            }

            user_role = g.user['role']

            # 检查用户角色是否有权限
            if user_role not in ROLES or permission not in ROLES[user_role]:
                return jsonify({'success': False, 'message': '权限不足'}), 403

            return f(*args, **kwargs)

        return decorated_function

    return decorator


# 认证检查装饰器
def requires_auth(f):
    """检查用户是否已认证的装饰器"""

    @wraps(f)
    def decorated(*args, **kwargs):
        if not hasattr(g, 'user'):
            return jsonify({'success': False, 'message': '未授权访问'}), 401
        return f(*args, **kwargs)

    return decorated


# 速率限制装饰器
def rate_limit(f):
    """基本的速率限制装饰器"""

    @wraps(f)
    def decorated(*args, **kwargs):
        # 获取客户端 IP
        client_ip = request.remote_addr
        endpoint = request.endpoint

        # TODO: 实现速率限制逻辑
        # 在实际项目中，应使用Redis或Memcached等存储请求计数

        return f(*args, **kwargs)

    return decorated


# 输入清理装饰器
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