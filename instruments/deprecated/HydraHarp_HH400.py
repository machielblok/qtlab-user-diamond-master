from ctypes import *
import os
from instrument import Instrument
import pickle
from time import sleep, time
import types
import logging
import numpy
import qt
from qt import *
from numpy import *

LIB_VERSION = "1.2"
MAXDEVNUM	  = 8		      # max num of USB devices
HHMAXCHAN   = 8		      # max num of logical channels
MAXBINSTEPS	= 12	      # get actual number via HH_GetBaseResolution) !
MAXHISTLEN  = 65536	    # max number of histogram bins
MAXLENCODE  = 6	    	  # max length code histo mode
MAXHISTLEN_CONT	= 8192	# max number of histogram bins in continuous mode
MAXLENCODE_CONT	= 3	  	# max length code in continuous mode
TTREADMAX   = 131072    # 128K event records can be read in one chunk
MODE_HIST                   = 0
MODE_T2                     = 2
MODE_T3                     = 3
MODE_CONT                   = 8
MEASCTRL_SINGLESHOT_CTC     = 0 # default
MEASCTRL_C1_GATE		        = 1
MEASCTRL_C1_START_CTC_STOP  = 2
MEASCTRL_C1_START_C2_STOP   = 3

#continuous mode only
MEASCTRL_CONT_EXTTRIG       = 5
MESACTRL_CONT_CTCTRIG       = 6

EDGE_RISING                 = 1
EDGE_FALLING                = 0

FLAG_OVERFLOW               = 0x0001  #histo mode only
FLAG_FIFOFULL               = 0x0002  
FLAG_SYNC_LOST              = 0x0004  
FLAG_REF_LOST               = 0x0008  
FLAG_SYSERROR               = 0x0010  #hardware error, must contact support

SYNCDIVMIN                  = 1
SYNCDIVMAX                  = 16

ZCMIN                       = 0			      # mV
ZCMAX                       = 40			    # mV 
DISCRMIN                    = 0			      # mV
DISCRMAX                    = 1000		    # mV 

CHANOFFSMIN                 = -99999	    # ps
CHANOFFSMAX                 = 99999		    # ps

OFFSETMIN                   =	0			      # ps
OFFSETMAX                   =	500000      # ps 
ACQTMIN	                    = 1			      # ms
ACQTMAX	                    =	360000000	  # ms  (100*60*60*1000ms = 100h)

STOPCNTMIN                  = 1
STOPCNTMAX                  = 4294967295  # 32 bit is mem max

#The following are bitmasks for return values from GetWarnings()

WARNING_SYNC_RATE_ZERO      = 0x0001
WARNING_SYNC_RATE_TOO_LOW   = 0x0002
WARNING_SYNC_RATE_TOO_HIGH  = 0x0004

WARNING_INPT_RATE_ZERO      = 0x0010
WARNING_INPT_RATE_TOO_HIGH  = 0x0040

WARNING_INPT_RATE_RATIO     = 0x0100
WARNING_DIVIDER_GREATER_ONE = 0x0200
WARNING_TIME_SPAN_TOO_SMALL = 0x0400
WARNING_OFFSET_UNNECESSARY  = 0x0800

class HydraHarp_HH400(Instrument): #1
    '''
    This is the driver for the HydraHarp HH400 Time Correlated Single Photon Counting module

    Usage:
    Initialize with
    <name> = qt.instruments.create('name', 'HydraHarp_PH400')
    
    status:
     1) create this driver!=> is never finished
    TODO:
    '''
    def __init__(self, name, DeviceIndex = 0): #2
        # Initialize wrapper
        logging.info(__name__ + ' : Initializing instrument HH400')
        Instrument.__init__(self, name, tags=['physical'])

        # Load dll and open connection
        self._load_dll()
        sleep(0.01)

        LibraryVersion = numpy.array([8*' '])
        self._HH400_win32.HH_GetLibraryVersion(LibraryVersion.ctypes.data)
        self.LibraryVersion = LibraryVersion
        if LibraryVersion[0][0:3] != '1.2':
            logging.warning(__name__ + ' : DLL Library supposed to be ver. 1.2, but found ' + LibraryVersion[0] + 'instead.')
