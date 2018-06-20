import autotest
import json
import math
import os
import sys
import valuize
import json_plus
import numpy as np
import unittest
import storage_engines
from loggers import DefaultLogger

# This engine checks the statistical consistency of the code behavior.

# Exponent of 10 for longest time scale at which to produce statistics.
MAX_TIME_SCALE = 6

# Exponent of 10 for minimum time scale at which we produce statistics.
MIN_TIME_SCALE = 2

# Number of time scale bins
NUM_BINS = MAX_TIME_SCALE - MIN_TIME_SCALE

# How many sigmas do we have so that the alarm is statistically justified?
SIGNIFICANT_SIGMAS = 4.0 # In real applications, at least 3.0

EPSILON = 1e-8

class StatEngine(autotest.ExampleEngine):

    def __init__(self,
                 mfunc=None,
                 mclass=None,
                 mattr=None,
                 module=None,
                 max_tests=None,
                 logger=DefaultLogger(),
                 storage_engine=storage_engines.FileStorageEngine,
                 fname=None,
                 exit_on_error=False,
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
        self.fname = fname
        self.exit_on_error = exit_on_error
        self.base_name = base_name
        self.class_name = class_name
        self.logger = logger
        self.storage_engine = storage_engine
        self.flat_function_name = flat_function_name
        self.qualified_function_name = qualified_function_name
        self.switches = switches or {}
        self.file_name = os.path.join(base_name, qualified_function_name) + ".json"

        # Model used for learning.
        self.model = None

        # Number of unsaved runs.
        self.num_unsaved_runs = 0
        # Log2 of unsaved runs.
        self.log2_unsaved_runs = 0


    def _load(self):
        """Loads the statistical model."""
        if self.model is None:
            json_data = self.storage_engine.read(self.file_name)
            self.model = StatModel.deserialize(json_data) if json_data else StatModel()

    def _save(self):
        """Saves the statistical model."""
        dr = self.file_name.rsplit(os.sep, 1)[0]
        if not os.path.exists(dr):
            os.makedirs(dr)
        self.storage_engine.write(self.model.serialize(), self.file_name)

    def _maybe_save(self):
        self.num_unsaved_runs += 1
        if self.num_unsaved_runs >= 1 << self.log2_unsaved_runs:
            self.log2_unsaved_runs += 1
            self._save()

    def learn(self, input, output):
        """Updates the statistical model, and checks for inconsistencies."""
        print 'Learning...'
        self._load()
        # Forms a dictionary describing what the input and output look like,
        # so we can then compute the various statistics.
        v = dict(input_state=input[1], input=input[0], output=output[0], output_state=output[1])
        d = {}
        valuize.valuize(d, '', v)
        # Sends the dictionary to the learner.
        self.model.learn(d)
        # From now and then, saves the model.
        self._maybe_save()

    def test(self, input, output):
        print 'Testing... %s.py and function %s:' % (self.module, self.qualified_function_name)
        significance = self.switches.get(self.qualified_function_name, SIGNIFICANT_SIGMAS)
        ok, msg = self.model.check(significance)
        if not ok:
            print "Change of behavior detected"
            print "Input State:", repr(input[1])
            print "Input:", repr(input[0])
            print "Output:", repr(output[0])
            print "Output State:", repr(output[1])
            print msg
            if self.exit_on_error:
                sys.exit(-1)

class StatModel(json_plus.Serializable):
    """Statistical model in python."""

    def __init__(self):
        """Produces a blank learning model."""
        self.vars = set()
        self.sum_x = {}
        self.sum_xx = {}
        self.weights = {}
        self.count = {} # Count of total number of data, to avoid giving alerts too early.
        self.count_since_alarm = {} # Count of data since last alarm.
        # Let's precompute the coefficients.
        self.nprange = np.array(range(MIN_TIME_SCALE, MAX_TIME_SCALE))
        self.coeffs = 1.0 - 10.0 ** - self.nprange
        self.intervals = 10 ** (self.nprange)

    @staticmethod
    def deserialize(s):
        if s is None:
            return StatModel()
        return json_plus.Serializable.from_json(s)

    def serialize(self):
        return self.to_json(pack_ndarray=True, tolerant=True)

    def learn(self, d):
        """Learns from a dictionary d, which is a dictionary of key/value pairs."""
        # First, adds to the model all the new variables in d.
        self.last_vars = set(d.keys())
        for v in self.last_vars - self.vars:
            self.sum_x[v] = np.zeros(NUM_BINS)
            self.sum_xx[v] = np.zeros(NUM_BINS)
            self.weights[v] = np.zeros(NUM_BINS)
            self.count[v] = 0L
        # Then, updates all models for the variables.
        self.vars = self.vars | self.last_vars
        for v in self.vars:
            # First, discounts the weights.
            self.weights[v] *= self.coeffs
            self.sum_x[v] *= self.coeffs
            self.sum_xx[v] *= self.coeffs
            # Then, if the variable is present this time, adds one more item of evidence.
            if v in d:
                x = d[v]
                self.weights[v] += 1.0
                self.sum_x[v] += x
                self.sum_xx[v] += x * x
                self.count[v] = min(10 ** MAX_TIME_SCALE + 1L, self.count.get(v, 0L) + 1L)
                self.count_since_alarm[v] = np.minimum(
                    10 ** MAX_TIME_SCALE + np.ones(NUM_BINS),
                    self.count_since_alarm.get(v, np.zeros(NUM_BINS)) + 1L)

    def check(self, significance):
        """Checks if there is a statistically significant discrepancy
        between long and short term behavior.
        Returns whether the results are ok, and an error message."""
        msg = ''
        ok = True
        for v in self.last_vars:
            if self.weights[v][0] > 1.0:
                # Computes means and distribution variances.
                means = self.sum_x[v] / self.weights[v]
                variances = self.sum_xx[v] / self.weights[v] - means * means
                # These are the variances of the means.  The distribution variance is N / (N - 1) the
                # sample variance; the variance of the mean is the distribution variance divided by
                # the number of points (the weight of) the mean, that is, N.
                mean_vars = variances / (self.weights[v] - 1.0)
                # Computes significance threshold for each pair of estimates.
                for k in range(NUM_BINS - 1):
                    # We perform the check only once we have enough data, and if sufficient time has passed
                    # since the latest alert.
                    if self.count[v] > self.intervals[k] and self.count_since_alarm[v][k] > self.intervals[k]:
                        mean_diff = abs(means[k] - means[k + 1])
                        stdev_diff = math.sqrt(abs(mean_vars[k] + mean_vars[k + 1]))
                        
                        if (stdev_diff == 0 and mean_diff != 0) or mean_diff / (stdev_diff or 1) > significance:

                            ok = False
                            msg += "\nQuantity %r differs from past behavior for timescale 10^%d with significance %r" % (
                                v, k + MIN_TIME_SCALE, "infinity" if stdev_diff == 0 else mean_diff / stdev_diff)
                            msg += "\nBehavior in last 10^%d iterations: mean = %f variance = %f variance of mean = %f" % (
                                k + MIN_TIME_SCALE, means[k], variances[k], mean_vars[k])
                            msg += "\nBehavior in last 10^%d iterations: mean = %f variance = %f variance of mean = %f" % (
                                k + 1 + MIN_TIME_SCALE, means[k + 1], variances[k + 1], mean_vars[k + 1])
                            self.count_since_alarm[v][k] = 0

                            print "v:", v
                            print "means:", means
                            print "count:", self.count[v]
                            print "k", k
                            print "mean_diff", mean_diff
                            print "stdev_diff", stdev_diff
                            print "significance", mean_diff / stdev_diff
                            if stdev_diff > 0:
                                print mean_diff / stdev_diff




        return ok, msg


class TestSerializable(unittest.TestCase):

    def test_simple(self):
        sm = StatModel.deserialize(None)
        sm.learn(dict(x=1))
        ok, msg = sm.check()
        self.assertTrue(ok)

    def test_serialize(self):
        sm = StatModel.deserialize(None)
        sm.learn(dict(x=1))
        s = sm.serialize()
        sm = StatModel.deserialize(s)
        sm.learn(dict(x=1))
        ok, msg = sm.check()
        self.assertTrue(ok)

    def test_short_change(self):
        sm = StatModel.deserialize(None)
        for i in range(10):
            sm.learn(dict(x=1))
        for i in range(3):
            sm.learn(dict(x=0))
            ok, msg = sm.check()
            self.assertTrue(ok)

    def test_long_change(self):
        sm = StatModel.deserialize(None)
        for i in range(1000):
            sm.learn(dict(x=1))
        for i in range(100):
            sm.learn(dict(x=0))
            ok, msg = sm.check()
            if not ok:
                print "---->", i
                print ok, msg
            # self.assertTrue(ok)


if __name__ == '__main__':
    unittest.main()
