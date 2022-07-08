"""
NumPy
=====

Provides
  1. An array object of arbitrary homogeneous items
  2. Fast mathematical operations over arrays
  3. Linear Algebra, Fourier Transforms, Random Number Generation

Documentation is available in the docstrings and at http://www.scipy.org

Available subpackages
---------------------
core
    Defines a multi-dimensional array and useful procedures
    for Numerical computation.
lib
    Basic functions used by several sub-packages and useful
    to have in the main name-space.
random
    Core Random Tools
linalg
    Core Linear Algebra Tools
fft
    Core FFT routines
testing
    Numpy testing tools

The following sub-packages must be explicitly imported:

f2py
    Fortran to Python Interface Generator.
distutils
    Enhancements to distutils with support for
    Fortran compilers support and more.


Global symbols from subpackages
-------------------------------
========  =================================
core      all (use numpy.* not numpy.core.*)
lib       all (use numpy.* not numpy.lib.*)
testing   NumpyTest
========  =================================


Utility tools
-------------

test
    Run numpy unittests
pkgload
    Load numpy packages
show_config
    Show numpy build configuration
dual
    Overwrite certain functions with high-performance Scipy tools
matlib
    Make everything matrices.
__version__
    Numpy version string

"""

# We first need to detect if we're being called as part of the numpy setup
# procedure itself in a reliable manner.
try:
    __NUMPY_SETUP__
except NameError:
    __NUMPY_SETUP__ = False


if __NUMPY_SETUP__:
    import sys as _sys
    print('Running from numpy source directory.', file=_sys.stderr)
    del _sys
else:
    try:
        from numpy.__config__ import show as show_config
    except ImportError as e:
        msg = """Error importing numpy: you should not try to import numpy from
        its source directory; please exit the numpy source tree, and relaunch
        your python intepreter from there."""
        raise ImportError(msg)
    from .version import version as __version__

    from ._import_tools import PackageLoader

    def pkgload(*packages, **options):
        loader = PackageLoader(infunc=True)
        return loader(*packages, **options)

    from . import add_newdocs
    __all__ = ['add_newdocs']

    pkgload.__doc__ = PackageLoader.__call__.__doc__
    from . import testing
    from .testing import ScipyTest, NumpyTest
    from . import core
    from .core import *
    from . import lib
    from .lib import *
    from . import linalg
    from . import fft
    from . import random
    from . import ctypeslib
    from . import ma

    # Make these accessible from numpy name-space
    #  but not imported in from numpy import *
    from builtins import bool, int, int, float, complex, \
         object, str, str
    from .core import round, abs, max, min

    __all__.extend(['__version__', 'pkgload', 'PackageLoader',
               'ScipyTest', 'NumpyTest', 'show_config'])
    __all__.extend(core.__all__)
    __all__.extend(lib.__all__)
    __all__.extend(['linalg', 'fft', 'random', 'ctypeslib'])

    def test(*args, **kw):
        import os, sys
        print('Numpy is installed in %s' % (os.path.split(__file__)[0],))
        print('Numpy version %s' % (__version__,))
        print('Python version %s' % (sys.version.replace('\n', '',),))
        return NumpyTest().test(*args, **kw)
    test.__doc__ = NumpyTest.test.__doc__