#        print ('HydraHarp DLL version %s loaded...'%str(LibraryVersion))

        self.add_parameter('Range', flags = Instrument.FLAG_SET, type=types.IntType)
        self.add_parameter('Offset', flags = Instrument.FLAG_SET, type=types.IntType,
                           minval=OFFSETMIN, maxval=OFFSETMAX)
        self.add_parameter('SyncDiv', flags = Instrument.FLAG_SET, type=types.IntType,
                           minval=SYNCDIVMIN, maxval=SYNCDIVMAX)
        self.add_parameter('ResolutionPS', flags = Instrument.FLAG_GET, type=types.FloatType)
        self.add_parameter('BaseResolutionPS', flags = Instrument.FLAG_GET, type=types.FloatType)
        self.add_parameter('MaxBinSteps', flags = Instrument.FLAG_GET, type=types.IntType)
        self.add_parameter('SyncCFDLevel', flags = Instrument.FLAG_SET, type=types.IntType,
                           minval=DISCRMIN, maxval=DISCRMAX)
        self.add_parameter('SyncCFDZeroCross', flags = Instrument.FLAG_SET, type=types.IntType,
                           minval=ZCMIN, maxval=ZCMAX)
        self.add_parameter('SyncChannelOffset', flags = Instrument.FLAG_SET, type=types.IntType,
                           minval=CHANOFFSMIN, maxval=CHANOFFSMAX)
        self.add_parameter('InputCFDLevel', flags = Instrument.FLAG_SET, type=types.IntType,
                           minval=DISCRMIN, maxval=DISCRMAX)
        self.add_parameter('InputCFDZeroCross', flags = Instrument.FLAG_SET, type=types.IntType,
                           minval=ZCMIN, maxval=ZCMAX)
        self.add_parameter('InputChannelOffset', flags = Instrument.FLAG_SET, type=types.IntType,
                           minval=CHANOFFSMIN, maxval=CHANOFFSMAX)
        self.add_parameter('HistoLen', flags = Instrument.FLAG_SET, type=types.IntType,
                           minval=0, maxval=MAXLENCODE)
        self.add_parameter('CFDLevel0', flags = Instrument.FLAG_SET, type=types.IntType)
        self.add_parameter('CFDLevel1', flags = Instrument.FLAG_SET, type=types.IntType)
        self.add_parameter('CFDZeroCross0', flags = Instrument.FLAG_SET, type=types.IntType)
        self.add_parameter('CFDZeroCross1', flags = Instrument.FLAG_SET, type=types.IntType)
        self.add_parameter('CountRate0', flags = Instrument.FLAG_GET, type=types.IntType)
        self.add_parameter('CountRate1', flags = Instrument.FLAG_GET, type=types.IntType)
        self.add_parameter('ElapsedMeasTimePS', flags = Instrument.FLAG_GET, type=types.FloatType)
        self.add_parameter('DeviceIndex', flags = Instrument.FLAG_SET, type=types.IntType)
        self.add_parameter('ExternalRefClock', flags = Instrument.FLAG_SET, type=types.BooleanType)
        self.add_parameter('MeasRunning', flags = Instrument.FLAG_GET, type=types.BooleanType)
        self.add_parameter('Flags', flags = Instrument.FLAG_GET, type=types.IntType)
        self.add_parameter('Flag_Overflow', flags = Instrument.FLAG_GET, type=types.BooleanType)
        self.add_parameter('Flag_FifoFull', flags = Instrument.FLAG_GET, type=types.BooleanType)
        self.add_parameter('Flag_RefLost', flags = Instrument.FLAG_GET, type=types.BooleanType)
        self.add_parameter('Flag_SyncLost', flags = Instrument.FLAG_GET, type=types.BooleanType)
        self.add_parameter('Flag_SystemError', flags = Instrument.FLAG_GET, type=types.BooleanType)
        self.add_parameter('NumOfInputChannels', flags = Instrument.FLAG_GET, type=types.IntType)
        self.add_parameter('NumOfModules', flags = Instrument.FLAG_GET, type=types.IntType)
        self.add_parameter('ModuleInfo', flags = Instrument.FLAG_GET, type=types.IntType)
        self.add_parameter('ModuleIndex', flags = Instrument.FLAG_GETSET, type=types.IntType)
        self.add_parameter('Channel', flags = Instrument.FLAG_SET, type=types.IntType)
        self.add_parameter('Binning', flags = Instrument.FLAG_SET, type=types.IntType,
                           minval=0, maxval=MAXBINSTEPS-1)
        self.add_function('start_histogram_mode')
        self.add_function('start_T2_mode')
        self.add_function('start_T3_mode')
        self.add_function('calibrate')
        self.add_function('ClearHistMem')
        self.add_function('StartMeas')
        self.add_function('StopMeas')
        self.add_function('OpenDevice')
        self.add_function('CloseDevice')

        self._do_set_DeviceIndex(DeviceIndex)
        self.OpenDevice()
        
        self.set_ExternalRefClock(False)
        self.start_histogram_mode()

        self.Model = numpy.array([16*' '])
        self.PartNo = numpy.array([8*' '])
        self.SerialNo = numpy.array([8*' '])
        
        success = self._HH400_win32.HH_GetHardwareInfo(self.DevIdx, 
            self.Model.ctypes.data, self.PartNo.ctypes.data)
        if success != 0:
            logging.warning(__name__ + ' : error getting hardware info')
            self.get_ErrorString(success)
 #       print ('HydraHarp model %s'%self.Model)            
 #       print ('HydraHarp part no. %s'%self.PartNo)            
        success = self._HH400_win32.HH_GetSerialNumber(self.DevIdx, 
            self.SerialNo.ctypes.data)
        if success != 0:
            logging.warning(__name__ + ' : error getting serial number')
            self.get_ErrorString(success)
 #       print ('HydraHarp serial no. %s'%self.SerialNo)            

        self.calibrate()
        self._do_get_NumOfModules()
        self._do_get_NumOfInputChannels()
        self._do_set_ModuleIndex(0)
        
        self._do_set_SyncCFDLevel(200)
        self._do_set_SyncCFDZeroCross(10)
        self._do_set_SyncChannelOffset(0)

        self._do_set_Channel(0)
        self._do_set_InputCFDLevel(200)
        self._do_set_InputCFDZeroCross(10)
        self._do_set_InputChannelOffset(0)
        
        self._do_set_Channel(1)
        self._do_set_InputCFDLevel(200)
        self._do_set_InputCFDZeroCross(10)
        self._do_set_InputChannelOffset(0)
       
        self._do_set_SyncDiv(1)
        self._do_set_Binning(8)
        self._do_set_HistoLen(MAXLENCODE)
        self._do_set_Offset(0)
        self.set_StopOverflow(0,STOPCNTMAX)
        self._do_get_BaseResolutionPS()
        self._do_get_MaxBinSteps()
        self._do_get_ResolutionPS()

    def _load_dll(self): #3
