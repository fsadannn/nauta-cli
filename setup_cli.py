# -*- coding: utf-8 -*-
import sys
from cx_Freeze import setup, Executable

base = None
if sys.platform == 'win32':
    base = 'Console'

options = {
    'build_exe': {
        'includes': ['atexit','nauta'],
        'packages': ['bs4', 'lxml','requests', 'fire', 'lockfile','queue','dbm'],
        'include_msvcr': True,
        'optimize': 2
    }
}

executables = [
    Executable('main.py', base=base,
               targetName='nauta_cli.exe',),
]

setup(name='nauta_cli',
      version='2.0.2',
      description='cli for control nauta connection and accounts',
      options=options,
      executables=executables
      )
