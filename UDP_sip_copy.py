# !/usr/bin/python  
# encoding: utf-8
# author: zhangtong

"""
    海康视频转接平台
"""

import time
import os
import itertools
import random
import socket
import threading
import multiprocessing
# import pymysql
from h264 import main

ip_haikang = ''         # 海康端口IP信息18062904141310236235
device_dict = {
               # '52010000001310000467': [6000, 0, 0, 0, 0],
               # '52010000001310000466': [6000, 0, 0, 0, 0],
               # '52262274001322910598': [6000, 0, 0, 0, 0],
               # '18070511461310236681': [6000, 0, 0, 0],
               # '18062804101310239734': [6000, 0, 0, 0],
               # '18062804101310238708': [6000, 0, 0, 0],
               # '18062804101310239683': [6000, 0, 0, 0],
               # '18070511441310232617': [6000, 0, 0, 0]
               }        # 设备信息 {'设备编码':端口号,尝试次数,Call-ID,tag,关闭视频流失败次数,未响应请求次数}
device_dict_shiyong = {}  # 正在预览的设备信息
device_dict_now = {}    # 请求发出去了，还没告诉我消息呢
device_dict_over = {}   # 当前预览过的设备信息
local_ip = ''
local_port = ''
time_now = ''
device_len = 5
port = 32500
sema = ''


# TODO 登入
def login_sip(s):
    global ip_haikang
    global device_dict
    global device_dict_now
    global device_dict_shiyong
    sema.acquire()
    while True:
        data, addr = s.recvfrom(1024)
        str_receive = data.decode('gbk')
        print(addr)
        if len(str_receive) > 30:
            ip_haikang = str_receive[(str_receive.find('From:') + 11):str_receive.find('>', str_receive.find('From:'))]
            keep_heart(s, addr, str_receive)
            data, addr = s.recvfrom(1024)
            str_receive = data.decode('latin1')
            if str_receive[(str_receive.find('CSeq: ') + 6):str_receive.find(
                    '\n', str_receive.find('CSeq: '))-1] == '20 MESSAGE':
                keep_heart(s, addr, str_receive)
                device_dict.clear()
                device_dict_now.clear()
                device_dict_shiyong.clear()
                sema.release()
                return addr


# TODO 保持心跳
def keep_heart(s, addr_heart, str_receive):
    str_send = 'SIP/2.0 200 OK\n'
    str_send += 'To: <sip:{}>;tag=69113a2a\n'.format(ip_haikang)
    str_send += 'Contact: sip:{}\n'.format(ip_haikang)
    str_send += 'Content-Length: 0\n'
    str_send += 'CSeq: {}\n'.format(
        str_receive[(str_receive.find('CSeq:') + 6):str_receive.find('\n', str_receive.find('CSeq:'))])
    str_send += 'Call-ID: {}\n'.format(
        str_receive[(str_receive.find('Call-ID: ') + 9):str_receive.find('\n', str_receive.find('Call-ID: '))])
    str_send += 'From: <sip:{}>;tag={}\n'.format(
        ip_haikang, str_receive[(str_receive.find('tag=') + 4):str_receive.find('\n', str_receive.find('tag='))])
    str_send += 'Via: SIP/2.0/UDP {}:{};branch={}\n'.format(
        local_ip, local_port,
        str_receive[(str_receive.find('branch=') + 7):str_receive.find('\n', str_receive.find('branch='))])
    b4 = str_send.encode()
    s.sendto(b4, addr_heart)


