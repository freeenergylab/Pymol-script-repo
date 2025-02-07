import os
import sys
import imp

from .TreeWidget import TreeItem
from .ClassBrowser import ClassBrowser, ModuleBrowserTreeItem

class PathBrowser(ClassBrowser):

    def __init__(self, flist):
        self.init(flist)

    def settitle(self):
        self.top.wm_title("Path Browser")
        self.top.wm_iconname("Path Browser")

    def rootnode(self):
        return PathBrowserTreeItem(self.flist)

class PathBrowserTreeItem(TreeItem):

    def __init__(self, flist):
        self.flist = flist

    def GetText(self):
        return "sys.path"

    def GetSubList(self):
        sublist = []
        for dir in sys.path:
            item = DirBrowserTreeItem(dir, flist=self.flist)
            sublist.append(item)
        return sublist

class DirBrowserTreeItem(TreeItem):

    def __init__(self, dir, packages=[], flist=None):
        self.dir = dir
        self.packages = packages
        self.flist = flist

    def GetText(self):
        if not self.packages:
            return self.dir
        else:
            return self.packages[-1] + ": package"

    def GetSubList(self):
        try:
            names = os.listdir(self.dir or os.curdir)
        except os.error:
            return []
        packages = []
        for name in names:
            file = os.path.join(self.dir, name)
            if self.ispackagedir(file):
                nn = os.path.normcase(name)
                packages.append((nn, name, file))
        packages.sort()
        sublist = []
        for nn, name, file in packages:
            item = DirBrowserTreeItem(file, self.packages + [name], self.flist)
            sublist.append(item)
        for nn, name in self.listmodules(names):
            item = ModuleBrowserTreeItem(os.path.join(self.dir, name), 
                self.flist)
            sublist.append(item)
        return sublist

    def ispackagedir(self, file):
        if not os.path.isdir(file):
            return 0
        init = os.path.join(file, "__init__.py")
        return os.path.exists(init)

    def listmodules(self, allnames):
        modules = {}
        suffixes = imp.get_suffixes()
        sorted = []
        for suff, mode, flag in suffixes:
            i = -len(suff)
            for name in allnames[:]:
                normed_name = os.path.normcase(name)
                if normed_name[i:] == suff:
                    mod_name = name[:i]
                    if mod_name not in modules:
                        modules[mod_name] = None
                        sorted.append((normed_name, name))
                        allnames.remove(name)
        sorted.sort()
        return sorted

def main():
    from . import PyShell
    PathBrowser(PyShell.flist)
    if sys.stdin is sys.__stdin__:
        mainloop()

if __name__ == "__main__":
    main()
