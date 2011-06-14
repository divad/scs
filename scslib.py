#!/usr/bin/python
# Subversion Configuration System Manager
# Library File
# This "scslib" is a Module

import ConfigParser
import sys
import json
import os
import shutil
import fcntl
import re
import subprocess
import errno
import logging
import logging.handlers 
import urllib
import hashlib
import errno
import pwd
import grp
import pysvn
import stat

## functions starting with lowercase 's' are for the server component only
## functions starting with lowercase 'c' are for the client component only
## all other functions are intended for both, classes follow the same rules

################################################################################	
################################################################################	
################################################################################

def version():
	return 47
	
def versionStr():
	return str(version())

## informant
## used for logging to file and stdout/stderr
class informant:
	logOpened = False
	logger = logging.getLogger('scs')
	quietFlag = False
	debugFlag = False

	def setDebug(self):
		self.debugFlag = True
		
	def setQuiet(self):
		self.quietFlag = True

	def openLog(self,logfile):
		self.logger.setLevel(logging.DEBUG)
	
		handler = logging.handlers.RotatingFileHandler(logfile, maxBytes=512000, backupCount=5)
		formatter = logging.Formatter("%(asctime)s %(name)s %(levelname)s: %(message)s")
		handler.setFormatter(formatter)

		self.logger.addHandler(handler)
		self.logOpened = True

	def debug(self,o,log=False):
		if not self.quietFlag:
			if self.debugFlag:
				print str(o)
			
		if log and self.logOpened:
			self.logger.debug(str(o))

	def warn(self,o,log=True):
		if not self.quietFlag:
			print str(o)
		
		if log and self.logOpened:
			self.logger.warning(str(o))

	def error(self,o,log=True):
		sys.stderr.write(str(o) + "\n")
	
		if log and self.logOpened:
			self.logger.error(str(o))
	
	def info(self,o,log=False):
		if not self.quietFlag:
			print str(o)
		
		if log and self.logOpened:
			self.logger.info(str(o))

	def fatal(self,o,code=1,log=True):
		## Log the fault
		if log and self.logOpened:
			self.logger.critical(str(o))
	
		## Panic and quit
		sys.stderr.write('FATAL: ' + str(o) + "\n")
		sys.exit(code)
		
################################################################################	
################################################################################	
################################################################################

## metaman
## used for loading and saving metadata, either on the client program or server
class metaman:
	data = {}
	filePath = ''
	fd = None
	
	def load(self,path):
		self.filePath = path

		## open and lock file
		try:
			self.fd = open(self.filePath,'r+')
			fcntl.lockf(self.fd,fcntl.LOCK_EX | fcntl.LOCK_NB)
		except (IOError, OSError) as exception:
			if exception.errno == errno.EAGAIN or exception.errno == errno.EACCES:
				inform.fatal('Sorry, another process is currently executing - try again later')
			else:
				inform.fatal('Unable to lock metadata: ' + str(exception.filename) + ': ' + str(exception.strerror))

		## read data
		try:
			jsonData = self.fd.read()
			self.fd.seek(0)
		except (IOError, OSError) as e:
			inform.fatal('Unable to read from ' + e.filename + ': ' + e.strerror)

		## Convert to python objects from json
		if len(jsonData) == 0:
			self.data = {'channels': {}, 'packages': {}}
		else:
			## Turn json data into python objects
			try:
				self.data = json.loads(jsonData)
			except (TypeError,ValueError) as e:
				inform.fatal('Unable to understand metadata: ' + str(e))

	def save(self):
		## Turn python objects into json
		jsonOut = json.dumps(self.data, sort_keys=True, indent=4)

		## Write to file
		try:
			self.fd.seek(0)
			self.fd.truncate(0)
			self.fd.write(jsonOut)
			self.fd.close
		except (IOError, OSError) as error:
			## We can't call fatal here since this function() might be called FROM it!
			## The best we can do is write to the stderr... TODO??
			sys.stderr.write('Failed to write metadata: ' + error.strerror + ' on ' + error.filename)
	
def sLoadConfig(configFile):

	## Defaults
	conf = {
		'svnroot': '/opt/scsm/svn/',
		'dataroot': '/opt/scsm/',
		'metadataPath': '/opt/scsm/www/server.meta'
	}

	#### LOAD CONFIG
	config = ConfigParser.RawConfigParser()
	config.read(configFile)

	if config.has_option('server','svn root'):
		configValue = config.get('server','svn root')
		if os.path.isdir(configValue):
			conf['svnroot'] = configValue
		else:
			inform.fatal('The subversion root specified in ' + configFile + ' is not a directory')

	if config.has_option('server','metadata file'):
		configValue = config.get('server','metadata file')
		if os.path.isfile(configValue):
			conf['metadataPath'] = configValue
		else:
			inform.fatal('The metadata file specified in ' + configFile + ' is not a file')

	if config.has_option('main','data root'):
		configValue = config.get('main','data root')
		
		if os.path.isdir(configValue):
			conf['dataroot'] = os.path.join(configValue,'server')
			if not os.path.isdir(conf['dataroot']):
				inform.fatal('The directory ' + conf['dataroot'] + ' is not a directory or does not exist!')
		else:
			inform.fatal('The data root specified in ' + configFile + ' is not a directory')			
			
	if config.has_option('server','svn user'):
		conf['svnuser'] = config.get('server','svn user')
	else:
		conf['svnuser'] = None
		
	if config.has_option('server','svn group'):
		conf['svngroup'] = config.get('server','svn group')
	else:
		conf['svngroup'] = None
		
	if config.has_option('server','svn chmod'):
		conf['svnchmod'] = config.get('server','svn chmod')
	else:
		conf['svnchmod'] = None
						
	return conf	
	
