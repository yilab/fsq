import unittest
import sys

from .install import TestInstallUninstall
from .configure import TestUpDownIsDown, TestTriggers
from . import constants as _test_c

############ INTERNAL HELPERS
_LOADER = unittest.TestLoader()
_RUNNER = unittest.TextTestRunner(verbosity=2)

############ Runner Wrappers
def run_install():
    install_tests = _LOADER.loadTestsFromTestCase(TestInstallUninstall)
    _RUNNER.run(install_tests)

def run_updownisdown():
    updownisdown_tests = _LOADER.loadTestsFromTestCase(TestUpDownIsDown)
    _RUNNER.run(updownisdown_tests)

def run_triggers():
    triggers_tests = _LOADER.loadTestsFromTestCase(TestTriggers)
    _RUNNER.run(triggers_tests)

def run_all():
    run_install()
    run_updownisdown()
    run_triggers()
    print >> sys.stderr, "Total Tests Run: {0}".format(_test_c.TOTAL_COUNT)
