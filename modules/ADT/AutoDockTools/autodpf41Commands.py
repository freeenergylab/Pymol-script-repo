#############################################################################
#
# Author: Ruth HUEY, Michel F. SANNER
#
# Copyright: M. Sanner TSRI 2000
#
#############################################################################

#
# $Header: /opt/cvs/python/packages/share1.5/AutoDockTools/autodpf41Commands.py,v 1.3 2010/06/28 22:08:55 rhuey Exp $
#
# $Id: autodpf41Commands.py,v 1.3 2010/06/28 22:08:55 rhuey Exp $
#
#
#
#
#
#

"""
This Module facilitates producing a docking parameter file for AutoDock. The steps in this process are:

    * Selecting the macromolecule filename: The user can select the macromolecule for autodpf in three ways: it can be chosen from molecules previously added to the moleculeViewer, it can be picked as a PDB file,  or it can be picked as a MOL2 file:

        o Choose Macromol...

        o Select PDB Macromolecule 

        o Select MOL2 Macromolecule

    * Selecting the small molecule which has been previously formatted by AutoTors: 

        o Via Reading a PDBQ-File which adds the ligand to the viewer

    * The user sets parameters pertaining to the small molecule 

        o Checking that a grid map exists for each of the ligand atom types 

        o Indicating whether a floating grid map exists

        o Setting the initial translation of the small molecule

            - by choosing  the 'random' option which sets a random starting position for the ligand

            - by entering the desired coordinates in the entry

        o Setting the initial quaternion of the small molecule

            - by choosing  the 'random' option which sets a random starting quaternion.

            - by entering the desired initial quaternion -Qx,Qy,Qz,Qw in the entry.  Qx, Qy, Qz define the unit vector in the direction of rigid body rotation and Qw the angle of rotation about this unit vector.

        o Setting the coefficient of the torsional DOF

        o By choosing to set the initial dihedrals for the small molecule or not: If not, AutoDock assumes that the chi1, chi2, chi3 etc are all zero and does not change the initial ligand torsion angles. If the user chooses to set the initial dihedrals, he further chooses:

            - for them to be randomly assigned 

            - an initial relative dihedral angle for each active torsion in the ligand.

        o The user can specify two types of torsion constraints for the ligand:

            -  Gaussian constraints which use an inverted Gaussian bell curve to calculate the energy function input of the constraint.  This type of constraint is specified by two floating point numbers: the perferred angle in the range -180-+180decreeds and the half-width which is the difference between two angles at which the energy is half the barrier PLUS an integer which identifies the torsion according to the list at the top of the AutoTors-generated input ligand PDBQ file. More than one constraint of this type may be specified for a single torsion.

            - Hard torsion constraints may also be specified. These differ from the previous type in that the torsion is never allowed to take values bewond the range defined and in that the second parameter is the full width of the allowed range of torsion angles. Moreover, only one constraint of this type is allowed per torsion.

        o If the user specifies torsion constraints, he may also specify the height of the energy barrier to be applied to these constraints.

        o If the user specifies Gaussian torsion constraints, he may also specify whether to store and output the torsion energies

    * The user sets parameters pertaining to docking algorithm(s) he wishes to use
:
        o Setting Simulated Annealing parameters.

        o Setting Genetic Algorithm parameters (GA).

        o Setting Local Search parameters (LS).

    It is important to remember that any of these may be used alone but only GA and LS may be used together


    * The user adjusts these additional parameters: 
    
        o the step sizes of translation, quaternion rotation and dihedral torsion change.
        o  energy parameters including energy assigned to atoms outside the grid volume, the maximum allowable initial energy and the maximum number of retries.

        o output format parameters including the level of detail for the output, the rms cluster tolerance, the reference file for rms calculations and whether to do symmetry checking in the rms calculations.


    * The user selects which kind of docking parameter file to write : 
    
        o Simulated Annealing 

        o GA

        o LS

        o GALS


    * The results of the previous steps are written to a file. The user selects a filename via a filebrowser.  By convention, the file should have a .dpf extension. If no macromolecule has been selected, it is not possible to write a grid parameter file and the user gets a warning message to that effect. Likewise, the types of the maps to be calculated must be set before the grid parameter file is written and a warning message to this effect appears if the types have not been set.
(A checkbutton, "DONE", allows the user to withdraw the autoTools menuBar)
    
"""
from ViewerFramework.VFCommand import CommandGUI
from AutoDockTools.autodpfCommands import DpfSetDpo, DpfLoadDefaults,\
Dpf4MacroSelector, Dpf4FlexResSelector, Dpf4MacroChooser,\
Dpf4InitLigand, Dpf4LigandChooser, Dpf4LigPDBQReader,\
DpfEditor, Dpf41SAWriter, Dpf41GAWriter, Dpf41LSWriter,\
Dpf41GALSWriter, Dpf4ClusterWriter, SimAnneal, GA,\
LS, SetDockingRunParms, SetAutoDock4Parameters, SetAutoDock41Parameters,\
StopAutoDpf, menuText, checkHasDpo, sortKeyList, setDpoFields


