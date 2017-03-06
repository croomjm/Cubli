#!/usr/bin/env python

#Basic imports
from ctypes import *
import sys
import time
#Phidget specific imports
from Phidgets.PhidgetException import PhidgetErrorCodes, PhidgetException
from Phidgets.Events.Events import AttachEventArgs, DetachEventArgs, ErrorEventArgs, EncoderPositionChangeEventArgs, InputChangeEventArgs
from Phidgets.Devices.Encoder import Encoder
from Phidgets.Phidget import PhidgetLogLevel


#Create an encoder object
try:
    encoder = Encoder()
except RuntimeError as e:
    print("Runtime Exception: {0:s}".format(e.details))
    print("Exiting....")
    exit(1)

#Information Display Function
def displayDeviceInfo():
    print("|------------|----------------------------------|--------------|------------|")
    print("|- Attached -|-              Type              -|- Serial No. -|-  Version -|")
    print("|------------|----------------------------------|--------------|------------|")
    print("|- {0:8} -|- {1:30s} -|- {2:10d} -|- {3:8d} -|".format(encoder.isAttached(), encoder.getDeviceName(), encoder.getSerialNum(), encoder.getDeviceVersion()))
    print("|------------|----------------------------------|--------------|------------|")

#Event Handler Callback Functions
def encoderAttached(e):
    attached = e.device
    print("Encoder %i Attached!" % (attached.getSerialNum()))

def encoderDetached(e):
    detached = e.device
    print("Encoder %i Detached!" % (detached.getSerialNum()))

def encoderError(e):
    try:
        source = e.device
        print("Encoder %i: Phidget Error %i: %s" % (source.getSerialNum(), e.eCode, e.description))
    except PhidgetException as e:
        print("Phidget Exception %i: %s" % (e.code, e.details))

def encoderInputChange(e):
    source = e.device
    print("Encoder %i: Input %i: %s" % (source.getSerialNum(), e.index, e.state))

def encoderPositionChange(e):
    source = e.device
    print("Encoder %i: Encoder %i -- Change: %i -- Time: %i -- Position: %i" % (source.getSerialNum(), e.index, e.positionChange, e.time, encoder.getPosition(e.index)))

#Main Program Code
try:
	#logging example, uncomment to generate a log file
    encoder.enableLogging(PhidgetLogLevel.PHIDGET_LOG_VERBOSE, "phidgetlog.log")

    encoder.setOnAttachHandler(encoderAttached)
    encoder.setOnDetachHandler(encoderDetached)
    encoder.setOnErrorhandler(encoderError)
    encoder.setOnInputChangeHandler(encoderInputChange)
    encoder.setOnPositionChangeHandler(encoderPositionChange)
except PhidgetException as e:
    print("Phidget Error %i: %s" % (e.code, e.details))
    exit(1)

print("Opening phidget object....")

try:
    encoder.openPhidget()
except PhidgetException as e:
    print("Phidget Error %i: %s" % (e.code, e.details))
    exit(1)

print("Waiting for attach....")

try:
    encoder.waitForAttach(10000)
except PhidgetException as e:
    print("Phidget Error %i: %s" % (e.code, e.details))
    try:
        encoder.closePhidget()
    except PhidgetException as e:
        print("Phidget Error %i: %s" % (e.code, e.details))
        exit(1)
    exit(1)
else:
    displayDeviceInfo()

for i in xrange(3):
    print "Encoder channel {0} enabled state is {1}".format(i,encoder.getEnabled(i))
    print "Setting channel {0} to enabled state 'True'".format(i)
    encoder.setEnabled(i,True)
    print "Encoder channel {0} enabled state is {1}".format(i,encoder.getEnabled(i))

def positionChange():
    print "I moved..."

encoder.setOnPositionChangeHandler(positionChange)


print 'Press Enter to Continue...'
chr = sys.stdin.read(1)

positions = [0,0,0,0]
position_log = [0,0,0,0,0]
time_init = time.time()
for j in xrange(1000):
    for i in xrange(3):
        positions[i] = encoder.getPosition(i)
        print "Position of channel {0}: {1} pulses".format(i, positions[i])
        position_log.append([time.time()-time_init].extend(positions))
    time.sleep(.25)


print("Closing...")

print "Position log:"
for l in position_log:
    print ','.join(l)


try:
    encoder.closePhidget()
except PhidgetException as e:
    print("Phidget Error %i: %s" % (e.code, e.details))
    print("Exiting....")
    exit(1)

print("Done.")
exit(0)