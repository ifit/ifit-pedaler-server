#!/usr/bin/env python3

from dataclasses import dataclass
from dotenv import load_dotenv
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
from threading import Thread, Event
from time import sleep
from typing import List
import gpiozero
import json
import math
import os
import random
import serial
import shortbus
import threading
import time

load_dotenv()

#os.environ['GPIOZERO_PIN_FACTORY'] = os.environ.get('GPIOZERO_PIN_FACTORY', 'mock') # uncomment for dev on a non-pi machine

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
socketio = SocketIO(app, async_mode=None)

devices = { }

shortbus_monitor_worker = None
shortbus_socket_update_worker = None
stop_shortbus_mon_event = Event()

@dataclass
class ConsoleDevice:
    useRs485: bool
    bcmPin: int
    rpm: int
    strokeRpm: bool
    pedalThread: object
    keepRunning: bool

class PedalLooper(threading.Thread):
    def __init__(self, gpioPin, args=(), kwargs=None):
        threading.Thread.__init__(self, args=(), kwargs=None)
        self.gpioPin = gpioPin
        self.daemon = True

    def run(self):
        device = devices[self.gpioPin]
        wire = gpiozero.LED(int(self.gpioPin))
        while devices[self.gpioPin].keepRunning:
            if device.strokeRpm:
                self.runStroke(device, wire)
            else:
                self.runConstant(device, wire)

    def runConstant(self, device, wire):
        jitterRpm = device.rpm + random.choices([-1, 0, 1], weights=[0.15, 0.7, 0.15], k=1)[0]
        delaySec = (14110.1 / math.pow(jitterRpm, 0.988567318803339)) / 1000.0 # These magic numbers came from experimental data
        print('running at ' + str(jitterRpm) + ' rpm (delay ' + str(delaySec) + ' sec) on pin ' + str(device.bcmPin))
        wire.on()
        sleep(delaySec)
        if not devices[self.gpioPin].keepRunning:
            return
        wire.off()
        sleep(delaySec)
        if not devices[self.gpioPin].keepRunning:
            return

    # Rowers expect the signal to ramp from 300 to 900 pulses and then back down to count strokes
    # we'll treat the RPM as strokes per minute, and thats how often we ramp up and down between 300 and 900 pulses
    def runStroke(self, device, wire):
        jitterSpm = device.rpm + random.choices([-1, 0, 1], weights=[0.15, 0.7, 0.15], k=1)[0]
        strokeDelaySec = (14110.1 / math.pow(jitterSpm, 0.988567318803339)) / 1000.0
        print('Stroking at ' + str(jitterSpm) + ' spm (delay ' + str(strokeDelaySec) + 'sec) on pin ' + str(device.bcmPin))
        timerSec = 0.0
        while timerSec < strokeDelaySec:
            rpm = self.simpleLerp(timerSec / strokeDelaySec, 300, 900)
            delaySec = (14110.1 / math.pow(rpm, 0.988567318803339)) / 1000.0
            #print('Stroking Up -- spm: ' + str(jitterSpm) + ' stroke delay (s): ' + str(strokeDelaySec) + ' timer (s): ' + str(timerSec) + ' delay (s): ' + str(delaySec))
            wire.on()
            sleep(delaySec)
            wire.off()
            sleep(delaySec)
            timerSec += delaySec
        
        timerSec = 0.0
        while timerSec < strokeDelaySec:
            rpm = self.simpleLerp(timerSec / strokeDelaySec, 900, 300)
            delaySec = (14110.1 / math.pow(rpm, 0.988567318803339)) / 1000.0
            #print('Stroking Down -- spm: ' + str(jitterSpm) + ' stroke delay (s): ' + str(strokeDelaySec) + ' timer (s): ' + str(timerSec) + ' delay (s): ' + str(delaySec))
            wire.on()
            sleep(delaySec)
            wire.off()
            sleep(delaySec)
            timerSec += delaySec
    
    def simpleLerp(self, alpha, at0, at1):
        return ((1 - alpha) * at0) + (alpha * at1)


