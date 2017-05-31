#!/usr/bin/env python

import os
import sys
import smbus

import time
import socket

import threading

import datetime


dir = '/home/pi/tmpdata'
file = '/home/pi/tmpdata'

if os.path.isdir(dir):
    print 'Tmp Folder Exist.'
else:
    print 'First run, make Tmp Folder.'
    os.makedirs(dir)


bus = smbus.SMBus(1)

Temp = []
Pres = []
Humi = []
tt = 0.0

t2 = 0
p2 = 0
h2 = 0
lastdate = datetime.datetime(2000, 1, 1, 1, 1, 1)

def file_thread(file_lock):
    
    global t2
    global p2
    global h2
    global lastdate
    
    old = datetime.datetime(2000, 1, 1, 1, 1, 1)
    
    while True:
        now = datetime.datetime.today()
        
        if (now.year != old.year \
         or now.month != old.month \
         or now.day != old.day \
         or now.hour != old.hour \
         or now.minute != old.minute \
         or now.second != old.second) \
         and  now.second == 0 : 
            
            nowdir = dir + '/' + now.strftime("%Y%m")
            if os.path.isdir(nowdir):
                # print 'Month Folder Exist.'
                print ''
            else:
                # print 'First run, make Month Folder.'
                os.makedirs(nowdir)
            
            # file lock
            file_lock.acquire()
            
            SensorReadData()
            t = '%02d' % t2
            t = t + '%02d' % ((t2 * 100) % 100)
            h = '%02d' % h2
            h = h + '%02d' % ((h2 * 100) % 100)
            
            nowfile = nowdir + '/' + now.strftime("%Y%m%d") + '.log'
            if os.path.isfile(nowfile):
                # print 'Add Data to File.' + now.strftime("%H%M%S")
                f = open(nowfile, 'a')
                if t2 >= 0:
                    data = now.strftime("%H%M%S") + ':+' + t + ':' + h + '\n'
                else:
                    data = now.strftime("%H%M%S") + ':-' + t + ':' + h + '\n'
                f.write(data)
                f.close()
                # print data
                
            else:
                # print 'Create Data File.' + now.strftime("%H%M%S")
                f = open(nowfile, 'a')
                if t2 >= 0:
                    data = now.strftime("%H%M%S") + ':+' + t + ':' + h + '\n'
                else:
                    data = now.strftime("%H%M%S") + ':-' + t + ':' + h + '\n'
                f.write(data)
                f.close()
                # print data
                
            
            lastdate = now
            
            # file release
            file_lock.release()
            
        
        time.sleep(0.1)
        old = now


