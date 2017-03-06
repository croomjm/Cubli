import Motors
import math
import time

i2c_bus_num = 1
nmotors = 3
min_throttle_percentage = -100
max_throttle_percentage = 100
min_throttle_pulse_width = 1100 #in microseconds
max_throttle_pulse_width = 1940 #in microseconds
PWM_frequency = 500 #in Hz

#instantiate motor group object
motors = Motors.Motors(i2c_bus_num,nmotors,min_throttle_percentage, max_throttle_percentage, min_throttle_pulse_width, max_throttle_pulse_width)

def wave(amp, phi, f, t):
    return amp*math.sin(f*t + phi)

if __name__ == "__main__":
    try:
        motors.setPWMfreq(PWM_frequency)
        print 'PWM frequency before setting PWM: {0:.02f} Hz'.format(motors.PWM_frequency)

        motors.motor_startup()

        #drive motors in wave
        pi = 3.14159
        freq = 1.0 #wave frequency in radians/s
        while True:
            for pwmNum in xrange(nmotors):
                print 'PWM Num = {0}'.format(pwmNum)
                motors.setPWM(pwmNum,wave(100, 2*pi/nmotors*pwmNum, freq, time.time()))
    except KeyboardInterrupt:
        print "Interrupt Detected"
        for i in xrange(nmotors):
            motors.setPWM(i,0)
