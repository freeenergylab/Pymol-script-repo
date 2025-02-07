"""
    Driver for PDB2PQR

    This module takes a PDB file as input and performs optimizations
    before yielding a new PDB-style file as output.

    Ported to Python by Todd Dolinsky (todd@ccb.wustl.edu)
    Washington University in St. Louis

    Parsing utilities provided by Nathan A. Baker (Nathan.Baker@pnl.gov)
    Pacific Northwest National Laboratory

    Copyright (c) 2002-2011, Jens Erik Nielsen, University College Dublin; 
    Nathan A. Baker, Battelle Memorial Institute, Developed at the Pacific 
    Northwest National Laboratory, operated by Battelle Memorial Institute, 
    Pacific Northwest Division for the U.S. Department Energy.; 
    Paul Czodrowski & Gerhard Klebe, University of Marburg.

	All rights reserved.

	Redistribution and use in source and binary forms, with or without modification, 
	are permitted provided that the following conditions are met:

		* Redistributions of source code must retain the above copyright notice, 
		  this list of conditions and the following disclaimer.
		* Redistributions in binary form must reproduce the above copyright notice, 
		  this list of conditions and the following disclaimer in the documentation 
		  and/or other materials provided with the distribution.
        * Neither the names of University College Dublin, Battelle Memorial Institute,
          Pacific Northwest National Laboratory, US Department of Energy, or University
          of Marburg nor the names of its contributors may be used to endorse or promote
          products derived from this software without specific prior written permission.

	THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND 
	ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED 
	WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. 
	IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, 
	INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, 
	BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, 
	DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF 
	LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE 
	OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED 
	OF THE POSSIBILITY OF SUCH DAMAGE.

"""

__date__  = "5 April 2010"
__author__ = "Todd Dolinsky, Nathan Baker, Jens Nielsen, Paul Czodrowski, Jan Jensen, Samir Unni, Yong Huang"
__version__ = "1.7.1"


import string
import sys
import getopt
from optparse import OptionParser, OptionGroup
import os
import time
from .src import pdb
from .src import utilities
from .src import structures
from .src import routines
from .src import protein
from .src.pdb import *
from .src.utilities import *
from .src.structures import *
from .src.definitions import *
from .src.forcefield import *
from .src.routines import *
from .src.protein import *
from .src.server import *
from .src.hydrogens import *
from .src.aconf import *
from io import *

from . import extensions

def printPQRHeader(atomlist, reslist, charge, ff, warnings, pH, ffout):
    """
        Print the header for the PQR file

        Parameters:
            atomlist: A list of atoms that were unable to have
                      charges assigned (list)
            reslist:  A list of residues with non-integral charges
                      (list)
            charge:   The total charge on the protein (float)
            ff:       The forcefield name (string)
            warnings: A list of warnings generated from routines (list)
            options:  A dictionary of command lnie options (float)
        Returns
            header:   The header for the PQR file (string)
    """
    if ff is None:
        ff = 'User force field'
    else:
        ff = ff.upper()
    header = "REMARK   1 PQR file generated by PDB2PQR (Version %s)\n" % __version__
    header = header + "REMARK   1\n"
    header = header + "REMARK   1 Forcefield Used: %s\n" % ff
    if not ffout is None:
        header = header + "REMARK   1 Naming Scheme Used: %s\n" % ffout
    header = header + "REMARK   1\n"
    
    if not pH is None:
        header = header + "REMARK   1 pKas calculated by propka and assigned using pH %.2f\n" % pH
        header = header + "REMARK   1\n"

    for warning in warnings:
        header = header + "REMARK   5 " + warning 
    header = header + "REMARK   5\n"
    
    if len(atomlist) != 0:
        header += "REMARK   5 WARNING: PDB2PQR was unable to assign charges\n"
        header += "REMARK   5          to the following atoms (omitted below):\n"
        for atom in atomlist:
            header += "REMARK   5              %i %s in %s %i\n" % \
                      (atom.get("serial"), atom.get("name"), \
                       atom.get("residue").get("name"), \
                       atom.get("residue").get("resSeq"))
        header += "REMARK   5 This is usually due to the fact that this residue is not\n"
        header += "REMARK   5 an amino acid or nucleic acid; or, there are no parameters\n" 
        header += "REMARK   5 available for the specific protonation state of this\n" 
        header += "REMARK   5 residue in the selected forcefield.\n"
        header += "REMARK   5\n"
    if len(reslist) != 0:
        header += "REMARK   5 WARNING: Non-integral net charges were found in\n"
        header += "REMARK   5          the following residues:\n"
        for residue in reslist:
            header += "REMARK   5              %s - Residue Charge: %.4f\n" % \
                      (residue, residue.getCharge())
        header += "REMARK   5\n"
    header += "REMARK   6 Total charge on this protein: %.4f e\n" % charge
    header += "REMARK   6\n"

    return header

