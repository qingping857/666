# routes.py
from flask import Blueprint, request, jsonify, g
import logging
from middleware import requires_auth, requires_permission, sanitize_input, rate_limit
from auth import login, create_user, list_users, reset_password, toggle_user_status, change_password
from task_service import TaskService

logger = logging.getLogger(__name__)

# 创建API蓝图
api_bp = Blueprint('api', __name__, url_prefix='/api')
auth_bp = Blueprint('auth', __name__, url_prefix='/api')


# ====== 认证路由 ======

@auth_bp.route('/login', methods=['POST'])
@sanitize_input
@rate_limit
def api_login():
    """
    用户登录端点

    请求:
    {
        "username": "用户名",
        "password": "密码"
    }

    响应:
    {
        "success": true,
        "token": "JWT令牌",
        "role": "用户角色",
        "username": "用户名",
        "password_expired": 布尔值
    }
    """
    try:
        data = request.get_json()

        if not data or 'username' not in data or 'password' not in data:
            return jsonify({'success': False, 'message': '缺少用户名或密码'}), 400

        username = data['username']
        password = data['password']
        ip_address = request.remote_addr

        result = login(username, password, ip_address)

        if result['success']:
            return jsonify(result)
        return jsonify(result), 401
    except Exception as e:
        logger.error(f"登录处理失败: {str(e)}")
        return jsonify({'success': False, 'message': f'登录失败: {str(e)}'}), 500


@auth_bp.route('/logout', methods=['POST'])
@requires_auth
def api_logout():
    """
    用户注销端点

    注意: JWT是无状态的，所以这主要是用于客户端清理

    响应:
    {
        "success": true,
        "message": "已成功注销"
    }
    """
    # 记录注销操作
    user_id = g.user['user_id'] if hasattr(g, 'user') else None

    if user_id:
        # 这里可以记录注销日志
        pass

    return jsonify({
        'success': True,
        'message': '已成功注销'
    })


@auth_bp.route('/change-password', methods=['POST'])
@requires_auth
@sanitize_input
def api_change_password():
    """
    修改密码端点

    请求:
    {
        "old_password": "旧密码",
        "new_password": "新密码"
    }

    响应:
    {
        "success": true,
        "message": "密码修改成功"
    }
    """
    try:
        data = request.get_json()

        if not data or 'old_password' not in data or 'new_password' not in data:
            return jsonify({'success': False, 'message': '缺少旧密码或新密码'}), 400

        old_password = data['old_password']
        new_password = data['new_password']

        success, message = change_password(g.user['user_id'], old_password, new_password)

        if success:
            return jsonify({'success': True, 'message': message})
        return jsonify({'success': False, 'message': message}), 400
    except Exception as e:
        logger.error(f"修改密码失败: {str(e)}")
        return jsonify({'success': False, 'message': f'修改密码失败: {str(e)}'}), 500


@auth_bp.route('/reset-password-request', methods=['POST'])
@sanitize_input
@rate_limit
def api_reset_password_request():
    """
    请求密码重置（忘记密码）

    请求:
    {
        "username": "用户名"
    }

    响应:
    {
        "success": true,
        "message": "如果提供的用户名存在，重置链接将发送到关联的电子邮件"
    }
    """
    try:
        data = request.get_json()

        if not data or 'username' not in data:
            return jsonify({'success': False, 'message': '缺少用户名'}), 400

        username = data['username']

        # 这里应该实现发送密码重置邮件的逻辑
        # 出于安全考虑，无论用户名是否存在，都返回相同的消息

        return jsonify({
            'success': True,
            'message': '如果提供的用户名存在，重置链接已发送到关联的电子邮件'
        })
    except Exception as e:
        logger.error(f"处理密码重置请求失败: {str(e)}")
        return jsonify({'success': False, 'message': '服务器处理请求时出错'}), 500


