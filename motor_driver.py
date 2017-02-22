#derived from adafruit PWM servo driver written for arduino
#https://github.com/adafruit/Adafruit-PWM-Servo-Driver-Library

#
#
#
#need to understand the meaning of offset vs. subaddress
#in PWM library and in python SMBus library. Make sure
#interpretation is correct before running commands.
#
#
#
#
#

import smbus2
from time import sleep

DEVICE_ADDRESS = 0x40 #default pwm driver address

PCA9685_SUBADR1 = 0x2
PCA9685_SUBADR2 = 0x3
PCA9685_SUBADR3 = 0x4

PCA9685_MODE1 = 0x0
PCA9685_PRESCALE = 0xFE

LED0_ON_L = 0x6
LED0_ON_H = 0x7
LED0_OFF_L = 0x8
LED0_OFF_H = 0x9

ALLLED_ON_L = 0xFA
ALLLED_ON_H = 0xFB
ALLLED_OFF_L = 0xFC
ALLLED_OFF_H = 0xFD

pwm_frequency = 1600
full_reverse = 1100 #pulse width in microseconds for full reverse
full_forward = 1520 #pulse width in microseconds for full forward
min_pulse_width = 10**6/4096/pwm_frequency


#resets PWM driver on startup
def reset():
	bus = smbus2.SMBus(1)
	bus.write8(PCA9685_MODE1, 0x0)
	bus.close()

#sets 
def setPWMfreq(freq, bus):
	print 'Attempting to set frequency to '+ freq +'Hz'
	freq *= 0.9 #fix issue where requested frequency is overshot by factor of 1/0.9
	prescale = int(round(25000000 / 4096 / freq - 1))

	print 'Estimated pre-scale: ', prescale

	oldmode = read8(PCA9685_MODE1, 0x0)
	newmode = (oldmode&0x7F) | 0x10 #sleep
	write8(PCA9685_MODE1, newmode)
	write8(PCA9685_PRESCALE, prescale)
	write8(PCA9685_MODE1, oldmode)
	sleep(0.005)

	#set MODE1 register to turn on auto increment
	write8(PCA9685_MODE1, oldmode | 0xa1)

	print 'Mode now {0:#04x}'.format(bus.read_byte_data(PCA9685_MODE1,0))

def return_off_bit(throttle):
	off_bit = full_reverse/min_pulse_width + (full_forward - full_reverse)/(200*min_pulse_width)*throttle + 1
	return int(round(off_bit))

def setPWM(num, throttle):

	off = return_off_bit(throttle)
	on = 0


	print "Setting PWM {0}:{1}->{2}".format(num, on, off)
	bus = smbus.SMBus(1)

	#note: Each channel has 4 byte addresses for LED_ON_L,
	#LED_ON_H, LED_OFF_L, and LED_OFF_H. Shifting from LED0_ON_L
	#by 4*num gets to LED{num}_ON_L. 16-bit on time and off time
	#are written are written to each of the 4 registers in sequence.
	#Ex (LED0 90% Duty cycle -> LED off at 0.9*4096):
	#write_array = [LED0_ON_L, 0, 0, 0.9*4096, 0.9*4096>>8]
	write_array = [LED0_ON_L+4*num, on, on>>8, off, off>>8]
	bus.write_i2c_block_data(DEVICE_ADDRESS,0,write_array)
	bus.close()


#
#
#
#chose not to include setpin() from original docs.
#not sure what this is for...
#
#
#

#function to open comm, write data, close comm
def write8(addr,d):
	bus = smbus.SMBus(1)
	bus.write_byte_data(DEVICE_ADDRESS,0,addr)
	bus.write_byte_data(DEVICE_ADDRESS,0,d)
	bus.close()


#function to open comm, read data, close comm
def read8(addr):
	bus = smbus.SMBus(1)
	#not sure if this is right...
	#send local address to request data from,
	#then retrieve that data?
	bus.write_byte_data(DEVICE_ADDRESS,0,addr)
	bus.read_byte_data(DEVICE_ADDRESS,0)
	bus.close()

reset()
setPWMfreq(pwm_frequency)
set_pwm(0,50)