class ExtentionOptions(object):
    pass

def runPDB2PQR(pdblist, ff,
               outname = "",
               ph = None,
               verbose = False,
               extentions = [],
               ententionOptions = ExtentionOptions(),
               clean = False,
               neutraln = False,
               neutralc = False,
               ligand = None,
               assign_only = False,
               chain = False,
               debump = True,
               opt = True,
               typemap = False,
               userff = None,
               usernames = None,
               ffout = None):
    """
        Run the PDB2PQR Suite

        Arguments:
            pdblist: The list of objects that was read from the PDB file
                     given as input (list)
            ff:      The name of the forcefield (string)
        
        Keyword Arguments:
            outname:       The name of the desired output file
            ph:            The desired ph of the system (float)
            verbose:       When True, script will print information to stdout
                             When False, no detailed information will be printed (float)
            extentions:      List of extensions to run
            ententionOptions:optionParser like option object that is passed to each object. 
            clean:         only return original PDB file in aligned format.
            neutraln:      Make the N-terminus of this protein neutral
            neutralc:      Make the C-terminus of this protein neutral
            ligand:        Calculate the parameters for the ligand in mol2 format at the given path.
            assign_only:   Only assign charges and radii - do not add atoms, debump, or optimize.
            chain:     Keep the chain ID in the output PQR file
            debump:        When 1, debump heavy atoms (int)
            opt:           When 1, run hydrogen optimization (int)
            typemap:       Create Typemap output.
            userff:        The user created forcefield file to use. Overrides ff.
            usernames:     The user created names file to use. Required if using userff.
            ffout:         Instead of using the standard canonical naming scheme for residue and atom names,  +
                           use the names from the given forcefield
            
        Returns
            header:  The PQR file header (string)
            lines:   The PQR file atoms (list)
            missedligandresidues:  A list of ligand residue names whose charges could
                     not be assigned (ligand)
    """
    
    pkaname = ""
    outroot = ""
    lines = []
    Lig = None
    atomcount = 0   # Count the number of ATOM records in pdb
    
    period = string.rfind(outname,".")
    
    if period > 0: 
        outroot = outname[0:period]
    else: 
        outroot = outname

    if not ph is None:
        pka = True
        pkaname = outroot + ".propka"
        if os.path.isfile(pkaname): os.remove(pkaname)
    else: 
        pka = False

    start = time.time()

    if verbose:
        print("Beginning PDB2PQR...\n")

    myDefinition = Definition()
    if verbose:
        print("Parsed Amino Acid definition file.")   

    # Check for the presence of a ligand!  This code is taken from pdb2pka/pka.py

    if not ligand is None:
        from .pdb2pka.ligandclean import ligff
        myProtein, myDefinition, Lig = ligff.initialize(myDefinition, ligand, pdblist, verbose)        
        for atom in myProtein.getAtoms():
            if atom.type == "ATOM": 
                atomcount += 1
    else:
        myProtein = Protein(pdblist, myDefinition)

    if verbose:
        print("Created protein object -")
        print("\tNumber of residues in protein: %s" % myProtein.numResidues())
        print("\tNumber of atoms in protein   : %s" % myProtein.numAtoms())
        
    myRoutines = Routines(myProtein, verbose)

    for residue in myProtein.getResidues():
        multoccupancy = 0
        for atom in residue.getAtoms():
            if atom.altLoc != "":
                multoccupancy = 1
                txt = "Warning: multiple occupancies found: %s in %s\n" % (atom.name, residue)
                sys.stderr.write(txt)
        if multoccupancy == 1:
            myRoutines.warnings.append("WARNING: multiple occupancies found in %s,\n" % (residue))
            myRoutines.warnings.append("         at least one of the instances is being ignored.\n")

    myRoutines.setTermini(neutraln, neutralc)
    myRoutines.updateBonds()

    if clean:
        header = ""
        lines = myProtein.printAtoms(myProtein.getAtoms(), chain)
      
        # Process the extensions
        # TODO: kill the eval call.
        for ext in extentions:
            module = extensions.extDict[ext]
            call = "module.%s(myRoutines, outroot)" % ext
            eval(call)  
    
        if verbose:
            print("Total time taken: %.2f seconds\n" % (time.time() - start))
        
        #Be sure to include None for missed ligand residues
        return header, lines, None
    
    #remove any future need to convert to lower case
    if not ff is None:
        ff = ff.lower()
    if not ffout is None:
        ffout = ffout.lower()

    if not assign_only:
        # It is OK to process ligands with no ATOM records in the pdb
        if atomcount == 0 and Lig != None:
            pass
        else:
            myRoutines.findMissingHeavy()
        myRoutines.updateSSbridges()

        if debump:
            myRoutines.debumpProtein()  

        if pka:
            myRoutines.runPROPKA(ph, ff, pkaname)

        myRoutines.addHydrogens()

        myhydRoutines = hydrogenRoutines(myRoutines)

        if debump:
            myRoutines.debumpProtein()  

        if opt:
            myhydRoutines.setOptimizeableHydrogens()
            myhydRoutines.initializeFullOptimization()
            myhydRoutines.optimizeHydrogens()
        else:
            myhydRoutines = hydrogenRoutines(myRoutines)
            myhydRoutines.initializeWaterOptimization()
            myhydRoutines.optimizeHydrogens()

        # Special for GLH/ASH, since both conformations were added
        myhydRoutines.cleanup()


    else:  # Special case for HIS if using assign-only
        for residue in myProtein.getResidues():
            if isinstance(residue, HIS):
                myRoutines.applyPatch("HIP", residue)

    myRoutines.setStates()

    myForcefield = Forcefield(ff, myDefinition, userff, usernames)
    hitlist, misslist = myRoutines.applyForcefield(myForcefield)
  
    ligsuccess = 0
    
    if not ligand is None:
        # If this is independent, we can assign charges and radii here 
        for residue in myProtein.getResidues():
            if isinstance(residue, LIG):
                templist = []
                Lig.make_up2date(residue)
                for atom in residue.getAtoms():
                    atom.ffcharge = Lig.ligand_props[atom.name]["charge"]
                    atom.radius = Lig.ligand_props[atom.name]["radius"]
                    if atom in misslist:
                        misslist.pop(misslist.index(atom))
                        templist.append(atom)

                charge = residue.getCharge()
                if abs(charge - int(charge)) > 0.001:
                    # Ligand parameterization failed
                    myRoutines.warnings.append("WARNING: PDB2PQR could not successfully parameterize\n")
                    myRoutines.warnings.append("         the desired ligand; it has been left out of\n")
                    myRoutines.warnings.append("         the PQR file.\n")
                    myRoutines.warnings.append("\n")
                    
                    # remove the ligand
                    myProtein.residues.remove(residue) 
                    for myChain in myProtein.chains:
                        if residue in myChain.residues: myChain.residues.remove(residue)
                else:
                    ligsuccess = 1
                    # Mark these atoms as hits
                    hitlist = hitlist + templist
    
    # Temporary fix; if ligand was successful, pull all ligands from misslist
    if ligsuccess:
        templist = misslist[:]
        for atom in templist:
            if isinstance(atom.residue, Amino) or isinstance(atom.residue, Nucleic): continue
            misslist.remove(atom)

    # Create the Typemap
    if typemap:
        typemapname = "%s-typemap.html" % outroot
        myProtein.createHTMLTypeMap(myDefinition, typemapname)

    # Grab the protein charge
    reslist, charge = myProtein.getCharge()

    # If we want a different naming scheme, use that

    if not ffout is None:
        scheme = ffout
        userff = None # Currently not supported
        if scheme != ff: 
            myNameScheme = Forcefield(scheme, myDefinition, userff)
        else: 
            myNameScheme = myForcefield
        myRoutines.applyNameScheme(myNameScheme)

    header = printPQRHeader(misslist, reslist, charge, ff, myRoutines.getWarnings(), ph, ffout)
    lines = myProtein.printAtoms(hitlist, chain)

    # Determine if any of the atoms in misslist were ligands
    missedligandresidues = []
    for atom in misslist:
        if isinstance(atom.residue, Amino) or isinstance(atom.residue, Nucleic): continue
        if atom.resName not in missedligandresidues:
            missedligandresidues.append(atom.resName)

    # Process the extensions
    #TODO: kill the eval call.
    for ext in extentions:
        module = extensions.extDict[ext]
        call = "module.%s(myRoutines, outroot)" % ext
        eval(call)

    if verbose:
        print("Total time taken: %.2f seconds\n" % (time.time() - start))

    return header, lines, missedligandresidues

