#!/usr/bin/env python
from datetime import datetime
from threading import Thread, Event, Lock
import os
import queue
import serial
import serial.rs485
import string
import time
import threading

# https://github.com/ifit/SparkyWikiJS/blob/master/icon-protocols/shortbus.md

monitor_q = queue.Queue()

address_dict = {
    b'21': "Motor Controller",
    b'22': "Upright Low Voltage Motor Controller",
    b'23': "Crawler",
    b'24': "Console Tilt",
    b'25': "Torque Sensor",
    b'26': "Strider (!!DEPRECATED!!)",
    b'27': "Accelerometer",
    b'28': "Drive Motor PWM",
    b'29': "Vibration Motor",
    b'30': "Proximity Sensor (Reserved)",
    b'31': "Proximity Sensor #1",
    b'32': "Proximity Sensor #2",
    b'33': "Proximity Sensor #3",
    b'34': "Proximity Sensor #4",
    b'35': "Proximity Sensor #5",
    b'36': "Proximity Sensor #6",
    b'37': "Proximity Sensor #7",
    b'38': "Proximity Sensor #8",
    b'39': "Proximity Sensor #9",
    b'40': "Incline (Reserved)",
    b'41': "Incline Motor #1",
    b'42': "Incline Motor #2",
    b'43': "Incline Motor #3",
    b'44': "Incline Motor #4",
    b'45': "Incline Motor #5",
    b'46': "Incline Motor #6",
    b'47': "Incline Motor #7",
    b'48': "Incline Motor #8",
    b'49': "Incline Motor #9",
    b'50': "Speed (Reserved)",
    b'51': "Speed #1",
    b'52': "Speed #2",
    b'53': "Speed #3",
    b'54': "Speed #4",
    b'55': "Speed #5",
    b'56': "Speed #6",
    b'57': "Speed #7",
    b'58': "Speed #8",
    b'59': "Speed #9",
    b'60': "Resistance (Reserved)",
    b'61': "Resistance Motor #1",
    b'62': "Resistance Motor #2",
    b'63': "Resistance Motor #3",
    b'64': "Resistance Motor #4",
    b'65': "Resistance Motor #5",
    b'66': "Resistance Motor #6",
    b'67': "Resistance Motor #7",
    b'68': "Resistance Motor #8",
    b'69': "Resistance Motor #9",
    b'70': "Fan (Reserved)",
    b'71': "Fan Motor #1",
    b'72': "Fan Motor #2",
    b'73': "Fan Motor #3",
    b'74': "Fan Motor #4",
    b'75': "Fan Motor #5",
    b'76': "Fan Motor #6",
    b'77': "Fan Motor #7",
    b'78': "Fan Motor #8",
    b'79': "Fan Motor #9",
    b'E1': "Heart Rate",
    b'E2': "BLE Speed Ring",
    b'E3': "BLE Radio (!!DEPRECATED!!)",
    b'E4': "BLE Radio (!!DEPRECATED!!)",
    b'E5': "BLE Radio (!!DEPRECATED!!)",
    b'E6': "BLE Radio (!!DEPRECATED!!)",
}

# Motor Controller (21)
addr_21_cmd_dict = {
    b'00': 'RESERVED',
    b'01': 'Desired Speed',
    b'02': 'Current Speed',
    b'03': 'Stride Current',
    b'04': 'Speed Slope',
    b'05': 'Speed Intercept',
    b'06': 'Volts 2 PWM',
    b'07': 'Max Speed',
    b'08': 'Min Speed',
    b'09': 'Current Limit',
    b'0A': 'Error Codes',
    b'0B': 'Motor Volts',
    b'0C': 'HV Bus Volts',
    b'0D': 'Motor Current',
    b'0E': 'Calibrate Speed',
    b'0F': 'Roller Size',
    b'10': 'Roller Pulley Size',
    b'11': 'Motor Pulley Size',
    b'12': 'AC Input',
    b'13': 'Acceleration Rate',
    b'14': 'Deceleration Rate',
}