def sortByPin(e):
    return e.bcmPin

@app.route('/')
def homePage():
    data = list(devices.values())
    data.sort(key=sortByPin)
    return render_template('index.html', deviceData=data)

@app.route('/edit')
def statusPage():
    bcmPin = request.args.get('bcmPin', 21)
    rpm = request.args.get('rpm', 45)
    strokeRpm = request.args.get('strokeRpm', False)
    return render_template('edit.html', bcmPin=bcmPin, rpm=rpm, strokeRpm=strokeRpm)

@app.route('/rs485')
def rs485Page():
    return render_template('rs485.html')

@socketio.on('connect')
def testSocketConnect():
    print('socket.io connected')
    
@socketio.on('disconnect')
def testSocketDisconnect():
    print('socket.io disconnected')

@socketio.on('connect', namespace='/rs485socket')
def rs485SocketConnect():
    print('RS-485 Socket Client: CONNECTED')
    shortbus_monitor_worker = threading.Thread(target=shortbus.monitor, daemon=True)
    shortbus_monitor_worker.start()
    shortbus_socket_update_worker = threading.Thread(target=shortbusSocketUpdate, daemon=True)
    shortbus_socket_update_worker.start()

@socketio.on('disconnect', namespace='/rs485socket')
def rs485SocketDisconnect():
    print('RS-485 Socket Client: DISCONNECTED')
    shortbus.stop_monitor()
    stop_shortbus_mon_event.set()

@app.route('/set', methods=['POST'])
def set():
    reqData = request.get_json(force=True)
    useRs485 = bool(reqData['useRs485'])
    bcmPin = int(reqData['bcmPin'])
    rpm = int(reqData['rpm'])
    strokeRpm = bool(reqData['strokeRpm'])

    if bcmPin < 0 or bcmPin > 27:
        return json.dumps({'success':False, 'message':'BCM pin outside of allowable range.'}), 400, {'ContentType':'application/json'}
    
    # TODO: Some more work making sure legacy pedaling and RS-485 dont clobber each other
    if any(d.useRs485 for d in devices) and (bcmPin == 14 or bcmPin == 15 or bcmPin == 18):
        return json.dumps({'success':False, 'message':'Cannot use pins 14, 15, or 18 when RS-485 is in use.'}), 400, {'ContentType':'application/json'}
    
    device = devices.get(bcmPin)

    if device is None:
        device = ConsoleDevice(bcmPin, rpm, strokeRpm, None, True)
        devices[bcmPin] = device

    device.rpm = rpm
    device.strokeRpm = strokeRpm

    if device.pedalThread is None:
        device.pedalThread = PedalLooper(gpioPin=bcmPin)
        device.keepRunning = True
        device.pedalThread.start()
    
    return json.dumps({'success':True}), 200, {'ContentType':'application/json'} 

@app.route('/stop', methods=['POST'])
def stop():
    reqData = request.get_json (force=True)
    bcmPin = int(reqData['bcmPin'])

    if bcmPin < 0:
        stopAll()
        return json.dumps({'success':True}), 200, {'ContentType':'application/json'} 

    device = devices.get(bcmPin)
    
    if device is None:
        print('Not running on ' + str(bcmPin))
        return json.dumps({'success':True}), 404, {'ContentType':'application/json'} 
    
    device.keepRunning = False
    device.pedalThread = None
    return json.dumps({'success':True}), 200, {'ContentType':'application/json'} 

def stopAll():
    for i in range(28):
        device = devices.get(i)
        if device is None:
            continue
        else:
            device.keepRunning = False
            device.pedalThread = None

def shortbusSocketUpdate():
    while not stop_shortbus_mon_event.is_set():
        if shortbus.monitor_q.empty():
            time.sleep(0.01)
            continue
        
        msg = shortbus.monitor_q.get()
        emit('rs485MonUpdate', {'data':msg}, namespace='/rs485socket')
        shortbus.monitor_q.task_done()
        time.sleep(0.01)

if __name__ == '__main__':
    from waitress import serve
    serve(socketio.run(app, host='0.0.0.0', port=5000))
