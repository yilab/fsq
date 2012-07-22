import unittest
import sys

from .path import TestPath
from .const import TestConsts
from .configure import TestUpDownIsDown, TestTriggers
from .install import TestInstallUninstall
from . import constants as _test_c

############ INTERNAL HELPERS
_LOADER = unittest.TestLoader()
_RUNNER = unittest.TextTestRunner(verbosity=2)
def _extract(result, errors, failures):
    errors += len(result.errors)
    failures += len(result.failures)
    return errors, failures

############ Runner Wrappers
def run_paths():
    paths_tests = _LOADER.loadTestsFromTestCase(TestPath)
    return _RUNNER.run(paths_tests)

def run_consts():
    consts_tests = _LOADER.loadTestsFromTestCase(TestConsts)
    return _RUNNER.run(consts_tests)

def run_updownisdown():
    updownisdown_tests = _LOADER.loadTestsFromTestCase(TestUpDownIsDown)
    return _RUNNER.run(updownisdown_tests)

def run_triggers():
    triggers_tests = _LOADER.loadTestsFromTestCase(TestTriggers)
    return _RUNNER.run(triggers_tests)

def run_install():
    install_tests = _LOADER.loadTestsFromTestCase(TestInstallUninstall)
    return _RUNNER.run(install_tests)

def run_all():
    failures = errors = 0
    failures, errors = _extract(run_paths(), errors, failures)
    failures, errors = _extract(run_consts(), errors, failures)
    failures, errors = _extract(run_updownisdown(), errors, failures)
    failures, errors = _extract(run_triggers(), errors, failures)
    failures, errors = _extract(run_install(), errors, failures)
    print >> sys.stderr, "Total Tests Run: {0}".format(_test_c.TOTAL_COUNT)
    print >> sys.stderr, "Total Failures: {0}, Total Errors:"\
                         " {1}".format(failures, errors)
