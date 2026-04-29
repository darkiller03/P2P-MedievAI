#!/usr/bin/env python
"""
Battle CLI - Simple entry point
Usage:
    battle run <scenario> [-d DATAFILE] [--seed SEED]
    battle run <scenario> <AI1> <AI2> [-t] [-d DATAFILE] [--seed SEED]
    battle load <savefile>
    battle tourney [-G AI1 AI2...] [-S SCENARIO...] [-N ROUNDS] [-na] [-d DATAFILE]
    battle plot <AI> <plotter> <scenario> <units...> range (values) [-N ROUNDS]
"""

import sys
import os

# Add the FinalCode directory to the path so we can import modules
script_dir = os.path.dirname(os.path.abspath(__file__))
terminal_code_dir = os.path.join(script_dir, 'age', 'FinalCode')
if os.path.exists(terminal_code_dir):
    sys.path.insert(0, terminal_code_dir)
else:
    # If running from within TerminalCodeOrganized
    sys.path.insert(0, script_dir)

# Now import and run Main
from Main import main

if __name__ == '__main__':
    main()
