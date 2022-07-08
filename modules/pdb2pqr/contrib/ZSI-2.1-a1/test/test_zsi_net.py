#!/usr/bin/env python
import test_t4
import test_callhome
from test_zsi import *

def makeTestSuite():
    return unittest.TestSuite(
        [globals()[t].makeTestSuite() for t in [g for g in globals() if g.startswith('test_') and True]]
    )

def main():
    unittest.main(defaultTest="makeTestSuite")
    suite = unittest.TestSuite()

if __name__ == "__main__" : main()
