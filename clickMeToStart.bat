@echo off
REM 进入脚本所在目录
cd /d %~dp0

REM 激活虚拟环境
call venv\Scripts\activate

REM 运行 Python 脚本
python entrypoint.py

REM 暂停，以便查看输出（可选）
pause