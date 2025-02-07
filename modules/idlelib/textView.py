"""Simple text browser for IDLE"""

import tkinter.messagebox
from tkinter import Toplevel, Frame, Button, Scrollbar, Text
from tkinter.constants import DISABLED, SUNKEN, VERTICAL, WORD, RIGHT, Y, TOP, \
                        LEFT, BOTH, BOTTOM

from .configHandler import idleConf

TTK = idleConf.GetOption('main', 'General', 'use-ttk', type='int')
if TTK:
    from tkinter.ttk import Frame, Button, Scrollbar

class TextViewer(Toplevel):
    """A simple text viewer dialog for IDLE

    """
    def __init__(self, parent, title, text):
        """Show the given text in a scrollable window with a 'close' button

        """
        Toplevel.__init__(self, parent)
        self.configure(borderwidth=5)
        self.geometry("=%dx%d+%d+%d" % (625, 500,
                                        parent.winfo_rootx() + 10,
                                        parent.winfo_rooty() + 10))
        #elguavas - config placeholders til config stuff completed
        self.bg = '#ffffff'
        self.fg = '#000000'

        self.CreateWidgets()
        self.title(title)
        self.transient(parent)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self.Ok)
        self.parent = parent
        self.textView.focus_set()
        #key bindings for this dialog
        self.bind('<Return>',self.Ok) #dismiss dialog
        self.bind('<Escape>',self.Ok) #dismiss dialog
        self.textView.insert(0.0, text)
        self.textView.config(state=DISABLED)
        self.wait_window()

    def CreateWidgets(self):
        frameText = Frame(self, relief=SUNKEN, height=700)
        frameButtons = Frame(self)
        self.buttonOk = Button(frameButtons, text='Close',
                               command=self.Ok, takefocus=False)
        self.scrollbarView = Scrollbar(frameText, orient=VERTICAL,
                                       takefocus=False)
        self.textView = Text(frameText, wrap=WORD, fg=self.fg, bg=self.bg,
                             highlightthickness=0)
        self.scrollbarView.config(command=self.textView.yview)
        self.textView.config(yscrollcommand=self.scrollbarView.set)
        self.buttonOk.pack()
        self.scrollbarView.pack(side=RIGHT,fill=Y)
        self.textView.pack(side=LEFT,expand=True,fill=BOTH)
        frameButtons.pack(side=BOTTOM)
        frameText.pack(side=TOP,expand=True,fill=BOTH)

        if TTK:
            frameButtons['style'] = 'RootColor.TFrame'

    def Ok(self, event=None):
        self.destroy()


def view_text(parent, title, text):
    TextViewer(parent, title, text)

def view_file(parent, title, filename, encoding=None):
    try:
        if encoding:
            import codecs
            textFile = codecs.open(filename, 'r')
        else:
            textFile = open(filename, 'r')
    except IOError:
        tkinter.messagebox.showerror(title='File Load Error',
                               message='Unable to load file %r .' % filename,
                               parent=parent)
    else:
        return view_text(parent, title, textFile.read())


if __name__ == '__main__':
    from tkinter import Tk
    #test the dialog
    root=Tk()
    root.title('textView test')
    filename = './textView.py'
    text = file(filename, 'r').read()
    btn1 = Button(root, text='view_text',
                 command=lambda:view_text(root, 'view_text', text))
    btn1.pack(side=LEFT)
    btn2 = Button(root, text='view_file',
                  command=lambda:view_file(root, 'view_file', filename))
    btn2.pack(side=LEFT)
    close = Button(root, text='Close', command=root.destroy)
    close.pack(side=RIGHT)
    root.mainloop()
