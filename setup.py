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
        'includes': ['atexit', 'nauta'],
        'packages': ['parsel','lxml','requests','pyqt5.QtWidgets','pyqt5.QtCore','termcolor',
                    'threading', 'qtawesome', 'six', 'pipes', 'w3lib', 'cssselect', 'tinydb',
                    'ctypes','colorama'],
        'include_msvcr': True,
        'optimize': 2,
        'excludes': ['tkinter']
    }
}

executables = [
    Executable('nauta_gui.py', base=base,
               targetName='nauta_gui.exe',),
    Executable('main.py', base=base2,
               targetName='nauta_cli.exe',)
]

setup(name='Nauta',
      version='2.0.0',
      description='gui and cli for control nauta connection and accounts',
      options=options,
      executables=executables
      )
