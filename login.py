"""
Discuz论坛登录模块
用于处理论坛的登录流程，包括验证码处理和会话维护
主要功能包括：
1. 自动处理验证码
2. 支持账号密码登录
3. 自动处理Cloudflare验证
"""

from time import time
import logging

import ddddocr
import re
import time
import random
import cloudscraper

from PIL import Image




# 修复ANTIALIAS问题
if not hasattr(Image, 'ANTIALIAS'):
    # PIL 9.1.0 及以上版本用 Image.Resampling.LANCZOS 替代了 Image.ANTIALIAS
    Image.ANTIALIAS = Image.Resampling.LANCZOS if hasattr(Image, 'Resampling') else Image.LANCZOS

# 配置日志记录，设置日志级别为INFO，输出到终端而不是文件
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(filename)s %(funcName)s：line %(lineno)d %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler()  # 输出到控制台
    ]
)

class CustomOCR:
    """
    自定义OCR识别类，用于处理验证码识别
    避开ddddocr内部可能存在的ANTIALIAS错误
    """
    def __init__(self):
        """
        初始化OCR对象
        """
        self.ocr = ddddocr.DdddOcr()
    
    def classification(self, img_bytes):
        """
        识别验证码图片
        
        参数:
            img_bytes: 图片二进制数据
            
        返回:
            识别结果字符串
        """
        try:
            # 直接使用原始方法
            return self.ocr.classification(img_bytes)
        except Exception as e:
            logging.error(f"验证码识别失败: {str(e)}")
            # 尝试直接从文件读取，跳过中间步骤
            try:
                with open('captcha.png', 'wb') as f:
                    f.write(img_bytes)
                
                image_data = open('captcha.png', 'rb').read()
                result = self.ocr.classification(image_data)
                return result
            except Exception as e2:
                logging.error(f"从文件读取也失败: {str(e2)}")
                return ''

