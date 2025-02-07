'''
See more here: http://www.pymolwiki.org/index.php/apbsplugin


# TODO:

#  - Fold in ApbsInterface.py
#
#  - Check to see if the selection from the main page is actually an
#    object. If it is, select it by default on the visualization pane.
#
#  - Make sure there's a warning for when PDB2PQR decides to ignore
#    things.
#
# Under consideration
#
#  - Add support for dual core machines via mpi versions and pdime
#
#  - Deal with MSE like util.py protein_assign_charges_and_radii()

# Done
#  - provide diff for pdb2pqr freemol
#  - use remove_alt to count alternate atom locations and warn the user
#  - Note to users that they should remove freemol's pymol.exe on OS X.
#  - Default to calling psize.py and pdb2pqr rather than our internals.
#  - Check for environment variables for APBS_BINARY and APBS_PSIZE
#

### (all) and resn glu and resi 154+157
### flag ignore, atom-selection, clear

# APBS TOOLS Copyright Notice
# ============================
#
# The APBS TOOLS source code is copyrighted, but you can freely use and
# copy it as long as you don't change or remove any of the copyright
# notices.
#
# ----------------------------------------------------------------------
# APBS TOOLS is Copyright (C) 2009 by Michael G. Lerner
#
#                        All Rights Reserved
#
# Permission to use, copy, modify, distribute, and distribute modified
# versions of this software and its documentation for any purpose and
# without fee is hereby granted, provided that the above copyright
# notice appear in all copies and that both the copyright notice and
# this permission notice appear in supporting documentation, and that
# the name of Michael G. Lerner not be used in advertising or publicity
# pertaining to distribution of the software without specific, written
# prior permission.
#
# MICHAEL G. LERNER DISCLAIMS ALL WARRANTIES WITH REGARD TO THIS
# SOFTWARE, INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY AND
# FITNESS.  IN NO EVENT SHALL MICHAEL G. LERNER BE LIABLE FOR ANY
# SPECIAL, INDIRECT OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER
# RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF
# CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF OR IN
# CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
# ----------------------------------------------------------------------

"""

A NOTE TO USERS:

You can change the default locations for the APBS and PDB2PQR binaries
as well as the default temporary file directory below. If you set them
in this file, they will be preserved each time you load up the
plugin. Scroll down to the section entitled "Global config variables"
(no quotes) below.

A NOTE TO OTHER DEVELOPERS:

I understand that I'm giving this code away for Free, and that there's
not a ton of great sample PyMOL plugin code out there, so you're
certainly encouraged to use this as a template.  However, please
acknowledge me in some way if you do (somewhere in the comments if you
only use a little bit of code or something more if you use a lot).

Thanks.

-Michael

Features under consideration:

 - Use 'acc' to calculate solvent-accessible surface areas. We'll use
   the PyMOL 'standard' method and store this data as B-factors.

 - Deal with Zinc. Here's an email snippet from David Neuhaus:

      2) Many of the proteins I work with are zinc finger proteins,
      and back in 2006 I had some correspondence with Nathan Baker and
      Todd Dolinsky about how to handle this for .pdb files that
      contain a zinc atom - essentially by hand-editing the pdb file
      to change CYS residues to CYM, running pdb2pqr using the AMBER
      force field, restoring the zinc atom to the .pqr file by
      hand-editing (pdb2pqr stripped it out, so I cut-and-paste back
      from the original .pdb file), and hand-editing the .pqr file
      charge on the zinc to +2, and the radius to 1.2.  I haven't yet
      tested such a hand-made .pqr file for a zinc finger protein yet
      with your plugin, but I am assuming it will work as before
      (selected via "Choose Externally Generated PQR").  I guess this
      would still be the only way to achieve this workflow with your
      new plugin, or might there be some clever way of scripting any
      of this?  I'd be happy to send further details if you are
      interested - but I appreciate also that even if it is possible,
      it might well be more trouble to implement than it is worth.

 - Force users to click through a dialog box telling them which atoms
   are being ignored in the PQR file.

Known hacks:


1. (code in execute() )There's a bug in the version of APBS shipped
   with Ubuntu 9.10 (version 1.1.0) that causes the name to become
   foo-PE0.dx instead of foo.dx. This would normally only occur in
   mg-para calcs or MPI versions of apbs. It's clearly bug-possible,
   but we will check for foo-PE0 if we can't find foo.dx.

2. We look for dylib errors in the APBS executable that's shipped with
   freemol on OS X. Code in get_default()'s verify().

3. We play some weird tricks to import pdb2pqr. They're documented,
   but the first import gets pdb2pqr itself, and the second gets the
   data directories containing the force fields. They're required
   because OS X launches MacPyMOL without running .bash_profile or
   .bashrc.

"""
'''




INCLUDEWEBAPBS = False

DEBUG = 1

APBS_DEFAULT = True

import tempfile
import os
import math
import re
import sys

if sys.version_info[0] < 3:
    import tkinter
    from tkinter import *
else:
    import tkinter as Tkinter
    from tkinter import *

import Pmw
import distutils.spawn  # used for find_executable
import traceback
import pymol
###!!! Edited for Pymol-script-repo !!!###
import subprocess
###!!!------------------------------!!!###

#
# Global config variables
#
# To change the default locations, change these to something like
# APBS_BINARY_LOCATION = '/opt/bin/'
#
APBS_BINARY_LOCATION = None  # corresponding environment variable: APBS_BINARY_DIR
APBS_WEB_LOCATION = None  # corresponding environment variable: APBS_WEB_DIR
APBS_PSIZE_LOCATION = None  # corresponding environment variable: APBS_PSIZE_DIR
APBS_PDB2PQR_LOCATION = None  # corresponding environment variable: APBS_PDB2PQR_DIR
TEMPORARY_FILE_DIR = tempfile.gettempdir() # corresponding environment variable: TEMP

apbs_plea = ("IMPORTANT REQUEST: If you have not already done so, please register\n"
             "your use of the open-source Adaptive Poisson-Boltzmann Solver (APBS) at\n"
             "-> http://www.poissonboltzmann.org/\n"
             "Such proof of usage is vital in securing funding for APBS development!\n")

pdb2pqr_plea = ("IMPORTANT REQUEST: If you have not already done so, please register\n"
                "your use of the open-source PDB2PQR at\n"
                "-> http://www.poissonboltzmann.org/pdb2pqr/d\n"
                "Such proof of usage is vital in securing funding for PDB2PQR development!\n")
global apbs_message, pdb2pqr_message
apbs_message = """You must have APBS installed on your system."""
pdb2pqr_message = """PDB2PQR can be used to generate .PQR files."""


def get_default_location(name):
    """
    Given the name of an APBS-related binary, look in
        * pymol path,
        * freemol path,
        * user defined places,
        * the system path,
        * Known other paths (/usr/local/bin and /opt/local/bin)
    for the parameter, name.

    Some programs are verified with additional tests. In particular,
    some versions of PyMOL ship with a broken apbs.exe, so we verify
    that it can be run.

    PARAMS
        name, (string) the basename of the file we're looking for
    EXAMPLE
        get_default_location("apbs.exe")
    RETURNS
        (string) path/to/file on success or "" on failure
    NOTES
        For any program name <foo>.exe we will also search for
        <foo>. We'll search for the .exe version first. We do not
        automatically check for .exe versions of programs when .exe is
        not specified. We will do the same for <foo>.py
    """
    def verify(name, f):
        if name in 'apbs.exe apbs apbs-mpi-openmpi apbs-mpi-lammpi apbs-mpi'.split():  # maybe if 'apbs' in name ?
            # You'd think we could just check the return code, but
            # APBS doesn't return zero on success. Instead, it returns
            # things like 3328. It seems to return 5 or -5 in this
            # particular failure case, but I'm not sure we can depend
            # on that always.
            (retcode, prog_out) = run(f, '--version')
            if 'dyld: Library not loaded' in prog_out:
                print("Skipping", f, "because it appears to be broken (dyld)")
                return False
        if name in 'ApbsClient.py ApbsClient'.split():
            # The python script does seem to return 0 on success.
            # Here we just test to make sure it runs with the help
            # message properly, i.e. that it can import the things it
            # wants to import.
            (retcode, prog_out) = run(f, '')
            if retcode != 0:
                print('Bad ApbsClient.py')
                print('Program out')
                print(prog_out)
                print("Just so you know, os.system returns")
                print(os.system(f))
                print(".")
                return False
        return True
    searchDirs = []
###!!! Edited for Pymol-script-repo !!!###
    if 'PYMOL_GIT_MOD' in os.environ:
        searchDirs.append(os.path.join(os.environ['PYMOL_GIT_MOD'], "pdb2pqr", "src"))
        searchDirs.append(os.path.join(os.environ['PYMOL_GIT_MOD'], "pdb2pqr"))
    if sys.platform.startswith('win') and 'PYMOL_GIT_MOD' in os.environ:
        searchDirs.append(os.path.join(os.environ['PYMOL_GIT_MOD'], "APBS1_3_0"))
    elif sys.platform.startswith('win'):
        searchDirs.append("C:\\")
###!!!------------------------------!!!###
    # Previous order was A B C D
    # D
    for x in 'APBS_BINARY_DIR APBS_WEB_DIR APBS_PSIZE_DIR APBS_PDB2PQR_DIR'.split():
        if x in os.environ:
            searchDirs.append(os.environ[x])
    # C
    for x in (APBS_BINARY_LOCATION, APBS_WEB_LOCATION, APBS_PSIZE_LOCATION, APBS_PDB2PQR_LOCATION):
        if x != None and x != "":
            searchDirs.append(x)
    # A
    if "FREEMOL" in os.environ:
        searchDirs.append(os.environ["FREEMOL"])
    # B
    if "PYMOL_PATH" in os.environ:
        searchDirs.append(os.path.join(os.environ["PYMOL_PATH"], "ext", "bin"))
        searchDirs.append(os.path.join(os.environ["PYMOL_PATH"], "freemol", "bin"))
        searchDirs.append(os.path.join(os.environ["PYMOL_PATH"], "freemol", "share", "apbs"))
        searchDirs.append(os.path.join(os.environ["PYMOL_PATH"], "freemol", "share", "pdb2pqr"))

    # OTHER KNOWN PATHS WHERE PROGRAMS RESIDE

    # This must come before /sw/bin (which may also be in PATH) in
    # order for our pdb2pqr importing to work
    # correctly. /sw/bin/pdb2pqr just calls through to this.
    searchDirs.append(os.path.join("/sw", "share", "pdb2pqr"))
    searchDirs.append(os.path.join("/sw", "share", "apbs", "tools", "manip"))
    searchDirs.append(os.path.join("/sw", "share", "apbs-mpi-openmpi", "tools", "manip"))
    searchDirs.append(os.path.join("/sw", "share", "apbs-mpi-lammpi", "tools", "manip"))
    searchDirs.append(os.path.join("/usr", "local", "share", "tools", "manip"))

    searchDirs.extend(os.environ["PATH"].split(":"))
    searchDirs.append(os.path.join("/usr", "local", "bin"))
    searchDirs.append(os.path.join("/opt", "local", "bin"))
    searchDirs.append(os.path.join("/sw", "bin"))

    # This comes last because it must reset everything. Temp is
    # different because it's just a directory to store things, not
    # for finding things to run.
    if name == "temp":
        searchDirs = []
        if 'TEMP' in os.environ:
            searchDirs.append(os.environ['TEMP'])
        if TEMPORARY_FILE_DIR != None and TEMPORARY_FILE_DIR != "":
            searchDirs.append(TEMPORARY_FILE_DIR)
        searchDirs.append("/tmp")
        searchDirs.append(".")

    # print "Search dirs",searchDirs  ###!!!

    if DEBUG:
        # print "get_default_location will search the following: ", searchDirs   ###!!!
        pass  # !!!
    for d in searchDirs:
        if name == "temp":
            f = d           # just search for the directory
            if os.path.isdir(f):
                return f
        else:
            f = os.path.join(d, name)  # make path/name.py
            if DEBUG:
                print("trying",f)
            if os.path.exists(f) and verify(name, f):
                return f
            elif name.endswith('.exe'):
                f = os.path.join(d, name[:-4])  # make path/name.exe
                if DEBUG:
                    print("trying",f)
                if os.path.exists(f) and verify(name, f):
                    return f
            elif name.endswith('.py'):
                f = os.path.join(d, name[:-3])  # make path/name
                if DEBUG:
                    print("trying",f)
                if os.path.exists(f) and verify(name, f):
                    return f
    print("Could not find default location for file: %s" % name)
    return ""


