#!/usr/bin/env python3

from dataclasses import dataclass
from flask import Flask, render_template, request
from queue import Queue
from threading import Thread
from time import sleep
from typing import List
import math
import json
import random
import threading
import os
#os.environ['GPIOZERO_PIN_FACTORY'] = os.environ.get('GPIOZERO_PIN_FACTORY', 'mock') # uncomment for dev on a non-pi machine
import gpiozero

app = Flask(__name__)

devices = { }

@dataclass
class ConsoleDevice:
	bcmPin: int
	rpm: int
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
			jitterRpm = device.rpm + random.choices([-1, 0, 1], weights=[0.15, 0.7, 0.15], k=1)[0]
			delaySec = (14110.1 / math.pow(jitterRpm, 0.988567318803339)) / 1000.0
			print('running at ' + str(jitterRpm) + ' rpm (delay ' + str(delaySec) + ' sec) on pin ' + str(device.bcmPin))
			wire.on()
			sleep(delaySec)
			if not devices[self.gpioPin].keepRunning:
				return
			wire.off()
			sleep(delaySec)
			if not devices[self.gpioPin].keepRunning:
				return

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
	return render_template('edit.html', bcmPin=bcmPin, rpm=rpm)

@app.route('/set', methods=['POST'])
def set():
	reqData = request.get_json (force=True)
	bcmPin = int(reqData['bcmPin'])
	rpm = int(reqData['rpm'])
	device = devices.get(bcmPin)

	if device is None:
		device = ConsoleDevice(bcmPin, rpm, None, True)
		devices[bcmPin] = device

	device.rpm = rpm

	if device.pedalThread is None:
		device.pedalThread = PedalLooper(gpioPin=bcmPin)
		device.keepRunning = True
		device.pedalThread.start()
	
	return json.dumps({'success':True}), 200, {'ContentType':'application/json'} 

@app.route('/stop', methods=['POST'])
def stop():
	reqData = request.get_json (force=True)
	bcmPin = int(reqData['bcmPin'])
	device = devices.get(bcmPin)
	
	if device is None:
		print('Not running on ' + str(bcmPin))
		return json.dumps({'success':True}), 404, {'ContentType':'application/json'} 
	
	device.keepRunning = False
	device.pedalThread = None
	return json.dumps({'success':True}), 200, {'ContentType':'application/json'} 

