#############################################################################
#
# Author: Ruth HUEY, Michel F. SANNER
#
# Copyright: M. Sanner TSRI 2000
#
#############################################################################


# $Header: /opt/cvs/python/packages/share1.5/AutoDockTools/autostartCommands.py,v 1.37 2010/11/23 17:40:27 rhuey Exp $
#
# $Id: autostartCommands.py,v 1.37 2010/11/23 17:40:27 rhuey Exp $
#
#
#
#
#
#

"""
This Module facilitates starting autogrid and autodock jobs and managing them

"""
from ViewerFramework.VFCommand import CommandGUI, Command
##  from ViewerFramework.gui import InputFormDescr
from mglutil.gui.InputForm.Tk.gui import InputFormDescr
from mglutil.popen2Threads import SysCmdInThread
from mglutil.util.callback import CallBackFunction
from mglutil.util.packageFilePath import findResourceFile
import tkinter.messagebox, tkinter.filedialog
from Pmv.mvCommand import MVCommand
from Pmv.guiTools import MoleculeChooser, BarButton, Kill

from MolKit.tree import TreeNode, TreeNodeSet
from MolKit.molecule import Atom

from tkinter.simpledialog import SimpleDialog
import types, string, tkinter, re
import subprocess, os, sys, socket, time
from string import splitfields



try:
    import Entropia
    entropiaPresent = 1
except:
    entropiaPresent = 0


def removePCs():
    print('removing PCs from hostTable')
     

if entropiaPresent:
    from Entropia.EntropiaDef import entropia_job_dir
    from Entropia.EntropiaUI import EntropiaUI
    from Entropia.EntropiaEx import EntropiaError
    import ftplib


#these are the texts on menubuttons, menu entries etc:
menuText = {}
menuText['StartMB'] = 'Run'
#menuText['StartMB'] = '   Run   '
menuText['startGridMB'] = 'Run AutoGrid...'
menuText['startDockMB'] = 'Run AutoDock...'
menuText['processManagerMB'] = 'Job Status...'
menuText['editHostsMB'] = 'Host Preferences...'



class ADKill(Kill):

    def __init__(self, master):
        self.master=master
        Kill.__init__(self, master)
        self.view.set(4)
        self.bar.file.forget()
        self.bar.view.forget()
        self.frame2=tkinter.Frame(self.master)
        self.frame2.pack()
        self.dismiss = tkinter.Button(self.frame2, text='Dismiss', command=self.quit)
        self.update.forget()
        self.dismiss.pack(side = 'right', fill = 'x')
        self.winfo_toplevel().title('Autodock Process Manager')
        self.done=0


    def kill(self, selected):
        if not selected:
            return
        c=self.format_list[self.format.get()][2]
        pid = string.split(selected)[c]
        host = string.split(selected)[-1]
        #put in are you sure dialog here
        t = "Do you wish to kill this process?"
        d= SimpleDialog(self.master, text=t, buttons=['Yes','No'],
        default = 0, title = 'Kill Process')
        ok = d.go()
        if ok == 0:
            if host != self.vf.ADstart_manage.localHost:
                cmdStr="\'kill -9 %s\'"%pid
            else:
                cmdStr="ssh " + host+ " -n \'kill -9 %s\'"%pid
            subprocess.getoutput(cmdStr)
        hosts = self.hosts
        self.do_update(self.psList, hosts)


    def updateHosts(self, hostList):
        self.hosts=hostList


    def do_update(self, psList=['autodock'], hosts=None):
        if not hosts: return
        self.hosts=hosts
        self.psList = psList
        format = self.format_list[self.format.get()][1]
        view = self.view_list[self.view.get()][1]
        self.frame.list.delete(0,tkinter.AtEnd())
        self.done=1
        for item in self.hosts:
            if item == self.vf.ADstart_manage.localHost:
                cmdStr="ps %s %s"%(view,format)
            else:
                cmdStr="ssh " + item+ " -n \'ps %s %s\'"%(view,format)
            p=subprocess.getoutput(cmdStr)
            if p:
                list = string.splitfields(p,'\n')
                del list[0]
                for line in list:
                    for ps in psList:
                        if string.find(line, ps)>-1:
                            #check here that the line has ps: autodock/autogrid 
                            line = line + ' ' + item
                            self.frame.list.insert(0,line)
                            self.done=0
            else:
                self.hosts.remove(item)
        return(self.hosts)


    def quit(self, event=None):
        self.master.withdraw()



class ADProcessManager(MVCommand):

    def onAddCmdToViewer(self):
        if not self.vf.hasGui:
            self.root = tkinter.Tk()
            self.root.withdraw()
            root = self.root
        else:
            root = self.vf.GUI.ROOT
        self.hostVal=tkinter.IntVar(master=root)
        self.macroVal=tkinter.IntVar(master=root)
        self.top = tkinter.Toplevel(master=root)
        self.top.withdraw()
        self.kill = ADKill(self.top)
        self.kill.vf = self.vf

    def __init__(self):
        MVCommand.__init__(self)
        self.localHost = socket.gethostname()
        self.invalid = 0
        import AutoDockTools
        self.hostDict = AutoDockTools.hostDict
        self.currentHosts=None
        self.psList=None


    def addHost(self, host):
        if not self.currentHosts: self.currentHosts=[]
        if not host in self.currentHosts:
            self.currentHosts.append(host)

    def addProcess(self, ps):
        if not self.psList: self.psList=[]
        if not ps in self.psList:
            self.psList.append(ps)

    def adUpdate(self):
        #currentHosts should be all hosts of all active jobs
        if not self.currentHosts: self.currentHosts=[]
        self.currentHosts = self.kill.do_update(self.psList,self.currentHosts)
        if self.kill.done:
            self.kill.master.withdraw()
        else:
            self.kill.after(100,self.adUpdate)

    def guiCallback(self, event=None):
        if not self.top.winfo_ismapped():
            self.top.deiconify()
        self.kill.after(100, self.adUpdate)

    def __call__(self, **kw):
        self.doitWrapper(*(), **kw)

    def doit(self):
        #kill
        print('killed')

ADProcessManagerGUI=CommandGUI()
ADProcessManagerGUI.addMenuCommand('AutoToolsBar', menuText['StartMB'], menuText['processManagerMB'])



