def f(x):
    return 2 * x

def g(x):
    return f(x+2)

class A(object):
    def h(self, x):
        self.y = x
        return x * 3


class B(object):
    def __init__(self):
        self.n = 0
        self.a = A()
        
    def h(self, x):
        if self.n < 1000:
            self.y = self.a.h(x)
            return self.y
        else:
            # Simulates something changing.
            self.y = -x
            return x / 3.0
        

import stat_engine
import autotest
autotest.testall(engines=[stat_engine.StatEngine])