# Upright Low Voltage Motor Controller (22)
addr_22_cmd_dict = {
    b'00': 'RESERVED',
    b'01': 'Move Motors #1 and #2 UP',
    b'02': 'Move Motors #1 and #2 DOWN',
    b'03': 'Brake to Vcc',
    b'04': 'Brake to GND',
    b'05': 'Desired Position',
    b'06': 'Current Position',
    b'07': 'Move Motor #1 UP',
    b'08': 'Move Motor #1 DOWN',
    b'09': 'Move Motor #2 UP',
    b'0A': 'Move Motor #2 DOWN',
    b'0B': 'Stop ALL Motors',
    b'0C': 'Zero Motors',
    b'0D': 'Get Motor #1 Pot Value',
    b'0E': 'Get Motor #2 Pot Value',
    b'0F': 'Get Non-Volatile data (16 bytes)',
    b'10': 'Hall FX Sensor',
}

# Crawler (23)
addr_23_cmd_dict = {
    b'00': 'RESERVED',
    b'01': 'Command #1',
    b'02': 'Command #2',
}

# Console Tilt (24)
addr_24_cmd_dict = {
    b'00': 'RESERVED',
    b'01': 'Command #1',
    b'02': 'Command #2',
}

# Torque Sensor (25)
addr_25_cmd_dict = {
    b'00': 'RESERVED',
    b'01': 'Current Watts',
    b'02': 'Desired Watts',
    b'03': 'Torque Magnet Offset',
    b'04': 'Spring Constant #1',
    b'05': 'Spring Constant #2',
}

# Strider (26)
addr_26_cmd_dict = {
    b'00': 'RESERVED',
    b'01': 'Stride Direction',
    b'02': 'Total Stride Length',
    b'03': 'Current Stride Position',
    b'04': 'Stride Speed',
}

# Accelerometer (27)
addr_27_cmd_dict = {
    b'00': 'RESERVED',
    b'01': 'Device ID',
    b'02': 'Axis Data',
    b'03': 'Get Slope Data (%)',
    b'04': 'XYZ Axis Configuration',
    b'05': 'Get Device State',
    b'06': 'Arm Length (mm)',
    b'07': 'Arc Total Distance (m)',
    b'08': 'Arc Speed (kph*100)',
    b'C0': 'Control Registers',
    b'C1': 'Control Registers #1',
    b'C2': 'Control Registers #2',
    b'C3': 'Control Registers #3',
    b'C4': 'Control Registers #4',
    b'C5': 'Control Registers #5',
}

# Drive Motor PWM (28)
addr_28_cmd_dict = {
    b'00': 'RESERVED',
    b'01': 'PWM Out',
}

# Vibration Motor (29)
addr_29_cmd_dict = {
    b'00': 'RESERVED',
    b'01': 'Frequency',
    b'02': 'Amplitude',
    b'03': 'Timer',
}

# Proximity Sensor (3x)
addr_3x_cmd_dict = {
    b'00': 'RESERVED',
    b'01': 'Get Sensor Reading',
    b'02': 'Set Sensor Sensitivity',
    b'03': 'Enable/Disable Sensor',
}

# Incline (4x)
addr_4x_cmd_dict = {
    b'00': 'RESERVED',
    b'01': 'Desired Incline',
    b'02': 'Current Incline',
    b'03': 'Calibrate Incline',
    b'04': 'Stop Incline',
    b'05': 'Trans Max',
    b'06': 'Min Incline',
    b'07': 'Max Incline',
    b'08': 'Actual Incline',
    b'09': 'Negative Incline Offset',
    b'0A': 'Incline UP',
    b'0B': 'Incline DOWN',
    b'0C': 'Trans Zero',
    b'0D': 'Incline Use',
    b'0E': 'Max Incline Up PWM',
    b'0F': 'Max Incline Down PWM',
    b'10': 'Desired Trans Value',
    b'11': 'Current Trans Value',
    b'12': 'Trans Offset Up',
    b'13': 'Trans Offset Down',
    b'14': 'Trans Reposition Limit',
    b'15': 'Feedback Timeout',
    b'16': 'Open Loop PWM',
    b'17': 'Trans Max Reduction',
}

