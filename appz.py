import traceback
import pandas as pd
from flask import Flask, jsonify, request, g, send_file
from flask_cors import CORS
import logging
import os
import sys
import subprocess
from datetime import datetime
import io
import time
import random

# 确保当前目录在搜索路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 设置基础日志配置
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 创建应用实例
app = Flask(__name__)

# 配置CORS - 允许跨域请求
CORS(app,
     resources={r"/api/*": {"origins": "http://localhost:3000"}},
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
     allow_headers=["Content-Type", "Authorization"],
     supports_credentials=True)

try:
    # 尝试导入配置
    try:
        from config import Config

        # 配置应用
        app.config['SECRET_KEY'] = Config.SECRET_KEY
        app.config['DEBUG'] = Config.DEBUG
        # 设置日志级别
        log_level = getattr(logging, Config.LOG_LEVEL)
        logger.setLevel(log_level)
        app.logger.setLevel(log_level)
    except ImportError:
        logger.warning("无法导入Config，使用默认配置")
        app.config['SECRET_KEY'] = 'dev-key'
        app.config['DEBUG'] = True

    # 添加控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    app.logger.addHandler(console_handler)

    # 尝试导入数据库
    try:
        from database import Database

        has_database = True
    except ImportError:
        logger.warning("无法导入数据库模块，将使用模拟数据")
        has_database = False

    # 导入和注册拦截器
    try:
        from interceptors import register_interceptors

        register_interceptors(app)
        logger.info("已成功注册拦截器")
    except Exception as e:
        logger.warning(f"无法注册拦截器: {str(e)}")
        # 如果拦截器导入失败，尝试导入中间件（保留原代码的兼容性）
        try:
            from middleware import register_middleware

            register_middleware(app)
            logger.info("已成功加载中间件")
        except Exception as mid_error:
            logger.warning(f"无法加载中间件: {str(mid_error)}")

    # 导入认证路由
    try:
        from auth_routes import register_auth_routes

        register_auth_routes(app)
        logger.info("已成功加载认证路由")
    except Exception as e:
        logger.warning(f"无法加载认证路由: {str(e)}")

    # 导入API路由（如果存在）
    try:
        from routes import api_bp

        app.register_blueprint(api_bp)
        logger.info("已成功注册API路由蓝图")
    except Exception as e:
        logger.warning(f"无法加载API路由蓝图: {str(e)}")
        logger.info("将使用内联API路由")

except Exception as e:
    logger.error(f"应用初始化失败: {str(e)}")
    logger.error(traceback.format_exc())


# ======================
# 全局OPTIONS处理
# ======================

@app.route('/api/<path:path>', methods=['OPTIONS'])
def handle_options(path):
    response = jsonify({})
    response.headers.add('Access-Control-Allow-Origin', 'http://localhost:3000')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    response.headers.add('Access-Control-Allow-Credentials', 'true')
    return response


# ======================
# 健康检查路由 - 不需要身份验证
# ======================

@app.route('/api/health', methods=['GET'])
def health_check():
    """系统健康检查接口"""
    return jsonify({
        'status': 'healthy',
        'version': '1.0.0',
        'timestamp': datetime.now().isoformat()
    })


# ======================
# 爬虫相关路由
# ======================

