import HTMLCyclops

import types, sys, string
from os import path

""" This module runs Tim Peter's Cyclops cycle finder on a module given as
    a command line parameter. It was subclassed to provide browsable HTML.
    
    Please comment out lines to avoid running certain sub reports.
    See comments in the code further down.

"""

def mod_refs(x):
    return x.__dict__.values()

def mod_tag(x, i):
    return "." + x.__dict__.keys()[i]

def func_refs(x):
    return x.func_globals, x.func_defaults

def func_tag(x, i):
    return (".func_globals", ".func_defaults")[i]

def instance_filter(cycle):
    for obj, index in cycle:
        if type(obj) is types.InstanceType:
            return 1
    return 0

def run():
    mod_name = path.splitext(sys.argv[1])[0]
    print 'MOD_NAME', mod_name
    # remove command line option
    del sys.argv[1]
    f = open(mod_name+'.cycles', 'w')
    sys.path.append('.')
    try: 
        z = HTMLCyclops.CycleFinderHTML()
        mod = __import__(mod_name)
    
        # Comment out any of the following lines to not add a chaser or filter
        z.chase_type(types.ModuleType, mod_refs, mod_tag)
        z.chase_type(types.FunctionType, func_refs, func_tag)
        z.install_cycle_filter(instance_filter)
    
        # Execute the module and trace the first round of cycles
        try:
            z.run(mod.main)
        except:
            import traceback
            
            tp, vl, tb = sys.exc_info()
            err = '<font color="#FF4444"><h3>Error:</h3></font>'+\
              string.join(traceback.format_exception(tp, vl, tb), '<br>')
            f.write(err)
            
        z.find_cycles()
    
        # Comment out any of the following lines to not show a certain section
        # of the report.
        z.show_stats(z.stats_list())        # Statistics
        z.show_cycles()               # All cycles  
        z.show_cycleobjs()            # Objects involved in cycles
        z.show_sccs()                 # Cycle objects partitioned into maximal SCCs
        z.show_arcs()                 # Arc types involved in cycles
        z.iterate_til_steady_state(show_objs=0) # Repeatedly purge until there are no more dead roots
        
        # Write out the report
        f.write(z.get_page())
    finally:
        f.close()
        

run()





