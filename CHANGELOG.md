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