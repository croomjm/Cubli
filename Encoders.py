#!/usr/bin/env python

#Basic imports
from ctypes import *
import sys, time
from collections import deque
from math import pi
#Phidget specific imports
from Phidgets.PhidgetException import PhidgetErrorCodes, PhidgetException
from Phidgets.Events.Events import AttachEventArgs, DetachEventArgs, ErrorEventArgs, EncoderPositionChangeEventArgs, InputChangeEventArgs
from Phidgets.Devices.Encoder import Encoder
from Phidgets.Phidget import PhidgetLogLevel

class Encoders:
    default_unit = 'rad/s'

    def __init__(self, countsPerRevolution, units = default_unit):
        self.countsPerRevolution = float(countsPerRevolution)
        print 'self.countsPerRevolution : {0}'.format(self.countsPerRevolution)
        self.max_counts = 2**30 #set max counts below max integer regular int size
        self.unitConversionMultiplier = None
        self.__setVelocityUnits(units)

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
            self.encoder.setOnAttachHandler(self.__encoderAttached)
            self.encoder.setOnDetachHandler(self.__encoderDetached)
            self.encoder.setOnErrorhandler(self.__encoderError)
        except PhidgetException as e:
            raise RuntimeError("Phidget Error {0}: {1}".format(e.code, e.details))

        try:
            self.encoder.openPhidget()
            self.encoder.waitForAttach(10000)
        except PhidgetException as e:
            raise RuntimeError("Phidget Error {0}: {1}.\nFailed 'openPhidget()'.".format(e.code, e.details))

        time.sleep(2) #pause here to avoid starting motors before encoders fully initialized

        #set all encoder positions to 0
        for i in xrange(3):
            self.__resetCounts(i)

        self.time_init = time.time()
        self.prevCountArray = [self.time_init, 0, 0, 0]

    #Event Handler Callback Functions
    def __encoderAttached(self,e):
        attached = e.device
        print "Encoder {0} Attached!".format(attached.getSerialNum())
        #self.__displayDeviceInfo()

    def __encoderDetached(self,e):
        detached = e.device
        raise RuntimeError("Encoder {0} Detached!".format(detached.getSerialNum()))

    def __encoderError(self,e):
        try:
            source = e.device
            raise RuntimeError("Encoder {0}: Phidget Error {1}: {2}".format(source.getSerialNum(), e.eCode, e.description))
        except PhidgetException as e:
            raise RuntimeError("Phidget Exception {0}: {1}".format(e.code, e.details))

    #External Methods
    def resetCounter(self, index):
        self.encoder.setPostion(index)

    def getVelocities(self):
        #return instantaneous velocities for each encoder
        print '\n'
        print 'self.unitConversionMultiplier : {0}'.format(self.unitConversionMultiplier)
        count_array = self.returnCountArray()
        print 'count_array : {0}'.format(count_array)
        print 'prevCountArray : {0}'.format(self.prevCountArray)
        diff_array = [float(j-self.prevCountArray[i]) for i,j in enumerate(count_array)]
        print 'diff_array : {0}'.format(diff_array)
        self.prevCountArray = [i for i in count_array]
        velocities = [count_array[0]] + self.__returnVelocitiesFromCounts(diff_array)
        print 'velocities : {0}'.format(velocities)

        #check if any encoders need to be reset to avoid exceeding max integer value
        #if so, reset them
        encoders_to_reset = [i for i,x in enumerate(count_array[1:]) if abs(x)>self.max_counts]
        for i in encoders_to_reset:
            print 'Reset counts on index {0} from {1} to 0 to avoid int overflow.'.format(i, )
            self.__resetCounts(i)

        return velocities

    def reverseDirection(self, index):
        #set interpreted spin direction of an encoder channel
        self.encoder_direction[index] *= -1
        return None

    def returnCountArray(self):
        #return counts array:
        #[time of measurement, encoder 0 count, encoder 1 count, encoder 2 count]
        counts_array = []
        counts_array = [time.time()]+[self.encoder.getPosition(i)*self.encoder_direction[i] for i in xrange(3)]
        return counts_array

    #Internal Methods
    def __returnVelocitiesFromCounts(self,diffCountsArray):
        #convert counts to velocity in selected units
        return [i/diffCountsArray[0]/self.countsPerRevolution*self.unitConversionMultiplier for i in diffCountsArray[1:]]

    def __returnEncoderTime(self,time_init):
        return time.time()-self.time_init

    def __displayDeviceInfo():
        #Information Display Function
        print("|------------|----------------------------------|--------------|------------|")
        print("|- Attached -|-              Type              -|- Serial No. -|-  Version -|")
        print("|------------|----------------------------------|--------------|------------|")
        print("|- {0:8} -|- {1:30s} -|- {2:10d} -|- {3:8d} -|".format(encoder.isAttached(), encoder.getDeviceName(), encoder.getSerialNum(), encoder.getDeviceVersion()))
        print("|------------|----------------------------------|--------------|------------|")

    def __resetCounts(self, index):
        #reset encoder channel position to zero
        self.encoder.setPosition(index,0)

    def __setVelocityUnits(self, units):
        #toggle output between rad/s, Hz, rpm
        #multipliers for converting from Hz
        #self.unitConversion is used in __returnVelocitiesFromCounts to get to desired units
        unitsConversion = {'rad/s': (2.0*pi), 'Hz': 1, 'rpm': 60.0}
        if units in unitsConversion:
            self.unitConversionMultiplier = unitsConversion[units]
            print 'Units set to {0}.'.format(units)
        else:
            self.unitConversionMultiplier = unitsConversion[default_unit]
            print('Requested units ({0}) not available. Using {1} instead.'.format(units,default_unit))