def __init__(self):
    """
    Init PyMOL, by adding APBSTools to the GUI under Plugins

    Creates the APBS widget/notebook.  Once the event is received,
    we create a new instance of APBSTools2 which is a Pmw, which upon
    creation shows itself.
    """
    self.menuBar.addmenuitem('Plugin', 'command',
                             'Launch APBS Tools2.1',
                             label='APBS Tools2.1...',
                             command=lambda s=self: APBSTools2(s))


def run(prog, args):
    '''
    wrapper to handle spaces on windows.
    prog is the full path to the program.
    args is a string that we will split up for you.
        or a tuple.  or a list. your call.

    return value is (retval,prog_out)

    e.g.

    (retval,prog_out) = run("/bin/ls","-al /tmp/myusername")
    '''
    import subprocess
    import tempfile

    if type(args) == type(''):
        args = tuple(args.split())
    elif type(args) in (type([]), type(())):
        args = tuple(args)
    args = (prog,) + args

    try:
        output_file = tempfile.TemporaryFile(mode="w+")  # <-- shouldn't this point to the temp dir
    except IOError:
        print("Error opening output_file when trying to run the APBS command.")

    if DEBUG:
        print("Running:\n\tprog=%s\n\targs=%s" % (prog, args))
    retcode = subprocess.call(args, stdout=output_file.fileno(), stderr=subprocess.STDOUT)
    output_file.seek(0)
    #prog_out = output_file.read()
    prog_out = ''.join(output_file.readlines())
    output_file.close()  # windows doesn't do this automatically
    if DEBUG:
        print("Results were:")
        print("Return value:", retcode)
        print("Output:")
        print(prog_out)
    return (retcode, prog_out)


class util:

    """
    A quick collection of utility functions.
    """
    #@staticmethod
    def getMolecules():
        """returns all molecules that PyMOL knows about"""
        return [i for i in pymol.cmd.get_names() if pymol.cmd.get_type(i) == 'object:molecule']
    getMolecules = staticmethod(getMolecules)
    #@staticmethod

    def getMaps():
        """returns all maps that PyMOL knows about"""
        return [i for i in pymol.cmd.get_names() if pymol.cmd.get_type(i) == 'object:map']
    getMaps = staticmethod(getMaps)
    # def hasAlt(sel):
    #    """returns true if non-standard locations (rotamers) are present for this selection"""
    #    return cmd.count_atoms(sel + " and not alt ''")!=0
    #hasAlt = staticmethod(hasAlt)

util = util()

##############################################################################
##############################################################################
###                                                                        ###
###       ApbsInterface                                                    ###
###                                                                        ###
##############################################################################
##############################################################################


def getApbsInputFile(pqr_filename,
                     grid_points,
                     cglen,
                     fglen,
                     cent,
                     apbs_mode,
                     bcfl,
                     ion_plus_one_conc, ion_plus_one_rad,
                     ion_minus_one_conc, ion_minus_one_rad,
                     ion_plus_two_conc, ion_plus_two_rad,
                     ion_minus_two_conc, ion_minus_two_rad,
                     interior_dielectric, solvent_dielectric,
                     chgm,
                     srfm,
                     solvent_radius,
                     system_temp,
                     sdens,
                     dx_filename,
                     ):
    print("Getting APBS input")
    # print "system_temp",system_temp,type(system_temp)
    # print "sdens",sdens,type(sdens)
    #
    # How shall we set up the grid?  We'll use cglen, fglen, cgcent, fgcent
    # and dime.
    # This allows people to automate things (e.g. "Alanine scanning")
    #

    #
    # New template using mg-auto
    # See http://agave.wustl.edu/apbs/doc/api/html/#mg-auto
    #

    apbs_template = """#
# Note that most of the comments here were taken from sample
# input files that came with APBS.  You can find APBS at
# http://agave.wustl.edu/apbs/
# Note that APBS is GPL'd code.
#
read
    mol pqr %s       # read molecule 1
end
elec
    mg-auto
    dime   %d %d %d  # number of find grid points
                     # calculated by psize.py
    cglen   %f %f %f # coarse mesh lengths (A)
    fglen   %f %f %f # fine mesh lengths (A)
                     # calculated by psize.py
    cgcent %f %f %f  # (could also give (x,y,z) form psize.py) #known center
    fgcent %f %f %f  # (could also give (x,y,z) form psize.py) #known center
    %s               # solve the full nonlinear PBE with npbe
    #lpbe            # solve the linear PBE with lpbe
    bcfl %s          # Boundary condition flag
                     #  0 => Zero
                     #  1 => Single DH sphere
                     #  2 => Multiple DH spheres
                     #  4 => Focusing
                     #
    #ion 1 0.000 2.0 # Counterion declaration:
    ion charge  1 conc %f radius %f     # Counterion declaration:
    ion charge -1 conc %f radius %f     # ion <charge> <conc (M)> <radius>
    ion charge  2 conc %f radius %f     # ion <charge> <conc (M)> <radius>
    ion charge -2 conc %f radius %f     # ion <charge> <conc (M)> <radius>
    pdie %f          # Solute dielectric
    sdie %f          # Solvent dielectric
    chgm %s          # Charge disc method
                     # 0 is linear splines
                     # 1 is cubic b-splines
    mol 1            # which molecule to use
    srfm smol        # Surface calculation method
                     #  0 => Mol surface for epsilon;
                     #       inflated VdW for kappa; no
                     #       smoothing
                     #  1 => As 0 with harmoinc average
                     #       smoothing
                     #  2 => Cubic spline
    srad %f          # Solvent radius (1.4 for water)
    swin 0.3         # Surface cubic spline window .. default 0.3
    temp %f          # System temperature (298.15 default)
    sdens %f         # Specify the number of grid points per square-angstrom to use in Vacc object. Ignored when srad is 0.0 (see srad) or srfm is spl2 (see srfm). There is a direct correlation between the value used for the Vacc sphere density, the accuracy of the Vacc object, and the APBS calculation time. APBS default value is 10.0.
    #gamma 0.105      # Surface tension parameter for apolar forces (in kJ/mol/A^2)
                     # only used for force calculations, so we don't care, but
                     # it *used to be* always required, and 0.105 is the default
    calcenergy no    # Energy I/O to stdout
                     #  0 => don't write out energy
                     #  1 => write out total energy
                     #  2 => write out total energy and all
                     #       components
    calcforce no     # Atomic forces I/O (to stdout)
                     #  0 => don't write out forces
                     #  1 => write out net forces on molecule
                     #  2 => write out atom-level forces
    write pot dx %s  # What to write .. this says write the potential in dx
                     # format to a file.
end
quit

"""
    return apbs_template % (pqr_filename,
                            grid_points[0], grid_points[1], grid_points[2],
                            cglen[0], cglen[1], cglen[2],
                            fglen[0], fglen[1], fglen[2],
                            cent[0], cent[1], cent[2],
                            cent[0], cent[1], cent[2],
                            apbs_mode,
                            bcfl,
                            ion_plus_one_conc, ion_plus_one_rad,
                            ion_minus_one_conc, ion_minus_one_rad,
                            ion_plus_two_conc, ion_plus_two_rad,
                            ion_minus_two_conc, ion_minus_two_rad,
                            interior_dielectric, solvent_dielectric,
                            chgm,
                            solvent_radius,
                            system_temp,
                            sdens,
                            dx_filename,
                            )


##############################################################################
##############################################################################
###                                                                        ###
###       PluginCode                                                       ###
###                                                                        ###
##############################################################################
##############################################################################


