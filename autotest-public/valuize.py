import numbers

# We analyze lists only up to a maximum length.
MAX_ANALYSIS_LEN = 20

def str_to_float(s):
    """Converts a string to a float."""
    t = 0.0
    for c in reversed(s):
        i = max(0, min(127, ord(c)))
        t = (i + t) / 128.0
    return t

def valuize(d, prefix, ob, refs=None):
    """Produces a dictionary string --> float describing an object ob.  
    The dictionary entries are added to an existing dictionary d, passed as input. 
    prefix is a string prefix used as a prefix for all dictionary entries."""
    # TODO: numpy array??
    refs = refs or set()
    if ob is None:
        d[prefix] = -1.0
    elif isinstance(ob, numbers.Number):
        if isinstance(ob, numbers.Integral) or isinstance(ob, numbers.Real):
            d[prefix] = float(ob)
        elif isinstance(ob, numbers.Complex):
            d[prefix + '.real'] = ob.real
            d[prefix + '.imag'] = ob.imag
        else:
            d[prefix] = float(ob)
    elif isinstance(ob, basestring):
        d['hash(%s)' % prefix] = str_to_float(ob)
        d['len(%s)' % prefix] = len(ob)
    elif isinstance(ob, dict):
        if not id(ob) in refs:
            refs.add(id(ob))
            for k, v in ob.items():
                # Hmm, should I do something better here to distinguish the number 0
                # from the string '0'? 
                valuize(d, (prefix + '.' if prefix else '') + str(k), v, refs=refs)
            if prefix:
                d['len(%s)' % prefix] = len(ob)
    elif isinstance(ob, list) or isinstance(ob, tuple):
        if not id(ob) in refs:
            refs.add(id(ob))
            for i, v in enumerate(ob[:MAX_ANALYSIS_LEN]):
                valuize(d, prefix + '[%d]' % i, v, refs=refs)
            d['len(%s)' % prefix] = len(ob)
    elif isinstance(ob, set):
        if not id(ob) in refs:
            refs.add(id(ob))
            # Not sure what best to do.
            d['len(%s)' % prefix] = len(ob)
    elif hasattr(ob, '__dict__'):
        if not id(ob) in refs:
            refs.add(id(ob))
            valuize(d, prefix, ob.__dict__)
    else:
        # Boh?
        pass

            
if __name__ == '__main__':

    class A(object):
        def __init__(self):
            self.x = 0
            self.y = "hello"
        
    a = A()
    
    b = [3, 4, 5, 6]
    
    c = dict(x=1, y=2, z="sushi")

    d = {}
    valuize(d, 'a', a)
    print d
    
    d = {}
    valuize(d, 'b', b)
    print d
    
    d = {}
    valuize(d, 'c', c)
    print d
