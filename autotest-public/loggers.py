import logging
import urllib
import urllib2
import datetime

class DefaultLogger(object):
    def write(self, msg):
        print msg

class FileLogger(object):
    def __init__(self, filename):
        self.filename = filename
        self.file = open(filename,'w')
    def write(self, msg):
        self.file.write(msg.strip()+'\n')

import logging
class NetLogger(object):
    def __init__(self, url, realm='default'):
        self.url = url
        self.realm = realm
    def write(self, msg):
        data = urllib.urlencode({'msg':msg, 
                                 'realm':realm,
                                 'timestamp':datetime.datetime.now().isoformat()})
        return urllib2.urlopen(self.url, data).read()