@app.route('/api/run-crawler', methods=['POST'])
def run_crawler():
    try:
        logger.info(f"收到爬虫请求: {request.json}")
        data = request.json

        if not data:
            logger.error("未收到JSON数据")
            return jsonify({"success": False, "message": "未提供数据"}), 400

        crawler_type = data.get('type', '8A')
        page_number = data.get('pageNumber', 1)
        page_size = data.get('pageSize', 200)
        params = data.get('params', '')

        logger.info(f"解析参数: type={crawler_type}, page={page_number}, size={page_size}, params={params}")

        # 验证参数
        try:
            page_number = int(page_number)
            if page_number <= 0:
                logger.error("无效的页码")
                return jsonify({"success": False, "message": "页码必须为正整数"}), 400
        except (ValueError, TypeError):
            logger.error(f"无效的页码格式: {page_number}")
            return jsonify({"success": False, "message": "页码必须为正整数"}), 400

        try:
            page_size = int(page_size)
            if page_size <= 0:
                logger.error("无效的页面大小")
                return jsonify({"success": False, "message": "页面大小必须为正整数"}), 400
        except (ValueError, TypeError):
            logger.error(f"无效的页面大小格式: {page_size}")
            return jsonify({"success": False, "message": "页面大小必须为正整数"}), 400

        # 直接使用Scrapy命令行运行爬虫
        cmd = [
            'scrapy', 'crawl', 'SamSearch',
            '-a', f'page={int(page_number) - 1}',  # 用户输入从1开始，但API从0开始
            '-a', f'size={page_size}',
            '-a', f'param={params}',
            '-a', f'searchType={crawler_type}'
        ]

        logger.info(f"执行命令: {' '.join(cmd)}")

        # 启动爬虫进程 - 作为后台进程运行
        try:
            process = subprocess.Popen(cmd)
            logger.info(f"爬虫进程已启动，PID: {process.pid}")
        except Exception as proc_error:
            logger.error(f"启动爬虫进程失败: {str(proc_error)}")
            return jsonify({"success": False, "message": f"启动爬虫进程失败: {str(proc_error)}"}), 500

        # 记录任务信息
        logger.info(f"爬虫任务已启动: type={crawler_type}, page={page_number}, size={page_size}, params={params}")

        # 为已认证用户记录到数据库
        if has_database and hasattr(g, 'user'):
            try:
                task_id = Database.execute_insert(
                    """
                    INSERT INTO crawler_tasks 
                    (task_type, parameters, status, created_by, created_at) 
                    VALUES (%s, %s, %s, %s, NOW())
                    """,
                    (
                        crawler_type,
                        str({'page': page_number, 'size': page_size, 'params': params}),
                        'running',
                        g.user.get('user_id')
                    )
                )
                logger.info(f"任务已记录到数据库，ID: {task_id}")
            except Exception as db_error:
                logger.error(f"记录任务到数据库失败: {str(db_error)}")

        # 返回成功响应，包含进程ID，前端可以用它来跟踪进程
        return jsonify({
            "success": True,
            "message": f"爬虫已启动: {crawler_type}, 页码: {page_number}, 每页数量: {page_size}",
            "pid": process.pid,
            "startTime": datetime.now().isoformat()
        })

    except Exception as e:
        error_msg = f"启动爬虫失败: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())  # 打印完整堆栈跟踪
        return jsonify({"success": False, "message": error_msg}), 500


# ======================
# API路由
# ======================

@app.route('/api/login', methods=['POST'])
def api_login():
    try:
        # 获取请求数据
        data = request.get_json()
        if not data or 'username' not in data or 'password' not in data:
            return jsonify({'success': False, 'message': '缺少用户名或密码'}), 400

        username = data['username']
        password = data['password']
        ip_address = request.remote_addr

        # 导入登录函数
        try:
            from auth import login
            # 使用统一的登录函数处理认证
            result = login(username, password, ip_address)
        except ImportError:
            # 如果没有auth模块，使用模拟认证
            logger.warning("未找到auth模块，使用模拟认证")
            if username == "admin" and password == "admin":
                result = {
                    'success': True,
                    'token': 'mock-token-123',
                    'username': username,
                    'role': 'admin'
                }
            else:
                result = {'success': False, 'message': '用户名或密码不正确'}

        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 401

    except Exception as e:
        logger.error(f"登录异常: {str(e)}")
        return jsonify({'success': False, 'message': f'登录失败: {str(e)}'}), 500


