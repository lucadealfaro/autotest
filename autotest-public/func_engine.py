import autotest
import glob
import imp
import json
import math
import os
import cPickle as pickle
import hashlib
import sys
import subprocess
from loggers import DefaultLogger

# This engine checks the functional invariance of the code behavior.

def serialize(obj):
    """
    given an obj(ect) returns a string s such that eval(s) == obj
    tries s = repr(obj) and s = pickle. if none works raises an exception
    """
    serial = repr(obj)
    try:
        if eval(serial) == obj:
            return serial
    except:
        pass
    try:
        serial = pickle.dumps(obj)
        return 'pickle.loads(%s)' % repr(serial)
    except:
        raise Exception #unable to serialize


def prep(name):
    """
    converts 'one.two.three' in 'OneTwoThree'
    used to generate test class name from a module.function name
    """
    return ''.join(x.capitalize() for x in name.split('.'))


class FuncEngine(autotest.ExampleEngine):
    """
        - if func is a regular function:

          output[0] == func(*input[0], **input[1])

        - if func is a method:

          output[0] == func(*input[0], **input[1]) # actual output
          output[1] == input[0][0].__dict__  # state of the obj after call

        if this is the first time the function is encountered with this
        input it generates a test to make sure the same output is
        produced by the same function and the same input in the future;

        if this is not the first time the function is encountered with this
        input, it compares the current output with the previous output.

        It retuns:
        - True if previous test found and passed
        - False if previous test found and not passed
        - None otherwise

        In case the test fails it also logs an error message to stderr and,
        if exit_on_error=True (default) it sys.exit(-1)

    """

    def __init__(self,
                 mfunc=None,
                 mclass=None,
                 mattr=None,
                 module=None,
                 max_tests=None,
                 exit_on_error=True,
                 logger=DefaultLogger(),
                 fname=None,
                 base_name='base',
                 class_name='class',
                 flat_function_name='flat_function',
                 qualified_function_name='qual_name',
                 switches=None):
        self.mfunc = mfunc
        self.mclass = mclass
        self.mattr = mattr
        self.module = module
        self.max_tests = max_tests
        self.exit_on_error = exit_on_error
        self.logger = logger
        self.fname = fname
        self.base_name = base_name
        self.class_name = class_name
        self.flat_function_name = flat_function_name
        self.qualified_function_name = qualified_function_name
        self.switches = switches or {}
        # How many tests have we already generated?
        self.test_counter = 0
        # Have we already checked all tests?
        self.has_run_tests = False

    def test(self, input, output):
        return

    def learn(self, input, output):
        if self.test_counter >= self.max_tests:
            # We have learned (created tests) as much as it is possible.
            return
        # Tries to serialize the input and output; does nothing if this does not work.
        try:
            serial_input = serialize(input)
            serial_output = serialize(output)
        except:
            return
        # hash the serialized input
        input_hash = hashlib.md5(serial_input).hexdigest()
        # if the filename is "path/to/filename.py" name_parts becomes ["path/to","autotest","filename"]
        # this is the filename associate to this autotest the name is generated as
        # "path/to/autotests/filename_<class>_<func>_<hash>.py"
        # This contains a test.  The test contains the serialization of the input and output.
        test_filename = self.base_name + '_' + self.flat_function_name + '_' + input_hash +'.py'
        test_exists = os.path.exists(test_filename)
        if test_exists:
            self.run_single_test(test_filename, output)
        if not test_exists and (self.test_counter < self.max_tests or self.max_tests is None):
            # We need to generate the test.
            self.test_counter += 1
            self._save_test(test_filename, self.module, self.class_name, self.qualified_function_name,
                           self.flat_function_name, serial_input, serial_output, self.mclass)

    def run_single_test(self, test_filename, output):
        module_name = 'tmp_'+test_filename.split(os.sep)[-1].rstrip('.py')
        foo = imp.load_source(module_name, test_filename)
        del sys.modules[module_name]
        if foo.OUTPUT != output and not self.qualified_function_name in self.switches:
            print 'test %s failed' % test_filename
            if self.exit_on_error:
                sys.exit(-1)

    def _save_test(self, test_filename, module, name_obj, name_method, fname, serial_input, serial_output, cls=False):
        """Saves a test, to be able to run it later."""
        dr = test_filename.rsplit(os.sep, 1)[0]
        if not os.path.exists(dr):
            os.makedirs(dr)
        with open(test_filename,'w') as test_file:
            w = test_file.write
            w('import unittest\n')
            w('import cPickle as pickle\n')
            w('import sys; sys.path.append(%s)\n' % repr(os.getcwd()))
            w('from %s import %s\n' % (module, name_obj))
            w('\n')
            w('INPUT = %s\n' % serial_input)
            w('\n')
            w('OUTPUT = %s\n' % serial_output)
            w('\n')
            w('class Test%sFunctions(unittest.TestCase):\n' % prep(module))
            w('    def test_%s(self):\n' % fname)
            w('        args, kwargs = INPUT\n')
            w('        func = %s\n' % name_method)
            w('        c = func(*args, **kwargs)\n')
            if cls:
                w('        obj = args[0]\n')
                w('        self.assertEqual(c,OUTPUT[0])\n')
                w('        self.assertEqual(obj.__dict__, OUTPUT[1])\n')
            else:
                w('        self.assertEqual(c,OUTPUT[0])\n')
            w('\n')
            w('if __name__ == "__main__": unittest.main()')

