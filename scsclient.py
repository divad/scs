#!/usr/bin/python
# Subversion Configuration System Manager
# Client Library File
# This "scsclient" is a Module

import os
import stat
import sys
import pysvn
import subprocess
import shutil
import pwd
import grp
import ConfigParser
import logging
import smtplib
from email.mime.text import MIMEText
import socket
import re
import scslib
from scslib import inform, meta, svnclient

class scsClient:
	dataroot = '/opt/scs/client/'
	svnurl   = ''
	metaurl  = ''
	smtp     = 'localhost'
	mailaddr = None
	svnuser  = None
	svnpass  = None
	remoteMeta = None
	
	## This is bascially a constructor, except I can't call it immediatley (why?)
	def loadConfig(self,filepath):
		config = ConfigParser.RawConfigParser()
		config.read(filepath)
	
		## log file
		if config.has_option('client','log file'):
			inform.openLog(config.get('client','log file'))
		else:
			inform.openLog('/var/log/scs.log')
	
		## data root
		if config.has_option('main','data root'):
			configValue = config.get('main','data root')
			
			if os.path.isdir(configValue):
				self.dataroot = os.path.join(configValue,'client')
				if not os.path.isdir(self.dataroot):
					inform.fatal('The directory ' + self.dataroot + ' is not a directory or does not exist!')
			else:
				inform.fatal('The data root specified in ' + configValue + ' is not a directory')				
				
		## svn url
		if config.has_option('client','svn url'):
			self.svnurl = config.get('client','svn url')
		else:
			inform.fatal('No svn url defined in ' + filepath)
			
		## svn user (HTTP(S))
		if config.has_option('client','svn username'):
			self.svnuser = config.get('client','svn username')
		else:
			if re.match('https?\://',self.svnurl):
				inform.fatal('SVN http url specified but no svn username is defined in ' + filepath)
			
		if config.has_option('client','svn password'):
			self.svnpass = config.get('client','svn password')
		else:
			if re.match('https?\://',self.svnurl):
				inform.fatal('SVN http url specified but no svn password is defined in ' + filepath)
			
		## svn url must include a trailing slash
		if not self.svnurl[-1] == '/':
			self.svnurl = self.svnurl + '/'

		if config.has_option('client','metadata url'):
			self.metaurl = config.get('client','metadata url')
		else:
			inform.fatal('No metadata url defined in ' + filepath)
		
		## email options
		if config.has_option('client','smtp server'):
			configValue = config.get('client','smtp server')
			self.smtp = configValue
		if config.has_option('client','notify email'):
			configValue = config.get('client','notify email')
			self.mailaddr = configValue	
			
		## Tell svnclient the u/p function
		svnclient.callback_get_login = self.getSvnLogin
		
		## Fetch remote metadata!
		self.remoteMeta = scslib.fetchRemoteMetadata(self.metaurl)
			
	## Callback function for pySVN to consult
	def getSvnLogin(self, realm, username, may_save):
	    return True, self.svnuser, self.svnpass, False

	## "check" property
	### before increment it checks all files with "check" property
	#### check value can be:
	#### - fail - Fail the entire package upgrade if the local file has changed - DOES NOT OVERWRITE
	#### - ignore - (default) - Do nothing - don't care - OVERWITES LOCAL CHANGES
	#### - warn - Warn the file has changed - OVERWRITES LOCAL CHANGES
	#### - skip - don't change /that/ file, and that file alone, on the next increment - DOES NOT OVERWRITE
	def checkForLocalChanges(self,pkg):
		ignoreList = []
		propList = svnclient.proplist(os.path.join(self.dataroot,'packages',pkg,'data'),recurse=True)
	
		## Return code
		# 0 - no locally changed files
		# 1 - locally changed files, but they were all skipped
		# 2 - locally changed files, but they were all skipped or warned about
		# 3 - locally changed files, DO NOT PROCEED!
		retcode = 0

		for propSet in propList:
			source     = propSet[0]
			properties = propSet[1]

			if 'dest' in properties:
				dest = properties['dest']
				inform.debug('Checking for local changes on file: ' + dest,log=True)

				## Get SHA sums
				try:
					sourceh = scslib.shasum(source)
					desth   = scslib.shasum(dest)
				except Exception as e:
					inform.warn('Cannot check for local changes on ' + dest + ': ' + str(e))
				else:
					## Compare sums
					if not sourceh == desth:

						inform.debug('The file ' + dest + ' has been modified outside of SCS control',log=True)

						# default is warn - i.e. it overwrites
						checkAction = 'warn'

						if 'check' in properties:
							checkAction = properties['check']

						inform.debug('The file has been configured to "' + checkAction + '" in this scenario',log=True)

						if checkAction == 'fail':
							retcode = 3
							inform.error("Local changes found in package " + pkg + ", file " + dest)						
						elif checkAction == 'warn':
							retcode = 2					
							inform.warn("WARNING! Local changes found to file " + dest)
						elif checkAction == 'skip':
							retcode = 1					
							## add the file to the "ignore" list
							ignoreList.append(source)
						
		return (retcode, ignoreList)

	################################################################################
	################################################################################

	def packageInstalled(self,pkg):
		if meta.data['packages'].has_key(pkg):
			return True
		else:
			return False

	################################################################################
	################################################################################

	def channelSubscribed(self,channel):
		if meta.data['channels'].has_key(channel):
			return True
		else:
			return False

	################################################################################
	################################################################################

	def listFiles(self,pkg):
		propList = svnclient.proplist(os.path.join(self.dataroot,'packages',pkg,'data'),recurse=True)

		for propSet in propList:
			source     = propSet[0]
			properties = propSet[1]

			if 'dest' in properties:
				dest = properties['dest']
				print "{0:38}  {1:38}".format(dest, source)

	################################################################################
	################################################################################

	def printPackageHeader(self):
		print "{0:14}  {1:14}  {2:9}  {3:37}".format('PACKAGE NAME','REVISION','STATUS','DESCRIPTION')
		print "{0:14}  {1:14}  {2:9}  {3:37}".format('------------','--------','------','-----------')

	################################################################################
	################################################################################

	def printPackageInfo(self,pkg):
		data = meta.data['packages'][pkg]
		if type(data).__name__=='dict':
			if self.isPackageSuspended(data['name']):
				flags = 'SUSPENDED'
			else:
				flags = 'OK'

			if data.has_key('name') and data.has_key('revision') and data.has_key('desc'):
				print "{0:14}  {1:14}  {2:9}  {3:37}".format(str(data['name']), str(data['revision']), flags, str(data['desc']))
			elif data.has_key('name') and data.has_key('revision'):
				print "{0:14}  {1:14}  {2:9}  {3:37}".format(str(data['name']), str(data['revision']), flags,'N/A')
			else:
				inform.fatal('Unable to understand data: ' + str(e))
		else:
			inform.fatal('Unable to understand data: ' + str(e))

	################################################################################
	################################################################################

	def suspendPackage(self,pkg,reason):
		if self.packageInstalled(pkg):
			meta.data['packages'][pkg]['status'] = 'suspended'
			meta.data['packages'][pkg]['suspend_reason'] = reason
			
	################################################################################
	################################################################################			

	def resumePackage(self,pkg):
		if self.isPackageSuspended(pkg):
			del(meta.data['packages'][pkg]['status'])
			del(meta.data['packages'][pkg]['suspend_reason'])
			
	################################################################################
	################################################################################			

	def isPackageSuspended(self,pkg):
		if self.packageInstalled(pkg):
			if meta.data['packages'][pkg].has_key('status'):
				if meta.data['packages'][pkg]['status'] == 'suspended':
					return True

		return False

	################################################################################
	################################################################################

	## Runs a package script, returns false 
	def runScript(self,pkgName,scriptName):
		inform.debug('Executing ' + scriptName,log=True)
		scriptPath = os.path.join(self.dataroot,'packages',pkgName,'scripts',scriptName)

		## CHMOD First
		os.chmod(scriptPath,stat.S_IRWXU)

		if os.path.getsize(scriptPath) == 0:
			inform.debug("Script is empty; not executing",log=True)
			return False

		## Now run the script
		try:
			script = subprocess.Popen([scriptPath],stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
			(stdoutdata, stderrdata) = script.communicate()
		
			## If the command returned a non-zero exit we should log its full output to error()
			if not script.returncode == 0:
				inform.error(stdoutdata)
		
				## Log the error
				inform.error(scriptName + ' script returned non-zero')
		
				## Return true to say we found an error
				return True
		
		except OSError as e:
			inform.error('Execution of script ' + scriptName + ' failed: ' + str(e))
			## Return true to say we found an error
			return True
		
		## Return no errors (False = no errors!
		return False

	################################################################################
	################################################################################

	# 0 = success
	# 1 = false
	def uninitPkg(self,pkg):

		if self.packageInstalled(pkg):
			errorOccured = self.runScript(pkg,'uninit')
		
			if errorOccured:
				return 1
			else:
				## Delete data
				shutil.rmtree(os.path.join(self.dataroot,'packages',pkg))

				## Update metadata
				del(meta.data['packages'][pkg])

				## Output
				inform.info('Removed package "' + pkg + '"')
	
				## Return OK
				return 0
		else:
			inform.info('Package "' + pkg + '" not installed so not removing',log=True)
			return 0

	################################################################################
	################################################################################

	def isChannelUpToDate(self,channel):
		remotePath  = self.svnurl + '/' + channel + '/'

		## Get the latest revision of the channel
		infoList = svnclient.info2(remotePath,recurse=False)
		for infoTuple in infoList:
			infoDict = infoTuple[1]
			latestRevision = infoDict['rev']
		inform.debug('Latest remote channel revision is ' + str(latestRevision.number))

		## Get the installed revision
		localRevision = int(meta.data['channels'][channel]['revision'])
		inform.debug('Latest local channel revision is ' + str(localRevision))
	
		if localRevision == latestRevision.number:
			return 1
		else:
			return 0
		
	################################################################################
	################################################################################		
		
	def updateChildChannels(self,channel):
		# List all channels
		for name in meta.data['channels']:
	
			# If its a child channel
			if meta.data['channels'][name].has_key('parent'):
		
				# And its parent is the channel we care about
				if meta.data['channels'][name]['parent'] == channel:

					# Then update it
					self.updateChannel(name)
				
	################################################################################
	################################################################################				

	# results
	# 0 OK!
	# 1 Could not upgrade
	def updateChannel(self,channel):
		inform.debug('updateChannel(' + channel + ') called')

		if self.channelSubscribed(channel):
			remotePath  = self.svnurl + channel + '/'
			localPath   = os.path.join(self.dataroot,'channels',channel)
			localPkgs   = os.path.join(localPath,'packages')
			upgradeFile = remotePath + 'upgrade'

			## Get the latest revision of the channel
			infoList = svnclient.info2(remotePath,recurse=False)
			for infoTuple in infoList:
				infoDict = infoTuple[1]
				latestRevision = infoDict['rev']
			inform.debug('Latest remote channel revision is ' + str(latestRevision.number))

			## Get the installed revision
			localRevision = int(meta.data['channels'][channel]['revision'])
			inform.debug('Latest local channel revision is ' + str(localRevision))

			## Decide upon which revision to go to????
			if localRevision == latestRevision.number:
				## Mark the channel as up to date
				inform.info('Channel "' + channel + '" is up to date')

				## Update child channels
				self.updateChildChannels(channel)
				return 0
			else:
				inform.info('Updating channel "' + channel + '" to revision ' + str(localRevision +1))
				revisionToUse = pysvn.Revision(pysvn.opt_revision_kind.number, localRevision + 1)

			## No need to download the upgrade file, we'll just read its properties from remote :)
			## Get the properties
			propList = svnclient.proplist(upgradeFile,revision=revisionToUse)

			for propSet in propList:
				properties = propSet[1]

				if properties.has_key('name') and properties.has_key('revision') and properties.has_key('action'):
					if properties['action'] == 'install':
						## Install 'revision' of 'name'
						(retCode,faultMsg) = self.initPkg(properties['name'],int(properties['revision']))
					
						if retCode > 0:
							inform.error("Could not init/upgrade " + properties['name'] + ". Channel could not be updated")

							## Alert email
							if not self.mailaddr == None:
								text  = "An error occured whilst trying to update the channel '" + channel + "'\n"
								text += "The error occured within the package '" + properties['name'] + "'\n"
								text += "Reason: " + faultMsg
							
								hostname = socket.gethostname()
							
								msg = MIMEText(text)
								msg['Subject'] = "scs on " + hostname + " failed to update channel '" + channel + "'"
								msg['From'] = 'root@' + hostname
								msg['To'] = self.mailaddr
					
								smtp = smtplib.SMTP(self.smtp)
								smtp.sendmail('root@' + hostname, self.mailaddr, msg.as_string())
								smtp.quit()
					
							## Return 1 to say we failed
							return 1

				elif properties.has_key('name') and properties.has_key('action'):
					if properties['action'] == 'remove':
						## Remove 
						result = self.uninitPkg(properties['name'])

						if result == 1:
							inform.fatal("Could not upgrade channel. Please correct the error and try to upgrade again")
							return 1
					
				else:
					inform.warn('Warning! Channel upgrade file does not have properties set against it!')

			## Update package info (Although we don't actually use the info until an unsubscribe - but they are there if an admin wants them)
			svnclient.update(localPkgs,revision=revisionToUse)

			## Save new revision
			meta.data['channels'][channel]['revision'] = revisionToUse.number;

			## We're upgraded
			if revisionToUse.number < latestRevision:
		
				## We need to recursive-call and upgrade again! :)
				self.updateChannel(channel)
			
			else:		
				## Update child channels
				self.updateChildChannels(channel)

		else:
			inform.fatal('Not subscribed to channel ' + channel,log=False)
		
	################################################################################
	################################################################################		
		
	def installPackageData(self,localDataPath,ignoreList=[]):
		"""Install the package data as described via Subversion properties in the package.

		Takes two arguments. The first is a string, the path of the "data" folder
		which has been checked out from subversion. The second is a list of strings, each
		of which is a path (installation path) which should be skipped from being installed.

		The function will apply properties for each file found in the "data" folder of
		the package. If errors are found the package then an error is returned and the
		entire package install/upgrade should be aborted. The only exceptions to this
		are when a file is skipped due to being in the ignore list OR if the destination
		of a file already exists and the "ifexists" propery is set to "skip".
		"""

		## Get properties from the local data path
		fileList = svnclient.proplist(localDataPath,recurse=True)

		## For each file...
		for propSet in fileList:
			source     = propSet[0]
			properties = propSet[1]

			## Skip files we've been instructed to due to local changes
			if source in ignoreList:
				inform.debug('Skipping file ' + source + ' from inst stage due to local changes')
				continue;

			## If there is a 'dest' property...
			if 'dest' in properties:
				dest = properties['dest']
			
				## Default action is copy
				action = 'copy'

				## Load a user-defined action
				if 'action' in properties:
					action = properties['action']

				## Deal with immutability - i.e. remove it!
				### if destination file exists, and isn't a symbolic link then remove immutable flag
				if os.path.exists(dest):
					if not os.path.islink(dest):
						if scslib.isFileImmutable(dest):

							## Remove immutable flag
							chattr = subprocess.Popen(['chattr', '-i', dest],stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
							(stdoutdata, stderrdata) = chattr.communicate()
							retcode = chattr.returncode

							## If the command failed
							if retcode > 0:
								inform.debug('Unable to remove immutable flag from ' + dest)
								## return an error
								return True


				## Determine the source file type
				if os.path.isfile(source):
					pathtype = 'file'
				elif os.path.isdir(source):
					pathtype = 'dir'
				else:
					inform.error("Source file - " + source + " - is not a file or directory.")
					## return an error
					return True

				## Does the destination exist?
				if os.path.lexists(dest):
					inform.warn("Installing file from '" + source + "' to '" + dest + "': Destination already exists")

					## If the destination is a directory then immediatley fail
					if os.path.isdir(dest):
						inform.error("Cannot install file - existing destination is a directory")
						return True
					
					## Otherwise determine what we should do			

					## Yes, it exists
					# default action is to generate an error and back out
					ifexists = 'error'

					## Load a user-defined 
					if 'ifexists' in properties:
						ifexists = properties['ifexists']

					## Determine what to do based on "ifexists"
					if ifexists == 'skip':
						inform.error("Skipping installation as per configuration of file")
						continue;

					elif ifexists == 'delete':
						## Try to delete the file first
						inform.warn("Deleting existing file")

						try:
							os.unlink(dest)
						except (IOError, OSError) as e:
							inform.error("Unable to delet existing file '" + dest + "': " + str(e))
							return True
						
					else:
						inform.error("Cannot install file")
						return True			

				## What is the target file? If copying its the "dest" property, otherwise its the "source" (cos it'll be a symlink or no action)
				target = source

				## COPY THE SOURCE TO THE DEST
				if action == 'copy':
					target = dest

					if pathtype == 'file':
						try:
							shutil.copyfile(source,dest)
						except IOError as e:
							inform.error("Unable to copy from " + source + " to " + dest + ": " + str(e))
							return True
					else:
						inform.error("Unable to copy from " + source + " to " + dest + ": Source is not a file")
						return True

				elif action == 'link':
					try:
						os.symlink(source,dest)
					except (IOError, OSError) as e:
						inform.error("Unable to link " + source + " to " + dest + ": " + str(e))
						return True

			## THE "CHMOD", "OWNER", "GROUP", "UID" and "GID" properties apply to
			## the "target" variable which differs based on the type of "action" (or not action)

			## chmod - set the permissions to octal mode
			if 'chmod' in properties:
				try:
					os.chmod(target,int(properties['chmod'],8))
				except Exception as e:
					inform.error('Could not apply chmod property to ' + dest + ': ' + str(e))	
					return True

			## owner - set the owner to
			if 'owner' in properties:
				try:
					pwdid = pwd.getpwnam(properties['owner'])
					uid = pwdid[2]
					os.chown(target,uid,-1)
				except Exception as e:
					inform.error('Could not apply owner property to ' + dest + ': ' + str(e))
					return True

			## group - set the group to
			if 'group' in properties:
				try:
					grpid = grp.getgrnam(properties['group'])
					gid = grpid[2]
					os.chown(target,-1,gid)
				except Exception as e:
					inform.error('Could not apply group property to ' + dest + ': ' + str(e))
					return True

			if 'uid' in properties:
				try:
					os.chown(target,properties['uid'],-1)
				except Exception as e:
					inform.error('Could not apply uid property to ' + dest + ': ' + str(e))
					return True

			## group - set the group to
			if 'gid' in properties:
				try:
					os.chown(target,-1,properties['gid'])
				except Exception as e:
					inform.error('Could not apply gid property to ' + dest + ': ' + str(e))
					return True

			## immutable - set the file to immutable after
			if 'immutable' in properties:
				## NOTE although python has os.chflags, due to a python configure bug they
				## are NEVER compiled in - stupid python.

				if not os.path.islink(dest):
					chattr = subprocess.Popen(['chattr', '+i', dest],stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
					(stdoutdata, stderrdata) = chattr.communicate()
					retcode = chattr.returncode

					if retcode > 0:
						inform.error(stdoutdata)
						return True
					
				else:
					inform.warn('Not applying immutable attribute to symlink - not possible')
				
		
		## Return false, no error occured
		return False

	################################################################################
	################################################################################

	# Returns 0 if it was init'ed
	# Returns 1 if it wasn't
	# Returns 2 if it was, but failures occured and the package is now suspended
	# Returns a string or None, if error is 1/2 its a string saying why, useful for logging or whatever

	def initPkg(self,pkg,rev=-1,ignore=False):
		## See if the package requested actually exists
		found = False
		for pkgName in self.remoteMeta['packages']:
			if pkgName == pkg:
				found = True

		## Catch errors
		if not found:
			inform.error('Could not find package to install in server metadata')
			return (1,'Could not find package to install in server metadata')

		if self.remoteMeta['packages'][pkg].has_key('desc'):
			packageDescription = self.remoteMeta['packages'][pkg]['desc']
		else:
			packageDescription = ''

		## Work out paths
		remotePath   = self.svnurl + pkg + '/' 
		localPath    = os.path.join(self.dataroot,'packages',pkg)
		localScripts = os.path.join(localPath,'scripts')
		localData    = os.path.join(localPath,'data')

		## Get latest remote revision
		infoList = svnclient.info2(remotePath,recurse=False)
		for infoTuple in infoList:
			infoDict = infoTuple[1]
			latestRevision = infoDict['rev']

		## Should we use a speciifc max version? (for channels tagged at a specific version)
		if rev >= 0 and rev <= latestRevision.number:
			latestRevision = pysvn.Revision(pysvn.opt_revision_kind.number, rev)

		## What type, init or upgrade?
		upgrade = False

		## A list of files to ignore during property-apply phase
		ignoreList = []

		## If this is an upgrade
		if self.packageInstalled(pkg):
			upgrade = True

			## Get local revision installed
			localRevision = int(meta.data['packages'][pkg]['revision'])

			## Is the package suspended?
			if self.isPackageSuspended(pkg):
				inform.error("Package '" + pkg + "' is currently suspended: " + meta.data['packages'][pkg]['suspend_reason'])
				return (1,"Package '" + pkg + "' is currently suspended: " + meta.data['packages'][pkg]['suspend_reason'])

			## Are we already up to date?
			if localRevision >= latestRevision.number:
				inform.info('Package ' + pkg + ' up to date (revision ' + str(localRevision) + ')')
				return (0,None)
			else:
				revisionToUse = pysvn.Revision(pysvn.opt_revision_kind.number, int(localRevision) + 1)

			inform.info('Updating package "' + pkg + '" to revision ' + str(revisionToUse.number),log=True)

			## If we shouldn't then check for local changes
			if not ignore:
				inform.info('Checking for local changes',log=True)
				(localChangesResult,ignoreList) = self.checkForLocalChanges(pkg)
			
			## If local changes were detected and we must not proceed because of them...
			if localChangesResult == 3:
				inform.error('One or more files have been changed locally, this must be corrected before upgrading')
				return (1,'One or more files have been changed locally, this must be corrected before upgrading')

			## Pre-increment ("pre-upgrade") script
			if self.runScript(pkg,'preinc'):
				inform.error('Could not init package')
				return (1,'The preinc script returned an error')

			## Update data now
			inform.debug('Updating package data')
			svnclient.update(localData,revision=revisionToUse)
		
		else:
			revisionToUse = latestRevision
			inform.info('Installing ' + pkg,log=True)

			## Create paths only if they haven't been already
			## This can happen if a pre* script failed
			if not os.path.isdir(localPath):
				## set up directory layout
				try:
					os.mkdir(localPath)
					os.mkdir(os.path.join(localPath,'conf'))
					os.mkdir(os.path.join(localPath,'scripts'))
					os.mkdir(os.path.join(localPath,'data'))
				except (OSError, IOError) as e:
					inform.fatal('Failed to init package. Error was: ' + e.strerror + ' on ' + e.filename)

				## Initial check out of data
				inform.debug('Deploying package data')
				svnclient.checkout(remotePath + 'data',localData,revision=revisionToUse)

			else:
				inform.debug('Updating package data')
				svnclient.update(localData,revision=revisionToUse)

		inform.debug('Deploying scripts')
		svnclient.export(remotePath + 'scripts',localScripts,revision=revisionToUse,force=True,recurse=True)

		## Run scripts
		if upgrade:
			if self.runScript(pkg,'preup'):
				inform.error('Cancelling package init 1')
				return (1,'The preup script returned an error')			
		else:
			if self.runScript(pkg,'preinit'):
				inform.error('Cancelling package init 2')
				return (1,'The preinit script returned an error')

		if self.runScript(pkg,'preinst'):
			inform.error('Cancelling package init 3')
			return (1,'The preinst script returned an error')

		## If anything fails now then we can't/shouldn't stop, but we should mark
		## a failure and then optionally the calling function can suspend the pkg
		## and channel
		faultMsg  = ''

		## Install the package data
		faultOccured = self.installPackageData(localData,ignoreList=ignoreList)
	
		if faultOccured:
			faultMsg = 'A fault occured during applying package data properties'
		else:

			## Success! Run the post scripts

			if self.runScript(pkg,'postinst'):
				faultMsg = 'The postinst script returned an error'
				faultOccured = True

			if upgrade:
				if self.runScript(pkg,'postup'):
					faultMsg = 'The postup script returned an error'
					faultOccured = True
			else:
				if self.runScript(pkg,'postinit'):
					faultMsg = 'The postinit script returned an error'
					faultOccured = True

		## Output some info
		inform.info('Package ' + pkg + ' now at revision ' + str(revisionToUse.number),log=True)

		## update metadata
		meta.data['packages'][pkg] = { 'name': pkg, 'revision': revisionToUse.number, 'desc': packageDescription}

		if faultOccured:
			self.suspendPackage(pkg,faultMsg)
			inform.error('An error occured during the init process. The package "' + pkg + '" is now suspended')
			return (2,'An error occured during the init process. The package "' + pkg + '" is now suspended')
		else:
			## Recursive call package if we're not at the latest now
			if revisionToUse.number < latestRevision.number:
				return self.initPkg(pkg)
			else:
				inform.info('Package ' + pkg + ' is now up to date',log=True)
				return (0,None)

client = scsClient()