# Speed (5x)
addr_5x_cmd_dict = {
    b'00': 'RESERVED',
    b'01': 'Get/Set Speed (MPH)',
    b'02': 'Get/Set Speed (RPM)',
    b'03': 'Get/Set Precise Speed (RPM)',
    b'04': 'Cadence',
    b'05': 'Pedal Position'
}

# Resistance (6x)
addr_6x_cmd_dict = {
    b'00': 'RESERVED',
    b'01': 'Move Motor UP',
    b'02': 'Move Motor DOWN',
    b'03': 'Stop Motor',
    b'04': 'Calibrate Motor',
    b'05': 'Desired Pot Value',
    b'06': 'Current Pot Value',
    b'07': 'Min Pot Value',
    b'08': 'Max Pot Value',
    b'09': 'Target Voltage',
    b'0A': 'Step Loss',
}

# Fan (7x)
addr_7x_cmd_dict = {
    b'00': 'RESERVED',
    b'01': 'Frequency',
    b'02': 'PWM',
    b'03': 'Min PWM',
    b'04': 'Max PWM'
}

# Heart Rate (E1)
addr_E1_cmd_dict = {
    b'00': 'RESERVED',
    b'01': 'Heart Rate Measurement',
    b'02': 'HR Monitor Battery Level',
    b'03': 'Get Transciever State',
    b'04': 'Scan for Devices',
    b'05': 'Get # of Device Found',
    b'06': 'Connect to Device',
    b'07': 'Get Device ID#',
    b'08': 'Get Device Name',
    b'09': 'Get Signal Strength',
}

# BLE Speed Ring (E2)
addr_E2_cmd_dict = {
    b'00': 'RESERVED',
    b'01': 'Remote Keys',
    b'02': 'Ring Remote Battery Level',
    b'03': 'Get Transciever State',
    b'04': 'Scan for Devices',
    b'05': 'Get # of Devices Found',
    b'06': 'Connect to Device',
    b'07': 'Get Device ID#',
    b'08': 'Get Device Name',
    b'09': 'Get Signal Strength',
}

addr_to_cmd_dict = {
    b'21': addr_21_cmd_dict,
    b'22': addr_22_cmd_dict,
    b'23': addr_23_cmd_dict,
    b'24': addr_24_cmd_dict,
    b'25': addr_25_cmd_dict,
    b'26': addr_26_cmd_dict,
    b'27': addr_27_cmd_dict,
    b'28': addr_28_cmd_dict,
    b'29': addr_29_cmd_dict,
    b'3': addr_3x_cmd_dict,
    b'4': addr_4x_cmd_dict,
    b'5': addr_5x_cmd_dict,
    b'6': addr_6x_cmd_dict,
    b'7': addr_7x_cmd_dict,
    b'E1': addr_E1_cmd_dict,
    b'E2': addr_E2_cmd_dict,
}

addr_group = [ b'3', b'4', b'5', b'6', b'7' ]

# TODO: command to data length data

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

class ShortbusMessage:
    def __init__(self, raw_data, msg_len, msg_type_str, addr, addr_str, cmd_type, cmd_type_str, data_len, cmd, cmd_dir, cmd_str, data, data_str, checksum):
        self.raw_data = raw_data
        self.msg_len = msg_len
        self.msg_type_str = msg_type_str
        self.addr = addr
        self.addr_str = addr_str
        self.cmd_type = cmd_type
        self.cmd_type_str = cmd_type_str
        self.data_len = data_len
        self.cmd = cmd
        self.cmd_dir = cmd_dir
        self.cmd_str = cmd_str
        self.data = data
        self.data_str = data_str
        self.checksum = checksum

    def print_out(self):
        print('[ShortbusMessage] details:')
        print('  Type: ' + self.msg_type_str + ' (Length: ' + str(self.msg_len) + ')')
        print('  Address: (' + str(self.addr)[2:4] + ') ' + self.addr_str)
        print('  Command type: (' + str(self.cmd_type)[2:4] + ') ' + self.cmd_type_str)
        print('  Command: (' + str(self.cmd)[2:6] + ') ' + self.cmd_dir + ' ' + self.cmd_str)
        print('  Data: (' + str(self.data)[2:-1] + ') ' + self.data_str)
        print('  Checksum: ' + self.checksum)
        
    def to_bin(self):
        if self.cmd_dir == 'REQUEST':
            return self.to_bin_req()
        elif self.cmd_dir == 'RESPONSE':
            if self.cmd_type == b'03': # READ
                return self.to_bin_res_r()
            elif self.cmd_type == b'06': # WRITE
                return self.to_bin_res_w()
    
    def to_bin_req(self):
        return b':' + b'\r\n'
        
    def to_bin_res_r(self):
        content = self.addr + self.cmd_type + self.data_len + self.cmd + self.data
        self.checksum = calculate_checksum(content).upper()
        return b':' + content + self.checksum.encode('utf-8') + b'\r\n'
        
    def to_bin_res_w(self):
        content = self.addr + self.cmd_type + self.cmd + self.data
        self.checksum = calculate_checksum(content).upper()
        return b':' + content + self.checksum.encode('utf-8') + b'\r\n'

