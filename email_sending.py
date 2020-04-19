#-*- coding:utf-8 -*-
import yagmail
from configparser import ConfigParser
class MailSender(object):
    def __init__(self):
        config = ConfigParser()
        config.read('cfg.ini', encoding='UTF-8') 
        user = config.get('mail', 'user')
        password = config.get('mail', 'password')
        host = config.get('mail', 'host')
        port = config.getint('mail', 'port')
        to = config.get('mail', 'to')

        self.yag = yagmail.SMTP(user=user, password=password, host=host, port=port)
        self.remote_addr = to
    
    def send(self, subject, content):
        contents = []
        contents.append(content) 
        self.yag.send(self.remote_addr, subject, contents)        
        print('发送邮件成功')

if __name__ == '__main__':
    m = MailSender()
    m.send('测试', 'this is a test')