#        print __name__ +' : Loading HHLib.dll'
        WINDIR=os.environ['WINDIR']
        self._HH400_win32 = windll.LoadLibrary(WINDIR+'\\System32\\HHLib')
        sleep(0.02)

    def _do_set_ExternalRefClock(self,val):
        self._ExternalRefClock = val
        if val == True:
            self.RefClock = 1
        else:
            self.RefClock = 0

    def _do_set_DeviceIndex(self,val):
        self.DevIdx = val

    def _do_set_ModuleIndex(self,val):
	if val < self.NumOfModules:
            self.ModIdx = val
        else:
            print('Error: Module Index out of range')


    def _do_set_Channel(self,val):
	if val < self.NumOfInputChannels:
            self.Channel = val
        else:
            print('Error: Channel Index out of range')

    def calibrate(self):
        success = self._HH400_win32.HH_Calibrate(self.DevIdx)
        if success != 0:
            logging.warning(__name__ + ' : calibration error')
            self.get_ErrorString(success)

    def start_histogram_mode(self):
        success = self._HH400_win32.HH_Initialize(self.DevIdx, MODE_HIST, self.RefClock)
        if success != 0:
            logging.warning(__name__ + ' : Histogramming mode could not be started')
            self.get_ErrorString(success)

    def start_T2_mode(self):
        success = self._HH400_win32.HH_Initialize(self.DevIdx, MODE_T2, self.RefClock)
        if success != 0:
            logging.warning(__name__ + ' : T2 mode could not be started')
            self.get_ErrorString(success)

    def start_T3_mode(self):
        success = self._HH400_win32.HH_Initialize(self.DevIdx, MODE_T3, self.RefClock)
        if success != 0:
            logging.warning(__name__ + ' : T3 mode could not be started')
            self.get_ErrorString(success)

    def _do_get_NumOfInputChannels(self):
        nchannels = c_int(0)
        success = self._HH400_win32.HH_GetNumOfInputChannels(self.DevIdx, byref(nchannels))
        if success < 0:
            logging.warning(__name__ + ' : error in HH_GetNomOfInputChannels')
            self.get_ErrorString(success)
        self.NumOfInputChannels = int(nchannels.value)
        return self.NumOfInputChannels

    def _do_get_NumOfModules(self):
        nummod = c_int(0)
        success = self._HH400_win32.HH_GetNumOfModules(self.DevIdx, byref(nummod))
        if success < 0:
            logging.warning(__name__ + ' : error in HH_GetNumOfModules')
            self.get_ErrorString(success)
        self.NumOfModules = int(nummod.value)
        return self.NumOfModules

    def _do_get_ModuleInfo(self):
        modelcode = c_int(0)
        versioncode = c_int(0)
        success = self._HH400_win32.HH_GetModuleInfo(self.DevIdx, self.ModIdx, byref(modelcode), byref(versioncode))
        if success < 0:
            logging.warning(__name__ + ' : error in HH_GetModuleInfo')
            self.get_ErrorString(success)
        self.ModelCode = modelcode.value
        self.VersionCode = versioncode.value
        return self.ModelCode

    def _do_get_ModuleIndex(self):
        modidx = c_int(0)
        success = self._HH400_win32.HH_GetModuleIndex(self.DevIdx, self.Channel, byref(modidx))
        if success < 0:
            logging.warning(__name__ + ' : error in HH_GetModuleIndex')
            self.get_ErrorString(success)
        self.ModIdx = modidx.value
        return self.ModIdx
        
    def _do_get_MaxBinSteps(self):
        resolution = c_double(0)
        binsteps = c_int(0)
        success = self._HH400_win32.HH_GetBaseResolution(self.DevIdx, byref(resolution), byref(binsteps))
        if success < 0:
            logging.warning(__name__ + ' : error in HH_GetBaseResolution')
            self.get_ErrorString(success)
        self.MaxBinSteps = binsteps.value
        self.BaseResolutionPS = resolution.value
        return self.MaxBinSteps

    def _do_get_BaseResolutionPS(self):
        resolution = c_double(0)
        binsteps = c_int(0)
        success = self._HH400_win32.HH_GetBaseResolution(self.DevIdx, byref(resolution), byref(binsteps))
        if success < 0:
            logging.warning(__name__ + ' : error in HH_GetBaseResolution')
            self.get_ErrorString(success)
        self.BaseResolution = binsteps.value
        self.BaseResolutionPS = resolution.value
        return self.BaseResolutionPS

    def _do_get_ResolutionPS(self):
        resolution = c_double(0)
        success = self._HH400_win32.HH_GetResolution(self.DevIdx,byref(resolution))
        if success < 0:
            logging.warning(__name__ + ' : error in HH_GetResolution')
            self.get_ErrorString(success)
        self.ResolutionPS = resolution.value
        return self.ResolutionPS

    def get_CountRate(self):
        cntrate = c_int(0)
        success = self._HH400_win32.HH_GetCountRate(self.DevIdx, self.Channel, byref(cntrate))
        if success < 0:
            logging.warning(__name__ + ' : error in HH_GetCountRate')
            self.get_ErrorString(success)
        return cntrate.value

    def get_SyncRate(self):
        syncrate = c_int(0)
        success = self._HH400_win32.HH_GetSyncRate(self.DevIdx, byref(syncrate))
        if success < 0:
            logging.warning(__name__ + ' : error in HH_GetSyncRate')
            self.get_ErrorString(success)
        return syncrate.value

    def _do_get_CountRate0(self):
        temp = self.Channel
        self.Channel = 0
        CountRate = self.get_CountRate()
        self.Channel = temp
        return CountRate

    def _do_get_CountRate1(self):
        temp = self.Channel
        self.Channel = 1
        CountRate = self.get_CountRate()
        self.Channel = temp
        return CountRate

    def _do_set_CFDLevel0(self, value):
        temp = self.Channel
        self.Channel = 0
        self.set_InputCFDLevel(value)
        self.Channel = temp

    def _do_set_CFDLevel1(self, value):
        temp = self.Channel
        self.Channel = 1
        self.set_InputCFDLevel(value)
        self.Channel = temp

    def set_CFDLevel(self, value):
        self._do_set_SyncCFDLevel(value)
        self._do_set_CFDLevel0(value)
        self._do_set_CFDLevel1(value)

    def _do_set_InputCFDLevel(self, value):
        success = self._HH400_win32.HH_SetInputCFDLevel(self.DevIdx, self.Channel, value)
        if success < 0:
            logging.warning(__name__ + ' : error in HH_SetInputCFDLevel')
            self.get_ErrorString(success)

    def _do_set_SyncCFDLevel(self, value):
        success = self._HH400_win32.HH_SetSyncCFDLevel(self.DevIdx, value)
        if success < 0:
            logging.warning(__name__ + ' : error in HH_SetSyncCFDLevel')
            self.get_ErrorString(success)

    def _do_set_CFDZeroCross0(self, value):
        temp = self.Channel
        self.Channel = 0
        self._do_set_InputCFDZeroCross(value)
        self.Channel = temp

    def _do_set_CFDZeroCross1(self, value):
        temp = self.Channel
        self.Channel = 1
        self._do_set_InputCFDZeroCross(value)
        self.Channel = temp

    def _do_set_CFDZeroCross(self, value):
        self._do_set_SyncCFDZeroCross(value)
        self._do_set_CFDZeroCross0(value)
        self._do_set_CFDZeroCross1(value)

    def _do_set_InputCFDZeroCross(self, value):
        success = self._HH400_win32.HH_SetInputCFDZeroCross(self.DevIdx, self.Channel, value)
        if success < 0:
            logging.warning(__name__ + ' : error in HH_SetInputCFDZeroCross')
            self.get_ErrorString(success)

    def _do_set_SyncCFDZeroCross(self, value):
        success = self._HH400_win32.HH_SetSyncCFDZeroCross(self.DevIdx, value)
        if success < 0:
            logging.warning(__name__ + ' : error in HH_SetSyncCFDZeroCross')
            self.get_ErrorString(success)

    def _do_set_InputChannelOffset(self, value):
        success = self._HH400_win32.HH_SetInputChannelOffset(self.DevIdx, self.Channel, value)
        if success < 0:
            logging.warning(__name__ + ' : error in HH_SetInputChannelOffset')
            self.get_ErrorString(success)

    def _do_set_SyncChannelOffset(self, value):
        success = self._HH400_win32.HH_SetSyncChannelOffset(self.DevIdx, value)
        if success < 0:
            logging.warning(__name__ + ' : error in HH_SetSyncChannelOffset')
            self.get_ErrorString(success)

    def _do_set_SyncDiv(self, div):
        success = self._HH400_win32.HH_SetSyncDiv(self.DevIdx, div)
        if success < 0:
            logging.warning(__name__ + ' : error in HH_SetSyncDiv')
            self.get_ErrorString(success)

    def set_StopOverflow(self, stop_ovfl, stopcount):
        if (stopcount < STOPCNTMIN) | (stopcount > STOPCNTMAX):
            logging.warning(__name__ + ' : error in HH_SetStopOverflow: stopcount out of range')
        else:         
            success = self._HH400_win32.HH_SetStopOverflow(self.DevIdx, stop_ovfl, stopcount)
            if success < 0:
                logging.warning(__name__ + ' : error in HH_SetStopOverflow')
                self.get_ErrorString(success)

    def _do_set_Binning(self, value):
        success = self._HH400_win32.HH_SetBinning(self.DevIdx, value)
        if success < 0:
            logging.warning(__name__ + ' : error in HH_SetBinning')
            self.get_ErrorString(success)

    def _do_set_Offset(self, offset):
        success = self._HH400_win32.HH_SetOffset(self.DevIdx, offset)
        if success < 0:
            logging.warning(__name__ + ' : error in HH_SetOffset')
            self.get_ErrorString(success)

    def _do_set_Range(self, binsize):  # binsize in 2^n times base resolution (4ps)
        self.set_Binning(binsize+2)

    def _do_set_HistoLen(self, lencode):
        actuallen = c_int(0)
        success = self._HH400_win32.HH_SetHistoLen(self.DevIdx, lencode, byref(actuallen))
        if success < 0:
            logging.warning(__name__ + ' : error in HH_SetHistoLen')
            self.get_ErrorString(success)
	actuallen = int(actuallen.value)
        self.HistogramLength = actuallen

    def ClearHistMem(self):
        success = self._HH400_win32.HH_ClearHistMem(self.DevIdx)
        if success < 0:
            logging.warning(__name__ + ' : error in HH_ClearHistMem')
            self.get_ErrorString(success)

    def StartMeas(self,tacq):
        if (tacq < ACQTMIN) | (tacq > ACQTMAX):
            logging.warning(__name__ + ' : error in HH_StartMeas: acquisition time out of range')
        else:         
            success = self._HH400_win32.HH_StartMeas(self.DevIdx, tacq)
            if success < 0:
                logging.warning(__name__ + ' : error in HH_StartMeas')
                self.get_ErrorString(success)

    def StopMeas(self):
        success = self._HH400_win32.HH_StopMeas(self.DevIdx)
        if success < 0:
            logging.warning(__name__ + ' : error in HH_StopMeas')
            self.get_ErrorString(success)

    def OpenDevice(self):
        SerialNr = numpy.array([8*' '])
