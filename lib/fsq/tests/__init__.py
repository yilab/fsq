import os
import unittest

TEST_DIR = os.path.join(os.path.dirname(__file__), 'test_queues')
ROOT1 = os.path.join(TEST_DIR, 'queue')
ROOT2 = os.path.join(TEST_DIR, 'queue2')

from .install import TestInstallUninstall

def run_all():
    loader = unittest.TestLoader()
    runner = unittest.TextTestRunner(verbosity=2)

    install_tests = loader.loadTestsFromTestCase(TestInstallUninstall)
    runner.run(install_tests)

__all__ = [ 'TEST_DIR', 'ROOT1', 'ROOT2', 'TestInstallUninstall',  ]
