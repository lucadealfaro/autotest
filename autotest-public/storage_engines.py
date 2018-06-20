import os

__all__ = ['FileStorageEngine']

try:
    from google.appengine.ext import ndb
    class AutotestFileStorage(ndb.Model):
        filename = ndb.StringProperty()
        data = ndb.BlobProperty()
    HAVE_NDB = True
except:
    HAVE_NDB = False

class FileStorageEngine(object):
    @staticmethod
    def read(filename):
        if os.path.exists(filename):
            with open(filename) as stream:
                return stream.read()
        else:
            return None
    @staticmethod
    def write(binary_data, filename):
        with open(filename, 'w')as stream:
            stream.write(binary_data)


class GAEStorageEngine(object):    
    @staticmethod
    def read(filename):
        return AutotestFileStorage.query(AutotestFileStorage.filename==filename).get()
    @staticmethod
    def write(binary_data, filename):
        AutotestFileStorage(filename=filename, data=binary_data).save()

if HAVE_NDB:
    FileStorageEngine = GAEStorageEngine
