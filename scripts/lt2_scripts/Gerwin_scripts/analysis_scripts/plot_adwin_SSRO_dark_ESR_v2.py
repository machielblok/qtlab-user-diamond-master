plt.close('all')


def num2str(num, precision): 
    return "%0.*f" % (precision, num)


def plot_SSRO_data(datapath, SSRO_duration = 20):
    ###########################################
    ######## MEASUREMENT SPECS ################
    ###########################################
    e = load(datapath+'\\dark_esr-1_statics_and_parameters.npz')
    mwpower = e['mw_power']
    mw_min_freq = e['min_mw_freq']
    mw_max_freq = e['max_mw_freq']
    noof_datapoints = e['noof_datapoints']


    ###########################################
    ######## SPIN RO  #########################
    ###########################################
    
    
    f = load(datapath+'\\dark_esr-0_Spin_RO.npz')
    raw_counts = f['counts']
    repetitions = f['sweep_axis']
    time = f['time']

    print f.keys()

    tot_size = len(repetitions)
    reps_per_point = tot_size/float(noof_datapoints)

    print reps_per_point
    
    idx = 0
    counts_during_readout = zeros(noof_datapoints)
    mw_freq = linspace(mw_min_freq,mw_max_freq,noof_datapoints)
    for k in arange(noof_datapoints):
        counts_during_readout[k] = raw_counts[k,:].sum()
        idx += 1
        print (idx)/float(noof_datapoints)

    figure1 = plt.figure(1)
    plt.plot(mw_freq,counts_during_readout, 'sk')
    plt.xlabel('MW length (ns)')
    plt.ylabel('Integrated counts')
    plt.title('MW frequency sweep, power = '+num2str(mwpower,0)+' dBm')
    plt.text(0.1*(mw_max_freq+mw_min_freq),max(counts_during_readout),datapath)
    figure1.savefig(datapath+'\\histogram_integrated.png')
    

    x = 6.0
    y = 8.0

    figure2 = plt.figure(figsize=(x,y))
    plt.pcolor(raw_counts, cmap = 'hot', edgecolors = None)
    plt.xlabel('Readout time (us)')
    plt.ylabel('MW repetition number')
    plt.title('Total histogram, integrated over repetitions')
    plt.colorbar()
    figure2.savefig(datapath+'\\histogram_counts_2d.png')


    f.close()
    ###########################################
    ######## CHARGE RO ########################
    ###########################################

    #g = load(datapath+'\\spin_control-0_ChargeRO_before.npz')
    #h = load(datapath+'\\spin_control-0_ChargeRO_after.npz')

    #g.close()
    #h.close()



    ###########################################
    ######## SPIN PUMPING #####################
    ###########################################
    v = load(datapath+'\\dark_esr-0_SP_histogram.npz')
    sp_counts = v['counts']
    sp_time = v['time']
    figure6 = plt.figure(6)
    plt.plot(sp_time,sp_counts,'sg')
    plt.xlabel('Time (ns)')
    plt.ylabel('Integrated counts')
    plt.title('Spin pumping')
    v.close()
        
plot_SSRO_data(r'D:\measuring\data\20120614\174735_dark_esr_SIL9', SSRO_duration = 20)
    