def mainCommand(argv):
    """
        Main driver for running program from the command line.
    """
    
    fieldNames = ('amber','charmm','parse', 'ty106','peopb','swanson')
    
    validForcefields = []
    validForcefields.extend(fieldNames)
    validForcefields.extend((x.upper() for x in fieldNames))
    
    description = 'This module takes a PDB file as input and performs ' +\
                  'optimizations before yielding a new PQR-style file in PQR_OUTPUT_PATH.\n' +\
                  'If PDB_PATH is an ID it will automatically be obtained from the PDB archive.'
                  
    usage = 'Usage: %prog [options] PDB_PATH PQR_OUTPUT_PATH'
    
    parser = OptionParser(description=description, usage=usage, version='%prog (Version ' + __version__ + ')')
    

    group = OptionGroup(parser,"Manditory options", "One of the following options must be used.")
    group.add_option('--ff', dest='ff', metavar='FIELD_NAME', choices=validForcefields,
                      help='The forcefield to use - currently amber, ' +
                           'charmm, parse, tyl06, peoepb and swanson ' +
                           'are supported.')
    
    group.add_option('--userff', dest='userff', metavar='USER_FIELD_FILE', 
                      help='The user created forcefield file to use. Requires --usernames overrides --ff')
    
    group.add_option('--clean', dest='clean', action='store_true', default=False,
                      help='Do no optimization, atom addition, or parameter assignment, ' +
                           'just return the original PDB file in aligned format. ' +
                           'Overrides --ff and --userff')
    parser.add_option_group(group)
    
    
    group = OptionGroup(parser,"General options")
    group.add_option('--nodebump', dest='debump', action='store_false', default=True,
                      help='Do not perform the debumping operation')
    
    group.add_option('--noopt', dest='opt', action='store_false', default=True,
                      help='Do not perform hydrogen optimization')
    
    group.add_option('--chain', dest='chain', action='store_true', default=False,
                      help='Keep the chain ID in the output PQR file')
    
    group.add_option('--assign-only', dest='assign_only', action='store_true', default=False,
                      help='Only assign charges and radii - do not add atoms, debump, or optimize.')
    
    group.add_option('--ffout', dest='ffout', metavar='FIELD_NAME',choices=validForcefields,
                      help='Instead of using the standard canonical naming scheme for residue and atom names, ' +
                           'use the names from the given forcefield - currently amber, ' +
                           'charmm, parse, tyl06, peoepb and swanson ' +
                           'are supported.')
    
    group.add_option('--usernames', dest='usernames', metavar='USER_NAME_FILE', 
                      help='The user created names file to use. Required if using --userff')
    
    group.add_option('--with-ph', dest='pH', action='store', type='float',
                      help='Use propka to calculate pKas and apply them to the molecule given the pH value. ' +
                           'Actual PropKa results will be output to <output-path>.propka.')
    
    group.add_option('--apbs-input', dest='input', action='store_true', default=False,
                      help='Create a template APBS input file based on the generated PQR file.  Also creates a Python ' +
                           'pickle for using these parameters in other programs.')
    
    group.add_option('--ligand', dest='ligand',  metavar='PATH',
                      help='Calculate the parameters for the ligand in mol2 format at the given path. ' + 
                           'Pdb2pka must be compiled.')
    
    group.add_option('--whitespace', dest='whitespace', action='store_true', default=False,
                      help='Insert whitespaces between atom name and residue name, between x and y, and between y and z.')   
    
    group.add_option('--typemap', dest='typemap', action='store_true', default=False,
                      help='Create Typemap output.')
    
    group.add_option('--neutraln', dest='neutraln', action='store_true', default=False,
                      help='Make the N-terminus of this protein neutral (default is charged). ' +
                           'Requires PARSE force field.')  
    
    group.add_option('--neutralc', dest='neutralc', action='store_true', default=False,
                      help='Make the C-terminus of this protein neutral (default is charged). ' +
                           'Requires PARSE force field.')  

    group.add_option('-v', '--verbose', dest='verbose', action='store_true', default=False,
                      help='Print information to stdout.')
    parser.add_option_group(group)
    
    extentionsGroup = extensions.setupExtensionsOptions(parser)
    
    (options, args) = parser.parse_args() 
    
    if len(args) != 2:
        parser.error('Incorrect number (%d) of arguments!\nargv: %s, args: %s' % (len(args),argv, args))   

    # Append Numeric/Numpy path to sys.path if the user specified a non-standard location during configuration
    sys.argv=argv
    package_path = PACKAGE_PATH
    if package_path != "":
        sys.path.extend(package_path.split(":"))
        
    if (not options.pH is None) and (options.pH < 0.0 or options.pH > 14.0):
        parser.error('%i is not a valid pH!  Please choose a pH between 0.0 and 14.0.' % options.pH)
        
    if options.assign_only or options.clean:
        options.debump = options.optflag = False
        
    userfffile = None
    usernamesfile = None
    
    if not options.clean:
        if not options.usernames is None:
            try:
                usernamesfile = open(options.usernames, 'rU')
            except IOError:
                parser.error('Unable to open user names file %s' % options.usernames)
                
        if not options.userff is None:
            try:
                userfffile = open(options.userff, 'rU')
            except IOError:
                parser.error('Unable to open user force field file %s' % options.userff)
            
            if options.usernames is None:
                parser.error('--usernames must be specified if using --userff')
            
        else:
            if options.ff is None:
                parser.error('One of the manditory options was not specified.\n' + 
                             'Please specify either --ff, --userff, or --clean')
        
            if getFFfile(options.ff) == '':
                parser.error('Unable to find parameter files for forcefield %s!' % options.ff)

    if not options.ligand is None:
        try:
            options.ligand = open(options.ligand, 'rU')
        except IOError:
            parser.error('Unable to find ligand file %s!' % options.ligand)

    if options.neutraln and (options.ff != 'parse' or not options.userff is None):
        parser.error('--neutraln option only works with PARSE forcefield!')
        
    if options.neutralc and (options.ff != 'parse' or not options.userff is None):
        parser.error('--neutralc option only works with PARSE forcefield!')

    text =  "\n--------------------------\n"
    text += "PDB2PQR - a Python-based structural conversion utility\n"
    text += "--------------------------\n"
    text += "Please cite your use of PDB2PQR as:\n"
    text += "  Dolinsky TJ, Nielsen JE, McCammon JA, Baker NA.\n"
    text += "  PDB2PQR: an automated pipeline for the setup, execution,\n"
    text += "  and analysis of Poisson-Boltzmann electrostatics calculations.\n"
    text += "  Nucleic Acids Research 32 W665-W667 (2004).\n\n"
    sys.stdout.write(text)
            
    path = args[0]
    file = getPDBFile(path)
    pdblist, errlist = readPDB(file)
    
    if len(pdblist) == 0 and len(errlist) == 0:
        #TODO: Why are we doing this?
