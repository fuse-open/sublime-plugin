# Fuse Sublime package 1.4.16
* Switched to using stdout instead of Fuse Protocol events for output, to support future versions of Fuse

# Fuse Sublime package 1.4.15
* Added support for starting preview when selecting a project folder that contains an unoproj
* Fixed a bug where the plugin would crash

# Fuse Sublime package 1.4.14
* Added logging for communication with the Fuse daemon

# Fuse Sublime package 1.4.13
* Added UX syntax and completion for .ngux extension (Angular 2 integration)
* Renamed 'Fuse: Local Preview' to 'Fuse: Preview Local', 'Fuse: Android Preview' to 'Fuse: Preview Android', and 'Fuse: iOS Preview' to 'Fuse: Preview iOS',
	to be consistent with the naming scheme in the Atom plugin. 

# Fuse Sublime package 1.4.12
* Improved error handling

# Fuse Sublime package 1.4.11
* Fixed code completion bug with closing `<JavaScript>` tags (it used to close the `<App>` tag instead)
* Windows: Suggest to reboot if fuse is not in path

# Fuse Sublime package 1.4.10
* Use correct logging directory on Windows
* Create logging directory if it doesn't exist
* Write Sublime version and plugin version to log

# Fuse Sublime package 1.4.9
* Improved error handling

# Fuse Sublime package 1.4.8
## Changes
* "Visual cues in preview" toggle button changed to "Select element at caret".
* Build view was updated to include new type of debug data.

## Bug fixes
* Fixed possible exception when right clicking in a file without extension.

# Fuse Sublime package 1.4.7
## Changes
* Removed project creation until a better gui can be supplied

## Bug fixes
* Fixed broken fuse create commands

# Fuse Sublime package 1.4.6
## Bug fixes
* Fixed builds failing after altered Fuse install path
* Disabling visual cues in the fuse menu should now correctly remove any active cues rather than let them linger.

# Fuse Sublime package 1.4.5
## Bug fixes
* Preview build log was broken in last release, this is now fixed.

# Fuse Sublime package 1.4.4
## Bug fixes
* Fixed build tagging breaking build outputs

# Fuse Sublime package 1.4.3
## Bug fixes
* Fixed build systems mismatch  on OSX

## Changes
* Added selection ability for preview.
	The carret position is used to select elements. 
	A cue of current selected element should be shown inside preview.
	Toggle this feature on and off from the Fuse menu item inside sublime.
	NOTE: This feature is only available in Fuse 0.5.3524 and upwards.


# Fuse Sublime package 1.4.2

## Bug fixes
* Fixed user guide showing up on EVERY first run

# Fuse Sublime package 1.4.1

## Changes
* Added a user guide showing up on first run

# Fuse Sublime package 1.4

## Changes
* Added fuse create options for json and js files
* Added user guide document and display option

# Fuse Sublime package 1.3.9

## Bug fixes
* Building from Fuse build system should now properly trigger build log output

## Changes
* Moved menu items to existing relevant menus. "New Fuse project..." is now under the Project menu, for instance.
* Removed Goto Definition until it can be better implemented
* Replaced default build system use with a system of defaults. Pick a build target with ctrl+shift+b and future ctrl+b will use that target.
* Right clicking in sidebar and choosing "Fuse: Build" now uses the same build target as ctrl+b.
* Added message dialog in case no default build target has been set

# Fuse Sublime package 1.3.8

## New features

## Changes
* Build result views will now be reused for each target and project.
* Build result views are now not spawned for builds initiated outside of Sublime.

# Fuse Sublime package 1.3.7

## New features

## Regression
* Removed json/js creation options temporarily to expedite plugin release

## Changes
* Improved AutoComplete speed and hickups by not blocking the editor thread while doing a Fuse CodeCompletion request
* Improved UX syntax highlightning to include support for periods in tag names
* UX attribute name folding is now set to be default on

## Bug fixes
* Fixed issue where creating files under a path that included periods would fail
* Fixed auto complete inside ux:Binding attribute value

# Fuse Sublime package 1.3.6

## New features
* Template instancing for json and javascript

## Changes
* Relabeled and moved some menu items around for clarity

## Bug fixes
* Fixed issue where creating files under a path that included periods would fail

# Fuse Sublime package 1.3.5

## New features
* Build systems for android, ios, cmake and dotnet
* Command palette implementations of most fuse commands
* Better error checking and handling for fuse commands

# Fuse Sublime package 1.3.4

## New features
* Added context menus to sidebar for creating ux, uno and project templates

## Bug fix
* Minor text changes for clarity

# Fuse Sublime package 1.3.3

## Bug fix
* A fix for code completion problems introduced in last release.

# Fuse Sublime package 1.3.2

## New features
* A new setting called "fuse_show_build_results" has been added. Set this to false to disable the use of build result tabs.

# Fuse Sublime package 1.3.1

## New features
* Your app can now be previewed for different targets from Sublime. Triggered by right clicking in a ux file, and selecting "Preview UX".
* Build result view will now start in it is own tab
* Debug log in Sublime is removed
