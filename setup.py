# -*- coding: utf-8 -*-
import sys
from cx_Freeze import setup, Executable

base = None
if sys.platform == 'win32':
    base = 'Console'

options = {
    'build_exe': {
        'includes': ['atexit','nauta'],
        'packages': ['bs4', 'lxml','requests', 'fire', 'lockfile','queue','dbm','pyqt5'],
        'include_msvcr': True,
        'optimize': 2
    }
}

executables = [
    Executable('main.py', base=base,
               targetName='nauta_cli.exe',),
    Executable('nauta_gui.py', base=base,
               targetName='nauta_gui.exe',)
]

setup(name='nauta_cli',
      version='3.0.0',
      description='cli and gui for control nauta connection and accounts',
      options=options,
      executables=executables
      )