# TODO 获取设备信息请求
def get_messages_receive(s, addr_get):
    list1 = '<?xml version="1.0"?>\n<Query>\n<CmdType>Catalog</CmdType>\n<SN>1{}</SN>\n<DeviceID>{}</DeviceID>\n</Query>\n'.format(str(random.randint(10000, 99999))[1:], ip_haikang[:ip_haikang.find('@')])
    str_send = 'MESSAGE sip:{} SIP/2.0\n'.format(ip_haikang)
    str_send += 'To: <sip:{}>\n'.format(ip_haikang)
    str_send += 'Content-Length: {}\n'.format(len(list1))
    str_send += 'CSeq: 2 MESSAGE\n'
    str_send += 'Call-ID: 12495{}\n'.format(str(random.randint(10000, 99999))[1:])
    str_send += 'Via: SIP/2.0/UDP {}:{};rport;branch=z9hG4bK342026{}\n'.format(local_ip, local_port, str(random.randint(10000, 99999))[1:])
    str_send += 'From: <sip:0000042001000001@{}:{}>;tag=50048{}\n'.format(local_ip, local_port, str(random.randint(10000, 99999))[1:])
    str_send += 'Content-Type: Application/MANSCDP+xml\n'
    str_send += 'Max-Forwards: 70\n\n'
    str_send += list1
    b4 = str_send.encode()
    s.sendto(b4, addr_get)


# TODO 设备信息数据解析
def get_messages_send(str_receive):
    name = str_receive[(str_receive.find('<Name>')+6):str_receive.find('<', str_receive.find('<Name>')+6)]
    device_id = str_receive[(str_receive.find('<DeviceID>', str_receive.find('</DeviceID>'))+10):str_receive.find(
        '<', str_receive.find('<DeviceID>', str_receive.find('</DeviceID>'))+10)]
    longitude = str_receive[(str_receive.find('<Longitude>')+11):str_receive.find('<', str_receive.find('<Longitude>')+11)]
    latitude = str_receive[(str_receive.find('<Latitude>')+10):str_receive.find('<', str_receive.find('<Latitude>')+10)]
    status = str_receive[(str_receive.find('<Status>')+8):str_receive.find('<', str_receive.find('<Status>')+8)]
    PTZType = str_receive[(str_receive.find('<PTZType>')+9):str_receive.find('<', str_receive.find('<PTZType>')+9)]
    name = name.replace(' ', '')
    with open('zong_sb_sbdy.txt', 'a') as f:
        f.write(str_receive+'\r\n')
    with open('sb_sbdy.txt', 'a') as f:
        f.write(name+' '+device_id+' '+longitude+' '+latitude+' '+status+' '+PTZType+'\r\n')


# TODO 发送ACK确认推流
def get_video_receive2(s, addr_get, str_receive):
    global device_dict_shiyong
    global device_dict
    sb_id = str_receive[(str_receive.find('To:') + 9):str_receive.find('@', str_receive.find('To:'))]
    if sb_id in device_dict:
        str_send = 'ACK sip:{} SIP/2.0\n'.format(ip_haikang)
        str_send += 'To: <sip:{}>\n'.format(
            str_receive[(str_receive.find('To:') + 9):str_receive.find('>', str_receive.find('To:'))])
        str_send += 'Content-Length: 0\n'
        str_send += 'Contact: <sip:0000042001000001@{}:{}>\n'.format(local_ip, local_port)
        str_send += 'CSeq: {}\n'.format(
            str_receive[(str_receive.find('CSeq:') + 6):str_receive.find('\n', str_receive.find('CSeq:'))])
        str_send += 'Call-ID: {}\n'.format(
            str_receive[(str_receive.find('Call-ID: ') + 9):str_receive.find('\n', str_receive.find('Call-ID: '))])
        str_send += 'Via: SIP/2.0/UDP {}:{};branch={}\n'.format(
            local_ip, local_port,
            str_receive[(str_receive.find('branch=') + 7):str_receive.find('\n', str_receive.find('branch='))])
        str_send += 'From: <sip:0000042001000001@{}:{}>;tag={}\n'.format(local_ip, local_port, device_dict[sb_id][3])
        str_send += 'User-Agent: NCG V2.6.3.777777\n'
        str_send += 'Max-Forwards: 70\n'
        b4 = str_send.encode()
        s.sendto(b4, addr_get)
        device_dict[sb_id][1] = 0
        device_dict_shiyong[sb_id] = device_dict[sb_id].copy()
        device_dict[sb_id][1] = 100
        p1 = multiprocessing.Process(target=shi_pin_liu, args=(sb_id,))
        p1.start()
        # timer = threading.Timer(3600, get_videoclose_receive, (s, addr_get, sb_id))
        # timer.start()


