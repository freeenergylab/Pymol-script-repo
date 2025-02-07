"Dialog to specify or edit the parameters for a user configured help source."
import os
import sys
from tkinter import Toplevel, Frame, Entry, Button, Label, StringVar
from tkinter.constants import GROOVE, LEFT, RIGHT, W, ACTIVE, X, BOTH, TOP, BOTTOM
import tkinter.messagebox
import tkinter.filedialog

from .configHandler import idleConf

TTK = idleConf.GetOption('main', 'General', 'use-ttk', type='int')
if TTK:
    from tkinter.ttk import Frame, Entry, Button, Label

class GetHelpSourceDialog(Toplevel):
    def __init__(self, parent, title, menuItem='', filePath=''):
        """Get menu entry and url/ local file location for Additional Help

        User selects a name for the Help resource and provides a web url
        or a local file as its source.  The user can enter a url or browse
        for the file.

        """
        Toplevel.__init__(self, parent)
        self.configure(borderwidth=5)
        self.resizable(height=False, width=False)
        self.title(title)
        self.transient(parent)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self.Cancel)
        self.parent = parent
        self.result = None

        self.CreateWidgets()
        self.menu.set(menuItem)
        self.path.set(filePath)
        self.withdraw() #hide while setting geometry
        #needs to be done here so that the winfo_reqwidth is valid
        self.update_idletasks()
        #centre dialog over parent:
        self.geometry("+%d+%d" %
                      ((parent.winfo_rootx() + ((parent.winfo_width()/2)
                                                -(self.winfo_reqwidth()/2)),
                        parent.winfo_rooty() + ((parent.winfo_height()/2)
                                                -(self.winfo_reqheight()/2)))))
        self.deiconify() #geometry set, unhide
        self.bind('<Return>', self.Ok)
        self.wait_window()

    def CreateWidgets(self):
        self.menu = StringVar(self)
        self.path = StringVar(self)
        self.fontSize = StringVar(self)
        self.frameMain = Frame(self, borderwidth=2, relief=GROOVE)
        labelMenu = Label(self.frameMain, anchor=W, justify=LEFT,
            text='Menu Item:')
        self.entryMenu = Entry(self.frameMain, textvariable=self.menu)
        labelPath = Label(self.frameMain, anchor=W, justify=LEFT,
            text='Help File Path: Enter URL or browse for file')
        self.entryPath = Entry(self.frameMain, textvariable=self.path,
            width=30)
        browseButton = Button(self.frameMain, text='Browse', width=8,
            command=self.browseFile)
        frameButtons = Frame(self)
        self.buttonOk = Button(frameButtons, text='OK', width=8,
            default=ACTIVE,  command=self.Ok)
        self.buttonCancel = Button(frameButtons, text='Cancel', width=8,
            command=self.Cancel)

        self.entryMenu.focus_set()

        self.frameMain.pack(side=TOP, expand=True, fill=BOTH)
        labelMenu.pack(anchor=W, padx=5, pady=3)
        self.entryMenu.pack(anchor=W, padx=5, pady=3, fill=X)
        labelPath.pack(anchor=W, padx=5, pady=3)
        self.entryPath.pack(anchor=W, padx=5, pady=3, side=LEFT, fill=X)
        browseButton.pack(pady=3, padx=5, side=RIGHT)
        frameButtons.pack(side=BOTTOM, fill=X)
        self.buttonOk.pack(pady=5, side=RIGHT)
        self.buttonCancel.pack(padx=5, pady=5, side=RIGHT)

        if TTK:
            frameButtons['style'] = 'RootColor.TFrame'

    def browseFile(self):
        filetypes = [
            ("HTML Files", "*.htm *.html", "TEXT"),
            ("PDF Files", "*.pdf", "TEXT"),
            ("Windows Help Files", "*.chm"),
            ("Text Files", "*.txt", "TEXT"),
            ("All Files", "*")]
        path = self.path.get()
        if path:
            dir, base = os.path.split(path)
        else:
            base = None
            if sys.platform[:3] == 'win':
                dir = os.path.join(os.path.dirname(sys.executable), 'Doc')
                if not os.path.isdir(dir):
                    dir = os.getcwd()
            else:
                dir = os.getcwd()
        opendialog = tkinter.filedialog.Open(parent=self, filetypes=filetypes)
        file = opendialog.show(initialdir=dir, initialfile=base)
        if file:
            self.path.set(file)

    def MenuOk(self):
        "Simple validity check for a sensible menu item name"
        menuOk = True
        menu = self.menu.get()
        menu.strip()
        if not menu:
            tkinter.messagebox.showerror(title='Menu Item Error',
                                   message='No menu item specified',
                                   parent=self)
            self.entryMenu.focus_set()
            menuOk = False
        elif len(menu) > 30:
            tkinter.messagebox.showerror(title='Menu Item Error',
                                   message='Menu item too long:'
                                           '\nLimit 30 characters.',
                                   parent=self)
            self.entryMenu.focus_set()
            menuOk = False
        return menuOk

    def PathOk(self):
        "Simple validity check for menu file path"
        pathOk = True
        path = self.path.get()
        path.strip()
        if not path: #no path specified
            tkinter.messagebox.showerror(title='File Path Error',
                                   message='No help file path specified.',
                                   parent=self)
            self.entryPath.focus_set()
            pathOk = False
        elif path.startswith(('www.', 'http')):
            pass
        else:
            if path[:5] == 'file:':
                path = path[5:]
            if not os.path.exists(path):
                tkinter.messagebox.showerror(title='File Path Error',
                                       message='Help file path does not exist.',
                                       parent=self)
                self.entryPath.focus_set()
                pathOk = False
        return pathOk

    def Ok(self, event=None):
        if self.MenuOk() and self.PathOk():
            self.result = (self.menu.get().strip(),
                           self.path.get().strip())
            if sys.platform == 'darwin':
                path = self.result[1]
                if path.startswith(('www', 'file:', 'http:')):
                    pass
                else:
                    # Mac Safari insists on using the URI form for local files
                    self.result = list(self.result)
                    self.result[1] = "file://" + path
            self.destroy()

    def Cancel(self, event=None):
        self.result = None
        self.destroy()

if __name__ == '__main__':
    from tkinter import Tk
    #test the dialog
    root = Tk()
    def run():
        keySeq = ''
        dlg = GetHelpSourceDialog(root, 'Get Help Source')
        print(dlg.result)
    Button(root,text='Dialog', command=run).pack()
    root.mainloop()
