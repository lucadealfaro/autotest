from nlib import *
import collections
import hashlib
import sys
from rebalance import rebalance, debug

# ignoring HOT and DEN

SYMBOLS = 'BEL,CHH,MYCC,STAY,HLT,H,IHG,LQ,LVS,MAR,MGM,RLH,SHO,WYN,XHR'.split(',')

def color(symbol):
    return '#'+hashlib.sha1(symbol).hexdigest()[:6].upper()

def fetch_data(symbols=SYMBOLS):
    d = PersistentDictionary('storage.sqlite')    
    for symbol in symbols:        
        if not symbol in d:
            print 'fetching',symbol
            stock = YStock(symbol)
            h = stock.historical()[-250:]
            d[symbol] = h
    return d

def find_splits(d):
    for symbol in d.keys():
        h = d[symbol]
        print symbol, h[0]['date']
        for k in range(len(h)-1,-1,-1):            
            day = h[k]
            if abs(day['adjusted_close'] - day['close']) > 0.10*day['close']:
                print symbol, day['date'], day['adjusted_close'], day['close'], 'split?'
                break

def daily_rebalance(d, amount=1000000):
    symbols = d.keys()
    ndays = len(d['HLT']) 
    amount = amount
    shares = {}
    series1 = collections.defaultdict(list)
    series2 = collections.defaultdict(list)
    for day in range(ndays):
        v = {symbol: d[symbol][day]['close'] for symbol in sorted(symbols)}
        amount = amount + sum(v[symbol]*shares[symbol] for symbol in shares)
        print day, d['HLT'][day]['date'], amount
        shares = rebalance(v, amount)
        amount = amount - sum(v[symbol]*shares[symbol] for symbol in shares)
        for symbol in sorted(symbols):
            series1[symbol].append((day, v[symbol]))
            series2[symbol].append((day, shares[symbol]))

    canvas1 = Canvas(title="Hotel Share Prices")
    for symbol in series1: canvas1.plot(series1[symbol], legend=symbol, color=color(symbol))
    canvas1.save('prices.png')
    canvas2 = Canvas(title="Hotel Portfolio Shares")
    for symbol in series2: canvas2.plot(series2[symbol], legend=symbol, color=color(symbol))
    canvas2.save('shares.png')

if __name__ == '__main__':
    
    d = fetch_data()
    [debug(float(i)) for i in range(1000)]
    # find_splits(d)    
    # daily_rebalance(d)
