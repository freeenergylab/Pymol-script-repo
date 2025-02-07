""" Modified version of build_ext that handles fortran source files.
"""

import os
import sys
from glob import glob

from distutils.dep_util import newer_group
from distutils.command.build_ext import build_ext as old_build_ext
from distutils.errors import DistutilsFileError, DistutilsSetupError,\
     DistutilsError
from distutils.file_util import copy_file

from numpy.distutils import log
from numpy.distutils.exec_command import exec_command
from numpy.distutils.system_info import combine_paths
from numpy.distutils.misc_util import filter_sources, has_f_sources, \
     has_cxx_sources, get_ext_source_files, \
     get_numpy_include_dirs, is_sequence
from numpy.distutils.command.config_compiler import show_fortran_compilers

try:
    set
except NameError:
    from sets import Set as set

class build_ext (old_build_ext):

    description = "build C/C++/F extensions (compile/link to build directory)"

    user_options = old_build_ext.user_options + [
        ('fcompiler=', None,
         "specify the Fortran compiler type"),
        ]

    help_options = old_build_ext.help_options + [
        ('help-fcompiler',None, "list available Fortran compilers",
         show_fortran_compilers),
        ]

    def initialize_options(self):
        old_build_ext.initialize_options(self)
        self.fcompiler = None

    def finalize_options(self):
        incl_dirs = self.include_dirs
        old_build_ext.finalize_options(self)
        if incl_dirs is not None:
            self.include_dirs.extend(self.distribution.include_dirs or [])

    def run(self):
        if not self.extensions:
            return

        # Make sure that extension sources are complete.
        self.run_command('build_src')

        if self.distribution.has_c_libraries():
            self.run_command('build_clib')
            build_clib = self.get_finalized_command('build_clib')
            self.library_dirs.append(build_clib.build_clib)
        else:
            build_clib = None

        # Not including C libraries to the list of
        # extension libraries automatically to prevent
        # bogus linking commands. Extensions must
        # explicitly specify the C libraries that they use.

        from distutils.ccompiler import new_compiler
        from numpy.distutils.fcompiler import new_fcompiler

        compiler_type = self.compiler
        # Initialize C compiler:
        self.compiler = new_compiler(compiler=compiler_type,
                                     verbose=self.verbose,
                                     dry_run=self.dry_run,
                                     force=self.force)
        self.compiler.customize(self.distribution)
        self.compiler.customize_cmd(self)
        self.compiler.show_customization()

        # Create mapping of libraries built by build_clib:
        clibs = {}
        if build_clib is not None:
            for libname,build_info in build_clib.libraries or []:
                if libname in clibs and clibs[libname] != build_info:
                    log.warn('library %r defined more than once,'\
                             ' overwriting build_info\n%s... \nwith\n%s...' \
                             % (libname, repr(clibs[libname])[:300], repr(build_info)[:300]))
                clibs[libname] = build_info
        # .. and distribution libraries:
        for libname,build_info in self.distribution.libraries or []:
            if libname in clibs:
                # build_clib libraries have a precedence before distribution ones
                continue
            clibs[libname] = build_info

        # Determine if C++/Fortran 77/Fortran 90 compilers are needed.
        # Update extension libraries, library_dirs, and macros.
        all_languages = set()
        for ext in self.extensions:
            ext_languages = set()
            c_libs = []
            c_lib_dirs = []
            macros = []
            for libname in ext.libraries:
                if libname in clibs:
                    binfo = clibs[libname]
                    c_libs += binfo.get('libraries',[])
                    c_lib_dirs += binfo.get('library_dirs',[])
                    for m in binfo.get('macros',[]):
                        if m not in macros:
                            macros.append(m)

                for l in clibs.get(libname,{}).get('source_languages',[]):
                    ext_languages.add(l)
            if c_libs:
                new_c_libs = ext.libraries + c_libs
                log.info('updating extension %r libraries from %r to %r'
                         % (ext.name, ext.libraries, new_c_libs))
                ext.libraries = new_c_libs
                ext.library_dirs = ext.library_dirs + c_lib_dirs
            if macros:
                log.info('extending extension %r defined_macros with %r'
                         % (ext.name, macros))
                ext.define_macros = ext.define_macros + macros

            # determine extension languages
            if has_f_sources(ext.sources):
                ext_languages.add('f77')
            if has_cxx_sources(ext.sources):
                ext_languages.add('c++')
            l = ext.language or self.compiler.detect_language(ext.sources)
            if l:
                ext_languages.add(l)
            # reset language attribute for choosing proper linker
            if 'c++' in ext_languages:
                ext_language = 'c++'
            elif 'f90' in ext_languages:
                ext_language = 'f90'
            elif 'f77' in ext_languages:
                ext_language = 'f77'
            else:
                ext_language = 'c' # default
            if l and l != ext_language and ext.language:
                log.warn('resetting extension %r language from %r to %r.' %
                         (ext.name,l,ext_language))
            ext.language = ext_language
            # global language
            all_languages.update(ext_languages)

        need_f90_compiler = 'f90' in all_languages
        need_f77_compiler = 'f77' in all_languages
        need_cxx_compiler = 'c++' in all_languages

        # Initialize C++ compiler:
        if need_cxx_compiler:
            self._cxx_compiler = new_compiler(compiler=compiler_type,
                                             verbose=self.verbose,
                                             dry_run=self.dry_run,
                                             force=self.force)
            compiler = self._cxx_compiler
            compiler.customize(self.distribution,need_cxx=need_cxx_compiler)
            compiler.customize_cmd(self)
            compiler.show_customization()
            self._cxx_compiler = compiler.cxx_compiler()
        else:
            self._cxx_compiler = None

        # Initialize Fortran 77 compiler:
        if need_f77_compiler:
            ctype = self.fcompiler
            self._f77_compiler = new_fcompiler(compiler=self.fcompiler,
                                               verbose=self.verbose,
                                               dry_run=self.dry_run,
                                               force=self.force,
                                               requiref90=False,
                                               c_compiler=self.compiler)
            fcompiler = self._f77_compiler
            if fcompiler:
                ctype = fcompiler.compiler_type
                fcompiler.customize(self.distribution)
            if fcompiler and fcompiler.get_version():
                fcompiler.customize_cmd(self)
                fcompiler.show_customization()
            else:
                self.warn('f77_compiler=%s is not available.' %
                          (ctype))
                self._f77_compiler = None
        else:
            self._f77_compiler = None

        # Initialize Fortran 90 compiler:
        if need_f90_compiler:
            ctype = self.fcompiler
            self._f90_compiler = new_fcompiler(compiler=self.fcompiler,
                                               verbose=self.verbose,
                                               dry_run=self.dry_run,
                                               force=self.force,
                                               requiref90=True,
                                               c_compiler = self.compiler)
            fcompiler = self._f90_compiler
            if fcompiler:
                ctype = fcompiler.compiler_type
                fcompiler.customize(self.distribution)
            if fcompiler and fcompiler.get_version():
                fcompiler.customize_cmd(self)
                fcompiler.show_customization()
            else:
                self.warn('f90_compiler=%s is not available.' %
                          (ctype))
                self._f90_compiler = None
        else:
            self._f90_compiler = None

        # Build extensions
        self.build_extensions()

    def swig_sources(self, sources):
        # Do nothing. Swig sources have beed handled in build_src command.
        return sources

    def build_extension(self, ext):
        sources = ext.sources
        if sources is None or not is_sequence(sources):
            raise DistutilsSetupError(
                ("in 'ext_modules' option (extension '%s'), " +
                 "'sources' must be present and must be " +
                 "a list of source filenames") % ext.name)
        sources = list(sources)

        if not sources:
            return

        fullname = self.get_ext_fullname(ext.name)
        if self.inplace:
            modpath = fullname.split('.')
            package = '.'.join(modpath[0:-1])
            base = modpath[-1]
            build_py = self.get_finalized_command('build_py')
            package_dir = build_py.get_package_dir(package)
            ext_filename = os.path.join(package_dir,
                                        self.get_ext_filename(base))
        else:
            ext_filename = os.path.join(self.build_lib,
                                        self.get_ext_filename(fullname))
        depends = sources + ext.depends

        if not (self.force or newer_group(depends, ext_filename, 'newer')):
            log.debug("skipping '%s' extension (up-to-date)", ext.name)
            return
        else:
            log.info("building '%s' extension", ext.name)

        extra_args = ext.extra_compile_args or []
        macros = ext.define_macros[:]
        for undef in ext.undef_macros:
            macros.append((undef,))

        c_sources, cxx_sources, f_sources, fmodule_sources = \
                   filter_sources(ext.sources)



        if self.compiler.compiler_type=='msvc':
            if cxx_sources:
                # Needed to compile kiva.agg._agg extension.
                extra_args.append('/Zm1000')
            # this hack works around the msvc compiler attributes
            # problem, msvc uses its own convention :(
            c_sources += cxx_sources
            cxx_sources = []

        # Set Fortran/C++ compilers for compilation and linking.
        if ext.language=='f90':
            fcompiler = self._f90_compiler
        elif ext.language=='f77':
            fcompiler = self._f77_compiler
        else: # in case ext.language is c++, for instance
            fcompiler = self._f90_compiler or self._f77_compiler
        cxx_compiler = self._cxx_compiler

        # check for the availability of required compilers
        if cxx_sources and cxx_compiler is None:
            raise DistutilsError("extension %r has C++ sources" \
                  "but no C++ compiler found" % (ext.name))
        if (f_sources or fmodule_sources) and fcompiler is None:
            raise DistutilsError("extension %r has Fortran sources " \
                  "but no Fortran compiler found" % (ext.name))
        if ext.language in ['f77','f90'] and fcompiler is None:
            self.warn("extension %r has Fortran libraries " \
                  "but no Fortran linker found, using default linker" % (ext.name))
        if ext.language=='c++' and cxx_compiler is None:
            self.warn("extension %r has C++ libraries " \
                  "but no C++ linker found, using default linker" % (ext.name))

        kws = {'depends':ext.depends}
        output_dir = self.build_temp

        include_dirs = ext.include_dirs + get_numpy_include_dirs()

        c_objects = []
        if c_sources:
            log.info("compiling C sources")
            c_objects = self.compiler.compile(c_sources,
                                              output_dir=output_dir,
                                              macros=macros,
                                              include_dirs=include_dirs,
                                              debug=self.debug,
                                              extra_postargs=extra_args,
                                              **kws)

        if cxx_sources:
            log.info("compiling C++ sources")
            c_objects += cxx_compiler.compile(cxx_sources,
                                              output_dir=output_dir,
                                              macros=macros,
                                              include_dirs=include_dirs,
                                              debug=self.debug,
                                              extra_postargs=extra_args,
                                              **kws)

        extra_postargs = []
        f_objects = []
        if fmodule_sources:
            log.info("compiling Fortran 90 module sources")
            module_dirs = ext.module_dirs[:]
            module_build_dir = os.path.join(
                self.build_temp,os.path.dirname(
                    self.get_ext_filename(fullname)))

            self.mkpath(module_build_dir)
            if fcompiler.module_dir_switch is None:
                existing_modules = glob('*.mod')
            extra_postargs += fcompiler.module_options(
                module_dirs,module_build_dir)
            f_objects += fcompiler.compile(fmodule_sources,
                                           output_dir=self.build_temp,
                                           macros=macros,
                                           include_dirs=include_dirs,
                                           debug=self.debug,
                                           extra_postargs=extra_postargs,
                                           depends=ext.depends)

            if fcompiler.module_dir_switch is None:
                for f in glob('*.mod'):
                    if f in existing_modules:
                        continue
                    t = os.path.join(module_build_dir, f)
                    if os.path.abspath(f)==os.path.abspath(t):
                        continue
                    if os.path.isfile(t):
                        os.remove(t)
                    try:
                        self.move_file(f, module_build_dir)
                    except DistutilsFileError:
                        log.warn('failed to move %r to %r' %
                                 (f, module_build_dir))
        if f_sources:
            log.info("compiling Fortran sources")
            f_objects += fcompiler.compile(f_sources,
                                           output_dir=self.build_temp,
                                           macros=macros,
                                           include_dirs=include_dirs,
                                           debug=self.debug,
                                           extra_postargs=extra_postargs,
                                           depends=ext.depends)

        objects = c_objects + f_objects

        if ext.extra_objects:
            objects.extend(ext.extra_objects)
        extra_args = ext.extra_link_args or []
        libraries = self.get_libraries(ext)[:]
        library_dirs = ext.library_dirs[:]

        linker = self.compiler.link_shared_object
        # Always use system linker when using MSVC compiler.
        if self.compiler.compiler_type=='msvc':
            # expand libraries with fcompiler libraries as we are
            # not using fcompiler linker
            self._libs_with_msvc_and_fortran(fcompiler, libraries, library_dirs)
        elif ext.language in ['f77','f90'] and fcompiler is not None:
            linker = fcompiler.link_shared_object
        if ext.language=='c++' and cxx_compiler is not None:
            linker = cxx_compiler.link_shared_object

        if sys.version[:3]>='2.3':
            kws = {'target_lang':ext.language}
        else:
            kws = {}

        linker(objects, ext_filename,
               libraries=libraries,
               library_dirs=library_dirs,
               runtime_library_dirs=ext.runtime_library_dirs,
               extra_postargs=extra_args,
               export_symbols=self.get_export_symbols(ext),
               debug=self.debug,
               build_temp=self.build_temp,**kws)

    def _libs_with_msvc_and_fortran(self, fcompiler, c_libraries,
                                    c_library_dirs):
        if fcompiler is None: return

        for libname in c_libraries:
            if libname.startswith('msvc'): continue
            fileexists = False
            for libdir in c_library_dirs or []:
                libfile = os.path.join(libdir,'%s.lib' % (libname))
                if os.path.isfile(libfile):
                    fileexists = True
                    break
            if fileexists: continue
            # make g77-compiled static libs available to MSVC
            fileexists = False
            for libdir in c_library_dirs:
                libfile = os.path.join(libdir,'lib%s.a' % (libname))
                if os.path.isfile(libfile):
                    # copy libname.a file to name.lib so that MSVC linker
                    # can find it
                    libfile2 = os.path.join(self.build_temp, libname + '.lib')
                    copy_file(libfile, libfile2)
                    if self.build_temp not in c_library_dirs:
                        c_library_dirs.append(self.build_temp)
                    fileexists = True
                    break
            if fileexists: continue
            log.warn('could not find library %r in directories %s'
                     % (libname, c_library_dirs))

        # Always use system linker when using MSVC compiler.
        f_lib_dirs = []
        for dir in fcompiler.library_dirs:
            # correct path when compiling in Cygwin but with normal Win
            # Python
            if dir.startswith('/usr/lib'):
                s,o = exec_command(['cygpath', '-w', dir], use_tee=False)
                if not s:
                    dir = o
            f_lib_dirs.append(dir)
        c_library_dirs.extend(f_lib_dirs)

        # make g77-compiled static libs available to MSVC
        for lib in fcompiler.libraries:
            if not lib.startswith('msvc'):
                c_libraries.append(lib)
                p = combine_paths(f_lib_dirs, 'lib' + lib + '.a')
                if p:
                    dst_name = os.path.join(self.build_temp, lib + '.lib')
                    if not os.path.isfile(dst_name):
                        copy_file(p[0], dst_name)
                    if self.build_temp not in c_library_dirs:
                        c_library_dirs.append(self.build_temp)

    def get_source_files (self):
        self.check_extensions_list(self.extensions)
        filenames = []
        for ext in self.extensions:
            filenames.extend(get_ext_source_files(ext))
        return filenames

    def get_outputs (self):
        self.check_extensions_list(self.extensions)

        outputs = []
        for ext in self.extensions:
            if not ext.sources:
                continue
            fullname = self.get_ext_fullname(ext.name)
            outputs.append(os.path.join(self.build_lib,
                                        self.get_ext_filename(fullname)))
        return outputs
