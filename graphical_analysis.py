import DataLog, sys, numpy, matplotlib
matplotlib.use('GTKAgg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

dataLog = DataLog.DataLog()
fileName = str(sys.argv[1])

data = dataLog.openLog(fileName)

"""
graphs:
1) Velocities:
	commanded velocity and measured velocity versus time
	legend with PID gains
2) Latency:
	measurement latency vs. time
	iteration latency vs. time
	command latency vs. time
3) Torque versus Time
	dv/dt*J
4) Counts versus Time
"""

velocity_units = data['velocity_units']
vel_command = data['commanded_velocity']
vel_meas = data['measured_velocity']
comm_latency = data['command_latency']
meas2comm_latency = data['measurement_to_command_latency']
iter_latency = data['iteration_latency']
counts = data['counts']

#commanded velocities and measured velocities vs time
for i in xrange(3):
	plt.subplot(int('31'+str(i+1)))

	#plot commanded velocities
	plt.plot(vel_command['time'], vel_command[i],'b-', label =  'Commanded')

	#plot measured velocities
	plt.plot(vel_meas['time'], vel_meas[i], 'g-', label =  'Measured')

	plt.title('Encoder {0}'.format(i))
	plt.ylabel('Velocity ({0})'.format(velocity_units))
	plt.legend()
plt.xlabel('Timestamp (s)')
plt.suptitle('Encoder Velocity ({0}) vs Time'.format(velocity_units))

#plot loop latencies
plt.figure()
plt.plot(comm_latency, label = 'Command Latency')
plt.plot(meas2comm_latency, label = 'Measurement to Command Latency')
plt.plot(iter_latency,label = 'Iteration Latency')
plt.title('Loop Latencies')
plt.ylabel('Latency (s)')
plt.xlabel('Sample')
plt.legend()

#plot counts for each axis
plt.figure()
lines = []
for i in xrange(3):
	plt.plot(counts['time'], counts[i], label = 'Encoder {0} Counts'.format(i))
plt.title('Counts vs Time')
plt.legend()
plt.xlabel('Timestamp (s)')
plt.ylabel('Counts')

plt.show()