class Login:
    """
    论坛登录类，处理论坛的登录流程，包括验证码处理和会话维护
    """
    def __init__(self, hostname, username, password, questionid='0', answer=None):
        """
        初始化登录对象
        
        参数:
            hostname: 论坛主机地址
            username: 用户名
            password: 密码
            questionid: 安全问题ID，默认为'0'
            answer: 安全问题答案，默认为None
        """
        # 使用cloudscraper替代requests，用于绕过Cloudflare验证
        self.session = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'desktop': True
            }
        )
        
        self.hostname = hostname
        self.username = str(username)
        self.password = str(password)
        self.questionid = questionid
        self.answer = answer
        self.ocr = CustomOCR()  # 使用自定义OCR类

    def wait_for_cloudflare(self, max_retries=5):
        """
        等待Cloudflare验证完成
        
        参数:
            max_retries: 最大重试次数，默认为5
            
        返回:
            布尔值，表示是否成功通过Cloudflare验证
        """
        for i in range(max_retries):
            try:
                # 访问主页
                response = self.session.get(f'https://{self.hostname}/')
                if 'cf-browser-verification' not in response.text:
                    logging.info('Cloudflare验证已完成')
                    return True
                logging.info(f'等待Cloudflare验证完成... 尝试 {i+1}/{max_retries}')
                time.sleep(3)
            except Exception as e:
                logging.error(f'等待Cloudflare验证时发生错误: {str(e)}')
                time.sleep(3)
        return False

    def form_hash(self):
        """
        获取论坛登录表单的formhash值
        
        返回:
            loginhash: 登录hash值
            formhash: 表单hash值
        """
        try:
            # 添加随机延迟
            time.sleep(random.uniform(1, 2))
            
            rst = self.session.get(f'https://{self.hostname}/member.php?mod=logging&action=login').text
            # 保存页面内容用于调试
            with open('login_page.html', 'w', encoding='utf-8') as f:
                f.write(rst)
            
            # 改进正则表达式匹配
            logininfo = re.search(r'<div id="main_messaqge_(.+?)">', rst)
            loginhash = logininfo.group(1) if logininfo else ""
            
            formhash_match = re.search(r'<input type="hidden" name="formhash" value="(.+?)"', rst)
            if not formhash_match:
                logging.error('未找到formhash，尝试备用匹配模式')
                formhash_match = re.search(r'formhash=([^&"]+)', rst)
            
            if not formhash_match:
                logging.error('无法获取formhash，登录失败')
                return "", ""
                
            formhash = formhash_match.group(1)
            logging.info(f'loginhash : {loginhash} , formhash : {formhash} ')
            return loginhash, formhash
        except Exception as e:
            logging.error(f'获取formhash失败: {str(e)}')
            return "", ""

    def verify_code_once(self):
        try:
            # 添加随机延迟
            time.sleep(random.uniform(1, 2))
            
            # 访问登录页面获取Cloudflare cookie
            login_page = self.session.get(f'https://{self.hostname}/member.php?mod=logging&action=login')
            time.sleep(random.uniform(1, 2))  
            
            # 改进验证码ID匹配模式
            seccode_patterns = [
                r'updateseccode\(\'([^\']+)\'',
                r'seccodehash=([^&"]+)',
                r'idhash=([^&"]+)'
            ]
            
            seccode_id = None
            for pattern in seccode_patterns:
                seccode_match = re.search(pattern, login_page.text)
                if seccode_match:
                    seccode_id = seccode_match.group(1)
                    logging.info(f'使用模式 {pattern} 找到验证码ID: {seccode_id}')
                    break
            
            if not seccode_id:
                logging.error('未找到验证码ID，尝试备用方法')
                seccode_match = re.search(r'seccode.*?idhash=([^&"]+)', login_page.text)
                if seccode_match:
                    seccode_id = seccode_match.group(1)
                    logging.info(f'使用备用方法找到验证码ID: {seccode_id}')
            
            if not seccode_id:
                logging.error('无法获取验证码ID')
                return ''
            
            update_url = f'https://{self.hostname}/misc.php?mod=seccode&action=update&idhash={seccode_id}&makeseed=1&modid=member::logging'
            
            # 添加随机延迟
            time.sleep(random.uniform(1, 2))
            
            headers = {
                'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Connection': 'keep-alive',
                'Host': self.hostname,
                'Referer': f'https://{self.hostname}/member.php?mod=logging&action=login',
                'Sec-Fetch-Dest': 'image',
                'Sec-Fetch-Mode': 'no-cors',
                'Sec-Fetch-Site': 'same-origin',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
            }
            
            # 获取验证码更新响应
            update_resp = self.session.get(update_url, headers=headers)
            
            time.sleep(random.uniform(1, 2))

            img_url = f'https://{self.hostname}/misc.php?mod=seccode&idhash={seccode_id}&{int(time.time())}'
            logging.info(f'请求验证码图片: {img_url}')
            
            rst = self.session.get(img_url, headers=headers)
            if rst.status_code != 200:
                logging.error(f'验证码请求失败，状态码: {rst.status_code}')
                return ''
                
            # 保存原始响应内容用于调试
            try:
                with open('captcha.png', 'wb') as f:
                    f.write(rst.content)
                logging.info('已保存验证码图片到captcha.png')
            except Exception as e:
                logging.error(f'保存调试信息失败: {str(e)}')
            
            # 尝试识别验证码
            try:
                # 检查响应内容类型
                content_type = rst.headers.get('content-type', '')
                logging.info(f'验证码响应内容类型: {content_type}')
                
                # 如果响应是图片，直接识别
                if 'image' in content_type.lower():
                    # 直接从文件读取验证码图片进行识别
                    try:
                        # 先保存后读取
                        code = ""
                        with open('captcha.png', 'rb') as f:
                            image_bytes = f.read()
                            code = self.ocr.classification(image_bytes)
                        if code:
                            logging.info(f'成功识别验证码: {code}')
                            return code
                        else:
                            logging.error('验证码识别结果为空')
                            return ''
                    except Exception as e:
                        logging.error(f'验证码识别失败: {str(e)}')
                        return ''
                else:
                    # 如果不是图片，记录日志
                    logging.info('响应不是图片格式')
                    return ''
                        
            except Exception as e:
                logging.error(f'验证码处理过程发生错误: {str(e)}')
                return ''
                
        except Exception as e:
            logging.error(f'验证码获取过程发生错误: {str(e)}')
            return ''

    def verify_code(self,num = 10):
        """
        获取并验证验证码，可多次重试
        """
        while num > 0:
            num -= 1
            code = self.verify_code_once()
            
            if not code:
                logging.info('验证码获取失败，等待1秒后重试...')
                time.sleep(1)
                continue
                
            # 先重新获取验证码ID
            try:
                login_page = self.session.get(f'https://{self.hostname}/member.php?mod=logging&action=login')
                seccode_pattern = r'updateseccode\(\'([^\']+)\''
                seccode_match = re.search(seccode_pattern, login_page.text)
                
                if not seccode_match:
                    logging.error('未找到验证码ID，无法验证')
                    time.sleep(1)
                    continue
                    
                seccode_id = seccode_match.group(1)
                logging.info(f'验证使用验证码ID: {seccode_id}')
                
                # 验证验证码，使用动态获取的ID
                verify_url = f'https://{self.hostname}/misc.php?mod=seccode&action=check&inajax=1&modid=member::logging&idhash={seccode_id}&secverify={code}'
                
                res = self.session.get(verify_url).text
                if 'succeed' in res:
                    logging.info(f'验证码识别成功，验证码:{code}, ID:{seccode_id}')
                    return code, seccode_id
                else:
                    logging.info('验证码识别失败，重新识别中...')
                    time.sleep(1)
            except Exception as e:
                logging.error(f'验证码验证请求失败: {str(e)}')
                time.sleep(1)

        logging.error('验证码获取失败，请增加验证次数或检查当前验证码识别功能是否正常')
        return '', ''

    def account_login_without_verify(self):
        """
        尝试无需验证码直接登录
        """
        try:
            loginhash, formhash = self.form_hash()
            login_url = f'https://{self.hostname}/member.php?mod=logging&action=login&loginsubmit=yes&loginhash={loginhash}&inajax=1'
            formData = {
                'formhash': formhash,
                'referer': f'https://{self.hostname}/',
                'username': self.username,
                'password': self.password,
                'handlekey':'ls',
            }
            
            # 添加登录请求头
            login_headers = {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Connection': 'keep-alive',
                'Host': f'{self.hostname}',
                'Referer': f'https://{self.hostname}/member.php?mod=logging&action=login',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'same-origin',
                'Sec-Fetch-User': '?1',
                'Upgrade-Insecure-Requests': '1',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.45 Safari/537.36',
                'Cookie': '; '.join([f'{k}={v}' for k, v in self.session.cookies.items()])
            }
            
            login_rst = self.session.post(login_url, data=formData, headers=login_headers).text
            
            if 'succeed' in login_rst:
                logging.info('无验证码登录成功')
                return True
            elif 'seccodeverify' in login_rst:
                logging.info('论坛需要验证码登录，这是正常的安全措施')
                return False
            else:
                # 保存响应内容用于调试
                with open('login_response.txt', 'w', encoding='utf-8') as f:
                    f.write(login_rst)
                logging.info('无验证码登录失败，将尝试使用验证码登录')
                return False
                
        except Exception as e:
            logging.error(f'登录过程发生错误: {str(e)}')
            return False

    def account_login(self):
        """
        登录账号，先尝试无验证码登录，失败则使用验证码
        """
        # 首先尝试不使用验证码直接登录
        if self.account_login_without_verify():
            self.post_formhash = self.get_post_hash()
            return True

        # 需要验证码的情况
        code, seccode_id = self.verify_code()
        if code == '':
            return False

        loginhash, formhash = self.form_hash()
        login_url = f'https://{self.hostname}/member.php?mod=logging&action=login&loginsubmit=yes&loginhash={loginhash}&inajax=1'
        formData = {
            'formhash': formhash,
            'referer': f'https://{self.hostname}/',
            'loginfield': 'username',
            'username': self.username,
            'password': self.password,
            'questionid': self.questionid,
            'answer': self.answer,
            'cookietime': 2592000,
            'seccodehash': seccode_id,
            'seccodemodid': 'member::logging',
            'seccodeverify': code,  # verify code
        }
        
        # 增加尝试次数
        for _ in range(3):
            login_rst = self.session.post(login_url, data=formData).text
            if 'succeed' in login_rst:
                logging.info('登陆成功')
                self.post_formhash = self.get_post_hash()
                return True
            else:
                logging.info('登陆失败，重试中...')
                time.sleep(1)
                
        logging.error('登陆失败，请检查账号或密码是否正确')
        return False

    def get_post_hash(self):
        """
        获取发帖需要的formhash
        """
        try:
            res = self.session.get(f'https://{self.hostname}/forum.php').text
            patterns = [
                r'formhash=(.+?)&',
                r'<input type="hidden" name="formhash" value="(.+?)" />',
                r'formhash" value="(.+?)"'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, res)
                if match:
                    formhash = match.group(1)
                    logging.info(f'成功获取formhash: {formhash}')
                    return formhash
                    
            logging.error('所有formhash匹配模式均失败')
            return ''
        except Exception as e:
            logging.error(f'获取发帖formhash失败: {str(e)}')
            return ''

    def go_home(self):
        """
        访问论坛首页
        """
        return self.session.get(f'https://{self.hostname}/forum.php').text

    def get_conis(self):
        """
        获取用户当前金币数量
        """
        try:
            res = self.session.get(f'https://{self.hostname}/home.php?mod=spacecp&ac=credit&showcredit=1&inajax=1&ajaxtarget=extcreditmenu_menu').text
            coins = re.search(r'<span id="hcredit_2">(.+?)</span>', res).group(1)
            logging.info(f'当前金币数量：{coins}')
        except Exception:
            logging.error('获取金币数量失败！', exc_info=True)

    def main(self):
        """
        执行主要登录流
        """
        try:
            if not self.account_login():
                logging.error('登录失败，请检查账号密码或网络连接')
                return False
                
            # 尝试获取formhash和其他信息
            try:
                res = self.go_home()
                self.post_formhash = re.search(r'<input type="hidden" name="formhash" value="(.+?)" />', res).group(1)
                credit = re.search(r' class="showmenu">(.+?)</a>', res).group(1)
                logging.info(f'{credit},提交文章formhash:{self.post_formhash}')
                
                self.get_conis()
                return True
            except Exception as e:
                logging.error(f'获取网站信息失败: {str(e)}')
                # 虽然登录成功但无法获取信息，仍然返回True
                return True
                
        except Exception as e:
            logging.error(f'登录过程中发生错误: {str(e)}', exc_info=True)
            return False