def server_thread(serversocket, file_lock):
    
    global t2
    global p2
    global h2
    global lastdate
    
    while True:
        # wait client connection
        print('Wait connection...(localhost : port=4000)')
        
        clientsocket, (client_address, client_port) = serversocket.accept()
        print('New client: {0}:{1}'.format(client_address, client_port))

        while True:
            try:
                message = clientsocket.recv(1024)
                # print('Recv: {0} from {1}:{2}'.format(message, client_address, client_port))
            except OSError:
                break
            except:
                print('Disconnect from Client.')
                break

            if len(message) == 0:
                print('rcv null message.')
                break

            print( 'message len = {0}'.format(len(message)) )
            
            mode = 0;
            if len(message) == 7:
                if 'get now' == message:
                    print('rcv message [get now]')
                    # file lock
                    file_lock.acquire()
                    
                    send_mess = 'NOW  :'
                    send_mess = send_mess + lastdate.strftime("%Y%m%d%H%M%S") + ':'
                    t = '%02d' % t2
                    t = t + '%02d' % ((t2 * 100) % 100)
                    h = '%02d' % h2
                    h = h + '%02d' % ((h2 * 100) % 100)
                    p = '%04d' % p2
                    p = p + '%02d' % ((p2 * 100) % 100)
                    if t2 >= 0:
                        send_mess = send_mess + '+' + t + ':' + h + ':' + p
                    else:
                        send_mess = send_mess + '-' + t + ':' + h + ':' + p
                    
                    # file release
                    file_lock.release()

                else:
                    send_mess = 'NACK :5'
                    print( 'Command : Error <' + message + '>' )

            elif len(message) == 13:
                if 'get year' == message[:8]:
                    print( 'Comand : Year ' + message[9:] )
                    send_mess = 'YEAR '
                    buff = ''
                    n = 0
                    # scan month in year
                    for var in range(1, 13):
                        folder = message[9:] + ('%02d' % var)
                        nowdir = dir + '/' + folder
                        if os.path.isdir(nowdir):
                            buff = buff + ':' + ('%02d' % var)
                            n+=1
                            # print 'find : ' + folder
                    send_mess = send_mess + ':' + ('%02d' % n) + buff

                else:
                    send_mess = 'NACK :1'
                    print( 'Command : Error <' + message + '>' )

            elif len(message) == 16:
                if 'get month' == message[:9]:
                    print( 'Comand : Month ' + message[10:] )
                    send_mess = 'MONTH'
                    buff = ''
                    n = 0
                    # scan file in month
                    for var in range(1, 32):
                        nowfile = dir + '/' + message[10:] + '/' \
                                + message[10:] + ('%02d' % var) + '.log'
                        if os.path.isfile(nowfile):
                            buff = buff + ':' + ('%02d' % var)
                            n+=1
                            # print 'find : ' +  message[10:] + ('%02d' % var)
                    send_mess = send_mess + ':' + ('%02d' % n) + buff

                elif 'get tmp' == message[:7]:
                    print( 'Comand : Tmp ' + message[8:] )
                    nowfile = dir + '/' + message[8:14] + '/' \
                            + message[8:] + '.log'
                    if os.path.isfile(nowfile):
                        # file lock
                        file_lock.acquire()
                        # access log file
                        fsize = os.path.getsize(nowfile)
                        # max file size < 345600B(20Bx24hx60mx12)
                        send_mess = 'LOG  :' + ('%06d' % fsize)
                        f = open(nowfile)
                        tmpdata = f.read()
                        f.close()
                        # file release
                        file_lock.release()
                        send_mess = send_mess + tmpdata
                        print 'access : ' + message[8:] + '.log' + (' %dB' % fsize)
                        mode = 1

                    else:
                        send_mess = 'NACK :2'
                        print( 'Command : Error <' + message + '>' )

                else:
                    send_mess = 'NACK :3'
                    print( 'Command : Error <' + message + '>' )

            else:
                send_mess = 'NACK :4'
                print( 'Command : Error <' + message + '>' )

            # send_mess = message
            while True:
                sent_len = clientsocket.send(send_mess)
                if sent_len == len(send_mess):
                    break
                send_mess = send_mess[sent_len:]
            
            if mode == 0:
                print('Send: {0}'.format(send_mess))

        clientsocket.close()
        print('Client Bye-Bye: {0}:{1}'.format(client_address, client_port))


# Write Sensor I2C
def writeSensor(reg_addr, data):
    bus.write_byte_data(0x76, reg_addr, data)


# Get Calibration Data
def getCalibration():
    calib = []

    for i in range(0x88, 0x88+24):
        calib.append(bus.read_byte_data(0x76, i))
    calib.append(bus.read_byte_data(0x76, 0xA1))
    for i in range(0xE1, 0xE1+7):
        calib.append(bus.read_byte_data(0x76, i))

    Temp.append((calib[1] << 8) | calib[0])
    Temp.append((calib[3] << 8) | calib[2])
    Temp.append((calib[5] << 8) | calib[4])
    Pres.append((calib[7] << 8) | calib[6])
    Pres.append((calib[9] << 8) | calib[8])
    Pres.append((calib[11]<< 8) | calib[10])
    Pres.append((calib[13]<< 8) | calib[12])
    Pres.append((calib[15]<< 8) | calib[14])
    Pres.append((calib[17]<< 8) | calib[16])
    Pres.append((calib[19]<< 8) | calib[18])
    Pres.append((calib[21]<< 8) | calib[20])
    Pres.append((calib[23]<< 8) | calib[22])
    Humi.append( calib[24] )
    Humi.append((calib[26]<< 8) | calib[25])
    Humi.append( calib[27] )
    Humi.append((calib[28]<< 4) | (0x0F & calib[29]))
    Humi.append((calib[30]<< 4) | ((calib[29] >> 4) & 0x0F))
    Humi.append( calib[31] )

    for i in range(1,2):
        if Temp[i] & 0x8000:
            Temp[i] = (-Temp[i] ^ 0xFFFF) + 1

    for i in range(1,8):
        if Pres[i] & 0x8000:
            Pres[i] = (-Pres[i] ^ 0xFFFF) + 1

    for i in range(0,6):
        if Humi[i] & 0x8000:
            Humi[i] = (-Humi[i] ^ 0xFFFF) + 1


