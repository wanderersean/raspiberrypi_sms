#-*- coding:utf-8 -*-
import serial
import time
import re
from gsm_lib import GSM
from email_sending import MailSender
import sys
from logger_config import logger
import logging
import retry

class Decoder(object):
    def __init__(self, msg):
        self.logger = logging.getLogger('sms.Decoder')
        self.msg = msg
        self.phone_center = ''
        self.timestamp = ''
        self.phone_sender = ''
        self.head_info = {}
        self.content = ''
        self()

    def print_all_info(self):
        print('phone_center', self.phone_center)
        print('timestamp', self.timestamp)
        print('phone_sender', self.phone_sender)
        print('content', self.content)
        print('head info')
        for k,v in self.head_info.items():
            print('     ',k,v)

    def __get_phone(self, text):
        ret = ''
        for i in range(0,len(text),2):
            if i+1< len(text):
                ret += text[i+1]
                ret += text[i]
            else:
                ret += text[i]

        return ret[2:-1] if ret[-1] == 'F' else ret[2:]

    def __get_timestamp(self, text):
        ret = ''
        for i in range(0,len(text),2):
            if i+1< len(text):
                ret += text[i+1]
                ret += text[i]
                if i<= 2: ret += '/'
                if i == 4: ret += ' '
                if i>= 6: ret += ':'

        return ret[:-4]

    def __to_unicode(self, text):
        ret = ''
        for i in range(len(text)//4):
            t = '"\\u' + text[4*i:4*i+4] + '"'
            try:
                t = eval(t)
                ret = ret + t
            except:
                self.logger.error(f'转换到unicode失败:t为:{t}', exc_info=True)
        return ret


    def __call__(self):
        ret = {}
        msg = self.msg

        #短信中心
        index = 0
        len1 = int(msg[index:index+2])
        index = index + 2
        s_phone1 = msg[index: index+len1*2]
        index = index+len1*2
        self.phone_center = self.__get_phone(s_phone1)

        #控制位,后续是否有用户头部分
        s_first_byte = msg[index:index+2]
        first_byte = int(s_first_byte, 16)
        has_head = first_byte & (1<<6)
        index = index+2

        #发送人
        len2 = int(msg[index:index+2], 16)
        index = index+2

        odd = 0 if len2%2 == 0 else 1
        s_phone2 = msg[index:index+len2+2+odd]  # include 91 or A0 and 'F'
        index = index+len2+2+odd+4
        self.phone_sender = self.__get_phone(s_phone2)

        #时间戳
        s_time_stamp = msg[index:index + 14]
        index = index + 14
        self.timestamp = self.__get_timestamp(s_time_stamp)

        #用户数据
        len_userinfo_msg = int(msg[index:index+2], 16)
        index = index + 2
        if has_head:
            len_userinfo = int(msg[index:index+2], 16)
            index = index + 2

            temp_index = index
            temp_index += 4
            self.head_info['uniq_token'] = msg[temp_index:temp_index+2]
            temp_index += 2
            self.head_info['total'] = int(msg[temp_index:temp_index+2], 16)
            temp_index += 2
            self.head_info['current'] = int(msg[temp_index:temp_index+2], 16)

#            user_info = msg[index:index+len_userinfo*2]
            index = index + len_userinfo*2

        #消息内容
        self.content = self.__to_unicode(msg[index:])



def decode_encoded_messages(msgs):
    '''从编码字符串列表中解析出所有的短信,以(时间,发送者,内容)为格式'''
    messages_temp = {}
    messages_head = []
    messages_nohead = []
    for i in msgs:
        d = Decoder(i)
        if d.head_info:
            #考虑到uniq码可能会重复
            token = d.head_info['uniq_token']
            messages_temp.setdefault(token, [])
            messages_temp[token].append(d)

        else:
            messages_nohead.append([d.timestamp, d.phone_sender, d.content])

    for token, ds in messages_temp.items():
        temp = {}
        #按照时间来划分
        for d in ds:
            temp.setdefault(d.timestamp+'&'+d.phone_sender, ['' for i in range(d.head_info['total'])])
            temp[d.timestamp+'&'+d.phone_sender][d.head_info['current']-1] = d.content
        for k,v in temp.items():
            time, sender = k.split('&')
            text = ''.join(v)
            messages_head.append([time, sender, text])

    messages = messages_head + messages_nohead
    messages = sorted(messages, key = lambda x:x[0])
    return messages

class Saver(object):
    def __init__(self):
        try:
            self.f = open('sms.db', 'a')
        except Exception as e:
            print('[ERROR]', e)
    def save_to_file(self,string):
        self.f.write(string)

    def __del__(self):
        try:
            self.f.close()
        except Exception as e:
            print('[ERROR]', e)

if __name__ == '__main__':
    # TODO 增加定时执行功能
    while(1):
        try:
            ser = serial.Serial('/dev/ttyAMA0', 115200, timeout=1)
            gsm = GSM(ser)
            mail_sender = MailSender()
            while 1:
                msgs = gsm.read_messages()
                gsm.delete_messages()

                for i in decode_encoded_messages(msgs):
                    try:
                        logger.info(f'接收到短信:{i}, 开始写sms.db')
                        with open('sms.db','a') as f:
                            f.write('%s\n'%i)

                        logger.info('写db成功，开始发送邮件')
                        mail_sender.send('短信通知', '%s\r\n%s\r\n%s\r\n'%(i[0],i[1],i[2]))

                        sys.stdout.flush()
                        time.sleep(2)
                    except Exception:
                        logger.error(f"发送短信出错了，跳过该条短信：{i}", exc_info=True)
                        time.sleep(5)

                time.sleep(10)

        except Exception as e:
            logger.error('出错了。。。', exc_info=True)
        finally:
            ser.close()

