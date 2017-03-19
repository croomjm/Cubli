#!/usr/bin/env python

#Basic imports
from ctypes import *
import sys
import time
import numpy
from collections import deque
#Phidget specific imports
from Phidgets.PhidgetException import PhidgetErrorCodes, PhidgetException
from Phidgets.Events.Events import AttachEventArgs, DetachEventArgs, ErrorEventArgs, EncoderPositionChangeEventArgs, InputChangeEventArgs
from Phidgets.Devices.Encoder import Encoder
from Phidgets.Phidget import PhidgetLogLevel

class Encoders:
    default_unit = 'rad/s'

    def __init__(self, counts_per_revolution, recording = False, units = default_unit):
        self.counts_per_revolution = counts_per_revolution
        self.max_counts = 2**30 #set max counts below max integer regular int size
        self.unitConversionMultiplier = None
        self.__setVelocityUnits(units)
        self.velocity_median_filter_length = 20

        #set encoder direction defaults
        #may be modified to modify interpreted direction of encoder to match intended ESC input
        self.encoder_direction = {0:1,1:1,2:1}

        #Create an encoder object
        try:
            self.encoder = Encoder()
        except RuntimeError as e:
            raise RuntimeError("Runtime Exception: {0:s}".format(e.details))

        #Set event handler behavior
        try:
            self.encoder.setOnAttachHandler(encoderAttached)
            self.encoder.setOnDetachHandler(encoderDetached)
            self.encoder.setOnErrorhandler(encoderError)
        except PhidgetException as e:
            raise RuntimeError("Phidget Error {0}: {1}".format(e.code, e.details))

        self.time_init = time.time()
    
    class dataLog:
        #class to contain saved data and save to file when commanded
        def __init__(self,buffer_length = 5*10**4,logging = True):
            self.buffer_length = buffer_length #max number of data points to save
            self.velocities = deque(self.buffer_length)
            self.counts = deque(self.buffer_length)
            self.logging = logging

        def appendVelocities(self, velocity_array):
            if self.logging:
                self.velocities.append(velocity_array)

        def appendCounts(self, counts_array):
            if self.logging:
                self.counts.append(counts_array)

        def saveLog(self):
            return None

    #Event Handler Callback Functions
    def __encoderAttached(e):
        attached = e.device
        print "Encoder {0} Attached!".format(attached.getSerialNum())
        self.__displayDeviceInfo()

    def __encoderDetached(e):
        detached = e.device
        raise RuntimeError("Encoder {0} Detached!".format(detached.getSerialNum()))

    def __encoderError(e):
        try:
            source = e.device
            raise RuntimeError("Encoder {0}: Phidget Error {1}: {2}".format(source.getSerialNum(), e.eCode, e.description))
        except PhidgetException as e:
            raise RuntimeError("Phidget Exception {0}: {1}".format(e.code, e.details))

    #External Methods
    def getVelocities(self):
        #return instantaneous median filtered velocities for each encoder
        count_array = self.__returnCountArray(self.velocity_median_filter_length)
        median_counts = self.__medianFilter(count_array)
        velocities = self.__returnVelocitiesFromCounts(median_counts)
        
        #check if any encoders need to be reset to avoid exceeding max integer value
        #if so, reset them
        encoders_to_reset = [i-1 for i, x in enumerate(median_counts) if abs(x)>self.max_counts]
        for i in encoders_to_reset:
            self.__resetCounts(i)

        return velocities

    def reverseDirection(self, index):
        #set interpreted spin direction of an encoder channel
        self.encoder_direction[index] *= -1
        return None

    #Internal Methods
    def __returnVelocitiesFromCounts(self,counts_array):
        #convert counts to velocity in selected units
        return [counts_array[0], i*self.unitConversionMultiplier for i in counts_array[1:3]]

    def __medianFilter(self,array):
        return numpy.median(array,axis=1)

    def __returnEncoderTime(self,time_init):
        return time.time()-self.time_init

    def __returnCountArray(self,iterations):
        #return counts array with 'iterations' rows of data
        #row structure: [time of measurement, encoder 0 count, encoder 1 count, encoder 2 count]
        time_start = self.__returnEncoderTime(self.time_init)
        counts_array = []
        for _ in xrange(iterations):
            counts = [self.encoder.getCounts(i) for i in xrange(3)]
            count_array.append([self.__returnEncoderTime(self.time_init), counts])
        return count_array

    def __displayDeviceInfo():
        #Information Display Function
        print("|------------|----------------------------------|--------------|------------|")
        print("|- Attached -|-              Type              -|- Serial No. -|-  Version -|")
        print("|------------|----------------------------------|--------------|------------|")
        print("|- {0:8} -|- {1:30s} -|- {2:10d} -|- {3:8d} -|".format(encoder.isAttached(), encoder.getDeviceName(), encoder.getSerialNum(), encoder.getDeviceVersion()))
        print("|------------|----------------------------------|--------------|------------|")

    def __resetCounts(self, index):
        #reset encoder channel to zero if counts exceed int max size
        self.encoder.setPosition(index,0)

    def __setVelocityUnits(self, units):
        #toggle output between rad/s, Hz, rpm
        #baseline units are rad, rad/s
        #self.unitConversion multiplies rad/s to get to desired units
        unitsConversion = {'rad/s': 1, 'Hz': 1.0/(2.0*math.pi), 'rpm': 60.0/(2.0*math.pi)}
        if units in unitsConversion:
            self.unitConversionMultiplier = unitsConversion[units]
            print 'Units set to {0}.'.format(units)
        else:
            self.unitConversionMultiplier = unitsConversion[default_unit]
            print('Requested units ({0}) not available. Using {1} instead.'.format(units,self.default_unit))



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

try:
    encoder.closePhidget()
except PhidgetException as e:
    print("Phidget Error %i: %s" % (e.code, e.details))
    print("Exiting....")
    exit(1)

print("Done.")
exit(0)