#
#
#
#
# $Id: test_hydrogenBuilder.py,v 1.1 2004/08/11 16:44:22 rhuey Exp $
#

import unittest
from string import split
from MolKit.hydrogenBuilder import HydrogenBuilder, PolarHydrogenBuilder


class BaseTests(unittest.TestCase):
    def setUp(self):
        from MolKit import Read
        self.mol = Read('Data/1crn.pdb')[0]
        self.mol.buildBondsByDistance()
    

    def tearDown(self):
        """
        clean-up
        """
        del(self.mol)


    def test_constructor(self):
        """
        instantiate an HydrogenBuilder
        """
        h_builder = HydrogenBuilder()
        self.assertEqual(h_builder.__class__, HydrogenBuilder)


    def test_constructorOptions(self):
        """
         test possible constructor options
            options = htype, renumber, method
        """
    
        h_builder = HydrogenBuilder(htype='polarOnly')
        self.assertEqual(h_builder.__class__, HydrogenBuilder)
        h_builder = HydrogenBuilder(renumber=0)
        self.assertEqual(h_builder.__class__, HydrogenBuilder)
        h_builder = HydrogenBuilder(method='withBondOrder')
        self.assertEqual(h_builder.__class__, HydrogenBuilder)


    def test_addHydrogens(self):
        """
         test addHydrogens 
        """
        beforeLen = len(self.mol.allAtoms)
        h_builder = HydrogenBuilder()
        h_builder.addHydrogens(self.mol)
        afterLen = len(self.mol.allAtoms)
        #print "beforeLen=", beforeLen, ' afterLen=', afterLen
        self.assertEqual(beforeLen<afterLen, True)






if __name__ == '__main__':
    unittest.main()
