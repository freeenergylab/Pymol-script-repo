"""Extension to execute code outside the Python shell window.

This adds the following commands:

- Check module does a full syntax check of the current module.
  It also runs the tabnanny to catch any inconsistent tabs.

- Run module executes the module's code in the __main__ namespace.  The window
  must have been saved previously. The module is added to sys.modules, and is
  also added to the __main__ namespace.

XXX GvR Redesign this interface (yet again) as follows:

- Present a dialog box for ``Run Module''

- Allow specify command line arguments in the dialog box

"""

import os
import re
import string
import tabnanny
import tokenize
import tkinter.messagebox
from . import PyShell

from .configHandler import idleConf

IDENTCHARS = string.ascii_letters + string.digits + "_"

indent_message = """Error: Inconsistent indentation detected!

1) Your indentation is outright incorrect (easy to fix), OR

2) Your indentation mixes tabs and spaces.

To fix case 2, change all tabs to spaces by using Edit->Select All followed \
by Format->Untabify Region and specify the number of columns used by each tab.
"""

class ScriptBinding:

    menudefs = [
        ('run', [None,
                 ('Check Module', '<<check-module>>'),
                 ('Run Module', '<<run-module>>'), ]), ]

    def __init__(self, editpage):
        self.editpage = editpage
        self.editwin = editpage.editwin
        # Provide instance variables referenced by Debugger
        # XXX This should be done differently
        self.flist = self.editwin.flist
        self.root = self.editwin.root

    def check_module_event(self, event):
        filename = self.getfilename()
        if not filename:
            return 'break'
        if not self.checksyntax(filename):
            return 'break'
        if not self.tabnanny(filename):
            return 'break'

    def tabnanny(self, filename):
        f = open(filename, 'r')
        try:
            tabnanny.process_tokens(tokenize.generate_tokens(f.readline))
        except tokenize.TokenError as msg:
            msgtxt, (lineno, start) = msg
            self.editwin.gotoline(lineno)
            self.errorbox("Tabnanny Tokenizing Error",
                "Token Error: %s" % msgtxt)
            return False
        except tabnanny.NannyNag as nag:
            # The error messages from tabnanny are too confusing...
            self.editwin.gotoline(nag.get_lineno())
            self.errorbox("Tab/space error", indent_message)
            return False
        return True

    def checksyntax(self, filename):
        self.shell = shell = self.flist.open_shell()
        saved_stream = shell.get_warning_stream()
        shell.set_warning_stream(shell.stderr)
        f = open(filename, 'r')
        source = f.read()
        f.close()
        if '\r' in source:
            source = re.sub(r"\r\n", "\n", source)
            source = re.sub(r"\r", "\n", source)
        if source and source[-1] != '\n':
            source = source + '\n'
        text = self.editpage.text
        text.tag_remove("ERROR", "1.0", "end")
        try:
            try:
                # If successful, return the compiled code
                return compile(source, filename, "exec")
            except (SyntaxError, OverflowError) as err:
                try:
                    msg, (errorfilename, lineno, offset, line) = err
                    if not errorfilename:
                        err.args = msg, (filename, lineno, offset, line)
                        err.filename = filename
                    self.colorize_syntax_error(msg, lineno, offset)
                except:
                    msg = "*** " + str(err)
                self.errorbox("Syntax error",
                              "There's an error in your program:\n" + msg)
                return False
        finally:
            shell.set_warning_stream(saved_stream)

    def colorize_syntax_error(self, msg, lineno, offset):
        text = self.editpage.text
        pos = "0.0 + %d lines + %d chars" % (lineno-1, offset-1)
        text.tag_add("ERROR", pos)
        char = text.get(pos)
        if char and char in IDENTCHARS:
            text.tag_add("ERROR", pos + " wordstart", pos)
        if '\n' == text.get(pos):   # error at line end
            text.mark_set("insert", pos)
        else:
            text.mark_set("insert", pos + "+1c")
        text.see(pos)

    def run_module_event(self, event):
        """Run the module after setting up the environment.

        First check the syntax.  If OK, make sure the shell is active and
        then transfer the arguments, set the run environment's working
        directory to the directory of the module being executed and also
        add that directory to its sys.path if not already included.

        """
        filename = self.getfilename()
        if not filename:
            return 'break'
        code = self.checksyntax(filename)
        if not code:
            return 'break'
        if not self.tabnanny(filename):
            return 'break'
        shell = self.shell
        interp = shell.interp
        if PyShell.use_subprocess:
            shell.restart_shell()
        dirname = os.path.dirname(filename)
        # XXX Too often this discards arguments the user just set...
        interp.runcommand("""if 1:
            _filename = %r
            import sys as _sys
            from os.path import basename as _basename
            if (not _sys.argv or
                _basename(_sys.argv[0]) != _basename(_filename)):
                _sys.argv = [_filename]
            import os as _os
            _os.chdir(%r)
            del _filename, _sys, _basename, _os
            \n""" % (filename, dirname))
        interp.prepend_syspath(filename)
        # XXX KBK 03Jul04 When run w/o subprocess, runtime warnings still
        #         go to __stderr__.  With subprocess, they go to the shell.
        #         Need to change streams in PyShell.ModifiedInterpreter.
        interp.runcode(code)
        return 'break'

    def getfilename(self):
        """Get source filename.  If not saved, offer to save (or create) file

        The debugger requires a source file.  Make sure there is one, and that
        the current version of the source buffer has been saved.  If the user
        declines to save or cancels the Save As dialog, return None.

        If the user has configured IDLE for Autosave, the file will be
        silently saved if it already exists and is dirty.
        """
        page = self.editpage
        filename = page.io.filename
        if not page.get_saved():
            autosave = idleConf.GetOption('main', 'General',
                                          'autosave', type='bool')
            if autosave and filename:
                page.io.save(None)
            else:
                reply = self.ask_save_dialog()
                page.text.focus_set()
                if reply == "ok":
                    page.io.save(None)
                    filename = page.io.filename
                else:
                    filename = None
        return filename

    def ask_save_dialog(self):
        msg = "Source Must Be Saved\n" + 5*' ' + "OK to Save?"
        mb = tkinter.messagebox.Message(title="Save Before Run or Check",
            message=msg, icon=tkinter.messagebox.QUESTION,
            type=tkinter.messagebox.OKCANCEL, default=tkinter.messagebox.OK,
            master=self.editpage.text)
        return mb.show()

    def errorbox(self, title, message):
        # XXX This should really be a function of EditorWindow...
        tkinter.messagebox.showerror(title, message, master=self.editpage.text)
        self.editpage.text.focus_set()