class APBSTools2:
    # The current goal is to factor all of the APBS-specific code into
    # an ApbsInterface class.  The functions defined here before
    # __init__, as well as the functions defined on the various
    # Panels/Panes, will call through to self.ApbsInterface.

    def setPqrFile(self, name):
        print(" APBS Tools: set pqr file to", name)
        self.pqr_to_use.setvalue(name)
        self.radiobuttons.setvalue('Use another PQR')

    def getPqrFilename(self):
        if self.radiobuttons.getvalue() != 'Use another PQR':
            return self.pymol_generated_pqr_filename.getvalue()
        else:
            return self.pqr_to_use.getvalue()

    def setPsizeLocation(self, value):
        self.psize.setvalue(value)

    def setBinaryLocation(self, value):
        self.binary.setvalue(value)

    def setWebApbsLocation(self, value):
        self.webapbs.setvalue(value)

    def setPdb2pqrLocation(self, value):
        self.pdb2pqr.setvalue(value)

    def setPymolGeneratedPqrFilename(self, value):
        self.pymol_generated_pqr_filename.setvalue(value)

    def setPymolGeneratedPdbFilename(self, value):
        self.pymol_generated_pdb_filename.setvalue(value)

    def setPymolGeneratedDxFilename(self, value):
        self.pymol_generated_dx_filename.setvalue(value)

    def setPymolGeneratedInFilename(self, value):
        self.pymol_generated_in_filename.setvalue(value)

    def getPymolGeneratedPqrFilename(self):
        return self.pymol_generated_pqr_filename.getvalue()

    def getPymolGeneratedPdbFilename(self):
        return self.pymol_generated_pdb_filename.getvalue()

    def getPymolGeneratedDxFilename(self):
        return self.pymol_generated_dx_filename.getvalue()

    def getPymolGeneratedInFilename(self):
        return self.pymol_generated_in_filename.getvalue()
    defaults = {
        "interior_dielectric": 2.0,
        "solvent_dielectric": 78.0,
        "solvent_radius": 1.4,
        "system_temp": 310.0,
        "apbs_mode": 'Linearized Poisson-Boltzmann Equation',
        "ion_plus_one_conc": 0.15,
        "ion_plus_one_rad": 2.0,
        "ion_plus_two_conc": 0.0,
        "ion_plus_two_rad": 2.0,
        "ion_minus_one_conc": 0.15,
        "ion_minus_one_rad": 1.8,
        "ion_minus_two_conc": 0.0,
        "ion_minus_two_rad": 2.0,
        #"max_mem_allowed" : 400,
        "max_mem_allowed": 1500,
        "potential_at_sas": 1,
        "surface_solvent": 0,
        "show_surface_for_scanning": 1,
        #"grid_buffer" : 0,
        #"grid_buffer" : 20,
        "bcfl": 'Single DH sphere',  # Boundary condition flag for APBS
        "sdens": 10.0,  # Specify the number of grid points per
                       # square-angstrom to use in Vacc
                       # object. Ignored when srad is 0.0 (see srad)
                       # or srfm is spl2 (see srfm). There is a direct
                       # correlation between the value used for the
                       # Vacc sphere density, the accuracy of the Vacc
                       # object, and the APBS calculation time. APBS
                       # default value is 10.0.
        "chgm": 'Cubic B-splines',  # Charge disc method for APBS
    }

    def __init__(self, app):
        self.parent = app.root

        # Create the dialog.
        self.dialog = Pmw.Dialog(self.parent,
                                 buttons=('Register APBS Use', 'Register PDB2PQR Use', 'Set grid', 'Run APBS', 'Exit APBS tools'),
                                 title = 'PyMOL APBS Tools',
                                 command = self.execute)
        self.dialog.withdraw()

        if sys.platform.startswith('win'):
            # avoid crash on Windows with PyMOL 2.0 (PyQt)
            self.dialog.resizable(0, 0)

        Pmw.setbusycursorattributes(self.dialog.component('hull'))

        w = tkinter.Label(self.dialog.interior(),
                          text='PyMOL APBS Tools\nMichael G. Lerner, Heather A. Carlson, 2009 - http://pymolwiki.org/index.php/APBS\n(incorporates modifications by Warren L. DeLano)',
                          background='black',
                          foreground='white',
                          #pady = 20,
                          )
        w.pack(expand=1, fill='both', padx=4, pady=4)

        self.notebook = Pmw.NoteBook(self.dialog.interior())
        self.notebook.pack(fill='both', expand=1, padx=10, pady=10)

        # Set up the Main page
        page = self.notebook.add('Main')
        group = Pmw.Group(page, tag_text='Main options')
        group.pack(fill='both', expand=1, padx=10, pady=5)
        self.selection = Pmw.EntryField(group.interior(),
                                        labelpos='w',
                                        label_text='Selection to use: ',
                                        value='(polymer)',
                                        )
        self.map = Pmw.EntryField(group.interior(),
                                  labelpos='w',
                                  label_text='What to call the resulting map: ',
                                  value='apbs_map',
                                  )
        self.radiobuttons = Pmw.RadioSelect(group.interior(),
                                            buttontype='radiobutton',
                                            orient='vertical',
                                            labelpos='w',
                                            )
        for text in ('Use PyMOL generated PQR and existing Hydrogens and termini',
                     'Use PyMOL generated PQR and PyMOL generated Hydrogens and termini',
                     'Use another PQR',
                     'Use PDB2PQR',):
            self.radiobuttons.add(text)
        #self.radiobuttons.setvalue('Use PyMOL generated PQR and PyMOL generated Hydrogens and termini')
        self.radiobuttons.setvalue('Use PDB2PQR')

        self.pdb2pqr_options = Pmw.EntryField(group.interior(),
                                              labelpos='w',
                                              label_text='pdb2pqr command line options: ',
                                              value='--ff=AMBER',
                                              )
        self.pqr_to_use = Pmw.EntryField(group.interior(),
                                         labelpos='w',
                                         label_pyclass=FileDialogButtonClassFactory.get(self.setPqrFile, '*.pqr'),
                                         label_text='\tChoose Externally Generated PQR:',
                                         )

        for entry in (self.selection, self.map, self.radiobuttons, self.pdb2pqr_options, self.pqr_to_use):
            # for entry in (self.selection,self.map,self.radiobuttons,):
            entry.pack(fill='x', padx=4, pady=1)  # vertical

        # Set up the main "Calculation" page
        page = self.notebook.add('Configuration')

        group = Pmw.Group(page, tag_text='Dielectric Constants')
        group.grid(column=0, row=0)
        self.interior_dielectric = Pmw.EntryField(group.interior(), labelpos='w',
                                                  label_text='Protein Dielectric:',
                                                  value=str(APBSTools2.defaults['interior_dielectric']),
                                                  validate={'validator': 'real',
                                                              'min': 0, }
                                                  )
        self.solvent_dielectric = Pmw.EntryField(group.interior(), labelpos='w',
                                                 label_text='Solvent Dielectric:',
                                                 value=str(APBSTools2.defaults['solvent_dielectric']),
                                                 validate={'validator': 'real',
                                                             'min': 0, }
                                                 )
        entries = (self.interior_dielectric, self.solvent_dielectric)
        for entry in entries:
            # entry.pack(side='left',fill='both',expand=1,padx=4) # side-by-side
            entry.pack(fill='x', expand=1, padx=4, pady=1)  # vertical
        group = Pmw.Group(page, tag_text='Other')
        group.grid(column=1, row=1, columnspan=4)
        self.max_mem_allowed = Pmw.EntryField(group.interior(), labelpos='w',
                                              label_text='Maximum Memory Allowed (MB):',
                                              value=str(APBSTools2.defaults['max_mem_allowed']),
                                              validate={'validator': 'real',
                                                          'min': 1, }
                                              )
        self.apbs_mode = Pmw.OptionMenu(group.interior(),
                                        labelpos='w',
                                        label_text='APBS Mode',
                                        items=('Nonlinear Poisson-Boltzmann Equation', 'Linearized Poisson-Boltzmann Equation',),
                                        initialitem = APBSTools2.defaults['apbs_mode'],
                                        )
        self.apbs_mode.pack(fill='x', expand=1, padx=4)
        # self.apbs_mode.grid(column=0,row=0,columnspan=3)
        self.solvent_radius = Pmw.EntryField(group.interior(),
                                             labelpos='w',
                                             label_text='Solvent Radius:',
                                             validate={'validator': 'real', 'min': 0},
                                             value=str(APBSTools2.defaults['solvent_radius']),
                                             )
        self.system_temp = Pmw.EntryField(group.interior(),
                                          labelpos='w',
                                          label_text='System Temperature:',
                                          validate={'validator': 'real', 'min': 0},
                                          value=str(APBSTools2.defaults['system_temp']),
                                          )
        self.sdens = Pmw.EntryField(group.interior(),
                                    labelpos='w',
                                    label_text='Vacc sphere density (grid points/A^2)',
                                    validate={'validator': 'real', 'min': 0},
                                    value=str(APBSTools2.defaults['sdens']),
                                    )
        self.bcfl = Pmw.OptionMenu(group.interior(),
                                   labelpos='w',
                                   label_text='Boundary Condition',
                                   items=('Zero', 'Single DH sphere', 'Multiple DH spheres',),  # 'Focusing',),
                                   initialitem = APBSTools2.defaults['bcfl'],
                                   )
        self.chgm = Pmw.OptionMenu(group.interior(),
                                   labelpos='w',
                                   label_text='Charge disc method',
                                   items=('Linear', 'Cubic B-splines', 'Quintic B-splines',),
                                   initialitem = APBSTools2.defaults['chgm'],
                                   )
        self.srfm = Pmw.OptionMenu(group.interior(),
                                   labelpos='w',
                                   label_text='Surface Calculation Method',
                                   items=('Mol surf for epsilon; inflated VdW for kappa, no smoothing', 'Same, but with harmonic average smoothing', 'Cubic spline', 'Similar to cubic spline, but with 7th order polynomial'),
                                   initialitem = 'Same, but with harmonic average smoothing',
                                   )
        # for entry in (self.apbs_mode,self.system_temp,self.solvent_radius,):
        for entry in (self.max_mem_allowed, self.solvent_radius, self.system_temp, self.sdens, self.apbs_mode, self.bcfl, self.chgm, self.srfm):
            entry.pack(fill='x', expand=1, padx=4, pady=1)  # vertical

        group = Pmw.Group(page, tag_text='Ions')
        group.grid(column=0, row=1, )
        self.ion_plus_one_conc = Pmw.EntryField(group.interior(),
                                                labelpos='w',
                                                label_text='Ion Concentration (M) (+1):',
                                                validate={'validator': 'real', 'min': 0},
                                                value=str(APBSTools2.defaults['ion_plus_one_conc']),
                                                )
        self.ion_plus_one_rad = Pmw.EntryField(group.interior(),
                                               labelpos='w',
                                               label_text='Ion Radius (+1):',
                                               validate={'validator': 'real', 'min': 0},
                                               value=str(APBSTools2.defaults['ion_plus_one_rad']),
                                               )
        self.ion_minus_one_conc = Pmw.EntryField(group.interior(),
                                                 labelpos='w',
                                                 label_text='Ion Concentration (M) (-1):',
                                                 validate={'validator': 'real', 'min': 0},
                                                 value=str(APBSTools2.defaults['ion_minus_one_conc']),
                                                 )
        self.ion_minus_one_rad = Pmw.EntryField(group.interior(),
                                                labelpos='w',
                                                label_text='Ion Radius (-1):',
                                                validate={'validator': 'real', 'min': 0},
                                                value=str(APBSTools2.defaults['ion_minus_one_rad']),
                                                )
        self.ion_plus_two_conc = Pmw.EntryField(group.interior(),
                                                labelpos='w',
                                                label_text='Ion Concentration (M) (+2):',
                                                validate={'validator': 'real', 'min': 0},
                                                value=str(APBSTools2.defaults['ion_plus_two_conc']),
                                                )
        self.ion_plus_two_rad = Pmw.EntryField(group.interior(),
                                               labelpos='w',
                                               label_text='Ion Radius (+2):',
                                               validate={'validator': 'real', 'min': 0},
                                               value=str(APBSTools2.defaults['ion_plus_two_rad']),
                                               )
        self.ion_minus_two_conc = Pmw.EntryField(group.interior(),
                                                 labelpos='w',
                                                 label_text='Ion Concentration (M) (-2):',
                                                 validate={'validator': 'real', 'min': 0},
                                                 value=str(APBSTools2.defaults['ion_minus_two_conc']),
                                                 )
        self.ion_minus_two_rad = Pmw.EntryField(group.interior(),
                                                labelpos='w',
                                                label_text='Ion Radius (-2):',
                                                validate={'validator': 'real', 'min': 0},
                                                value=str(APBSTools2.defaults['ion_minus_two_rad']),
                                                )
        entries = (self.ion_plus_one_conc, self.ion_plus_one_rad,
                   self.ion_minus_one_conc, self.ion_minus_one_rad,
                   self.ion_plus_two_conc, self.ion_plus_two_rad,
                   self.ion_minus_two_conc, self.ion_minus_two_rad,
                   )
        for entry in entries:
            entry.pack(fill='x', expand=1, padx=4)

        group = Pmw.Group(page, tag_text='Coarse Mesh Length')
        group.grid(column=1, row=0)
        for coord in 'x y z'.split():
            setattr(self, 'grid_coarse_%s' % coord, Pmw.EntryField(group.interior(),
                                                               labelpos='w',
                                                               label_text=coord,
                                                               validate={'validator': 'real', 'min': 0},
                                                               value=-1,
                                                               entry_width=15,
                                                               )
                    )
            getattr(self, 'grid_coarse_%s' % coord).pack(fill='x', expand=1, padx=4, pady=1)

        group = Pmw.Group(page, tag_text='Fine Mesh Length')
        group.grid(column=2, row=0)
        for coord in 'x y z'.split():
            setattr(self, 'grid_fine_%s' % coord, Pmw.EntryField(group.interior(),
                                                             labelpos='w',
                                                             label_text=coord,
                                                             validate={'validator': 'real', 'min': 0},
                                                             value=-1,
                                                             entry_width=15,
                                                             )
                    )
            getattr(self, 'grid_fine_%s' % coord).pack(fill='x', expand=1, padx=4, pady=1)

        group = Pmw.Group(page, tag_text='Grid Center')
        group.grid(column=3, row=0)
        for coord in 'x y z'.split():
            setattr(self, 'grid_center_%s' % coord, Pmw.EntryField(group.interior(),
                                                               labelpos='w',
                                                               label_text=coord,
                                                               validate={'validator': 'real'},
                                                               value=0,
                                                               entry_width=10,
                                                               )
                    )
            getattr(self, 'grid_center_%s' % coord).pack(fill='x', expand=1, padx=4, pady=1)

        group = Pmw.Group(page, tag_text='Grid Points')
        group.grid(column=4, row=0)
        for coord in 'x y z'.split():
            setattr(self, 'grid_points_%s' % coord, Pmw.EntryField(group.interior(),
                                                               labelpos='w',
                                                               label_text=coord,
                                                               validate={'validator': 'integer', 'min': 0},
                                                               value=-1,
                                                               entry_width=8,
                                                               )
                    )
            getattr(self, 'grid_points_%s' % coord).pack(fill='x', expand=1, padx=4, pady=1)

        page.grid_rowconfigure(2, weight=1)
        page.grid_columnconfigure(5, weight=1)
        page = self.notebook.add('Program Locations')
        group = Pmw.Group(page, tag_text='Locations')
        group.pack(fill='both', expand=1, padx=10, pady=5)

        def quickFileValidation(s):
            if s == '':
                return Pmw.PARTIAL
            elif os.path.isfile(s):
                return Pmw.OK
            elif os.path.exists(s):
                return Pmw.PARTIAL
            else:
                return Pmw.PARTIAL

        def quickFileDirValidation(s):
            '''
            assumes s ends in filename
            '''
            if os.path.exists(s) and not os.path.isfile(s):
                return Pmw.PARTIAL
            if os.path.isdir(os.path.split(s)[0]):
                return Pmw.OK
            return Pmw.PARTIAL
        # Both macports and fink allow you to install MPI versions
        # now.  They change the name to apbs-mpi and apbs-mpi-openmpi
        # respectively. So, we need to check for those versions.  fink
        # also allows apbs-mpi-lammpi. It's easier to deal with that
        # here than it is to make the get_default_location check
        # recursively for everything.
        apbs_location = ''
        psize_location = ''

        try:
            import freemol.apbs
            apbs_location = freemol.apbs.get_exe_path()
            psize_location = freemol.apbs.get_psize_path()
        except:
            pass

        if not psize_location:
            psize_location = get_default_location('psize.py')
        if not apbs_location:
            apbs_location = get_default_location('apbs.exe')
        if not apbs_location:
            apbs_location = get_default_location('apbs-mpi.exe')
        if not apbs_location:
            apbs_location = get_default_location('apbs-mpi-openmpi.exe')
        if not apbs_location:
            apbs_location = get_default_location('apbs-mpi-lammpi.exe')
        self.binary = Pmw.EntryField(group.interior(),
                                     labelpos='w',
                                     label_pyclass=FileDialogButtonClassFactory.get(self.setBinaryLocation),
                                     validate={'validator': quickFileValidation, },
                                     value=apbs_location,
                                     label_text='APBS binary location:',
                                     )
        self.binary.pack(fill='x', padx=20, pady=10)
        if INCLUDEWEBAPBS:
            self.webapbs = Pmw.EntryField(group.interior(),
                                          labelpos='w',
                                          label_pyclass=FileDialogButtonClassFactory.get(self.setWebApbsLocation),
                                          validate={'validator': quickFileValidation, },
                                          value=get_default_location('ApbsClient.py'),
                                          label_text='APBS web interface location:',
                                          )
            self.webapbs.pack(fill='x', padx=20, pady=10)

        self.psize = Pmw.EntryField(group.interior(),
                                     labelpos='w',
                                     label_pyclass=FileDialogButtonClassFactory.get(self.setPsizeLocation),
                                     validate={'validator': quickFileValidation, },
                                     #value = '/usr/local/apbs-0.3.1/tools/manip/psize.py',
                                     value=psize_location,
                                     label_text='APBS psize.py location:',
                                     )
        self.psize.pack(fill='x', padx=20, pady=10)
        self.pdb2pqr = Pmw.EntryField(group.interior(),
                                       labelpos='w',
                                       label_pyclass=FileDialogButtonClassFactory.get(self.setPdb2pqrLocation),
                                       validate={'validator': quickFileValidation, },
                                       value=get_default_location('pdb2pqr.py'),
                                       label_text='pdb2pqr location:',
                                       )
        self.pdb2pqr.pack(fill='x', padx=20, pady=10)

        label = tkinter.Label(group.interior(),
                              pady=10,
                              justify=LEFT,
                              text="""
By default, the PyMOL APBS Tools will use APBS's psize.py to calculate proper grid dimensions and
spacing. This tool attempts to make the fine mesh spacing approximately 0.5 A, but will make a coarser
grid if constrained to do so by the Maximum Memory Allowed setting in the configuration pane. If
you wish this behavior, you must ensure that "APBS psize.py location" above points to a valid file.
This plugin can also calculate grid dimensions and spacing itself. If you wish that behavior, simply
delete the "APBS psize.py location" above.

By default, the PyMOL APBS Tools will use PDB2PQR to generate PQR files. Command line options for
PDB2PQR can be controlled on the Main panel. If you wish to use PDB2PQR, you must ensure that
"pdb2pqr location" above points to a valid file. PyMOL can directly generate PQR files using standard
protein residues and AMBER charges.  If wish that behavior, simply delete the "pdb2pqr location" above.
""",
                              )
        label.pack()

        page = self.notebook.add('Temp File Locations')
        group = Pmw.Group(page, tag_text='Locations')
        group.pack(fill='both', expand=1, padx=10, pady=5)
        self.pymol_generated_pqr_filename = Pmw.EntryField(group.interior(),
                                                           labelpos='w',
                                                           label_pyclass=FileDialogButtonClassFactory.get(self.setPymolGeneratedPqrFilename),
                                                           validate={'validator': quickFileDirValidation, },
                                                           label_text='Temporary PQR file: ',
                                                           value=os.path.join(get_default_location('temp'), 'pymol-generated.pqr'),
                                                           )
        self.pymol_generated_pqr_filename.pack(fill='x', padx=20, pady=10)

        self.pymol_generated_pdb_filename = Pmw.EntryField(group.interior(),
                                                           labelpos='w',
                                                           label_pyclass=FileDialogButtonClassFactory.get(self.setPymolGeneratedPdbFilename),
                                                           validate={'validator': quickFileDirValidation, },
                                                           label_text='Temporary PDB file: ',
                                                           value=os.path.join(get_default_location('temp'), 'pymol-generated.pdb'),
                                                           )
        self.pymol_generated_pdb_filename.pack(fill='x', padx=20, pady=10)

        self.pymol_generated_dx_filename = Pmw.EntryField(group.interior(),
                                                          labelpos='w',
                                                          label_pyclass=FileDialogButtonClassFactory.get(self.setPymolGeneratedDxFilename),
                                                          validate={'validator': quickFileDirValidation, },
                                                          label_text='Temporary DX file: ',
                                                          value=os.path.join(get_default_location('temp'), 'pymol-generated.dx'),
                                                          )
        self.pymol_generated_dx_filename.pack(fill='x', padx=20, pady=10)

        self.pymol_generated_in_filename = Pmw.EntryField(group.interior(),
                                                           labelpos='w',
                                                           label_pyclass=FileDialogButtonClassFactory.get(self.setPymolGeneratedInFilename),
                                                           validate={'validator': quickFileDirValidation, },
                                                           value=os.path.join(get_default_location('temp'), 'pymol-generated.in'),
                                                           label_text='APBS input file:')
        self.pymol_generated_in_filename.pack(fill='x', padx=20, pady=10)
        label = tkinter.Label(group.interior(),
                              pady=10,
                              justify=LEFT,
                              text="""You can automatically set the default location of temporary files
by setting the environment variable TEMP.
""",
                              )
        label.pack()
        # Create the visualization pages
        page = self.notebook.add('Visualization (1)')
        group = VisualizationGroup(page, tag_text='Visualization', visgroup_num=1)
        self.visualization_group_1 = group
        group.pack(fill='both', expand=1, padx=10, pady=5)

        page = self.notebook.add('Visualization (2)')
        group = VisualizationGroup(page, tag_text='Visualization', visgroup_num=2)
        self.visualization_group_2 = group
        group.pack(fill='both', expand=1, padx=10, pady=5)

        # Create a couple of other empty pages
        page = self.notebook.add('About')
        group = Pmw.Group(page, tag_text='About PyMOL APBS Tools')
        group.pack(fill='both', expand=1, padx=10, pady=5)
        text = """This plugin integrates PyMOL (http://PyMOL.org/) with APBS (http://www.poissonboltzmann.org/apbs/).

Documentation may be found at
http://pymolwiki.org/index.php/APBS
and
http://www.pymolwiki.org/index.php/Apbsplugin

It requires APBS version >= 0.5.0.

In the simplest case,

1) Load a structure into PyMOL.
2) Start this plugin.
3) Make sure that the path to the APBS binary is correct on the "Program Locations" tab.
4) Click the "Set grid" button to set up the grid.
5) Click the "Run APBS" button.

Many thanks to
 - Warren DeLano and Jason Vertrees for everything involving PyMOL
 - Nathan Baker, Todd Dolinsky and David Gohara for everything involving APBS
 - William G. Scott for help with several APBS+PyMOL issues and documentation

Created by Michael Lerner (http://pymolwiki.org/index.php/User:Mglerner) mglerner@gmail.com
Carlson Group, University of Michigan (http://www.umich.edu/~carlsonh/)

Please contact the author and cite this plugin if you use it in a publication.

Citation for this plugin:
    MG Lerner and HA Carlson. APBS plugin for PyMOL, 2006,
    University of Michigan, Ann Arbor.

Citation for PyMOL may be found here:
    http://pymol.sourceforge.net/faq.html#CITE

Citation for APBS:
    Baker NA, Sept D, Joseph S, Holst MJ, McCammon JA. Electrostatics of
    nanosystems: application to microtubules and the ribosome. Proc.
    Natl. Acad. Sci. USA 98, 10037-10041 2001.

Citation for PDB2PQR:
    Dolinsky TJ, Nielsen JE, McCammon JA, Baker NA.
    PDB2PQR: an automated pipeline for the setup, execution,
    and analysis of Poisson-Boltzmann electrostatics calculations.
    Nucleic Acids Research 32 W665-W667 (2004).
"""
        #
        # Add this as text in a scrollable pane.
        # Code based on Caver plugin
        # http://loschmidt.chemi.muni.cz/caver/index.php
        #
        interior_frame = Frame(group.interior())
        bar = Scrollbar(interior_frame,)
        text_holder = Text(interior_frame, yscrollcommand=bar.set, background="#ddddff", font="Times 14")
        bar.config(command=text_holder.yview)
        text_holder.insert(END, text)
        text_holder.pack(side=LEFT, expand="yes", fill="both")
        bar.pack(side=LEFT, expand="yes", fill="y")
        interior_frame.pack(expand="yes", fill="both")

        self.notebook.setnaturalsize()
        self.showAppModal()

    def showAppModal(self):
        # self.dialog.activate() #geometry = 'centerscreenfirst',globalMode = 'nograb')
        self.dialog.show()

    def generatePqrFile(self):
        ''' Wrapper for all of our PQR generation routines.

        - Generate PQR file if necessary
        - Return False if unsuccessful, True if successful.

        - Clean up PQR file if we generated it (the
          generate... functions are required to do this.).
        '''
        if self.radiobuttons.getvalue() == 'Use another PQR':
            pass
        elif self.radiobuttons.getvalue() == 'Use PDB2PQR':
            if DEBUG:
                print("GENERATING PQR FILE via PDB2PQR")
            good = self._generatePdb2pqrPqrFile()
            if not good:
                if DEBUG:
                    print("Could not generate PDB2PQR file.  _generatePdb2pqrPqrFile failed.")
                return False
            if DEBUG:
                print("GENERATED")
        else:  # it's one of the pymol-generated options
            if DEBUG:
                print("GENERATING PQR FILE via PyMOL")
            good = self._generatePymolPqrFile()
            if not good:
                if DEBUG:
                    print("Could not generate the PyMOL-basd PQR file.  generatePyMOLPqrFile failed.")
                return False
            if DEBUG:
                print("GENERATED")
        return True

    def execute(self, result, refocus=True):
        if result == 'Register APBS Use':
            import webbrowser
            webbrowser.open("http://www.poissonboltzmann.org/")
        elif result == 'Register PDB2PQR Use':
            import webbrowser
            webbrowser.open("http://www.poissonboltzmann.org/")
        elif result == 'Run APBS':
            good = self.generateApbsInputFile()
            if not good:
                if DEBUG:
                    print("ERROR: Something went wrong trying to generate the APBS input file.")
                return False
            # START
            good = self.generatePqrFile()
            if not good:
                return False
            # Stop
            if os.path.exists(self.pymol_generated_dx_filename.getvalue()):
                try:
                    os.unlink(self.pymol_generated_dx_filename.getvalue())
                except:
                    traceback.print_exc()
                    pass
            #command = "%s %s" % (self.binary.getvalue(),self.pymol_generated_in_filename.getvalue())
            # os.system(command)

            #
            # NOTE: if there are spaces in the directory name that contains pymol_generated_in_filename,
            #       our run command will want to split it up into several arguments if we pass it as a
            #       string.  So, we pass it as a tuple.
            #
            (retval, progout) = run(self.binary.getvalue(), (self.pymol_generated_in_filename.getvalue(),))
            if refocus:
                #
                # There's a bug in the version of APBS shipped with
                # Ubuntu 9.10 (version 1.1.0) that causes the name to
                # become foo-PE0.dx instead of foo.dx. This would
                # normally only occur in mg-para calcs or MPI versions
                # of apbs. It's clearly bug-possible, but we will
                # check for foo-PE0 if we can't find foo.dx.
                #
                fname = self.pymol_generated_dx_filename.getvalue()
                if not os.path.isfile(fname):
                    print("Could not find", fname, "so searching for", end=' ')
                    fname = '-PE0'.join(os.path.splitext(fname))
                    print(fname)
                pymol.cmd.load(fname,self.map.getvalue())
                self.visualization_group_1.refresh()
                self.visualization_group_2.refresh()
                self.notebook.tab('Visualization (1)').focus_set()
                self.notebook.selectpage('Visualization (1)')
        elif result == 'Set grid':
            self.runPsize()
        else:
            #
            # Doing it this way takes care of clicking on the x in the top of the
            # window, which as result set to None.
            #
            global APBS_BINARY_LOCATION, APBS_PSIZE_LOCATION, APBS_WEB_LOCATION
            APBS_BINARY_LOCATION = self.binary.getvalue()
            if INCLUDEWEBAPBS:
                APBS_WEB_LOCATION = self.webapbs.getvalue()
            APBS_PSIZE_LOCATION = self.psize.getvalue()
            self.quit()

    def quit(self):
        self.dialog.destroy()  # stops CPU hogging, perhaps fixes Ubuntu bug MGL

    def runPsize(self):
        class NoPsize(Exception):
            pass

        class NoPDB(Exception):
            pass
        try:
            if not self.psize.valid():
                raise NoPsize
            good = self.generatePqrFile()
            if not good:
                print("Could not generate PQR file!")
                return False
            pqr_filename = self.getPqrFilename()
            try:
                f = open(pqr_filename, 'r')
                f.close()
            except:
                raise NoPDB

            #
            # Do some magic to load the psize module
            #
            import imp
            f, fname, description = imp.find_module('psize', [os.path.split(self.psize.getvalue())[0]])
            psize = imp.load_module('psize', f, fname, description)
            # WLD
            sel = "((%s) or (neighbor (%s) and hydro))" % (
                self.selection.getvalue(), self.selection.getvalue())

            if pymol.cmd.count_atoms(self.selection.getvalue() + " and not alt ''") != 0:
                print("WARNING: You have alternate locations for some of your atoms!")
            # pymol.cmd.save(pqr_filename,sel) # Pretty sure this was a bug. No need to write it when it's externally generated.
            f.close()

            size = psize.Psize()
            size.setConstant('gmemceil', int(self.max_mem_allowed.getvalue()))
            size.runPsize(pqr_filename)
            coarsedim = size.getCoarseGridDims()  # cglen
            finedim = size.getFineGridDims()  # fglen
            # could use procgrid for multiprocessors
            finegridpoints = size.getFineGridPoints()  # dime
            center = size.getCenter()  # cgcent and fgcent
            print("APBS's psize.py was used to calculated grid dimensions")
        except (NoPsize, ImportError, AttributeError) as e:
            print(e)
            print("This plugin was used to calculated grid dimensions")
            #
            # First, we need to get the dimensions of the molecule
            #
            # WLD
            sel = "((%s) or (neighbor (%s) and hydro))" % (
                self.selection.getvalue(), self.selection.getvalue())
            model = pymol.cmd.get_model(sel)
            mins = [None, None, None]
            maxs = [None, None, None]
            for a in model.atom:
                for i in (0, 1, 2):
                    if mins[i] is None or (a.coord[i] - a.elec_radius) < mins[i]:
                        mins[i] = a.coord[i] - a.elec_radius
                    if maxs[i] is None or (a.coord[i] + a.elec_radius) > maxs[i]:
                        maxs[i] = a.coord[i] + a.elec_radius
            if None in mins or None in maxs:
                error_dialog = Pmw.MessageDialog(self.parent,
                                                 title='Error',
                                                 message_text="No atoms were in your selection",
                                                 )
                junk = error_dialog.activate()
                return False

            box_length = [maxs[i] - mins[i] for i in range(3)]
            center = [(maxs[i] + mins[i]) / 2.0 for i in range(3)]
            #
            # psize expands the molecular dimensions by CFAC (which defaults
            # to 1.7) for the coarse grid
            #
            CFAC = 1.7
            coarsedim = [length * CFAC for length in box_length]

            #
            # psize also does something strange .. it adds a buffer FADD to
            # the box lengths to get the fine lengths.  you'd think it'd also
            # have FFAC or CADD, but we'll mimic it here.  it also has the
            # requirement that the fine grid lengths must be <= the corase
            # grid lengths.  FADD defaults to 20.
            #
            FADD = 20
            finedim = [min(coarsedim[i], box_length[i] + FADD) for i in range(3)]

            #
            # And now the hard part .. setting up the grid points.
            # From the APBS manual at http://agave.wustl.edu/apbs/doc/html/user-guide/x594.html#dime
            # we have the formula
            # n = c*2^(l+1) + 1
            # where l is the number of levels in the MG hierarchy.  The typical
            # number of levels is 4.
            #
            nlev = 4
            mult_fac = 2 ** (nlev + 1)  # this will typically be 2^5==32
            # and c must be a non-zero integer

            # If we didn't have to be c*mult_fac + 1, this is what our grid points
            # would look like (we use the ceiling to be on the safe side .. it never
            # hurts to do too much.
            SPACE = 0.5  # default desired spacing = 0.5A
            # desired_points = [int(math.ceil(flen / SPACE)) for flen in finedim] # as integers
            desired_points = [flen / SPACE for flen in finedim]  # as floats .. use int(math.ceil(..)) later

            # Now we set up our cs, taking into account mult_fac
            # (we use the ceiling to be on the safe side .. it never hurts to do
            # too much.)
            cs = [int(math.ceil(dp / mult_fac)) for dp in desired_points]

            finegridpoints = [mult_fac * c + 1 for c in cs]

            print("cs", cs)
            print("finedim", finedim)
            print("nlev", nlev)
            print("mult_fac", mult_fac)
            print("finegridpoints", finegridpoints)

        except NoPDB:
            error_dialog = Pmw.MessageDialog(self.parent,
                                             title='Error',
                                             message_text="Please set a temporary PDB file location",
                                             )
            junk = error_dialog.activate()
            return False

        if (finegridpoints[0] > 0) and (finegridpoints[1] > 0) and (finegridpoints[2] > 0):
            max_mem_allowed = float(self.max_mem_allowed.getvalue())

            def memofgrid(finegridpoints):
                return 200. * float(finegridpoints[0] * finegridpoints[1] * finegridpoints[2]) / 1024. / 1024

            def gridofmem(mem):
                return mem * 1024. * 1024. / 200.
            max_grid_points = gridofmem(max_mem_allowed)
            print("Estimated memory usage", memofgrid(finegridpoints), 'MB out of maximum allowed', max_mem_allowed)
            if memofgrid(finegridpoints) > max_mem_allowed:
                print("Maximum memory usage exceeded.  Old grid dimensions were", finegridpoints)
                product = float(finegridpoints[0] * finegridpoints[1] * finegridpoints[2])
                factor = pow(max_grid_points / product, 0.333333333)
                finegridpoints[0] = (int(factor * finegridpoints[0] / 2)) * 2 + 1
                finegridpoints[1] = (int(factor * finegridpoints[1] / 2)) * 2 + 1
                finegridpoints[2] = (int(factor * finegridpoints[2] / 2)) * 2 + 1
                print("Fine grid points rounded down from", finegridpoints)
                #
                # Now we have to make sure that this still fits the equation n = c*2^(l+1) + 1.  Here, we'll
                # just assume nlev == 4, which means that we need to be (some constant times 32) + 1.
                #
                # This can be annoying if, e.g., you're trying to set [99, 123, 99] .. it'll get rounded to [99, 127, 99].
                # First, I'll try to round to the nearest 32*c+1.  If that doesn't work, I'll just round down.
                #
                new_gp = [0, 0, 0]
                for i in 0, 1, 2:
                    dm = divmod(finegridpoints[i] - 1, 32)
                    if dm[1] > 16:
                        new_gp[i] = (dm[0] + 1) * 32 + 1
                    else:
                        new_gp[i] = (dm[0]) * 32 + 1
                new_prod = new_gp[0] * new_gp[1] * new_gp[2]
                # print "tried new_prod",new_prod,"max_grid_points",max_grid_points,"small enough?",new_prod <= max_grid_points
                if new_prod <= max_grid_points:
                    # print "able to round to closest"
                    for i in 0, 1, 2:
                        finegridpoints[i] = new_gp[i]
                else:
                    # darn .. have to round down.
                    # Note that this can still fail a little bit .. it can only get you back down to the next multiple <= what was in
                    # finegridpoints.  So, if finegridpoints was exactly on a multiple, like (99,129,99), you'll get rounded down to
                    # (99,127,99), which is still just a bit over the default max of 1200000.  I think that's ok.  It's the rounding error
                    # from int(factor*finegridpoints ..) above, but it'll never be a huge error.  If we needed to, we could easily fix this.
                    #
                    # print "rounding down more"
                    for i in 0, 1, 2:
                        # print finegridpoints[i],divmod(finegridpoints[i] - 1,32),
                        finegridpoints[i] = divmod(finegridpoints[i] - 1, 32)[0] * 32 + 1
                print("New grid dimensions are", finegridpoints)
        print(" APBS Tools: coarse grid: (%5.3f,%5.3f,%5.3f)" % tuple(coarsedim))
        self.grid_coarse_x.setvalue(coarsedim[0])
        self.grid_coarse_y.setvalue(coarsedim[1])
        self.grid_coarse_z.setvalue(coarsedim[2])
        print(" APBS Tools: fine grid: (%5.3f,%5.3f,%5.3f)" % tuple(finedim))
        self.grid_fine_x.setvalue(finedim[0])
        self.grid_fine_y.setvalue(finedim[1])
        self.grid_fine_z.setvalue(finedim[2])
        print(" APBS Tools: center: (%5.3f,%5.3f,%5.3f)" % tuple(center))
        self.grid_center_x.setvalue(center[0])
        self.grid_center_y.setvalue(center[1])
        self.grid_center_z.setvalue(center[2])
        print(" APBS Tools: fine grid points (%d,%d,%d)" % tuple(finegridpoints))
        self.grid_points_x.setvalue(finegridpoints[0])
        self.grid_points_y.setvalue(finegridpoints[1])
        self.grid_points_z.setvalue(finegridpoints[2])

    def fixColumns(self, sel):
        """
        Make sure that everything fits into the correct columns.
        This means doing some rounding. It also means getting rid of
        chain, occupancy and b-factor information.
        """
        #pymol.cmd.alter_state(1,'all','(x,y,z)=(int(x*1000)/1000.0, int(y*1000)/1000.0, int(z*1000)/1000.0)')
        # pymol.cmd.alter_state(1,'all','(x,y,z)=float("%.2f"%x),float("%.2f"%y),float("%.2f"%z)')
        pymol.cmd.alter_state(1, 'all', '(x,y,z)=float("%.3f"%x),float("%.3f"%y),float("%.3f"%z)')
        pymol.cmd.alter(sel, 'chain=""')
        pymol.cmd.alter(sel, 'b=0')
        pymol.cmd.alter(sel, 'q=0')

    def cleanupGeneratedPdbOrPqrFile(self, filename):
        """
        More cleanup on PQR files.

        pdb2pqr will happily write out a file where the coordinate
        columns overlap if you have -100.something as one of the
        coordinates, like

        90.350  97.230-100.010

        and so will PyMOL. We can't just assume that it's 0-1
        because pdb2pqr will debump things and write them out with
        3 digits post-decimal. Bleh.
        """
        f = open(filename, 'r')
        txt = f.read()
        f.close()
        print("Erasing contents of", filename, "in order to clean it up")
        f = open(filename, 'w')
        # APBS accepts whitespace-delimited columns
        coordregex = r'([- 0-9]{4}\.[ 0-9]{3})'
        txt = re.sub(
                r'^(ATOM  |HETATM)(........................)' + 3 * coordregex,
                r'\1\2 \3 \4 \5', txt, flags=re.M)
        f.write(txt)
        f.close()

    def getUnassignedAtomsFromPqr(self, fname):
        """
        Here is a comment from Todd Dolinsky via email:

        There's a couple of different errors which can be printed out via REMARK 5 lines; a good sample is:

        REMARK   1 PQR file generated by PDB2PQR (Version 1.2.0)
        REMARK   1
        REMARK   1 Forcefield Used: charmm
        REMARK   1
        REMARK   1 pKas calculated by propka and assigned using pH 7.00
        REMARK   1
        REMARK   5 WARNING: Propka determined the following residues to be
        REMARK   5          in a protonation state not supported by the
        REMARK   5          charmm forcefield!
        REMARK   5          All were reset to their standard pH 7.0 state.
        REMARK   5
        REMARK   5              CYS 61 2 (negative)
        REMARK   5              CYS 79 2 (negative)
        REMARK   5
        REMARK   5 WARNING: Unable to debump ALA 1 19
        REMARK   5 WARNING: Unable to debump MET 1 151
        REMARK   5 WARNING: Unable to debump PRO 1 258
        REMARK   5 WARNING: Unable to debump GLY 2 8
        REMARK   5 WARNING: Unable to debump THR 3 118
        REMARK   5
        REMARK   5 WARNING: PDB2PQR was unable to assign charges
        REMARK   5          to the following atoms (omitted below):
        REMARK   5              6657 O1 in TRS 900
        REMARK   5              6658 C2 in TRS 900
        REMARK   5              6659 C3 in TRS 900
        REMARK   5              6660 C4 in TRS 900
        REMARK   5              6661 O5 in TRS 900
        REMARK   5              6662 C6 in TRS 900
        REMARK   5              6663 O7 in TRS 900
        REMARK   5              6664 N8 in TRS 900
        REMARK   5
        REMARK   6 Total charge on this protein: -1.0000 e
        REMARK   6

        If all you care about is the atom number, you can probably regexp match on the 'in' field, something like

        >>> re.compile('REMARK   5 *(\d)* \w* in').findall(text)  # Text contains PQR output string
        ['6657', '6658', '6659', '6660', '6661', '6662', '6663', '6664']

        Or you can grab any other useful information - I'd say that using a regular expression like this would be the best option to ensure you don't get false positives.
        """
        f = open(fname)
        unassigned = re.compile('REMARK   5 *(\d+) \w* in').findall(f.read())  # Text contains PQR output string
        f.close()
        return '+'.join(unassigned)

    def generateApbsInputFile(self):
        if self.checkInput():
            #
            # set up our variables
            #
            pqr_filename = self.getPqrFilename()

            grid_points = [int(getattr(self, 'grid_points_%s' % i).getvalue()) for i in 'x y z'.split()]
            cglen = [float(getattr(self, 'grid_coarse_%s' % i).getvalue()) for i in 'x y z'.split()]
            fglen = [float(getattr(self, 'grid_fine_%s' % i).getvalue()) for i in 'x y z'.split()]
            cent = [float(getattr(self, 'grid_center_%s' % i).getvalue()) for i in 'x y z'.split()]

            apbs_mode = self.apbs_mode.getvalue()
            if apbs_mode == 'Nonlinear Poisson-Boltzmann Equation':
                apbs_mode = 'npbe'
            else:
                apbs_mode = 'lpbe'

            bcflmap = {'Zero': 'zero',
                       'Single DH sphere': 'sdh',
                       'Multiple DH spheres': 'mdh',
                       #'Focusing': 'focus',
                       }
            bcfl = bcflmap[self.bcfl.getvalue()]

            chgmmap = {'Linear': 'spl0',
                       'Cubic B-splines': 'spl2',
                       'Quintic B-splines': 'spl4',
                       }
            chgm = chgmmap[self.chgm.getvalue()]

            srfmmap = {'Mol surf for epsilon; inflated VdW for kappa, no smoothing': 'mol',
                        'Same, but with harmonic average smoothing': 'smol',
                        'Cubic spline': 'spl2',
                        'Similar to cubic spline, but with 7th order polynomial': 'spl4', }

            srfm = srfmmap[self.srfm.getvalue()]

            dx_filename = self.pymol_generated_dx_filename.getvalue()
            if dx_filename.endswith('.dx'):
                dx_filename = dx_filename[:-3]
            apbs_input_text = getApbsInputFile(pqr_filename,
                                               grid_points,
                                               cglen,
                                               fglen,
                                               cent,
                                               apbs_mode,
                                               bcfl,
                                               float(self.ion_plus_one_conc.getvalue()), float(self.ion_plus_one_rad.getvalue()),
                                               float(self.ion_minus_one_conc.getvalue()), float(self.ion_minus_one_rad.getvalue()),
                                               float(self.ion_plus_two_conc.getvalue()), float(self.ion_plus_two_rad.getvalue()),
                                               float(self.ion_minus_two_conc.getvalue()), float(self.ion_minus_two_rad.getvalue()),
                                               float(self.interior_dielectric.getvalue()), float(self.solvent_dielectric.getvalue()),
                                               chgm,
                                               srfm,
                                               float(self.solvent_radius.getvalue()),
                                               float(self.system_temp.getvalue()),
                                               float(self.sdens.getvalue()),
                                               dx_filename,
                                               )
            if DEBUG:
                print("GOT THE APBS INPUT FILE")

            #
            # write out the input text
            #
            try:
                print("Erasing contents of", self.pymol_generated_in_filename.getvalue(), "in order to write new input file")
                f = open(self.pymol_generated_in_filename.getvalue(), 'w')
                f.write(apbs_input_text)
                f.close()
            except IOError:
                print("ERROR: Got the input file from APBS, but failed when trying to write to %s" % self.pymol_generated_in_filename.getvalue())
            return True
        else:
            # self.checkInput()
            return False

    def checkInput(self):
        """No silent checks. Always show error.
        """
        def show_error(message):
            print("In show error 1")
            error_dialog = Pmw.MessageDialog(self.parent,
                                             title='Error',
                                             message_text=message,
                                             )
            junk = error_dialog.activate()

        #
        # First, check to make sure we have valid locations for apbs and psize
        #
        if not self.binary.valid():
            show_error('Please set the APBS binary location')
            return False
        #
        # If the path to psize is not correct, that's fine .. we'll
        # do the calculations ourself.
        #

        # if not self.psize.valid():
        #    show_error("Please set APBS's psize location")
        #    return False

        #
        # Now check the temporary filenames
        #
        if self.radiobuttons.getvalue() != 'Use another PQR':
            if not self.pymol_generated_pqr_filename.getvalue():
                show_error('Please choose a name for the PyMOL\ngenerated PQR file')
                return False
        elif not self.pqr_to_use.valid():
            show_error('Please select a valid pqr file or tell\nPyMOL to generate one')
            return False
        if not self.pymol_generated_pdb_filename.getvalue():
            show_error('Please choose a name for the PyMOL\ngenerated PDB file')
            return False
        if not self.pymol_generated_dx_filename.getvalue():
            show_error('Please choose a name for the PyMOL\ngenerated DX file')
            return False
        if not self.pymol_generated_in_filename.getvalue():
            show_error('Please choose a name for the PyMOL\ngenerated APBS input file')
            return False
        if not self.map.getvalue():
            show_error('Please choose a name for the generated map.')
            return False

        #
        # Now, the ions
        #
        for sign in 'plus minus'.split():
            for value in 'one two'.split():
                for parm in 'conc rad'.split():
                    if not getattr(self, 'ion_%s_%s_%s' % (sign, value, parm)).valid():
                        show_error('Please correct Ion concentrations and radii')
                        return False
        #
        # Now the grid
        #
        for grid_type in 'coarse fine points center'.split():
            for coord in 'x y z'.split():
                if not getattr(self, 'grid_%s_%s' % (grid_type, coord)).valid():
                    show_error('Please correct grid dimensions\nby clicking on the "Set grid" button')
                    return False

        #
        # Now other easy things
        #
        for (message, thing) in (('solvent dielectric', self.solvent_dielectric),
                                 ('protein dielectric', self.interior_dielectric),
                                 ('solvent radius', self.solvent_radius),
                                 ('system temperature', self.system_temp),
                                 ('sdens', self.sdens),
                                 ):
            if not thing.valid():
                show_error('Please correct %s' % message)
                return False

        return True

    # PQR generation routines are required to call
    # cleanupGeneratedPdbOrPqrFile themselves.
    def _generatePdb2pqrPqrFile(self):
        """use pdb2pqr to generate a pqr file
        Call this via the wrapper generatePqrFile()
        """
        def show_error(message):
            print("In show error 2")
            error_dialog = Pmw.MessageDialog(self.parent,
                                             title='Error',
                                             message_text=message,
                                             )
            junk = error_dialog.activate()

        #
        # First, generate a PDB file
        #
        pdb_filename = self.pymol_generated_pdb_filename.getvalue()
        try:
            print("Erasing contents of", pdb_filename, "in order to generate new PDB file")
            f = open(pdb_filename, 'w')
            f.close()
        except:
            show_error('Please set a temporary PDB file location that you have permission to edit')
            return False
        # copied from WLD code
        sel = "((%s) or (neighbor (%s) and hydro))" % (
            self.selection.getvalue(), self.selection.getvalue())

        apbs_clone = pymol.cmd.get_unused_name()
        pymol.cmd.create(apbs_clone,sel) 

        self.fixColumns(apbs_clone)
        pymol.cmd.save(pdb_filename, apbs_clone)

        pymol.cmd.delete(apbs_clone)
        #
        # Now, generate a PQR file
        #