# TODO: why do these two echoes error?
os.system("echo 18 > /sys/class/gpio/export")
os.system("echo out > /sys/class/gpio/gpio18/direction")

ser = serial.rs485.RS485(port='/dev/ttyS0', baudrate=38400, bytesize=serial.SEVENBITS, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_TWO, timeout=0.2)
ser.rs485_mode = serial.rs485.RS485Settings(False,True)

receiving = False

monitor_dict = {}
monitor_dict_lock = Lock()

class SpooferThread(threading.Thread):
    def __init__(self,  *args, **kwargs):
        super(SpooferThread, self).__init__(*args, **kwargs)
        self._stop_event = threading.Event()
        self.setDaemon(True)
        
    def stop(self):
        self._stop_event.set()
        
        with monitor_q.mutex:
            monitor_q.queue.clear()

    def stopped(self):
        return self._stop_event.is_set()
    
    def run(self):
        while not self.stopped():
            req = receive()
        
            if req == None:
                time.sleep(0.01)
                continue
        
            try:
                req.cmd_type
                req.addr
                req.data_str
            except AttributeError:
                time.sleep(0.01)
                continue
        
            key = get_dict_key(req)
                
            if req.cmd_type == b'03': # Read
                val = read_value_from_monitor_dict(key, -1234567890)
                if val == -1234567890:
                    print(bcolors.WARNING + '[Shortbus:Warning] I don\'t have a response for this READ! Did you start spoofing after turning the machine on? ' + bcolors.ENDC)
                    req.print_out()
                    continue
                val = int(val, 16)
                res = make_response(req, val)
            elif req.cmd_type == b'06': # Write
                write_monitor_dict(req)
                print('[Shortbus:Write] ' + req.addr_str + ' ' + req.cmd_str + ': ' + req.data_str)
                res = make_response(req)
                if key.startswith(b'4'): #need to write to current incline for that motor as well
                    cmd_dict = addr_to_cmd_dict[b'4']
                    cmd_str = cmd_dict[b'02']
                    req2 = ShortbusMessage(req.raw_data, req.msg_len, req.msg_type_str, req.addr, req.addr_str, req.cmd_type, req.cmd_type_str, req.data_len, b'0002', req.cmd_dir, cmd_str, req.data, req.data_str, req.checksum)
                    write_monitor_dict(req2)
                if key.startswith(b'6'): #need to write to current resistance for that motor as well
                    cmd_dict = addr_to_cmd_dict[b'6']
                    cmd_str = cmd_dict[b'06']
                    req2 = ShortbusMessage(req.raw_data, req.msg_len, req.msg_type_str, req.addr, req.addr_str, req.cmd_type, req.cmd_type_str, req.data_len, b'0006', req.cmd_dir, cmd_str, req.data, req.data_str, req.checksum)
                    write_monitor_dict(req2)
            else:
                print(bcolors.FAIL + '[Shortbus:Error] Something is wrong with this message! ' + str(req) + bcolors.ENDC)
                res.print_out()
                break
        
            send_sb(res)
            time.sleep(0.01)