class AutoStarter(MVCommand):
    """Base class for AutoGridStarter and AutoDockStarter, whose command structure is
very similar with a few differences such as programType, title for file browser, first letters of required parameter and log file extensions and the presence or absence of possible flags,etc """


    def onAddCmdToViewer(self):
        if self.vf.hasGui:
            self.hostVal=tkinter.IntVar(master=self.vf.GUI.ROOT)
            self.macroVal=tkinter.IntVar(master=self.vf.GUI.ROOT)
            self.projectVal=tkinter.IntVar(master=self.vf.GUI.ROOT)


    def __init__(self, program=None, dictObj=None,
            ifdTitle="Run BaseClass", 
            browserPFTitle="baseclassPF", browserEXETitle='baseClass',
            browserLOGTitle="baseLog", logType='.base',
            pfType='.bpf', programType=None):

        MVCommand.__init__(self)
        self.program=program
        self.programType=programType
        self.dictObj = dictObj
        self.ifdTitle=ifdTitle
        self.browserPFTitle=browserPFTitle
        self.browserEXETitle=browserEXETitle
        self.browserLOGTitle=browserLOGTitle
        self.logType=logType
        self.pfType=pfType
        self.qT='int'
        self.command=None
        self.RemoteCommand=None
        self.nqeJobFile=None
        self.Host=None
        self.Exe=None
        self.FlagStr=""
        self.ParmFile=None
        self.LogFile=None
        self.Nice=20
        #
        self.localHost = socket.gethostname()
        self.invalid=0
        import AutoDockTools
        self.hostDict=AutoDockTools.hostDict


        
    def guiCallback(self, event=None):
        #AutoStarter: dict is only self.vf.gpo since autodock is handled separately
        self.customizeGUI()
        if not hasattr(self, 'form'):
            if self.vf.hasGui:    
                #self.form = self.vf.getUserInput(self.ifd, scrolledFrame = 1, width = 1000, height = 300,modal=0, blocking=0)
                self.form = self.vf.getUserInput(self.ifd, modal=0,blocking=0)
                self.form.root.protocol('WM_DELETE_WINDOW',self.Close_cb)
                self.topLevel = self.form.root
            else:
                ##  from ViewerFramework.gui import InputForm
                from mglutil.gui.InputForm.Tk.gui import InputForm
                self.form = InputForm(self.vf.master,self.ifd,modal=0, blocking=0)
                self.form.root.protocol('WM_DELETE_WINDOW',self.Close_cb)
                self.topLevel = self.form.root
            if self.dictObj:
                self.dict=eval('self.vf.%s'%self.dictObj)
            if hasattr(self.vf, 'hasGui') and hasattr(self.vf, self.dictObj) and  len(self.dict.gpf_filename):    
                if self.paramFile.get()=='':
                    self.paramFile.set(self.dict.gpf_filename)
                    self.updateLF()
            #4/5 return seems better than leave
            entryItems= ['lFentry','eXentry','pFentry','nqeTimeEntry','nqeCpuEntry',\
                'pbsCpuEntry','pbsTimeEntry','pbsDirEntry','pbsWallTimeEntry',\
                'pbsCpuEntry', 'niceEntry']
            for item in entryItems:
                self.ifd.entryByName[item]['widget'].bind('<Return>', self.getCmd)
            self.ifd.entryByName['pFentry']['widget'].bind('<Return>', self.updateLF)
            self.ifd.entryByName['mNentry']['widget'].bind('<Return>', self.getMacro)
            self.ifd.entryByName['mNMenu']['widget'].bind('<ButtonPress>', self.buildMacroMenu, add='+')
            self.ifd.entryByName['hNentry']['widget'].bind('<Return>', self.getHost)
            self.intWids=['niceLab','niceEntry']
            if os.name == 'nt': #sys.platform=='win32':
                for item in self.intWids:
                    self.ifd.entryByName[item]['widget'].grid_forget()
                self.niceLevel.set('0')
            self.commonWids=['hNLab','hNentry','eXLab','eXentry','eXbutton',
                'pFLab','pFentry','pFbutton',
                'lFLab','lFentry','lFbutton']
            self.nqeWids=['nqeCpuLab','nqeCpuEntry','nqeTimeLab','nqeTimeEntry']
            self.pbsWids=['pbsCpuLab','pbsCpuEntry','pbsDirLab','pbsDirEntry','pbsTimeLab','pbsTimeEntry','pbsWallTimeLab','pbsWallTimeEntry','pbsRerunCB']
            self.entWids=['pjLab','pjentry','pjMenu','nodesEntLab',
            'nodesEnt', 'gpfEntLab', 'gpfEnt','pdbqsEntLab','pdbqsEnt',
            'dpfEntLab','dpfEnt', 'pdbqEntLab','pdbqEnt',
            'jobDirEntLab','jobDirEnt', 'gpfFilterEnt', 'pdbqsFilterEnt',
            'dpfFilterEnt','pdbqFilterEnt']
            self.entWidLCS=['gpfFiles','pdbqsFiles','dpfFiles','pdbqFiles']
            self.entButs=[ 'uploadGpfFileBut','uploadPdbqFileBut',
                'uploadDpfFileBut','uploadPdbqsFileBut', 'monitorCB',
                'ftpBackCB']
            self.getMacroVal(0)
            self.flagWids=[]
            self.form.autoSize()


    def updateLCS(self, key, event=None):
        if not entropiaPresent: return
        keyList= ['gpf','pdbqs','dpf','pdbq']
        itemList= ['gpfFiles','pdbqsFiles','dpfFiles','pdbqFiles']
        fileList=[self.EntropiaUI.gpf_list,self.EntropiaUI.pdbqs_list,self.EntropiaUI.dpf_list,self.EntropiaUI.pdbq_list]
        #compile the re items if any
        reList=[]
        for filterStr in [self.gpfFilter.get(),self.pdbqsFilter.get(),self.dpfFilter.get(), self.pdbqFilter.get()]:
            reList.append(re.compile(filterStr))
        if key:
            ind=keyList.index(key)
            item=itemList[ind]
            files=fileList[ind]
            reitem=reList[ind]
            lb=self.ifd.entryByName[item]['widget'].lb
            lb.delete(0,'end')
            for f in files:
                match=reitem.match(f)
                if match!=None:
                    lb.insert(lb.index('end'),match.string)
                #lb.insert(lb.index('end'),f)
        else:
            for i in range(4):
                #'gpfFiles','pdbqsFiles','dpfFiles','pdbqFiles'
                item=itemList[i]
                files=fileList[i]
                reitem=reList[i]
                lb=self.ifd.entryByName[item]['widget'].lb
                lb.delete(0,'end')
                for f in files:
                    match=reitem.match(f)
                    if match!=None:
                        lb.insert(lb.index('end'), match.string)
 

    def uploadFiles(self,key, event=None):
        if not entropiaPresent: return
        titleStr='Upload '+key+' file:'
        newfile=self.vf.askFileOpen(types=[(key,'*'+key)], title=titleStr)
        if newfile:
            try:
                self.EntropiaUI.upload(newfile)
            except EntropiaError as msg:
                self.vf.warningMsg(msg)
                return
            self.updateLCS(key[1:])

    def setFile(self,item,event=None):
        pass
        
    def customizeGUI(self):
        #AutoStarter
        if not hasattr(self, 'ifd'):
            #for the moment:
            self.gpf_list=[]
            self.dpf_list=[]
            self.pdbq_list=[]
            self.pdbqs_list=[]

            #self.gpfFileList=['h2.gpf','hpi1s.gpf']
            #self.dpfFileList=['h2.dpf','hpi1s.dpf']
            #self.pdbqFileList=['h2.out.pdbq','hpi1s.out.pdbq']
            #self.pdbqsFileList=['1crn.pdbqs','1hvr.pdbqs']
            ifd=self.ifd=InputFormDescr(title=self.ifdTitle)
            self.execPath = tkinter.StringVar(master=self.vf.GUI.ROOT)
            self.workingDirPath = tkinter.StringVar(master=self.vf.GUI.ROOT, value = os.getcwd() ) # N3P
            self.queueType = tkinter.StringVar(master=self.vf.GUI.ROOT)
            self.queueType.set('int')
            self.jobFile = tkinter.StringVar(master=self.vf.GUI.ROOT)
            self.jobFile.set('')
            self.paramFile = tkinter.StringVar(master=self.vf.GUI.ROOT)
            self.paramFile.set('')
            self.niceLevel=tkinter.StringVar(master=self.vf.GUI.ROOT)
            self.niceLevel.set('20')
            self.nqeTime=tkinter.StringVar(master=self.vf.GUI.ROOT)
            self.nqeTime.set('144000')
            self.nqeCpu=tkinter.StringVar(master=self.vf.GUI.ROOT)
            self.nqeCpu.set('1')
            self.pbsCpu=tkinter.StringVar(master=self.vf.GUI.ROOT)
            self.pbsCpu.set('1')
            self.pbsCpuTime=tkinter.StringVar(master=self.vf.GUI.ROOT)
            self.pbsCpuTime.set('24:00:00')
            self.pbsWallTime=tkinter.StringVar(master=self.vf.GUI.ROOT)
            self.pbsWallTime.set('24:30:00')
            self.pbsRerun=tkinter.StringVar(master=self.vf.GUI.ROOT)
            self.pbsRerun.set('y')
            self.logFile = tkinter.StringVar(master=self.vf.GUI.ROOT)
            self.cmd = tkinter.StringVar(master=self.vf.GUI.ROOT)
            self.setUpFlagVars()
            self.pidStr = tkinter.StringVar(master=self.vf.GUI.ROOT)
            self.macroName = tkinter.StringVar(master=self.vf.GUI.ROOT)
            self.hostName = tkinter.StringVar(master=self.vf.GUI.ROOT)
            self.remoteDir = tkinter.StringVar(master=self.vf.GUI.ROOT)
            try:
                usr = os.environ['USER']
                self.remoteDir.set('/usr/people/'+usr)
            except:
                self.remoteDir.set('./')
            self.showMacroMenu = tkinter.IntVar(master=self.vf.GUI.ROOT)
            self.showHostMenu = tkinter.IntVar(master=self.vf.GUI.ROOT)
            #the tkinter variables for the entropia stuff
            self.projectName=tkinter.StringVar(master=self.vf.GUI.ROOT)
            self.gpf=tkinter.StringVar(master=self.vf.GUI.ROOT)
            self.dpf=tkinter.StringVar(master=self.vf.GUI.ROOT)
            self.pdbq=tkinter.StringVar(master=self.vf.GUI.ROOT)
            self.pdbqs=tkinter.StringVar(master=self.vf.GUI.ROOT)
            self.jobDir=tkinter.StringVar(master=self.vf.GUI.ROOT)
            if entropiaPresent:
                self.jobDir.set(entropia_job_dir + 'job_id')
            self.nodes=tkinter.StringVar(master=self.vf.GUI.ROOT)
            self.nodes.set('1')
            self.gpfFilter=tkinter.StringVar(master=self.vf.GUI.ROOT)
            self.pdbqsFilter=tkinter.StringVar(master=self.vf.GUI.ROOT)
            self.dpfFilter=tkinter.StringVar(master=self.vf.GUI.ROOT)
            self.pdbqFilter=tkinter.StringVar(master=self.vf.GUI.ROOT)
            self.monitorVar=tkinter.IntVar(master=self.vf.GUI.ROOT)
            self.ftpBackVar=tkinter.IntVar(master=self.vf.GUI.ROOT)
            ifd.append( {'name': 'mNLab',
                'widgetType': tkinter.Label,
                'text': 'Macro Name:',
                'gridcfg':{'sticky':tkinter.E}})
            ifd.append( {'name': 'mNentry',
                'widgetType':tkinter.Entry,
                'wcfg':{
                    'width':25,
                    'textvariable': self.macroName,},
                'gridcfg':{'sticky':tkinter.E,'row':-1,'column':1}})
            ifd.append( {'name': 'mNMenu',
                'widgetType':tkinter.Menubutton,
                'text': 'macros',
                'gridcfg':{'sticky':tkinter.W,'row':-1, 'column':2}})
            ifd.append( {'name': 'hNLab',
                'widgetType': tkinter.Label,
                'text': 'Host Name:',
                'gridcfg':{'sticky':tkinter.E}})
            ifd.append( {'name': 'hNentry',
                'widgetType':tkinter.Entry,
                'wcfg':{
                    'width':25,
                    'textvariable': self.hostName,
                },
                'gridcfg':{'sticky':tkinter.E,'row':-1,'column':1}})


            # here you define the working directory
            # N3P trace
            ifd.append( {'name': 'wDLab',
                'widgetType': tkinter.Label,
                'text': 'Working Directory:',
                'gridcfg':{'sticky':tkinter.E}})
            ifd.append( {'name': 'wDentry',
                'widgetType':tkinter.Label,
                'wcfg':{
                    'width':65,
                    'justify':tkinter.LEFT,
                    'textvariable': self.workingDirPath,
                },
                'gridcfg':{'sticky':tkinter.E,'row':-1,'column':1, 'columnspan':12}})
            ifd.append({'name': 'wDbutton',
                'widgetType': tkinter.Button,
                'text':'Browse',
                'wcfg':{'bd':6},
                'command':self.browseWD,
                'gridcfg':{'sticky':tkinter.W,'row':-1, 'column':13}})

            # # # # #  N3P trace


            ifd.append( {'name': 'eXLab',
                'widgetType': tkinter.Label,
                'text': 'Program Pathname:',
                'gridcfg':{'sticky':tkinter.E}})
            ifd.append( {'name': 'eXentry',
                'widgetType':tkinter.Entry,
                'wcfg':{
                    'width':65,
                    'textvariable': self.execPath,
                },
                'gridcfg':{'sticky':tkinter.E,'row':-1,'column':1, 'columnspan':12}})
            ifd.append({'name': 'eXbutton',
                'widgetType': tkinter.Button,
                'text':'Browse',
                'wcfg':{'bd':6},
                'command':self.browseEX,
                'gridcfg':{'sticky':tkinter.W,'row':-1, 'column':13}})

            ifd.append( {'name': 'pFLab',
                'widgetType': tkinter.Label,
                'text': 'Parameter Filename:',
                'gridcfg':{'sticky':tkinter.E}})
            ifd.append( {'name': 'pFentry',
                'widgetType':tkinter.Entry,
                'wcfg':{
                    'width':65,
                    'textvariable': self.paramFile,
                },
                'gridcfg':{'sticky':tkinter.E,'row':-1,'column':1, 'columnspan':12}})
            ifd.append({'name': 'pFbutton',
                'widgetType': tkinter.Button,
                'text':'Browse',
                'wcfg':{'bd':6},
                'command':self.browsePF,
                'gridcfg':{'sticky':tkinter.W,'row':-1, 'column':13}})
            ifd.append( {'name': 'lFLab',
                'widgetType': tkinter.Label,
                'text': 'Log Filename:',
                'gridcfg':{'sticky':tkinter.E}})
            ifd.append( {'name': 'lFentry',
                'widgetType':tkinter.Entry,
                'wcfg':{
                    'width':65,
                    'textvariable': self.logFile,
                },
                'gridcfg':{'sticky':tkinter.E,'row':-1,'column':1, 'columnspan':12}})
            ifd.append({'name': 'lFbutton',
                'widgetType': tkinter.Button,
                'text':'Browse',
                'wcfg':{'bd':6},
                'command':self.browseLF,
                'gridcfg':{'sticky':tkinter.W,'row':-1, 'column':13}})
            self.getFlags()
            ifd.append({'name':'niceLab',
                'widgetType':tkinter.Label,
                'text': 'Nice Level:',
                'gridcfg':{'sticky':tkinter.E}})
            ifd.append( {'name': 'niceEntry',
                'widgetType':tkinter.Entry,
                'wcfg':{
                    'width':25,
                    'textvariable': self.niceLevel,
                },
                'gridcfg':{'sticky':tkinter.E,'row':-1,'column':1}})
            ifd.append({'name':'pbsDirLab',
                'widgetType':tkinter.Label,
                'text': 'PBS: Remote Directory:',
                'gridcfg':{'sticky':tkinter.E}})
            ifd.append( {'name': 'pbsDirEntry',
                'widgetType':tkinter.Entry,
                'wcfg':{
                    'width':65,
                    'textvariable': self.remoteDir,
                },
                'gridcfg':{'sticky':tkinter.E,'row':-1,'column':1, 'columnspan':12}})
            ifd.append({'name':'nqeTimeLab',
                'widgetType':tkinter.Label,
                'text': 'NQE: Time Limit:',
                'gridcfg':{'sticky':tkinter.E}})
            ifd.append( {'name': 'nqeTimeEntry',
                'widgetType':tkinter.Entry,
                'wcfg':{
                    'width':25,
                    'textvariable': self.nqeTime,
                },
                'gridcfg':{'sticky':tkinter.E,'row':-1,'column':1}})
            ifd.append({'name':'pbsTimeLab',
                'widgetType':tkinter.Label,
                'text': 'PBS: CpuTime Limit:',
                'gridcfg':{'sticky':tkinter.E}})
            ifd.append( {'name': 'pbsTimeEntry',
                'widgetType':tkinter.Entry,
                'wcfg':{
                    'width':25,
                    'textvariable': self.pbsCpuTime,
                },
                'gridcfg':{'sticky':tkinter.E,'row':-1,'column':1}})
            ifd.append({'name':'pbsWallTimeLab',
                'widgetType':tkinter.Label,
                'text': 'PBS: WallTime Limit:',
                'gridcfg':{'sticky':tkinter.E}})
            ifd.append( {'name': 'pbsWallTimeEntry',
                'widgetType':tkinter.Entry,
                'wcfg':{
                    'width':25,
                    'textvariable': self.pbsWallTime,
                },
                'gridcfg':{'sticky':tkinter.E,'row':-1,'column':1}})
            ifd.append({'name':'pbsRerunCB',
                'widgetType':tkinter.Checkbutton,
                'text': 'PBS: Rerun on System Crash',
                'onvalue':'y',
                'offvalue':'n',
                'variable':self.pbsRerun,
                'command': self.getCmd,
                'gridcfg':{'sticky':tkinter.E+tkinter.W,'columnspan':2}})
            ifd.append({'name':'pbsCpuLab',
                'widgetType':tkinter.Label,
                'text': 'PBS: Number of Processors:',
                'gridcfg':{'sticky':tkinter.E}})
            ifd.append( {'name': 'pbsCpuEntry',
                'widgetType':tkinter.Entry,
                'wcfg':{
                    'width':25,
                    'textvariable': self.pbsCpu,
                },
                'gridcfg':{'sticky':tkinter.E,'row':-1,'column':1}})
            ifd.append({'name':'nqeCpuLab',
                'widgetType':tkinter.Label,
                'text': 'NQE: Number of Processors:',
                'gridcfg':{'sticky':tkinter.E}})
            ifd.append( {'name': 'nqeCpuEntry',
                'widgetType':tkinter.Entry,
                'wcfg':{
                    'width':25,
                    'textvariable': self.nqeCpu,
                },
                'gridcfg':{'sticky':tkinter.E,'row':-1,'column':1}})
            #next the widgets for entropia widgets:
            self.showProjectMenu = tkinter.IntVar(master=self.vf.GUI.ROOT)
            ifd.append( {'name': 'pjLab',
                'widgetType': tkinter.Label,
                'text': 'project:',
                'gridcfg':{'sticky':tkinter.E}})
            ifd.append( {'name': 'pjentry',
                'widgetType':tkinter.Entry,
                'wcfg':{
                    'width':25,
                    'textvariable': self.projectName,
                },
                'gridcfg':{'sticky':tkinter.E,'row':-1,'column':1}})
            ifd.append( {'name': 'pjMenu',
                'widgetType':tkinter.Menubutton,
                'text': 'projects',
                'gridcfg':{'sticky':tkinter.W,'row':-1, 'column':2}})
            ifd.append({'name':'nodesEntLab',
                'widgetType':tkinter.Label,
                'text': 'number of nodes',
                'gridcfg':{'sticky':tkinter.E}})
            ifd.append( {'name': 'nodesEnt',
                'widgetType':tkinter.Entry,
                'wcfg':{
                    'width':25,
                    'textvariable': self.nodes,
                },
                'gridcfg':{'sticky':tkinter.E,'row':-1,'column':1}})
            ifd.append({'name':'gpfEntLab',
                'widgetType':tkinter.Label,
                'text': 'gpf file',
                'gridcfg':{'sticky':tkinter.E}})
            ifd.append( {'name': 'gpfEnt',
                'widgetType':tkinter.Entry,
                'wcfg':{
                    'width':25,
                    'textvariable': self.gpf,
                },
                'gridcfg':{'sticky':tkinter.E,'row':-1,'column':1}})
            ifd.append({'name':'pdbqsEntLab',
                'widgetType':tkinter.Label,
                'text': 'pdbqs file',
                'gridcfg':{'sticky':tkinter.E}})
            ifd.append( {'name': 'pdbqsEnt',
                'widgetType':tkinter.Entry,
                'wcfg':{
                    'width':25,
                    'textvariable': self.pdbqs,
                },
                'gridcfg':{'sticky':tkinter.E,'row':-1,'column':1}})
            ifd.append({'name':'dpfEntLab',
                'widgetType':tkinter.Label,
                'text': 'dpf file',
                'gridcfg':{'sticky':tkinter.E}})
            ifd.append( {'name': 'dpfEnt',
                'widgetType':tkinter.Entry,
                'wcfg':{
                    'width':25,
                    'textvariable': self.dpf,
                },
                'gridcfg':{'sticky':tkinter.E,'row':-1,'column':1}})
            ifd.append({'name':'pdbqEntLab',
                'widgetType':tkinter.Label,
                'text': 'pdbq file',
                'gridcfg':{'sticky':tkinter.E}})
            ifd.append( {'name': 'pdbqEnt',
                'widgetType':tkinter.Entry,
                'wcfg':{
                    'width':25,
                    'textvariable': self.pdbq,
                },
                'gridcfg':{'sticky':tkinter.E,'row':-1,'column':1}})
            ifd.append( {'name': 'monitorCB',
                'widgetType':tkinter.Checkbutton,
                'text': 'Monitor job',
                'variable': self.monitorVar,
                'gridcfg':{'sticky':tkinter.W,'row':-1, 'column':2}})
            ifd.append({'name':'jobDirEntLab',
                'widgetType':tkinter.Label,
                'text': 'job directory',
                'gridcfg':{'sticky':tkinter.E}})
            ifd.append( {'name': 'jobDirEnt',
                'widgetType':tkinter.Entry,
                'wcfg':{
                    'width':25,
                    'textvariable': self.jobDir,
                },
                'gridcfg':{'sticky':tkinter.E,'row':-1,'column':1}})
            ifd.append( {'name': 'ftpBackCB',
                'widgetType':tkinter.Checkbutton,
                'text': 'FTP back',
                'variable': self.ftpBackVar,
                'gridcfg':{'sticky':tkinter.W,'row':-1, 'column':2}})
            ifd.append( {'name': 'cmdentry',
                'widgetType':tkinter.Entry,
                'wcfg':{
                    'width':90,
                    'label': 'Cmd :',
                    'textvariable': self.cmd,
                },
                'gridcfg':{'sticky':tkinter.W+tkinter.E ,'columnspan':15}})
            ifd.append({'widgetType': tkinter.Button,
                'text':'Launch',
                'wcfg':{'bd':6},
                'gridcfg':{'sticky':tkinter.E+tkinter.W,'columnspan':3},
                'command':self.callDoit_cb})
            ifd.append({'widgetType': tkinter.Button,
                'text':'Cancel',
                'wcfg':{'bd':6},
                'gridcfg':{'sticky':tkinter.E+tkinter.W,'row':-1,'column':3,'columnspan':2},
                'command':self.Close_cb})
            #last the widgets for the Entropia lists:
            #ifd.append({'name':'gpfFilterLab',
                #'widgetType':Tkinter.Label,
                #'text': 'gpf file filter',
                #'gridcfg':{'sticky':Tkinter.E}})
            ifd.append({'name': 'gpfFilterEnt',
                'widgetType':tkinter.Entry,
                'wcfg':{
                    'width':25,
                    'textvariable': self.gpfFilter,
                },
                'gridcfg':{'sticky':tkinter.E}})
            #ifd.append({'name':'pdbqsFilterLab',
                #'widgetType':Tkinter.Label,
                #'text': 'pdbqs file filter',
                #'gridcfg':{'sticky':Tkinter.E,'row':-1,'column':4}})
            ifd.append( {'name': 'pdbqsFilterEnt',
                'widgetType':tkinter.Entry,
                'wcfg':{
                    'width':25,
                    'textvariable': self.pdbqsFilter,
                },
                'gridcfg':{'sticky':tkinter.E,'row':-1,'column':1}})
            #ifd.append({'name':'dpfFilterLab',
                #'widgetType':Tkinter.Label,
                #'text': 'dpf file filter',
                #'gridcfg':{'sticky':Tkinter.E}})
            ifd.append( {'name': 'dpfFilterEnt',
                'widgetType':tkinter.Entry,
                'wcfg':{
                    'width':25,
                    'textvariable': self.dpfFilter,
                },
                'gridcfg':{'sticky':tkinter.E,'row':-1,'column':2}})
            #ifd.append({'name':'pdbqFilterLab',
                #'widgetType':Tkinter.Label,
                #'text': 'pdbq file filter',
                #'gridcfg':{'sticky':Tkinter.E,'row':-1,'column':6}})
            ifd.append( {'name': 'pdbqFilterEnt',
                'widgetType':tkinter.Entry,
                'wcfg':{
                    'width':25,
                    'textvariable': self.pdbqFilter,
                },
                'gridcfg':{'sticky':tkinter.E,'row':-1,'column':3}})
            ifd.append({'widgetType':'ListChooser',
                'name':'gpfFiles',
                'entries':self.gpf_list,
                'mode':'single',
                'title':'Select gpf file',
                'lbwcfg':{'height':5,'selectforeground':'red','exportselection':0},
                'command':CallBackFunction(self.setFile,'gpfFiles'),
                'gridcfg':{'sticky':'w','rowspan':5}})
            ifd.append({'widgetType':'ListChooser',
                'name':'pdbqsFiles',
                'entries':self.pdbqs_list,
                'mode':'single',
                'lbwcfg':{'height':5, 'selectforeground':'red','exportselection':0},
                'command':CallBackFunction(self.setFile,'pdbqsFiles'),
                'title':'Select pdbqs file',
                'gridcfg':{'sticky':'w','column':1,'row':-5,
                'rowspan':5}})
            ifd.append({'widgetType':'ListChooser',
                'name':'dpfFiles',
                'entries':self.dpf_list,
                'title':'Select dpf file',
                'mode':'single',
                'lbwcfg':{'height':5, 'selectforeground':'red','exportselection':0},
                'command':CallBackFunction(self.setFile,'dpfFiles'),
                'gridcfg':{'sticky':'w','column':2,'row':-9,
                'rowspan':5}})
            ifd.append({'widgetType':'ListChooser',
                'name':'pdbqFiles',
                'entries':self.pdbq_list,
                'title':'Select pdbq file',
                'mode':'single',
                'command':CallBackFunction(self.setFile,'pdbqFiles'),
                'lbwcfg':{'height':5, 'selectforeground':'red','exportselection':0},
                'gridcfg':{'sticky':'w','column':3,'row':-13,
                'rowspan':5}})
            ifd.append({'name':'uploadGpfFileBut',
                'widgetType':tkinter.Button,
                'text': 'Upload gpf File',
                'command': CallBackFunction(self.uploadFiles,'.gpf'),
                'gridcfg':{'sticky':tkinter.E+tkinter.W}})
            ifd.append({'name':'uploadPdbqsFileBut',
                'widgetType':tkinter.Button,
                'text': 'Upload pdbqs File',
                'command': CallBackFunction(self.uploadFiles,'.pdbqs'),
                'gridcfg':{'sticky':tkinter.E+tkinter.W,'column':1, 'row':-1}})
            ifd.append({'name':'uploadDpfFileBut',
                'widgetType':tkinter.Button,
                'text': 'Upload dpf File',
                'command': CallBackFunction(self.uploadFiles,'.dpf'),
                'gridcfg':{'sticky':tkinter.E+tkinter.W,'column':2, 'row':-1}})
            ifd.append({'name':'uploadPdbqFileBut',
                'widgetType':tkinter.Button,
                'text': 'Upload pdbq File',
                'command': CallBackFunction(self.uploadFiles,'.pdbq'),
                'gridcfg':{'sticky':tkinter.E+tkinter.W,'column':3, 'row':-1}})
        else:
            if hasattr(self, 'form') and self.form!=None:
                self.form.deiconify()
                self.form.autoSize()
        
    
    def Close_cb(self, event=None):
        self.form.root.withdraw()

    def callDoit_cb(self, event = None):
        self.doitWrapper(self.cmd.get(),log=1,redraw=0)

    def setUpFlagVars(self):
        self.flagVar = tkinter.IntVar(master=self.vf.GUI.ROOT)
        self.flagVar.set(0)

    def getFlags(self):
        pass

    def __call__(self, cmd, ask=1, **kw):
        kw['ask']=ask
        self.doitWrapper(*(cmd,), **kw)


    def doit(self, cmd, ask=1):
        "AutoStarter:"

        curdir=self.workingDirPath.get() # N3P

        if string.find(curdir, 'tmp_mnt')>=0:
            curdir=curdir[8:]
        if self.vf.hasGui:
            self.qT=self.queueType.get()
            self.Host=self.hostName.get()
            self.nqeJobFile=self.jobFile.get()
            self.pF=self.paramFile.get()
        if self.qT=='int':
            if os.name == 'nt': #sys.platform=='win32':
                #need to remove the & and flip the backslashes...
                # #cmd=string.replace(cmd,'/','\\')  # N3P use os.path.normpath!
                cmd = os.path.normpath(cmd)
                afterID = None
                if cmd[-1]=='&':
                    cmd=cmd[:-1]
                cmd = cmd.split(' -p ')
                if len(cmd) > 1:
                    cmd[1] = cmd[1].split('-l')
                    if len(cmd[1]) > 1:
                        cmd[1][0] = cmd[1][0].strip()
