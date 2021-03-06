import time
import qt
import data
import gobject
import msvcrt


# measurement parameters
start_v = -1.0
stop_v = -2.5
steps = 2501
pxtime = 50  #ms
do_smooth = True
green_during = 0.e-6
green_before = 300e-6
red_during= 8e-9
f_offset = 470400 # GHz
mw = True
mw_power = 15
mw_frq = 2.8578e9 #2.878e9
dataname = 'Laserscan_sil9_LT2_MW_0uW_green'
LT2 = True

# end measurement parameters

# This version of laserscan now includes an abort function. To abort the laser
# scan, press 'q'.

def power_ok():
    if mw_power > 0:
        proceed = 0
        max_idx = 30
        while proceed == 0:
            print 'Warning: power > 0, hit c to continue' 
            qt.msleep(1)
            idx += idx + 1
            if idx > max_idx:
                proceed = 1
                print 'No key stroke detected, quiting laser scan'
                ret = False
            if msvcrt.kbhit() and msvcrt.getch() = "q":
                proceed = 1
                print 'Quiting laser scan'
                ret = False
            if msvcrt.kbhit() and msvcrt.getch() = "c":
                proceed = 1
                print 'Continuing laser scan'
                ret = True
    return ret
#while c 

abort_check_time = 1000 #ms

def check_for_abort():
    if msvcrt.kbhit() and msvcrt.getch() == "q" : 
        ins_laser_scan.abort_scan()
        return False
    return True

def rolling_avg(xvals, length=10):
    new = zeros(len(xvals))
    for i,x in enumerate(xvals):
        _length = length
        if i < length:
            _length = i
        elif i > len(xvals)-length:
            _length = len(xvals)-i
        
        idxs = range(i-_length,i+_length)
        new[i] = sum([ xvals[idx] for idx in idxs ])/2./_length
    return new


if LT2:
    ins_adwin = qt.instruments['adwin']
    ins_laser_scan = qt.instruments['laser_scan']
    ins_mw = qt.instruments['SMB100']
else:
    ins_adwin = qt.instruments['adwin_lt1']
    ins_laser_scan = qt.instruments['laser_scan_lt1']
    ins_mw = qt.instruments['SMB_100_lt1']

ins_laser_scan.set_StartVoltage(start_v)
ins_laser_scan.set_StopVoltage(stop_v)
ins_laser_scan.set_ScanSteps(steps)
ins_laser_scan.set_IntegrationTime(pxtime)
ins_running = True
step = 0

#_before_voltages = ins_adwin.get_dac_voltages(['green_aom','newfocus_aom'])
#FIXME NEED A CONDITION FOR WHEN THE Newfocus IS ONE THE AWG.

if LT2:
    GreenAOM.set_power(green_before)
    qt.msleep(1)

    NewfocusAOM.set_power(red_during)
    GreenAOM.set_power(green_during)
else:
    GreenAOM_lt1.set_power(green_before)
    qt.msleep(1)

    NewfocusAOM_lt1.set_power(red_during)
    GreenAOM_lt1.set_power(green_during)




if mw:
    ins_mw.set_iq('off')
    ins_mw.set_pulm('off')
    ins_mw.set_power(mw_power)
    ins_mw.set_frequency(mw_frq)
    ins_mw.set_status('on')


qt.mstart()
qt.Data.set_filename_generator(data.DateTimeGenerator())
d = qt.Data(name=dataname)
d.add_coordinate('voltage [V]')
d.add_value('frequency [GHz]')
d.add_value('counts')
d.create_file()

p_f = qt.Plot2D(d, 'rO', name='frequency', coorddim=0, valdim=1, clear=True)
p_c = qt.Plot2D(d, 'bO', name='counts', coorddim=1, valdim=2, clear=True)

# go manually to initial position
ins_adwin.set_dac_voltage(('newfocus_frq',start_v))
qt.msleep(1)

ins_laser_scan.start_scan()
qt.msleep(1)
timer_id=gobject.timeout_add(abort_check_time,check_for_abort)

while(ins_running):
  
    ins_running = not ins_laser_scan.get_TraceFinished()
    
    _step = ins_laser_scan.get_CurrentStep()

    qt.msleep(0.3)

    if _step > step:
        _v = ins_laser_scan.get_voltages()[step:_step]
        _f = ins_laser_scan.get_frequencies()[step:_step] - f_offset
        _c = ins_laser_scan.get_counts()[step:_step]
       
        # print _v,_f,_c
        
        if len(_v) == 1:
            _v = _v[0]
            _f = _f[0]
            _c = _c[0]

        d.add_data_point(_v,_f,_c)
        step = _step
        p_f.update()
        p_c.update()

ins_laser_scan.end_scan()
gobject.source_remove(timer_id)
#ins_adwin.set_dac_voltage(['green_aom',_before_voltages[0]])
#ins_adwin.set_dac_voltage(['newfocus_aom',_before_voltages[1]])
if mw:
    ins_mw.set_status('off')

qt.mend()

if do_smooth:
    basepath = d.get_filepath()[:-4]
    ds = qt.Data()
    ds.set_filename_generator(data.IncrementalGenerator(basepath))
    ds.add_coordinate('voltage [V]')
    ds.add_value('smoothed frequency [GHz]')
    ds.add_value('counts')
    ds.create_file()

    p_fs = qt.Plot2D(ds, 'rO', name='frequency smoothed', coorddim=0, valdim=1, clear=True)
    p_cs = qt.Plot2D(ds, 'bO', name='counts smoothed', coorddim=1, valdim=2, clear=True)
     
    ds.add_data_point(d.get_data()[:,0], rolling_avg(d.get_data()[:,1]), 
            d.get_data()[:,2])
    ds.close_file()
    p_fs.save_png()
    p_cs.save_png()
else:
    p_f.save_png()
    p_c.save_png()

d.close_file()

qt.Data.set_filename_generator(data.DateTimeGenerator())


if LT2:
    MatisseAOM.set_power(0)
    NewfocusAOM.set_power(0)
    GreenAOM.set_power(green_before)
else:
    MatisseAOM_lt1.set_power(0)
    NewfocusAOM_lt1.set_power(0)
    GreenAOM_lt1.set_power(green_before)
