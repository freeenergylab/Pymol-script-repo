#! /usr/bin/env python

# System imports
from   distutils.util import get_platform
import os
import sys
import unittest

# Import NumPy
import numpy as np
major, minor = [ int(d) for d in np.__version__.split(".")[:2] ]
if major == 0:
    BadListError = TypeError
else:
    BadListError = ValueError

# Add the distutils-generated build directory to the python search path and then
# import the extension module
libDir = "lib.%s-%s" % (get_platform(), sys.version[:3])
sys.path.insert(0,os.path.join("build", libDir))
import Array

######################################################################

class Array1TestCase(unittest.TestCase):

    def setUp(self):
        self.length = 5
        self.array1 = Array.Array1(self.length)

    def testConstructor0(self):
        "Test Array1 default constructor"
        a = Array.Array1()
        self.assertTrue(isinstance(a, Array.Array1))
        self.assertTrue(len(a) == 0)

    def testConstructor1(self):
        "Test Array1 length constructor"
        self.assertTrue(isinstance(self.array1, Array.Array1))

    def testConstructor2(self):
        "Test Array1 array constructor"
        na = np.arange(self.length)
        aa = Array.Array1(na)
        self.assertTrue(isinstance(aa, Array.Array1))

    def testConstructor3(self):
        "Test Array1 copy constructor"
        for i in range(self.array1.length()): self.array1[i] = i
        arrayCopy = Array.Array1(self.array1)
        self.assertTrue(arrayCopy == self.array1)

    def testConstructorBad(self):
        "Test Array1 length constructor, negative"
        self.assertRaises(ValueError, Array.Array1, -4)

    def testLength(self):
        "Test Array1 length method"
        self.assertTrue(self.array1.length() == self.length)

    def testLen(self):
        "Test Array1 __len__ method"
        self.assertTrue(len(self.array1) == self.length)

    def testResize0(self):
        "Test Array1 resize method, length"
        newLen = 2 * self.length
        self.array1.resize(newLen)
        self.assertTrue(len(self.array1) == newLen)

    def testResize1(self):
        "Test Array1 resize method, array"
        a = np.zeros((2*self.length,), dtype='l')
        self.array1.resize(a)
        self.assertTrue(len(self.array1) == len(a))

    def testResizeBad(self):
        "Test Array1 resize method, negative length"
        self.assertRaises(ValueError, self.array1.resize, -5)

    def testSetGet(self):
        "Test Array1 __setitem__, __getitem__ methods"
        n = self.length
        for i in range(n):
            self.array1[i] = i*i
        for i in range(n):
            self.assertTrue(self.array1[i] == i*i)

    def testSetBad1(self):
        "Test Array1 __setitem__ method, negative index"
        self.assertRaises(IndexError, self.array1.__setitem__, -1, 0)

    def testSetBad2(self):
        "Test Array1 __setitem__ method, out-of-range index"
        self.assertRaises(IndexError, self.array1.__setitem__, self.length+1, 0)

    def testGetBad1(self):
        "Test Array1 __getitem__ method, negative index"
        self.assertRaises(IndexError, self.array1.__getitem__, -1)

    def testGetBad2(self):
        "Test Array1 __getitem__ method, out-of-range index"
        self.assertRaises(IndexError, self.array1.__getitem__, self.length+1)

    def testAsString(self):
        "Test Array1 asString method"
        for i in range(self.array1.length()): self.array1[i] = i+1
        self.assertTrue(self.array1.asString() == "[ 1, 2, 3, 4, 5 ]")

    def testStr(self):
        "Test Array1 __str__ method"
        for i in range(self.array1.length()): self.array1[i] = i-2
        self.assertTrue(str(self.array1) == "[ -2, -1, 0, 1, 2 ]")

    def testView(self):
        "Test Array1 view method"
        for i in range(self.array1.length()): self.array1[i] = i+1
        a = self.array1.view()
        self.assertTrue(isinstance(a, np.ndarray))
        self.assertTrue(len(a) == self.length)
        self.assertTrue((a == [1,2,3,4,5]).all())

######################################################################

