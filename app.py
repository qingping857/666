# app.py
import traceback
import pandas as pd
from flask import Flask, jsonify, request, g, send_file
from flask_cors import CORS
import logging
import os
import sys
from datetime import datetime
import io

# 确保当前目录在搜索路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 设置基础日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 创建应用实例
app = Flask(__name__)

# 配置CORS - 修改部分
CORS(app,
     resources={r"/api/*": {"origins": "http://localhost:3000"}},
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
     allow_headers=["Content-Type", "Authorization"],
     supports_credentials=True)

# 添加一个全局的OPTIONS处理器 - 关键修改
@app.route('/api/<path:path>', methods=['OPTIONS'])
def handle_options(path):
    response = jsonify({})
    response.headers.add('Access-Control-Allow-Origin', 'http://localhost:3000')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    response.headers.add('Access-Control-Allow-Credentials', 'true')
    return response

try:
    # 直接从项目根目录导入配置
    from config import Config

    # 配置应用
    app.config['SECRET_KEY'] = Config.SECRET_KEY
    app.config['DEBUG'] = Config.DEBUG

    # 设置日志级别
    log_level = getattr(logging, Config.LOG_LEVEL)
    logger.setLevel(log_level)
    app.logger.setLevel(log_level)

    # 添加控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    app.logger.addHandler(console_handler)

    # 导入数据库
    from database import Database

    # 导入和注册中间件
    try:
        from middleware import register_middleware

        register_middleware(app)
        logger.info("已成功加载中间件")
    except Exception as e:
        logger.warning(f"无法加载中间件: {str(e)}")

    # 导入认证路由
    try:
        from auth_routes import register_auth_routes

        register_auth_routes(app)
        logger.info("已成功加载认证路由")
    except Exception as e:
        logger.warning(f"无法加载认证路由: {str(e)}")


    # 导入API路由
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
            from auth import login

            # 使用统一的登录函数处理认证
            result = login(username, password, ip_address)

            if result['success']:
                return jsonify(result)
            else:
                return jsonify(result), 401

        except Exception as e:
            logger.error(f"登录异常: {str(e)}")
            return jsonify({'success': False, 'message': f'登录失败: {str(e)}'}), 500


    @app.route('/api/users', methods=['GET'])
    def api_list_users():
        try:
            # 使用Database类查询用户列表
            users = Database.execute_query(
                "SELECT id, username, role, status FROM users ORDER BY username"
            )
            return jsonify({'success': True, 'users': users})
        except Exception as e:
            logger.error(f"获取用户列表失败: {str(e)}")
            return jsonify({'success': False, 'message': f'获取用户列表失败: {str(e)}'}), 500


    @app.route('/api/profile', methods=['GET'])
    def api_profile():
        try:
            # 这里应该有验证登录的逻辑
            # 临时返回模拟数据
            return jsonify({
                'success': True,
                'user_id': 1,
                'username': 'admin',
                'role': 'admin'
            })
        except Exception as e:
            logger.error(f"获取用户资料失败: {str(e)}")
            return jsonify({'success': False, 'message': f'获取用户资料失败: {str(e)}'}), 500


    # 修改SAM机会API路由
    @app.route('/api/sam-opportunities', methods=['GET'])
    def api_list_opportunities():
        try:
            # 查询SAM机会数据 - 使用正确的字段名 publish_date
            logger.info("开始查询SAM机会数据")

            opportunities = Database.execute_query(
                "SELECT * FROM sam_opportunities ORDER BY publish_date DESC"
            )

            logger.info(f"查询结果: 获取到{len(opportunities)}条记录")
            return jsonify({'success': True, 'opportunities': opportunities})
        except Exception as e:
            logger.error(f"获取SAM机会数据失败: {str(e)}", exc_info=True)
            return jsonify({'success': False, 'message': f'获取SAM机会数据失败: {str(e)}'}), 500


    @app.route('/api/tasks', methods=['GET'])
    def api_list_tasks():
        try:
            # 查询任务数据
            logger.info("开始查询任务数据")
            tasks = Database.execute_query(
                "SELECT * FROM crawler_tasks ORDER BY created_at DESC"
            )
            logger.info(f"查询结果: 获取到{len(tasks)}条记录")
            return jsonify({'success': True, 'tasks': tasks})
        except Exception as e:
            logger.error(f"获取任务列表失败: {str(e)}", exc_info=True)  # 记录完整堆栈
            return jsonify({'success': False, 'message': f'获取任务列表失败: {str(e)}'}), 500

    @app.route('/api/export-opportunities', methods=['GET'])
    def export_opportunities():
        try:
            logger.info("开始导出数据为Excel...")

            # 1. 从数据库获取数据
            from database import Database

            logger.info("正在从数据库查询数据...")
            try:
                opportunities = Database.execute_query(
                    "SELECT * FROM sam_opportunities ORDER BY publish_date DESC"
                )
                logger.info(f"成功查询到 {len(opportunities)} 条记录")
            except Exception as db_error:
                logger.error(f"数据库查询失败: {str(db_error)}")
                logger.error(traceback.format_exc())
                return jsonify({'success': False, 'message': f'数据库查询失败: {str(db_error)}'}), 500

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

except ImportError as e:
    logger.error(f"导入模块失败: {str(e)}")






# 全局错误处理
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


@app.route('/api/health', methods=['GET'])
def health_check():
    """系统健康检查接口"""
    return jsonify({
        'status': 'healthy',
        'version': '1.0.0',
        'timestamp': datetime.now().isoformat()
    })


if __name__ == '__main__':
    try:
        # 测试数据库连接
        try:
            with Database.get_db_connection() as conn:
                logger.info("数据库连接成功")
        except Exception as e:
            logger.error(f"数据库连接失败: {str(e)}")
            logger.warning("继续启动应用，但数据库功能可能不可用")

        # 启动应用
        port = 8888
        logger.info(f"启动应用，监听端口 {port}")
        app.run(host='0.0.0.0', port=port, debug=Config.DEBUG)
    except NameError:
        # Config可能未定义，使用默认值
        logger.warning("使用默认配置启动应用")
        app.run(host='0.0.0.0', port=8888, debug=False)
    except Exception as e:
        logger.critical(f"应用启动失败: {str(e)}", exc_info=True)