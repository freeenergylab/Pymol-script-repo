#!/usr/bin/env python
"""
A setup.py script to use setuptools, which gives egg goodness, etc.
"""

from setuptools import setup
exec(compile(open('setup.py', "rb").read(), 'setup.py', 'exec'))
