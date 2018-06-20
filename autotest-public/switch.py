import os
import sys
import json

def switch(module, function, mode):
    mode = mode.lower()
    switches = read_switches(module)
    if mode == 'off':
        switches[function] = 'off'
    elif mode == 'on':
        if function in switches:
            del switches[function]
    else:
        try:
            switches[function] = float(mode)
        except:
            print 'unknown command'
    save_switches(module, switches)


def read_switches(module):
    filename = os.path.join('autotests',module,'switches.json')        
    if os.path.exists(filename):
        with open(filename) as myfile:
            switches = json.load(myfile)
    else:
        switches = {}
    return switches

def save_switches(module, switches):
    filename = os.path.join('autotests',module,'switches.json')        
    with open(filename, 'w') as myfile:
        json.dump(switches, myfile)

if __name__ == '__main__':
    switch(
        module = sys.argv[1],
        function = sys.argv[2],
        mode = sys.argv[3])
