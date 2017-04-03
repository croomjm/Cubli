import Encoders, Motors, PID, DataLog

import numpy, time
from math import pi, sin
from datetime import datetime
from collections import deque
from os import path

#counts per revolution from encoder
countsPerRevolution = 1024.0

#motor operation parameters
i2c_bus_num = 1
nmotors = 3
min_throttle_percentage = -100
max_throttle_percentage = 100
min_throttle_pulse_width = 1100 #in microseconds
max_throttle_pulse_width = 1940 #in microseconds
deadband = 20 #pulse width in microseconds
throttle_deadband = 100*20/(1940-1100)/2.0
PWM_frequency = 500 #in Hz
kV = 300
supplyVoltage = 12

def actuatorVelocityModel(throttle):
    if throttle>100:
        return kV*supplyVoltage
    if throttle<-100:
        return -1*kV*supplyVoltage
    if throttle<throttle_deadband and throttle>-throttle_deadband:
        return 0
    return throttle/100.0*kV*12

def wave(amp, phi, f, t):
    return amp*sin(f*t + phi)

def main():
    try:
        dataLog = DataLog.DataLog(logDir = 'logs/')
        encoders = Encoders.Encoders(countsPerRevolution = countsPerRevolution, units = 'Hz')
        motors = Motors.Motors(i2c_bus_num,nmotors,min_throttle_percentage, max_throttle_percentage, min_throttle_pulse_width, max_throttle_pulse_width)
        
        #start motor communication
        motors.setPWMfreq(PWM_frequency)
        motors.motor_startup()
        for i in xrange(3):
            motors.setPWM(i, 0)
        
        freq = 1/5.0    
        while True:
            #get measured velocity array
            #calculate commanded velocities array
            #convert commanded velocities to throttle
            #send commanded PWM signal to motors
            loop_start_time = time.time()
            count_array = encoders.returnCountArray()
            measured_velocities = encoders.getVelocities()
            command_time = time.time()
            commanded_throttles = [command_time] + [wave(100,2*pi/nmotors*pwmNum, freq, command_time) for pwmNum in xrange(nmotors)]
            for pwmNum, throttle in enumerate(commanded_throttles):
                motors.setPWM(pwmNum,throttle)
            loop_end_time = time.time()

            #write information to logs
            log_info = {
                'counts': count_array,
                'commanded_velocity': [command_time] + map(actuatorVelocityModel, commanded_throttles[1:]),
                'commanded_throttle': commanded_throttles,
                'measured_velocity': measured_velocities,
                'iteration_latency': loop_end_time - loop_start_time,
                'command_latency': loop_end_time - command_time,
                'measurement_to_command_latency': command_time - measured_velocities[0]
                }
            dataLog.updateLog(log_info)

    except KeyboardInterrupt:
        dataLog.saveLog(baseName = 'Closed_Loop_Test')

if __name__ == '__main__':
    main()