# This should mostly be used for development. It just
# monitors the RS-485 traffic and prints out the parsed
# messages to the console. You can set monitoring = False
# to stop it from other scripts. If its eating too much
# CPU, you can uncomment the time.sleeps(..) and adjust
# the wait times.
class MonitorThread(threading.Thread):
    def __init__(self, print_out=False, add_to_q=False, *args, **kwargs):
        super(MonitorThread, self).__init__(*args, **kwargs)
        self._stop_event = threading.Event()
        self.setDaemon(True)
        self.print_out = print_out
        self.add_to_q = add_to_q
        
    def stop(self):
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()
    
    def run(self):
        with monitor_q.mutex:
            monitor_q.queue.clear()
    
        while not self.stopped():
            sdata = try_read_msg()
            #print(sdata)
            if sdata != b'':
                msg = parse_message(sdata, self.print_out)
                if msg == None:
                    continue
            
                write_monitor_dict(msg)
            
                if self.add_to_q:
                    monitor_q.put(msg)
        
            time.sleep(0.005)

def write_monitor_dict(msg):
    global monitor_dict
    monitor_dict_lock.acquire()
    key = get_dict_key(msg)
    monitor_dict[key] = msg
    monitor_dict_lock.release()
    return key

def get_dict_key(msg):
    return msg.addr + msg.cmd[2:]

def read_monitor_dict():
    global monitor_dict
    monitor_dict_lock.acquire()
    copy = monitor_dict
    monitor_dict_lock.release()
    return copy

def read_value_from_monitor_dict(key, default=0):
    monitor_dict_lock.acquire()
    try:
        msg = monitor_dict[key]
        value = msg.data
    except:
        value = default
    monitor_dict_lock.release()
    
    return value

def clear_monitor_dict():
    monitor_dict_lock.acquire()
    monitor_dict.clear()
    monitor_dict_lock.release()

# Runs until it thinks it found a message and returns it.
# You should not call this while monitoring=True!
# You should not call receive() and send(..) on different threads!
def receive(print_out=False):
    global receiving
    
    receiving = True
    
    while receiving:
        sdata = try_read_msg()
        
        if sdata != b'':
            msg = parse_message(sdata, print_out)
            break
        
        time.sleep(0.005)
    
    return msg

def stop_receive():
    global receiving
    
    receiving = False

# Tries to read a complete message from the serial port
def try_read_msg():
    os.system("echo 0 > /sys/class/gpio/gpio18/value")
    time.sleep(0.005)
    sdata = ser.read()
    count = 0
    # most of our messages are going to be like 15-30 bytes, I believe
    # 256 seems like a good max number of bytes to read, ymmv
    while count < 256: 
        #count = ser.inWaiting()
        x = ser.read(1) 
        sdata += x
        if x == b'\n': #read until we get a \n
            break
        count += 1
    
    try:
        colonIdx = sdata.index(b':')
        if colonIdx != 0:
            sdata = sdata[colonIdx:]
    except ValueError:
        print(bcolors.WARNING + '[Shortbus:Warning] Tried to read a message, but its probably invalid or empty. Returning it anyway and hoping for the best: ' + bcolors.ENDC + str(sdata))
    
    return sdata

# Sends an arbitrary message
# You should not call this while monitoring=True!
# You should not call receive() and send(..) on different threads!
def send(msg):
    os.system("echo 1 > /sys/class/gpio/gpio18/value")
    time.sleep(0.005)
    ser.write(msg)

# Sends a ShortbusMessage via send(..), first converting it to binary
# You should not call this while monitoring=True!
# You should not call receive() and send(..) on different threads!
def send_sb(sb_msg):
    bmsg = sb_msg.to_bin()
    send(bmsg)

# Makes a response for the given request.
# params:
#   sb_req, ShortbusMessage object
#   val, optional, the data value to send in the response
# returns:
#   the binary response message
def make_response(sb_req, val=0):
    if sb_req.cmd_type == b'03':
        res = make_read_response(sb_req, val)
    elif sb_req.cmd_type == b'06':
        res = make_write_response(sb_req)
    else:
        print(bcolors.FAIL + '[Shortbus:Error] Trying to make a response for an unknown command type: ' + str(sb_req.cmd_type) + bcolors.ENDC)
        raise ValueError()
    
    bres = res.to_bin()
    #print('[ShortBus:Info] Made response: ' + str(bres))
    
    if not check_message(bres):
        print(bcolors.FAIL + '[Shortbus:Error] Oops, we made an invalid response. Check the code!' + bcolors.ENDC)
        
    return res

