# user_management.py
# 用于创建新用户或重置现有用户密码的实用脚本 - 改进版

import bcrypt
import pymysql
import sys
import getpass
import logging
import os
from datetime import datetime

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='user_management.log'  # 添加日志文件
)
logger = logging.getLogger(__name__)

# 数据库配置
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '123456',  # 此处应该使用环境变量或安全存储
    'database': 'sam_gov_data',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor,
    'connect_timeout': 10  # 添加连接超时
}


def get_db_connection():
    """获取数据库连接"""
    try:
        logger.info("尝试连接数据库...")
        conn = pymysql.connect(**DB_CONFIG)
        logger.info("数据库连接成功")
        return conn
    except Exception as e:
        logger.error(f"数据库连接失败: {str(e)}")
        print(f"错误: 无法连接到数据库。详情: {str(e)}")
        return None


def check_database_connection():
    """检查数据库连接和用户表是否存在"""
    conn = get_db_connection()
    if not conn:
        return False

    try:
        with conn.cursor() as cursor:
            # 检查用户表是否存在
            cursor.execute("SHOW TABLES LIKE 'users'")
            if not cursor.fetchone():
                print("错误: 'users' 表不存在，请先创建表")
                logger.error("'users' 表不存在")
                return False
            return True
    except Exception as e:
        logger.error(f"检查数据库结构时出错: {str(e)}")
        print(f"检查数据库结构时出错: {str(e)}")
        return False
    finally:
        conn.close()


def hash_password(password):
    """使用bcrypt哈希密码"""
    try:
        if isinstance(password, str):
            password = password.encode('utf-8')

        # 生成bcrypt哈希（以字符串形式返回，不使用Base64编码）
        hashed = bcrypt.hashpw(password, bcrypt.gensalt(rounds=12))
        return hashed.decode('utf-8')  # 存储为字符串
    except Exception as e:
        logger.error(f"密码哈希处理失败: {str(e)}")
        print(f"密码处理错误: {str(e)}")
        return None


def create_user(username, password, role='viewer'):
    """创建新用户"""
    logger.info(f"尝试创建用户: {username}, 角色: {role}")

    # 验证输入
    if not username or not password:
        print("错误: 用户名和密码不能为空")
        return False

    # 验证角色
    valid_roles = ['admin', 'operator', 'viewer']
    if role not in valid_roles:
        print(f"无效的角色。有效选项: {', '.join(valid_roles)}")
        return False

    # 哈希密码
    password_hash = hash_password(password)
    if not password_hash:
        return False

    # 插入用户
    conn = get_db_connection()
    if not conn:
        return False

    try:
        with conn.cursor() as cursor:
            # 检查用户是否已存在
            cursor.execute(
                "SELECT id FROM users WHERE username = %s",
                (username,)
            )
            if cursor.fetchone():
                print(f"用户 '{username}' 已存在!")
                logger.warning(f"创建用户失败 - 用户 '{username}' 已存在")
                return False

            # 创建用户
            cursor.execute(
                """
                INSERT INTO users 
                (username, password_method, password_hash, role, status, created_at) 
                VALUES (%s, %s, %s, %s, %s, NOW())
                """,
                (username, 'bcrypt', password_hash, role, 'active')
            )
            conn.commit()
            print(f"用户 '{username}' 创建成功，角色: {role}")
            logger.info(f"用户 '{username}' 创建成功，角色: {role}")
            return True
    except Exception as e:
        logger.error(f"创建用户时出错: {str(e)}")
        print(f"创建用户时出错: {str(e)}")
        return False
    finally:
        conn.close()


