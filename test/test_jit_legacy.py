# Owner(s): ["oncall: jit"]

import sys
sys.argv.append("--jit-executor=legacy")
from torch.testing._internal.common_utils import parse_cmd_line_args, run_tests

# The tests decorators depend on command line arguments
if __name__ == '__main__':
    parse_cmd_line_args()

from test_jit import *  # noqa: F403, F401

if __name__ == '__main__':
    run_tests()
