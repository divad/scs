The scripts are:

| preinit | script to run when package installed, before |
|:--------|:---------------------------------------------|
| postinit | script to run when package installed, after |
| uninit | script to run when package removed |
| preup | script to run when package upgraded, before upgrade |
| postup | script to run when package is upgraded, after upgrade |
| preinst | script to run before installation of package data |
| postinst | script to run after installation of package data |
| preinc | script run in existing version package just before new version is installed |

# Script Orders #

Initial package install:

  1. preinit
  1. preinst
  1. <inst stage>
  1. postinst
  1. postinit

On uninit:

  1. uninit

On upgrade:

  1. preinc (old package revision)
  1. preup
  1. preinst
  1. <inst stage>
  1. postinst
  1. postup