# command_line = '%s %s %s %s'%(self.pdb2pqr.getvalue(),
# self.pdb2pqr_options.getvalue(),
# pdb_filename,
# self.pymol_generated_pqr_filename.getvalue(),
# )
# print "RAN",command_line
##        result = os.system(command_line)
        #
        # We have to be a little cute about args, because _options could have several options in it.

        if DEBUG:
            print("TESTING")
            # run('/tmp/tmp.py',())
            print("DONE TESTING")

        import shlex
        args = [self.pdb2pqr.getvalue(),
                ] + shlex.split(self.pdb2pqr_options.getvalue()) + [
                            pdb_filename,
                            self.pymol_generated_pqr_filename.getvalue(),
        ]
        try:
            # This allows us to import pdb2pqr
            # sys.path.append(os.path.dirname(os.path.dirname(self.pdb2pqr.getvalue())))
            # print "Appended", os.path.dirname(os.path.dirname(self.pdb2pqr.getvalue()))
            ###!!! Edited for Pymol-script-repo !!!###
            # sys.path.append(os.path.join(os.environ['PYMOL_GIT_MOD'],"pdb2pqr"))
            # print "Appended", os.path.join(os.environ['PYMOL_GIT_MOD'],"pdb2pqr")
            ###!!!------------------------------!!!###
            #import pdb2pqr.pdb2pqr
            # This allows pdb2pqr to correctly find the dat directory with AMBER.DAT.
            # sys.path.append(os.path.dirname(self.pdb2pqr.getvalue()))
            # print "Appended", os.path.dirname(self.pdb2pqr.getvalue())
            # print "Imported pdb2pqr"
            # print "args are: ", args
            #from pdb2pqr import main
            # print "Imported main"
            try:
                ###!!! Edited for Pymol-script-repo !!!###
                args = ' '.join(map(str, args))
                print("args are now converted to string: ", args)
