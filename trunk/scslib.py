#!/usr/bin/python
# Subversion Configuration System Manager
# Library File

import ConfigParser
import sys
import json
import os
import shutil
import fcntl
import re
import subprocess

## functions starting with lowercase 's' are for the server component only
## functions starting with lowercase 'c' are for the client component only
## all other functions are intended for both

################################################################################

def fatal(msg,code=1):
	sys.stderr.write(msg + "\n")
	sys.exit(1)
	
################################################################################	

def sLoadConfig(configFile):
	#### Variable defaults
	svnroot  = '/opt/scsm/svn/'
	scsmroot = '/opt/scsm/scsm/'
	metafilePath = '/opt/scsm/www/server.meta'
	
	#### LOAD CONFIG
	config = ConfigParser.RawConfigParser()
	config.read(configFile)

	if config.has_option('server','svn root'):
		configValue = config.get('server','svn root')
		if os.path.isdir(configValue):
			svnroot = configValue
		else:
			fatal('The subversion root specified in ' + configFile + ' is not a directory')

	if config.has_option('server','metadata file'):
		configValue = config.get('server','metadata file')
		if os.path.isfile(configValue):
			metafilePath = configValue
		else:
			fatal('The metadata file specified in ' + configFile + ' is not a file')

	if config.has_option('server','scsm root'):
		configValue = config.get('server','scsm root')
		if os.path.isdir(configValue):
			scsmroot = configValue
		else:
			fatal('The scsm root specified in ' + configFile + ' is not a directory')
			
	return (svnroot,scsmroot,metafilePath)
	
################################################################################

def sLockAndLoad(metadataPath):
	global metafileHandle
	metafileHandle = None

	try:
		metafileHandle = open(metadataPath,'r+')
		fcntl.flock(metafileHandle,fcntl.LOCK_EX)
	except (IOError, OSError) as e:
		fatal('Unable to lock ' + str(e.filename) + ': ' + str(e.strerror))

	try:
		jsonData = metafileHandle.read()
		metafileHandle.seek(0)
	except (IOError, OSError) as e:
		fatal('Unable to read from ' + e.filename + ': ' + e.strerror)

	## Handle empty data
	if len(jsonData) == 0:
		metadict = {'channels': {}, 'packages': {}}
	else:
		## Turn json data into python objects
		try:
			metadict = json.loads(jsonData)
		except (TypeError,ValueError) as e:
			fatal('Unable to understand metadata: ' + str(e))
			
	return metadict
	
################################################################################

def sSaveAndUnlock(metadict):
	global metafileHandle
	
	## Turn "metadict" into json
	jsonOut = json.dumps(metadict, sort_keys=True, indent=4)

	## Write to file
	try:
		metafileHandle.seek(0)
		metafileHandle.truncate(0)
		metafileHandle.write(jsonOut)
		metafileHandle.close
	except (IOError, OSError) as error:
		fatal('Failed to write metadata: ' + error.strerror + ' on ' + error.filename)

def sCreateSVN(path,name,svntype):
	## Validate the name
	regex = re.compile('^[a-zA-Z\_\-0-9]+$')
	matched = regex.match(name)
	if not matched:
		fatal('Invalid name! Name must only contain a-z, 0-9 or the characters _ and -')

	## Check dir doesnt already exist
	if os.path.exists(path):
		fatal('That ' + svntype + ' already exists!')

	svnadmin = subprocess.Popen(['svnadmin', 'create', path],stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
	(stdoutdata, stderrdata) = svnadmin.communicate()

	## Handle errors
	if svnadmin.returncode > 0:
		fatal(stdoutdata)

################################################################################

def svn_delete(path,svntype):
	if os.path.exists(path):
		shutil.rmtree(path)
	else:
		print >> sys.stderr, 'That ' + svntype + ' does not exist!'
		sys.exit(1)