# Read Now Temperature,Pressure,Humidity
def SensorReadData():
    
    global t2
    global p2
    global h2
    
    data = []
    for i in range(0xF7, 0xF7+8):
        data.append(bus.read_byte_data(0x76, i))
    pres = (data[0] << 12) | (data[1] << 4) | (data[2] >> 4)
    temp = (data[3] << 12) | (data[4] << 4) | (data[5] >> 4)
    humi = (data[6] << 8)  |  data[7]

    t2 = adjustTemp(temp)
    p2 = adjustPres(pres)
    h2 = adjustHumi(humi)

    # print "temp : %6.2f C" % t2
    # print "pressure : %7.2f hPa" % p2
    # print "hum : %6.2f %%" % h2
    # print ""


# Adjust Pressure by Calibration
def adjustPres(nowpres):
    global  tt
    pressure = 0.0

    v1 = (tt / 2.0) - 64000.0
    v2 = (((v1 / 4.0) * (v1 / 4.0)) / 2048) * Pres[5]
    v2 = v2 + ((v1 * Pres[4]) * 2.0)
    v2 = (v2 / 4.0) + (Pres[3] * 65536.0)
    v1 = (((Pres[2] * (((v1 / 4.0) * (v1 / 4.0)) / 8192)) / 8) \
         + ((Pres[1] * v1) / 2.0)) / 262144
    v1 = ((32768 + v1) * Pres[0]) / 32768

    if v1 == 0:
        return 0
    pressure = ((1048576 - nowpres) - (v2 / 4096)) * 3125
    if pressure < 0x80000000:
        pressure = (pressure * 2.0) / v1
    else:
        pressure = (pressure / v1) * 2
    v1 = (Pres[8] * (((pressure / 8.0) * (pressure / 8.0)) \
         / 8192.0)) / 4096
    v2 = ((pressure / 4.0) * Pres[7]) / 8192.0
    pressure = pressure + ((v1 + v2 + Pres[6]) / 16.0)

    return pressure/100


# Adjust Temperature by Calibration
def adjustTemp(nowtemp):
    global tt
    v1 = (nowtemp / 16384.0 - Temp[0] / 1024.0) * Temp[1]
    v2 = (nowtemp / 131072.0 - Temp[0] / 8192.0) \
        * (nowtemp / 131072.0 - Temp[0] / 8192.0) * Temp[2]
    tt = v1 + v2
    temperature = tt / 5120.0

    return temperature


# Adjust Humidity by Calibration
def adjustHumi(nowhumi):
    global tt
    var_h = tt - 76800.0
    if var_h != 0:
        var_h = (nowhumi - (Humi[3] * 64.0 + Humi[4]/16384.0 \
                * var_h)) * (Humi[1] / 65536.0 * (1.0 \
                + Humi[5] / 67108864.0 * var_h * (1.0 \
                + Humi[2] / 67108864.0 * var_h)))
    else:
        return 0
    var_h = var_h * (1.0 - Humi[0] * var_h / 524288.0)
    if var_h > 100.0:
        var_h = 100.0
    elif var_h < 0.0:
        var_h = 0.0

    return var_h


# Initialize Sensor
def sensor_setup():
    Tovs = 1     # Temperature oversampling x 1
    Povs = 1     # Pressure oversampling x 1
    Hovs = 1     # Humidity oversampling x 1
    mode   = 3   # Normal mode
    stby   = 5   # Tstandby 1000ms
    filter = 0   # Filter off
    spion = 0    # 3-wire SPI Disable

    ctrl_meas_reg = (Tovs << 5) | (Povs << 2) | mode
    config_reg    = (stby << 5) | (filter << 2) | spion
    ctrl_hum_reg  = Hovs

    writeSensor(0xF2, ctrl_hum_reg)
    writeSensor(0xF4, ctrl_meas_reg)
    writeSensor(0xF5, config_reg)


def main():
    # for sensor
    sensor_setup()
    getCalibration()

    serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    serversocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)

    # for server
    host = ''
    port = 4000
    serversocket.bind((host, port))

    serversocket.listen(128)

    file_lock = threading.Lock()   # LOCK OBJECT

    # create file thread
    fthread = threading.Thread(target=file_thread, args=(file_lock, ))
    fthread.daemon = True
    fthread.start()

    # create server thread
    sthread = threading.Thread(target=server_thread, args=(serversocket, file_lock, ))
    sthread.daemon = True
    sthread.start()

    while True:
        # main loop
        
        time.sleep(1)


if __name__ == '__main__':
    main()


