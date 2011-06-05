#!/usr/bin/python

import os 
from fnmatch import fnmatch 
import wx
import wx.lib.sheet as sheet

class PropsPage(wx.Panel):

	def __init__(self, parent):
		wx.Panel.__init__(self,parent)

		hbox = wx.BoxSizer(wx.HORIZONTAL)
		fgs = wx.FlexGridSizer(3, 2, 9, 25)
		title = wx.StaticText(self, label="Title")
		author = wx.StaticText(self, label="Author")
		review = wx.StaticText(self, label="Review")
		tc1 = wx.TextCtrl(self)
		tc2 = wx.TextCtrl(self)
		tc3 = wx.TextCtrl(self, style=wx.TE_MULTILINE)

		fgs.AddMany([(title), (tc1, 1, wx.EXPAND), (author), (tc2, 1, wx.EXPAND), (review, 1, wx.EXPAND), (tc3, 1, wx.EXPAND)])

		fgs.AddGrowableRow(2, 1)
		fgs.AddGrowableCol(1, 1)

		hbox.Add(fgs, proportion=1, flag=wx.ALL|wx.EXPAND, border=15)
		self.SetSizer(hbox)

class FileTree(wx.TreeCtrl): 
 
	def __init__(self, parent, id=-1, pos=wx.DefaultPosition, 
                 size=wx.DefaultSize, style=wx.TR_DEFAULT_STYLE| wx.TR_HIDE_ROOT, 
                 validator=wx.DefaultValidator, name="", 
                 rootfolder=".", file_filter=("*.*")): 

		wx.TreeCtrl.__init__( self, parent, id, pos, size, style, validator, name) 
		self.file_filter = file_filter 
		il = wx.ImageList(16,16) 
		self.fldridx = il.Add(wx.ArtProvider.GetBitmap(wx.ART_FOLDER, wx.ART_OTHER, (16,16))) 
		self.fldropenidx = il.Add(wx.ArtProvider.GetBitmap(wx.ART_FILE_OPEN, wx.ART_OTHER, (16,16))) 
		self.fileidx = il.Add(wx.ArtProvider.GetBitmap(wx.ART_NORMAL_FILE, wx.ART_OTHER, (16,16))) 
		self.AssignImageList(il)
        
		root = self.AddRoot(os.path.split(rootfolder)[1]) 
		self.SetItemImage(root, self.fldridx,wx.TreeItemIcon_Normal) 
		self.SetItemImage(root, self.fldropenidx,wx.TreeItemIcon_Expanded) 
		self.AddTreeNodes(root, rootfolder)
		try: 
			self.Expand(root) 
		except: 
			# not if we have a hidden root 
			pass 

	def AddTreeNodes(self, parentItem, rootfolder): 
		items = os.listdir(rootfolder) 
		items = sorted(items,key=str.lower) 
		folders = [] 
		files = [] 

		for item in items: 
			if item[0]==".": 
				continue 
			itempath = os.path.join(rootfolder, item) 
			if os.path.isfile(itempath): 
				fileok=False 
				for filter in self.file_filter: 
					if fnmatch(item, filter): 
						fileok=True 
						break 
				if fileok: 
					files.append((item,itempath)) 
			else: 
				folders.append((item,itempath))
 
		for folder, itempath in folders+files: 
			newItem = self.AppendItem(parentItem, folder) 
			if os.path.isfile(itempath): 
				self.SetItemImage(newItem, self.fileidx,wx.TreeItemIcon_Normal) 
			elif os.path.isdir(itempath): 
				self.SetItemImage(newItem, self.fldridx,wx.TreeItemIcon_Normal) 
				self.SetItemImage(newItem, self.fldropenidx, wx.TreeItemIcon_Expanded) 
				self.AddTreeNodes(newItem, itempath) 
			self.SetPyData( newItem, itempath) 
	def GetFilePath(self): 
		return self.GetPyData(self.GetSelection())

class MySheet(sheet.CSheet):
	def __init__(self, parent):
		sheet.CSheet.__init__(self, parent)
		self.SetNumberRows(50)
		self.SetNumberCols(50)

class PackageEditor(wx.Frame):

	def onSelect(self, event):
		print "I GOT AN EVENT!"
		tree = event.GetEventObject()
		path = tree.GetPyData(event.GetItem())
		print path

	def __init__(self, parent, id, title):
		
		## Super constructor
		wx.Frame.__init__(self, parent, id, title, size=(600, 500))

		## Menus
		menubar = wx.MenuBar()
		file = wx.Menu()
		file.Append(101, 'Quit', '' )
		menubar.Append(file, '&File')
		self.SetMenuBar(menubar)

		wx.EVT_MENU(self, 101, self.OnQuit)

		## Notebook (tabbed notebook)
		nb = wx.Notebook(self, -1, style=wx.NB_TOP)

		## Panel for file browser
		self.splitter = wx.SplitterWindow(nb, -1, style = wx.SP_LIVE_UPDATE)
		
		self.panelLeft = wx.Panel(self.splitter,-1,style=wx.BORDER_SUNKEN)
		self.panelRight = PropsPage(self.splitter)
		#self.dirBrowser = wx.GenericDirCtrl(self.panel, wx.ID_ANY, style = wx.DIRCTRL_3D_INTERNAL,name="props")
		#self.dirBrowser.SetDefaultPath('/tmp/')
		#self.dirBrowser.SetPath('/tmp/')
		#self.dirBrowser.ShowHidden(True)

		self.dirBrowser = FileTree(self.panelLeft, rootfolder="/home/drb")
		sizer = wx.BoxSizer(wx.VERTICAL)
		sizer.Add(self.dirBrowser,1,wx.EXPAND)
		self.panelLeft.SetSizer(sizer)

		self.dirBrowser.Bind(wx.EVT_TREE_SEL_CHANGED,  self.onSelect, id=id)
		self.splitter.SplitVertically(self.panelLeft, self.panelRight)

		self.sheet1 = MySheet(nb)
		self.sheet3 = MySheet(nb)

		nb.AddPage(self.sheet1, 'Overview')
		nb.AddPage(self.splitter, 'Data Manager')
		nb.AddPage(self.sheet3, 'Script Editor')

		self.sheet1.SetFocus()
#		self.StatusBar()
		self.Centre()
		self.Show()

		self.splitter.SetMinimumPaneSize(200)
#		self.splitter.SetSashPosition(100)		#

#	def StatusBar(self):
#		self.statusbar = self.CreateStatusBar()

	def OnQuit(self, event):
		self.Close()

app = wx.App()
PackageEditor(None, -1, 'SCS Package Editor')
app.MainLoop()
