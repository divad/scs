#!/usr/bin/python

from distutils.core import setup

setup(name='scs',
      version='1.0',
      summary='Subversion Configuration System',
      licence='GPL3',
      description='A unix system configuration tool based around subversion',
      platform='Linux',
      url='http://code.google.com/p/scs/',
      author='David Bell',
      author_email='dave@evad.info',
      py_modules=['scslib','scsclient'],
      scripts=['scsc','scs','scsp'],
      data_files=[('/etc',['etc/scs.conf'])]
      )
