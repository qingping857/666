# task_service.py
import json
import logging
from flask import g
from database import Database

logger = logging.getLogger(__name__)


class TaskService:
    """任务管理服务"""

    @classmethod
    def list_tasks(cls, user_id=None, limit=None, status=None):
        """
        获取任务列表，可选过滤条件

        Args:
            user_id: 可选的用户ID筛选任务创建者
            limit: 可选的返回任务数量限制
            status: 可选的状态筛选

        Returns:
            包含任务列表的字典
        """
        try:
            query_parts = ["SELECT * FROM crawler_tasks WHERE deleted = FALSE"]
            params = []

            # 添加WHERE子句
            where_clauses = []

            if user_id:
                where_clauses.append("created_by = %s")
                params.append(user_id)

            if status:
                where_clauses.append("status = %s")
                params.append(status)

            if where_clauses:
                query_parts.append("AND " + " AND ".join(where_clauses))

            # 添加排序
            query_parts.append("ORDER BY created_at DESC")

            # 添加限制
            if limit:
                query_parts.append("LIMIT %s")
                params.append(int(limit))

            # 构建最终查询
            query = " ".join(query_parts)

            # 执行查询
            tasks = Database.execute_query(query, params)

            # 将参数格式化为JSON以便显示
            for task in tasks:
                if isinstance(task['parameters'], str):
                    try:
                        task['parameters'] = json.loads(task['parameters'])
                    except:
                        pass

            return {'success': True, 'tasks': tasks}
        except Exception as e:
            logger.error(f"获取任务列表失败: {str(e)}")
            return {'success': False, 'message': f'获取任务列表失败: {str(e)}'}

    @classmethod
    def create_task(cls, task_type, parameters, created_by):
        """
        创建新任务

        Args:
            task_type: 任务类型
            parameters: 任务参数（字典或JSON字符串）
            created_by: 创建者用户ID

        Returns:
            包含创建结果的字典
        """
        try:
            # 确保parameters是JSON字符串
            if isinstance(parameters, dict):
                parameters = json.dumps(parameters)

            # 验证任务类型
            valid_task_types = ['web_crawler', 'api_crawler', 'data_extractor', 'scheduler']
            if task_type not in valid_task_types:
                return {'success': False, 'message': '无效的任务类型'}

            # 插入任务
            task_id = Database.execute_insert(
                """
                INSERT INTO crawler_tasks 
                (task_type, parameters, status, created_by, created_at) 
                VALUES (%s, %s, %s, %s, NOW())
                """,
                (task_type, parameters, 'pending', created_by)
            )

            return {
                'success': True,
                'message': '任务创建成功',
                'task_id': task_id
            }

        except Exception as e:
            logger.error(f"创建任务失败: {str(e)}")
            return {'success': False, 'message': f'创建任务失败: {str(e)}'}

    @classmethod
    def get_task(cls, task_id):
        """
        获取指定任务详情

        Args:
            task_id: 任务ID

        Returns:
            包含任务详情的字典
        """
        try:
            task = Database.execute_query_single(
                "SELECT * FROM crawler_tasks WHERE id = %s AND deleted = FALSE",
                (task_id,)
            )

            if not task:
                return {'success': False, 'message': '任务不存在'}

            # 将参数格式化为JSON
            if isinstance(task['parameters'], str):
                try:
                    task['parameters'] = json.loads(task['parameters'])
                except:
                    pass

            return {'success': True, 'task': task}
        except Exception as e:
            logger.error(f"获取任务详情失败: {str(e)}")
            return {'success': False, 'message': f'获取任务详情失败: {str(e)}'}

    @classmethod
    def update_task_status(cls, task_id, status, result=None):
        """
        更新任务状态

        Args:
            task_id: 任务ID
            status: 新状态('pending', 'running', 'completed', 'failed')
            result: 可选的结果数据

        Returns:
            包含更新结果的字典
        """
        try:
            valid_statuses = ['pending', 'running', 'completed', 'failed', 'cancelled']
            if status not in valid_statuses:
                return {'success': False, 'message': '无效的任务状态'}

            query_parts = [
                "UPDATE crawler_tasks SET status = %s"
            ]
            params = [status]

            # 添加结果（如果提供）
            if result is not None:
                if isinstance(result, dict):
                    result = json.dumps(result)

                query_parts.append(", result = %s")
                params.append(result)

            # 添加更新时间戳
            query_parts.append(", updated_at = NOW()")

            # 添加WHERE子句
            query_parts.append("WHERE id = %s AND deleted = FALSE")
            params.append(task_id)

            # 构建最终查询
            query = " ".join(query_parts)

            # 执行更新
            affected = Database.execute_update(query, params)

            if affected == 0:
                return {'success': False, 'message': '任务不存在或未更新'}

            return {'success': True, 'message': '任务状态已更新'}

        except Exception as e:
            logger.error(f"更新任务状态失败: {str(e)}")
            return {'success': False, 'message': f'更新任务状态失败: {str(e)}'}

    @classmethod
    def delete_task(cls, task_id, user_id):
        """
        删除任务（软删除）

        Args:
            task_id: 任务ID
            user_id: 执行删除操作的用户ID

        Returns:
            包含删除结果的字典
        """
        try:
            # 检查任务是否存在以及用户是否有权限
            task = Database.execute_query_single(
                """
                SELECT created_by FROM crawler_tasks 
                WHERE id = %s AND deleted = FALSE
                """,
                (task_id,)
            )

            if not task:
                return {'success': False, 'message': '任务不存在或已删除'}

            # 只有管理员或任务创建者可以删除
            if hasattr(g, 'user'):
                is_admin = g.user.get('role') == 'admin'
            else:
                is_admin = False

            is_creator = task['created_by'] == user_id

            if not (is_admin or is_creator):
                return {'success': False, 'message': '无权删除此任务'}

            # 软删除
            affected = Database.execute_update(
                """
                UPDATE crawler_tasks 
                SET deleted = TRUE, deleted_at = NOW(), deleted_by = %s 
                WHERE id = %s
                """,
                (user_id, task_id)
            )

            if affected == 0:
                return {'success': False, 'message': '任务删除失败'}

            return {'success': True, 'message': '任务已删除'}

        except Exception as e:
            logger.error(f"删除任务失败: {str(e)}")
            return {'success': False, 'message': f'删除任务失败: {str(e)}'}