class Array2TestCase(unittest.TestCase):

    def setUp(self):
        self.nrows = 5
        self.ncols = 4
        self.array2 = Array.Array2(self.nrows, self.ncols)

    def testConstructor0(self):
        "Test Array2 default constructor"
        a = Array.Array2()
        self.assertTrue(isinstance(a, Array.Array2))
        self.assertTrue(len(a) == 0)

    def testConstructor1(self):
        "Test Array2 nrows, ncols constructor"
        self.assertTrue(isinstance(self.array2, Array.Array2))

    def testConstructor2(self):
        "Test Array2 array constructor"
        na = np.zeros((3,4), dtype="l")
        aa = Array.Array2(na)
        self.assertTrue(isinstance(aa, Array.Array2))

    def testConstructor3(self):
        "Test Array2 copy constructor"
        for i in range(self.nrows):
            for j in range(self.ncols):
                self.array2[i][j] = i * j
        arrayCopy = Array.Array2(self.array2)
        self.assertTrue(arrayCopy == self.array2)

    def testConstructorBad1(self):
        "Test Array2 nrows, ncols constructor, negative nrows"
        self.assertRaises(ValueError, Array.Array2, -4, 4)

    def testConstructorBad2(self):
        "Test Array2 nrows, ncols constructor, negative ncols"
        self.assertRaises(ValueError, Array.Array2, 4, -4)

    def testNrows(self):
        "Test Array2 nrows method"
        self.assertTrue(self.array2.nrows() == self.nrows)

    def testNcols(self):
        "Test Array2 ncols method"
        self.assertTrue(self.array2.ncols() == self.ncols)

    def testLen(self):
        "Test Array2 __len__ method"
        self.assertTrue(len(self.array2) == self.nrows*self.ncols)

    def testResize0(self):
        "Test Array2 resize method, size"
        newRows = 2 * self.nrows
        newCols = 2 * self.ncols
        self.array2.resize(newRows, newCols)
        self.assertTrue(len(self.array2) == newRows * newCols)

    #def testResize1(self):
    #    "Test Array2 resize method, array"
    #    a = np.zeros((2*self.nrows, 2*self.ncols), dtype='l')
    #    self.array2.resize(a)
    #    self.failUnless(len(self.array2) == len(a))

    def testResizeBad1(self):
        "Test Array2 resize method, negative nrows"
        self.assertRaises(ValueError, self.array2.resize, -5, 5)

    def testResizeBad2(self):
        "Test Array2 resize method, negative ncols"
        self.assertRaises(ValueError, self.array2.resize, 5, -5)

    def testSetGet1(self):
        "Test Array2 __setitem__, __getitem__ methods"
        m = self.nrows
        n = self.ncols
        array1 = [ ]
        a = np.arange(n, dtype="l")
        for i in range(m):
            array1.append(Array.Array1(i*a))
        for i in range(m):
            self.array2[i] = array1[i]
        for i in range(m):
            self.assertTrue(self.array2[i] == array1[i])

    def testSetGet2(self):
        "Test Array2 chained __setitem__, __getitem__ methods"
        m = self.nrows
        n = self.ncols
        for i in range(m):
            for j in range(n):
                self.array2[i][j] = i*j
        for i in range(m):
            for j in range(n):
                self.assertTrue(self.array2[i][j] == i*j)

    def testSetBad1(self):
        "Test Array2 __setitem__ method, negative index"
        a = Array.Array1(self.ncols)
        self.assertRaises(IndexError, self.array2.__setitem__, -1, a)

    def testSetBad2(self):
        "Test Array2 __setitem__ method, out-of-range index"
        a = Array.Array1(self.ncols)
        self.assertRaises(IndexError, self.array2.__setitem__, self.nrows+1, a)

    def testGetBad1(self):
        "Test Array2 __getitem__ method, negative index"
        self.assertRaises(IndexError, self.array2.__getitem__, -1)

    def testGetBad2(self):
        "Test Array2 __getitem__ method, out-of-range index"
        self.assertRaises(IndexError, self.array2.__getitem__, self.nrows+1)

    def testAsString(self):
        "Test Array2 asString method"
        result = """\
[ [ 0, 1, 2, 3 ],
  [ 1, 2, 3, 4 ],
  [ 2, 3, 4, 5 ],
  [ 3, 4, 5, 6 ],
  [ 4, 5, 6, 7 ] ]
"""
        for i in range(self.nrows):
            for j in range(self.ncols):
                self.array2[i][j] = i+j
        self.assertTrue(self.array2.asString() == result)

    def testStr(self):
        "Test Array2 __str__ method"
        result = """\
[ [ 0, -1, -2, -3 ],
  [ 1, 0, -1, -2 ],
  [ 2, 1, 0, -1 ],
  [ 3, 2, 1, 0 ],
  [ 4, 3, 2, 1 ] ]
"""
        for i in range(self.nrows):
            for j in range(self.ncols):
                self.array2[i][j] = i-j
        self.assertTrue(str(self.array2) == result)

    def testView(self):
        "Test Array2 view method"
        a = self.array2.view()
        self.assertTrue(isinstance(a, np.ndarray))
        self.assertTrue(len(a) == self.nrows)

######################################################################

if __name__ == "__main__":

    # Build the test suite
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(Array1TestCase))
    suite.addTest(unittest.makeSuite(Array2TestCase))

    # Execute the test suite
    print("Testing Classes of Module Array")
    print("NumPy version", np.__version__)
    print()
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(len(result.errors) + len(result.failures))