# Makes a read response for the given request.
# params:
#   sb_req, ShortbusMessage object
#   val, the data value to send in the response
# returns:
#   the ShortbusMessage response object
def make_read_response(sb_req, val):
    data_len = 2 # TODO: get this from a dict or something
    bhexval = '{0:0{1}x}'.format(val, data_len * 2).upper().encode('utf-8')
    bdata_len = '{0:0{1}x}'.format(data_len, 2).encode('utf-8')
    res = ShortbusMessage('', -1, '', sb_req.addr, '', b'03', '', bdata_len, b'01' + sb_req.cmd[2:], 'RESPONSE', '', bhexval, '', '')
    
    return res

# Makes a write response for the given request.
# params:
#   sb_req, ShortbusMessage object
# returns:
#   the ShortbusMessage response object
def make_write_response(sb_req):
    res = ShortbusMessage('', -1, '', sb_req.addr, '', b'06', '', '', b'01' + sb_req.cmd[2:], 'RESPONSE', '', sb_req.data, '', '')
    
    return res

# parse a message into an object
#   print_out=True, will print the human readable message details
# returns:
#   ShortbusMessage
def parse_message(msg, print_out=False):
    #print('[ShortBus:Info] Parsing message: ' + str(msg))
    if not check_message(msg):
        return 
    
    msg_len = get_msg_len(msg)
    msg_type_str = get_msg_type_str(msg)
    addr = get_addr(msg)
    addr_str = get_addr_str(msg)
    data_len = get_data_len(msg)
    cmd_type = get_cmd_type(msg)
    cmd_type_str = get_cmd_type_str(msg)
    cmd = get_cmd(msg)
    cmd_dir = get_cmd_dir(cmd)
    cmd_str = get_cmd_str(msg)
    data = get_data(msg)
    data_str = get_data_str(msg)
    checksum = get_checksum(msg)
    
    sb_msg = ShortbusMessage(msg, msg_len, msg_type_str, addr, addr_str, cmd_type, cmd_type_str, data_len, cmd, cmd_dir, cmd_str, data, data_str, checksum)
    
    if print_out:
        sb_msg.print_out()

    return sb_msg

# Checks a full message to make sure its valid
def check_message(msg):
    if not msg.startswith(b':'):
        print(bcolors.FAIL + '[ShortBus:Error] Message does not start with \':\'!' + bcolors.ENDC)
        return False

    if not msg.endswith(b'\r\n'):
        print(bcolors.FAIL + '[ShortBus:Error] Message does not end with \'\\r\\n\'!' + bcolors.ENDC)
        return False

    try:
        int(msg[1:-2], 16)
    except ValueError:
        print(bcolors.FAIL + '[ShortBus:Error] Message contains invalid hex characters!' + bcolors.ENDC)
        return False

    expected = get_checksum(msg)
    try:
        checksum = calculate_checksum(msg).upper()
    except ValueError:
        checksum = ' '
        
    if not (expected == checksum):
        print(bcolors.FAIL + '[ShortBus:Error] Message checksum is wrong! Expected ' + expected + ' but got ' + checksum + bcolors.ENDC)
        return False
    
    #print('[ShortBus:Info] Message appears to be valid.')
    return True

# get the checksum from the message
def get_checksum(msg):
    return msg[-4:-2].decode('utf-8')

# Supply either a full message, ex. b':510300020000AA\r\n'
# or just the "payload", ex. b'510300020000'
def calculate_checksum(msg):
    tmpmsg = msg
    if tmpmsg.startswith(b':'):
        tmpmsg = tmpmsg[1:] # remove the command start
    
    if tmpmsg.endswith(b'\r\n'):
        tmpmsg = tmpmsg[:-4] # remove the \r\n and the checksum

    tmpmsg = tmpmsg.decode('utf-8')
    split_tmp = [tmpmsg[i:i+2] for i in range(0, len(tmpmsg), 2)]
    #print(split_tmp)
    sum = 0x0
    for p in split_tmp:
        ph = '0x{0}'.format(p)
        #print(ph)
        sum += int(ph, 16)

    return twos_comp(sum)