#                        if cmd[1][0]:
#                            cmd[1][0] = "\""+cmd[1][0]+"\""    
                        cmd[1][1] = cmd[1][1].strip()
                        if cmd[1][1] and self.vf.hasGui:
                            afterID = self.vf.GUI.ROOT.after(500, self.saveLog, cmd[1][1])
                        cmd[1] = cmd[1][0]# + ' -l ' + cmd[1][1]

                    cmd[0] = cmd[0].strip()
                    if not cmd[1]:
                        if self.vf.hasGui:
                            tkinter.messagebox.showerror("Error!","Please specify parameter file.",
                                           parent=self.topLevel)
                        return

                    cmd = [cmd[0], '-p', cmd[1]]

                # execute the command on Windows
                
                # add the cd command to move into the working directory # N3P
                wd = os.path.normpath( self.workingDirPath.get() )
                cmd = ("cd \"%s\" && "+cmd ) % wd

                self.WinCmd = SysCmdInThread(cmd, shell=False)
                self.WinCmd.start()             
            else:


                bin = cmd.split()[0]
                if os.system("which "+bin) != 0:
                    if self.vf.hasGui:
                        tkinter.messagebox.showerror("Error!", bin + " not found. Please include "+bin+" in your path.",
                                           parent=self.topLevel)
                    return
                # execute the command on posix
                # add the cd command to move into the working directory # N3P
                wd = os.path.normpath( self.workingDirPath.get() )
                cmd = ("cd \"%s\";"+cmd ) % wd
                os.system(cmd)
                if ask:
                    self.vf.ADstart_manage.addHost(self.Host)
                    self.vf.ADstart_manage.addProcess(self.programType)
                    self.vf.ADstart_manage.guiCallback()
        elif self.qT=='nqe':
            if self.nqeJobFile == None:
                jobFile = self.makeJobFile(self.pF)
                if self.vf.hasGui:self.jobFile.set(jobFile)
            self.feedback = subprocess.getoutput(cmd)
            if ask and self.vf.hasGui:self.vf.warningMsg(self.feedback)
        elif self.qT=='pbs':
            t='PBS not yet implemented'
            self.vf.warningMsg(t)
            return 'ERROR'
            if self.nqeJobFile == None:
                jobFile = self.makeJobFile(self.pF)
                if self.vf.hasGui:self.jobFile.set(jobFile)
            print('cmd')
            #self.feedback = commands.getoutput(cmd)
            #if ask and self.vf.hasGui:self.vf.warningMsg(self.feedback)
        elif self.qT=='ent' and entropiaPresent:
            print(('calling Entropia launch with ', cmd, self.projectName.get(), \
                'monitor_job=',self.monitorVar.get(),'ftp_back=',self.ftpBackVar.get()))
            try:
                jobid=self.EntropiaUI.launch(cmd,self.projectName.get(),\
                    monitor_job=self.monitorVar.get(),ftp_back=self.ftpBackVar.get())
            except EntropiaError as msg:
                self.vf.warningMsg(msg)
                return 'ERROR'
            if jobid:
                self.jobDir.set(entropia_job_dir+str(jobid))
                msg='Entropia job started as:\n'+str(jobid)
                self.vf.warningMsg(msg)
        else:
            msg ='unknown queuetype', self.qT
            if ask and self.vf.hasGui: 
                self.vf.warningMsg(msg)
            return
        if hasattr(self, 'form') and self.qT!='ent':self.form.root.withdraw()

    def saveLog(self, logPath):
        """Checks the queue for results until we get one"""
        if self.WinCmd.ok.configure()['state'][-1] == 'normal':
            if not hasattr(self.WinCmd,'com'):
                return
            txt =self.WinCmd.stdoutTk.component('text').get(1.0,'end')
            #txt = txt.split('\n')
            ind = txt.find("\n")
            txt = txt[ind+1:] #this should get rid of the first line
            ind = txt.find("Successful Completion")
            if not ind == -1:
                ind1 = txt[:ind].rfind("\n")
                ind2 = ind + txt[ind:].find("\n") + 1
                if txt[ind1-5:ind1] == "____\n":
                    ind1 = txt[:ind1-5].rfind("\n")
                    ind2 = ind2+3 + txt[ind2+2:].find("\n")
                tmp_txt = txt[:ind1]
                tmp_txt += txt[ind2:]
                txt = tmp_txt
            f = open(logPath,'w')
            f.write(txt)
            f.close()
            import winsound
            winsound.MessageBeep()
            return
        self.vf.GUI.ROOT.after(300,self.saveLog, logPath)

    def makeJobFile(self, pFName):
        """AutoStarter:"""
        #NOT FINISHED:
        #MUST PUT COPY OF JOB FILE ON REMOTE MACHINE!?!
        if not pFName: return ''
        if self.qT=='int': 
            return ''
        elif self.qT=='nqe':
            curdir=os.getcwd()
            if string.find(curdir, 'tmp_mnt')>=0:
                curdir=curdir[8:]
            dName = curdir
        elif self.qT == 'pbs':
            t='PBS not yet implemented'
            self.vf.warningMsg(t)
            return
            curdir=os.getcwd()
            dName = self.remoteDir.get()
        else:
            msg = 'unknown queuetype->' + self.qT
            self.vf.warningMsg(msg)
            return
        msg='self.'+self.name+'.makeJobFile(' + pFName+')'
        self.vf.log(msg)
        pName = os.path.split(pFName)[-1]
        pnum=string.rfind(pName, '.')
        pStem =pName[:pnum]
        jobFile = pStem + '.j'
        fptr= open(jobFile, 'w')
        if self.qT=='nqe':
            jobStr='cd '+dName+";"+self.Exe+" -p "+pName+" -l "+self.LogFile+"\n"
            fptr.write(jobStr)
        else:
            outstring = '#PBS -l nodes=' + self.pbsCpu.get()
            fptr.write(outstring)
            outstring = '#PBS -l walltime=' +self.pbsWallTime.get()
            fptr.write(outstring)
            #what is cput???
            outstring = '#PBS -l cput=' +self.pbsTime.get()
            fptr.write(outstring)
            outstring = '#PBS -j oe'
            fptr.write(outstring)
            outstring = 'cd '+dName
            #outstring = 'cd $PBSTMPDIR'
            fptr.write(outstring)
            #outstring = 'dmf get exec/autogrid.'
            #fptr.write(outstring)
            outstring = "./autogrid -p  "+pName+" -l "+self.LogFile+"\n"
            fptr.write(outstring)
            #copy the logfile and MAPS?? back to curdir??
            outstring = "cp "+self.LogFile + ' ' +dName
            fptr.write(outstring)
            outstring = "exit"
            fptr.write(outstring)
        fptr.close()
        os.chmod(jobFile, 0o755)
        return jobFile
        
    def getMacro(self, event=None):
        return self.macroName.get()

    def getHost(self, event=None):
        return self.hostName.get()

    def setHostVal(self, host):
        #this triggers getting the rest of the cmd
        self.hostName.set(host)
        msg= 'self.setHostVal(' + host + ')'
        self.vf.log(msg)
        self.Exe=self.hostDict[host][self.programType]
        self.execPath.set(self.Exe)
        self.queueType.set(self.hostDict[host]['queuetype'])
        self.getCmd()

    def setMacroVal(self, macro):
        #this triggers getting the rest of the cmd
        d=self.hostDict[macro]
        self.hostName.set(d['host'])
        msg= 'self.setMacroVal(' + macro + ')'
        self.vf.log(msg)
        self.Exe=d[self.programType]
        self.execPath.set(self.Exe)
        self.queueType.set(d['queuetype'])
        self.getCmd()

    def getEntropiaUIObject(self):
        if not entropiaPresent: return
        idf = InputFormDescr("Entropia Password")
        idf.append({'widgetType':tkinter.Entry,
                'name': 'password',
                'label': 'Password',
                'wcfg':{ 
                    #'label': 'Password',
                    'show': '*'
                },
                'defaultValue': '',
                'gridcfg':{'sticky':tkinter.E}
              })
        idf_dict = self.vf.getUserInput(idf)
        if idf_dict:
            password = idf_dict['password']
            ##initialize EntropiaUI object
            try:
                self.EntropiaUI=EntropiaUI(password)
                return 1 # true
            except ftplib.error_perm as msg:
                self.vf.warningMsg(msg)
                return None
        else: return None

    def checkPrevious(self):
        if not entropiaPresent: return
        files = {}
        newAdtFile = 0
        ifd=InputFormDescr(title='Process current adt files?')
        ifd.append( {'name': 'thisLab',
            'widgetType': tkinter.Label,
            'text': 'Upload newly created adt files:',
            'gridcfg':{'sticky':tkinter.E}})
        if hasattr(self.vf, 'gpo') and len(self.vf.gpo.gpf_filename):
            newAdtFile = 1
            files['gpf']= self.vf.gpo.gpf_filename
            ifd.append( {'name': 'gpfCBut',
                'widgetType':tkinter.Checkbutton,
                'text':files['gpf'],
                'gridcfg':{'sticky':tkinter.W}})
        if 'outfile' in self.vf.atorsDict:
            newAdtFile = 1
            files['pdbq']=os.path.split(self.vf.atorsDict['outfile'])[-1]
            ifd.append( {'name': 'pdbqCBut',
                'widgetType':tkinter.Checkbutton,
                'text':files['pdbq'],
                'gridcfg':{'sticky':tkinter.W}})
        if hasattr(self.vf,'dpo') and len(self.vf.dpo.dpf_filename):
            newAdtFile = 1
            files['dpf'] = self.vf.dpo.dpf_filename
            ifd.append( {'name': 'dpfCBut',
                'widgetType':tkinter.Checkbutton,
                'text':files['dpf'],
                'gridcfg':{'sticky':tkinter.W}})
        if hasattr(self.vf, 'gpo') and len(self.vf.gpo.receptor_filename):
            newAdtFile = 1
            files['pdbqs'] = self.vf.gpo.receptor_filename
            ifd.append( {'name': 'pdbqsCBut',
                'widgetType':tkinter.Checkbutton,
                'text':files['pdbqs'],
                'gridcfg':{'sticky':tkinter.W}})
        elif hasattr(self.vf,'dpo') and len(self.vf.dpo.receptor_filename):
            newAdtFile = 1
            files['pdbqs'] = self.vf.dpo.receptor_filename
            ifd.append( {'name': 'pdbqsCBut',
                'widgetType':tkinter.Checkbutton,
                'text':files['pdbqs'],
                'gridcfg':{'sticky':tkinter.W}})
        if not newAdtFile: return
        val_dict = self.vf.getUserInput(ifd)
        if val_dict:
            for item in list(val_dict.keys()):
                if val_dict[item]:
                    #upload this file
                    itemName=item[:-4]
                    try:
                        print(('uploading ', files[itemName]))
                        self.EntropiaUI.upload(files[itemName])
                    except EntropiaError as msg:
                        self.vf.warningMsg(msg)
                        return
                    #this gets called with 'gpf' or 'pdbqs' etc
                    print(('uploaded ', files[itemName]))
                    #select it in the listchooser
                    self.updateLCS(itemName)
                    #put it in the entry
                    #FIX ME: I don't know if this is ok or not
                    #because i don't know if self.itemName is a Tkinter var
                    # or not ?????
                    #setattr(self, itemName, files[itemName])
                    exec('self.'+itemName+'.set(files[itemName])')
                    #also highlightit in the listchooser
                    itemWidget=itemName+'Files'
                    lb = self.ifd.entryByName[itemWidget]['widget'].lb
                    for i in range(lb.index('end')):
                        if lb.get(i)==files[itemName]:
                            lb.select_clear('end')
                            lb.select_set(i)
                            lb.see(i)
            #update cmd
            self.getCmd()


    def getMacroVal(self, val, event=None):
        #autostarter
        macroList=list(self.hostDict.keys())
        macro=macroList[val]
        self.macroName.set(macro)
        self.Host = self.hostDict[macro]['host']
        #self.Host=host
        self.hostName.set(self.Host)
        self.Exe=self.hostDict[macro][self.programType]
        self.execPath.set(self.Exe)
        self.qT=self.hostDict[macro]['queuetype']
        self.queueType.set(self.qT)
        if self.qT=='int':
            for item in self.intWids:
                self.ifd.entryByName[item]['widget'].grid(self.ifd.entryByName[item]['gridcfg'])
            for item in self.commonWids:
                self.ifd.entryByName[item]['widget'].grid(self.ifd.entryByName[item]['gridcfg'])
            for item in self.nqeWids:
                self.ifd.entryByName[item]['widget'].grid_forget()
            for item in self.pbsWids:
                self.ifd.entryByName[item]['widget'].grid_forget()
            for item in self.entWids:
                self.ifd.entryByName[item]['widget'].grid_forget()
            for item in self.entWidLCS:
                self.ifd.entryByName[item]['widget'].top.grid_forget()
            for item in self.entButs:
                self.ifd.entryByName[item]['widget'].grid_forget()
        elif self.qT=='nqe':
            for item in self.commonWids:
                self.ifd.entryByName[item]['widget'].grid(self.ifd.entryByName[item]['gridcfg'])
            for item in self.nqeWids:
                self.ifd.entryByName[item]['widget'].grid(self.ifd.entryByName[item]['gridcfg'])
            for item in self.intWids:
                self.ifd.entryByName[item]['widget'].grid_forget()
            for item in self.pbsWids:
                self.ifd.entryByName[item]['widget'].grid_forget()
            for item in self.entWids:
                self.ifd.entryByName[item]['widget'].grid_forget()
            for item in self.entWidLCS:
                self.ifd.entryByName[item]['widget'].top.grid_forget()
            for item in self.entButs:
                self.ifd.entryByName[item]['widget'].grid_forget()
            if os.name == 'nt': #sys.platform=='win32':
                self.niceLevel.set('0')
        elif self.qT=='pbs':
            for item in self.commonWids:
                self.ifd.entryByName[item]['widget'].grid(self.ifd.entryByName[item]['gridcfg'])
            for item in self.pbsWids:
                self.ifd.entryByName[item]['widget'].grid(self.ifd.entryByName[item]['gridcfg'])
            for item in self.intWids:
                self.ifd.entryByName[item]['widget'].grid_forget()
            for item in self.nqeWids:
                self.ifd.entryByName[item]['widget'].grid_forget()
            for item in self.entWids:
                self.ifd.entryByName[item]['widget'].grid_forget()
            for item in self.entWidLCS:
                self.ifd.entryByName[item]['widget'].top.grid_forget()
            for item in self.entButs:
                self.ifd.entryByName[item]['widget'].grid_forget()
            if os.name == 'nt': #sys.platform=='win32':
                self.niceLevel.set('0')
        elif self.qT=='ent' and entropiaPresent:
            if not hasattr(self, 'EntropiaUI'):
                if not self.getEntropiaUIObject(): return

            if self==self.vf.ADstart_autogrid:
                msg='AutoGrid Jobs not defined separately for Entropia system'
                self.vf.warningMsg(msg)
                self.getMacroVal(0)
                return
            for item in self.entWids:
                self.ifd.entryByName[item]['widget'].grid(self.ifd.entryByName[item]['gridcfg'])
            for item in self.entWidLCS:
                self.ifd.entryByName[item]['widget'].top.grid(self.ifd.entryByName[item]['gridcfg'])
            for item in self.entButs:
                self.ifd.entryByName[item]['widget'].grid(self.ifd.entryByName[item]['gridcfg'])
            for item in self.commonWids:
                self.ifd.entryByName[item]['widget'].grid_forget()
            for item in self.intWids:
                self.ifd.entryByName[item]['widget'].grid_forget()
            for item in self.flagWids:
                self.ifd.entryByName[item]['widget'].grid_forget()
            for item in self.nqeWids:
                self.ifd.entryByName[item]['widget'].grid_forget()
            for item in self.pbsWids:
                self.ifd.entryByName[item]['widget'].grid_forget()
            if os.name == 'nt': #sys.platform=='win32':
                self.niceLevel.set('0')
            # call local updateListChooser with new file_lists
            for item in ['gpf_list','dpf_list','pdbq_list','pdbqs_list']:
                #exec('self.'+item+'=self.EntropiaUI.'+item)
                #these items are not Tkinter vars, so this is ok
                setattr(self, item, getattr(self.EntropiaUI, item))
            for item in ['gpf','pdbqs','dpf','pdbq']:
                self.updateLCS(item)
            #CHECK here for previous work done in adt:
            self.checkPrevious()
        else:
            t='Unknown queueType: '+self.qT
            self.vf.warningMsg(t)
            return
        self.getCmd()

    def getProjectVal(self, val, event=None):
        if not entropiaPresent: return
        try:
            projectList=self.EntropiaUI.project_list
        except AttributeError:
            return
        project=projectList[val]
        self.projectName.set(project)

    def getHostVal(self, val, event=None):
        #autostarter
        hostList=list(self.hostDict.keys())
        host=hostList[val]
        self.Host=host
        self.hostName.set(host)
        self.Exe=self.hostDict[host][self.programType]
        self.execPath.set(self.Exe)
        self.qT=self.hostDict[host]['queuetype']
        self.queueType.set(self.qT)
        if self.queueType.get()=='int':
            self.ifd.entryByName['niceLab']['widget'].grid(self.ifd.entryByName['niceLab']['gridcfg'])
            self.ifd.entryByName['niceEntry']['widget'].grid(self.ifd.entryByName['niceEntry']['gridcfg'])
            self.ifd.entryByName['nqeTimeLab']['widget'].grid_forget()
            self.ifd.entryByName['nqeTimeEntry']['widget'].grid_forget()
            self.ifd.entryByName['pbsDirLab']['widget'].grid_forget()
            self.ifd.entryByName['pbsDirEntry']['widget'].grid_forget()
            self.ifd.entryByName['nqeCpuLab']['widget'].grid_forget()
            self.ifd.entryByName['nqeCpuEntry']['widget'].grid_forget()
            self.ifd.entryByName['niceLab']['widget'].grid(self.ifd.entryByName['niceLab']['gridcfg'])
            self.ifd.entryByName['niceEntry']['widget'].grid(self.ifd.entryByName['niceEntry']['gridcfg'])
        else:
            self.ifd.entryByName['nqeTimeLab']['widget'].grid(self.ifd.entryByName['nqeTimeLab']['gridcfg'])
            self.ifd.entryByName['nqeTimeEntry']['widget'].grid(self.ifd.entryByName['nqeTimeEntry']['gridcfg'])
            self.ifd.entryByName['pbsDirLab']['widget'].grid(self.ifd.entryByName['pbsDirLab']['gridcfg'])
            self.ifd.entryByName['pbsDirEntry']['widget'].grid(self.ifd.entryByName['pbsDirEntry']['gridcfg'])
            self.ifd.entryByName['nqeCpuLab']['widget'].grid(self.ifd.entryByName['nqeCpuLab']['gridcfg'])
            self.ifd.entryByName['nqeCpuEntry']['widget'].grid(self.ifd.entryByName['nqeCpuEntry']['gridcfg'])
            self.ifd.entryByName['niceLab']['widget'].grid_forget()
            self.ifd.entryByName['niceEntry']['widget'].grid_forget()
            if os.name == 'nt': #sys.platform=='win32':
                self.ifd.entryByName['niceLab']['widget'].grid_forget()
                self.ifd.entryByName['niceEntry']['widget'].grid_forget()
                self.niceLevel.set('0')
        self.getCmd()

    def setParmFileVal(self,  pF):
        self.ParmFile=pF
        self.paramFile.set(pF)
        ##llist = string.split(pF,'.')    
        lnum=string.rfind(pF, '.')
        llist=pF[:lnum]
        self.logFile.set(llist+'.'+self.logType)
        self.LogFile=llist+'.'+self.logType
        msg= 'self.setParmFileVal(' + pF + ')'
        self.vf.log(msg)
        host = self.hostName.get()
        self.Exe=self.hostDict[host][self.programType]
        self.execPath.set(self.Exe)
        self.queueType.set(self.hostDict[host]['queuetype'])
        self.getCmd()

    def buildMacroMenu(self, event=None):
        macroMb=self.ifd.entryByName['mNMenu']['widget']
        macroMb.config(text='macros')
        if not self.showMacroMenu.get():
            #hostList is ['noah','saul','job']
            macroList = list(self.hostDict.keys())
            self.buildMenu(macroList,macroMb,self.macroVal, self.getMacroVal)
            self.showHostMenu.set(1)
        else:
            hostMenubutton.menu.unpost()
            self.showHostMenu.set(0)
        

    def buildHostMenu(self, event=None):
        hostMb=self.ifd.entryByName['hNMenu']['widget']
        hostMb.config(text='hosts')
        if not self.showHostMenu.get():
            #hostList is ['noah','saul','job']
            hostList = list(self.hostDict.keys())
            self.buildMenu(hostList,hostMb,self.hostVal, self.getHostVal)
            self.showHostMenu.set(1)
        else:
            hostMenubutton.menu.unpost()
            self.showHostMenu.set(0)
        
    def updateProjectMenu(self, event=None):
        if not entropiaPresent: return
        projectMb=self.ifd.entryByName['pjMenu']['widget']
        projectMb.config(text='projects')
        try:
            projectList = self.EntropiaUI.project_list
        except AttributeError: 
            projectList=[]
        self.buildMenu(projectList,projectMb,self.projectVal, self.getProjectVal)

    def buildProjectMenu(self, event=None):
        if not entropiaPresent: return
        projectMb=self.ifd.entryByName['pjMenu']['widget']
        projectMb.config(text='projects')
        if not self.showProjectMenu.get():
            try:
                projectList = self.EntropiaUI.project_list
                print(("projectList=", projectList))
            except AttributeError: 
                projectList=[]
            self.buildMenu(projectList,projectMb,self.projectVal, self.getProjectVal)
            self.showProjectMenu.set(1)
        else:
            projectMb.menu.unpost()
            self.showProjectMenu.set(0)
        
    def buildMenu(self,keyList,mB, var, cmd):
        #start from scratch and build menu
        mB.config(bg='white')
        if not hasattr(mB, 'menu'):
            mB.menu=tkinter.Menu(mB)
            mB['menu']=mB.menu
        else:
            mB.menu.delete(1, 'end')
        #raise runTimeError('check this')
        #Pack all the entries:
        for i in range(len(keyList)):
            mB.menu.add_radiobutton(label=keyList[i],
            var=var,value=i,command=CallBackFunction(cmd,i))

    def getCmd(self, event=None):
        "AutoStart:"
        host = self.hostName.get()
        exe = self.execPath.get()
        cmd = self.cmd
        pFile = self.paramFile.get()
        logName = self.logFile.get()
        curdir = self.workingDirPath.get()
        remotedir = self.remoteDir.get()
        niceStr=' '
        if self.niceLevel.get()=='':
            self.niceLevel.set('0')
        if self.niceLevel.get()!='0':
            niceStr = 'nice +'+self.niceLevel.get()+ ' '
        if string.find(curdir, 'tmp_mnt')>=0:
            curdir=curdir[8:]
        jobFile = self.jobFile.get()
        qT=self.queueType.get()
        if jobFile=='' and pFile and (qT=='nqe' or qT=='pbs'):
            self.jobFile.set(self.makeJobFile(pFile))
            jobFile = self.jobFile.get()
        if qT=='int':
            if host==self.localHost:
                cmd_string = (exe + ' -p ' + pFile + ' -l ' + logName + '&') 
                #cmd.set(("%s" + exe + ' -p ' + pFile + ' -l ' + logName + '&' % change_to_dir)) # 
                cmd.set(cmd_string)
            else:
                cmdStr="rsh "+host+" -n "+"\'cd "+curdir+";"+ niceStr + exe+" -p "+pFile+" -l "+logName+"&\'&"
                cmd.set(cmdStr)
        elif qT=='nqe':
            cmdStr = "rsh "+host+" -n \'cd "+curdir+";/nqe/bin/cqsub -lT "+self.nqeTime.get()+ " -la ncpu="+ self.nqeCpu.get()+" "+jobFile+"\'"
            cmd.set(cmdStr)
        elif qT=='win':
            print('in case queueType==win')
            cmdStr = "rsh "+host+" -n \'cd "+curdir+";/nqe/bin/cqsub -lT "+self.nqeTime.get()+ " -la ncpu="+ self.nqeCpu.get()+" "+jobFile+"\'"
            cmd.set(cmdStr)
        elif qT=='pbs':
            if remotedir=='':
                msg = 'No REMOTE DIRECTORY specified!'
                self.vf.warningMsg(msg)
                return
            cmdStr = "ssh "+host+"-n \'cd "+remotedir+";qsub -l cput="+self.pbsCpuTime.get()+"-l nodes="+self.pbsCpu.get()+ " -l walltime="+ self.pbsWallTime.get()+"-r  "+self.pbsRerun.get()+' ' + jobFile+"\'"
            cmd.set(cmdStr)
        elif qT=='ent':
            msg='AutoGrid Jobs not defined separately for Entropia system'
            self.vf.warningMsg(msg)
            self.getMacroVal(0)
            return
        else:
            msg = 'Unknown queueType->'+ qT
            self.vf.warningMsg(msg)
            return
        

    def updateLF(self, event=None):
        #llist = string.split(self.paramFile.get(),'.')    
        #self.logFile.set(llist[0]+'.'+self.logType)
        #self.LogFile=llist[0]+'.'+self.logType
        pF=self.paramFile.get()
        lnum=string.rfind(pF, '.')
        llist=pF[:lnum]
        self.logFile.set(llist+'.'+self.logType)
        self.LogFile=llist+'.'+self.logType
        #at this moment, make a jobFile if you can
        self.jobFile.set(self.makeJobFile(self.paramFile.get()))
        #self.getCmd()

    def browsePF(self, event=None):
        pf = self.vf.askFileOpen(parent = self.topLevel,
                                 types=[('select '+self.browserPFTitle,'*.'+self.pfType)], title= self.program +' Parameter File:')
        if pf: 
            #don't strip off the pathname??
            pfList=os.path.split(pf)
            if pfList[0]==os.getcwd():
                pfname = os.path.split(pf)[-1]
            else:
                pfname=pf
            self.paramFile.set(pfname)
            self.ParmFile=pfname
            self.updateLF()
            self.getCmd()
        if hasattr(self, 'topLevel'):self.topLevel.lift()

    def browseEX(self, event=None):
        ef = self.vf.askFileOpen(parent = self.topLevel,
                                 types=[('select program:','*')], title= self.program)
        if ef: 
            #don't strip off the pathname??
            efList=os.path.split(ef)
            if efList[0]==os.getcwd():
                efname = os.path.split(ef)[-1]
            else:
                efname=ef
            self.execPath.set(efname)
            self.Exe=efname
            self.getCmd()
        if hasattr(self, 'topLevel'):self.topLevel.lift()

    def browseLF(self, event=None):
        lf = self.vf.askFileOpen(parent = self.topLevel,
                                 types=[('select :','*.'+self.logType)], title= self.program+ ' log File:')
        if lf: 
            #strip off the pathname??
            lfList=os.path.split(lf)
            if lfList[0]==os.getcwd():
                lfname = os.path.split(lf)[-1]
            else:
                lfname=lf
            self.logFile.set(lfname)
            self.getCmd()
        if hasattr(self, 'topLevel'):self.topLevel.lift()

    def browseWD(self, event=None):
        wd = tkinter.filedialog.askdirectory(parent = self.topLevel, title= self.program) # N3P
        if wd: 
            self.workingDirPath.set(wd)
            """
            efList=os.path.split(ef)
            if efList[0]==os.getcwd():
                efname = os.path.split(ef)[-1]
            else:
                efname=ef
            self.execPath.set(efname)
            self.Exe=efname
            """
            self.getCmd()
        if hasattr(self, 'topLevel'):self.topLevel.lift()



    def setNiceLevel(self,val,event=None):
        self.niceLevel.set(str(val))
        self.getCmd()

    def setNqeTime(self,val,event=None):
        self.nqeTime.set(str(val))
        self.getCmd()

    def setNqeCpu(self,val,event=None):
        self.nqeCpu.set(str(val))
        self.getCmd()

    def setHost(self, hostStr):
        self.Host=hostStr
    
    def setExe(self, exeStr):
        self.Exe=exeStr
    
    def setFlagStr(self, flagStr):
        self.FlagStr=flagStr
    
    def setParmFile(self, parmStr):
        self.ParmFile=parmStr
    
    def setLogFile(self, logStr):
        self.LogFile=logStr

