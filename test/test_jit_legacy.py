# Owner(s): ["oncall: jit"]

import sys
sys.argv.append("--jit-executor=legacy")
from torch.testing._internal.common_utils import run_tests

from test_jit import *  # noqa: F403, F401

if __name__ == '__main__':
    run_tests()
