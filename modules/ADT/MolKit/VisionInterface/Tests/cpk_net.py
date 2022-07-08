########################################################################
#
#    Vision Network - Python source code - file generated by vision
#    Wednesday 11 July 2007 11:10:25 
#    
#       The Scripps Research Institute (TSRI)
#       Molecular Graphics Lab
#       La Jolla, CA 92037, USA
#
# Copyright: Daniel Stoffler, Michel Sanner and TSRI
#   
# revision: Guillaume Vareille
#  
#########################################################################
#
# $Header: /opt/cvs/python/packages/share1.5/MolKit/VisionInterface/Tests/cpk_net.py,v 1.8 2007/10/08 20:20:32 vareille Exp $
#
# $Id: cpk_net.py,v 1.8 2007/10/08 20:20:32 vareille Exp $
#

from traceback import print_exc
## loading libraries ##
from MolKit.VisionInterface.MolKitNodes import molkitlib
masterNet.getEditor().addLibraryInstance(molkitlib,"MolKit.VisionInterface.MolKitNodes", "molkitlib")

from DejaVu.VisionInterface.DejaVuNodes import vizlib
masterNet.getEditor().addLibraryInstance(vizlib,"DejaVu.VisionInterface.DejaVuNodes", "vizlib")

try:
    ## saving node Read Molecule ##
    from MolKit.VisionInterface.MolKitNodes import ReadMolecule
    Read_Molecule_0 = ReadMolecule(constrkw = {}, name='Read Molecule', library=molkitlib)
    masterNet.addNode(Read_Molecule_0,16,22)
    Read_Molecule_0.inputPortByName['filename'].widget.set("cv.pdb", run=False)
    Read_Molecule_0.configure(*(), **{'expanded': True})
except:
    print("WARNING: failed to restore ReadMolecule named Read Molecule in network masterNet")
    print_exc()
    Read_Molecule_0=None

try:
    ## saving node CPK Macro ##
    from MolKit.VisionInterface.MolKitNodes import CPKMacro
    CPK_Macro_1 = CPKMacro(constrkw = {}, name='CPK Macro', library=molkitlib)
    masterNet.addNode(CPK_Macro_1,117,152)
    Select_Nodes_5 = CPK_Macro_1.macroNetwork.nodes[3]
    Select_Nodes_5.inputPortByName['selectionString'].widget.set(".*", run=False)
    Extract_Atom_Property_6 = CPK_Macro_1.macroNetwork.nodes[4]
    Extract_Atom_Property_6.inputPortByName['propertyName'].widget.set("coords", run=False)
    spheres_7 = CPK_Macro_1.macroNetwork.nodes[5]
    spheres_7.inputPortByName['quality'].widget.set(15, run=False)
    spheres_7.inputPortByName['name'].widget.set("", run=False)

    ## saving connections for network CPK Macro ##
    CPK_Macro_1.macroNetwork.freeze()
    CPK_Macro_1.macroNetwork.unfreeze()

    ## modifying MacroOutputNode dynamic ports
    output_Ports_3 = CPK_Macro_1.macroNetwork.opNode
    output_Ports_3.inputPorts[1].configure(singleConnection=True)
    CPK_Macro_1.shrink()
except:
    print("WARNING: failed to restore CPKMacro named CPK Macro in network masterNet")
    print_exc()
    CPK_Macro_1=None