@auth_bp.route('/reset-password', methods=['POST'])
@requires_auth
@requires_permission('manage_users')
@sanitize_input
def api_reset_password():
    """
    重置用户密码（仅管理员）

    请求:
    {
        "user_id": 用户ID,
        "new_password": "新密码"
    }

    响应:
    {
        "success": true,
        "message": "密码重置成功"
    }
    """
    try:
        data = request.get_json()

        if not data or 'user_id' not in data or 'new_password' not in data:
            return jsonify({'success': False, 'message': '缺少用户ID或新密码'}), 400

        user_id = data['user_id']
        new_password = data['new_password']

        result = reset_password(g.user['user_id'], user_id, new_password)

        if result['success']:
            return jsonify(result)
        return jsonify(result), 400
    except Exception as e:
        logger.error(f"重置密码失败: {str(e)}")
        return jsonify({'success': False, 'message': f'重置密码失败: {str(e)}'}), 500


# ====== 用户管理路由 ======

@api_bp.route('/users', methods=['GET'])
@requires_auth
@requires_permission('manage_users')
def api_list_users():
    """
    获取所有用户列表（仅管理员）

    响应:
    {
        "success": true,
        "users": [用户对象列表]
    }
    """
    try:
        result = list_users()

        if result['success']:
            return jsonify(result)
        return jsonify(result), 500
    except Exception as e:
        logger.error(f"获取用户列表失败: {str(e)}")
        return jsonify({'success': False, 'message': f'获取用户列表失败: {str(e)}'}), 500


@api_bp.route('/users', methods=['POST'])
@requires_auth
@requires_permission('manage_users')
@sanitize_input
def api_create_user():
    """
    创建新用户（仅管理员）

    请求:
    {
        "username": "用户名",
        "password": "密码",
        "role": "角色"
    }

    响应:
    {
        "success": true,
        "message": "用户创建成功",
        "user_id": 用户ID
    }
    """
    try:
        data = request.get_json()

        if not data or 'username' not in data or 'password' not in data or 'role' not in data:
            return jsonify({'success': False, 'message': '缺少必要参数'}), 400

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


@api_bp.route('/users/<int:user_id>/toggle-status', methods=['POST'])
@requires_auth
@requires_permission('manage_users')
def api_toggle_user_status(user_id):
    """
    激活或停用用户（仅管理员）

    请求:
    {
        "active": 布尔值
    }

    响应:
    {
        "success": true,
        "message": "用户已激活/停用"
    }
    """
    try:
        data = request.get_json()

        if not data or 'active' not in data:
            return jsonify({'success': False, 'message': '缺少激活状态参数'}), 400

        active = data['active']

        result = toggle_user_status(g.user['user_id'], user_id, active)

        if result['success']:
            return jsonify(result)
        return jsonify(result), 400
    except Exception as e:
        logger.error(f"切换用户状态失败: {str(e)}")
        return jsonify({'success': False, 'message': f'操作失败: {str(e)}'}), 500


# ====== 任务管理路由 ======

@api_bp.route('/tasks', methods=['GET'])
@requires_auth
@requires_permission('read')
def api_list_tasks():
    """
    获取爬虫任务列表

    查询参数:
    - limit: 最大返回任务数
    - status: 按状态筛选
    - mine: 如果为"true"，则筛选为用户自己的任务

    响应:
    {
        "success": true,
        "tasks": [任务对象列表]
    }
    """
    try:
        limit = request.args.get('limit', None)
        status = request.args.get('status', None)
        mine = request.args.get('mine', 'false').lower() == 'true'

        user_id = g.user['user_id'] if mine else None

        result = TaskService.list_tasks(user_id, limit, status)

        if result['success']:
            return jsonify(result)
        return jsonify(result), 500
    except Exception as e:
        logger.error(f"获取任务列表失败: {str(e)}")
        return jsonify({'success': False, 'message': f'获取任务列表失败: {str(e)}'}), 500


