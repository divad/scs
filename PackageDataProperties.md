<h1>SCS Package Data Properties</h1>

The core function of SCS is to install configuration files (or other files) and to deal with local changes (in a way defined by the package creator or the system administrator). To do this SCS packages are divided into two - "scripts" and "data". Packages contain "scripts" which are run at various points (such as on upgrade of a package). Packages also have a "data" component which is what this article focuses on.

Inside the "data" directory of an SCS package the package designer/creator will place files and directories and then mark each file or directory with "properties" to let SCS know what to do with them. SCS packages are at their most basic level Subversion repositories, so the Subversion properties feature is used to add the SCS metadata or properties to each file within "data".

Upon an installation of an SCS package (or an upgrade) SCS will "install" the package data. It does this by looking at each file in turn and reading the Subversion properties set against it. These tell SCS what to then do with the file.

<h2>List of properties:</h2>




---


## action ##

When the "dest" property is set (See below) then SCS needs to know what you'd like to do with the file.

The "action" property defaults to the value "copy" if the "dest" property is set.

### copy ###

Copy the file to the location specified by the "dest" property.

Copy can only apply to files, it is ignored when set against directories.

### link ###

Link to the file from the location specified by "dest" property.

The file remains in (by default) /opt/scs/client/packages/

&lt;name&gt;

/data/

&lt;file&gt;

 but a symbolic link is created at "dest" linked to the file.


---


## dest ##

This is an optional property. When not set then no copying or linking takes place. If set then the "dest" property is used by the process specified by the "action" property, see above.


---


## ifexists ##

When copying or linking the path specified by the "dest" property might already exist. In this case the "ifexists" property is consulted on what to do. If that property is unset then "


---


## check ##

If the file has been modified locally after package [revision 1](https://code.google.com/p/scs/source/detail?r=1) is installed, on upgrade to package [revision 2](https://code.google.com/p/scs/source/detail?r=2) the file will be overwritten with the contents of package 2 - if any.

You can control this behaviour on a per-file basis:


---


### ignore ###

Silently ignore the local change and overwrite its contents from the new package revision.

### warn (Default) ###

Ignore the local change and overwrite its contents from the new package revision. This logs a warning during upgrade.

### fail ###

The package revision upgrade does not take place, instead the whole package will be suspended pending administrator input (they can then use --force to override local changes on the command line).

### skip ###

The package is still upgraded but this file is skipped from the upgrade process altogether. This is not recommended but in certain cases this might be useful.


---


## chmod ##

Set the octal permissions.


---


## owner ##

Set the owner.


---


## group ##

Set the group.


---


## uid ##


---


## gid ##


---


## immutable ##