try:
    ## saving node Viewer ##
    from DejaVu.VisionInterface.DejaVuNodes import Viewer
    Viewer_8 = Viewer(constrkw = {}, name='Viewer', library=vizlib)
    masterNet.addNode(Viewer_8,39,235)
    ##
    ## Saving State for Viewer
    Viewer_8.vi.TransformRootOnly(1)
    ##

    ## Light Model
    ## End Light Model

    ## Light sources
    ## End Light sources 7

    ## Cameras
    ## Camera Number 0
    state = {'color': (0.0, 0.0, 0.0, 1.0), 'd2off': 1, 'height': 400, 'lookAt': [0.0, 0.0, 0.0], 'rootx': 18, 'pivot': [0.0, 0.0, 0.0], 'translation': [0.0, 0.0, 0.0], 'sideBySideTranslation': 0.0, 'fov': 40.0, 'scale': [1.0, 1.0, 1.0], 'stereoMode': 'MONO', 'width': 400, 'sideBySideRotAngle': 3.0, 'boundingbox': 0, 'projectionType': 0, 'contours': False, 'd2cutL': 150, 'direction': [0.0, 0.0, -30.0], 'd2cutH': 255, 'far': 50.0, 'd1off': 4, 'lookFrom': [0.0, 0.0, 30.0], 'd1cutH': 60, 'antialiased': 0, 'rotation': [1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0], 'd1ramp': [0.0, 0.0, 0.0, 0.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 3.0, 3.0, 3.0, 3.0, 3.0, 3.0, 4.0, 4.0, 4.0, 4.0, 7.0, 9.0, 12.0, 14.0, 17.0, 19.0, 22.0, 24.0, 27.0, 29.0, 32.0, 34.0, 37.0, 44.0, 51.0, 57.0, 64.0, 71.0, 78.0, 84.0, 91.0, 98.0, 105.0, 111.0, 118.0, 125.0, 126.0, 128.0, 129.0, 130.0, 132.0, 133.0, 135.0, 136.0, 137.0, 139.0, 140.0, 141.0, 143.0, 144.0, 145.0, 147.0, 148.0, 149.0, 151.0, 152.0, 154.0, 155.0, 156.0, 158.0, 159.0, 160.0, 162.0, 163.0, 164.0, 166.0, 167.0, 168.0, 170.0, 171.0, 173.0, 174.0, 175.0, 177.0, 178.0, 179.0, 181.0, 182.0, 183.0, 185.0, 186.0, 187.0, 189.0, 190.0, 192.0, 193.0, 194.0, 196.0, 197.0, 197.0, 198.0, 198.0, 199.0, 199.0, 199.0, 200.0, 200.0, 200.0, 201.0, 201.0, 202.0, 202.0, 202.0, 203.0, 203.0, 204.0, 204.0, 204.0, 205.0, 205.0, 205.0, 206.0, 206.0, 207.0, 207.0, 207.0, 208.0, 208.0, 209.0, 209.0, 209.0, 210.0, 210.0, 210.0, 211.0, 211.0, 212.0, 212.0, 212.0, 213.0, 213.0, 214.0, 214.0, 214.0, 215.0, 215.0, 215.0, 216.0, 216.0, 217.0, 217.0, 217.0, 218.0, 218.0, 219.0, 219.0, 219.0, 220.0, 220.0, 220.0, 221.0, 221.0, 222.0, 222.0, 222.0, 223.0, 223.0, 224.0, 224.0, 224.0, 225.0, 225.0, 225.0, 226.0, 226.0, 227.0, 227.0, 227.0, 228.0, 228.0, 228.0, 229.0, 229.0, 230.0, 230.0, 230.0, 231.0, 231.0, 232.0, 232.0, 232.0, 233.0, 233.0, 233.0, 234.0, 234.0, 235.0, 235.0, 235.0, 236.0, 236.0, 237.0, 237.0, 237.0, 238.0, 238.0, 238.0, 239.0, 239.0, 240.0, 240.0, 240.0, 241.0, 241.0, 242.0, 242.0, 242.0, 243.0, 243.0, 243.0, 244.0, 244.0, 245.0, 245.0, 245.0, 246.0, 246.0, 247.0, 247.0, 247.0, 248.0, 248.0, 248.0, 249.0, 249.0, 250.0, 250.0, 250.0, 251.0, 251.0, 252.0, 252.0, 252.0, 253.0, 253.0, 253.0, 254.0, 254.0, 255.0, 255.0], 'suspendRedraw': False, 'd1cutL': 0, 'd2scale': 0.0, 'near': 0.10000000000000001, 'drawThumbnail': False, 'rooty': 69, 'd1scale': 0.012999999999999999}
    Viewer_8.vi.cameras[0].Set(*(), **state)

    state = {'end': 40, 'density': 0.10000000000000001, 'color': (0.0, 0.0, 0.0, 1.0), 'enabled': False, 'start': 25, 'mode': 'GL_LINEAR'}
    Viewer_8.vi.cameras[0].fog.Set(*(), **state)

    ## End Cameras

    ## Clipping planes
    ## End Clipping planes

    ## Root object
    ## End Root Object

    ## Material for root
    if Viewer_8.vi.rootObject:
        pass  ## needed in case there no modif
    ## End Materials for root

    ## Clipping Planes for root
    if Viewer_8.vi.rootObject:
        Viewer_8.vi.rootObject.clipP = []
        Viewer_8.vi.rootObject.clipPI = []
        pass  ## needed in case there no modif
    ## End Clipping Planes for root

except:
    print("WARNING: failed to restore Viewer named Viewer in network masterNet")
    print_exc()
    Viewer_8=None

masterNet.run()
masterNet.freeze()

## saving connections for network cpk ##
if Read_Molecule_0 is not None and CPK_Macro_1 is not None:
    try:
        masterNet.connectNodes(
            Read_Molecule_0, CPK_Macro_1, "MolSets", "Assign Radii_molecules", blocking=True)
    except:
        print("WARNING: failed to restore connection between Read_Molecule_0 and CPK_Macro_1 in network masterNet")
if CPK_Macro_1 is not None and Viewer_8 is not None:
    try:
        masterNet.connectNodes(
            CPK_Macro_1, Viewer_8, "spheres_spheres", "geometries", blocking=True)
    except:
        print("WARNING: failed to restore connection between CPK_Macro_1 and Viewer_8 in network masterNet")
masterNet.unfreeze()


