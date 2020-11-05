# !/usr/bin/python  
# encoding: utf-8
# author: zhangtong
import socket
import random

with open('config.txt', 'r') as df:
    str2 = df.read()
    local_ip = str2[str2.find('ip=') + 3:str2.find('\n')]
    local_port = 7778
sip_udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sip_udp.bind((local_ip, int(local_port)))

sb_id = '18062804121310234425'


def ptz(i, control=0, height=144, width=144, speed=16):
    """
    Generate a random iotile.

    Args:
        i: (int): write your description
        control: (str): write your description
        height: (int): write your description
        width: (int): write your description
        speed: (int): write your description
    """
    list1 = '<?xml version="1.0"?>\n'
    list1 += '<Control>\r\n'
    list1 += '<CmdType>DeviceControl</CmdType>\r\n'
    list1 += '<SN>{}</SN>\r\n'.format(str(random.randint(100000, 999999))[1:])
    list1 += '<DeviceID>{}</DeviceID>\r\n'.format(i)
    list1 += '<PTZCmd>a50f4d{:0>2}{:0>2}{:0>2}{:0>2}{:0>2}</PTZCmd>\r\n'.format(
        hex(control)[2:],
        hex(height)[2:],
        hex(width)[2:],
        hex(speed)[2:],
        hex((0xa5 + 0x0f + 0x4d + control + height + width + speed) % 0x100)[2:])
    list1 += '<Info>\r\n'
    list1 += '<ControlPriority>150</ControlPriority>\r\n'
    list1 += '<startX>0</startX>\r\n'
    list1 += '<startY>0</startY>\r\n'
    list1 += '<endX>0</endX>\r\n'
    list1 += '<endY>0</endY>\r\n'
    list1 += '</Info>\r\n'
    list1 += '</Control>\r\n'

    str_send = 'MESSAGE sip:{}@192.168.60.5:7100 SIP/2.0\n'.format(i)
    str_send += 'Via: SIP/2.0/UDP {}:{};rport;branch=z9hG4bK34202{}\n'.format(local_ip, local_port, str(random.randint(1000, 9999)))
    str_send += 'From: <sip:0000042001000001@{}:{}>;tag=500485{}\n'.format(local_ip, local_port, str(random.randint(1000, 9999)))
    str_send += 'To: <sip:{}@192.168.60.5:7100>\n'.format(i)
    str_send += 'Call-ID: {}\n'.format(i[12:]+str(random.randint(1000, 9999))[1:])
    str_send += 'CSeq: 20 MESSAGE\n'
    str_send += 'Content-Type: Application/MANSCDP+xml\n'
    str_send += 'Max-Forwards: 70\n'
    str_send += 'User-Agent: NCG V2.6.3.477777\n'
    str_send += 'Content-Length: {}\n\n'.format(len(list1))
    str_send += list1
    b4 = str_send.encode()
    sip_udp.sendto(b4, ('192.168.60.5', 7100))

# ptz(sb_id, 5)
# data = sip_udp.recvfrom(1500)
# str_receive = data[0].decode('gbk')
# print(str_receive)
#
# ptz(str_receive[(str_receive.find('To: <sip:') + 9):str_receive.find('@', str_receive.find('To: <sip:'))])
# data = sip_udp.recvfrom(1500)
# str_receive = data[0].decode('gbk')
# print(str_receive)

while True:
    ptz_control = input('右:1\t左:2\t右下:5\t右上:9\t放大:16\n'
                        '上:8\t下:4\t左下:6\t左上:10\t缩小:32:\n')
    if len(ptz_control) > 2:
        break
    ptz(sb_id, int(ptz_control))
    data = sip_udp.recvfrom(1500)
    str_receive = data[0].decode('gbk')
    print(str_receive)

    ptz(str_receive[(str_receive.find('To: <sip:') + 9):str_receive.find('@', str_receive.find('To: <sip:'))])
    data = sip_udp.recvfrom(1500)
    str_receive = data[0].decode('gbk')
    print(str_receive)















