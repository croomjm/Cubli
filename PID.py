#!/usr/bin/env python

__author__ = "Jordan Croom"
__copyright__ = ""
__credits__ = []
__license__ = ""
__version__ = ""
__maintainer__ = "Jordan Croom"
__email__ = "croomjm@gmail.com"
__status__ = "Prototype"

from collections import defaultDict
import types

class PID:
	"""Basic PID controller class for SISO systems."""

	"""
	Algorithm is based on work by Karl Astrom and Richard Murray.
		Original Reference: Control System Design by Karl Astrom, 2002. See https://www.cds.caltech.edu/~murray/courses/cds101/fa02/caltech/astrom-ch6.pdf.

		Expanded, up-to-date reference: "Feedback Systems: An Introduction for Scientists and Engineers" by Karl Astrom and Richard Murray. Publicly available at http://www.cds.caltech.edu/~murray/amwiki/index.php/Main_Page.
	
	The PID controller is implmented with optional anti-windup and set point weighting features as described in Astrom.
	"""

	"""Capabilities to add:
	1) MIMO upgrade (implement state-space gains)
	2) Anti-windup integrator with direct measurement of output
	"""

	def __init__(self,K, Ti = None, Td = None, N = None, h = None, antiWindupDict = None, setPointWeightingDict = None):
		
		"""Initialize required values for control loop and set behavior of required helper functions."""

		"""
		Basic Controller Constants:
			Proportional gain (K) is a required input, but Ti and Td are optional. This allows the user to select 'P', 'PI', 'PD', and 'PID' controller behavior. Td and Ti should be set to None to remove the integral and derivative terms, respectively. Setting either to zero will result in divide by zero errors.

		Timesteps (h):
			If user does not input value for h (the control loop time step), h is calculated for each control loop step. If h is set, it is used as a constant for all controller calculations. In either case, a time (in seconds) is required at each time step in 'returnOutput' function.

		Anti-windup:
			Anti-windup is an optional parameter that should be passed as a dict. By default, it will not be used in the control loop, which could result in undesirable behavior at or near actuator saturation (see references). If anti-windup is desired, the class must be initialized with 'antiWindup' set to a dict with the following keys:
				Required - 'Tt':
					Time constant for anti-windup feedback loop (see {reference}). Sqrt(Ti*Td) is suggested by the rule of thumb in Astrom. Tt must be a positive int or float.

				Required - 'actuatorModel':
					'actuatorModel' is a function taking a single argument 'v', the control loop output before anti-windup integrator calculation. This function will be used to estimate the actual output of the actuator in response to v, which is used in the anti-windup calculation. 

					For example, an actuator with linear behavior and known saturation at 0 and 100 could be modeled as:
						def saturatingActuator(v):
							if v<0:
								return 0
							elif v>100:
								return 100
							else:
								return v

					Then antiWindup['actuatorModel'] = saturatingActuator

		Set-point Weighting:
			Set-point weighting is implemented as described in Astrom to avoid impulses in the control signal. By default, set-point weighting will not be used in the control loop. If set-point weighting is desired, the class must be initialized with 'setPointWeighting' set to a dictionary with the following keys:
				Required - 'b':
					'b' multiplies the reference input ('ysp', the desired set-point) in the proportional term. 'b' must be a float between 0 and 1 to function as intended. If b > 1, the proportional gain on the controller will actually push u away from the set-point. If b < 1, the proportional gain will attempt to pull u beyond the set-point. Setting b = 0 will eliminate the proportional term of the set-point weighting. The default value is 0.
		"""

		self.parameters = {
			'mode': None,
			'K': None,
			'Ti': None,
			'Td': None,

			'timing_mode': None,
			'h': None,

			'antiWindup': False,
			'Tt': None,
			#'actuatorMode': None
			'actuatorModel': None,

			'setPointWeighting': False,
			'b': 0,

			'ai': None,
			'ad': None,
			'bd': None,
			'a0': None
		}

		#initialize required system values
		self.y_old = 0
		self.t_old = 0
		self.I = 0
		self.D = 0

		#set basic parameters
		self.__setControllerMode(K,Ti,Td)
		self.__setConstant(K, 'K')

		if Ti:
			self.__setConstant(Ti, 'Ti')
		if Td:
			self.__setConstant(Td, 'Td')
			if N:
				self.__setConstant(N, 'N')
			else:
				#if no value is provided, set to 14 (midpoint between typical values of 8 to 20 as described in Astrom)
				self.__setConstant(N, 14)

		#determine timing mode and set parameters appropriately
		if h:
			self.__sethHandle('constant',h)
		else:
			self.__sethHandle('variable')

		#set anti-windup parameters
		if antiWindupDict:
			self.__setAntiWindup(antiWindupDict)

		#set setpoint weighting parameters
		if setPointWeightingDict:
			self.__setSetPointWeighting(setPointWeightingDict)

		#precompute constants for controller loop
		self.__setPrecomputedGains()

	def __setControllerMode(self,K,Ti,Td):
		portions = ['P','I', 'D']
		mode = ''.join([x for x in portions, y in [K,Ti,Td] if y!=None])
		if mode in ['', 'D', 'ID']:
			raise RuntimeError('User input of K = {0}, Ti = {1}, Td = {2} is invalid. Proportional gain (K) is required.'.format(K,Ti,Td))

	def __setConstant(self, constant, name):
		if type(constant) is not in [int,float]:
			raise TypeError('Invalid type for {0} (provided {1}, type is {2}). Type must be either int or float.'.format(name, constant, type(constant)))
		
		constant = float(constant)
		if constant<0:
			raise RuntimeError('Invalid value for {0} ({1:02f}). Negative value will cause controller to diverge.'.format(name, constant))
		else:
			self.parameters[name] = constant

	def __sethHandle(self, timing_mode, h = None):
		if timing_mode = 'variable':
			self.__returnh = lambda x: x - self.told
		elif timing_mode = 'constant':
			if type(h) is not in [int, float]:
				raise TypeError('Variable timing selected, but value of h ({0}, type: {1}) provided is not int or float type.'.format(h, type(h)))
			elif h<0:
				raise RuntimeError('Value of h provided ({0}, type: {1}) is negative. This would cause the control loop to diverge.'.format(h, type(h)))
			else:
				self.__returnh = lambda x: h
		else:
			raise RuntimeError("Timing mode '{0}' is invalid. Please select from 'constant' and 'variable.'".format(timing_mode))

	def __setAntiWindup(self, antiWindupDict):
		"""
		Sets the required anti-windup parameters in self.parameters.
		"""

		#make sure the input is correctly formatted
		if type(antiWindupDict) != dict:
			raise TypeError("PID object parameter 'antiWindup' must be passed as a dictionary. 'antiWindup' was instead passed as {0} type".format(type(antiWindupDict)))

		#set the anti-windup time constant
		if 'Tt' not in antiWindupDict:
			#self.__setConstant((self.parameters['Ti']*self.parameters['Td'])**0.5,'Tt')
			raise RuntimeError("Anti-windup dictionary does not contain required value for 'Tt'.")
		else:
			self.__setConstant(antiWindupDict['Tt'], 'Tt')

		#set the actuator model handle
		if 'actuatorModel' in antiWindupDict and type(antiWindupDict['actuatorModel']) == types.FunctionType:
			self.parameters['actuatorModel'] = antiWindupDict['actuatorModel']
		else:
			raise RuntimeError("'antiWindup' must contain the key 'actuatorModel' set as a function taking a single argument (control loop output) and returning a single value (approximate actuator output).")

		"""
		Control flow once code is updated to allow for measured actuator output feedback.


		if 'actuatorMode' in antiWindupDict:
			if antiWindupDict['actuatorMode'] == 'modeled':
				self.parameters['actuatorMode'] = 'modeled'
				if 'actuatorModel' in antiWindupDict and type(antiWindupDict['actuatorModel']) == types.FunctionType:
					self.parameters['actuatorModel'] = antiWindupDict['actuatorModel']
				else:
					raise RuntimeError("Since the 'antiWindup' dictionary passed to PID object specified the 'actuatorModel' is 'modeled', 'antiWindup' must also contain the key 'actuatorModel' set as a function taking a single argument (control loop output) and returning a single value (approximate actuator output).")
			elif antiWindupDict['actuatorMode'] == 'measured':
				self.parameters['actuatorMode'] = antiWindupDict['actuatorMode']
			else:
				raise RuntimeError("Invalid value for 'actuatorMode' ({0}). Please specify 'actuatorMode' as either 'modeled' or 'measured'.".format(antiWindupDict['actuatorMode']))
		else:
			raise RuntimeError('"actuatorMode" must be specified within "antiWindup" as either "modeled" or "measured". Provided antiWindup dictionary was {0}'.format(antiWindupDict))
		"""

		self.parameters['antiWindup'] = True

	def __setSetPointWeighting(self,setPointWeightingDict):
		if type(setPointWeightingDict) != dict:
			raise TypeError("PID object parameter 'setPointWeighting' must be passed as a dictionary. 'setPointWeighting' was instead passed as {0} type".format(type(setPointWeightingDict)))

		if 'b' not in setPointWeightingDict:
			raise RuntimeError("PID object parameter 'setPointWeighting' dictionary does not contain required value for 'b'.")
		else:
			self.__setConstant(setPointWeightingDict['b'], 'b')


		self.parameters['setPointWeighting'] = True

	def __setPrecomputedGains(self):
		mode = self.parameters['mode']

		K = self.parameters['K']
		Ti = self.parameters['Ti']
		Td = self.parameters['Td']
		Tt = self.parameters['Tt']
		b = self.parameters['b']
		c = self.parameters['c']

		if mode in ['PD', 'PID']:
			self.parameters['ad'] = lambda h: Td/(Td + N*h)
			self.parameters['bd'] = lambda h: -Td*K*N/(Td + N*h)
		if mode in ['PI', 'PID']:
			self.parameters['bi'] = lambda h: K*h/Ti

		if self.parameters['antiWindup']:
			self.parameters['a0'] = 1/Tt 

	def getParameters(self):
		return self.parameters

	def printParameters(self):
		"""Prints relevant PID object information, including constants, anti-windup mode (on or off, modeled or measured actuator), setpoint weighting mode (on or off)"""
		for i in self.parameters:
			print '{0}: {1}'.format(i, self.parameters[i])

	def returnOutput(self,ysp,measured_state):
		"""Take in commanded state and measured state. Return output."""
		t, y = measured_state
		h = self.parameters['h'](t)

		P = self.parameters['K']*(self.parameters['b']*ysp-y)
		self.D = self.parameters['ad'](h)*self.D - self.parameters['bd'](h)*(y-self.y_old)

		v = P + self.D + self.I

		if self.parameters['antiWindup']:
			u = self.parameters['actuatorModel'](v)
			self.I += self.parameters['bi'](h)*(ysp - self.y_old) + self.parameters['a0']*(u-v)
		else:
			self.I += self.parameters['bi'](h)*(ysp - self.y_old)
			u = v

		self.t_old = t
		self.y_old = y

		return u