#                retval = main.mainCommand(args)
                if 'PYMOL_GIT_MOD' in os.environ:
                    os.environ['PYTHONPATH'] = os.path.join(os.environ['PYMOL_GIT_MOD']) + ":" + os.path.join(os.environ['PYMOL_GIT_MOD'], "pdb2pqr")
                pymol_env = os.environ
                callfunc = subprocess.Popen(args, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=pymol_env)
                child_stdout, child_stderr = callfunc.communicate()
                print(child_stdout)
                print(child_stderr)
                retval = callfunc.returncode
                print("PDB2PQR's mainCommand returned", retval)
#                if retval == 1:
# retval = 0 # success condition is backwards in pdb2pqr
#                elif retval == 0:
# retval = 1 # success condition is backwards in pdb2pqr
#                elif retval == None:
# retval = 0 # When PDB2PQR does not explicitly
# return anything, it's a success.
###!!!-------------------------------!!!###
            except:
                print("Exception raised by main.mainCommand!")
                print(sys.exc_info())
                retval = 1
        except:
            print("Unexpected error encountered while trying to import pdb2pqr:", sys.exc_info())
            retval = 1  # failure is nonzero here.

        if retval != 0:
            show_error('Could not run pdb2pqr: %s %s\n\nIt returned %s.\nCheck the PyMOL external GUI window for more information\n' % (self.pdb2pqr.getvalue(),
                                                                                                                                      args,
                                                                                                                                      retval)
                       )
            return False
        self.cleanupGeneratedPdbOrPqrFile(self.pymol_generated_pqr_filename.getvalue())
        unassigned_atoms = self.getUnassignedAtomsFromPqr(self.pymol_generated_pqr_filename.getvalue())
        if unassigned_atoms:
            pymol.cmd.select('unassigned', 'ID %s' % unassigned_atoms)
            message_text = "Unable to assign parameters for the %s atoms in selection 'unassigned'.\nPlease either remove these unassigned atoms and re-start the calculation\nor fix their parameters in the generated PQR file and run the calculation\nusing the modified PQR file (select 'Use another PQR' in 'Main')." % len(unassigned_atoms.split('+'))
            print("Unassigned atom IDs", unassigned_atoms)
            show_error(message_text)
            return False
        if DEBUG:
            print("I WILL RETURN TRUE from pdb2pqr")
        return True

    # PQR generation routines are required to call
    # cleanupGeneratedPdbOrPqrFile themselves.
    def _generatePymolPqrFile(self):
        """generate a pqr file from pymol

        This will also call through to champ to set the Hydrogens and charges
        if it needs to.  If it does that, it may change the value self.selection
        to take the new Hydrogens into account.

        To make it worse, APBS seems to freak out when there are chain ids.  So,
        this gets rid of the chain ids.

        call this through the wrapper generatePqrFile
        """
        # CHAMP will break in many cases if retain_order is set. So,
        # we unset it here and reset it later. Note that it's fine to
        # reset it before things are written out.
        ret_order = pymol.cmd.get('retain_order')
        pymol.cmd.set('retain_order', 0)

        # WLD
        sel = "((%s) or (neighbor (%s) and hydro))" % (
            self.selection.getvalue(), self.selection.getvalue())

        pqr_filename = self.getPqrFilename()
        try:
            if DEBUG:
                print("Erasing previous contents of", pqr_filename)
            f = open(pqr_filename, 'w')
            f.close()
        except:
            error_dialog = Pmw.MessageDialog(self.parent,
                                             title='Error',
                                             message_text="Could not write PQR file.\nPlease check that temporary PQR filename is valid.",
                                             )
            junk = error_dialog.activate()
            return False

        # PyMOL + champ == pqr
        from chempy.champ import assign
        if self.radiobuttons.getvalue() == 'Use PyMOL generated PQR and PyMOL generated Hydrogens and termini':
            pymol.cmd.remove('hydro and %s' % sel)
            assign.missing_c_termini(sel)
            assign.formal_charges(sel)
            pymol.cmd.h_add(sel)
            # WLD (code now unnecessary)
            # new_hydros = '(hydro and neighbor %s)'%sel
            # sel = '%s or %s' % (sel,new_hydros)
        assign.amber99(sel)
        pymol.cmd.set('retain_order', ret_order)

        # WLD (code now unnecessary)
        # if not self.selection.getvalue() in '(all) all'.split():
        #     self.selection.setvalue(sel)

        #
        # Get rid of chain information
        #
        # WLD -- PyMOL now does this automatically with PQR files
        # pymol.cmd.alter(sel,'chain = ""')

        apbs_clone = pymol.cmd.get_unused_name()
        pymol.cmd.create(apbs_clone,sel) 
        
        self.fixColumns(apbs_clone)
        pymol.cmd.save(pqr_filename, apbs_clone)
        
        pymol.cmd.delete(apbs_clone) 

        self.cleanupGeneratedPdbOrPqrFile(pqr_filename)
        missed_count = pymol.cmd.count_atoms("(" + sel + ") and flag 23")
        if missed_count > 0:
            pymol.cmd.select("unassigned", "(" + sel + ") and flag 23")
            error_dialog = Pmw.MessageDialog(self.parent,
                                             title='Error',
                                             message_text="Unable to assign parameters for the %s atoms in selection 'unassigned'.\nPlease either remove these unassigned atoms and re-start the calculation\nor fix their parameters in the generated PQR file and run the calculation\nusing the modified PQR file (select 'Use another PQR' in 'Main')." % missed_count,
                                             )
            junk = error_dialog.activate()
            return False
        return True