# TODO 发送ACK确认推流失败
def get_video_receive3(s, addr_get, str_receive):
    global device_dict
    global device_dict_now
    sb_id = str_receive[(str_receive.find('To: <sip:') + 9):str_receive.find('@', str_receive.find('To: <sip:'))]
    if sb_id in device_dict:
        str_send = 'ACK sip:{} SIP/2.0\n'.format(ip_haikang)
        str_send += 'To: <sip:{}>\n'.format(
            str_receive[(str_receive.find('To:') + 9):str_receive.find('>', str_receive.find('To:'))])
        str_send += 'Content-Length: 0\n'
        str_send += 'CSeq: 20 ACK\n'
        str_send += 'Call-ID: {}\n'.format(
            str_receive[(str_receive.find('Call-ID: ') + 9):str_receive.find('\n', str_receive.find('Call-ID: '))])
        str_send += 'Via: SIP/2.0/UDP {}:{};branch={}\n'.format(
            local_ip, local_port,
            str_receive[(str_receive.find('branch=') + 7):str_receive.find('\n', str_receive.find('branch='))])
        str_send += 'From: <sip:0000042001000001@{}:{}>;tag={}\n'.format(local_ip, local_port, device_dict[sb_id][3])
        b4 = str_send.encode()
        s.sendto(b4, addr_get)
        try:
            del device_dict_now[sb_id]
        except KeyError:
            pass
        device_dict[sb_id][1] = int(device_dict[sb_id][1]) + 1


# TODO 请求设备视频流
def get_video_receive(s, addr_get):
    global port
    global device_dict
    global device_dict_now
    port_not_equal = 0
    print(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())) + '一轮预览开始\n', device_dict)
    for i in list(device_dict.keys()):  # 删除五次预览失败的id以及成功预览的id
        if device_dict[i][1] == 100:
            del device_dict[i]
        elif device_dict[i][1] >= device_len:
            print('删除 {} 该设备无法预览'.format(i))
            del device_dict[i]
            try:
                del device_dict_now[i]
            except KeyError:
                pass
    for i in list(device_dict_now.keys()):  # 清理device_dict_now中错误的id
        if i in device_dict_shiyong:
            try:
                del device_dict_now[i]
            except KeyError:
                continue
        if i not in device_dict:
            try:
                del device_dict_now[i]
            except KeyError:
                pass
    for i in device_dict:  # 五次请求之后该id预览请求还是未响应，默认删了它 重新预览
        if i in device_dict_now:
            device_dict[i][5] += 1
            if device_dict[i][5] >= 5:
                device_dict[i][5] = 0
                try:
                    del device_dict_now[i]
                except KeyError:
                    pass
            continue
        print(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())) + '请求预览设备:', i)
        while not port_not_equal:  # 保证使用的端口不重复
            port_not_equal = 1
            for j in device_dict_shiyong.values():
                if j[0] == port:
                    port_not_equal = 0
                    port += 2
                    continue
        device_dict[i][0] = port
        device_dict[i][2] = i[12:]+str(random.randint(1000, 9999))[1:]
        device_dict[i][3] = str(500485)+str(random.randint(1000, 9999))[1:]
        list1 = 'v=0\r\n'
        list1 += 'o={} 0 0 IN IP4 {}\r\n'.format(i, local_ip)
        list1 += 's=Play\r\n'
        list1 += 'c=IN IP4 {}\r\n'.format(local_ip)
        list1 += 't=0 0\r\n'
        list1 += 'm=video {} RTP/AVP 96 97 98\r\n'.format(port)
        list1 += 'a=rtpmap:96 PS/90000\r\n'
        list1 += 'a=rtpmap:97 H264/90000\r\n'
        list1 += 'a=rtpmap:98 MPEG4/90000\r\n'
        list1 += 'a=recvonly\r\n'
        list1 += 'a=streamMode:MAIN\r\n'
        list1 += 'a=filesize:-1\r\n'
        list1 += 'y=0999999999\r\n'

        str_send = 'INVITE sip:{}{} SIP/2.0\n'.format(i, ip_haikang[ip_haikang.find('@'):])
        str_send += 'Via: SIP/2.0/UDP {}:{};rport;branch=z9hG4bK34202{}\n'.format(local_ip, local_port, str(random.randint(1000, 9999)))
        str_send += 'From: <sip:0000042001000001@{}:{}>;tag={}\n'.format(local_ip, local_port, device_dict[i][3])
        str_send += 'To: <sip:{}{}>\n'.format(i, ip_haikang[ip_haikang.find('@'):])
        str_send += 'Call-ID: {}\n'.format(device_dict[i][2])
        str_send += 'CSeq: 20 INVITE\n'
        str_send += 'Contact: <sip:0000042001000001@{}:{}>\n'.format(local_ip, local_port)
        str_send += 'Content-Type: Application/SDP\n'
        str_send += 'Max-Forwards: 70\n'
        str_send += 'User-Agent: NCG V2.6.3.477777\n'
        str_send += 'Subject: {}:{},0000042001000001:0\n'.format(i, port)
        str_send += 'Content-Length: {}\n\n'.format(len(list1))
        str_send += list1
        b4 = str_send.encode()
        s.sendto(b4, addr_get)
        port += 2
        if port == 33500:
            port = 32500
        device_dict_now[i] = device_dict[i].copy()


