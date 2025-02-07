#!/usr/bin/env python

def configuration(parent_package='',top_path=None):
    from numpy.distutils.misc_util import Configuration
    config = Configuration('numpy',parent_package,top_path, setup_name = 'setupscons.py')
    config.add_subpackage('distutils')
    config.add_subpackage('testing')
    config.add_subpackage('f2py')
    config.add_subpackage('core')
    config.add_subpackage('lib')
    config.add_subpackage('oldnumeric')
    config.add_subpackage('numarray')
    config.add_subpackage('fft')
    config.add_subpackage('linalg')
    config.add_subpackage('random')
    config.add_subpackage('ma')
    config.add_data_dir('doc')
    config.add_data_dir('tests')
    config.scons_make_config_py() # installs __config__.py
    return config

if __name__ == '__main__':
    print('This is the wrong setup.py file to run')