############################################################
############################################################
############################################################
##                                                        ##
##         PmwExtensions                                  ##
##                                                        ##
############################################################
############################################################
############################################################

"""
This contains all of the visualization groups that we'll use for our
PMW interface.
"""

#
# Generically useful PMW extensions

import os
import fnmatch
import time
import Pmw
# Pmw.setversion("0.8.5")

#
# The classes PmwFileDialog and PmwExistingFileDialog and the _errorpop function
# are taken from the Pmw contrib directory.  The attribution given in that file
# is:
################################################################################
# Filename dialogs using Pmw
#
# (C) Rob W.W. Hooft, Nonius BV, 1998
#
# Modifications:
#
# J. Willem M. Nissink, Cambridge Crystallographic Data Centre, 8/2002
#    Added optional information pane at top of dialog; if option
#    'info' is specified, the text given will be shown (in blue).
#    Modified example to show both file and directory-type dialog
#
# No Guarantees. Distribute Freely.
# Please send bug-fixes/patches/features to <r.hooft@euromail.com>
#
################################################################################


def _errorpop(master, text):
    d = Pmw.MessageDialog(master,
                        title="Error",
                        message_text=text,
                        buttons=("OK",))
    d.component('message').pack(ipadx=15, ipady=15)
    d.activate()
    d.destroy()


