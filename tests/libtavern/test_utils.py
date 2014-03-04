import libtavern.utils
from nose.tools import *

@istest
def gettime():
    # Create timestamp string
    ts = '1393872171.558932'
    eq_(libtavern.utils.gettime(timestamp=ts,format='timestamp'),1393872171)
