#derived from adafruit PWM servo driver written for arduino
#https://github.com/adafruit/Adafruit-PWM-Servo-Driver-Library

#deal with nested file structure...
import smbus2.smbus2.smbus2 as smbus2

from time import sleep
#import matplotlib ##need to import this

verbose = True #toggle to False to suppress debug output

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

pwm_frequency = 500 #desired refresh rate; reset to exact value following setPWMfreq
#make sure frequency results in window width that is greater than full_forward width
#condition: 1/pwm_frequency*10**6 > full_forward (with some margin)

full_reverse = 1100.0 #pulse width in microseconds for full reverse
full_forward = 1940.0 #pulse width in microseconds for full forward
neutral = 1520.0 #pulse width in microseconds for 0% throttle

#resets PWM driver MODE1 registers to default
def reset():
	write8(PCA9685_MODE1, 0x0)
	verbose_print('Device has been reset.')

#given prescale, calculate effective refresh rate; return refresh rate (float) 
def calculate_refresh_rate(prescale):
	return 25000000.0 / 4096/(prescale + 1)
	#follows formula from table 5 of PCA9685 data sheet

#given refresh rate, calculate prescale; return prescale (float)
def calculate_prescale(refresh_rate):
	return 25000000.0 / 4096 / refresh_rate - 1
	#follows formula from table 5 of PCA9685 data sheet

#set refresh rate of PWM driver; return estimated refresh rate in Hz
def setPWMfreq(desired_freq):
	#fix issue where requested frequency is overshot by factor of 1/0.9
	frequency_scaling_factor = 0.9

	verbose_print('Attempting to set frequency to {0} Hz'.format(desired_freq))
	
	commanded_freq = frequency_scaling_factor*desired_freq

	prescale = calculate_prescale(commanded_freq)
	verbose_print('Exact pre-scale is {0}'.format(prescale))

	#round to nearest integer value
	prescale = int(round(prescale))
	verbose_print('Prescale rounded to {0}'.format(prescale))

	#actual commanded frequency given rounded prescale value
	commanded_frequency = calculate_refresh_rate(prescale)
	verbose_print('Frequency to be commanded including correction factor and prescale rounding is {0:.2f} Hz.'.format(commanded_frequency))

	estimated_output_frequency = commanded_frequency/frequency_scaling_factor
	verbose_print('Output frequency will be approximately {0:.2f} Hz'.format(estimated_output_frequency))

	oldmode = read8(PCA9685_MODE1)
	verbose_print(MODE1_status())
	newmode = oldmode | 0x10 #enable sleep bit (bit 4)
	#newmode = (oldmode & 0x7F) | 0x10 #sleep
	
	verbose_print("\nSetting newmode to {0:08b}. (Sleep mode)".format(newmode))
	write8(PCA9685_MODE1, newmode)
	verbose_print(MODE1_status())

	verbose_print("\nSetting PRESCALE to {0}".format(prescale))
	write8(PCA9685_PRESCALE, prescale)
	verbose_print("PRESCALE now set to: {0}".format(read8(PCA9685_PRESCALE)))
	
	verbose_print("\nReverting MODE1 to old mode: {0:08b}".format(oldmode))
	write8(PCA9685_MODE1, oldmode)
	verbose_print(MODE1_status())
	
	sleep(0.005)

	#set MODE1 register to turn on auto increment
	verbose_print('\nEnabling auto-increment. (Bit 5)')
	write8(PCA9685_MODE1, oldmode | 0xa0)
	verbose_print(MODE1_status())

	estimated_window_width = 1/estimated_output_frequency*10**6
	verbose_print("Estimated window width = 1/estimated_pwm_frequency = {0:.2f}".format(1/estimated_output_frequency*10**6))
	if estimated_window_width < full_forward + 50:
		print 'WARNING! Estimated pwm window width close to or less than 100%% forward throttle pulse duration.\n'
		print 'Reset PWM frequency to greater than (full forward throttle pulse with)^-1 to avoid issues.'

	return estimated_output_frequency

