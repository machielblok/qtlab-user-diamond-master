'<ADbasic Header, Headerversion 001.001>
' Process_Number                 = 4
' Initial_Processdelay           = 1000
' Eventsource                    = Timer
' Control_long_Delays_for_Stop   = No
' Priority                       = High
' Version                        = 1
' ADbasic_Version                = 5.0.6
' Optimize                       = Yes
' Optimize_Level                 = 1
' Info_Last_Save                 = TUD276629  TUD276629\localadmin
'<Header End>
#INCLUDE ADwinPro_All.inc
#INCLUDE configuration.inc
DIM channel, set AS LONG

INIT:
  P2_Digprog(DIO_MODULE, PAR_63)   'configure DIO-16 to DIO 31 as outputs, the rest are inputs
  channel=PAR_61    'Number of DIO to set 
  set=PAR_62        'can be 1 or 0
EVENT:

  DIGOUT(DIO_Module,channel, set)   'This sets the digital output with channelnr to the value given by set
   
  END   
