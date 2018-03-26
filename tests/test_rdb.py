# coding=utf-8
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import rdb

def test_rdb(x, y):
    result = x + y
    rdb.set_trace()
    return result


if __name__ == '__main__':
    x, y = 1, 2
    result = test_rdb(x, y)
    print('{0} + {1} = {2}'.format(x, y, result))