from collections import deque
import os

class DataLog:
    """
    Class to contain saved data and save to json file when commanded.

    All logged data are limited to self.__buffer_length unique records.
    Exclusively uses jsonpickle library to read/write log data.
    """

    def __init__(self,logDir = None, buffer_length = 5*10**4,logging = True):
        self.__buffer_length = buffer_length
        self.log = {
            '__buffer_length': self.__buffer_length, #max number of data points to save
            'counts': {
                i: deque(maxlen = self.__buffer_length) for i in ['time', 0, 1, 2]
                },
            'commanded_velocity': {
                i: deque(maxlen = self.__buffer_length) for i in ['time', 0, 1, 2]
                },
            'commanded_throttle': {
                i: deque(maxlen = self.__buffer_length) for i in ['time', 0, 1, 2]
                },
            'measured_velocity': {
                i: deque(maxlen = self.__buffer_length) for i in ['time', 0, 1, 2]
                },
            'command_latency': deque(maxlen = self.__buffer_length),
            'measurement_to_command_latency': deque(maxlen = self.__buffer_length),
            'iteration_latency': deque(maxlen = self.__buffer_length),
            'velocity_units': None,
            'PID_parameters': None
        }

        #set path for saving log file if it exists
        #otherwise, use current directory
        self.logDir = os.getcwd() + '/'
        if logDir:
            logDir = str(logDir)
            if os.path.isdir(logDir):
                self.logDir = logDir


    def saveLog(self, fileDir = None, fileName = None, baseName = None):
        """
        Save all log information to file.

        If filePath is provided, file is written to this directory (if it exists). Otherwise, the file path created in __init__ is used.

        If fileName is provided, file is written with this file name. Otherwise, a file name is generated based on the file in which DataLog instance is created. This fileName will override a baseName if provided.

        If baseName is provided, use this to construct the file name automatically.
        """

        import jsonpickle
        jsonpickle.set_encoder_options('simplejson', sort_keys=True, indent=4)
        jsonpickle.set_preferred_backend('simplejson')

        if fileDir:
            fileDir = str(fileDir)
            if not os.path.isdir(fileDir):
                raise RuntimeError('Provided filePath is not an existing directory. Aborting saveLog method.')
                return
        else:
            fileDir = self.logDir

        if fileName:
            fileName = fileDir + str(fileName) + '.json'
        else:
            from datetime import datetime
            
            if baseName:
                baseName = str(baseName)
            else:
                #use file name of this class
                baseName = os.path.basename(__file__).split('.')[0]

            fileName = fileDir + baseName + '_' + str(datetime.now()) + '.json'

        try:
            with open(fileName, 'w') as f:
                f.write(jsonpickle.encode(self.log, keys = True))
            print 'Log file successfully saved as {0}'.format(fileName)
        except:
            print 'Error saving log file.'

    def updateLog(self, kwDict):
        for input_key in kwDict:
            if isinstance(self.log[input_key],deque):
                self.log[input_key].append(kwDict[input_key])
            elif type(self.log[input_key]) is dict:
                for i,key in enumerate(self.log[input_key]):
                        self.log[input_key][key].append(kwDict[input_key][i]) 
            else:
                self.log[input_key] = kwDict[input_key]
                #raise TypeError("Function 'updateLog' received input in 'kwDict' that was neither dictType or an instance of deque.")

    def openLog(self, filePath):
        import jsonpickle
        jsonpickle.set_encoder_options('simplejson', sort_keys=True, indent=4)
        jsonpickle.set_preferred_backend('simplejson')

        filePath = str(filePath)

        with open(filePath, 'r') as f:
                obj = jsonpickle.decode(f.read(), keys = True)
        return obj

        # try:
        #     with open(filePath, 'r') as f:
        #         obj = jsonpickle.decode(f.read(), backend = 'simplejson', keys = True)
        #     return obj
        # except:
        #     raise RuntimeError('Unable to open and decode json file at {0}'.format(filePath))