# calculate the two's compliment
def twos_comp(sum):
    sumhexstr = hex(sum)
    #print(sumhexstr)
    binsumstr = bin(int(sumhexstr, 16))[2:]
    #print(binsumstr)
    tcsum = ~int(binsumstr, 2) + 1
    #print(tcsum)
    tchex = '{0:0{1}x}'.format((tcsum & 0xFF), 2)
    #print(tchex)
    return tchex

# gets the message length
def get_msg_len(msg):
    return len(msg)

# gets the message type as a string
def get_msg_type_str(msg):
    length = get_msg_len(msg)

    if length == 17:
        return "PRIMARY"

    return "SECONDARY"

# gets address from the message
def get_addr(msg):
    return msg[1:3]

# gets the human readable address from the message
def get_addr_str(msg):
    addr = get_addr(msg)
    return address_dict[addr]

# gets the command type from the message
def get_cmd_type(msg):
    return msg[3:5]

# gets the human readable command type from the message
def get_cmd_type_str(msg):
    cmd_type = get_cmd_type(msg)

    if cmd_type == b'03':
        return "READ"
    
    if cmd_type == b'06':
        return "WRITE"

    return "ERROR"

# gets the data length
def get_data_len(msg):
    cmd = get_cmd(msg)
    cmd_dir = get_cmd_dir(cmd)
    
    if cmd_dir == 'REQUEST':
        return b'-1'
    
    return msg[5:7]

# gets command from the message
def get_cmd(msg):
    msg_type = get_msg_type_str(msg)

    if msg_type == 'PRIMARY':
        return msg[5:9]

    cmd_type = get_cmd_type(msg)
    if cmd_type == b'03':
        return msg[7:11]

    return msg[5:9]

# 
def get_cmd_dir(cmd):
    if cmd[0:2] ==  b'00':
        return 'REQUEST'
    
    if cmd[0:2] == b'01':
        return 'RESPONSE'

    return 'ERROR'

# gets the 2 byte command that corresponds to the address command 
# from the full 4 byte command
def get_addr_cmd(cmd):
    return cmd[2:4]

# gets the human readable command from the message
def get_cmd_str(msg):
    addr = get_addr(msg)

    if addr[0:1] in addr_group:
        addr = addr[0:1]
    
    cmd_dict = addr_to_cmd_dict[addr]
    full_cmd = get_cmd(msg)
    cmd = get_addr_cmd(full_cmd)

    return cmd_dict[cmd]

# gets the raw data from the message
def get_data(msg):
    msg_type = get_msg_type_str(msg)

    if msg_type == 'PRIMARY':
        return msg[9:-4]

    cmd = get_cmd(msg)
    dir = get_cmd_dir(cmd)
    
    if dir == 'REQUEST':
        return msg[9:-4]

    if dir == 'RESPONSE':
        return msg[11:-4]

    return -1

# gets the data from the message as string
# converts the hex characters to a decimal number first
def get_data_str(msg):
     data = get_data(msg)
     return str(int(data, 16))

# Cause its easy to forget what the ShortbusMessage properties are all the way down here:
# raw_data, msg_len, msg_type_str, addr, addr_str, cmd_type, cmd_type_str, data_len, cmd, cmd_dir, cmd_str, data, data_str, checksum

#def spoofer_test():
#    spooferThread = SpooferThread()
#    spooferThread.start()
#    spooferThread.join()

#def monitor_test():
#    monitorThread = MonitorThread(print_out=True,add_to_q=True)
#    monitorThread.start()
#    monitorThread.join()

# !!! HERE BE DRAGONS !!!
# or, some development things...
#receive(True)
#sb_req = parse_message(b':510300020000AA\r\n')
#make_response(sb_req, 16)
#spoofer_test()
#monitor_test()