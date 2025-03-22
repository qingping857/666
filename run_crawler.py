# run_crawler.py
import sys
import subprocess
import time

# 获取命令行参数
if len(sys.argv) < 5:
    print("用法: python run_crawler.py <页码> <每页大小> <搜索关键词> <类型>")
    sys.exit(1)

page = int(sys.argv[1]) - 1  # 用户输入从1开始，但API从0开始
size = sys.argv[2]
param = sys.argv[3]
search_type = sys.argv[4]

# 构建scrapy命令
cmd = [
    'scrapy', 'crawl', 'SamSearch',
    '-a', f'page={page}',
    '-a', f'size={size}',
    '-a', f'param={param}',
    '-a', f'searchType={search_type}'
]

# 执行命令
print(f"正在启动爬虫：{' '.join(cmd)}")
start_time = time.time()

process = subprocess.Popen(cmd)
print(f"爬虫进程已启动，PID: {process.pid}")

try:
    # 等待爬虫完成
    process.wait()
    end_time = time.time()
    duration = end_time - start_time
    print(f"爬虫执行完成，耗时: {duration:.2f}秒，退出码: {process.returncode}")
except KeyboardInterrupt:
    print("收到中断信号，正在终止爬虫...")
    process.terminate()
    print("爬虫已终止")