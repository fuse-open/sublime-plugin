Sublime Plugin
==================
Sublime plugin for Fuse Editor

How to install
=================
Go to AppData/Roaming (Type %appdata% in file explorer). Find the "Sublime Text 3" folder, and go into "Packages".
Clone repo into this folder, and RENAME the folder to "Fuse", and restart sublime if it's already open.

Also if you have set the default syntax language for .uno and .ux files before, you must set these again. Set .uno to Fuse/Uno and .ux to Fuse/UX.

This is a temporary install solution. There will be an eaiser way of doing this in the future.

Current Features
=================
* Code completion, however not for UX attributes
* Goto definition (F12) or in the menu called Goto->Goto definition
* Build result(should open automatically if errors or warnings) but can be found in the menu called Fuse->Build result
* Debug log ouput can be found in the menu called Fuse->Output
* Refresh viewport from sublime (F5)