# TODO 请求关闭某个设备视频流
def get_videoclose_receive(s, addr_get, sb_id):
    if sb_id in device_dict_shiyong:
        print(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())) + '请求关闭{}视频流'.format(sb_id))
        str_send = 'BYE sip:{} SIP/2.0\n'.format(ip_haikang)
        str_send += 'Via: SIP/2.0/UDP {}:{};rport;branch=z9hG4bK34202{}\n'.format(local_ip, local_port, str(random.randint(1000, 9999)))
        str_send += 'From: <sip:0000042001000001@{}:{}>;tag={}\n'.format(local_ip, local_port, device_dict_shiyong[sb_id][3])
        str_send += 'To: <sip:{}{}>;tag=3982398926\n'.format(sb_id, ip_haikang[ip_haikang.find('@'):])
        str_send += 'Call-ID: {}\n'.format(device_dict_shiyong[sb_id][2])
        str_send += 'CSeq: 21 BYE\n'
        str_send += 'Contact: <sip:0000042001000001@{}:{}>\n'.format(local_ip, local_port)
        str_send += 'Max-Forwards: 70\n'
        str_send += 'User-Agent: NCG V2.6.3.477777\n'
        str_send += 'Content-Length: 0\n'
        b4 = str_send.encode()
        s.sendto(b4, addr_get)


