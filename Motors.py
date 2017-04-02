#deal with nested file structure on smbus2...
import smbus2.smbus2.smbus2 as smbus2
from time import sleep

#Constants for PCA9685
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

verbose = False #toggle to False to suppress debug output


#driver for adafruit PWM servo driver
#derived from https://github.com/adafruit/Adafruit-PWM-Servo-Driver-Library
#uses NXP PCA 9685 16-channel, 12-bit PWM controller
class Motors:

    #fix issue where requested frequency is overshot by factor of 1/0.97
    frequency_scaling_factor = 0.97


    def __init__(self, i2c_bus_num, nmotors, min_throttle_percentage, max_throttle_percentage, min_throttle_pulse_width, max_throttle_pulse_width):

        #desired refresh rate; reset to exact value following setPWMfreq
        #self.PWM_frequency = float(PWM_frequency)
        #make sure frequency results in window width that is greater than max throttle pulse width
        #condition: 1/pwm_frequency*10**6 > max_throttle_pulse_width (with some margin)

        #set i2c bus to use for communication with PCA9685
        self.i2c_bus_num = i2c_bus_num

        self.min_throttle_pulse_width = float(max_throttle_pulse_width)
        #pulse width in microseconds for minimum throttle

        self.max_throttle_pulse_width = float(min_throttle_pulse_width)
        #pulse width in microseconds for max throttle

        self.min_throttle_percentage = int(min_throttle_percentage)
        #minimum throttle

        self.max_throttle_percentage = int(max_throttle_percentage)
        #maximum throttle

        self.nmotors = int(nmotors)

        self.prescale = None
        self.PWM_frequency = None #in Hz
        self.window_width = None #in microseconds

        #reset to remove any stored values
        self.reset()

    """
    Section for internal use functions
    """

    #resets PWM driver MODE1 registers to default
    def reset(self):
        self.__verbose_print(self.__MODE1_status())
        self.__write_array(PCA9685_MODE1,[0x0, 0x6])
        self.__verbose_print('Device has been reset.')
        self.__verbose_print(self.__MODE1_status())

    #open i2c bus, write array of bytes to address, close bus
    def __write_array(self,addr, array):
        bus = smbus2.SMBus(self.i2c_bus_num)
        for d in array:
            bus.write_byte_data(DEVICE_ADDRESS,addr,d)
            sleep(0.010)
        bus.close()

    #open i2c bus, write 1 byte of data from address, close bus
    def __write8(self,addr,d):
        bus = smbus2.SMBus(self.i2c_bus_num)
        bus.write_byte_data(DEVICE_ADDRESS,addr,d)
        bus.close()

    #open i2c bus, read 1 byte of data to address, close bus
    def __read8(self,addr):
        bus = smbus2.SMBus(self.i2c_bus_num)
        data = bus.read_byte_data(DEVICE_ADDRESS,addr)
        bus.close()
        return data

    #return formatted string of MODE1 register values
    def __MODE1_status(self):
        output = ["MODE1 Status:\n"]
        mode_1_status = list('{0:08b}'.format(self.__read8(PCA9685_MODE1)))
        mode_1_registers = ['Restart (bit 7)', 'EXTCLK (bit 6)', 'AI (BIT 5)', 'SLEEP (BIT 4)', 'SUB1 (BIT 3)', 'SUB2 (BIT 2)', 'SUB3 (BIT 1)', 'ALLCALL (BIT 0)']
        for b in mode_1_registers:
            output.append('{0}:  {1}\n'.format(b,mode_1_status.pop(0)))
        output.append('\n')
        return ''.join(output)

    #given prescale, calculate effective refresh rate; return refresh rate (float) 
    def __calculate_refresh_rate(self,prescale):
        return 25000000.0 / 4096/(prescale + 1)
        #follows formula from table 5 of PCA9685 data sheet

    #given refresh rate, calculate prescale; return prescale (float)
    def __calculate_prescale(self,refresh_rate):
        return 25000000.0 / 4096 / refresh_rate - 1
        #follows formula from table 5 of PCA9685 data sheet

    #convert throttle required to pulse width in microseconds
    def __return_pulse_width_from_counts(self,counts):
        return (counts+1)/(self.PWM_frequency*10.0**(-6)*4096)

    #convert throttle required to pulse width in microseconds (linear interpolation)
    def __return_pulse_width_from_throttle(self,throttle):
        return (self.max_throttle_pulse_width - self.min_throttle_pulse_width)/(self.max_throttle_percentage - self.min_throttle_percentage)*(throttle - self.min_throttle_percentage) + self.min_throttle_pulse_width

    #calculate on counts by linear interpolation between min and max throttle
    def __return_on_counts(self,throttle):
        #convert throttle required to pulse width in microseconds
        pulse_width = self.__return_pulse_width_from_throttle(throttle)

        #convert pulse width required to number of counts in pwm refresh window
        counts = pulse_width*self.PWM_frequency*10**(-6)*4096 - 1
        counts = int(round(counts))

        #confirm pulse width output after rounding counts to nearest value
        pulse_width = self.__return_pulse_width_from_counts(counts)
        self.__verbose_print("Calculated on counts for {0}% throttle: {1} counts".format(throttle, counts))
        self.__verbose_print("Approximate pulse width: {0:.0f} us".format(pulse_width))
        
        return [counts, pulse_width]

    #prints debug info if 'verbose' set to True
    def __verbose_print(self,*arg):
        if(verbose):
            for a in arg:
                print a
        return None


    """
    Section for external use functions
    """

    #function to set PWM output using either throttle or counts as input
    def setPWM(self, motor_index, throttle = 0, counts = None):

        #if counts is defined, use this directly
        #otherwise, calculate counts from throttle
        if counts:
            if counts > 4095 or counts < 0:
                print 'Error: Counts input is {0}. Counts limited to 0 to 4095 inclusive.'.format(counts)
                return None
            pulse_width = self.__return_pulse_width_from_counts(counts)
        else:
            counts, pulse_width= self.__return_on_counts(throttle)

        #optional delay time until pulse width begins in binary
        #must be in 12-bit format
        on = 10 #in counts, decimal
        off = counts + on #shift off time by on delay time

        self.__verbose_print("Setting PWM {0}: {1}->{2}".format(motor_index, on, off))
        #__verbose_print("Approximate pulse width: {0} us").format(pulse_width)


        #note: Each channel has 4 byte addresses for LED_ON_L,
        #LED_ON_H, LED_OFF_L, and LED_OFF_H. Shifting from LED0_ON_L
        #by 4*num gets to LED{num}_ON_L. 16-bit on time and off time
        #are written are written to each of the 4 registers in sequence.
        #See PCA9865 documentation for more details.
        
        start_register = LED0_ON_L + 4*motor_index
        write_array = [on, on>>8, off, off>>8]

        for i in xrange(4):
            self.__write8(start_register+i, write_array[i])

    #set refresh rate of PWM driver; set self.PWM_freq (Hz) and self.window_width (microseconds)
    def setPWMfreq(self,desired_freq):

        self.__verbose_print('Attempting to set frequency to {0} Hz'.format(desired_freq))
        
        commanded_freq = self.frequency_scaling_factor*desired_freq

        self.prescale = self.__calculate_prescale(commanded_freq)
        self.__verbose_print('Exact pre-scale is {0}'.format(self.prescale))

        #round to nearest integer value
        self.prescale = int(round(self.prescale))
        self.__verbose_print('Prescale rounded to {0}'.format(self.prescale))

        #actual commanded frequency given rounded prescale value
        commanded_frequency = self.__calculate_refresh_rate(self.prescale)
        self.__verbose_print('Frequency to be commanded including correction factor and prescale rounding is {0:.2f} Hz.'.format(commanded_frequency))

        estimated_output_frequency = commanded_frequency/self.frequency_scaling_factor
        self.__verbose_print('Output frequency will be approximately {0:.2f} Hz'.format(estimated_output_frequency))

        oldmode = self.__read8(PCA9685_MODE1)
        self.__verbose_print(self.__MODE1_status())
        newmode = oldmode | 0x10 #enable sleep bit (bit 4)
        #newmode = (oldmode & 0x7F) | 0x10 #sleep
        
        self.__verbose_print("\nSetting newmode to {0:08b}. (Sleep mode)".format(newmode))
        self.__write8(PCA9685_MODE1, newmode)
        self.__verbose_print(self.__MODE1_status())

        self.__verbose_print("\nSetting PRESCALE to {0}".format(self.prescale))
        self.__write8(PCA9685_PRESCALE, self.prescale)
        self.__verbose_print("PRESCALE now set to: {0}".format(self.__read8(PCA9685_PRESCALE)))
        
        self.__verbose_print("\nReverting MODE1 to old mode: {0:08b}".format(oldmode))
        self.__write8(PCA9685_MODE1, oldmode)
        self.__verbose_print(self.__MODE1_status())
        
        sleep(0.005)

        #set MODE1 register to turn on auto increment
        self.__verbose_print('\nEnabling auto-increment. (Bit 5)')
        self.__write8(PCA9685_MODE1, oldmode | 0xa0)
        self.__verbose_print(self.__MODE1_status())

        estimated_window_width = 1/estimated_output_frequency*10**6
        self.__verbose_print("Estimated window width = 1/estimated_pwm_frequency = {0:.2f}".format(1/estimated_output_frequency*10**6))
        if estimated_window_width < self.max_throttle_percentage + 50:
            print 'WARNING! Estimated pwm window width close to or less than max throttle pulse duration.\n'
            print 'Reset PWM frequency to greater than (max throttle pulse with)^-1 to avoid issues.'

        self.PWM_frequency = estimated_output_frequency
        self.window_width = estimated_window_width

    #startup routine to enable motor controllers
    def motor_startup(self):
        #set all motor channels to neutral
        for i in xrange(self.nmotors):
            self.setPWM(i,0)

        #plug in the ESCs!!
        raw_input('Plug in the power supply. Press enter to continue...')

        #move throttle to 50%
        for i in xrange(self.nmotors):
            self.setPWM(i,50)