#    
#    def setWorkingDir(self, workDir): N3P remove
#        self.workingDir = workDir
#


    def setCommand(self):
        self.command=self.Exe + " " + self.FlagStr+ " " + self.ParmFile+ " " + self.LogFile

    def doIntRemoteCommand(self,pFile,host=None,nice=20,flagStr=' ',log=None):
        if not host: host=self.localHost
        self.qT= self.hostDict[host]['queuetype']
        if self.qT!='int':
            t=host + ' is nqe queueType; use doNqeRemoteCommand instead'
            self.vf.warningMsg(t)
            return
        exe= self.hostDict[host][self.programType]
        curdir=os.getcwd()
        if string.find(curdir, 'tmp_mnt')>=0:
            curdir=curdir[8:]
        if not log: 
            #pFileStem=string.split(pFile,'.')[0]
            lnum=string.rfind(pFile, '.')
            pFileStem=pFile[:lnum]
            log = pFileStem  +"."+self.logType
        self.RemoteCommand= "rsh "+host+" -n "+"\'cd "+curdir+";nice +" + str(nice)+" "+exe+' '+flagStr+" -p "+pFile+" -l "+log+"&\'&"
        self.doitWrapper(self.RemoteCommand,0,log=1,redraw=0)

    def doNqeRemoteCommand(self,pFile,host=None,nqeTime=144000,ncpu=1,flagStr=' ',log=None):
        if not host: host=self.localHost
        self.qT= self.hostDict[host]['queuetype']
        if self.qT!='nqe':
            t=host + ' is int queueType; use doIntRemoteCommand instead'
            self.vf.warningMsg(t)
            return
        exe= self.hostDict[host][self.programType]
        curdir=os.getcwd()
        if string.find(curdir, 'tmp_mnt')>=0:
            curdir=curdir[8:]
        lnum=string.rfind(pFile, '.')
        pFileStem=pFile[:lnum]
        if not log: 
            log = pFileStem  +"."+self.logType
        cmdStr= "cd "+curdir+";"+exe+' ' +flagStr+" -p "+pFile+" -l "+log
        jobFileName=pFileStem+'.j'
        self.makeJF(jobFileName,cmdStr)
        self.RemoteCommand= "rsh " +host+ " -n " +  "\'cd " +curdir+";/nqe/bin/cqsub -lT "+str(nqeTime)+ " -la ncpu="+str(ncpu)+" "+jobFileName + "\'"
        self.doitWrapper(self.RemoteCommand,0,log=1,redraw=0)

    def makeJF(self,jobFile,jobStr):
        fptr= open(jobFile, 'w')
        fptr.write(jobStr)
        fptr.close()
        os.chmod(jobFile, 0o755)
        self.nqeJobFile=jobFile
        
    def setNqeRemoteCommand(self,host,nice,exe,flagStr,pFile,log,nqeTime,ncpu):
        curdir=os.getcwd()
        if string.find(curdir, 'tmp_mnt')>=0:
            curdir=curdir[8:]
        if self.Host==None:self.Host=host
        lnum=string.rfind(pFile, '.')
        pFileStem=pFile[:lnum]
        #pFileStem=string.split(pFile,'.')[0]
        jName=pFileStem+'.j'
        self.nqeJobFile=jName
        self.makeJF(jName,self.setIntRemoteCommand(self,host,curdir,nice,exe,flagStr,pFile,log))
        return "rsh " +host+ " -n " +  "\'cd " +curdir+";/nqe/bin/cqsub -lT "+nqeTime+ " -la ncpu="+ncpu+" "+job + "\'"