@app.route('/api/sam-opportunities', methods=['GET'])
def api_list_opportunities():
    try:
        # 可以添加分页和筛选参数
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        sort_by = request.args.get('sort_by', 'publish_date')
        sort_dir = request.args.get('sort_dir', 'desc')
        filter_dept = request.args.get('department')

        # 查询SAM机会数据
        logger.info("开始查询SAM机会数据")

        if has_database:
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

            logger.info(f"查询结果: 获取到{len(opportunities)}条记录，总共{total}条")

            # 返回结果，包含分页信息
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
        else:
            # 使用模拟数据
            logger.info("使用模拟数据")
            opportunities = [
                {
                    "id": 1,
                    "title": "Sources Sought - Digital Incentives",
                    "price": "N/A",
                    "duration": "N/A",
                    "count": "N/A",
                    "cycle": "N/A",
                    "publish_date": "2025-03-20 10:00:00",
                    "response_date": "2025-04-20 10:00:00",
                    "link": "https://sam.gov/example1",
                    "department": "Department of Example"
                },
                {
                    "id": 2,
                    "title": "Final Innovative Solutions Opening (ISO) ARPA-H Rare Disease AI/ML for Precision Integrated Diagnostics (RAPID)",
                    "price": "N/A",
                    "duration": "N/A",
                    "count": "N/A",
                    "cycle": "N/A",
                    "publish_date": "2025-03-18 09:30:00",
                    "response_date": "2025-04-18 09:30:00",
                    "link": "https://sam.gov/example2",
                    "department": "Department of Health"
                }
            ]

            # 过滤部门（如果需要）
            if filter_dept:
                opportunities = [o for o in opportunities if filter_dept.lower() in (o.get('department') or '').lower()]

            return jsonify({
                'success': True,
                'opportunities': opportunities,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': len(opportunities),
                    'pages': 1
                }
            })

    except Exception as e:
        logger.error(f"获取SAM机会数据失败: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'message': f'获取SAM机会数据失败: {str(e)}'}), 500


@app.route('/api/departments', methods=['GET'])
def api_list_departments():
    """获取所有部门列表，用于路由过滤功能"""
    try:
        # 获取唯一的部门列表
        if has_database:
            departments = Database.execute_query(
                "SELECT DISTINCT department FROM sam_opportunities WHERE department IS NOT NULL ORDER BY department"
            )

            # 提取部门名称
            department_names = [dept['department'] for dept in departments if dept['department']]
        else:
            # 使用模拟数据
            department_names = ["Department of Example", "Department of Health", "Department of Education"]

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


@app.route('/api/tasks', methods=['GET'])
def api_list_tasks():
    try:
        # 查询任务数据
        logger.info("开始查询任务数据")

        if has_database:
            tasks = Database.execute_query(
                "SELECT * FROM crawler_tasks ORDER BY created_at DESC"
            )
            logger.info(f"查询结果: 获取到{len(tasks)}条记录")
        else:
            # 使用模拟数据
            logger.info("使用模拟数据")
            tasks = [
                {
                    "id": 1,
                    "task_type": "8A",
                    "parameters": '{"page": 1, "size": 200, "params": "software"}',
                    "status": "completed",
                    "created_at": "2025-03-22 12:34:56"
                },
                {
                    "id": 2,
                    "task_type": "RP",
                    "parameters": '{"page": 1, "size": 200, "params": "cloud"}',
                    "status": "running",
                    "created_at": "2025-03-22 13:45:00"
                }
            ]

        return jsonify({'success': True, 'tasks': tasks})
    except Exception as e:
        logger.error(f"获取任务列表失败: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'message': f'获取任务列表失败: {str(e)}'}), 500


@app.route('/api/export-opportunities', methods=['GET'])
def export_opportunities():
    try:
        logger.info("开始导出数据为Excel...")

        # 获取过滤条件
        filter_dept = request.args.get('department')

        # 1. 从数据库或模拟数据获取数据
        if has_database:
            logger.info("正在从数据库查询数据...")
            try:
                # 构建查询
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

                logger.info(f"成功查询到 {len(opportunities)} 条记录")
            except Exception as db_error:
                logger.error(f"数据库查询失败: {str(db_error)}")
                logger.error(traceback.format_exc())
                return jsonify({'success': False, 'message': f'数据库查询失败: {str(db_error)}'}), 500
        else:
            # 使用模拟数据
            logger.info("数据库无数据")
            return jsonify({'success': False, 'message': '数据库无数据 '}), 404

        # 2. 将数据转换为DataFrame
        logger.info("将数据转换为DataFrame...")
        try:
            df = pd.DataFrame(opportunities)
            logger.info(f"DataFrame创建成功，包含 {len(df)} 行和 {len(df.columns)} 列")
        except Exception as df_error:
            logger.error(f"DataFrame创建失败: {str(df_error)}")
            logger.error(traceback.format_exc())
            return jsonify({'success': False, 'message': f'数据格式转换失败: {str(df_error)}'}), 500

        # 3. 创建Excel文件
        logger.info("创建Excel文件...")
        try:
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
            logger.info("Excel文件创建成功")

        except Exception as excel_error:
            logger.error(f"Excel创建失败: {str(excel_error)}")
            logger.error(traceback.format_exc())
            return jsonify({'success': False, 'message': f'Excel创建失败: {str(excel_error)}'}), 500

        # 4. 发送文件
        logger.info("发送Excel文件到客户端...")
        try:
            return send_file(
                output,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name='opportunities.xlsx'
            )
        except Exception as send_error:
            logger.error(f"文件发送失败: {str(send_error)}")
            logger.error(traceback.format_exc())
            return jsonify({'success': False, 'message': f'文件发送失败: {str(send_error)}'}), 500

    except Exception as e:
        error_message = f"导出Excel时发生未知错误: {str(e)}"
        logger.error(error_message)
        logger.error(traceback.format_exc())
        return jsonify({'success': False, 'message': error_message}), 500


@app.route('/api/search-opportunities', methods=['POST'])
def api_search_opportunities():
    """接收前端关键词并启动爬虫"""
    try:
        data = request.json
        if not data:
            return jsonify({"success": False, "message": "未提供数据"}), 400

        keyword = data.get('keyword', '')
        crawler_type = data.get('type', '8A')
        page_number = data.get('page', 1)
        page_size = data.get('pageSize', 200)

        logger.info(f"接收到搜索请求: 关键词={keyword}, 类型={crawler_type}, 页码={page_number}, 每页数量={page_size}")

        # 参数验证
        if not keyword.strip():
            return jsonify({"success": False, "message": "请提供搜索关键词"}), 400

        # 构造爬虫命令
        cmd = [
            'scrapy', 'crawl', 'SamSearch',
            '-a', f'page={int(page_number) - 1}',  # 页码从0开始
            '-a', f'size={page_size}',
            '-a', f'param={keyword}',
            '-a', f'searchType={crawler_type}'
        ]

        logger.info(f"执行命令: {' '.join(cmd)}")

        # 启动爬虫进程
        process = subprocess.Popen(cmd)
        logger.info(f"爬虫进程已启动，PID: {process.pid}")

        # 记录任务信息
        logger.info(f"搜索任务已启动: keyword={keyword}, type={crawler_type}, page={page_number}, size={page_size}")

        # 设置任务ID，前端可以用它来查询结果
        task_id = f"{int(time.time())}-{random.randint(1000, 9999)}"

        return jsonify({
            "success": True,
            "message": f"搜索已启动，正在获取数据",
            "taskId": task_id
        })

    except Exception as e:
        error_msg = f"启动搜索失败: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        return jsonify({"success": False, "message": error_msg}), 500


# ======================
# 全局错误处理
# ======================

@app.errorhandler(404)
def not_found_error(error):
    return jsonify({'success': False, 'message': '找不到请求的资源'}), 404


@app.errorhandler(500)
def internal_error(error):
    logger.error(f"服务器内部错误: {str(error)}")
    return jsonify({'success': False, 'message': '服务器内部错误'}), 500


@app.errorhandler(Exception)
def handle_exception(e):
    logger.error(f"未处理的异常: {str(e)}", exc_info=True)
    return jsonify({'success': False, 'message': '服务器处理请求时出错'}), 500


if __name__ == '__main__':
    try:
        # 测试数据库连接（如果存在）
        if has_database:
            try:
                with Database.get_db_connection() as conn:
                    logger.info("数据库连接成功")
            except Exception as e:
                logger.error(f"数据库连接失败: {str(e)}")
                logger.warning("继续启动应用，但数据库功能可能不可用")

        # 启动应用
        port = 8888
        debug_mode = app.config.get('DEBUG', False)
        logger.info(f"启动应用，监听端口 {port}，调试模式: {debug_mode}")
        app.run(host='0.0.0.0', port=port, debug=debug_mode)
    except Exception as e:
        logger.critical(f"应用启动失败: {str(e)}", exc_info=True)