DpfLoadDefaultsGUI = CommandGUI()
DpfLoadDefaultsGUI.addMenuCommand('AutoTools41Bar', menuText['AutoDpfMB'], menuText['ReadDpfMB'])


Dpf4MacroSelectorGUI=CommandGUI()
Dpf4MacroSelectorGUI.addMenuCommand('AutoTools41Bar', menuText['AutoDpfMB'],\
menuText['ReadMacro4'], cascadeName = menuText['MacromoleculeMB'])


Dpf4FlexResSelectorGUI=CommandGUI()
Dpf4FlexResSelectorGUI.addMenuCommand('AutoTools41Bar', menuText['AutoDpfMB'],\
menuText['ReadFlexRes4'], cascadeName = menuText['MacromoleculeMB'])


Dpf4MacroChooserGUI=CommandGUI()
Dpf4MacroChooserGUI.addMenuCommand('AutoTools41Bar', menuText['AutoDpfMB'],\
menuText['ChooseMacro4'], cascadeName = menuText['MacromoleculeMB'])



Dpf4InitLigandGUI=CommandGUI()
Dpf4InitLigandGUI.addMenuCommand('AutoTools41Bar', menuText['AutoDpfMB'],\
menuText['AdjustLigand4'], cascadeName = menuText['SetLigandParmsMB'])



Dpf4LigandChooserGUI=CommandGUI()
Dpf4LigandChooserGUI.addMenuCommand('AutoTools41Bar', menuText['AutoDpfMB'],\
menuText['ChooseLigand4'], cascadeName = menuText['SetLigandParmsMB'])


Dpf4LigPDBQReaderGUI = CommandGUI()
Dpf4LigPDBQReaderGUI.addMenuCommand('AutoTools41Bar', menuText['AutoDpfMB'],\
menuText['ReadLigand4'],  cascadeName = menuText['SetLigandParmsMB'])


DpfEditorGUI=CommandGUI()
DpfEditorGUI.addMenuCommand('AutoTools41Bar', menuText['AutoDpfMB'],\
menuText['EditDpfMB'])


Dpf41SAWriterGUI=CommandGUI()
Dpf41SAWriterGUI.addMenuCommand('AutoTools41Bar', menuText['AutoDpfMB'],\
menuText['WriteSA41'], cascadeName = menuText['WriteDpfMB'])



Dpf41GAWriterGUI=CommandGUI()
Dpf41GAWriterGUI.addMenuCommand('AutoTools41Bar', menuText['AutoDpfMB'],\
menuText['WriteGA41'], cascadeName = menuText['WriteDpfMB'])



Dpf41LSWriterGUI=CommandGUI()
Dpf41LSWriterGUI.addMenuCommand('AutoTools41Bar', menuText['AutoDpfMB'],\
menuText['WriteLS41'], cascadeName = menuText['WriteDpfMB'])



Dpf41GALSWriterGUI=CommandGUI()
Dpf41GALSWriterGUI.addMenuCommand('AutoTools41Bar', menuText['AutoDpfMB'],\
menuText['WriteGALS41'], cascadeName = menuText['WriteDpfMB'])




SimAnnealGUI=CommandGUI()
SimAnnealGUI.addMenuCommand('AutoTools41Bar', menuText['AutoDpfMB'],\
menuText['SA'], cascadeName = menuText['SetSearchParmsMB'])


