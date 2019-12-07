# -*- coding: utf-8 -*-
import sys
from cx_Freeze import setup, Executable

base = None
if sys.platform == 'win32':
    base = 'Win32GUI'

base2 = None
if sys.platform == 'win32':
    base2 = 'Console'

options = {
    'build_exe': {
        'includes': ['atexit','nauta'],
        'packages': ['bs4', 'lxml','requests', 'lockfile','queue','dbm','pyqt5','pipes','termcolor'],
        'include_msvcr': True,
        'optimize': 2
    }
}

executables = [
    Executable('nauta_gui.py', base=base,
               targetName='nauta_gui.exe',),
    Executable('main.py', base=base2,
               targetName='nauta_cli.exe',)
]

setup(name='Nauta',
      version='1.0.1',
      description='gui and cli for control nauta connection and accounts',
      options=options,
      executables=executables
      )
