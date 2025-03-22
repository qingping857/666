"""
  获取随机ip
  芝麻http

"""

import socket
import random
import requests
import json
import re
import time
import logging


def redom_proxy(spiderhost=''):

    # 每次获取一个代理ip
    url = 'http://webapi.http.zhimacangku.com/getip?num=1&type=2&pro=0&city=0&yys=0&port=1&time=1&ts=0&ys=0&cs=0&lb=1&sb=0&pb=4&mr=2&regions='
    res = requests.get(url)
    res_json = json.loads(res.text)

    # 如果当前ip没有被加入到请求白名单，则会请求失败
    if res_json['code'] == 113:
        # 添加当前ip到白名单
        msg = res_json['msg']
        ip = re.findall(r'([0-9.]*)', msg)
        ip = [i for i in ip if i != '']
        real_ip = ip[0]

        # 将当前ip加入请求白名单
        white_url = 'http://wapi.http.linkudp.com/index/index/save_white?neek=95064&appkey=78f898c8fb9e787f6a192542e2dfd9a2&white={}'.format(
            real_ip)
        requests.get(white_url)

        # 等待3秒后再尝试获取ip
        time.sleep(3)
        return redom_proxy()
    else:
        ip = res_json['data'][0]['ip']
        port = res_json['data'][0]['port']
        logging.info('当前代理ip和端口: {}:{}'.format(ip, port))

        return '{}:{}'.format(ip, port)