def reset_user_password(username, new_password):
    """重置用户密码"""
    logger.info(f"尝试重置用户密码: {username}")

    # 验证输入
    if not username or not new_password:
        print("错误: 用户名和密码不能为空")
        return False

    # 哈希新密码
    password_hash = hash_password(new_password)
    if not password_hash:
        return False

    # 更新用户密码
    conn = get_db_connection()
    if not conn:
        return False

    try:
        with conn.cursor() as cursor:
            # 检查用户是否存在
            cursor.execute(
                "SELECT id FROM users WHERE username = %s",
                (username,)
            )
            if not cursor.fetchone():
                print(f"用户 '{username}' 不存在!")
                logger.warning(f"重置密码失败 - 用户 '{username}' 不存在")
                return False

            # 更新密码
            cursor.execute(
                """
                UPDATE users 
                SET password_method = %s, 
                    password_hash = %s,
                    password_salt = NULL,
                    updated_at = NOW()
                WHERE username = %s
                """,
                ('bcrypt', password_hash, username)
            )
            conn.commit()
            print(f"用户 '{username}' 的密码已重置")
            logger.info(f"用户 '{username}' 的密码已重置")
            return True
    except Exception as e:
        logger.error(f"重置密码时出错: {str(e)}")
        print(f"重置密码时出错: {str(e)}")
        return False
    finally:
        conn.close()


def list_users():
    """列出所有用户"""
    logger.info("列出所有用户")

    conn = get_db_connection()
    if not conn:
        return False

    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT id, username, role, status, created_at, last_login FROM users ORDER BY username"
            )
            users = cursor.fetchall()

            if not users:
                print("没有找到用户")
                return True

            print("\n用户列表:")
            print("-" * 80)
            print(f"{'ID':<5} {'用户名':<15} {'角色':<10} {'状态':<10} {'创建时间':<20} {'最后登录':<20}")
            print("-" * 80)

            for user in users:
                created_at = user['created_at'].strftime('%Y-%m-%d %H:%M:%S') if user['created_at'] else ''
                last_login = user['last_login'].strftime('%Y-%m-%d %H:%M:%S') if user['last_login'] else ''

                print(f"{user['id']:<5} {user['username']:<15} {user['role']:<10} {user['status']:<10} "
                      f"{created_at:<20} {last_login:<20}")
            return True
    except Exception as e:
        logger.error(f"列出用户时出错: {str(e)}")
        print(f"列出用户时出错: {str(e)}")
        return False
    finally:
        conn.close()


def verify_login(username, password):
    """验证用户登录（用于测试）"""
    logger.info(f"验证用户登录: {username}")

    # 验证输入
    if not username or not password:
        print("错误: 用户名和密码不能为空")
        return False

    conn = get_db_connection()
    if not conn:
        return False

    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, username, password_method, password_hash, password_salt 
                FROM users WHERE username = %s
                """,
                (username,)
            )
            user = cursor.fetchone()

            if not user:
                print(f"用户 '{username}' 不存在")
                logger.warning(f"验证失败 - 用户 '{username}' 不存在")
                return False

            # 验证密码
            if user['password_method'] == 'bcrypt':
                # 确保密码是字节格式
                if isinstance(password, str):
                    password_bytes = password.encode('utf-8')
                else:
                    password_bytes = password

                # 确保哈希是字节格式
                stored_hash = user['password_hash']
                if isinstance(stored_hash, str):
                    stored_hash = stored_hash.encode('utf-8')

                try:
                    is_valid = bcrypt.checkpw(password_bytes, stored_hash)
                    print(f"密码验证结果: {'成功' if is_valid else '失败'}")
                    logger.info(f"密码验证结果: {'成功' if is_valid else '失败'}")

                    # 如果登录成功，更新最后登录时间
                    if is_valid:
                        cursor.execute(
                            "UPDATE users SET last_login = NOW() WHERE id = %s",
                            (user['id'],)
                        )
                        conn.commit()

                    return is_valid
                except Exception as e:
                    logger.error(f"bcrypt验证出错: {str(e)}")
                    print(f"bcrypt验证出错: {str(e)}")
                    return False
            else:
                print(f"不支持的密码方法: {user['password_method']}")
                logger.warning(f"不支持的密码方法: {user['password_method']}")
                return False
    except Exception as e:
        logger.error(f"验证登录时出错: {str(e)}")
        print(f"验证登录时出错: {str(e)}")
        return False
    finally:
        conn.close()


def initialize_database():
    """初始化数据库，创建用户表（如果不存在）"""
    logger.info("检查并初始化数据库")

    conn = get_db_connection()
    if not conn:
        return False

    try:
        with conn.cursor() as cursor:
            # 检查users表是否存在
            cursor.execute("SHOW TABLES LIKE 'users'")
            if cursor.fetchone():
                logger.info("users表已存在")
                return True

            # 创建users表
            cursor.execute("""
            CREATE TABLE users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) NOT NULL UNIQUE,
                password_method VARCHAR(20) NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                password_salt VARCHAR(255) NULL,
                role ENUM('admin', 'operator', 'viewer') NOT NULL DEFAULT 'viewer',
                status ENUM('active', 'inactive', 'locked') NOT NULL DEFAULT 'active',
                created_at DATETIME NOT NULL,
                updated_at DATETIME NULL,
                last_login DATETIME NULL,
                INDEX idx_username (username),
                INDEX idx_role (role),
                INDEX idx_status (status)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)

            print("成功创建users表")
            logger.info("成功创建users表")

            # 创建默认管理员用户
            admin_password = "admin123"  # 默认密码，应在首次登录后更改
            create_user("admin", admin_password, "admin")
            print("已创建默认管理员用户 (用户名: admin, 密码: admin123)")
            logger.info("已创建默认管理员用户")

            return True
    except Exception as e:
        logger.error(f"初始化数据库时出错: {str(e)}")
        print(f"初始化数据库时出错: {str(e)}")
        return False
    finally:
        conn.close()


