#!/usr/bin/python

import distutils.core

distutils.core.setup(name='scs',
      version='17',
      license='GPL3',
      description='A unix system configuration tool based around subversion',
      long_description='''SCS is a configuration management system for Unix 
      systems such as servers and workstations. SCS is a lightweight system. 
      It enforces strong use of version control (via Subversion) and, unlike 
      systems like CFengine and Puppet, it does not force you to write code 
      which is idempotent - instead SCS allows you to choose between 
      "Transactional" mode and "Idempotent" mode.''',
      url='http://code.google.com/p/scs/',
      author='David Bell',
      author_email='dave@evad.info',
      py_modules=['scslib','scsclient'],
      scripts=['scsc','scs','scsp','scsinit'],
      )
