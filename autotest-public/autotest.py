import sys
import copy
import inspect
import os
from loggers import DefaultLogger
from switch import read_switches

MAX_TESTS = 10

class ExampleEngine(object):
    """
    example of a learning engine
    the input/output of autotest functions is passed to learner
    and then checked with the check function

    for regular functions
        input = (*a, **b)
        output = (f(*a,**b), None)
    for methods
        input = (*a, **b) where a[0] = self
        output = (f(*a,**b), self)
    """
    def __init__(self,
                 mfunc=None,
                 mclass=None,
                 mattr=None,
                 module=None,
                 max_tests=None,
                 logger=DefaultLogger(),
                 fname=None,
                 base_name='base',
                 class_name='class',
                 flat_function_name='flat_function',
                 qualified_function_name='qual_name'):
        self.mfunc = mfunc
        self.mclass = mclass
        self.mattr = mattr
        self.module = module
        self.max_tests = max_tests
        self.logger = logger
        self.fname = fname
        self.base_name = base_name
        self.class_name = class_name
        self.flat_function_name = flat_function_name
        self.qualified_function_name = qualified_function_name
        # How many tests have we already generated?
        self.test_counter = 0
        # Have we already checked all tests?
        self.has_run_tests = False

    def learn(self, input, output):
        """Learns the desired behavior."""
        pass

    def test(self, input, output):
        """Checks that the behavior is as desired."""
        pass

class autotest(object):
    """
    Class in charge of generating and running autotests.
    One object of this class will decorate each function or method.
    We have to pass one of two things:
    - Either mfunc, in which case we are instrumenting a function,
    - or mclass and mattr, which which case we are instrumenting attribute mattr
      of class mclass.
    """
    def __init__(self, max_tests=10, exit_on_error=True, logger=DefaultLogger(),
                 engines = [], mfunc=None, mclass=None, mattr=None):
        # Max number of test cases generated, propagated to the various engines.
        self.max_tests = max_tests
        # Exit if there is an error or continue execution
        self.exit_on_error = exit_on_error
        # Where to log the error?
        self.logger = logger
        # Engines for testing.
        self.engine_classes = engines

        # Builds the various file names associated with the function or method annotated.
        if mfunc is not None:
            # We have a function.
            self.cls = None
            # name of the module that contains the function
            self.module = mfunc.__module__
            # name of the function
            self.fname = mfunc.__name__
            # Names for files.
            self.class_name = self.flat_function_name = self.qualified_function_name = self.fname
        else:
            # We have a method.
            self.module = mclass.__module__
            self.cls = mclass
            self.fname = mattr
            self.cname = mclass.__name__
            self.class_name = self.cname
            self.flat_function_name = self.cname + '_' + self.fname
            self.qualified_function_name = self.cname + '.' + self.fname
        # Name of the file that defined the function
        filename = sys.modules[self.module].__file__
        name_parts = filename.rsplit('.',1)[0].rsplit(os.sep,1)
        name_parts.insert(-1,'autotests')
        # key is tuple that identified this function uniquely
        self.base_name = os.path.join(*name_parts)
        self.subdir_name = os.path.join(self.base_name, self.flat_function_name)

        # Initializes one test engine for each of the testers that it is given.
        self.engines = [e(mfunc=mfunc, # function, or ...
                          mclass=mclass, # ...class and
                          mattr=mattr, # module we are instrumenting.
                          module=self.module, # module we are instrumenting.
                          max_tests=max_tests,
                          exit_on_error=exit_on_error,
                          logger=logger,
                          fname=self.fname,
                          base_name=self.base_name,
                          class_name=self.class_name, # class/function name
                          flat_function_name=self.flat_function_name, # class + function name
                          qualified_function_name=self.qualified_function_name, # similar to above but not quite
                          switches=read_switches(self.module)
                          )
                        for e in self.engine_classes]


    def autotest_check(self, func, input, output):
        """
        given a func(tion) an input and an output,
        checks that the function satisfies all of the checkers.
        """        
        for engine in self.engines:
            self.logger.write("calling engine %s for %s.%s" % (engine.__class__.__name__, 
                                                               self.module,
                                                               self.qualified_function_name))
            engine.learn(input, output)
            engine.test(input, output)


    def __call__(self, func):
        """
        An instance of the autotest class can be used as a decorator.
        This is the decorator, it simply wraps the function so that
        autotest runs when the function is called.
        """
        def autotest_tmp(*a,**b):
            input = copy.deepcopy((a,b))
            output = func(*a,**b)
            if inspect.ismethod(func):
                output_and_state = (output, a[0].__dict__)
            else:
                output_and_state = (output, None)
            self.autotest_check(func, input, output_and_state)
            return output
        autotest_tmp.__name__ = func.__name__
        autotest_tmp.__module__ = func.__module__
        return autotest_tmp

def testall(max_tests=MAX_TESTS,
            exit_on_error=True,
            logger=DefaultLogger(),
            engines=None):
    """
    decorates with autotests all functions and methods defined
    in the same module where this function is called
    """
    import func_engine

    if engines is None:
        engines = [func_engine.FuncEngine]

    name = inspect.getmodule(inspect.stack()[1][0]).__name__
    members = inspect.getmembers(sys.modules[name])
    functions = filter(lambda item:inspect.isfunction(item[1]), members)
    classes = filter(lambda item:inspect.isclass(item[1]), members)
    # Find all functions and decorate them
    for key, func in functions:
        kwargs = dict(max_tests=max_tests,
                      exit_on_error=exit_on_error,
                      logger=logger,
                      engines=engines,
                      mfunc=func)
        setattr(sys.modules[name], key, autotest(**kwargs)(func))
    # Find all classes
    for key, cls in classes:
        # Find all methods of each class and decorate them
        for attr in cls.__dict__:
            # ignore class private methods
            if (inspect.ismethod(getattr(cls,attr)) and not attr.startswith('__')):
                kwargs = dict(max_tests=max_tests,
                              exit_on_error=exit_on_error,
                              logger=logger,
                              engines=engines,
                              mclass=cls, mattr=attr)
                setattr(cls,attr, autotest(**kwargs)(getattr(cls,attr)))

