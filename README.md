Sublime Plugin
==================
Sublime plugin for Fuse Editor. 

How to install on Windows
=================
Fuse will install the plugin on demand, so the steps below are not neccessary in normal circumstances.

NOTE: The automatically installer does not work if you have installed the plugin manually

Go to AppData/Roaming (Type %appdata% in file explorer). Find the "Sublime Text 3" folder, and go into "Packages".
Clone repo into this folder, and RENAME the folder to "Fuse", and restart sublime if it's already open.

Also if you have set the default syntax language for .uno and .ux files before, you must set these again. Set .uno to Fuse/Uno and .ux to Fuse/UX.

This is a temporary install solution. There will be an eaiser way of doing this in the future.

How to install on Mac OS X
=================
Fuse will install the plugin on demand, so the steps below are not neccessary in normal circumstances. 

NOTE: The automatically installer does not work if you have installed the plugin manually

Go to ~/Library/Application Support. Find the "Sublime Text 3" folder, and go into "Packages".
Clone repo into this folder, and RENAME the folder to "Fuse", and restart sublime if it's already open.

Also if you have set the default syntax language for .uno and .ux files before, you must set these again. Set .uno to Fuse/Uno and .ux to Fuse/UX.

This is a temporary install solution. There will be an eaiser way of doing this in the future.

Current Features
=================
* Code completion
* Goto definition (F12 - Win) or in the menu called Goto->Goto definition
* Build result(should open automatically if errors or warnings) but can be found in the menu called Fuse->Build result
* Debug log ouput can be found in the menu called Fuse->Output
* Build and run from sublime (F7 - Win, CMD+E - Mac OS X)
* Recompile (F6 - Win, shift+Cmd+R - Mac OS X)
* Build log found in the Fuse menu
