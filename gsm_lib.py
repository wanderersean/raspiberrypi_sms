#-*- coding:utf-8 -*-
import serial 
import time
import re
from email_sending import MailSender 
class GSM(object):
    def __init__(self,ser):
        self.ser = ser
        self.p = re.compile(r'(?=\r\n(.*?)\r\n)', flags=re.DOTALL)

        self.set_CNMI()
        self.get_mem_use()
        self.set_mode(0)
        self.set_character_set()
        
    
    def handle_other_info(self, ret):

        incoming_call_phone = None
        ret = ret.decode()
        if 'RING' in ret:
            p = re.compile(r'CLIP: "([0-9]*)"')
            groups = p.search(ret).groups() 
            if len(groups) >= 1:
                incoming_call_phone = groups[0]
        print('incoming_call_phone', incoming_call_phone) 
        #发送短信
        mail_sender = MailSender()
        cur_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
        mail_sender.send('来电提醒', '%s\r\n%s\r\n'%(cur_time, incoming_call_phone))

        while 1:
            time.sleep(1)
            ret = ret + self.ser.read(100).decode()
            if 'NO CARRIER' in ret:
                break



        
        
    def send_string(self, cmd):
        '''写串口和读串口'''
        self.ser.write(cmd.encode())
        #time.sleep(1)
        #ret = ser.read(ser.inWaiting())
        ret = b''
        while 1:
            t = self.ser.read(100)
            if t == b'':
                break
            else:
                ret += t
    
        try:
            #print('返回的原始字节', ret)
            r = self.p.findall(ret.decode())  
            if 'RING' in ret.decode():
                raise Exception
            return r
        except Exception as e:
            print('[ERROR] failed to match re', ret)
            self.handle_other_info(ret)
            #再来一遍
            return self.send_string(cmd)

    def set_character_set(self):
        cmd = 'AT+CSCS="UCS2"\r'
        ret = self.send_string(cmd)
        print('set character set', ret)

    def get_signal_strength(self):
        cmd = 'AT+CSQ\r'
        r = self.send_string(cmd)  # ['+CSQ: 14,0', 'OK']
        print('signal strength', r)

    def set_mode(self,mode):
        if mode == 1:
            cmd = 'AT+CMGF=1\r'
            ret = self.send_string(cmd)
            print('set_mode', ret)
        else:
            cmd = 'AT+CMGF=0\r'
            ret = self.send_string(cmd)
            print('set_mode',ret)

    def set_CNMI(self):
        cmd = 'AT+CNMI=0,0,0,0,0\r'
        ret = self.send_string(cmd)
        print('set_CNMI', ret)

    def call_echo_incoming(self):
        cmd = 'AT+CLIP=1\r'
        r = self.send_string(cmd)
    
    def get_mem_use(self):
        cmd = 'AT+CPMS?\r'
        ret = self.send_string(cmd) # ['+CPMS: "SM",37,50,"SM",37,50,"SM",37,50', 'OK']
        print('get_mem_use', ret)
    
    def read_sms(self,i):
        cmd = 'AT+CMGR='+str(i)+'\r'
        ret = self.send_string(cmd)
        return ret
    
    
    def delete_sms(self,i):
        cmd = 'AT+CMGD='+str(i)+'\r'
        ret = self.send_string(cmd)
        print(ret)
    
    def read_messages(self):
        cmd = 'AT+CMGL=4,0\r'
        ret = self.send_string(cmd)
        messages = []
        for i in range(len(ret)//3):
            message = ret[i*3+1]
            messages.append(message)
        return messages
    
    def delete_messages(self):
        #删除所有已经阅读过的短信
        cmd = 'AT+CMGDA=1\r'
        ret = self.send_string(cmd)



if __name__ == '__main__':
    #ret = b'AT+CSCS="UCS2"\r\r\nOK\r\n\r\nRING\r\n\r\n+CLIP: "18000000000",161,"",,"",0\r\n'
    #ret = ret.decode()#b'AT+CSCS="UCS2"\r\r\nOK\r\n\r\nRING\r\n\r\n+CLIP: "18000000000",161,"",,"",0\r\n'
    ser = serial.Serial('/dev/ttyAMA0', 115200, timeout=1)
   
    gsm = GSM(ser)
    #get_signal_strength()
    
    msgs = gsm.read_messages()
    for msg in msgs:
        print(msg)
    #gsm.delete_messages() 
    
    ser.close()