def listChannel(chandict,metadict,depth):
	depthStr = ''
	
	if depth >= 0:
		for i in range(depth):
			depthStr += ' '
		depthStr += ' + '

	## Channel print
	if chandict.has_key('desc'):
		print depthStr + chandict['name'] + ' (' + chandict['desc'] + ')'
	else:
		print depthStr + chandict['name']
		
	## Child channels
	for channame in metadict['channels']:	
		if metadict['channels'][channame].has_key('parent'):
			if metadict['channels'][channame]['parent'] == chandict['name']:
				listChannel(metadict['channels'][channame],metadict,depth+1)
	
def listChannels(metadict):
	depth  = -1
	
	## For each channel...
	for channame in metadict['channels']:

		## Only print non-child channels
		if not metadict['channels'][channame].has_key('parent'):	
			listChannel(metadict['channels'][channame],metadict,depth)
			
def requireRoot():
	if not os.geteuid() == 0:
		inform.fatal("You must be root to run this program")
		
def sCreateSVN(path,name,conf):
	## Validate the name
	regex = re.compile('^[a-zA-Z\_\-0-9]+$')
	matched = regex.match(name)
	if not matched:
		inform.fatal('Invalid name! Name must only contain a-z, 0-9 or the characters _ and -')

	## Check dir doesnt already exist
	if os.path.exists(path):
		inform.fatal('A subversion repository with that name already exists')

	svnadmin = subprocess.Popen(['svnadmin', 'create', path],stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
	(stdoutdata, stderrdata) = svnadmin.communicate()

	## Handle errors
	if svnadmin.returncode > 0:
		inform.fatal(stdoutdata)

	## Unlock revprops (For some odd reason they're turned off by default. Thanks Subversion)
	try:
		hookfile = os.path.join(path,'hooks','pre-revprop-change')
		hook = open(hookfile,'w')
		hook.write("#!/bin/sh\n")
		hook.write("exit 0\n")
		hook.close()
		os.chmod(hookfile,stat.S_IRWXU)
	except (OSError, IOError) as error:
		inform.fatal('Unable to enable revision properties: ' + error.strerror + ' on ' + error.filename)	

	## Fix perms
	fixPerms(path,conf)
	
def sCloneSVN(oldpath,newpath,name,conf):
	## Validate the name
	regex = re.compile('^[a-zA-Z\_\-0-9]+$')
	matched = regex.match(name)
	if not matched:
		inform.fatal('Invalid name! Name must only contain a-z, 0-9 or the characters _ and -')

	## Check dir doesnt already exist
	if os.path.exists(newpath):
		inform.fatal('A subversion repository with that name already exists')

	svnadmin = subprocess.Popen(['svnadmin', 'hotcopy', oldpath, newpath],stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
	(stdoutdata, stderrdata) = svnadmin.communicate()

	## Handle errors
	if svnadmin.returncode > 0:
		inform.fatal(stdoutdata)
		
	## Fix perms
	fixPerms(oldpath,conf)
	fixPerms(newpath,conf)
	
def fixPerms(path,conf):
	# Yes, I should probably use os.path.walk and os.chmod, but screw that, thats
	# so stupidly long winded and this works perfectly fine.

	if not conf['svnchmod'] == None:
		proc = subprocess.Popen(['chmod', '-R',str(conf['svnchmod']), path],stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
		(stdoutdata, stderrdata) = proc.communicate()
		if proc.returncode > 0:
			inform.error(stdoutdata)

	if not conf['svnuser'] == None:		
		proc = subprocess.Popen(['chown', '-R',conf['svnuser'], path],stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
		(stdoutdata, stderrdata) = proc.communicate()
		if proc.returncode > 0:
			inform.error(stdoutdata)

	if not conf['svngroup'] == None:		
		proc = subprocess.Popen(['chgrp', '-R',conf['svngroup'], path],stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
		(stdoutdata, stderrdata) = proc.communicate()
		if proc.returncode > 0:
			inform.error(stdoutdata)
			
################################################################################

def sDeleteSVN(path):
	if os.path.exists(path):
		shutil.rmtree(path)
	else:
		print >> sys.stderr, 'That repository does not exist!'
		sys.exit(1)
		
################################################################################		

def isFileImmutable(filePath):
	script = subprocess.Popen(['/usr/bin/lsattr','-d',filePath],stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
	(stdoutdata, stderrdata) = script.communicate()
		
	if script.returncode == 0:
		if (stdoutdata[4] == 'i'):
			return True
		else:
			return False
	else:
		inform.error(stdoutdata)
		inform.error("Unable to determine if filePath is immutable")
		return False
		
################################################################################		
		
def fetchRemoteMetadata(metadataUrl):
	inform.debug('Fetching metadata from server')
	try:
		f = urllib.urlopen(metadataUrl)
		jsonData = f.read()
		f.close()
	except IOError as e:
		inform.fatal('Unable to download ' + metadataUrl + ': ' + str(e.strerror))

	try:
		metadict = json.loads(jsonData)
	except (TypeError,ValueError) as e:
		inform.fatal('Unable to understand server metadata: ' + str(e))

	return metadict	

################################################################################	

def shasum(filePath,blocksize=2**20):
	sha = hashlib.sha256()
	f = open(filePath,'rb')
	while True:
		data = f.read(blocksize)
		if not data:
			break;
		sha.update(data)
	return sha.hexdigest()

## Load "global" object instances
# Inform object
inform = informant()

# metadata object
meta = metaman()

# svn client
svnclient = pysvn.Client()