#        try: 
#            os.remove(path)
#        except OSError: 
#            pass
        parser.error("Unable to find file %s!" % path)

    if len(errlist) != 0 and options.verbose:
        print("Warning: %s is a non-standard PDB file.\n" % path)
        print(errlist)

    outpath = args[1]
    options.outname = outpath

    #In case no extensions were specified.
    if options.active_extentions is None:
        options.active_extentions = []
        
    #Filter out the options specifically for extentions.
    #Passed into runPDB2PQR, but not used by any extention yet.
    extentionOpts = ExtentionOptions()
    
    if extentionsGroup is not None:
        for opt in extentionsGroup.option_list:
            if opt.dest == 'active_extentions':
                continue
            setattr(extentionOpts, opt.dest, 
                    getattr(options, opt.dest))

    #TODO: The ideal would be to pass a file like object for the second
    # argument and get rid of the userff and username arguments to this function.
    # This would also do away with the redundent checks and such in 
    # the Forcefield constructor.
    header, lines, missedligands = runPDB2PQR(pdblist, 
                                              options.ff, 
                                              outname = options.outname,
                                              ph = options.pH,
                                              verbose = options.verbose,
                                              extentions = options.active_extentions,
                                              ententionOptions = extentionOpts,
                                              clean = options.clean,
                                              neutraln = options.neutraln,
                                              neutralc = options.neutralc,
                                              ligand = options.ligand,
                                              assign_only = options.assign_only,
                                              chain = options.chain,
                                              debump = options.debump,
                                              opt = options.opt,
                                              typemap = options.typemap,
                                              userff = userfffile,
                                              usernames = usernamesfile,
                                              ffout = options.ffout)
    
    # Print the PQR file
    outfile = open(outpath,"w")
    outfile.write(header)
    # Adding whitespaces if --whitespace is in the options
    for line in lines:
        if options.whitespace: 
            if line[0:4] == 'ATOM':
                newline = line[0:16] + ' ' + line[16:38] + ' ' + line[38:46] + ' ' + line[46:]
                outfile.write(newline)
            elif line[0:6] == 'HETATM':
                newline = line[0:16] + ' ' + line[16:38] + ' ' + line[38:46] + ' ' + line[46:]
                outfile.write(newline)
        else: 
            outfile.write(line)
    outfile.close()

    if options.input:
        from .src import inputgen
        from .src import psize
        method = "mg-auto"
        size = psize.Psize()
        size.parseInput(outpath)
        size.runPsize(outpath)
        async = 0 # No async files here!
        input = inputgen.Input(outpath, size, method, async)
        input.printInputFiles()
        input.dumpPickle()


if __name__ == "__main__":
    mainCommand(sys.argv)
