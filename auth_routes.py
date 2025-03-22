# auth_routes.py
from flask import Blueprint, request, jsonify, g
from flask_cors import CORS
# 导入auth模块中的函数
from auth import login, requires_auth, change_password, reset_password
import logging

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__)
CORS(auth_bp)

# 路由定义...

def register_auth_routes(app):
    """注册认证相关的路由到Flask应用"""
    app.register_blueprint(auth_bp, url_prefix='/api')