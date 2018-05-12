'''
Date : 19 April 2018
@author: David Crisp
'''

#TODO       Use https://www.python-course.eu/python3_properties.php for Get and Set properties.
#TODO       This allows the property to be updated on getting IF it is stale.   Stale might be 90 seconds.
#TODO       This is because we cant just query a siongle property with the Fronious API.
#TODO       We shouldnt hit the API for every property as this needlessly loads the server.

import requests
from collections import namedtuple
import datetime

class Fronius:
    '''
    Interface to communicate with the Fronius Symo over http / JSON
    Attributes:
        host        The ip/domain of the Fronius device
        useHTTPS    Use HTTPS instead of HTTP :  Froinus API V1 only supports HTTP
        timeout     HTTP timeout in seconds

        https://thomas-cokelaer.info/tutorials/sphinx/docstring_python.html

    '''

    def __init__(self, host, useHTTPS=False, HTTPtimeout=10):
        self.lastSuccessfullResponseTime = None     #   TimeStamp from that shows last successful query time
        self.datatimeoutseconds = 90                #   seconds


        self.scope = "Device"                       #   Default Scope
        self.DeviceID = 1                           #   Default Unit ID.


        """
        Core API / UNIT  Information
        http://<hostname>/solar_api/GetAPIVersion.cgi
        """
        self.APIVersion = None
        self.BaseURL = None
        self.CompatibilityRange = None


        """
        Unit Status
        from Common Response Header for Each Query
        """
        UnitStatusFields = ['TimeStamp', 'code', 'status', 'description', 'reason', 'usermessage']
        self.UnitStatus = namedtuple('InverterInfo', UnitStatusFields)
        self.UnitStatus.__new__.__defaults__ = (None,) * len(self.UnitStatus._fields)


        """
        Inverter Information
        http://<hostname>/solar_api/v1/GetInverterInfo.cgi
        """
        InverterInfoFields = ['CustomName','DT','ErrorCode','PVPower','Show','StatusCode','UniqueID']
        self.InverterInfo = namedtuple('InverterInfo',InverterInfoFields)
        self.InverterInfo.__new__.__defaults__ = (None,) * len(self.InverterInfo._fields)


        """
        Information about devices currently online
         http://<hostname>/solar_api/v1/GetActiveDeviceInfo.cgi?DeviceClass=System
        """
        # Section 3.7 - Lots of picking here to get it right... don't have half the devices needed to actually test and read.


        """
        Logger Informtation
        http://<hostname>/solar_api/v1/GetLoggerInfo.cgi
        """
        LoggerInfoFields = ['C02Factor','CO2Unit','CashCurrency','CashFactor','DefaultLanguage','DeliveryFactor','HWVersion','PlatformID','ProductID','SWVersion','TimezoneLocation','TimezoneName','UTCOffset','UniqueID']
        self.LoggerInfo = namedtuple('LoggerInfo', LoggerInfoFields)
        self.LoggerInfo.__new__.__defaults__ = (None,) * len(self.LoggerInfo._fields)


        """
        Inverter Status LEDs
        Current status of the Inverter LEDS
        http://<hostname>solar_api/v1/GetLoggerLEDInfo.cgi
        """
        InverterStatusLEDFields = ['powerLED','SolarNetLED','SolarWebLED','WLANLED']
        LEDinfoFields = ['Color','State','Source']
        self.InverterStatusLEDs = namedtuple('InverterStatusLEDs',InverterStatusLEDFields)
        self.InverterStatusLEDs.powerLED = namedtuple('powerLED',LEDinfoFields)       # GetLoggerLEDInfo.cgi - PowerLED
        self.InverterStatusLEDs.powerLED.__new__.__defaults__ = (None,) * len(self.InverterStatusLEDs.powerLED._fields)
        self.InverterStatusLEDs.SolarNetLED = namedtuple('SolarNetLED',LEDinfoFields)    # GetLoggerLEDInfo.cgi - SolarNetLED
        self.InverterStatusLEDs.SolarNetLED.__new__.__defaults__ = (None,) * len(self.InverterStatusLEDs.SolarNetLED._fields)
        self.InverterStatusLEDs.SolarWebLED = namedtuple('SolarWebLED',LEDinfoFields)    # GetLoggerLEDInfo.cgi - SolarWebLED
        self.InverterStatusLEDs.SolarWebLED.__new__.__defaults__ = (None,) * len(self.InverterStatusLEDs.SolarWebLED._fields)
        self.InverterStatusLEDs.WLANLED = namedtuple('WLANLED',LEDinfoFields)        # GetLoggerLEDInfo.cgi - WLANLED
        self.InverterStatusLEDs.WLANLED.__new__.__defaults__ = (None,) * len(self.InverterStatusLEDs.WLANLED._fields)

        """
        Inverter Realtime Data Collections        
        One of the problems with these variables listed in the API document is they do not align exactly with what the device ACTUALLY delivers when queired.                              
        """
        # TODO   Lets just collect THESE ones first, from whartever they actually gert processed from and then I can extend to collect ALL the values in the future.
        # TODO   Some of the data are collected from the same source. For instance, CumulationInverterData collects PAC which is the same PAC Value

        #   CommonInvertData - Universal values from all units
        #   http://<hostname>/solar_api/v1/GetInverterRealtimeData.cgi?Scope=System&DeviceID=0&DataCollection=CommonInvertData
        #   Note: the U for voltage is German.  U = Unterschied which stands for Difference.  Voltage is a Difference.
        #   I COULD convert it to V for Voltage.   It would probably make this tool slightly more functional for English speakers.
        #
        CommonInverterFields = ['PAC','SAC','IAC','VAC','FAC','IDC','VDC','Day_Energy','Year_Energy','Total_Energy','DeviceStatus']
        CommonDeviceStatusFields = ['ErrorCode','LEDColor','LEDState','MgmtTimerRemainingTime','StateToReset','StatusCode']
        CommonInverterValuesUnitValues = ['Value','Unit','Source']
        self.CommonInverterValues = namedtuple('CommonInverterValues',CommonInverterFields)
        self.CommonInverterValues.PAC = namedtuple('CommonInverterValuesUnitValues',CommonInverterValuesUnitValues)  #   THIS IS COMMON!  so all records will use this one.
        self.CommonInverterValues.PAC.__new__.__defaults__ = (None,) * len(self.CommonInverterValues.PAC._fields)
        self.CommonInverterValues.SAC = namedtuple('CommonInverterValuesUnitValues',CommonInverterValuesUnitValues)
        self.CommonInverterValues.SAC.__new__.__defaults__ = (None,) * len(self.CommonInverterValues.SAC._fields)
        self.CommonInverterValues.IAC = namedtuple('CommonInverterValuesUnitValues',CommonInverterValuesUnitValues)
        self.CommonInverterValues.IAC.__new__.__defaults__ = (None,) * len(self.CommonInverterValues.IAC._fields)
        self.CommonInverterValues.VAC = namedtuple('CommonInverterValuesUnitValues',CommonInverterValuesUnitValues)
        self.CommonInverterValues.VAC.__new__.__defaults__ = (None,) * len(self.CommonInverterValues.VAC._fields)
        self.CommonInverterValues.FAC = namedtuple('CommonInverterValuesUnitValues',CommonInverterValuesUnitValues)
        self.CommonInverterValues.FAC.__new__.__defaults__ = (None,) * len(self.CommonInverterValues.FAC._fields)
        self.CommonInverterValues.IDC = namedtuple('CommonInverterValuesUnitValues',CommonInverterValuesUnitValues)
        self.CommonInverterValues.IDC.__new__.__defaults__ = (None,) * len(self.CommonInverterValues.IDC._fields)
        self.CommonInverterValues.VDC = namedtuple('CommonInverterValuesUnitValues',CommonInverterValuesUnitValues)
        self.CommonInverterValues.VDC.__new__.__defaults__ = (None,) * len(self.CommonInverterValues.VDC._fields)
        self.CommonInverterValues.Day_Energy = namedtuple('CommonInverterValuesUnitValues',CommonInverterValuesUnitValues)       #   THIS IS COMMON!  so all records will use this one.
        self.CommonInverterValues.Day_Energy.__new__.__defaults__ = (None,) * len(self.CommonInverterValues.Day_Energy._fields)
        self.CommonInverterValues.Year_Energy = namedtuple('CommonInverterValuesUnitValues',CommonInverterValuesUnitValues)      #   THIS IS COMMON!  so all records will use this one.
        self.CommonInverterValues.Year_Energy.__new__.__defaults__ = (None,) * len(self.CommonInverterValues.Year_Energy._fields)
        self.CommonInverterValues.Total_Energy = namedtuple('CommonInverterValuesUnitValues', CommonInverterValuesUnitValues)    #   THIS IS COMMON!  so all records will use this one.
        self.CommonInverterValues.Total_Energy.__new__.__defaults__ = (None,) * len(self.CommonInverterValues.Total_Energy._fields)
        self.CommonInverterValues.DeviceStatus = namedtuple('CommonDeviceStatusFields', CommonDeviceStatusFields)
        self.CommonInverterValues.DeviceStatus.__new__.__defaults__ = (None,) * len(self.CommonInverterValues.DeviceStatus._fields)

        #   3 Phase Inverter Data
        #   http://<hostname>/solar_api/v1/GetInverterRealtimeData.cgi?Scope=System&DeviceID=0&DataCollection=3PInverterData
        #
        ThreePhaseinverterFields = ['IAC_L1','IAC_L2','IAC_L3','VAC_PH1','VAC_PH2','VAC_PH3','T_Ambient','Rotation_Speed_Fan_FL','Rotation_Speed_Fan_FR','Rotation_Speed_Fan_BL','Rotation_Speed_Fan_BR']
        ThreePhaseinverterUnitValues = ['Value','Unit','Source']
        self.ThreePhaseinverterValues = namedtuple('ThreePhaseinverterValues',ThreePhaseinverterFields)
        self.ThreePhaseinverterValues.IAC_L1 = namedtuple('ThreePhaseinverterUnitValues',ThreePhaseinverterUnitValues)
        self.ThreePhaseinverterValues.IAC_L1.__new__.__defaults__ = (None,) * len(self.ThreePhaseinverterValues.IAC_L1._fields)
        self.ThreePhaseinverterValues.IAC_L2 = namedtuple('ThreePhaseinverterUnitValues',ThreePhaseinverterUnitValues)
        self.ThreePhaseinverterValues.IAC_L2.__new__.__defaults__ = (None,) * len(self.ThreePhaseinverterValues.IAC_L2._fields)
        self.ThreePhaseinverterValues.IAC_L3 = namedtuple('ThreePhaseinverterUnitValues',ThreePhaseinverterUnitValues)
        self.ThreePhaseinverterValues.IAC_L3.__new__.__defaults__ = (None,) * len(self.ThreePhaseinverterValues.IAC_L2._fields)
        self.ThreePhaseinverterValues.VAC_PH1 = namedtuple('ThreePhaseinverterUnitValues',ThreePhaseinverterUnitValues)
        self.ThreePhaseinverterValues.VAC_PH1.__new__.__defaults__ = (None,) * len(self.ThreePhaseinverterValues.VAC_PH1._fields)
        self.ThreePhaseinverterValues.VAC_PH2 = namedtuple('ThreePhaseinverterUnitValues',ThreePhaseinverterUnitValues)
        self.ThreePhaseinverterValues.VAC_PH2.__new__.__defaults__ = (None,) * len(self.ThreePhaseinverterValues.VAC_PH2._fields)
        self.ThreePhaseinverterValues.VAC_PH3 = namedtuple('ThreePhaseinverterUnitValues',ThreePhaseinverterUnitValues)
        self.ThreePhaseinverterValues.VAC_PH3.__new__.__defaults__ = (None,) * len(self.ThreePhaseinverterValues.VAC_PH3._fields)

        #   The following data do not appear to be available on the Fronius Hybrid system.  Certainly not on the unit I have.
        #   These values MIGHT not be correctly retrieved from the system.
        self.ThreePhaseinverterValues.T_Ambient = namedtuple('ThreePhaseinverterUnitValues',ThreePhaseinverterUnitValues)
        self.ThreePhaseinverterValues.T_Ambient.__new__.__defaults__ = (None,) * len(self.ThreePhaseinverterValues.T_Ambient._fields)
        self.ThreePhaseinverterValues.Rotation_Speed_Fan_FR = namedtuple('ThreePhaseinverterUnitValues',ThreePhaseinverterUnitValues)
        self.ThreePhaseinverterValues.Rotation_Speed_Fan_FR.__new__.__defaults__ = (None,) * len(self.ThreePhaseinverterValues.Rotation_Speed_Fan_FR._fields)
        self.ThreePhaseinverterValues.Rotation_Speed_Fan_FL = namedtuple('ThreePhaseinverterUnitValues',ThreePhaseinverterUnitValues)
        self.ThreePhaseinverterValues.Rotation_Speed_Fan_FL.__new__.__defaults__ = (None,) * len(self.ThreePhaseinverterValues.Rotation_Speed_Fan_FL._fields)
        self.ThreePhaseinverterValues.Rotation_Speed_Fan_BR = namedtuple('ThreePhaseinverterUnitValues',ThreePhaseinverterUnitValues)
        self.ThreePhaseinverterValues.Rotation_Speed_Fan_BR.__new__.__defaults__ = (None,) * len(self.ThreePhaseinverterValues.Rotation_Speed_Fan_BR._fields)
        self.ThreePhaseinverterValues.Rotation_Speed_Fan_BL = namedtuple('ThreePhaseinverterUnitValues',ThreePhaseinverterUnitValues)
        self.ThreePhaseinverterValues.Rotation_Speed_Fan_BL.__new__.__defaults__ = (None,) * len(self.ThreePhaseinverterValues.Rotation_Speed_Fan_BL._fields)


        #   MinMaxInverterData   ----   Not Supported for Hybrid Systems
        #   http://<hostname>/solar_api/v1/GetInverterRealtimeData.cgi?Scope=System&DeviceID=0&DataCollection=MinMaxInverterData
        #
        #   TODO need to test this against an inverter that has these parameters

        MinMaxInverterDataFields = ['Day_PMAX','Day_VACMAX','Day_VACMNIN','Day_VDCMax','Year_PMAX','Year_VACMAX','Year_VACMNIN','Year_VDCMax','Total_PMAX','Total_VACMAX','Total_VACMNIN','Total_VDCMax']
        MinMaxInverterDataUnitValues = ['Value','Unit','Source']

        self.MinMaxInverterDatavalues = namedtuple('MinMaxInverterDataFields',MinMaxInverterDataFields)

        self.MinMaxInverterDatavalues.Day_PMAX = namedtuple('MinMaxInverterDataUnitValues',MinMaxInverterDataUnitValues)        # Maximum AC Power of Current Day
        self.MinMaxInverterDatavalues.Day_PMAX.__new__.__defaults__ = (None,) * len(self.MinMaxInverterDatavalues.Day_PMAX._fields)
        self.MinMaxInverterDatavalues.Day_VACMAX = namedtuple('MinMaxInverterDataUnitValues',MinMaxInverterDataUnitValues)      # Day_UACMAX - Maximum AC Voltage of Current Day
        self.MinMaxInverterDatavalues.Day_VACMAX.__new__.__defaults__ = (None,) * len(self.MinMaxInverterDatavalues.Day_VACMAX._fields)
        self.MinMaxInverterDatavalues.Day_VACMNIN = namedtuple('MinMaxInverterDataUnitValues',MinMaxInverterDataUnitValues)     # Day_UACMNIN - Minimum AC Voltage of Current Day
        self.MinMaxInverterDatavalues.Day_VACMNIN.__new__.__defaults__ = (None,) * len(self.MinMaxInverterDatavalues.Day_VACMNIN._fields)
        self.MinMaxInverterDatavalues.Day_VDCMax = namedtuple('MinMaxInverterDataUnitValues',MinMaxInverterDataUnitValues)      # UDCMax - Maximum DC Voltage Current Day
        self.MinMaxInverterDatavalues.Day_VDCMax.__new__.__defaults__ = (None,) * len(self.MinMaxInverterDatavalues.Day_VDCMax._fields)

        self.MinMaxInverterDatavalues.Year_PMAX = namedtuple('MinMaxInverterDataUnitValues',MinMaxInverterDataUnitValues)       # Maximum AC Power of Current Year
        self.MinMaxInverterDatavalues.Year_PMAX.__new__.__defaults__ = (None,) * len(self.MinMaxInverterDatavalues.Year_PMAX._fields)
        self.MinMaxInverterDatavalues.Year_VACMAX = namedtuple('MinMaxInverterDataUnitValues',MinMaxInverterDataUnitValues)     # Year_UACMAX - Maximum AC Voltage of Current Year
        self.MinMaxInverterDatavalues.Year_VACMAX.__new__.__defaults__ = (None,) * len(self.MinMaxInverterDatavalues.Year_VACMAX._fields)
        self.MinMaxInverterDatavalues.Year_VACMNIN = namedtuple('MinMaxInverterDataUnitValues',MinMaxInverterDataUnitValues)    # Year_UACMNIN - Minimum AC Voltage of Current Year
        self.MinMaxInverterDatavalues.Year_VACMNIN.__new__.__defaults__ = (None,) * len(self.MinMaxInverterDatavalues.Year_VACMNIN._fields)
        self.MinMaxInverterDatavalues.Year_VDCMax = namedtuple('MinMaxInverterDataUnitValues',MinMaxInverterDataUnitValues)     # Year_UDCMax -  Maximum DC Voltage Current Year
        self.MinMaxInverterDatavalues.Year_VDCMax.__new__.__defaults__ = (None,) * len(self.MinMaxInverterDatavalues.Year_VDCMax._fields)

        self.MinMaxInverterDatavalues.Total_PMAX = namedtuple('MinMaxInverterDataUnitValues',MinMaxInverterDataUnitValues)      # Maximum AC Power overall
        self.MinMaxInverterDatavalues.Total_PMAX.__new__.__defaults__ = (None,) * len(self.MinMaxInverterDatavalues.Total_PMAX._fields)
        self.MinMaxInverterDatavalues.Total_VACMAX = namedtuple('MinMaxInverterDataUnitValues',MinMaxInverterDataUnitValues)    # Total_UACMAX - Maximum AC Voltage overall
        self.MinMaxInverterDatavalues.Total_VACMAX.__new__.__defaults__ = (None,) * len(self.MinMaxInverterDatavalues.Total_VACMAX._fields)
        self.MinMaxInverterDatavalues.Total_VACMNIN = namedtuple('MinMaxInverterDataUnitValues',MinMaxInverterDataUnitValues)   # Total_UACMNIN - Minimum AC Voltage overall
        self.MinMaxInverterDatavalues.Total_VACMNIN.__new__.__defaults__ = (None,) * len(self.MinMaxInverterDatavalues.Total_VACMNIN._fields)
        self.MinMaxInverterDatavalues.Total_VDCMax = namedtuple('MinMaxInverterDataUnitValues',MinMaxInverterDataUnitValues)    # Total_UDCMax - Maximum DC Voltage overall
        self.MinMaxInverterDatavalues.Total_VDCMax.__new__.__defaults__ = (None,) * len(self.MinMaxInverterDatavalues.Total_VDCMax._fields)

        """
        MeterReraltimeData
        http://<hostname>/solar_api/v1/GetMeterRealtimeData.cgi?Scope=Device&DeviceID=1
        """
        MeterReatlTimeDataFields = ['Current_AC_Phase_1','Current_AC_Phase_2','Current_AC_Phase_3','Serial', 'Enable',
                                    'EnergyReactive_VArAC_Sum_Consumed','EnergyReactive_VArAC_Sum_Produced',
                                    'EnergyReal_WAC_Minus_Absolute', 'EnergyReal_WAC_Plus_Absolute',
                                    'EnergyReal_WAC_Sum_Consumed', 'EnergyReal_WAC_Sum_Produced',
                                    'Frequency_Phase_Average', 'Meter_Location_Current','PowerApparent_S_Phase_1',
                                    'PowerApparent_S_Phase_2', 'PowerApparent_S_Phase_3', 'PowerApparent_S_Sum',
                                    'PowerFactor_Phase_1', 'PowerFactor_Phase_2', 'PowerFactor_Phase_3',
                                    'PowerFactor_Sum','PowerReactive_Q_Phase_1','PowerReactive_Q_Phase_2',
                                    'PowerReactive_Q_Phase_3','PowerReactive_Q_Sum', 'PowerReal_P_Phase_1',
                                    'PowerReal_P_Phase_2','PowerReal_P_Phase_3', 'PowerReal_P_Sum', 'TimeStamp',
                                    'Visible', 'Voltage_AC_PhaseToPhase_12', 'Voltage_AC_PhaseToPhase_23',
                                    'Voltage_AC_PhaseToPhase_31', 'Voltage_AC_Phase_1', 'Voltage_AC_Phase_2',
                                    'Voltage_AC_Phase_3', 'Details', 'Manufacturer','Model']
        self.MeterReatlTimeData = namedtuple('MeterReatlTimeDataFields',MeterReatlTimeDataFields)
        self.MeterReatlTimeData.__new__.__defaults__ = (None,) * len(self.MeterReatlTimeData._fields)



        """
        PowerFlowRealtimeData
        http://<hostname>/Solar_api/v1/GetPowerFlowRealtimeData.fcgi 
        """
        #TODO We can set this up so we can add multiple inverters if they exist.
        # eg: PowerFlowRealtion inverters ---Inverter 1
        #                                  ---Inverter 2
        #                       site
        PowerFlowRealtimeSiteFields = ['BatteryStandby','Energy_Day','Energy_Total','Energy_Year','Meter_Location','Mode','Power_Akku','Power_Grid','Power_Load','Power_PV','Rel_Autonomy','Rel_SelfConsumption']
        self.PowerFlowRealtimeSite = namedtuple('PowerFlowRealtimeSiteFields',PowerFlowRealtimeSiteFields)
        self.PowerFlowRealtimeSite.__new__.__defaults__ = (None,) * len(self.PowerFlowRealtimeSite._fields)


        self.host = host
        self.HTTPtimeout = HTTPtimeout
        if useHTTPS:
            self.protocol = "https"
        else:
            self.protocol = "http"

        self._fetch_APIVersion()
        if (self.APIVersion != 1):
            raise ValueError('Wrong API Version.  Version {} not supported'.format(self.APIVersion))

        '''
        On first run we will go through ALL the different data collection routines... 
        Then when we query it later we only query what we want. 
        '''
        self._getInverterinfo()
        self._getLoggerInfo()
        self._getPowerFlowRealtimeData()
        self._GetInverterRealtimeData(self.scope, self.DeviceID, 'CumulationInverterData')
        self._GetInverterRealtimeData(self.scope, self.DeviceID, 'CommonInverterData')
        self._GetInverterRealtimeData(self.scope, self.DeviceID, '3PInverterData')
        self._GetInverterRealtimeData(self.scope, self.DeviceID, 'MinMaxInverterData')
        self._GetActiveDeviceInfo()
        self._GetMeterRealtimeData()

    #-------------------------------------------------------------------------------------------------------------------
    """
    By using a property decorator and the following properties wqe can trigger off updates if the data is stale when its queired. 
    If the data is still within a set "currency" time then it will just return the data the system already has.
    
    used documentation at https://www.python-course.eu/python3_properties.php for @property 
    """
    @property
    def ACPower(self):
        if (self._checkdatacurrency):
            return self.CommonInverterValues.PAC.Value
        else:
            self._GetInverterRealtimeData(self.scope, self.DeviceID, 'CommonInverterData')
            return self.CommonInverterValues.PAC.Value

    @property
    def Day_Energy(self):
        if (self._checkdatacurrency):
            return self.CommonInverterValues.Day_Energy.Value
        else:
            self._GetInverterRealtimeData(self.scope, self.DeviceID, 'CommonInverterData')
            return self.CommonInverterValues.Day_Energy.Value

    @property
    def Year_Energy(self):
        if (self._checkdatacurrency):
            return self.CommonInverterValues.Year_Energy.Value
        else:
            self._GetInverterRealtimeData(self.scope, self.DeviceID, 'CommonInverterData')
            return self.CommonInverterValues.Year_Energy.Value

    @property
    def Total_Energy(self):
        if (self._checkdatacurrency):
            return self.CommonInverterValues.Total_Energy.Value
        else:
            self._GetInverterRealtimeData(self.scope, self.DeviceID, 'CommonInverterData')
            return self.CommonInverterValues.Total_Energy.Value

    @property
    def ACCurrent(self):
        if (self._checkdatacurrency):
            return self.CommonInverterValues.IAC.Value
        else:
            self._GetInverterRealtimeData(self.scope, self.DeviceID, 'CommonInverterData')
            return self.CommonInverterValues.IAC.Value

    @property
    def ACVoltage(self):
        if (self._checkdatacurrency):
            return self.CommonInverterValues.VAC.Value
        else:
            self._GetInverterRealtimeData(self.scope, self.DeviceID, 'CommonInverterData')
            return self.CommonInverterValues.VAC.Value

    @property
    def ACFrequency(self):
        if (self._checkdatacurrency):
            return self.CommonInverterValues.FAC.Value
        else:
            self._GetInverterRealtimeData(self.scope, self.DeviceID, 'CommonInverterData')
            return self.CommonInverterValues.FAC.Value

    @property
    def DCCurrent(self):
        if (self._checkdatacurrency):
            return self.CommonInverterValues.IDC.Value
        else:
            self._GetInverterRealtimeData(self.scope, self.DeviceID, 'CommonInverterData')
            return self.CommonInverterValues.IDC.Value

    @property
    def DCVoltage(self):
        if (self._checkdatacurrency):
            return self.CommonInverterValues.VDC.Value
        else:
            self._GetInverterRealtimeData(self.scope, self.DeviceID, 'CommonInverterData')
            return self.CommonInverterValues.VDC.Value


    #-------------------------------------------------------------------------------------------------------------------
    @property
    def ACcurrentPH1(self):
        if (self._checkdatacurrency):
            return self.ThreePhaseinverterValues.IAC_L1.Value
        else:
            self._GetInverterRealtimeData(self.scope, self.DeviceID, '3PInverterData')
            return self.ThreePhaseinverterValues.IAC_L1.Value

    @property
    def ACcurrentPH2(self):
        if (self._checkdatacurrency):
            return self.ThreePhaseinverterValues.IAC_L2.Value
        else:
            self._GetInverterRealtimeData(self.scope, self.DeviceID, '3PInverterData')
            return self.ThreePhaseinverterValues.IAC_L2.Value

    @property
    def ACcurrentPH3(self):
        if (self._checkdatacurrency):
            return self.ThreePhaseinverterValues.IAC_L3.Value
        else:
            self._GetInverterRealtimeData(self.scope, self.DeviceID, '3PInverterData')
            return self.ThreePhaseinverterValues.IAC_L3.Value

    @property
    def ACVoltsPH1(self):
        if (self._checkdatacurrency):
            return self.ThreePhaseinverterValues.VAC_PH1.Value
        else:
            self._GetInverterRealtimeData(self.scope, self.DeviceID, '3PInverterData')
            return self.ThreePhaseinverterValues.VAC_PH1.Value

    @property
    def ACVoltsPH2(self):
        if (self._checkdatacurrency):
            return self.ThreePhaseinverterValues.VAC_PH2.Value
        else:
            self._GetInverterRealtimeData(self.scope, self.DeviceID, '3PInverterData')
            return self.ThreePhaseinverterValues.VAC_PH2.Value

    @property
    def ACVoltsPH1(self):
        if (self._checkdatacurrency):
            return self.ThreePhaseinverterValues.VAC_PH3.Value
        else:
            self._GetInverterRealtimeData(self.scope, self.DeviceID, '3PInverterData')
            return self.ThreePhaseinverterValues.VAC_PH3.Value

    @property
    def AmbientTemp(self):
        if (self._checkdatacurrency):
            return self.ThreePhaseinverterValues.T_Ambient.Value
        else:
            self._GetInverterRealtimeData(self.scope, self.DeviceID, '3PInverterData')
            return self.ThreePhaseinverterValues.T_Ambient.Value

    @property
    def Rotation_Speed_Fan_FR(self):
        if (self._checkdatacurrency):
            return self.ThreePhaseinverterValues.Rotation_Speed_Fan_FR.Value
        else:
            self._GetInverterRealtimeData(self.scope, self.DeviceID, '3PInverterData')
            return self.ThreePhaseinverterValues.Rotation_Speed_Fan_FR.Value

    @property
    def Rotation_Speed_Fan_FL(self):
        if (self._checkdatacurrency):
            return self.ThreePhaseinverterValues.Rotation_Speed_Fan_FL.Value
        else:
            self._GetInverterRealtimeData(self.scope, self.DeviceID, '3PInverterData')
            return self.ThreePhaseinverterValues.Rotation_Speed_Fan_FL.Value

    @property
    def Rotation_Speed_Fan_BR(self):
        if (self._checkdatacurrency):
            return self.ThreePhaseinverterValues.Rotation_Speed_Fan_BR.Value
        else:
            self._GetInverterRealtimeData(self.scope, self.DeviceID, '3PInverterData')
            return self.ThreePhaseinverterValues.Rotation_Speed_Fan_BR.Value

    @property
    def Rotation_Speed_Fan_BL(self):
        if (self._checkdatacurrency):
            return self.ThreePhaseinverterValues.Rotation_Speed_Fan_BL.Value
        else:
            self._GetInverterRealtimeData(self.scope, self.DeviceID, '3PInverterData')
            return self.ThreePhaseinverterValues.Rotation_Speed_Fan_BL.Value
    #-------------------------------------------------------------------------------------------------------------------
    @property
    def Day_PowerMAX(self):
        if (self._checkdatacurrency):
            return self.MinMaxInverterDatavalues.Day_PMAX.Value
        else:
            self._GetInverterRealtimeData(self.scope, self.DeviceID, 'MinMaxInverterData')
            return self.MinMaxInverterDatavalues.Day_PMAX.Value

    @property
    def Day_VoltageACMAX(self):
        if (self._checkdatacurrency):
            return self.MinMaxInverterDatavalues.Day_VACMAX.Value
        else:
            self._GetInverterRealtimeData(self.scope, self.DeviceID, 'MinMaxInverterData')
            return self.MinMaxInverterDatavalues.Day_VACMAX.Value

    @property
    def Day_VoltageACMIN(self):
        if (self._checkdatacurrency):
            return self.MinMaxInverterDatavalues.Day_VACMNIN.Value
        else:
            self._GetInverterRealtimeData(self.scope, self.DeviceID, 'MinMaxInverterData')
            return self.MinMaxInverterDatavalues.Day_VACMNIN.Value

    @property
    def Day_VoltageDCMAX(self):
        if (self._checkdatacurrency):
            return self.MinMaxInverterDatavalues.Day_VDCMax.Value
        else:
            self._GetInverterRealtimeData(self.scope, self.DeviceID, 'MinMaxInverterData')
            return self.MinMaxInverterDatavalues.Day_VDCMax.Value

    @property
    def Year_PowerMAX(self):
        if (self._checkdatacurrency):
            return self.MinMaxInverterDatavalues.Year_PMAX.Value
        else:
            self._GetInverterRealtimeData(self.scope, self.DeviceID, 'MinMaxInverterData')
            return self.MinMaxInverterDatavalues.Year_PMAX.Value

    @property
    def Year_VoltageACMAX(self):
        if (self._checkdatacurrency):
            return self.MinMaxInverterDatavalues.Year_VACMAX.Value
        else:
            self._GetInverterRealtimeData(self.scope, self.DeviceID, 'MinMaxInverterData')
            return self.MinMaxInverterDatavalues.Year_VACMAX.Value

    @property
    def Year_VoltageACMIN(self):
        if (self._checkdatacurrency):
            return self.MinMaxInverterDatavalues.Year_VACMNIN.Value
        else:
            self._GetInverterRealtimeData(self.scope, self.DeviceID, 'MinMaxInverterData')
            return self.MinMaxInverterDatavalues.Year_VACMNIN.Value

    @property
    def Year_VoltageDCMAX(self):
        if (self._checkdatacurrency):
            return self.MinMaxInverterDatavalues.Year_VDCMax.Value
        else:
            self._GetInverterRealtimeData(self.scope, self.DeviceID, 'MinMaxInverterData')
            return self.MinMaxInverterDatavalues.Year_VDCMax.Value

    @property
    def Total_PowerMAX(self):
        if (self._checkdatacurrency):
            return self.MinMaxInverterDatavalues.Total_PMAX.Value
        else:
            self._GetInverterRealtimeData(self.scope, self.DeviceID, 'MinMaxInverterData')
            return self.MinMaxInverterDatavalues.Total_PMAX.Value

    @property
    def Total_VoltageACMAX(self):
        if (self._checkdatacurrency):
            return self.MinMaxInverterDatavalues.Total_VACMAX.Value
        else:
            self._GetInverterRealtimeData(self.scope, self.DeviceID, 'MinMaxInverterData')
            return self.MinMaxInverterDatavalues.Total_VACMAX.Value

    @property
    def Total_VoltageACMIN(self):
        if (self._checkdatacurrency):
            return self.MinMaxInverterDatavalues.Total_VACMNIN.Value
        else:
            self._GetInverterRealtimeData(self.scope, self.DeviceID, 'MinMaxInverterData')
            return self.MinMaxInverterDatavalues.Total_VACMNIN.Value

    @property
    def Total_VoltageDCMAX(self):
        if (self._checkdatacurrency):
            return self.MinMaxInverterDatavalues.Total_VDCMax.Value
        else:
            self._GetInverterRealtimeData(self.scope, self.DeviceID, 'MinMaxInverterData')
            return self.MinMaxInverterDatavalues.Total_VDCMax.Value


    #-------------------------------------------------------------------------------------------------------------------
    def _checkdatacurrency(self):
        """
        check to make sure the data has not gone stale.
        :return:    If data is current then return true else return false.
        """

        SecondsFromLastSuccessfullQuery = datetime.datetime.utcnow().timestamp() - self.lastSuccessfullResponseTime
        if  SecondsFromLastSuccessfullQuery <= self.datatimeoutseconds:
            return True
        else:
            return False


    #-------------------------------------------------------------------------------------------------------------------
    def _fetchDataFromAPI(self, url):
        """
        Performs the http query to Fronius unit.
        Returns a json text strong

        :param url:    The Target URL of the Fronius system.  See STATIC definitions
        :return:    Return the JSON text block containing queried data
        """
        json = None
        #   Try to retrieve a WEB API response from the Fronius unit and handle common errors
        try:
            response = requests.get(url, timeout = self.HTTPtimeout)

        except requests.exceptions.ConnectTimeout:
            print("Request Exception Timed Out")

        except ConnectionError:
            print("Connection Error")

        #   If the actual HTTP call works (no hard error exception)
        #   then check if there's any soft errors returned from the Fronius API.
        #   Handle any other response other then 200 and 201.
        #   Generally none of the other errors should show up unless the Fronius Unit has ....
        #   Done somethign inconsistent.

        #TODO check the errors being raised and make sure they make sense.
        else:
            if (response.status_code == 201) or (response.status_code == 200):
                json = response.json()

            elif response.status_code >= 500:
                raise ValueError('[!] [{0}] Server Error'.format(response.status_code))

            elif response.status_code == 404:
                raise ValueError('[!] [{0}] URL not found: [{1}]'.format(response.status_code, url))

            elif response.status_code == 401:
                raise ValueError('[!] [{0}] Authentication Failed'.format(response.status_code))

            elif response.status_code >= 300:
                raise ValueError('[!] [{0}] Unexpected redirect.'.format(response.status_code))

            else:
                raise ValueError('[?] Unexpected Error: [HTTP {0}]: Content: {1}'.format(response.status_code, response.content))
        return json

    #-------------------------------------------------------------------------------------------------------------------
    def _fetch_APIVersion(self):
        """
        The API Version JSON does not contain a standard status header etc like the other urls.   This has to be handled differently and seperatly.
        :return:
        """
        url = "{protocol}://{host}/solar_api/GetAPIVersion.cgi".format(protocol = self.protocol, host = self.host)
        json = self._fetchDataFromAPI(url)
        self.APIVersion = json['APIVersion']
        self.BaseURL = json['BaseURL']
        self.CompatibilityRange = json['CompatibilityRange']


    #-------------------------------------------------------------------------------------------------------------------
    def _GetJSONData(self,url):
        """
        Extract the JSON Body from the code and return it as a dict
        :param url:
        :return:
        """
        json = self._fetchDataFromAPI(url)
        self._extractCRHData(json)
        return json


    #-------------------------------------------------------------------------------------------------------------------
    def _extractCRHData(self, json):
        """
        Take the JSON Data from the Fronius unit and extract the status data from it.
        :param json:
        :return:
        """


        self.UnitStatus.code = None # Set the Status code back to none ensures no data is accidently used when it shouldnt be

        #   Common Response Header code and error messages
        #   How do I offload these to another module.
        CRHErrorCodeFields = ['value','status','description']
        CRHErrorCodes = {0: namedtuple('CRHErrorCodes',CRHErrorCodeFields)(0,'OKAY', 'Request successfully finished, Data are valid'),
                      1: namedtuple('CRHErrorCodes',CRHErrorCodeFields)(1,'NotImplemented', 'The request or a part of the request is not implemented yet'),
                      2: namedtuple('CRHErrorCodes',CRHErrorCodeFields)(2,'Uninitialized', 'Instance of APIRequest created, but not yet configured'),
                      3: namedtuple('CRHErrorCodes',CRHErrorCodeFields)(3,'Initialized', 'Request is configured and ready to be sent'),
                      4: namedtuple('CRHErrorCodes',CRHErrorCodeFields)(4,'Running', 'Request is currently being processed (waiting for response)'),
                      5: namedtuple('CRHErrorCodes',CRHErrorCodeFields)(5,'Timeout', 'Response was not received within desired time'),
                      6: namedtuple('CRHErrorCodes',CRHErrorCodeFields)(6,'Argument Error', 'Invalid arguments/combination of arguments or missing arguments'),
                      7: namedtuple('CRHErrorCodes',CRHErrorCodeFields)(7,'LNRequestError', 'Something went wrong during sending/receiving of LN-message'),
                      8: namedtuple('CRHErrorCodes',CRHErrorCodeFields)(8,'LNRequestTimeout', 'LN-request timed out'),
                      9: namedtuple('CRHErrorCodes',CRHErrorCodeFields)(9,'LNParseError', 'Something went wrong during parsing of successfully received LN-message'),
                      10: namedtuple('CRHErrorCodes',CRHErrorCodeFields)(10,'ConfigIOError', 'Something went wrong while reading settings from local config'),
                      11: namedtuple('CRHErrorCodes',CRHErrorCodeFields)(11,'NotSupported', 'The operation/feature or whatever is not supported'),
                      12: namedtuple('CRHErrorCodes',CRHErrorCodeFields)(12,'DeviceNotAvailable', 'The device is not available'),
                      255: namedtuple('CRHErrorCodes',CRHErrorCodeFields)(255,'UnknownError', 'undefined runtime error')
                      }

        #   Note that the messages returned by the API are actually different to the messages provided in the API documentation PDF
        self.UnitStatus.timestamp = {'value': json['Head']['Timestamp']}
        self.UnitStatus.code = CRHErrorCodes[json['Head']['Status']['Code']].value
        self.UnitStatus.status = CRHErrorCodes[json['Head']['Status']['Code']].status
        self.UnitStatus.description = CRHErrorCodes[json['Head']['Status']['Code']].description
        self.UnitStatus.reason = json['Head']['Status']['Reason']
        self.UnitStatus.usermessage = json['Head']['Status']['UserMessage']

        #   If the Unit responds with a 0 error code that means the Request was successfully finished.
        #   Record the timestamp as the last successfully response.
        if self.UnitStatus.code == 0:
            self.lastSuccessfullResponseTime = datetime.datetime.utcnow().timestamp()
        return True

    #-------------------------------------------------------------------------------------------------------------------
    def _getInverterinfo(self):
        """
        Note:  At the moment this only supports the first (1) inverter in the system.   I need to obtain access to a ganged inverter array before I can properly test this code with multiple inverters.
        :return:
        """
        url = "{protocol}://{host}/{baseurl}/GetInverterInfo.cgi".format(protocol = self.protocol, host = self.host, baseurl = self.BaseURL)
        json = self._GetJSONData(url)

        inverterNumber = str(1)

        #TODO need to add handling incase these dont exist.
        self.InverterInfo.CustomName = json['Body']['Data'][inverterNumber]['CustomName']
        self.InverterInfo.DT = json['Body']['Data'][inverterNumber]['DT']
        self.InverterInfo.ErrorCode = json['Body']['Data'][inverterNumber]['ErrorCode']
        self.InverterInfo.PVPower = json['Body']['Data'][inverterNumber]['PVPower']
        self.InverterInfo.Show = json['Body']['Data'][inverterNumber]['Show']
        self.InverterInfo.StatusCode = json['Body']['Data'][inverterNumber]['StatusCode']
        self.InverterInfo.UniqueID = json['Body']['Data'][inverterNumber]['UniqueID']


    #-------------------------------------------------------------------------------------------------------------------
    def _getLoggerInfo(self):
        """
        #TODO need to add handling incase these dont exist.
        :return:
        """
        url = "{protocol}://{host}/{baseurl}/GetLoggerInfo.cgi".format(protocol=self.protocol, host=self.host,baseurl=self.BaseURL)
        json = self._GetJSONData(url)

        if 'CO2Factor' in json['Body']:
            self.LoggerInfo.C02Factor = json['Body']['LoggerInfo']['CO2Factor']
        else:
            self.LoggerInfo.C02Factor = 0

        if 'CO2Unit' in json['Body']:
            self.LoggerInfo.CO2Unit = json['Body']['LoggerInfo']['CO2Unit']
        else:
            self.LoggerInfo.CO2Unit = 0

        if 'CashCurrency' in json['Body']:
            self.LoggerInfo.CashCurrency = json['Body']['LoggerInfo']['CashCurrency']
        else:
            self.LoggerInfo.CashCurrency = 0

        if 'CashFactor' in json['Body']:
            self.LoggerInfo.CashFactor = json['Body']['LoggerInfo']['CashFactor']
        else:
            self.LoggerInfo.CashFactor = 0

        if 'DefaultLanguage' in json['Body']:
            self.LoggerInfo.DefaultLanguage = json['Body']['LoggerInfo']['DefaultLanguage']
        else:
           self.LoggerInfo.DefaultLanguage = 0

        if 'DeliveryFactor' in json['Body']:
            self.LoggerInfo.DeliveryFactor = json['Body']['LoggerInfo']['DeliveryFactor']
        else:
            self.LoggerInfo.DeliveryFactor = 0

        if 'HWVersion' in json['Body']:
            self.LoggerInfo.HWVersion = json['Body']['LoggerInfo']['HWVersion']
        else:
            self.LoggerInfo.HWVersion = 0

        if 'PlatformID' in json['Body']:
            self.LoggerInfo.PlatformID = json['Body']['LoggerInfo']['PlatformID']
        else:
            self.LoggerInfo.PlatformID = 0

        if 'SWVersion' in json['Body']:
            self.LoggerInfo.SWVersion = json['Body']['LoggerInfo']['SWVersion']
        else:
            self.LoggerInfo.SWVersion = 0

        if 'TimezoneLocation' in json['Body']:
            self.LoggerInfo.TimezoneLocation = json['Body']['LoggerInfo']['TimezoneLocation']
        else:
            self.LoggerInfo.TimezoneLocation = 0

        if 'TimezoneName' in json['Body']:
            self.LoggerInfo.TimezoneName = json['Body']['LoggerInfo']['TimezoneName']
        else:
            self.LoggerInfo.TimezoneName = 0

        if 'UTCOffset' in json['Body']:
            self.LoggerInfo.UTCOffset = json['Body']['LoggerInfo']['UTCOffset']
        else:
            self.LoggerInfo.UTCOffset = 0

        if 'UniqueIDs' in json['Body']:
            self.LoggerInfo.UniqueID = json['Body']['LoggerInfo']['UniqueID']
        else:
            self.LoggerInfo.UniqueID = 0


    #-------------------------------------------------------------------------------------------------------------------
    def _getLoggerLEDinfo(self):
        """
        :return:
        """
        url = "{protocol}://{host}/{baseurl}/GetLoggerLEDInfo.cgi".format(protocol=self.protocol, host=self.host, baseurl=self.BaseURL)
        json = self._GetJSONData(url)

        if self.UnitStatus.code == 0:
            if 'PowerLED' in json['Body']['Data']:
                self.InverterStatusLEDs.powerLED.Color = json['Body']['Data']['PowerLED']['Color']
                self.InverterStatusLEDs.powerLED.State = json['Body']['Data']['PowerLED']['State']
                self.InverterStatusLEDs.powerLED.source = 'system'
            else:
                self.InverterStatusLEDs.powerLED.Color = 0
                self.InverterStatusLEDs.powerLED.State = 0
                self.InverterStatusLEDs.powerLED.source = 'NA'

            if 'SolarNetLED' in json['Body']['Data']:
                self.InverterStatusLEDs.SolarNetLED.Color = json['Body']['Data']['SolarNetLED']['Color']
                self.InverterStatusLEDs.SolarNetLED.State = json['Body']['Data']['SolarNetLED']['State']
                self.InverterStatusLEDs.SolarNetLED.source = 'system'
            else:
                self.InverterStatusLEDs.SolarNetLED.Color = 0
                self.InverterStatusLEDs.SolarNetLED.State = 0
                self.InverterStatusLEDs.SolarNetLED.source = 'NA'

            if 'SolarWebLED' in json['Body']['Data']:
                self.InverterStatusLEDs.SolarWebLED.Color = json['Body']['Data']['SolarWebLED']['Color']
                self.InverterStatusLEDs.SolarWebLED.State = json['Body']['Data']['SolarWebLED']['State']
                self.InverterStatusLEDs.SolarWebLED.source = 'system'
            else:
                self.InverterStatusLEDs.SolarWebLED.Color = 0
                self.InverterStatusLEDs.SolarWebLED.State = 0
                self.InverterStatusLEDs.SolarWebLED.source = 'NA'

            if 'WLANLED' in json['Body']['Data']:
                self.InverterStatusLEDs.WLANLED.Color = json['Body']['Data']['WLANLED']['Color']
                self.InverterStatusLEDs.WLANLED.State = json['Body']['Data']['WLANLED']['State']
                self.InverterStatusLEDs.WLANLED.source = 'system'
            else:
                self.InverterStatusLEDs.WLANLED.Color = 0
                self.InverterStatusLEDs.WLANLED.State = 0
                self.InverterStatusLEDs.WLANLED.source = 'NA'
        else:
            print("Unable to retrieve data")
            #TODO Proper Error Handling here.

    #-------------------------------------------------------------------------------------------------------------------
    def _GetInverterRealtimeData(self, Scope = None , DeviceID = 0, DataCollection = None):
        """

        :param Scope:
        :param DeviceID:
        :param DataCollection:
        :return:


        self.fronius._GetInverterRealtimeData('System', 1, 'CurrentSumStringControlData')
        self._GetInverterRealtimeData('Device',1,'CumulationInverterData')
        self._GetStorageRealtimeData('System', 1)

        """

        if Scope is None:
            Scope = 'System'

        #   If device is selected but no deviceID and no DataCollection is selected then make an educated guess
        #   choose Device 1 and 'CumulationInverterData'
        #   Generally these should get overridden by the actual seections.
        if Scope == 'Device' and DeviceID is None and DataCollection is None:
            DeviceID = 0
            DataCollection = 'CumulationInverterData'


        url = "{protocol}://{host}/{baseurl}/GetInverterRealtimeData.cgi?Scope={Scope}&DeviceID={DeviceID}&DataCollection={DataCollection}".format(protocol=self.protocol, host=self.host, baseurl=self.BaseURL, Scope=Scope, DeviceID=DeviceID, DataCollection=DataCollection)
        json = self._GetJSONData(url)
 
        if DataCollection == 'CommonInverterData' and self.UnitStatus.code == 0:
            """
            This gets busy:    If the inverter slows down for the day it will stop collecting data and thus stop reporting the data. 
            Only fields with actual data in them will get returned.  Thus every field needs to be tested with a try.             
            """
            try:
                if 'PAC' in  json['Body']['Data']:
                    self.CommonInverterValues.PAC.Value = json['Body']['Data']['PAC']['Value']
                    self.CommonInverterValues.PAC.Unit = json['Body']['Data']['PAC']['Unit']
                    self.CommonInverterValues.PAC.source = 'system'
                else:
                    self.CommonInverterValues.PAC.Value = 0
                    self.CommonInverterValues.PAC.Unit = 0
                    self.CommonInverterValues.PAC.source = 'NA'

                if 'SAC' in  json['Body']['Data']:
                    self.CommonInverterValues.SAC.Value = json['Body']['Data']['SAC']['Value']
                    self.CommonInverterValues.SAC.Unit = json['Body']['Data']['SAC']['Unit']
                    self.CommonInverterValues.SAC.source = 'system'
                else:
                    self.CommonInverterValues.SAC.Value = 0
                    self.CommonInverterValues.SAC.Unit = 0
                    self.CommonInverterValues.SAC.source = 'NA'

                if 'IAC' in  json['Body']['Data']:
                    self.CommonInverterValues.IAC.Value = json['Body']['Data']['IAC']['Value']
                    self.CommonInverterValues.IAC.Unit = json['Body']['Data']['IAC']['Unit']
                    self.CommonInverterValues.IAC.source = 'system'
                else:
                    self.CommonInverterValues.IAC.Value = 0
                    self.CommonInverterValues.IAC.Unit = 0
                    self.CommonInverterValues.IAC.source = 'NA'

                if 'UAC' in  json['Body']['Data']:
                    self.CommonInverterValues.VAC.Value = json['Body']['Data']['UAC']['Value']
                    self.CommonInverterValues.VAC.Unit = json['Body']['Data']['UAC']['Unit']
                    self.CommonInverterValues.VAC.source = 'system'
                else:
                    self.CommonInverterValues.VAC.Value = 0
                    self.CommonInverterValues.VAC.Unit = 0
                    self.CommonInverterValues.VAC.source = 'NA'

                if 'IDC' in  json['Body']['Data']:
                    self.CommonInverterValues.IDC.Value = json['Body']['Data']['IDC']['Value']
                    self.CommonInverterValues.IDC.Unit = json['Body']['Data']['IDC']['Unit']
                    self.CommonInverterValues.IDC.source = 'system'
                else:
                    self.CommonInverterValues.IDC.Value = 0
                    self.CommonInverterValues.IDC.Unit = 0
                    self.CommonInverterValues.IDC.source = 'NA'

                if 'UDC' in  json['Body']['Data']:
                    self.CommonInverterValues.VDC.Value = json['Body']['Data']['UDC']['Value']
                    self.CommonInverterValues.VDC.Unit = json['Body']['Data']['UDC']['Unit']
                    self.CommonInverterValues.VDC.source = 'system'
                else:
                    self.CommonInverterValues.VDC.Value = 0
                    self.CommonInverterValues.VDC.Unit = 0
                    self.CommonInverterValues.VDC.source = 'NA'

                if 'DAY_ENERGY' in  json['Body']['Data']:
                    self.CommonInverterValues.Day_Energy.Value = json['Body']['Data']['DAY_ENERGY']['Value']
                    self.CommonInverterValues.Day_Energy.Unit = json['Body']['Data']['DAY_ENERGY']['Unit']
                    self.CommonInverterValues.Day_Energy.source = 'system'
                else:
                    self.CommonInverterValues.Day_Energy.Value = 0
                    self.CommonInverterValues.Day_Energy.Unit = 0
                    self.CommonInverterValues.Day_Energy.source = 'NA'

                if 'YEAR_ENERGY' in  json['Body']['Data']:
                    self.CommonInverterValues.Year_Energy.Value = json['Body']['Data']['YEAR_ENERGY']['Value']
                    self.CommonInverterValues.Year_Energy.Unit = json['Body']['Data']['YEAR_ENERGY']['Unit']
                    self.CommonInverterValues.Year_Energy.source = 'system'
                else:
                    self.CommonInverterValues.Year_Energy.Value = 0
                    self.CommonInverterValues.Year_Energy.Unit = 0
                    self.CommonInverterValues.Year_Energy.source = 'NA'

                if 'TOTAL_ENERGY' in  json['Body']['Data']:
                    self.CommonInverterValues.Total_Energy.Value = json['Body']['Data']['TOTAL_ENERGY']['Value']
                    self.CommonInverterValues.Total_Energy.Unit = json['Body']['Data']['TOTAL_ENERGY']['Unit']
                    self.CommonInverterValues.Total_Energy.source = 'system'
                else:
                    self.CommonInverterValues.Total_Energy.Value = 0
                    self.CommonInverterValues.Total_Energy.Unit = 0
                    self.CommonInverterValues.Total_Energy.source = 'NA'

                if 'DeviceStatus' in  json['Body']['Data']:
                    self.CommonInverterValues.DeviceStatus.ErrorCode = json['Body']['Data']['DeviceStatus']['ErrorCode']
                    self.CommonInverterValues.DeviceStatus.LEDColor = json['Body']['Data']['DeviceStatus']['LEDColor']
                    self.CommonInverterValues.DeviceStatus.LEDState = json['Body']['Data']['DeviceStatus']['LEDState']
                    self.CommonInverterValues.DeviceStatus.MgmtTimerRemainingTime = json['Body']['Data']['DeviceStatus']['MgmtTimerRemainingTime']
                    self.CommonInverterValues.DeviceStatus.StateToReset = json['Body']['Data']['DeviceStatus']['StateToReset']
                    self.CommonInverterValues.DeviceStatus.StatusCode = json['Body']['Data']['DeviceStatus']['StatusCode']
            except KeyError:
                raise ValueError('[{url}] Expected JSON KEY not available.  No Data Returned:'.format(url = url))
            except:
                raise ValueError('Something went wrong - _GetInverterRealtimeData')


        elif DataCollection == '3PInverterData' and self.UnitStatus.code == 0:
            try:
                if 'IAC_L1' in  json['Body']['Data']:
                    self.ThreePhaseinverterValues.IAC_L1.Value = json['Body']['Data']['IAC_L1']['Value']
                    self.ThreePhaseinverterValues.IAC_L1.Unit = json['Body']['Data']['IAC_L1']['Unit']
                    self.ThreePhaseinverterValues.IAC_L1.source = 'system'
                else:
                    self.ThreePhaseinverterValues.IAC_L1.Value = 0
                    self.ThreePhaseinverterValues.IAC_L1.Unit = 0
                    self.ThreePhaseinverterValues.IAC_L1.source = 'NA'

                if 'IAC_L2' in  json['Body']['Data']:
                    self.ThreePhaseinverterValues.IAC_L2.Value = json['Body']['Data']['IAC_L2']['Value']
                    self.ThreePhaseinverterValues.IAC_L2.Unit = json['Body']['Data']['IAC_L2']['Unit']
                    self.ThreePhaseinverterValues.IAC_L2.source = 'system'
                else:
                    self.ThreePhaseinverterValues.IAC_L2.Value = 0
                    self.ThreePhaseinverterValues.IAC_L2.Unit = 0
                    self.ThreePhaseinverterValues.IAC_L2.source = 'NA'

                if 'IAC_L3' in  json['Body']['Data']:
                    self.ThreePhaseinverterValues.IAC_L3.Value = json['Body']['Data']['IAC_L3']['Value']
                    self.ThreePhaseinverterValues.IAC_L3.Unit = json['Body']['Data']['IAC_L3']['Unit']
                    self.ThreePhaseinverterValues.IAC_L3.source = 'system'
                else:
                    self.ThreePhaseinverterValues.IAC_L3.Value = 0
                    self.ThreePhaseinverterValues.IAC_L3.Unit = 0
                    self.ThreePhaseinverterValues.IAC_L3.source = 'NA'

                if 'UAC_L1' in  json['Body']['Data']:
                    self.ThreePhaseinverterValues.VAC_PH1.Value = json['Body']['Data']['UAC_L1']['Value']
                    self.ThreePhaseinverterValues.VAC_PH1.Unit = json['Body']['Data']['UAC_L1']['Unit']
                    self.ThreePhaseinverterValues.VAC_PH1.source = 'system'
                else:
                    self.ThreePhaseinverterValues.VAC_PH1.Value = 0
                    self.ThreePhaseinverterValues.VAC_PH1.Unit = 0
                    self.ThreePhaseinverterValues.VAC_PH1.source = 'NA'

                if 'UAC_L2' in  json['Body']['Data']:
                    self.ThreePhaseinverterValues.VAC_PH2.Value = json['Body']['Data']['UAC_L2']['Value']
                    self.ThreePhaseinverterValues.VAC_PH2.Unit = json['Body']['Data']['UAC_L2']['Unit']
                    self.ThreePhaseinverterValues.VAC_PH2.source = 'system'
                else:
                    self.ThreePhaseinverterValues.VAC_PH2.Value = 0
                    self.ThreePhaseinverterValues.VAC_PH2.Unit = 0
                    self.ThreePhaseinverterValues.VAC_PH2.source = 'NA'

                if 'UAC_L3' in  json['Body']['Data']:
                    self.ThreePhaseinverterValues.VAC_PH3.Value = json['Body']['Data']['UAC_L3']['Value']
                    self.ThreePhaseinverterValues.VAC_PH3.Unit = json['Body']['Data']['UAC_L3']['Unit']
                    self.ThreePhaseinverterValues.VAC_PH3.source = 'system'
                else:
                    self.ThreePhaseinverterValues.VAC_PH3.Value = 0
                    self.ThreePhaseinverterValues.VAC_PH3.Unit = 0
                    self.ThreePhaseinverterValues.VAC_PH3.source = 'NA'

                if 'T_Ambient' in  json['Body']['Data']:
                    self.ThreePhaseinverterValues.T_Ambient.Value = json['Body']['Data']['T_Ambient']['Value']
                    self.ThreePhaseinverterValues.T_Ambient.Unit = json['Body']['Data']['T_Ambient']['Unit']
                    self.ThreePhaseinverterValues.T_Ambient.source = 'system'
                else:
                    self.ThreePhaseinverterValues.T_Ambient.Value = 0
                    self.ThreePhaseinverterValues.T_Ambient.Unit = 0
                    self.ThreePhaseinverterValues.T_Ambient.source = 'NA'

                if 'Rotation_Speed_Fan_FR' in  json['Body']['Data']:
                    self.ThreePhaseinverterValues.Rotation_Speed_Fan_FR.Value = json['Body']['Data']['Rotation_Speed_Fan_FR']['Value']
                    self.ThreePhaseinverterValues.Rotation_Speed_Fan_FR.Unit = json['Body']['Data']['Rotation_Speed_Fan_FR']['Unit']
                    self.ThreePhaseinverterValues.Rotation_Speed_Fan_FR.source = 'system'
                else:
                    self.ThreePhaseinverterValues.Rotation_Speed_Fan_FR.Value = 0
                    self.ThreePhaseinverterValues.Rotation_Speed_Fan_FR.Unit = 0
                    self.ThreePhaseinverterValues.Rotation_Speed_Fan_FR.source = 'NA'

                if 'Rotation_Speed_Fan_FL' in  json['Body']['Data']:
                    self.ThreePhaseinverterValues.Rotation_Speed_Fan_FL.Value = json['Body']['Data']['Rotation_Speed_Fan_FL']['Value']
                    self.ThreePhaseinverterValues.Rotation_Speed_Fan_FL.Unit = json['Body']['Data']['Rotation_Speed_Fan_FL']['Unit']
                    self.ThreePhaseinverterValues.Rotation_Speed_Fan_FL.source = 'system'
                else:
                    self.ThreePhaseinverterValues.Rotation_Speed_Fan_FL.Value = 0
                    self.ThreePhaseinverterValues.Rotation_Speed_Fan_FL.Unit = 0
                    self.ThreePhaseinverterValues.Rotation_Speed_Fan_FL.source = 'NA'

                if 'Rotation_Speed_Fan_BR' in  json['Body']['Data']:
                    self.ThreePhaseinverterValues.Rotation_Speed_Fan_BR.Value = json['Body']['Data']['Rotation_Speed_Fan_BR']['Value']
                    self.ThreePhaseinverterValues.Rotation_Speed_Fan_BR.Unit = json['Body']['Data']['Rotation_Speed_Fan_BR']['Unit']
                    self.ThreePhaseinverterValues.Rotation_Speed_Fan_BR.source = 'system'
                else:
                    self.ThreePhaseinverterValues.Rotation_Speed_Fan_BR.Value = 0
                    self.ThreePhaseinverterValues.Rotation_Speed_Fan_BR.Unit = 0
                    self.ThreePhaseinverterValues.Rotation_Speed_Fan_BR.source = 'NA'

                if 'Rotation_Speed_Fan_BL' in  json['Body']['Data']:
                    self.ThreePhaseinverterValues.Rotation_Speed_Fan_BL.Value = json['Body']['Data']['Rotation_Speed_Fan_BL']['Value']
                    self.ThreePhaseinverterValues.Rotation_Speed_Fan_BL.Unit = json['Body']['Data']['Rotation_Speed_Fan_BL']['Unit']
                    self.ThreePhaseinverterValues.Rotation_Speed_Fan_BL.source = 'system'
                else:
                    self.ThreePhaseinverterValues.Rotation_Speed_Fan_BL.Value = 0
                    self.ThreePhaseinverterValues.Rotation_Speed_Fan_BL.Unit = 0
                    self.ThreePhaseinverterValues.Rotation_Speed_Fan_BL.source = 'NA'
            except KeyError:
                raise ValueError('[{url}] Expected JSON KEY not available.  No Data Returned:'.format(url = url))
            except:
                raise ValueError('Something went wrong - _GetInverterRealtimeData')

        elif DataCollection == 'MinMaxInverterData' and self.UnitStatus.code == 0:
            #TODO :  Need to obtain an inverter that returns MinMax data
            try:
                self.MinMaxInverterDatavalues.Day_PMAX = json['Body']['Data']['DAY_PMAX']['Value']
                self.MinMaxInverterDatavalues.Day_VACMAX = json['Body']['Data']['DAY_UACMAX']['Value']
                self.MinMaxInverterDatavalues.Day_VACMNIN = json['Body']['Data']['DAY_UACMNIN']['Value']
                self.MinMaxInverterDatavalues.Day_VDCMax = json['Body']['Data']['DAY_UDCMax']['Value']
                #
                self.MinMaxInverterDatavalues.Year_PMAX = json['Body']['Data']['YEAR_PMAX']['Value']
                self.MinMaxInverterDatavalues.Year_VACMAX = json['Body']['Data']['YEAR_UACMAX']['Value']
                self.MinMaxInverterDatavalues.Year_VACMNIN = json['Body']['Data']['YEAR_UACMNIN']['Value']
                self.MinMaxInverterDatavalues.Year_VDCMax = json['Body']['Data']['YEAR_UDCMax']['Value']
                #
                self.MinMaxInverterDatavalues.Total_PMAX = json['Body']['Data']['TOTAL_PMAX']['Value']
                self.MinMaxInverterDatavalues.Total_VACMAX = json['Body']['Data']['TOTAL_UACMAX']['Value']
                self.MinMaxInverterDatavalues.Total_VACMNIN = json['Body']['Data']['TOTAL_UACMNIN']['Value']
                self.MinMaxInverterDatavalues.Total_VDCMax = json['Body']['Data']['TOTAL_UDCMax']['Value']
            except KeyError:
                raise ValueError('[!] [{url}] Excepcted JSON Data not returned:'.format(url = url))
            except:
                raise ValueError('Something went wrong - _GetInverterRealtimeData')
        else:
            return False
        return True


    #-------------------------------------------------------------------------------------------------------------------
    def _getPowerFlowRealtimeData(self):
        """

        :return:
        """
        url = "{protocol}://{host}/{baseurl}/GetPowerFlowRealtimeData.fcgi".format(protocol=self.protocol, host=self.host, baseurl=self.BaseURL)
        json = self._GetJSONData(url)

        if self.UnitStatus.code == 0:
            if 'BatteryStandby' in json['Body']['Data']['Site']:
                self.PowerFlowRealtimeSite.BatteryStandby = json['Body']['Data']['Site']['BatteryStandby']
            else:
                self.PowerFlowRealtimeSite.BatteryStandby = False

            if 'E_Day' in json['Body']['Data']['Site']:
                self.PowerFlowRealtimeSite.Energy_Day = json['Body']['Data']['Site']['E_Day']
            else:
                self.PowerFlowRealtimeSite.Energy_Day = False

            if 'E_Total' in json['Body']['Data']['Site']:
                self.PowerFlowRealtimeSite.Energy_Total = json['Body']['Data']['Site']['E_Total']
            else:
                self.PowerFlowRealtimeSite.Energy_Total = False

            if 'E_Year' in json['Body']['Data']['Site']:
                self.PowerFlowRealtimeSite.Energy_Year = json['Body']['Data']['Site']['E_Year']
            else:
                self.PowerFlowRealtimeSite.Energy_Year = False

            if 'Meter_Location' in json['Body']['Data']['Site']:
                self.PowerFlowRealtimeSite.Meter_Location = json['Body']['Data']['Site']['Meter_Location']
            else:
                self.PowerFlowRealtimeSite.Meter_Location = False

            if 'Mode' in json['Body']['Data']['Site']:
                self.PowerFlowRealtimeSite.Mode = json['Body']['Data']['Site']['Mode']
            else:
                self.PowerFlowRealtimeSite.Mode = False

            if 'P_Akku' in json['Body']['Data']['Site']:
                self.PowerFlowRealtimeSite.Power_Akku = json['Body']['Data']['Site']['P_Akku']
            else:
                self.PowerFlowRealtimeSite.Power_Akku = False

            if 'P_Grid' in json['Body']['Data']['Site']:
                self.PowerFlowRealtimeSite.Power_Grid = json['Body']['Data']['Site']['P_Grid']
            else:
                self.PowerFlowRealtimeSite.Power_Grid = False

            if 'P_Load' in json['Body']['Data']['Site']:
                self.PowerFlowRealtimeSite.Power_Load = json['Body']['Data']['Site']['P_Load']
            else:
                self.PowerFlowRealtimeSite.Power_Load = False

            if 'P_PV' in json['Body']['Data']['Site']:
                self.PowerFlowRealtimeSite.Power_PV = json['Body']['Data']['Site']['P_PV']
            else:
                self.PowerFlowRealtimeSite.Power_PV = False

            if 'rel_Autonomy' in json['Body']['Data']['Site']:
                self.PowerFlowRealtimeSite.Rel_Autonomy = json['Body']['Data']['Site']['rel_Autonomy']
            else:
                self.PowerFlowRealtimeSite.Rel_Autonomy = False

            if 'rel_SelfConsumption' in json['Body']['Data']['Site']:
                self.PowerFlowRealtimeSite.Rel_SelfConsumption  = json['Body']['Data']['Site']['rel_SelfConsumption']
            else:
                self.PowerFlowRealtimeSite.Rel_SelfConsumption = False

    #-------------------------------------------------------------------------------------------------------------------
    def _GetSensorRealtimeData(self, Scope=None, DeviceID=None, DataCollection=None):
        #TODO No sensors available on own system to test against.
        """

        :param Scope:
        :param DeviceID:
        :param DataCollection:
        :return:
        """

        if Scope is None:
            Scope = self.scope
        if DeviceID is None:
            DeviceID = self.DeviceID
        if DataCollection is None:
            DataCollection = 'NowSensorData'

        url = "{protocol}://{host}/{baseurl}/GetSensorRealtimeData.cgi?Scope={Scope}&DeviceID={DeviceID}&DataCollection={DataCollection}".format(protocol=self.protocol, host=self.host, baseurl=self.BaseURL, Scope=Scope, DeviceID=DeviceID, DataCollection=DataCollection)
        json = self._GetJSONData(url)
        # print(json)
        # print(url)

        #TODO

    #-------------------------------------------------------------------------------------------------------------------
    def _GetStringRealtimedata(self, Scope=None, DeviceID=None, DataCollection=None, TimePeriod=None):
        # TODO It's possible that this section is irrelevant and not needed for the purposes of data gathering.
        """

        :param Scope:
        :param DeviceID:
        :param DataCollection:
        :param TimePeriod:
        :return:
        """

        if Scope is None:
            Scope = self.scope
        if DeviceID is None:
            DeviceID = self.DeviceID
        if DataCollection is None:
            DataCollection = 'CurrentSumStringControlData'  # 'NowStringControlData', 'LastErrorStringControlData' or 'CurrentSumStringControlData'
        if TimePeriod is None:
            TimePeriod = "Total"

        url = "{protocol}://{host}/{baseurl}/GetStringRealtimeData.cgi?Scope={Scope}&DeviceID={DeviceID}&DataCollection={DataCollection}&TimePeriod={TimePeriod}".format(protocol=self.protocol, host=self.host, baseurl=self.BaseURL, Scope=Scope, DeviceID=DeviceID, DataCollection=DataCollection, TimePeriod=TimePeriod)
        json = self._GetJSONData(url)
        # print(url)
        # print(json)

        #TODO

    #-------------------------------------------------------------------------------------------------------------------
    def _GetActiveDeviceInfo(self, DeviceClass = None):
        """
        Collects a list of all devices connected to the system.
        :param string DeviceClass: Inverter | Storage | OhmPilot | SensorCard | StringControl | Meter | System
        :return:
        """
        #   TODO : this needs to be tested against a system with more than a single device on it to get some reasonable sense of the actual data returned.

        if DeviceClass is None:
            DeviceClass = "System"

        url = "{protocol}://{host}{baseurl}GetActiveDeviceInfo.cgi?DeviceClass={DeviceClass}".format(protocol=self.protocol, host=self.host, baseurl=self.BaseURL, DeviceClass=DeviceClass)
        json = self._GetJSONData(url)

        #TODO Process this data


    #-------------------------------------------------------------------------------------------------------------------
    def _GetMeterRealtimeData(self, Scope = None, DeviceID = None):
        """

        :param Scope:
        :param DeviceID:
        :return:
        """

        if Scope is None:
            Scope = self.scope
        if DeviceID is None:
            DeviceID = self.DeviceID

        url = "{protocol}://{host}/{baseurl}/GetMeterRealtimeData.cgi?Scope={Scope}&DeviceID={DeviceID}".format(protocol=self.protocol, host=self.host, baseurl=self.BaseURL, Scope=Scope, DeviceID=DeviceID)
        json = self._GetJSONData(url)

        # print(self.UnitStatus.code)
        #
        # print(url)
        # print(json)

        if self.UnitStatus.code == 0:
            try:
                self.MeterReatlTimeData.Manufacturer = json['Body']['Data']['Details']['Manufacturer']
                self.MeterReatlTimeData.Model = json['Body']['Data']['Details']['Model']
                self.MeterReatlTimeData.Serial = json['Body']['Data']['Details']['Serial']
                self.MeterReatlTimeData.Current_AC_Phase_1 = json['Body']['Data']['Current_AC_Phase_1']
                self.MeterReatlTimeData.Current_AC_Phase_2 = json['Body']['Data']['Current_AC_Phase_2']
                self.MeterReatlTimeData.Current_AC_Phase_3 = json['Body']['Data']['Current_AC_Phase_3']
                self.MeterReatlTimeData.Details = json['Body']['Data']['Details']
                self.MeterReatlTimeData.Enable = json['Body']['Data']['Enable']
                self.MeterReatlTimeData.EnergyReactive_VArAC_Sum_Consumed = json['Body']['Data']['EnergyReactive_VArAC_Sum_Consumed']
                self.MeterReatlTimeData.EnergyReactive_VArAC_Sum_Produced = json['Body']['Data']['EnergyReactive_VArAC_Sum_Produced']
                self.MeterReatlTimeData.EnergyReal_WAC_Minus_Absolute = json['Body']['Data']['EnergyReal_WAC_Minus_Absolute']
                self.MeterReatlTimeData.EnergyReal_WAC_Plus_Absolute = json['Body']['Data']['EnergyReal_WAC_Plus_Absolute']
                self.MeterReatlTimeData.EnergyReal_WAC_Sum_Consumed = json['Body']['Data']['EnergyReal_WAC_Sum_Consumed']
                self.MeterReatlTimeData.EnergyReal_WAC_Sum_Produced = json['Body']['Data']['EnergyReal_WAC_Sum_Produced']
                self.MeterReatlTimeData.Frequency_Phase_Average = json['Body']['Data']['Frequency_Phase_Average']
                self.MeterReatlTimeData.Meter_Location_Current = json['Body']['Data']['Meter_Location_Current']
                self.MeterReatlTimeData.PowerApparent_S_Phase_1 = json['Body']['Data']['PowerApparent_S_Phase_1']
                self.MeterReatlTimeData.PowerApparent_S_Phase_2 = json['Body']['Data']['PowerApparent_S_Phase_2']
                self.MeterReatlTimeData.PowerApparent_S_Phase_3 = json['Body']['Data']['PowerApparent_S_Phase_3']
                self.MeterReatlTimeData.PowerApparent_S_Sum = json['Body']['Data']['PowerApparent_S_Sum']
                self.MeterReatlTimeData.PowerFactor_Phase_1 = json['Body']['Data']['PowerFactor_Phase_1']
                self.MeterReatlTimeData.PowerFactor_Phase_2 = json['Body']['Data']['PowerFactor_Phase_2']
                self.MeterReatlTimeData.PowerFactor_Phase_3 = json['Body']['Data']['PowerFactor_Phase_3']
                self.MeterReatlTimeData.PowerFactor_Sum = json['Body']['Data']['PowerFactor_Sum']
                self.MeterReatlTimeData.PowerReactive_Q_Phase_1 = json['Body']['Data']['PowerReactive_Q_Phase_1']
                self.MeterReatlTimeData.PowerReactive_Q_Phase_2 = json['Body']['Data']['PowerReactive_Q_Phase_2']
                self.MeterReatlTimeData.PowerReactive_Q_Phase_3 = json['Body']['Data']['PowerReactive_Q_Phase_3']
                self.MeterReatlTimeData.PowerReactive_Q_Sum = json['Body']['Data']['PowerReactive_Q_Sum']
                self.MeterReatlTimeData.PowerReal_P_Phase_1 = json['Body']['Data']['PowerReal_P_Phase_1']
                self.MeterReatlTimeData.PowerReal_P_Phase_2 = json['Body']['Data']['PowerReal_P_Phase_2']
                self.MeterReatlTimeData.PowerReal_P_Phase_3 = json['Body']['Data']['PowerReal_P_Phase_3']
                self.MeterReatlTimeData.PowerReal_P_Sum = json['Body']['Data']['PowerReal_P_Sum']
                self.MeterReatlTimeData.TimeStamp = json['Body']['Data']['TimeStamp']
                self.MeterReatlTimeData.Visible = json['Body']['Data']['Visible']
                self.MeterReatlTimeData.Voltage_AC_PhaseToPhase_12 = json['Body']['Data']['Voltage_AC_PhaseToPhase_12']
                self.MeterReatlTimeData.Voltage_AC_PhaseToPhase_23 = json['Body']['Data']['Voltage_AC_PhaseToPhase_23']
                self.MeterReatlTimeData.Voltage_AC_PhaseToPhase_31 = json['Body']['Data']['Voltage_AC_PhaseToPhase_31']
                self.MeterReatlTimeData.Voltage_AC_Phase_1 = json['Body']['Data']['Voltage_AC_Phase_1']
                self.MeterReatlTimeData.Voltage_AC_Phase_2 = json['Body']['Data']['Voltage_AC_Phase_2']
                self.MeterReatlTimeData.Voltage_AC_Phase_3 = json['Body']['Data']['Voltage_AC_Phase_3']

            except Exception as err:
                print(err)
                #Lets just ignore the error shall we,  and let it all fall apart

    #-------------------------------------------------------------------------------------------------------------------
    def _GetStorageRealtimeData(self, Scope, DeviceID):
        #TODO   Need to test against a system with storage
        """
        NOTE:  this section is not implemented.   No storage device to test against.


        :param Scope:
        :param DeviceID:
        :return:
        """
        url = "{protocol}://{host}/{baseurl}/GetStorageRealtimeData.cgi?Scope={Scope}&DeviceID={DeviceID}".format(protocol=self.protocol, host=self.host, baseurl=self.BaseURL, Scope=Scope, DeviceID=DeviceID)
        json = self._GetJSONData(url)
        # TODO Process this data

    #-------------------------------------------------------------------------------------------------------------------
    def _getOhmPilotRealtimeData(self, Scope, DeviceID):
        """

        :param Scope:
        :param DeviceID:
        :return:
        """
        url = "{protocol}://{host}/{baseurl}/GetOhmPilotRealtimeData.cgi?Scope={Scope}&DeviceID={DeviceID}".format(protocol=self.protocol, host=self.host, baseurl=self.BaseURL, Scope=Scope, DeviceID=DeviceID)
        json = self._GetJSONData(url)

        #TODO

    #-------------------------------------------------------------------------------------------------------------------
    def _getGetArchiveData(self, Scope = None, SeriesType = 'Detail', HumanReadable = True, StartDate = None, EndDate = None, Channel = None, DeviceClass = None, DeviceID = '0'):
        #TODO Not Implemented yet.  Needs lots of work.  Will come back to this once all the simpler methods are done.  This might be simpler then.
        """
        :param Scope:
        :param SeriesType:
        :param HumanReadable:
        :param StartDate:
        :param EndDate:
        :param Channel:
        :param DeviceClass:
        :param DeviceID:
        :return:
        """
        if StartDate == None:
            StartDate = datetime.date.today() - datetime.timedelta(days=15)
        if EndDate == None:
            EndDate = datetime.date.today()

        url = ("{protocol}://{host}/{baseurl}/GetArchiveData.cgi?Scope={Scope}&SeriesType={SeriesType}&HumanReadable={HumanReadable}&StartDate={StartDate}&EndDate={EndDate}&Channel={Channel}&DeviceClass={DeviceClass}&DeviceID={DeviceID}"
               .format(protocol=self.protocol, host=self.host, baseurl=self.BaseURL, Scope = Scope, SeriesType=SeriesType,HumanReadable=HumanReadable, StartDate=StartDate, EndDate = EndDate, Channel=Channel, DeviceClass=DeviceClass, DeviceID=DeviceID))
        json = self._GetJSONData(url)


#-----------------------------------------------------------------------------------------------------------------------
if __name__ == "__main__":
    """
    This is used for part of the manual testing of the module during development
    """
    print("Testing the Data Aquisition from Fronius Symo Hybrid Solar Inverter")

    # print(messages.CRHErrorCodeFields)

    fronius = Fronius("10.0.3.250")
    # fronius._getInverterinfo()
    # fronius._getLoggerInfo()
    # fronius._getLoggerLEDinfo()
    # fronius._getPowerFlowRealtimeData()

    # print(fronius.CompatibilityRange)
    # print(fronius.BaseURL)
    # print(fronius.APIVersion)

    # print(fronius.ACPower)
    # print(fronius.Day_Energy)
    # print(fronius.ACPower)

    # fronius._GetGetArchiveData(Scope='System',Channel='EnergyReal_WAC_Sum_Produced',DeviceClass='Inverter',DeviceID='0')






