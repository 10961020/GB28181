# !/usr/bin/python  
# encoding: utf-8
# author: zhangtong

"""
    视频转接核心处理模块包
"""

import os
import shutil
import time
import socket
import bitstring
import random

MAX_RTP_PKT_LEN = 1500
sn = {}
ji_shu = {}
rtp_dict = {}  # {序号,数据内容}
rtp_shipin = {}
time_ = {}
# str111 = ''  # 测试用的


# TODO 跳过字段 一般用不到
def parse_csrc(pkt, cc, lc):
    for i in range(cc):
        lc += 4
    return lc


# TODO 跳过一些字段 一般用不到 为啥这么写我也不知道
def parse_ext_hdr(pkt, lc):
    bt = bitstring.BitArray(bytes=pkt)
    bc = 8 * lc + 16
    lc = 4 + 4*bt[bc:bc + 16].uint
    return lc


# TODO payload中取H264保存到文件
def parse_frame(pay, name_id):
    global ji_shu
    global time_
    global rtp_shipin
    rtp_shipin[name_id] += pay
    # bt = bitstring.BitArray(bytes=pay)
    if pay[:4] == b'\x00\x00\x01\xba':  # \xba固定开头14位后边跟着这是第几帧图片 需要读帧数所以没加一 [13-14]
        ji_shu[name_id] += 1
        if ji_shu[name_id] % 100 == 0:
            shutil.move('video/'+name_id+'/'+name_id+'_'+time_[name_id]+'.dat.tmp', 'video/'+name_id+'/'+name_id+'_'+time_[name_id]+'.dat')
            time_[name_id] = time.strftime('%Y%m%d%H%M%S', time.localtime(time.time()))
        with open('video/' + name_id + '/' + name_id + '_' + time_[name_id] + '.dat.tmp', 'a', encoding='latin1') as f:
            f.write(rtp_shipin[name_id].decode('latin1'))
            rtp_shipin[name_id] = b''
        # print('第', bt[8*13+8*(bt[8*13:8*14].uint & 7):8*14+8*(bt[8*13:8*14].uint & 7)].uint, '帧')
        # 8*原因是因为bt是按位算的不是字节

    # elif pay[:4] == b'\x00\x00\x01\xe0':  # \xe0第9位写着负载长度 需要之后的数据所以加一 [9-]
    #     if pay[9 + bt[8 * 8:8 * 9].uint:13 + bt[8 * 8:8 * 9].uint] == b'\x00\x00\x00\x01' and bt[8 * (13 + bt[8 * 8:8 * 9].uint) + 1:8 * (13 + bt[8 * 8:8 * 9].uint) + 3].uint == 0:
    #         if bt[8 * (13 + bt[8 * 8:8 * 9].uint) + 3:8 * (13 + bt[8 * 8:8 * 9].uint) + 8].uint == 6:  # 补充增强信息单元，没用 删了试试
    #             return
    #     with open('video/'+name_id+'/'+name_id+'_'+time_[name_id]+'.dat.tmp', 'a', encoding='latin1') as f:
    #         f.write(pay[9 + bt[8*8:8*9].uint:].decode('latin1'))
    # else:
    #     with open('video/'+name_id+'/'+name_id+'_'+time_[name_id]+'.dat.tmp', 'a', encoding='latin1') as f:
    #         f.write(pay.decode('latin1'))
    if ji_shu[name_id] == 0:
        if len(rtp_shipin[name_id]) > 140000:
            with open('video/' + name_id + '/' + name_id + '_' + time_[name_id] + '.dat.tmp', 'a', encoding='latin1') as f:
                f.write(rtp_shipin[name_id].decode('latin1'))
                rtp_shipin[name_id] = b''
            shutil.move('video/' + name_id + '/' + name_id + '_' + time_[name_id] + '.dat.tmp',
                        'video/' + name_id + '/' + name_id + '_' + time_[name_id] + '.dat')
            time_[name_id] = time.strftime('%Y%m%d%H%M%S', time.localtime(time.time()))


