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


@api_bp.route('/opportunities', methods=['GET'])
@requires_auth
@requires_permission('read')
def list_opportunities():
    """获取所有机会数据"""
    try:
        # 可以添加分页和筛选参数
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        sort_by = request.args.get('sort_by', 'publish_date')
        sort_dir = request.args.get('sort_dir', 'desc')
        filter_dept = request.args.get('department')

        # 构建查询
        query_parts = ["SELECT * FROM sam_opportunities"]
        params = []

        # 添加过滤条件
        where_clauses = []
        if filter_dept:
            where_clauses.append("department LIKE %s")
            params.append(f"%{filter_dept}%")

        if where_clauses:
            query_parts.append("WHERE " + " AND ".join(where_clauses))

        # 添加排序
        query_parts.append(f"ORDER BY {sort_by} {sort_dir}")

        # 添加分页
        query_parts.append("LIMIT %s OFFSET %s")
        params.append(per_page)
        params.append((page - 1) * per_page)

        # 执行查询
        query = " ".join(query_parts)
        opportunities = Database.execute_query(query, params)

        # 获取总数
        count_query = "SELECT COUNT(*) as total FROM sam_opportunities"
        count_params = []

        if where_clauses:
            count_query += " WHERE " + " AND ".join(where_clauses)
            count_params = params[:-2]  # 排除LIMIT和OFFSET参数

        result = Database.execute_query_single(count_query, count_params)
        total = result['total'] if result else 0

        # 返回结果
        return jsonify({
            'success': True,
            'opportunities': opportunities,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page
            }
        })
    except Exception as e:
        logger.error(f"获取机会数据失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'获取机会数据失败: {str(e)}'
        }), 500


@api_bp.route('/departments', methods=['GET'])
@requires_auth
@requires_permission('read')
def list_departments():
    """获取所有部门列表，用于路由过滤功能"""
    try:
        # 获取唯一的部门列表
        departments = Database.execute_query(
            "SELECT DISTINCT department FROM sam_opportunities WHERE department IS NOT NULL ORDER BY department"
        )

        # 提取部门名称
        department_names = [dept['department'] for dept in departments if dept['department']]

        return jsonify({
            'success': True,
            'departments': department_names
        })
    except Exception as e:
        logger.error(f"获取部门列表失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'获取部门列表失败: {str(e)}'
        }), 500


@api_bp.route('/run-crawler', methods=['POST'])
@requires_auth
@requires_permission('write')
@sanitize_input
def run_crawler():
    """运行爬虫爬取数据"""
    try:
        # 获取请求数据
        data = request.json

        if not data:
            return jsonify({'success': False, 'message': '未提供数据'}), 400

        crawler_type = data.get('type', '8A')
        page_number = data.get('pageNumber', 1)
        page_size = data.get('pageSize', 200)
        params = data.get('params', '')

        # 验证参数
        try:
            page_number = int(page_number)
            if page_number <= 0:
                return jsonify({'success': False, 'message': '页码必须为正整数'}), 400
        except (ValueError, TypeError):
            return jsonify({'success': False, 'message': '页码必须为正整数'}), 400

        try:
            page_size = int(page_size)
            if page_size <= 0:
                return jsonify({'success': False, 'message': '页面大小必须为正整数'}), 400
        except (ValueError, TypeError):
            return jsonify({'success': False, 'message': '页面大小必须为正整数'}), 400

        # 记录爬虫任务
        task_id = Database.execute_insert(
            """
            INSERT INTO crawler_tasks 
            (task_type, parameters, status, created_by, created_at) 
            VALUES (%s, %s, %s, %s, NOW())
            """,
            (
                crawler_type,
                str({'page': page_number, 'size': page_size, 'params': params}),
                'pending',
                g.user['user_id']
            )
        )

        # 这里应该启动爬虫进程，通常会使用异步任务队列
        # 为简化，这里直接返回成功响应

        return jsonify({
            'success': True,
            'message': f'爬虫任务已创建，类型: {crawler_type}，参数: {params}',
            'task_id': task_id
        })
    except Exception as e:
        logger.error(f"创建爬虫任务失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'创建爬虫任务失败: {str(e)}'
        }), 500


@api_bp.route('/export-opportunities', methods=['GET'])
@requires_auth
@requires_permission('read')
def export_opportunities():
    """导出数据为Excel"""
    try:
        import pandas as pd
        import io
        from flask import send_file

        # 构建查询
        filter_dept = request.args.get('department')

        query_parts = ["SELECT * FROM sam_opportunities"]
        params = []

        # 添加过滤条件
        if filter_dept:
            query_parts.append("WHERE department LIKE %s")
            params.append(f"%{filter_dept}%")

        # 添加排序
        query_parts.append("ORDER BY publish_date DESC")

        # 执行查询
        query = " ".join(query_parts)
        opportunities = Database.execute_query(query, params)

        # 将数据转换为DataFrame
        df = pd.DataFrame(opportunities)

        # 创建内存中的Excel文件
        output = io.BytesIO()

        # 使用xlsxwriter引擎
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Opportunities', index=False)

            # 获取工作表对象以进行格式化
            workbook = writer.book
            worksheet = writer.sheets['Opportunities']

            # 设置列宽
            for i, col in enumerate(df.columns):
                # 计算列的最大宽度
                column_len = df[col].astype(str).str.len().max()
                # 标题的长度
                header_len = len(str(col))
                # 取最大值并加上一点额外空间
                max_len = max(column_len, header_len) + 2
                # 设置列宽
                worksheet.set_column(i, i, max_len)

        # 将指针设置到文件开头
        output.seek(0)

        # 发送文件
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name='opportunities.xlsx'
        )
    except Exception as e:
        logger.error(f"导出数据失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'导出数据失败: {str(e)}'
        }), 500


@api_bp.route('/profile', methods=['GET'])
@requires_auth
def get_profile():
    """获取当前用户的个人资料"""
    try:
        # 用户信息已经在拦截器中添加到g对象
        return jsonify({
            'success': True,
            'user': {
                'id': g.user['user_id'],
                'username': g.user['username'],
                'role': g.user['role']
            }
        })
    except Exception as e:
        logger.error(f"获取用户资料失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'获取用户资料失败: {str(e)}'
        }), 500