#        print ('Opening HydraHarp Device no. %s'%self.DevIdx)            
        success = self._HH400_win32.HH_OpenDevice(self.DevIdx, SerialNr.ctypes.data)
        self.SerialNr = SerialNr
#        print ('HydraHarp serial no. %s'%self.SerialNr)            
        if success != 0:
            logging.warning(__name__ + ' : OpenDevice failed, check that HydraHarp software is not running.')
            self.get_ErrorString(success)

    def CloseDevice(self):
        success = self._HH400_win32.HH_CloseDevice(self.DevIdx)
        if success < 0:
            logging.warning(__name__ + ' : error in HH_CloseDevice')
            self.get_ErrorString(success)

    def _do_get_MeasRunning(self):
        running = c_int(0)
        success = self._HH400_win32.HH_CTCStatus(self.DevIdx, byref(running))
        if success < 0:
            logging.warning(__name__ + ' : error in HH_CTCStatus')
            self.get_ErrorString(success)
        return (running.value == 0)

    def _do_get_Flags(self):
        Flags = c_int(0)
        success = self._HH400_win32.HH_GetFlags(self.DevIdx, byref(Flags))
        print success
        if success < 0:
            logging.warning(__name__ + ' : error in HH_GetFlags')
            self.get_ErrorString(success)
        return Flags.value
        
    def _do_get_Flag_Overflow(self):
        return self._do_get_Flags() & FLAG_OVERFLOW == FLAG_OVERFLOW
        
    def _do_get_Flag_FifoFull(self):
        return self._do_get_Flags() & FLAG_FIFOFULL == FLAG_FIFOFULL
        
    def _do_get_Flag_SyncLost(self):
        return self._do_get_Flags() & FLAG_SYNC_LOST == FLAG_SYNC_LOST
        
    def _do_get_Flag_RefLost(self):
        return self._do_get_Flags() & FLAG_REF_LOST == FLAG_REF_LOST
        
    def _do_get_Flag_SystemError(self):
        return self._do_get_Flags() & FLAG_SYSERROR == FLAG_SYSERROR
        
    def _do_get_ElapsedMeasTimePS(self):
        elapsed = c_double(0)
        success = self._HH400_win32.HH_GetElapsedMeasTime(self.DevIdx, byref(elapsed))
        if success < 0:
            logging.warning(__name__ + ' : error in HH_GetElapsedMeasTime')
            self.get_ErrorString(success)
        return elapsed.value

    def get_Histogram(self, channel, clear=0):
        data = numpy.array(numpy.zeros(self.HistogramLength), dtype = numpy.uint32)
        success = self._HH400_win32.HH_GetHistogram(self.DevIdx,data.ctypes.data,channel,clear)
        if success < 0:
            logging.warning(__name__ + ' : error in HH_GetHistogram')
            self.get_ErrorString(success)
        return data
   
    def get_T3_pulsed_g2_Histogram(self, hist_length, channel0_delay = 0, channel1_delay = 0):   # in bins
        histogram = zeros(hist_length, dtype = int)
        while self._do_get_MeasRunning:
            length, data = self.get_TTTR_Data()
            for i in arange(0, length):
                nsync   = data[i] & (2**10 - 1)
                time    = (data[i] / 2**10) & (2**15 - 1)
                channel = (data[i] / 2**25) & (2**6 - 1)
                special = data[i] / 2**31

                if special == 1:
                    if channel == 63:
                        nsync_overflow += 1
                    else:
                        marker = channel & 15
                else:
                    if channel == 0:
                        if time >= channel0_delay:
                            channel0_time = time
                            channel0_sync = n_sync
                    if channel == 1:
                        if time >= channel1_delay:
                            channel1_time = time
                            channel1_sync = n_sync
                if channel0_sync == channel1_sync:
                    dt = channel1_time - channel0_time + hist_length/2
                    if 0 <= dt < hist_length:
                        histogram[dt] += 1
        return histogram
   
    def get_T3_pulsed_g2_2DHistogram(self, binsize_sync, range_sync, binsize_g2, range_g2, sync_period = 100, blocksize = TTREADMAX):   # in bins, period in ns
        if .001*2**binsize_g2 * 2**15 < sync_period:
            print('Warning: resolution is too high to cover entire sync period in T3 mode, events might get lost.')
        histogram = zeros((range_sync,range_g2), dtype = int)
        mode = 2    # mode = 0, if a start was received on channel 0, 
        #        1, if start on 1 
        #        2, if no start was detected, or after a stop was detected as well
        dt = -1     # dt = t_stop - t_start, if stop and start were detected (in bins set by binsize_g2)
        # dt = -1, otherwise
        nsync_overflow=0
        while self._do_get_MeasRunning() == True:
            length, data = self.get_TTTR_Data(blocksize)
            for i in arange(0, length):
                nsync   = data[i] & (2**10 - 1)
                time    = (data[i] / 2**10) & (2**15 - 1)
                channel = (data[i] / 2**25) & (2**6 - 1)
                special = data[i] / 2**31

                if special == 1:
                    if channel == 63:
                        nsync_overflow += 2**10
                    else:
                        marker = channel & 15
                else:
                    if channel == 0:
                        if mode != 1:
                            start = time
                            start_sync = nsync
                            nsync_overflow = 0
                            mode = 0
                        else:
                            stop = time
                            stop_sync = nsync
                            dt = stop - start + (stop_sync + nsync_overflow - start_sync)*int(sync_period/0.001/(2**binsize_g2))
                            dt = dt / 2**binsize_g2
                            mode = 2
                            
                    if channel == 1:
                        if mode != 0:
                            start = time
                            start_sync = nsync
                            nsync_overflow = 0
                            mode = 1
                        else:
                            stop = time
                            stop_sync = nsync
                            dt = stop - start + (stop_sync + nsync_overflow - start_sync)*int(sync_period/0.001/(2**binsize_g2))
                            dt = dt / 2**binsize_g2
                            mode = 2
    
                if (dt >= 0) and (dt < range_g2/2) and (start / 2**binsize_sync < range_sync):
                    if channel == 1:
                        dt = range_g2/2 + dt
                    else:
                        dt = range_g2/2 - dt
                    histogram[start/2**binsize_sync,dt] += 1
                    dt = -1
        return histogram
   
    def get_Block(self):
        return self.get_Histogram(0,0)

    def get_Warnings(self):
        result = self._HH400_win32.HH_GetWarnings(self.DevIdx)
        if result < 0:
            logging.warning(__name__ + ' : error in HH_GetWarnings')
            self.get_ErrorString(result)
        return result

    def get_WarningsText(self, warnings):
        WarningsText = numpy.array([16384*' '])
        if self._HH400_win32.HH_GetWarningsText(self.DevIdx, 
            WarningsText.ctypes.data, warnings) != 0:
            logging.warning(__name__ + ' : error in HH_GetWarningsText')
        return WarningsText
            
    def get_TTTR_Data(self,count = TTREADMAX):
        data = numpy.array(numpy.zeros(TTREADMAX), dtype = numpy.uint32)
        length = c_int(0)
        success = self._HH400_win32.HH_ReadFiFo(self.DevIdx,data.ctypes.data,count, byref(length))
        if success < 0:
            logging.warning(__name__ + ' : error in HH_ReadFiFo')
            self.get_ErrorString(success)
        return length.value, data
        
        
    def set_MarkerEdgesRising(self,me0,me1,me2,me3):
        success = self._HH400_win32.HH_SetMarkerEdges(self.DevIdx, int(me0), int(me1), int(me2), int(me3))
        if success < 0:
            logging.warning(__name__ + ' : error in HH_SetMarkerEdges')
            self.get_ErrorString(success)
            
    def set_MarkerEnable(self,me0,me1,me2,me3):
        success = self._HH400_win32.HH_SetMarkerEnable(self.DevIdx, int(me0), int(me1), int(me2), int(me3))
        if success < 0:
            logging.warning(__name__ + ' : error in HH_SetMarkerEnable')
            self.get_ErrorString(success)
            
    def get_ErrorString(self, errorcode):
        ErrorString = numpy.array([40*' '])
        if self._HH400_win32.HH_GetErrorString(ErrorString.ctypes.data, errorcode) != 0:
            logging.warning(__name__ + ' : error in HH_GetErrorString')
        print(ErrorString)
        return ErrorString

    def get_DeviceType(self):
        return 'HH_400'