class PmwFileDialog(Pmw.Dialog):

    """File Dialog using Pmw"""

    def __init__(self, parent=None, **kw):
        # Define the megawidget options.
        optiondefs = (
            ('filter', '*', self.newfilter),
            ('directory', os.getcwd(), self.newdir),
            ('filename', '', self.newfilename),
            ('historylen', 10, None),
            ('command', None, None),
            ('info', None, None),
        )
        self.defineoptions(kw, optiondefs)
        # Initialise base class (after defining options).
        Pmw.Dialog.__init__(self, parent)

        self.withdraw()

        # Create the components.
        interior = self.interior()

        if self['info'] is not None:
            rowoffset = 1
            dn = self.infotxt()
            dn.grid(row=0, column=0, columnspan=2, padx=3, pady=3)
        else:
            rowoffset = 0

        dn = self.mkdn()
        dn.grid(row=0 + rowoffset, column=0, columnspan=2, padx=3, pady=3)
        del dn

        # Create the directory list component.
        dnb = self.mkdnb()
        dnb.grid(row=1 + rowoffset, column=0, sticky='news', padx=3, pady=3)
        del dnb

        # Create the filename list component.
        fnb = self.mkfnb()
        fnb.grid(row=1 + rowoffset, column=1, sticky='news', padx=3, pady=3)
        del fnb

        # Create the filter entry
        ft = self.mkft()
        ft.grid(row=2 + rowoffset, column=0, columnspan=2, padx=3, pady=3)
        del ft

        # Create the filename entry
        fn = self.mkfn()
        fn.grid(row=3 + rowoffset, column=0, columnspan=2, padx=3, pady=3)
        fn.bind('<Return>', self.okbutton)
        del fn

        # Buttonbox already exists
        bb = self.component('buttonbox')
        bb.add('OK', command=self.okbutton)
        bb.add('Cancel', command=self.cancelbutton)
        del bb

        Pmw.alignlabels([self.component('filename'),
                         self.component('filter'),
                         self.component('dirname')])

    def infotxt(self):
        """ Make information block component at the top """
        return self.createcomponent(
            'infobox',
            (), None,
            tkinter.Label, (self.interior(),),
            width=51,
            relief='groove',
            foreground='darkblue',
            justify='left',
            text=self['info']
        )

    def mkdn(self):
        """Make directory name component"""
        return self.createcomponent(
            'dirname',
            (), None,
            Pmw.ComboBox, (self.interior(),),
            entryfield_value=self['directory'],
            entryfield_entry_width=40,
            entryfield_validate=self.dirvalidate,
            selectioncommand=self.setdir,
            labelpos='w',
            label_text='Directory:')

    def mkdnb(self):
        """Make directory name box"""
        return self.createcomponent(
            'dirnamebox',
            (), None,
            Pmw.ScrolledListBox, (self.interior(),),
            label_text='directories',
            labelpos='n',
            hscrollmode='none',
            dblclickcommand=self.selectdir)

    def mkft(self):
        """Make filter"""
        return self.createcomponent(
            'filter',
            (), None,
            Pmw.ComboBox, (self.interior(),),
            entryfield_value=self['filter'],
            entryfield_entry_width=40,
            selectioncommand=self.setfilter,
            labelpos='w',
            label_text='Filter:')

    def mkfnb(self):
        """Make filename list box"""
        return self.createcomponent(
            'filenamebox',
            (), None,
            Pmw.ScrolledListBox, (self.interior(),),
            label_text='files',
            labelpos='n',
            hscrollmode='none',
            selectioncommand=self.singleselectfile,
            dblclickcommand=self.selectfile)

    def mkfn(self):
        """Make file name entry"""
        return self.createcomponent(
            'filename',
            (), None,
            Pmw.ComboBox, (self.interior(),),
            entryfield_value=self['filename'],
            entryfield_entry_width=40,
            entryfield_validate=self.filevalidate,
            selectioncommand=self.setfilename,
            labelpos='w',
            label_text='Filename:')

    def dirvalidate(self, string):
        if os.path.isdir(string):
            return Pmw.OK
        else:
            return Pmw.PARTIAL

    def filevalidate(self, string):
        if string == '':
            return Pmw.PARTIAL
        elif os.path.isfile(string):
            return Pmw.OK
        elif os.path.exists(string):
            return Pmw.PARTIAL
        else:
            return Pmw.OK

    def okbutton(self):
        """OK action: user thinks he has input valid data and wants to
           proceed. This is also called by <Return> in the filename entry"""
        fn = self.component('filename').get()
        self.setfilename(fn)
        if self.validate(fn):
            self.canceled = 0
            self.deactivate()

    def cancelbutton(self):
        """Cancel the operation"""
        self.canceled = 1
        self.deactivate()

    def tidy(self, w, v):
        """Insert text v into the entry and at the top of the list of
           the combobox w, remove duplicates"""
        if not v:
            return
        entry = w.component('entry')
        entry.delete(0, 'end')
        entry.insert(0, v)
        list = w.component('scrolledlist')
        list.insert(0, v)
        index = 1
        while index < list.index('end'):
            k = list.get(index)
            if k == v or index > self['historylen']:
                list.delete(index)
            else:
                index = index + 1
        w.checkentry()

    def setfilename(self, value):
        if not value:
            return
        value = os.path.join(self['directory'], value)
        dir, fil = os.path.split(value)
        self.configure(directory=dir, filename=value)

        c = self['command']
        if callable(c):
            c()

    def newfilename(self):
        """Make sure a newly set filename makes it into the combobox list"""
        self.tidy(self.component('filename'), self['filename'])

    def setfilter(self, value):
        self.configure(filter=value)

    def newfilter(self):
        """Make sure a newly set filter makes it into the combobox list"""
        self.tidy(self.component('filter'), self['filter'])
        self.fillit()

    def setdir(self, value):
        self.configure(directory=value)

    def newdir(self):
        """Make sure a newly set dirname makes it into the combobox list"""
        self.tidy(self.component('dirname'), self['directory'])
        self.fillit()

    def singleselectfile(self):
        """Single click in file listbox. Move file to "filename" combobox"""
        cs = self.component('filenamebox').curselection()
        if cs != ():
            value = self.component('filenamebox').get(cs)
            self.setfilename(value)

    def selectfile(self):
        """Take the selected file from the filename, normalize it, and OK"""
        self.singleselectfile()
        value = self.component('filename').get()
        self.setfilename(value)
        if value:
            self.okbutton()

    def selectdir(self):
        """Take selected directory from the dirnamebox into the dirname"""
        cs = self.component('dirnamebox').curselection()
        if cs != ():
            value = self.component('dirnamebox').get(cs)
            dir = self['directory']
            if not dir:
                dir = os.getcwd()
            if value:
                if value == '..':
                    dir = os.path.split(dir)[0]
                else:
                    dir = os.path.join(dir, value)
            self.configure(directory=dir)
            self.fillit()

    def askfilename(self, directory=None, filter=None):
        """The actual client function. Activates the dialog, and
           returns only after a valid filename has been entered
           (return value is that filename) or when canceled (return
           value is None)"""
        if directory != None:
            self.configure(directory=directory)
        if filter != None:
            self.configure(filter=filter)
        self.fillit()
        self.canceled = 1  # Needed for when user kills dialog window
        self.activate()
        if self.canceled:
            return None
        else:
            return self.component('filename').get()

    lastdir = ""
    lastfilter = None
    lasttime = 0

    def fillit(self):
        """Get the directory list and show it in the two listboxes"""
        # Do not run unnecesarily
        if self.lastdir == self['directory'] and self.lastfilter == self['filter'] and self.lasttime > os.stat(self.lastdir)[8]:
            return
        self.lastdir = self['directory']
        self.lastfilter = self['filter']
        self.lasttime = time.time()
        dir = self['directory']
        if not dir:
            dir = os.getcwd()
        dirs = ['..']
        files = []
        try:
            fl = os.listdir(dir)
            fl.sort()
        except os.error as arg:
            if arg[0] in (2, 20):
                return
            raise
        for f in fl:
            if os.path.isdir(os.path.join(dir, f)):
                dirs.append(f)
            else:
                filter = self['filter']
                if not filter:
                    filter = '*'
                if fnmatch.fnmatch(f, filter):
                    files.append(f)
        self.component('filenamebox').setlist(files)
        self.component('dirnamebox').setlist(dirs)

    def validate(self, filename):
        """Validation function. Should return 1 if the filename is valid,
           0 if invalid. May pop up dialogs to tell user why. Especially
           suited to subclasses: i.e. only return 1 if the file does/doesn't
           exist"""
        return 1


class PmwExistingFileDialog(PmwFileDialog):

    def filevalidate(self, string):
        if os.path.isfile(string):
            return Pmw.OK
        else:
            return Pmw.PARTIAL

    def validate(self, filename):
        if os.path.isfile(filename):
            return 1
        elif os.path.exists(filename):
            _errorpop(self.interior(), "This is not a plain file")
            return 0
        else:
            _errorpop(self.interior(), "Please select an existing file")
            return 0