# TODO 监听消息
def monitor_messages(s):
    global device_dict_shiyong
    while True:
        data, addr_messages = s.recvfrom(1500)
        str_receive = data.decode('gbk')
        sb_id = str_receive[(str_receive.find('To: <sip:') + 9):str_receive.find('@', str_receive.find('To: <sip:'))]
        if str_receive[(str_receive.find('CSeq: ') + 6):str_receive.find(
                '\n', str_receive.find('CSeq: '))-1] == '20 MESSAGE':
            if str_receive.find('Keepalive') != -1:
                print('心跳反馈成功')
                keep_heart(s, addr_messages, str_receive)
            elif str_receive.find('Catalog') != -1:
                keep_heart(s, addr_messages, str_receive)
                if str_receive.find('Status') != -1:
                    get_messages_send(str_receive)
                    # print('1', str_receive[
                    #            (str_receive.find('<Name>') + 6):str_receive.find('<', str_receive.find('<Name>') + 6)])
                # else:
                #     print('>>>2', str_receive[
                #                (str_receive.find('<Name>') + 6):str_receive.find('<', str_receive.find('<Name>') + 6)])
            else:
                print(str_receive)
        elif str_receive[(str_receive.find('CSeq: ') + 6):str_receive.find(
                '\n', str_receive.find('CSeq: '))-1] == '1 REGISTER':
            login_sip(s)                                        # 注册
        elif str_receive[(str_receive.find('CSeq: ') + 6):str_receive.find(
                '\n', str_receive.find('CSeq: '))-1] == '20 INVITE':
            if str_receive.find('200 OK') != -1:
                print('视频流推流反馈成功 ', sb_id)
                if sb_id in device_dict_shiyong:
                    continue
                get_video_receive2(s, addr_messages, str_receive)   # 反馈发ACK
            elif str_receive.find('404 Not Found') != -1:
                print(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())) + ' 404 Not Found', sb_id, '  ', str_receive[str_receive.find('<ErrorCode>')+11:str_receive.find('<', str_receive.find('<ErrorCode>')+11)])
                get_video_receive3(s, addr_messages, str_receive)
            elif str_receive.find('400 Bad Request') != -1:
                print(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))+' 400 Bad Request', sb_id, '  ', str_receive[str_receive.find('<ErrorCode>')+11:str_receive.find('<', str_receive.find('<ErrorCode>')+11)])
                get_video_receive3(s, addr_messages, str_receive)
        elif str_receive[(str_receive.find('CSeq: ') + 6):str_receive.find(
                '\n', str_receive.find('CSeq: '))-1] == '21 BYE':
            if str_receive.find('200 OK') != -1:
                print('视频流推流结束 ', sb_id)
                str_send = 'by'
                b4 = str_send.encode('latin1')
                if sb_id in device_dict_shiyong:
                    s.sendto(b4, (local_ip, int(device_dict_shiyong[sb_id][0])))
                    device_dict_over[sb_id] = device_dict_shiyong[sb_id]
                    del device_dict_shiyong[sb_id]
            else:
                print('视频流关闭失败'+sb_id)
                if sb_id in device_dict_shiyong:
                    device_dict_shiyong[sb_id][4] += 1
                    if device_dict_shiyong[sb_id][4] > 5:
                        del device_dict_shiyong[sb_id]
                        continue
                timer = threading.Timer(15, get_videoclose_receive, (s, addr_messages, sb_id))
                timer.start()
        elif str_receive[(str_receive.find('CSeq: ') + 6):str_receive.find(
                '\n', str_receive.find('CSeq: ')) - 1] == '20 NOTIFY':
                if str_receive.find('Catalog') != -1:
                    keep_heart(s, addr_messages, str_receive)
                    if str_receive.find('Status') != -1:
                        get_messages_send(str_receive)
                        print('1 ', str_receive[(str_receive.find('<Name>') + 6):str_receive.find('<', str_receive.find('<Name>') + 6)])
        elif str_receive[:4] == 'del:':
            try:
                del device_dict_shiyong[str_receive[4:]]
            except KeyError:
                pass
            # get_videoclose_receive(s, addr_messages, str_receive[4:])


# TODO 视频预览模块
def mutual_interface(s, addr_interface):
    global device_dict
    global time_now
    time.sleep(30)
    timer = threading.Timer(time.mktime(time.strptime(time.strftime('%Y%m%d', time.localtime(time.time())), "%Y%m%d"))+60*60*25-time.time(), device_info, (s, addr_interface))
    timer.start()

    while True:
        sema.acquire()
        sb_dat(s, addr_interface)
        # if not device_dict:
        #     while device_dict_shiyong:
        #         time.sleep(2)
        #         print('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
        #         sb_dat(s, addr_interface)
        #     device_dict_over.clear()
        #     time.sleep(10)
        sema.release()
        time.sleep(2)