@api_bp.route('/tasks', methods=['POST'])
@requires_auth
@requires_permission('write')
@sanitize_input
def api_create_task():
    """
    创建新爬虫任务

    请求:
    {
        "task_type": "任务类型",
        "parameters": 参数对象
    }

    响应:
    {
        "success": true,
        "message": "任务创建成功",
        "task_id": 任务ID
    }
    """
    try:
        data = request.get_json()

        if not data or 'task_type' not in data or 'parameters' not in data:
            return jsonify({'success': False, 'message': '缺少必要参数'}), 400

        result = TaskService.create_task(
            data['task_type'],
            data['parameters'],
            g.user['user_id']
        )

        if result['success']:
            return jsonify(result)
        return jsonify(result), 400
    except Exception as e:
        logger.error(f"创建任务失败: {str(e)}")
        return jsonify({'success': False, 'message': f'创建任务失败: {str(e)}'}), 500


@api_bp.route('/tasks/<int:task_id>', methods=['GET'])
@requires_auth
@requires_permission('read')
def api_get_task(task_id):
    """
    获取特定任务的详情

    响应:
    {
        "success": true,
        "task": 任务对象
    }
    """
    try:
        result = TaskService.get_task(task_id)

        if result['success']:
            return jsonify(result)
        return jsonify(result), 404
    except Exception as e:
        logger.error(f"获取任务详情失败: {str(e)}")
        return jsonify({'success': False, 'message': f'获取任务详情失败: {str(e)}'}), 500


@api_bp.route('/tasks/<int:task_id>/status', methods=['PUT'])
@requires_auth
@requires_permission('write')
@sanitize_input
def api_update_task_status(task_id):
    """
    更新任务状态

    请求:
    {
        "status": "新状态",
        "result": 可选的结果数据
    }

    响应:
    {
        "success": true,
        "message": "任务状态已更新"
    }
    """
    try:
        data = request.get_json()

        if not data or 'status' not in data:
            return jsonify({'success': False, 'message': '缺少状态参数'}), 400

        result = TaskService.update_task_status(
            task_id,
            data['status'],
            data.get('result')
        )

        if result['success']:
            return jsonify(result)
        return jsonify(result), 400
    except Exception as e:
        logger.error(f"更新任务状态失败: {str(e)}")
        return jsonify({'success': False, 'message': f'更新任务状态失败: {str(e)}'}), 500


@api_bp.route('/tasks/<int:task_id>', methods=['DELETE'])
@requires_auth
@requires_permission('delete')
def api_delete_task(task_id):
    """
    删除任务

    响应:
    {
        "success": true,
        "message": "任务已删除"
    }
    """
    try:
        result = TaskService.delete_task(task_id, g.user['user_id'])

        if result['success']:
            return jsonify(result)
        return jsonify(result), 400
    except Exception as e:
        logger.error(f"删除任务失败: {str(e)}")
        return jsonify({'success': False, 'message': f'删除任务失败: {str(e)}'}), 500


# ====== 个人资料路由 ======

@api_bp.route('/profile', methods=['GET'])
@requires_auth
def api_get_profile():
    """
    获取当前用户资料

    响应:
    {
        "user_id": 用户ID,
        "username": "用户名",
        "role": "角色"
    }
    """
    try:
        return jsonify({
            'success': True,
            'user_id': g.user['user_id'],
            'username': g.user['username'],
            'role': g.user['role']
        })
    except Exception as e:
        logger.error(f"获取用户资料失败: {str(e)}")
        return jsonify({'success': False, 'message': f'获取用户资料失败: {str(e)}'}), 500


# ====== 系统路由 ======

@api_bp.route('/health', methods=['GET'])
def api_health_check():
    """
    系统健康检查

    响应:
    {
        "status": "healthy",
        "version": "1.0.0"
    }
    """
    return jsonify({
        'status': 'healthy',
        'version': '1.0.0'
    })