def loadSavedStates_Viewer_8(self=Viewer_8, event=None):
    ##
    ## Saving State for objects in Viewer
    ##

    ## End Object root

    ##
    ## Saving State for Viewer
    self.vi.TransformRootOnly(1)
    ##

    ## Light Model
    ## End Light Model

    ## Light sources
    ## End Light sources 7

    ## Cameras
    ## Camera Number 0
    state = {'color': (0.0, 0.0, 0.0, 1.0), 'd2off': 1, 'height': 400, 'lookAt': [0.0, 0.0, 0.0], 'pivot': [0.0, 0.0, 0.0], 'translation': [0.0, 0.0, 0.0], 'sideBySideTranslation': 0.0, 'fov': 40.0, 'scale': [1.0, 1.0, 1.0], 'stereoMode': 'MONO', 'width': 400, 'sideBySideRotAngle': 3.0, 'boundingbox': 0, 'projectionType': 0, 'contours': False, 'd2cutL': 150, 'direction': [0.0, 0.0, -30.0], 'd2cutH': 255, 'far': 50.0, 'd1off': 4, 'lookFrom': [0.0, 0.0, 30.0], 'd1cutH': 60, 'antialiased': 0, 'rotation': [1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0], 'd1ramp': [0.0, 0.0, 0.0, 0.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 3.0, 3.0, 3.0, 3.0, 3.0, 3.0, 4.0, 4.0, 4.0, 4.0, 7.0, 9.0, 12.0, 14.0, 17.0, 19.0, 22.0, 24.0, 27.0, 29.0, 32.0, 34.0, 37.0, 44.0, 51.0, 57.0, 64.0, 71.0, 78.0, 84.0, 91.0, 98.0, 105.0, 111.0, 118.0, 125.0, 126.0, 128.0, 129.0, 130.0, 132.0, 133.0, 135.0, 136.0, 137.0, 139.0, 140.0, 141.0, 143.0, 144.0, 145.0, 147.0, 148.0, 149.0, 151.0, 152.0, 154.0, 155.0, 156.0, 158.0, 159.0, 160.0, 162.0, 163.0, 164.0, 166.0, 167.0, 168.0, 170.0, 171.0, 173.0, 174.0, 175.0, 177.0, 178.0, 179.0, 181.0, 182.0, 183.0, 185.0, 186.0, 187.0, 189.0, 190.0, 192.0, 193.0, 194.0, 196.0, 197.0, 197.0, 198.0, 198.0, 199.0, 199.0, 199.0, 200.0, 200.0, 200.0, 201.0, 201.0, 202.0, 202.0, 202.0, 203.0, 203.0, 204.0, 204.0, 204.0, 205.0, 205.0, 205.0, 206.0, 206.0, 207.0, 207.0, 207.0, 208.0, 208.0, 209.0, 209.0, 209.0, 210.0, 210.0, 210.0, 211.0, 211.0, 212.0, 212.0, 212.0, 213.0, 213.0, 214.0, 214.0, 214.0, 215.0, 215.0, 215.0, 216.0, 216.0, 217.0, 217.0, 217.0, 218.0, 218.0, 219.0, 219.0, 219.0, 220.0, 220.0, 220.0, 221.0, 221.0, 222.0, 222.0, 222.0, 223.0, 223.0, 224.0, 224.0, 224.0, 225.0, 225.0, 225.0, 226.0, 226.0, 227.0, 227.0, 227.0, 228.0, 228.0, 228.0, 229.0, 229.0, 230.0, 230.0, 230.0, 231.0, 231.0, 232.0, 232.0, 232.0, 233.0, 233.0, 233.0, 234.0, 234.0, 235.0, 235.0, 235.0, 236.0, 236.0, 237.0, 237.0, 237.0, 238.0, 238.0, 238.0, 239.0, 239.0, 240.0, 240.0, 240.0, 241.0, 241.0, 242.0, 242.0, 242.0, 243.0, 243.0, 243.0, 244.0, 244.0, 245.0, 245.0, 245.0, 246.0, 246.0, 247.0, 247.0, 247.0, 248.0, 248.0, 248.0, 249.0, 249.0, 250.0, 250.0, 250.0, 251.0, 251.0, 252.0, 252.0, 252.0, 253.0, 253.0, 253.0, 254.0, 254.0, 255.0, 255.0], 'suspendRedraw': False, 'd1cutL': 0, 'd2scale': 0.0, 'near': 0.10000000000000001, 'drawThumbnail': False, 'd1scale': 0.012999999999999999}
    self.vi.cameras[0].Set(*(), **state)

    state = {'end': 40, 'density': 0.10000000000000001, 'color': (0.0, 0.0, 0.0, 1.0), 'enabled': False, 'start': 25, 'mode': 'GL_LINEAR'}
    self.vi.cameras[0].fog.Set(*(), **state)

    ## End Cameras

    ## Clipping planes
    ## End Clipping planes

    ## Root object
    ## End Root Object

    ## Material for root
    if self.vi.rootObject:
        pass  ## needed in case there no modif
    ## End Materials for root

    ## Clipping Planes for root
    if self.vi.rootObject:
        self.vi.rootObject.clipP = []
        self.vi.rootObject.clipPI = []
        pass  ## needed in case there no modif
    ## End Clipping Planes for root

Viewer_8.restoreStates_cb = Viewer_8.restoreStatesFirstRun = loadSavedStates_Viewer_8
Viewer_8.menu.add_separator()
Viewer_8.menu.add_command(label='Restore states', command=Viewer_8.restoreStates_cb)

#masterNet.run()