# TODO 视频处理中心
def shi_pin_liu(i):
    if i in device_dict_shiyong:
        main(i, device_dict_shiyong[i][0], time_now, local_ip, local_port)
    return


# def sql_sb():
#     global device_dict
#     device_dict = {}
#     db = pymysql.connect(
#         host='1.1.1.1',
#         user='pro',
#         password='1',
#         database='n'
#     )
#     cur = db.cursor()
#     sql_select = "SELECT"
#     cur.execute(sql_select)
#
#     data = cur.fetchall()
#     print('从库表中取出{}个隧道桥梁设备id'.format(len(data)))
#     db.commit()
#     cur.close()
#     db.close()
#     for i in data:
#         device_dict[i[0]] = [6000, 0, 0, 0]


# TODO 更新设备状态一天一次
def device_info(s, addr_interface):
    print(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())) + '更新设备状态')
    timer = threading.Timer(time.mktime(time.strptime(time.strftime('%Y%m%d', time.localtime(time.time())), "%Y%m%d"))+60*60*24*7-time.time(), device_info, (s, addr_interface))
    timer.start()
    try:
        os.remove('zong_sb_sbdy.txt')
        os.remove('sb_sbdy.txt')
    except Exception:
        pass
    get_messages_receive(s, addr_interface)


# TODO 读本地文件更新设备是否播放
def sb_dat(s, addr_interface):
    global device_dict
    global time_now
    time_now = time.strftime('%Y%m%d%H%M%S', time.localtime(time.time()))
    device_dict_del = []
    dizhi = '/data/video/'
    lists = os.listdir(dizhi)
    for k in lists:
        if k.find('.tmp') != -1:
            continue
        with open(dizhi + k, 'r', encoding='gbk') as f:
            str1 = f.read()
            open_1 = str1[str1.find('alives:') + 7:str1.find('\n')].split(',')
            close_1 = str1[str1.find('deads:') + 6:].split(',')
            for i, j in itertools.zip_longest(open_1, close_1):
                if i and i not in device_dict_shiyong and i not in device_dict_now:
                    if(i[:2] == '12' or i[:2] == '13' or i[0] == '5')and i not in device_dict:
                        device_dict[i] = [6000, 0, 0, 0, 0, 0]
                if j and j in device_dict_shiyong:
                    if(j[:2] == '12' or j[:2] == '13' or j[0] == '5')and j not in device_dict_del:
                        device_dict_del.append(j)
        os.remove(dizhi + k)
    if device_dict or device_dict_del:
        print('----------------------------------')
        print(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())) + '需要打开的视频设备: ', list(device_dict.keys()))
        print(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())) + '需要关闭的视频设备: ', device_dict_del)
        get_video_receive(s, addr_interface)
    for i in device_dict_del:
        get_videoclose_receive(s, addr_interface, i)
        # time.sleep(1)

if __name__ == '__main__':
    with open('config.txt', 'r') as df:
        str2 = df.read()
        local_ip = str2[str2.find('ip=') + 3:str2.find('\n')]
        local_port = str2[str2.find('port=') + 5:str2.find('\n', str2.find('port='))]
    sip_udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sip_udp.bind((local_ip, int(local_port)))
    sema = threading.Semaphore(value=1)
    print('开始注册...')
    addr1 = login_sip(sip_udp)
    print('注册成功...')
    t1 = threading.Thread(target=monitor_messages, args=(sip_udp,))
    t2 = threading.Thread(target=mutual_interface, args=(sip_udp, addr1))
    t1.start()
    t2.start()
    t1.join()
    t2.join()
    sip_udp.close()
