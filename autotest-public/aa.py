from c import f, g, A, B
import random


def main():
    for k in range(10): print f(g(k))
    print A().h(8)
    # Real test.
    bobj = B()
    for k in range(10000):
        x = random.random()
        y = bobj.h(x)

main()
