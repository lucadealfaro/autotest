def rebalance(stocks, amount):
    n = len(stocks)
    fraction = amount/n
    shares = {}
    for symbol in stocks:
        shares[symbol] = int(fraction/stocks[symbol])
    return shares

def debug(x):
    print x
    return 1.0

import autotest
import stat_engine
# import func_engine
# autotest.testall(engines=[func_engine.FuncEngine])
autotest.testall(engines=[stat_engine.StatEngine])