class AutoGridStarter(AutoStarter):
    """Interactive usage: 
            The user chooses host and parameter file and starts the Autogrid job. 
            If the host has an interactive queue, launching the job opens 
            a 'ADstart_manage' widget which allows the user to follow the job 
            and to kill it, if necesary. A 'job file' is written when a parameter 
            file is selected in combination with the selection of a 'nqe'-type host.
        Scripting usage:
            'doIntRemoteCommand' and 'doNqeRemoteCommand' methods allow starting 
            AutoGrid with the specified parameter file on a host with
            a appropriate queue type. (if not specified, host is assumed
            to be the local host and must be of appropriate queue type).
            All other parameters are optional"""

    def __init__(self): 
        AutoStarter.__init__(self,program='autogrid4',
            dictObj='gpo',
            ifdTitle="Run AutoGrid",
            browserPFTitle="Grid Parameter File",
            browserEXETitle='autogrid4',
            browserLOGTitle="Grid Log",
            logType='glg',
            pfType='gpf',
            programType='autogrid')


AutoGridStarterGUI=CommandGUI()
AutoGridStarterGUI.addMenuCommand('AutoToolsBar', menuText['StartMB'], menuText['startGridMB'])



class AutoDockStarter(AutoStarter):
    """Interactive usage: 
            The user chooses host and parameter file and starts the Autodock job. 
            If the host has an interactive queue, launching the job opens 
            a 'ADstart_manage' widget which allows the user to follow the job 
            and to kill it, if necesary. A 'job file' is written when a parameter 
            file is selected in combination with the selection of a 'nqe'-type host.
        Scripting usage:
            'doIntRemoteCommand' and 'doNqeRemoteCommand' methods allow starting 
            Autodock with the specified parameter file on a host with
            a appropriate queue type. (if not specified, host is assumed
            to be the local host and must be of appropriate queue type).
            All other parameters are optional"""

    def __init__(self): 
        AutoStarter.__init__(self,program='autodock4',
            dictObj='dpo',
            ifdTitle="Run AutoDock",
            browserPFTitle="Dock Parameter File",
            browserEXETitle='autodock4',
            browserLOGTitle="Dock Log",
            logType='dlg',
            pfType='dpf',
            programType='autodock')

    def guiCallback(self, event=None):
        #AutoDock
        self.customizeGUI()
        if not hasattr(self, 'form'):
            if self.vf.hasGui:    
                #self.form = self.vf.getUserInput(self.ifd,scrolledFrame=1,width=1000,height=350, modal=0, blocking=0)
                self.form = self.vf.getUserInput(self.ifd,modal=0, blocking=0)
                self.form.root.protocol('WM_DELETE_WINDOW',self.Close_cb)
                self.topLevel = self.form.root
            else:
                ##  from ViewerFramework.gui import InputForm
                from mglutil.gui.InputForm.Tk.gui import InputForm
                self.form = InputForm(self.vf.master,self.ifd,modal=0, blocking=0)
                self.topLevel = self.form.root
            if hasattr(self.vf, 'dpo') and len(self.vf.dpo.dpf_filename):
                if self.paramFile.get()=='':
                    self.paramFile.set(self.vf.dpo.dpf_filename)
                    self.updateLF()
            #self.bindEntries()
            self.flagVar.set(0)
            self.kflag.set(0)
            self.iflag.set(0)
            self.uflag.set(0)
            self.tflag.set(0)
            self.cflag.set(0)
            self.inputFile.set("")
            self.outputFile.set("")
            self.intWids=['niceLab','niceEntry']
            if os.name == 'nt': #sys.platform=='win32':
                self.ifd.entryByName['niceLab']['widget'].grid_forget()
                self.ifd.entryByName['niceEntry']['widget'].grid_forget()
            self.commonWids=['hNLab','hNentry','eXLab','eXentry','eXbutton',
                'pFLab','pFentry','pFbutton',
                'lFLab','lFentry','lFbutton']
            self.nqeWids=['nqeCpuLab','nqeCpuEntry','nqeTimeLab','nqeTimeEntry']
            self.pbsWids=['pbsCpuLab','pbsCpuEntry','pbsDirLab','pbsDirEntry','pbsTimeLab','pbsTimeEntry','pbsWallTimeLab','pbsWallTimeEntry','pbsRerunCB']
                
            self.entWids=['pjLab','pjentry','pjMenu','nodesEntLab','nodesEnt',
                'gpfEntLab', 'gpfEnt','pdbqEntLab','pdbqEnt',
                'dpfEntLab','dpfEnt', 'pdbqsEntLab','pdbqsEnt',
                'jobDirEntLab','jobDirEnt', 'gpfFilterEnt', 'pdbqFilterEnt',
                'dpfFilterEnt','pdbqsFilterEnt']
            self.entWidLCS=['gpfFiles','pdbqFiles','dpfFiles','pdbqsFiles']
            self.entButs=[ 'uploadGpfFileBut','uploadPdbqFileBut',
                'uploadDpfFileBut','uploadPdbqsFileBut', 'monitorCB',
                'ftpBackCB']
            self.bindEntries()
            self.getMacroVal(0)
        self.updateFlags()
        self.getInputs()
        self.form.autoSize()

    def setFile(self, item, event=None):
        lb=self.ifd.entryByName[item]['widget'].lb
        if lb.curselection()==(): return
        newsel=lb.get(lb.curselection())
        #FIX ME, i think this is ok, but i'm not sure
        #exec('self.'+item[:-5]+'.set(newsel)')
        setattr(self, item[:-5], newsel)
        self.getCmd()
        
        
    def bindEntries(self):
        if hasattr(self,'form'):
            self.ifd.entryByName['cmdentry']['widget'].bind('<Return>', self.getCmdParams)
            self.ifd.entryByName['mNentry']['widget'].bind('<Key>', self.getMacro)
            self.ifd.entryByName['mNMenu']['widget'].bind('<ButtonPress>', self.buildMacroMenu, add='+')
            self.ifd.entryByName['pjMenu']['widget'].bind('<ButtonPress>', self.buildProjectMenu, add='+')
            self.ifd.entryByName['pFentry']['widget'].bind('<Return>', self.updateLF)
            if entropiaPresent:
                entList=['lFentry','eXentry','inentry','outentry','niceEntry','nqeTimeEntry','nqeCpuEntry','nodesEnt','gpfEnt','dpfEnt','pdbqEnt','pdbqsEnt']
            else:
                entList=['lFentry','eXentry','inentry','outentry','niceEntry','nqeTimeEntry','nqeCpuEntry']
            for item in entList:
                self.ifd.entryByName[item]['widget'].bind('<Return>', self.getCmd)
            if entropiaPresent:
                filList=['gpf','pdbqs','dpf','pdbq']
                for item in filList:
                    n=item+'FilterEnt'
                    self.ifd.entryByName[n]['widget'].bind('<Return>', CallBackFunction(self.updateLCS,item), '+')

    def getCmdParams(self, event=None):
        print("in getCmdParms")
        if not entropiaPresent: return
        if self.queueType.get()=='ent':
            cmdList=string.split(self.cmd.get(), ';')
            self.nodes.set(cmdList[1])
            gpfFile=cmdList[2]
            if gpfFile in self.EntropiaUI.gpf_list:
                self.gpf.set(gpfFile)
            pdbqFile=cmdList[3]
            if pdbqFile in self.EntropiaUI.pdbq_list:
                self.pdbq.set(pdbqFile)
            dpfFile=cmdList[4]
            if dpfFile in self.EntropiaUI.pdbq_list:
                self.dpf.set(dpfFile)
            pdbqsFile=cmdList[5]
            if pdbqsFile in self.EntropiaUI.pdbqs_list:
                self.pdbqs.set(pdbqsFile)
        elif self.queueType.get()=='int' and self.hostName.get()==self.localHost:
            #in this case can set execPath,
            cmdList=string.split(self.cmd.get())
            self.execPath.set(cmdList[0])
            self.Exe=cmdList[0]
            self.paramFile.set(cmdList[2])
            self.ParmFile=cmdList[2]
            self.logFile.set(cmdList[4])
            self.LogFile=cmdList[4]

    def setUpFlagVars(self):
        self.flagVar = tkinter.IntVar(master=self.vf.GUI.ROOT)
        self.flagVar.set(0)
        self.kflag = tkinter.IntVar(master=self.vf.GUI.ROOT)
        self.iflag = tkinter.IntVar(master=self.vf.GUI.ROOT)
        self.uflag = tkinter.IntVar(master=self.vf.GUI.ROOT)
        self.tflag = tkinter.IntVar(master=self.vf.GUI.ROOT)
        self.cflag = tkinter.IntVar(master=self.vf.GUI.ROOT)
        self.inputFile = tkinter.StringVar(master=self.vf.GUI.ROOT)
        self.outputFile = tkinter.StringVar(master=self.vf.GUI.ROOT)

    def getFlags(self):
        self.ifd.append({'name': 'flagChoiceLab',
            'widgetType': tkinter.Label,
            'text':'Add Optional Flags?',
            'gridcfg':{'sticky':tkinter.E }})
        self.ifd.append({'name': 'flagYes',
            'widgetType':tkinter.Radiobutton,
            'wcfg': {'value':'1'},
            'variable': self.flagVar,
            'command': self.getCmd,
            'text':'Yes',
            'gridcfg':{'sticky':tkinter.E, 'row':-1,'column':1},
            'command': self.updateFlags })
        self.ifd.append({'name': 'flagNo',
            'widgetType':tkinter.Radiobutton,
            'wcfg': {'value':'0'},
            'variable': self.flagVar,
            'command': self.getCmd,
            'text':'No',
            'gridcfg':{'sticky':tkinter.W, 'row':-1,'column':2},
            'command': self.updateFlags })
        self.ifd.append({'name': 'kflag',
            'widgetType':tkinter.Checkbutton,
            'text':'Don\'t keep original residue numbers (-k)',
            'command': self.getCmd,
            'variable':self.kflag,
            'gridcfg':{'sticky':tkinter.W, 'column':1, 'columnspan':2}})
        self.ifd.append({'name': 'iflag',
            'widgetType':tkinter.Checkbutton,
            'text':'Ignore grid map header errors (-i)',
            'variable':self.iflag,
            'command': self.getCmd,
            'gridcfg':{'sticky':tkinter.W, 'column':1, 'columnspan':2}})
        self.ifd.append({'name': 'uflag',
            'widgetType':tkinter.Checkbutton,
            'text':'Return message describing cmd line usage (-u)',
            'variable':self.uflag,
            'command': self.getCmd,
            'gridcfg':{'sticky':tkinter.W, 'column':1, 'columnspan':2}})
        self.ifd.append({'name': 'tflag',
            'widgetType':tkinter.Checkbutton,
            'text':'Parse PDBQ to check torsion dfns + stop (-t)',
            'variable':self.tflag,
            'command': self.getCmd,
            'gridcfg':{'sticky':tkinter.W, 'column':1, 'columnspan':2}})
        self.ifd.append({'name': 'cflag',
            'widgetType':tkinter.Checkbutton,
            'text':'Run autodock in command mode (-c)',
            'variable':self.cflag,
            'command': self.getInputs,
            'gridcfg':{'sticky':tkinter.W, 'column':1, 'columnspan':2}})
        self.ifd.append( {'name': 'inentLab',
            'widgetType': tkinter.Label,
            'text':'Take input from:',
            'gridcfg':{'sticky':tkinter.E}})
        self.ifd.append( {'name': 'inentry',
            'widgetType':tkinter.Entry,
            'wcfg':{
                'textvariable': self.inputFile,
            },
            'gridcfg':{'sticky':tkinter.E,'row':-1,'column':1}})
        self.ifd.append( {'name': 'outentLab',
            'widgetType': tkinter.Label,
            'text':'Redirect output to:',
            'gridcfg':{'sticky':tkinter.E}})
        self.ifd.append( {'name': 'outentry',
            'widgetType':tkinter.Entry,
            'wcfg':{
                'textvariable': self.outputFile,
            },
            'gridcfg':{'sticky':tkinter.E,'row':-1,'column':1}})
        self.flagWids=['flagChoiceLab','flagYes','flagNo',
                        'kflag','iflag','uflag',
                        'tflag','cflag','inentLab',
                        'inentry','outentLab','outentry']


    def callDoit_cb(self, event = None):
        cmdStr=self.cmd.get()
        if self.queueType.get()=='int':
            if string.find(cmdStr,'dpf')<0:
                msgStr="Must Specify a docking parameter file (.dpf)!"
                self.vf.warningMsg(msgStr)    
                return
            if string.find(cmdStr,'dlg')<0:
                msgStr="Must Specify a docking log file (.dlg)!"
                self.vf.warningMsg(msgStr)    
                return
        self.doitWrapper(self.cmd.get(),log=1,redraw=0)


    def updateFlags(self, event=None):
        wlist = []
        wlist2 = []
        for item in ['kflag','iflag','uflag','tflag','cflag']:
            wlist.append(self.ifd.entryByName[item])
        for item in ['inentLab','inentry','outentLab','outentry']:
            wlist2.append(self.ifd.entryByName[item])
        if not self.flagVar.get():
            for item in wlist:
                item['widget'].grid_forget()
            for item in wlist2:
                item['widget'].grid_forget()
        else:
            for item in wlist:
                item['widget'].grid(item['gridcfg'])
            #call getInputs to pack or not pack wlist2 items according to cflag
            self.getInputs()
        self.getCmd()

    def getInputs(self, event=None):
        wlist=[]
        for item in ['inentLab','inentry','outentLab','outentry']:
            wlist.append(self.ifd.entryByName[item])
        if not self.cflag.get():
            for item in wlist:
                item['widget'].grid_forget()
        else:
            for item in wlist:
                item['widget'].grid(item['gridcfg'])
        self.getCmd()

    def getCmd(self, event=None):
        #AutoDock:
        if self.workingDirPath.get() == None:
            curdir = os.getcwd()
        else:
            curdir = self.workingDirPath.get()

        if string.find(curdir, 'tmp_mnt')>=0:
            curdir=curdir[8:]
        remotedir= self.remoteDir.get()
        host = self.hostName.get()
        pFile = self.paramFile.get()
        logName = self.logFile.get()
        exe = self.execPath.get()
        job = self.jobFile.get()
        cmd = self.cmd
        niceStr=''
        if self.niceLevel.get()=='':
            self.niceLevel.set('0')
        if self.niceLevel.get()!='0':
            niceStr = 'nice +'+self.niceLevel.get() + " "
        qT = self.queueType.get()
        if job=='' and pFile and (qT=='nqe' or qT=='pbs'):
            self.jobFile.set(self.makeJobFile(pFile))
            job= self.jobFile.get()
        flagStr=' '
        if self.flagVar.get(): 
            if self.kflag.get():
                flagStr= flagStr + ' -k'
            if self.iflag.get():
                flagStr= flagStr + ' -i'
            if self.uflag.get():
                flagStr= flagStr + ' -u'
            if self.tflag.get():
                flagStr= flagStr + ' -t'
        cStr=' '
        if self.cflag.get():
            cStr= cStr + ' -c'
            if self.inputFile.get()!='':
                cStr= cStr + ' < '+ self.inputFile.get()
            if self.outputFile.get()!='':
                cStr= cStr + ' > '+ self.outputFile.get()
        else:
            cStr = '&'

        qT=self.queueType.get()
        if qT =='int':
            if host==self.localHost:
                cmdStr=exe+flagStr+' -p '+pFile+' -l '+logName+'&'
            else:
                cmdStr="rsh "+host+" -n "+"\'cd "+curdir+";"+niceStr + exe + flagStr+" -p "+pFile+" -l "+logName+"&\'&"
        elif qT=='nqe':
            cmdStr="rsh " +host+ " -n " +  "\'cd " +curdir+";/nqe/bin/cqsub -lT "+self.nqeTime.get()+ " -la ncpu="+self.nqeCpu.get()+" "+job + "\'"
        elif qT=='pbs':
            msg = 'PBS queuetype not yet implemented'
            self.vf.warningMsg(msg)
            return
            if remotedir=='':
                msg = 'No REMOTE DIRECTORY specified!'
                self.vf.warningMsg(msg)
                return
            cmdStr="rsh " +host+ " -n " +  "\'cd " +remotedir+";/pbs/bin/qsub -l walltime= "+self.nqeTime.get()+ " -l nodes="+self.nqeCpu.get()+" "+job + "\'"
        elif qT=='ent':
            cmdStr='params=startjob;'+self.nodes.get()+';'+self.gpf.get()+';'+self.pdbqs.get()+';'+self.dpf.get()+';'+self.pdbq.get()
        else:
            msg='unknown queuetype-> ' + qT
            self.vf.warningMsg(msg)
            return
        self.cmd.set(cmdStr)
        self.command=cmdStr
        ###self.makeJobFile(pFile)
        if hasattr(self, 'topLevel'):self.topLevel.lift()

    def makeJobFile(self, pFName):
        """AutoDock:"""
        if not pFName: return ''
        #NOT FINISHED:
        #MUST PUT COPY OF JOB FILE ON REMOTE MACHINE!!
        if self.qT=='int': 
            return ''
        elif self.qT=='nqe':
            curdir= os.getcwd()
            if string.find(curdir, 'tmp_mnt')>=0:
                curdir=curdir[8:]
            dName = curdir
        elif self.qT=='pbs':
            dName = self.remoteDir.get()
        msg='self.ADstart_autodock.makeJobFile(' + pFName+')'
        self.vf.log(msg)
        pName = os.path.split(pFName)[-1]
        #pStem = string.split(pFName, '.')[0]
        pnum=string.rfind(pName, '.')
        pStem =pName[:pnum]
        host = self.Host
        exe = self.execPath.get()
        flagStr=' '
        if self.flagVar.get(): 
            if self.kflag.get():
                flagStr= flagStr + ' -k '
            if self.iflag.get():
                flagStr= flagStr + ' -i '
            if self.uflag.get():
                flagStr= flagStr + ' -u '
            if self.tflag.get():
                flagStr= flagStr + ' -t '
        cmd = self.cmd
        logName = self.logFile.get()
        jobFile = pStem + '.j'
        fptr= open(jobFile, 'w')
        jobStr='cd '+dName+";"+exe+" "+ flagStr +" -p "+pName+" -l "+logName+"\n"
        fptr.write(jobStr)
        fptr.close()
        os.chmod(jobFile, 0o755)
        return jobFile