class FileDialogButtonClassFactory:

    def get(fn, filter='*'):
        """This returns a FileDialogButton class that will
        call the specified function with the resulting file.
        """
        class FileDialogButton(tkinter.Button):
            # This is just an ordinary button with special colors.

            def __init__(self, master=None, cnf={}, **kw):
                '''when we get a file, we call fn(filename)'''
                self.fn = fn
                self.__toggle = 0
                tkinter.Button.__init__(self, master, cnf, **kw)
                self.configure(command=self.set)

            def set(self):
                fd = PmwFileDialog(self.master, filter=filter)
                fd.title('Please choose a file')
                n = fd.askfilename()
                if n is not None:
                    self.fn(n)
        return FileDialogButton
    get = staticmethod(get)

############################################################
############################################################
############################################################
##                                                        ##
##         PmwGroups                                      ##
##                                                        ##
############################################################
############################################################
############################################################


class VisualizationGroup(Pmw.Group):

    def __init__(self, *args, **kwargs):
        my_options = 'visgroup_num'.split()
        for option in my_options:
            # use these options as attributes of this class
            # and remove them from the kwargs dict before
            # passing on to Pmw.Group.__init__().
            setattr(self, option, kwargs.pop(option))
        kwargs['tag_text'] = kwargs['tag_text'] + ' (%s)' % self.visgroup_num
        Pmw.Group.__init__(self, *args, **kwargs)
        self.refresh()
        self.show_ms = False
        self.show_pi = False
        self.show_ni = False

    def refresh(self):
        things_to_kill = 'fl_group error_label update_buttonbox mm_group ms_group pi_group ni_group'.split()
        for thing in things_to_kill:
            try:
                getattr(self, thing).destroy()
                # print "destroyed",thing
            except AttributeError:
                # print "couldn't destroy",thing

                # note: this attributeerror will also hit if getattr(self,thing) misses.
                # another note: both halves of the if/else make an update_buttonbox.
                # if you rename the one in the top half to something else, you'll cause nasty Pmw errors.
                pass
        if [i for i in pymol.cmd.get_names() if pymol.cmd.get_type(i) == 'object:map'] and [i for i in pymol.cmd.get_names() if pymol.cmd.get_type(i) == 'object:molecule']:
            self.mm_group = Pmw.Group(self.interior(), tag_text='Maps and Molecules')
            self.map = Pmw.OptionMenu(self.mm_group.interior(),
                                      labelpos='w',
                                      label_text='Map',
                                      items=[i for i in pymol.cmd.get_names() if pymol.cmd.get_type(i) == 'object:map'],
                                      )
            self.map.pack(padx=4, side=LEFT)

            self.molecule = Pmw.OptionMenu(self.mm_group.interior(),
                                           labelpos='w',
                                           label_text='Molecule',
                                           items=[i for i in pymol.cmd.get_names() if pymol.cmd.get_type(i) == 'object:molecule'],
                                           )
            self.molecule.pack(padx=4, side=LEFT)
            self.update_buttonbox = Pmw.ButtonBox(self.mm_group.interior(), padx=0)
            self.update_buttonbox.pack(side=LEFT)
            self.update_buttonbox.add('Update', command=self.refresh)
            self.mm_group.pack(fill='both', expand=1, padx=4, pady=5, side=TOP)

            self.ms_group = Pmw.Group(self.interior(), tag_text='Molecular Surface')
            self.ms_buttonbox = Pmw.ButtonBox(self.ms_group.interior(), padx=0)
            self.ms_buttonbox.pack()
            self.ms_buttonbox.add('Show', command=self.showMolSurface)
            self.ms_buttonbox.add('Hide', command=self.hideMolSurface)
            self.ms_buttonbox.add('Update', command=self.updateMolSurface)
            self.ms_buttonbox.alignbuttons()
            self.surface_solvent = IntVar()
            self.surface_solvent.set(APBSTools2.defaults['surface_solvent'])
            self.sol_checkbutton = Checkbutton(self.ms_group.interior(),
                                               text="Solvent accessible surface",
                                               variable=self.surface_solvent)
            self.sol_checkbutton.pack()
            self.potential_at_sas = IntVar()
            self.potential_at_sas.set(APBSTools2.defaults['potential_at_sas'])
            self.pot_checkbutton = Checkbutton(self.ms_group.interior(),
                                               text="Color by potential on sol. acc. surf.",
                                               variable=self.potential_at_sas)
            self.pot_checkbutton.pack()
            self.mol_surf_low = Pmw.Counter(self.ms_group.interior(),
                                            labelpos='w',
                                            label_text='Low',
                                            orient='vertical',
                                            entry_width=4,
                                            entryfield_value=-5,
                                            datatype='real',
                                            entryfield_validate={'validator': 'real'},
                                            )
            self.mol_surf_middle = Pmw.Counter(self.ms_group.interior(),
                                               labelpos='w',
                                               label_text='Middle',
                                               orient='vertical',
                                               entry_width=4,
                                               entryfield_value=0,
                                               datatype='real',
                                               entryfield_validate={'validator': 'real'}
                                               )
            self.mol_surf_high = Pmw.Counter(self.ms_group.interior(),
                                             labelpos='w',
                                             label_text='High',
                                             orient='vertical',
                                             entry_width=4,
                                             entryfield_value=5,
                                             datatype='real',
                                             entryfield_validate={'validator': 'real'}
                                             )
            bars = (self.mol_surf_low, self.mol_surf_middle, self.mol_surf_high)
            Pmw.alignlabels(bars)
            for bar in bars:
                bar.pack(side=LEFT)
            self.ms_group.pack(fill='both', expand=1, padx=4, pady=5, side=LEFT)

            self.fl_group = Pmw.Group(self.interior(), tag_text='Field Lines')
            self.fl_buttonbox = Pmw.ButtonBox(self.fl_group.interior(), padx=0)
            self.fl_buttonbox.pack()
            self.fl_buttonbox.add('Show', command=self.showFieldLines)
            self.fl_buttonbox.add('Hide', command=self.hideFieldLines)
            self.fl_buttonbox.add('Update', command=self.updateFieldLines)
            self.fl_buttonbox.alignbuttons()
            label = tkinter.Label(self.fl_group.interior(),
                                  pady=10,
                                  justify=LEFT,
                                  text="""Follows same coloring as surface.""",
                                  )
            label.pack()
            self.fl_group.pack(fill='both', expand=1, padx=4, pady=5, side=TOP)

            self.pi_group = Pmw.Group(self.interior(), tag_text='Positive Isosurface')
            self.pi_buttonbox = Pmw.ButtonBox(self.pi_group.interior(), padx=0)
            self.pi_buttonbox.pack()
            self.pi_buttonbox.add('Show', command=self.showPosSurface)
            self.pi_buttonbox.add('Hide', command=self.hidePosSurface)
            self.pi_buttonbox.add('Update', command=self.updatePosSurface)
            self.pi_buttonbox.alignbuttons()
            self.pos_surf_val = Pmw.Counter(self.pi_group.interior(),
                                            labelpos='w',
                                            label_text='Contour (kT/e)',
                                            orient='vertical',
                                            entry_width=4,
                                            entryfield_value=1,
                                            datatype='real',
                                            entryfield_validate={'validator': 'real', 'min': 0}
                                            )
            self.pos_surf_val.pack(side=LEFT)
            self.pi_group.pack(fill='both', expand=1, padx=4, pady=5, side=LEFT)

            self.ni_group = Pmw.Group(self.interior(), tag_text='Negative Isosurface')
            self.ni_buttonbox = Pmw.ButtonBox(self.ni_group.interior(), padx=0)
            self.ni_buttonbox.pack()
            self.ni_buttonbox.add('Show', command=self.showNegSurface)
            self.ni_buttonbox.add('Hide', command=self.hideNegSurface)
            self.ni_buttonbox.add('Update', command=self.updateNegSurface)
            self.ni_buttonbox.alignbuttons()
            self.neg_surf_val = Pmw.Counter(self.ni_group.interior(),
                                            labelpos='w',
                                            label_text='Contour (kT/e)',
                                            orient='vertical',
                                            entry_width=4,
                                            entryfield_value=-1,
                                            datatype='real',
                                            entryfield_validate={'validator': 'real', 'max': 0}
                                            )
            self.neg_surf_val.pack(side=LEFT)
            self.ni_group.pack(fill='both', expand=1, padx=4, pady=5, side=LEFT)

        else:
            self.error_label = tkinter.Label(self.interior(),
                                             pady=10,
                                             justify=LEFT,
                                             text='''You must have at least a molecule and a map loaded.
If you have a molecule and a map loaded, please click "Update"''',
                                             )
            self.error_label.pack()
            self.update_buttonbox = Pmw.ButtonBox(self.interior(), padx=0)
            self.update_buttonbox.pack()
            self.update_buttonbox.add('Update', command=self.refresh)

    def showMolSurface(self):
        self.updateMolSurface()

    def hideMolSurface(self):
        pymol.cmd.hide('surface', self.molecule.getvalue())

    def getRampName(self):
        # return 'e_lvl'
        idx = [i for i in pymol.cmd.get_names() if pymol.cmd.get_type(i) == 'object:molecule'].index(self.molecule.getvalue())
        return '_'.join(('e_lvl', str(idx), str(self.visgroup_num)))

    def getGradName(self):
        # return 'e_lvl'
        idx = [i for i in pymol.cmd.get_names() if pymol.cmd.get_type(i) == 'object:molecule'].index(self.molecule.getvalue())
        return '_'.join(('grad', str(idx), str(self.visgroup_num)))

    def getIsoPosName(self):
        idx = [i for i in pymol.cmd.get_names() if pymol.cmd.get_type(i) == 'object:map'].index(self.map.getvalue())
        return '_'.join(('iso_pos', str(idx), str(self.visgroup_num)))

    def getIsoNegName(self):
        idx = [i for i in pymol.cmd.get_names() if pymol.cmd.get_type(i) == 'object:map'].index(self.map.getvalue())
        return '_'.join(('iso_neg', str(idx), str(self.visgroup_num)))

    def updateRamp(self):
        molecule_name = self.molecule.getvalue()
        ramp_name = self.getRampName()
        map_name = self.map.getvalue()
        low = float(self.mol_surf_low.getvalue())
        mid = float(self.mol_surf_middle.getvalue())
        high = float(self.mol_surf_high.getvalue())
        range = [low, mid, high]
        if DEBUG:
            print(" APBS Tools: range is", range)
        pymol.cmd.delete(ramp_name)
        pymol.cmd.ramp_new(ramp_name, map_name, range)
        pymol.cmd.set('surface_color', ramp_name, molecule_name)

    def updateMolSurface(self):
        molecule_name = self.molecule.getvalue()
        self.updateRamp()
        if self.surface_solvent.get() == 1:
            pymol.cmd.set('surface_solvent', 1, molecule_name)
            pymol.cmd.set('surface_ramp_above_mode', 0, molecule_name)
        else:
            pymol.cmd.set('surface_solvent', 0, molecule_name)
            pymol.cmd.set('surface_ramp_above_mode', self.potential_at_sas.get(), molecule_name)
        pymol.cmd.show('surface', molecule_name)
        pymol.cmd.refresh()
        pymol.cmd.recolor(molecule_name)

    def showPosSurface(self):
        self.updatePosSurface()

    def hidePosSurface(self):
        pymol.cmd.hide('everything', self.getIsoPosName())

    def updatePosSurface(self):
        pymol.cmd.delete(self.getIsoPosName())
        pymol.cmd.isosurface(self.getIsoPosName(), self.map.getvalue(), float(self.pos_surf_val.getvalue()))
        pymol.cmd.color('blue', self.getIsoPosName())
        pymol.cmd.show('everything', self.getIsoPosName())

    def showNegSurface(self):
        self.updateNegSurface()

    def hideNegSurface(self):
        pymol.cmd.hide('everything', self.getIsoNegName())

    def updateNegSurface(self):
        pymol.cmd.delete(self.getIsoNegName())
        pymol.cmd.isosurface(self.getIsoNegName(), self.map.getvalue(), float(self.neg_surf_val.getvalue()))
        pymol.cmd.color('red', self.getIsoNegName())
        pymol.cmd.show('everything', self.getIsoNegName())

    def showFieldLines(self):
        self.updateFieldLines()

    def hideFieldLines(self):
        pymol.cmd.hide('everything', self.getGradName())

    def updateFieldLines(self):
        print("IN update")
        pymol.cmd.gradient(self.getGradName(), self.map.getvalue())
        print("Made gradient")
        self.updateRamp()
        print("Updated ramp")
        pymol.cmd.color(self.getRampName(), self.getGradName())
        print("set colors")
        pymol.cmd.show('mesh', self.getGradName())