def clear_screen():
    """清除控制台屏幕"""
    os.system('cls' if os.name == 'nt' else 'clear')


def main_menu():
    """主菜单"""
    while True:
        clear_screen()
        print("\n用户管理工具")
        print("============")
        print("1. 创建新用户")
        print("2. 重置用户密码")
        print("3. 列出所有用户")
        print("4. 测试用户登录")
        print("5. 初始化数据库")
        print("0. 退出")

        try:
            choice = input("\n请选择操作 [0-5]: ")

            if choice == '1':
                username = input("输入用户名: ")
                if not username:
                    print("错误: 用户名不能为空!")
                    input("按回车键继续...")
                    continue

                password = getpass.getpass("输入密码: ")
                if not password:
                    print("错误: 密码不能为空!")
                    input("按回车键继续...")
                    continue

                role = input("输入角色 (admin/operator/viewer) [默认: viewer]: ") or 'viewer'
                create_user(username, password, role)

            elif choice == '2':
                username = input("输入要重置密码的用户名: ")
                if not username:
                    print("错误: 用户名不能为空!")
                    input("按回车键继续...")
                    continue

                password = getpass.getpass("输入新密码: ")
                if not password:
                    print("错误: 密码不能为空!")
                    input("按回车键继续...")
                    continue

                reset_user_password(username, password)

            elif choice == '3':
                list_users()

            elif choice == '4':
                username = input("输入用户名: ")
                if not username:
                    print("错误: 用户名不能为空!")
                    input("按回车键继续...")
                    continue

                password = getpass.getpass("输入密码: ")
                if not password:
                    print("错误: 密码不能为空!")
                    input("按回车键继续...")
                    continue

                verify_login(username, password)

            elif choice == '5':
                confirm = input("确定要初始化数据库吗? 这将创建新的users表 [y/N]: ").lower()
                if confirm == 'y':
                    initialize_database()
                else:
                    print("操作已取消")

            elif choice == '0':
                print("退出程序")
                sys.exit(0)

            else:
                print("无效选择! 请输入0-5之间的数字")

            input("\n按回车键继续...")
        except KeyboardInterrupt:
            print("\n操作已取消")
            input("按回车键继续...")
        except Exception as e:
            print(f"\n发生错误: {str(e)}")
            logger.error(f"主菜单操作出错: {str(e)}")
            input("按回车键继续...")


if __name__ == "__main__":
    print("正在检查数据库连接...")
    if not check_database_connection():
        print("是否要尝试初始化数据库? [y/N]")
        choice = input().lower()
        if choice == 'y':
            initialize_database()
        else:
            print("程序无法继续，请确保数据库配置正确")
            sys.exit(1)

    main_menu()