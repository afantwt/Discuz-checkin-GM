import random
import login
import time
import logging
import re
import os
from random import randint
import requests
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(filename)s %(funcName)s：line %(lineno)d %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler()  
    ]
)


class Discuz:

    def __init__(self, hostname, username, password, questionid='0', answer=None, pub_url=''):

        self.hostname = hostname
        if pub_url != '':
            self.hostname = self.get_host(pub_url)

        self.discuz_login = login.Login(self.hostname, username, password, questionid, answer)

    def login(self):
        """
        执行登录操作，并获取session和formhash
        """
        self.discuz_login.main()
        self.session = self.discuz_login.session
        self.formhash = self.discuz_login.post_formhash

    def get_host(self, pub_url):
        res = requests.get(pub_url)
        res.encoding = "utf-8"
        url = re.search(r'a href="https://(.+?)/".+?>.+?入口</a>', res.text)
        if url != None:
            url = url.group(1)
            logging.info(f'获取到最新的论坛地址:https://{url}')
            return url
        else:
            logging.error(f'获取失败，请检查发布页是否可用{pub_url}')
            return self.hostname

    def go_home(self):
        return self.session.get(f'https://{self.hostname}/forum.php').text

    def generate_random_numbers(self, start, end, count):
        random_numbers = []
        for _ in range(count):
            random_number = random.randint(start, end)
            random_numbers.append(random_number)
        return random_numbers

    def signin(self):
        """
        执行论坛签到操作
        """
        # 构建完整URL
        base_url = f"https://{self.hostname}/k_misign-sign.html"
        
        params = {
            "operation": "qiandao",
            "format": "button",
            "formhash": self.formhash,
            "inajax": 1,
            "ajaxtarget": "midaben_sign"
        }
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36",
            "Referer": f"https://{self.hostname}/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"
        }
        
        try:
            logging.info(f"正在访问: {base_url}")
            response = self.session.get(base_url, params=params, headers=headers)
            
            response.encoding = response.apparent_encoding
            
            logging.info(f"签到状态码: {response.status_code}")
            logging.info(f"签到响应内容: {response.text}")
            
            return response.text
        except Exception as e:
            logging.error(f"签到请求出错: {e}")
            return None

    def visit_home(self):
        """
        随机访问用户主页，以增加活跃度
        """
        start = 611111  # 起始数字
        end = 670000  # 结束数字
        count = 10  # 随机数字的数量

        random_numbers = self.generate_random_numbers(start, end, count)
        for number in random_numbers:
            time.sleep(5)
            signin_url = f'https://{self.hostname}/space-uid-{number}.html'
            self.session.get(signin_url)
            print(f'访问用户主页: {signin_url}')


if __name__ == '__main__':
    hostname = os.environ.get('HOSTNAME')
    username = os.environ.get('USERNAME')
    password = os.environ.get('PASSWORD')
    
    if not hostname or not username or not password:
        print("错误: 请设置必要的环境变量 HOSTNAME, USERNAME, PASSWORD")
        sys.exit(1)
        
    try:
        discuz = Discuz(hostname, username, password)
        discuz.login()
        logging.info(f"登录成功，formhash: {discuz.formhash}")
        discuz.signin()
        discuz.visit_home()
    except Exception as e:
        logging.error(f"执行过程中发生错误: {e}")
        sys.exit(1)