AutoDockStarterGUI=CommandGUI()
AutoDockStarterGUI.addMenuCommand('AutoToolsBar', menuText['StartMB'], menuText['startDockMB'])



class AddAutoDockHost(MVCommand):
    """ this class allows user to add entries to hosts dictionary 
        and write them to a file"""
        
    def guiCallback(self, event=None):
        #Edit AutoDockHosts
        self.customizeGUI()
        if not hasattr(self, 'form'):
            if self.vf.hasGui:    
                self.form = self.vf.getUserInput(self.ifd, modal=0, blocking=0)
                self.form.root.protocol('WM_DELETE_WINDOW',self.Close_cb)
                self.fillForm()
                self.qType.set('int')
                self.userSpecific.set(0)
                self.topLevel = self.form.root
            else:
##                  from ViewerFramework.gui import InputForm
                from mglutil.gui.InputForm.Tk.gui import InputForm
                self.form = InputForm(self.vf.master,self.ifd,modal=0, blocking=0)
                self.topLevel = self.form.root
            self.form.autoSize()


    def customizeGUI(self):
        if not hasattr(self, 'ifd'):
            import AutoDockTools
            self.hostDict = AutoDockTools.hostDict
            #print "AADH:hostDict.keys()=", self.hostDict.keys()
            self.macroName=tkinter.StringVar(master=self.vf.GUI.ROOT)
            self.hostName=tkinter.StringVar(master=self.vf.GUI.ROOT)
            self.agPath=tkinter.StringVar(master=self.vf.GUI.ROOT)
            self.adPath=tkinter.StringVar(master=self.vf.GUI.ROOT)
            self.qType=tkinter.StringVar(master=self.vf.GUI.ROOT)
            self.userSpecific=tkinter.IntVar(master=self.vf.GUI.ROOT)
            ifd=self.ifd=InputFormDescr(title='Add Host')
            ifd.append( {'name': 'hList',
                'widgetType': tkinter.Listbox,
                'gridcfg':{'sticky':tkinter.E,'column':0, 'row': 0,'rowspan':6}})
            ifd.append( {'name': 'mNLab',
                'widgetType': tkinter.Label,
                'wcfg':{ 'text': 'Macro Name:'},
                'gridcfg':{'sticky':tkinter.E, 'row':0, 'column':1}})
            ifd.append( {'name': 'mNentry',
                'widgetType':tkinter.Entry,
                'wcfg':{
                    'width':25,
                    'textvariable':self.macroName},
                'gridcfg':{'sticky':tkinter.E,'row':0,'column':2}})
            ifd.append( {'name': 'hNLab',
                'widgetType': tkinter.Label,
                'wcfg':{ 'text': 'Host Name:'},
                'gridcfg':{'sticky':tkinter.E, 'row':1, 'column':1}})
            ifd.append( {'name': 'hNentry',
                'widgetType':tkinter.Entry,
                'wcfg':{
                    'width':25,
                    'textvariable':self.hostName},
                'gridcfg':{'sticky':tkinter.E,'row':1,'column':2}})
            ifd.append( {'name': 'agPath',
                'widgetType': tkinter.Label,
                'wcfg':{ 
                    'text': 'Autogrid Program\nPathname:'},
                'gridcfg':{'sticky':tkinter.E,'row':2,'column':1}})
            ifd.append( {'name': 'agEntry',
                'widgetType':tkinter.Entry,
                'wcfg':{
                    'width':25,
                    'textvariable':self.agPath},
                'gridcfg':{'sticky':tkinter.E,'row':2,'column':2}})
            ifd.append({'name': 'agButton',
                'widgetType': tkinter.Button,
                'wcfg':{'text':'Browse','command':self.browseAG,'bd':6},
                'gridcfg':{'sticky':tkinter.W,'row':2, 'column':3}})
            ifd.append( {'name': 'adPath',
                'widgetType': tkinter.Label,
                'wcfg':{ 'text': 'Autodock Program\nPathname:'},
                'gridcfg':{'sticky':tkinter.E, 'row':3, 'column':1}})
            ifd.append( {'name': 'adEntry',
                'widgetType':tkinter.Entry,
                'wcfg':{
                    'width':25,
                    'textvariable':self.adPath},
                'gridcfg':{'sticky':tkinter.E,'row':3,'column':2}})
            ifd.append({'name': 'adButton',
                'widgetType': tkinter.Button,
                'wcfg':{'text':'Browse','command':self.browseAD,'bd':6},
                'gridcfg':{'sticky':tkinter.W,'row':3, 'column':3}})
            ifd.append( {'name': 'qChoice',
                'widgetType': tkinter.Label,
                'wcfg':{'text':'Queue Type'},
                'gridcfg':{'sticky':tkinter.E, 'row':4, 'column':1}})
            ifd.append({'name': 'intButton',
                'widgetType': tkinter.Radiobutton,
                'wcfg':{'value':'int', 'text':'int', 'variable':self.qType},
                'gridcfg':{'sticky':tkinter.E +tkinter.W, 'row':4,'column':2}})
            ifd.append({'name': 'winButton',
                'widgetType': tkinter.Radiobutton,
                'wcfg':{'text':'nqe','value':'nqe', 'variable':self.qType},
                'gridcfg':{'sticky':tkinter.W,'row':4, 'column':3}})
            ifd.append({'name': 'pdsButton',
                'widgetType': tkinter.Radiobutton,
                'wcfg':{'text':'pbs','value':'pbs', 'state':'disabled','variable':self.qType},
                'gridcfg':{'sticky':tkinter.W,'row':4, 'column':4}})
            ifd.append( {'name': 'userOnlyChoice',
                'widgetType': tkinter.Label,
                'wcfg':{'text':'From User Dict:'},
                'gridcfg':{'sticky':tkinter.E, 'row':5, 'column':1}})
            ifd.append({'name': 'userButton',
                'widgetType': tkinter.Radiobutton,
                'wcfg':{'text':'yes','value':1, 'variable':self.userSpecific},
                'gridcfg':{'sticky':tkinter.E +tkinter.W,'row':5,'column':2}})
            ifd.append({'name': 'notuserButton',
                'widgetType': tkinter.Radiobutton,
                'wcfg':{'text':'no','value':0, 'variable':self.userSpecific},
                'gridcfg':{'sticky':tkinter.W,'row':5, 'column':3}})
            ifd.append({'widgetType': tkinter.Button,
                'wcfg':{'text':'Add','bd':6,'command':self.addItem_cb},
                'gridcfg':{'sticky':tkinter.E+tkinter.W,'row':7,'column':0}})
            ifd.append({'widgetType': tkinter.Button,
                'wcfg':{'text':'Delete','command':self.delItem_cb,'bd':6},
                'gridcfg':{'sticky':tkinter.E+tkinter.W,'row':-1,'column':1}}),
            ifd.append({'widgetType': tkinter.Button,
                'text':'Write',
                'wcfg':{'text':'Write','command':self.write_cb,'bd':6},
                'gridcfg':{'sticky':tkinter.E+tkinter.W,'row':-1,'column':2}})
            ifd.append({'widgetType': tkinter.Button,
                'wcfg':{'text':'Cancel','bd':6,'command':self.Close_cb},
                'gridcfg':{'sticky':tkinter.E+tkinter.W,'row':-1,'column':3,'columnspan':5}})
        else:
            if hasattr(self, 'form') and self.form!=None:
                self.form.deiconify()

    def fillForm(self):
        lb = self.ifd.entryByName['hList']['widget']
        dict= self.hostDict
        for h in list(dict.keys()):
            lb.insert('end',h)
        lb.select_set(0)
        lb.bind('<Double-Button-1>', self.getItem)

    def getItem(self, event=None):
        lb = self.ifd.entryByName['hList']['widget']
        p=lb.curselection()
        picked = lb.get(p)
        dict= self.hostDict
        #self.hostName.set(picked)
        self.macroName.set(picked)
        self.hostName.set(dict[picked]['host'])
        self.agPath.set(dict[picked]['autogrid'])
        self.adPath.set(dict[picked]['autodock'])
        self.qType.set(dict[picked]['queuetype'])
        #FIX THIS: need to do something different for this case!
        self.userSpecific.set(dict[picked]['userSpecific'])
        
    def delItem_cb(self, event=None):
        lb = self.ifd.entryByName['hList']['widget']
        p=lb.curselection()
        picked = lb.get(p)
        dict= self.hostDict
        del dict[picked]
        lb.delete(p)
        self.macroName.set('')
        self.hostName.set('')
        self.agPath.set('')
        self.adPath.set('')
        self.qType.set('')
        
    def buildLogStr(self):
        logstr="self.ADstart_editHostMacros.addItem_cb(macro='"+self.macroName.get()+\
