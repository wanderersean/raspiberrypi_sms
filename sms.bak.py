import serial 
import time
import re
ser = serial.Serial('/dev/ttyAMA0', 115200, timeout=1)
p = re.compile(r'(?=\r\n(.*?)\r\n)', flags=re.DOTALL)

    
def send_string(cmd):
    '''写串口和读串口'''
    ser.write(cmd.encode())
    #time.sleep(1)
    #ret = ser.read(ser.inWaiting())
    ret = b''
    while 1:
        t = ser.read(100)
        if t == b'':
            break
        else:
            ret += t

    try:
        #print('返回的原始字节', ret)
        r = p.findall(ret.decode())  
        return r
    except Exception as e:
        print('[ERROR] failed to match re', ret)
        print(e)

def call_echo_incoming():
    cmd = 'AT+CLIP=1\r'
    r = send_string(cmd)

def get_signal_strength():
    cmd = 'AT+CSQ\r'
    r = send_string(cmd)  # ['+CSQ: 14,0', 'OK']
    print('signal strength', r)

def get_mem_use():
    cmd = 'AT+CPMS?\r'
    ret = send_string(cmd) # ['+CPMS: "SM",37,50,"SM",37,50,"SM",37,50', 'OK']
    print('get_mem_use', ret)


class Decoder(object):
    def __init__(self, msg):
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
                print('[ERROR] in convert to unicode', t)
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


def read_sms(i):
    cmd = 'AT+CMGR='+str(i)+'\r'
    ret = send_string(cmd)
    return ret


def delete_sms(i):
    cmd = 'AT+CMGD='+str(i)+'\r'
    ret = send_string(cmd)
    print(ret)


def set_character_set():
    cmd = 'AT+CSCS="UCS2"\r'
    ret = send_string(cmd)
    print(ret)

def read_messages():
    cmd = 'AT+CMGL=4,1\r'
    ret = send_string(cmd)
    messages = []
    for i in range(len(ret)//3):
        message = ret[i*3+1]
        messages.append(message)
    return messages

def delete_messages():
    pass

def set_mode(mode):
    if mode == 1:
        cmd = 'AT+CMGF=1\r'
        ret = send_string(cmd)
        print('set_mode', ret)
    else:
        cmd = 'AT+CMGF=0\r'
        ret = send_string(cmd)
        print('set_mode',ret)

def set_CNMI():
    cmd = 'AT+CNMI=0,0,0,0,0\r'
    ret = send_string(cmd)
    print(ret)


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


#get_signal_strength()
set_CNMI()
get_mem_use()
set_mode(0)
set_character_set()

msgs = read_messages()
for i in decode_encoded_messages(msgs):
    print(i)

#delete_sms(1)

ser.close()