GAGUI=CommandGUI()
GAGUI.addMenuCommand('AutoTools41Bar', menuText['AutoDpfMB'],menuText['GA'],\
cascadeName = menuText['SetSearchParmsMB'])


LSGUI=CommandGUI()
LSGUI.addMenuCommand('AutoTools41Bar', menuText['AutoDpfMB'],'Local Search Parameters ',\
cascadeName = menuText['SetSearchParmsMB'])


SetDockingRunParmsGUI=CommandGUI()
SetDockingRunParmsGUI.addMenuCommand('AutoTools41Bar', menuText['AutoDpfMB'],\
    menuText['SetDockingRunParmsMB'])


SetAutoDock41ParametersGUI=CommandGUI()
SetAutoDock41ParametersGUI.addMenuCommand('AutoTools41Bar', menuText['AutoDpfMB'],\
    menuText['SetAutoDock41Parameters'], cascadeName = menuText['OtherOptionsMB'])



commandList = [
    {'name':'AD41dpf_read','cmd':DpfLoadDefaults(),'gui':DpfLoadDefaultsGUI},
    #{'name':'AD41dpf_chooseMacromolecule','cmd':Dpf4MacroChooser(),'gui':Dpf4MacroChooserGUI},
    #macromolecule
    {'name':'AD41dpf_readMacromolecule','cmd':Dpf4MacroSelector(),'gui':Dpf4MacroSelectorGUI},
    {'name':'AD41dpf_readFlexRes','cmd':Dpf4FlexResSelector(),'gui':Dpf4FlexResSelectorGUI},
    #ligand
    {'name':'AD41dpf_chooseFormattedLigand','cmd':Dpf4LigandChooser(),'gui':Dpf4LigandChooserGUI},
    {'name':'AD41dpf_readFormattedLigand','cmd':Dpf4LigPDBQReader(),'gui':Dpf4LigPDBQReaderGUI},
    {'name':'AD41dpf_initLigand','cmd':Dpf4InitLigand(),'gui':Dpf4InitLigandGUI},
    {'name':'AD41dpf_setGAparameters','cmd':GA(),'gui':GAGUI},
    {'name':'AD41dpf_setSAparameters','cmd':SimAnneal(),'gui':SimAnnealGUI},
    {'name':'AD41dpf_setLSparameters','cmd':LS(),'gui':LSGUI},
    {'name':'AD41dpf_setDockingParameters','cmd':SetDockingRunParms(),'gui':SetDockingRunParmsGUI},
    {'name':'AD41dpf_setAutoDock4Parameters','cmd':SetAutoDock41Parameters(),\
            'gui':SetAutoDock41ParametersGUI},
    {'name':'AD41dpf_writeGALS','cmd':Dpf41GALSWriter(),'gui':Dpf41GALSWriterGUI},
    {'name':'AD41dpf_writeGA','cmd':Dpf41GAWriter(),'gui':Dpf41GAWriterGUI},
    {'name':'AD41dpf_writeSA','cmd':Dpf41SAWriter(),'gui':Dpf41SAWriterGUI},
    {'name':'AD41dpf_writeLS','cmd':Dpf41LSWriter(),'gui':Dpf41LSWriterGUI},
    {'name':'AD41dpf_edit','cmd':DpfEditor(),'gui':DpfEditorGUI},
]



def initModule(vf):

    for dict in commandList:
        vf.addCommand(dict['cmd'], dict['name'], dict['gui'])
    if not hasattr(vf, 'ADdpf_setDpo'):
        vf.addCommand(DpfSetDpo(), 'ADdpf_setDpo', None)

    if vf.hasGui and 'AutoTools41Bar' in list(vf.GUI.menuBars.keys()):
        for item in list(vf.GUI.menuBars['AutoTools41Bar'].menubuttons.values()):
            item.configure(background = 'tan')
        if not hasattr(vf.GUI, 'adtBar'):
            vf.GUI.adtBar = vf.GUI.menuBars['AutoTools41Bar']
            vf.GUI.adtFrame = list(vf.GUI.adtBar.menubuttons.values())[0].master




        