"', host='"+self.hostName.get()+"',autogrid='"+self.agPath.get()+\
"',autodock='"+self.adPath.get()+"',queuetype='"+self.qType.get()+\
"',userSpecific="+str(self.userSpecific.get())+")\n"
        print(logstr)
        return logstr

    def write_cb(self, newfile = None, whichOnes='all', event=None):
        # write only current content of widget....
        adtrcDict = findResourceFile(self.vf, '_adtrc')
        idir = './'
        if 'HOME' in list(os.environ.keys()):
            home=os.environ['HOME']
            idir=home

        #if there are NO _adtrc files any where, write to HOME if it exists
        #else write to current directory
        #check for >1 choice and ask user where to write it
        hasValues=[x for x in list(adtrcDict.values()) if not x is None]
        #if filter(lambda x: not x is None, adtrcDict.values())==[]:
        if hasValues==[]:
            filename=self.vf.askFileSave(idir=idir,
                ifile='_adtrc',
                types = [('adt Resource File', '_adtrc')], 
                title = 'Save new host macros in _adtrc:')
        elif len(hasValues)>1:
            #have to give a choice here:    
            location=tkinter.StringVar(master=self.vf.GUI.ROOT)
            levels=list(adtrcDict.keys())
            ifd = InputFormDescr(title='which adtrc file to write?')
            for level in levels:
                if adtrcDict[level]:
                    ifd.append({'name':    level,
                        'widgetType':tkinter.Radiobutton,
                        'wcfg': {'value': adtrcDict[level],
                        'variable':location,
                        'text':level},
                        'gridcfg':{'sticky':tkinter.W}})
            vals = self.vf.getUserInput(ifd)
            if vals:
                filename=location.get()
                #on UNIX machines, can test writeability:
                if sys.platform!=32:
                    if not os.access(filename, os.W_OK):
                        t=filename + " not writeable by you"
                        self.vf.warningMsg(t)
                        return
                
        elif adtrcDict['currentdir']:
            filename = adtrcDict['currentdir']

        elif adtrcDict['home']:
            filename = adtrcDict['home']

        elif adtrcDict['package']:
            filename = adtrcDict['package']
            import shutil
            if not filename is None:
                shutil.copy(adtrcDict['package'],filename)

        if filename:
            fptr= open(filename, 'r')
            logLine=self.buildLogStr()
            allLines=fptr.readlines()
            for l in allLines:
                if string.find(l,logLine)>-1:
                    fptr.close()
                    t= l+ ' already in ' + filename
                    self.vf.warningMsg(t)
                    return
            fptr.close()
            f= open(filename, 'a')
            f.write('\n')
            f.write(logLine)
            f.close()

        else:
            print("Careful: nothing has been written because no filename was give")
            return

    def checkit(self, host):
        ans=0
        if host!='' and  len(self.agPath.get()) and len(self.adPath.get()) and len(self.qType.get()):
            return 1
        return ans
        
    def checklb(self,host):
        if 'hList' not in self.ifd.entryByName: return
        lb = self.ifd.entryByName['hList']['widget']
        end =lb.index('end')
        for i in range(end):
            if lb.get(i)==host:
                return  1
        else:
            return 0
        
    def addItem_cb(self, macro=None, host= None, autogrid=None, autodock=None, queuetype=None, userSpecific=None):
        #need to update the lb
        if macro: 
            self.macroName.set(macro)
        else:
            macro = self.macroName.get()
        if autogrid:
            self.agPath.set(autogrid)
        else:
            autogrid = self.agPath.get()
        if autodock:
            self.adPath.set(autodock)
        else:
            autodock=self.adPath.get()
        if queuetype:
            self.qType.set(queuetype)
        else:
            queuetype= self.qType.get()
        ans = self.checkit(macro)
        if host: 
            self.hostName.set(host)
        else:
            host = self.hostName.get()
        if userSpecific:
            self.userSpecific.set(userSpecific)
        else:
            userSpecific= self.userSpecific.get()
        if ans:
            self.hostDict.addHost(macro, host=host,autogrid=autogrid,autodock=autodock,queuetype=queuetype,userSpecific=userSpecific)
            msg = "self.ADstart_editHostMacros.addItem_cb(macro='" + macro + "',host='"+host+ "', autogrid='"+ autogrid + "', autodock = '" + autodock + "', queuetype='" + queuetype+"', userSpecific="+ str(userSpecific) + ")"
            self.vf.log(msg)
        ans = self.checklb(macro)
        if not ans and 'hList' in self.ifd.entryByName:
            lb = self.ifd.entryByName['hList']['widget']
            lb.insert('end', macro)

    def Close_cb(self):
        self.form.root.withdraw()

    def browseAG(self):
        ag = self.vf.askFileOpen(parent = self.topLevel,
                                 types=[('autogrid..','*')], title=  'Autogrid Executable File:')
        if ag: 
            #don't strip off the pathname??
            agPathList=os.path.split(ag)
            if agPathList[0]==os.getcwd():
                ag = agPathList[-1]
            self.agPath.set(ag)
        if hasattr(self, 'topLevel'):self.topLevel.lift()

    def browseAD(self):
        ad = self.vf.askFileOpen(parent = self.topLevel,
                                 types=[('autodock..','*')], title=  'Autodock Executable File:')
        if ad: 
            #don't strip off the pathname??
            adPathList=os.path.split(ad)
            if adPathList[0]==os.getcwd():
                ad = adPathList[-1]
            self.adPath.set(ad)
        if hasattr(self, 'topLevel'):self.topLevel.lift()
        
