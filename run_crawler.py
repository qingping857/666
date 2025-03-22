# run_crawler.py
import sys
import subprocess

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
subprocess.call(cmd)