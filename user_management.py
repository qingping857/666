# user_management.py
# 用于创建新用户或重置现有用户密码的实用脚本

import bcrypt
import pymysql
import sys
import getpass
import logging

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 数据库配置
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '123456',  # 此处应该使用环境变量或安全存储
    'database': 'sam_gov_data',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}


def get_db_connection():
    """获取数据库连接"""
    return pymysql.connect(**DB_CONFIG)


def hash_password(password):
    """使用bcrypt哈希密码"""
    if isinstance(password, str):
        password = password.encode('utf-8')

    # 生成bcrypt哈希（以字符串形式返回，不使用Base64编码）
    hashed = bcrypt.hashpw(password, bcrypt.gensalt(rounds=12))
    return hashed.decode('utf-8')  # 存储为字符串


def create_user(username, password, role='viewer'):
    """创建新用户"""
    # 验证角色
    valid_roles = ['admin', 'operator', 'viewer']
    if role not in valid_roles:
        print(f"无效的角色。有效选项: {', '.join(valid_roles)}")
        return False

    # 哈希密码
    password_hash = hash_password(password)

    # 插入用户
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # 检查用户是否已存在
            cursor.execute(
                "SELECT id FROM users WHERE username = %s",
                (username,)
            )
            if cursor.fetchone():
                print(f"用户 '{username}' 已存在!")
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
            return True
    except Exception as e:
        print(f"创建用户时出错: {str(e)}")
        return False
    finally:
        conn.close()


def reset_user_password(username, new_password):
    """重置用户密码"""
    # 哈希新密码
    password_hash = hash_password(new_password)

    # 更新用户密码
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # 检查用户是否存在
            cursor.execute(
                "SELECT id FROM users WHERE username = %s",
                (username,)
            )
            if not cursor.fetchone():
                print(f"用户 '{username}' 不存在!")
                return False

            # 更新密码
            cursor.execute(
                """
                UPDATE users 
                SET password_method = %s, 
                    password_hash = %s,
                    password_salt = NULL
                WHERE username = %s
                """,
                ('bcrypt', password_hash, username)
            )
            conn.commit()
            print(f"用户 '{username}' 的密码已重置")
            return True
    except Exception as e:
        print(f"重置密码时出错: {str(e)}")
        return False
    finally:
        conn.close()


def list_users():
    """列出所有用户"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT id, username, role, status, created_at, last_login FROM users ORDER BY username"
            )
            users = cursor.fetchall()

            if not users:
                print("没有找到用户")
                return

            print("\n用户列表:")
            print("-" * 80)
            print(f"{'ID':<5} {'用户名':<15} {'角色':<10} {'状态':<10} {'创建时间':<20} {'最后登录':<20}")
            print("-" * 80)

            for user in users:
                print(f"{user['id']:<5} {user['username']:<15} {user['role']:<10} {user['status']:<10} "
                      f"{str(user['created_at']):<20} {str(user['last_login'] or ''):<20}")
    except Exception as e:
        print(f"列出用户时出错: {str(e)}")
    finally:
        conn.close()


def verify_login(username, password):
    """验证用户登录（用于测试）"""
    conn = get_db_connection()
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
                    return is_valid
                except Exception as e:
                    print(f"bcrypt验证出错: {str(e)}")
                    return False
            else:
                print(f"不支持的密码方法: {user['password_method']}")
                return False
    except Exception as e:
        print(f"验证登录时出错: {str(e)}")
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    print("用户管理工具")
    print("============")
    print("1. 创建新用户")
    print("2. 重置用户密码")
    print("3. 列出所有用户")
    print("4. 测试用户登录")
    print("5. 退出")

    choice = input("\n请选择操作: ")

    if choice == '1':
        username = input("输入用户名: ")
        password = getpass.getpass("输入密码: ")
        role = input("输入角色 (admin/operator/viewer) [默认: viewer]: ") or 'viewer'
        create_user(username, password, role)

    elif choice == '2':
        username = input("输入要重置密码的用户名: ")
        password = getpass.getpass("输入新密码: ")
        reset_user_password(username, password)

    elif choice == '3':
        list_users()

    elif choice == '4':
        username = input("输入用户名: ")
        password = getpass.getpass("输入密码: ")
        verify_login(username, password)

    elif choice == '5':
        print("退出程序")
        sys.exit(0)

    else:
        print("无效选择!")