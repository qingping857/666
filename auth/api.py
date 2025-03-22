from datetime import datetime
from flask import Flask, request, jsonify, g
from flask_cors import CORS
from config import Config
from database import Database
from auth import requires_auth, requires_permission, login
import logging

# 设置日志
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# 导入和注册中间件
from middleware import register_middleware

register_middleware(app)

# 导入和注册认证路由
from auth_routes import register_auth_routes

register_auth_routes(app)


@app.route('/api/login', methods=['POST'])
def api_login():
    try:
        # 获取请求数据
        data = request.get_json()
        if not data or 'username' not in data or 'password' not in data:
            return jsonify({'success': False, 'message': 'Missing username or password'}), 400

        username = data['username']
        password = data['password']
        ip_address = request.remote_addr

        # 使用统一的登录函数处理认证
        result = login(username, password, ip_address)

        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 401

    except Exception as e:
        logger.error(f"登录异常: {str(e)}")
        return jsonify({'success': False, 'message': f'Login failed: {str(e)}'}), 500


@app.route('/api/users', methods=['GET'])
@requires_auth
@requires_permission('manage_users')
def api_list_users():
    try:
        # 使用Database类查询用户列表
        users = Database.execute_query(
            "SELECT id, username, role, status FROM users ORDER BY username"
        )
        return jsonify({'success': True, 'users': users})
    except Exception as e:
        logger.error(f"获取用户列表失败: {str(e)}")
        return jsonify({'success': False, 'message': f'Failed to get the user list: {str(e)}'}), 500


@app.route('/api/users', methods=['POST'])
@requires_auth
@requires_permission('manage_users')
def api_create_user():
    try:
        data = request.get_json()
        if not data or 'username' not in data or 'password' not in data or 'role' not in data:
            return jsonify({'success': False, 'message': 'Please enter completely'}), 400

        # 导入创建用户函数
        from auth import create_user

        result = create_user(
            data['username'],
            data['password'],
            data['role'],
            g.user['user_id']
        )

        if result['success']:
            return jsonify(result)
        return jsonify(result), 400
    except Exception as e:
        logger.error(f"创建用户失败: {str(e)}")
        return jsonify({'success': False, 'message': f'创建用户失败: {str(e)}'}), 500


@app.route('/api/tasks', methods=['GET'])
@requires_auth
@requires_permission('read')
def api_list_tasks():
    try:
        # 查询爬虫任务
        tasks = Database.execute_query(
            "SELECT * FROM crawler_tasks ORDER BY created_at DESC"
        )
        return jsonify({'success': True, 'tasks': tasks})
    except Exception as e:
        logger.error(f"获取任务列表失败: {str(e)}")
        return jsonify({'success': False, 'message': f'Failed to get task list: {str(e)}'}), 500


@app.route('/api/tasks', methods=['POST'])
@requires_auth
@requires_permission('write')
def api_create_task():
    try:
        data = request.get_json()
        if not data or 'task_type' not in data or 'parameters' not in data:
            return jsonify({'success': False, 'message': 'Please enter completely'}), 400

        # 创建爬虫任务
        task_id = Database.execute_insert(
            """
            INSERT INTO crawler_tasks 
            (task_type, parameters, status, created_by, created_at) 
            VALUES (%s, %s, %s, %s, NOW())
            """,
            (
                data['task_type'],
                data['parameters'],
                'pending',
                g.user['user_id']
            )
        )

        return jsonify({
            'success': True,
            'message': 'The task is created',
            'task_id': task_id
        })
    except Exception as e:
        logger.error(f"创建任务失败: {str(e)}")
        return jsonify({'success': False, 'message': f'The task failed to be created: {str(e)}'}), 500


@app.route('/api/profile', methods=['GET'])
@requires_auth
def api_profile():
    try:
        # 返回当前用户信息
        return jsonify({
            'success': True,
            'user_id': g.user['user_id'],
            'username': g.user['username'],
            'role': g.user['role']
        })
    except Exception as e:
        logger.error(f"获取用户资料失败: {str(e)}")
        return jsonify({'success': False, 'message': f'Failed to get user profile: {str(e)}'}), 500


@app.route('/api/health', methods=['GET'])
def health_check():
    """系统健康检查接口"""
    return jsonify({
        'status': 'healthy',
        'version': '1.0.0',
        'timestamp': datetime.now().isoformat()
    })
@app.route('/api/sam-opportunities', methods=['GET'])
@requires_auth
@requires_permission('read')
def api_list_opportunities():
    try:
        # 查询SAM机会数据
        opportunities = Database.execute_query(
            "SELECT * FROM sam_opportunities ORDER BY publish_date DESC"
        )
        return jsonify({'success': True, 'opportunities': opportunities})
    except Exception as e:
        logger.error(f"获取SAM机会数据失败: {str(e)}")
        return jsonify({'success': False, 'message': f'Failed to get SAM opportunity data: {str(e)}'}), 500

# 全局错误处理
@app.errorhandler(404)
def not_found_error(error):
    return jsonify({'success': False, 'message': 'The requested resource could not be found'}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({'success': False, 'message': 'Server internal error'}), 500


if __name__ == '__main__':
    app.run(debug=Config.DEBUG, port=8888)