# TODO 提取RTP包中payload
def recv_pkt(data, name_id):
    global sn
    global rtp_dict
    # global str111
    len_1 = len(data)
    bt = bitstring.BitArray(bytes=data)
    cc = bt[4:8].uint  # 固定头部后面跟着的CSRC的数目
    sn_1 = bt[16:32].uint  # 序列号
    lc = 12
    lc = parse_csrc(data, cc, lc)
    if bt[2]:  # 如果该位置位，则该RTP包的尾部就包含附加的填充字节
        len_1 -= bt[-8:].uint
    if bt[3]:  # 如果该位置位的话，RTP固定头部后面就跟有一个扩展头部
        lc = parse_ext_hdr(data[lc:], lc*8)
    # str111 += str(sn_1) + ' ' + str(len(data[lc:len_1])) + '\n'
    if sn[name_id] == -1:
        if bt[9:16].uint == 40:
            sn[name_id] = bt[16:32].uint + 1
            while rtp_dict[name_id].get(sn[name_id]):
                parse_frame(rtp_dict[name_id].get(sn[name_id]), name_id)
                rtp_dict[name_id].pop(sn[name_id])
                sn[name_id] += 1
        else:
            rtp_dict[name_id][sn_1] = data[lc:len_1]
            if len(rtp_dict[name_id]) == 10:
                lin_shi = sorted(rtp_dict[name_id].keys())
                for i in lin_shi:
                    parse_frame(rtp_dict[name_id][i], name_id)
                    rtp_dict[name_id].pop(i)
                    sn[name_id] = i+1

    elif sn[name_id] == sn_1:  # 按序号接包 皆大欢喜
        parse_frame(data[lc:len_1], name_id)
        sn[name_id] += 1
        while rtp_dict[name_id].get(sn[name_id]):
            parse_frame(rtp_dict[name_id].get(sn[name_id]), name_id)
            rtp_dict[name_id].pop(sn[name_id])
            sn[name_id] += 1
    else:
        rtp_dict[name_id][sn_1] = data[lc:len_1]
        if len(rtp_dict[name_id]) == 10:
            lin_shi = sorted(rtp_dict[name_id].keys())
            for i in lin_shi:
                parse_frame(rtp_dict[name_id][i], name_id)
                rtp_dict[name_id].pop(i)
                sn[name_id] = i+1


def main(name_id, port, time_now, local_ip1, local_port1):
    global sn
    global ji_shu
    global time_
    global rtp_dict
    global rtp_shipin
    time_[name_id] = time_now
    sn[name_id] = -1
    ji_shu[name_id] = 0
    rtp_dict[name_id] = {}
    rtp_shipin[name_id] = b''
    with open('config.txt', 'r') as f:
        str2 = f.read()
        local_ip = str2[str2.find('ip=') + 3:str2.find('\n')]
    address = (local_ip, port)
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(address)
    s.settimeout(20)
    if not os.path.exists('video/'+name_id+'/'):
        os.makedirs('video/'+name_id+'/')
    with open('video/'+name_id+'/'+name_id+'_'+time_[name_id]+'.dat.tmp', 'w', encoding='latin1') as f:
        pass
    while True:
        try:
            data, addr = s.recvfrom(MAX_RTP_PKT_LEN)
        except socket.timeout:
            print("h264: ~Over {},端口: {} ,一共 {} 帧".format(name_id, port, ji_shu[name_id]))
            try:
                shutil.move('video/'+name_id+'/'+name_id+'_'+time_[name_id]+'.dat.tmp', 'video/'+name_id+'/'+name_id+'_'+time_[name_id]+'.dat')
            except FileNotFoundError:
                pass
            str_send = 'del:{}'.format(name_id)
            b4 = str_send.encode()
            s.sendto(b4, (local_ip1, int(local_port1)))
            # with open('1.txt', 'w')as f:
            #     f.write(str111)
            break
        if len(data) == 2:
            if data.decode('latin1') == 'by':
                print("h264: Over {},端口: {} ,一共 {} 帧".format(name_id, port, ji_shu[name_id]))
                try:
                    shutil.move('video/'+name_id+'/'+name_id+'_'+time_[name_id]+'.dat.tmp', 'video/'+name_id+'/'+name_id+'_'+time_[name_id]+'.dat')
                except FileNotFoundError:
                    pass
                # with open('1.txt', 'w')as f:
                #     f.write(str111)
                break
        recv_pkt(data, name_id)
    s.close()
    return

if __name__ == '__main__':
    main(1, 6000, 20180202, 1, None)
