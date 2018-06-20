import random

def f(x):
    #if random.random()<0.1: return 1000.0
    return 2*x

def g(x):
    f(4)
    return f(x+2)

class A(object):
    def h(self,x):
        self.y = x
        return x*3

import autotest
import stat_engine
import func_engine
# autotest.testall(engines=[func_engine.FuncEngine])
autotest.testall(engines=[stat_engine.StatEngine])