def return_on_counts(throttle):
	#calculate on count by linear interpolation between -100% and +100% throttle

	#convert throttle required to pulse width in microseconds
	pulse_width = (full_forward - full_reverse)/200*(throttle+100) + full_reverse

	#convert pulse width required to number of counts in pwm refresh window
	counts = pulse_width*pwm_frequency*10**(-6)*4096 - 1
	counts = int(round(counts))

	#confirm pulse width output after rounding counts to nearest value
	pulse_width = (counts+1)/(pwm_frequency*10.0**(-6)*4096)
	verbose_print("Calculated on counts for {0}% throttle: {1} counts".format(throttle, counts))
	verbose_print("Approximate pulse width: {0:.0f} us".format(pulse_width))
	
	return [counts, pulse_width]

def setPWM(num, throttle):
	
	#get pulse width and off bit to achieve throttle
	off, pulse_width= return_on_counts(throttle)

	#optional delay time until pulse width begins in binary
	#must be in 12-bit format
	on = 10 #in counts, decimal
	off = off + on #shift off time by on delay time

	#verbose_print('Converting variable \'off\' to 12-bit binary representation.')
	#off = '{0:12b}'.format(off)
	verbose_print('Variable \'on\' = {0}'.format(on))
	verbose_print('Variable \'off\' = {0}'.format(off))

	verbose_print("Setting PWM {0}: {1}->{2}".format(num, on, off))
	#verbose_print("Approximate pulse width: {0} us").format(pulse_width)


	#note: Each channel has 4 byte addresses for LED_ON_L,
	#LED_ON_H, LED_OFF_L, and LED_OFF_H. Shifting from LED0_ON_L
	#by 4*num gets to LED{num}_ON_L. 16-bit on time and off time
	#are written are written to each of the 4 registers in sequence.
	#See PCA9865 documentation for more details.
	
	start_register = LED0_ON_L + 4*num
	write_array = [on, on>>8, off, off>>8]

	verbose_print('Start register is {0:#03x}'.format(start_register))
	verbose_print('Write Array = {0:012b}, {1:012b}, {2:012b}, {3:012b}'.format(*write_array))


	verbose_print('Writing on and off counts to channel {0}'.format(num))
	bus = smbus2.SMBus(1)
	for i in xrange(4):
		verbose_print('Writing write array element {0} = {1:#012b} to register {2:#03x}'.format(i,write_array[i],start_register+i))
		bus.write_byte_data(DEVICE_ADDRESS, start_register+i, write_array[i])
		
		#check values were written correctly
		new_value = bus.read_byte_data(DEVICE_ADDRESS, start_register+i)
		verbose_print('Register {0:#03x} value is now {1:#08b}'.format(start_register+i,new_value))
	bus.close()

def motor_startup():
	#set all 3 channels to neutral
	setPWM(0,0)
	setPWM(1,0)
	setPWM(2,0)

	#plug in the ESCs!!
	raw_input('Plug in the power supply. Press enter to continue...')

	#wait until motor controller starts up
	#sleep(2.0)

	#move throttle to slightly over 50%
	setPWM(0,55)
	setPWM(1,55)
	setPWM(2,55)

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
	bus = smbus2.SMBus(1)
	bus.write_byte_data(DEVICE_ADDRESS,addr,d)
	bus.close()

#function to open comm, read data, close comm
def read8(addr):
	bus = smbus2.SMBus(1)
	data = bus.read_byte_data(DEVICE_ADDRESS,addr)
	bus.close()
	return data

#return pretty print string of MODE1 register values
def MODE1_status():
	output = ["MODE1 Status:\n"]
	mode_1_status = list('{0:08b}'.format(read8(PCA9685_MODE1)))
	mode_1_registers = ['Restart (bit 7)', 'EXTCLK (bit 6)', 'AI (BIT 5)', 'SLEEP (BIT 4)', 'SUB1 (BIT 3)', 'SUB2 (BIT 2)', 'SUB3 (BIT 1)', 'ALLCALL (BIT 0)']
	for b in mode_1_registers:
		output.append('{0}:  {1}\n'.format(b,mode_1_status.pop(0)))
	output.append('\n')
	return ''.join(output)

#prints debug info if 'verbose' set to True
def verbose_print(*arg):
	if(verbose):
		for a in arg:
			print a
	return None

MODE1_status()
print '\n'
reset()
pwm_frequency = setPWMfreq(pwm_frequency)
print 'PWM frequency before setting PWM: {0:.02f} Hz'.format(pwm_frequency)

motor_startup()

setPWM(0,0)