AddAutoDockHostGUI=CommandGUI()
AddAutoDockHostGUI.addMenuCommand('AutoToolsBar', menuText['StartMB'], menuText['editHostsMB'])

commandList = [
    {'name':'ADstart_autogrid','cmd':AutoGridStarter(),'gui':AutoGridStarterGUI},
    {'name':'ADstart_autodock','cmd':AutoDockStarter(),'gui':AutoDockStarterGUI},
    {'name':'ADstart_editHostMacros','cmd':AddAutoDockHost(),'gui':AddAutoDockHostGUI},
    ]

import sys
if os.name != 'nt': #not sys.platform == 'win32':
    commandList.insert(2,
    {'name':'ADstart_manage','cmd':ADProcessManager(),'gui':ADProcessManagerGUI})
else:
    import binaries
    if 'PATH' in os.environ:
        os.environ['PATH'] = binaries.__path__[0]+";"+os.environ['PATH']
    else:
        os.environ['PATH'] = binaries.__path__[0]
        
def initModule(vf):


    for dict in commandList:
        vf.addCommand(dict['cmd'],dict['name'],dict['gui'])

    if hasattr(vf,'GUI'):
        for item in list(vf.GUI.menuBars['AutoToolsBar'].menubuttons.values()):
            item.configure(background = 'tan')
            item.configure(underline = '-1')
 

    else:
        vf.addCommand(ADProcessManager(),'ADstart_manage')
        vf.addCommand(AutoGridStarter(), 'ADstart_autogrid')
        vf.addCommand(AutoDockStarter(), 'ADstart_autodock')
